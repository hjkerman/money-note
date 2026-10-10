"""Synthetic bounded financial commands + 12 projections + atomic finalization.

Only self-owned temporary SQLite. No configured DB, HTTP, credentials or app
startup. Preparation/legacy full-state differential oracles are outside timing.
"""

import argparse
from collections import Counter
from datetime import date
import json
import math
import os
from pathlib import Path
import platform
import resource
import sqlite3
import statistics
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts" / "benchmarks"))
from t66d2b import check_output, summarize  # noqa: E402


class CountedCursor:
    """Returned rows only; VM/proof/query plan cover work not returned to Python."""
    def __init__(self, cursor, counter):
        self.cursor, self.counter = cursor, counter

    def __getattr__(self, name):
        return getattr(self.cursor, name)

    def __iter__(self):
        for row in self.cursor:
            self.counter[0] += 1
            yield row

    def fetchone(self):
        row = self.cursor.fetchone()
        self.counter[0] += row is not None
        return row

    def fetchall(self):
        rows = self.cursor.fetchall()
        self.counter[0] += len(rows)
        return rows


def historical_scans(sql, plans):
    if "LIMIT 0" in sql.upper():
        return []  # schema-column probe: no row is visited
    return [p for p in plans if p.startswith("SCAN ") and not any(
        token in p for token in ("sqlite_master", "sync_current", "sync_tx_context", "sync_capture_profile", "sync_finalization_profile", "app_settings", "app_labels",
                                "authoritative_state_revision", "monthly_panels", "SCAN p "))]


def seed(conn, count):
    from isolated_sync.raw import MONEY_SETTINGS
    from tests.test_isolated_sync_capture import ROWS, insert
    for table, source in ROWS.items():
        value = dict(source)
        if table == "cash_flows":
            value["amount_value"] = -50
        insert(conn, table, value)
    conn.execute("DELETE FROM card_payment_deferrals")
    for key in MONEY_SETTINGS:
        conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
    conn.execute("INSERT INTO app_settings(key,value) VALUES ('last_closed_month','2026-09')")
    for n in range(count-1):
        value = dict(id=1000+n, book_section="current" if n < 104 else "archive", entry_kind="expense",
                     entry_date="2026-10-05" if n < 104 else "2026-07-03", title="synthetic-"+str(n),
                     amount_value=1000, sort_order=n, payment_key="synthetic-"+str(n), usage_place="synthetic-shop")
        if n == 0:
            value.update(entry_kind="planned", entry_date=None, payment_key=None, due_day=5, usage_place="service")
        insert(conn, "ledger_entries", value)
    insert(conn, "monthly_panels", dict(id=101, month="2026-10", panel_type="fixed", title="fixed", amount_value=500, sort_order=2, due_day=5))


def command(name, conn, trial):
    from app.repositories.entries import update_entry, delete_entry, confirm_planned_entry
    from app.repositories.cash_flows import create_cash_flow
    from app.schemas import LedgerEntryPatch, CashFlowIn, CardPaymentEventIn
    from app.services.card_payments import create_card_payment_event
    from app.services.card_charge.profiles import set_transit_discount_profile
    from app.services.panels import confirm_fixed_panel
    day = date(2026, 10, 5)
    if name == "card":
        return update_entry(1002, LedgerEntryPatch(amount_value=1000+trial % 2), conn=conn)
    if name == "cash":
        return create_cash_flow(CashFlowIn(occurred_on="2026-10-05", title="cash", amount_value=-10, sort_order=2), conn=conn)
    if name == "historical_update":
        return update_entry(1300, LedgerEntryPatch(title="history-"+str(trial)), conn=conn)
    if name == "historical_delete":
        return delete_entry(1300, conn=conn)
    if name == "payment":
        return create_card_payment_event(CardPaymentEventIn(event_date=day, event_type="immediate", idempotency_key="d2b-payment-sample-"+str(trial),
                                         allocations=[dict(entry_payment_key="card-100", amount_value=1)]), today=day, conn=conn)
    if name == "recurring":
        with patch("app.repositories.entries.new_payment_key", return_value="trial-recurring"):
            return confirm_planned_entry(1000, today=day, actual_amount=500, conn=conn)
    if name == "fixed":
        return confirm_fixed_panel(101, "2026-10-05", actual_amount=400, today=day, conn=conn)
    if name == "policy":
        return set_transit_discount_profile("2026-10", "owner" if trial % 2 else "none", conn=conn)
    if name == "several_rows":
        update_entry(1002, LedgerEntryPatch(title="multi-"+str(trial)), conn=conn)
        update_entry(1003, LedgerEntryPatch(title="multi-"+str(trial)), conn=conn)
        return create_cash_flow(CashFlowIn(occurred_on="2026-10-05", title="multi", amount_value=10, sort_order=3), conn=conn)
    if name != "no_change":
        raise ValueError("unknown synthetic command")


def prepare_next(name, result, conn, deleted):
    """Keep hot composition fixed; real cleanup transaction outside the sample."""
    from app.repositories.cash_flows import delete_cash_flow
    from app.repositories.entries import delete_entry
    from app.services.card_payments import delete_card_payment_event
    from isolated_sync.inputs import BoundedInputs
    from tests.test_isolated_sync_capture import insert
    if name not in {"cash", "historical_delete", "payment", "recurring", "fixed", "several_rows"}:
        return
    conn.begin_capture()
    writer = BoundedInputs(conn)
    if name in {"cash", "several_rows"}:
        delete_cash_flow(result["id"], conn=writer)
    elif name == "historical_delete":
        insert(writer, "ledger_entries", deleted)
    elif name == "payment":
        delete_card_payment_event(result["id"], conn=writer)
    elif name == "recurring":
        delete_entry(result["entry"]["id"], conn=writer)
    else:
        delete_cash_flow(result["cash_flow"]["id"], conn=writer)
    conn.finalize()
    conn.commit()


def run(output, targets, samples):
    from isolated_sync.finalization import FinalizationSandbox
    from isolated_sync.inputs import BoundedInputs
    from tests.d2b_financial_reference import projections
    from tests.test_isolated_sync_finalization import verify
    report = dict(starting_commit="158fbaab6867e0edda6b37647e129b743dd077b8", seed=662602,
                  evaluation_date="2026-10-05", hot_rows=105, profile="bounded-financial-inputs/3",
                  environment=dict(python=sys.version, sqlite=sqlite3.sqlite_version,
                                   platform=platform.platform(), cpu_count=os.cpu_count()), datasets={})
    for count in targets:
        with FinalizationSandbox() as db:
            with db.connect() as conn:
                seed(conn, count)
            db.install()
            started = time.perf_counter()
            db.bootstrap()
            entry = dict(rows=count, archived=count-105, bootstrap_ms=(time.perf_counter()-started)*1000, workloads={})
            with db.connect() as conn:
                verify(conn)
                deleted = dict(conn.execute("SELECT * FROM ledger_entries WHERE id=1300").fetchone())
                for name in ("card", "cash", "historical_update", "historical_delete", "payment", "recurring", "fixed", "policy", "no_change", "several_rows"):
                    measured, templates = [], set()
                    for trial in range(3+samples):
                        counts, vm, returned = Counter(), [0], [0]
                        execute = conn.execute
                        def observed(sql, parameters=()):
                            counts[sql.split()[0].upper()] += 1
                            templates.add(sql)
                            return CountedCursor(execute(sql, parameters), returned)
                        def progress():
                            vm[0] += 1
                            return 0
                        conn.execute = observed
                        conn.set_progress_handler(progress, 100)
                        start, cpu = time.perf_counter(), time.process_time()
                        conn.begin_capture()
                        writer_start = time.perf_counter()
                        writer = BoundedInputs(conn)
                        result = command(name, writer, trial)
                        writer_ms = (time.perf_counter()-writer_start)*1000
                        projection_start = time.perf_counter()
                        actual = projections(writer)
                        projection_ms = (time.perf_counter()-projection_start)*1000
                        metrics = conn.finalize()
                        commit_start = time.perf_counter()
                        conn.commit()
                        metrics.update(commit_ms=(time.perf_counter()-commit_start)*1000,
                                       total_ms=(time.perf_counter()-start)*1000, cpu_ms=(time.process_time()-cpu)*1000,
                                       writer_ms=writer_ms, projection_ms=projection_ms,
                                       input_object_reads=writer.store.reads, relationship_rows=writer.relationship_rows,
                                       sql=dict(counts), result_rows=returned[0], sqlite_vm_steps_lower_bound=vm[0]*100)
                        conn.execute = execute
                        conn.set_progress_handler(None, 0)
                        if trial >= 3:
                            measured.append(metrics)
                        # Legacy financial oracle (including history scans) is
                        # OUTSIDE observed/timed transaction on the same rows.
                        conn.execute("BEGIN DEFERRED")
                        assert actual == projections(conn)
                        conn.rollback()
                        prepare_next(name, result, conn, deleted)
                    plans, errors, scans = [], [], []
                    for sql in templates:
                        if sql.split()[0].upper() in {"SELECT", "INSERT", "UPDATE", "DELETE"}:
                            try:
                                # EXPLAIN only, trusted diagnostics: allow compilation
                                # of metadata SQL otherwise denied outside finalizer.
                                with conn._metadata():
                                    details = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN "+sql, [None]*sql.count("?"))]
                                plans.extend(details)
                                scans.extend(historical_scans(sql, details))
                            except sqlite3.Error as error:
                                errors.append(type(error).__name__)
                    # Alias-aware: include generated/planned/owned and a/e too.
                    scans = sorted(set(scans))
                    values = [s["total_ms"] for s in measured]
                    entry["workloads"][name] = dict(warmups=3, samples=measured, median_ms=statistics.median(values),
                        p95_ms=sorted(values)[math.ceil(len(values)*.95)-1], min_ms=min(values), max_ms=max(values),
                        stdev_ms=statistics.stdev(values) if len(values)>1 else 0,
                        ordinary_ledger_scans=scans, plan_errors=errors, unique_query_plans=sorted(set(plans)), differential="PASS")
                    print(f"completed synthetic {count}/{name}", flush=True)
                # Full raw/tree/facts/adjacency/aggregate oracle before and
                # after EACH dataset. Every sample still compares all twelve
                # legacy projections. Neither oracle is part of timing.
                verify(conn)
            entry["process_maxrss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report["datasets"][str(count)] = entry
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--targets", nargs="+", type=int, default=[376, 1000, 5000, 10000])
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--summarize", type=Path)
    args = parser.parse_args()
    check_output(args.output)
    if set(args.targets)-{376, 1000, 5000, 10000} or not 1 <= args.samples <= 30:
        parser.error("bounded synthetic scales/samples required")
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (3600, 3600))
    if args.summarize:
        if not args.summarize.resolve().is_relative_to(Path("/tmp")):
            parser.error("/tmp diagnostic input required")
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(summarize(json.loads(args.summarize.read_bytes())), handle, indent=2)
            handle.write("\n")
    else:
        run(args.output, args.targets, args.samples)

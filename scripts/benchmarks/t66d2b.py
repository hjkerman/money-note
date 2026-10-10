"""Opt-in D2b synthetic whole-transaction benchmark; no configured DB access.

Frozen seed 662600, fixed hot rows, archive-only growth. Full differential
oracles run OUTSIDE timed transactions. SQL text/row values never enter output.
"""

import argparse
from collections import Counter
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


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def check_output(output):
    resolved = output.resolve()
    if (not resolved.is_relative_to(Path("/tmp")) or resolved.is_relative_to(ROOT) or output.exists()):
        raise ValueError("new /tmp diagnostic output required")


def summarize(report):
    """Compact aggregates only; raw samples remain outside the checkout."""
    result = {k: v for k, v in report.items() if k != "datasets"}
    result["datasets"] = {}
    for count, dataset in report["datasets"].items():
        compact = {k: v for k, v in dataset.items() if k != "workloads"}
        compact["workloads"] = {}
        for name, workload in dataset["workloads"].items():
            samples = workload["samples"]
            values = {k: v for k, v in workload.items() if k not in {"samples", "unique_query_plans"}}
            values["sample_count"] = len(samples)
            values["median_metrics"] = {k: statistics.median(s[k] for s in samples)
                                         for k in samples[0] if k != "sql"}
            verbs = set().union(*(s["sql"] for s in samples))
            values["median_sql_calls"] = {k: statistics.median(s["sql"].get(k, 0) for s in samples)
                                          for k in sorted(verbs)}
            compact["workloads"][name] = values
        result["datasets"][count] = compact
    return result


def run(output, targets, samples):
    from isolated_sync.finalization import FinalizationSandbox
    from isolated_sync.raw import MONEY_SETTINGS
    from tests.test_isolated_sync_capture import ROWS, insert
    from tests.test_isolated_sync_finalization import verify

    report = dict(starting_commit="158fbaab6867e0edda6b37647e129b743dd077b8",
                  seed=662600, evaluation_date="2026-10-05", hot_rows=105,
                  environment=dict(python=sys.version, sqlite=sqlite3.sqlite_version,
                                   platform=platform.platform(), cpu_count=os.cpu_count()), datasets={})
    for count in targets:
        with FinalizationSandbox() as db:
            with db.connect() as conn:
                for table, source in ROWS.items():
                    value = dict(source)
                    if table == "cash_flows":
                        value["amount_value"] = -50
                    insert(conn, table, value)
                for key in MONEY_SETTINGS:
                    conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
                for n in range(count-1):
                    insert(conn, "ledger_entries", dict(id=1000+n, book_section="current" if n < 104 else "archive",
                           entry_kind="expense", entry_date="2026-10-05" if n < 104 else "2026-07-03",
                           title="synthetic-"+str(n), amount_value=1000, sort_order=n, payment_key="synthetic-"+str(n)))
            db.install()
            start = time.perf_counter()
            db.bootstrap()
            bootstrap = (time.perf_counter()-start)*1000
            entry = dict(rows=count, archived=count-105, bootstrap=dict(samples=1, warmups=0, ms=bootstrap,
                         reason="expensive O(N) initialization, not steady-state; no repeated bootstrap claim"), workloads={})
            with db.connect() as conn:
                verify(conn)
                operations = {
                    "card_row": ("UPDATE ledger_entries SET title=? WHERE id=1000",),
                    "cash_row": ("UPDATE cash_flows SET title=? WHERE id=100",),
                    "historical_update": ("UPDATE ledger_entries SET title=? WHERE id=1300",),
                    "historical_delete": ("DELETE FROM ledger_entries WHERE id=1300",),
                    "payment": ("UPDATE card_payment_events SET note=? WHERE id=100",),
                    "no_change": (),
                    "several_rows": ("UPDATE ledger_entries SET title=? WHERE id IN (1000,1001,1300)",),
                }
                for name, queries in operations.items():
                    measurements, sql_templates = [], set()
                    for trial in range(3 + samples):
                        counts = Counter()
                        vm_callbacks = [0]
                        execute = conn.execute

                        def observed(sql, parameters=()):
                            counts[sql.split()[0].upper()] += 1
                            sql_templates.add(sql)
                            return execute(sql, parameters)

                        conn.execute = observed
                        def progress():
                            vm_callbacks[0] += 1
                            return 0
                        conn.set_progress_handler(progress, 100)
                        start = time.perf_counter()
                        cpu_start = time.process_time()
                        conn.begin_capture()
                        raw_start = time.perf_counter()
                        for sql in queries:
                            conn.execute(sql, ("changed-"+str(trial),) if "?" in sql else ())
                        raw_ms = (time.perf_counter()-raw_start)*1000
                        metrics = conn.finalize()
                        commit_start = time.perf_counter()
                        # Measured COMMIT. Workload preparation below is outside
                        # timing; the historical delete is real in every trial.
                        conn.commit()
                        commit_ms = (time.perf_counter()-commit_start)*1000
                        total = (time.perf_counter()-start)*1000
                        conn.execute = execute
                        conn.set_progress_handler(None, 0)
                        metrics.update(total_ms=total, raw_ms=raw_ms, commit_ms=commit_ms,
                                       cpu_ms=(time.process_time()-cpu_start)*1000, sql=dict(counts),
                                       sqlite_vm_steps_lower_bound=vm_callbacks[0]*100)
                        if trial >= 3:
                            measurements.append(metrics)
                        # Restore only the test workload's removed row, through the
                        # SAME finalizer. This preparation is outside the sample.
                        if name == "historical_delete":
                            conn.begin_capture()
                            insert(conn, "ledger_entries", dict(id=1300, book_section="archive", entry_kind="expense",
                                   entry_date="2026-07-03", title="synthetic-300", amount_value=1000,
                                   sort_order=300, payment_key="synthetic-300"))
                            conn.finalize()
                            conn.commit()
                    plans, scans = [], []
                    for sql in sql_templates:
                        if sql.lstrip().split()[0].upper() in {"SELECT", "INSERT", "UPDATE", "DELETE"}:
                            try:
                                plan = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN "+sql, [None]*sql.count("?"))]
                                plans.extend(plan)
                                scans.extend(p for p in plan if "SCAN ledger_entries" in p and "LIMIT 0" not in sql)
                            except sqlite3.Error:
                                pass
                    verify(conn)
                    totals = [m["total_ms"] for m in measurements]
                    entry["workloads"][name] = dict(warmups=3, samples=measurements,
                        median_ms=statistics.median(totals), p95_ms=sorted(totals)[math.ceil(len(totals)*.95)-1],
                        min_ms=min(totals), max_ms=max(totals), stdev_ms=statistics.stdev(totals) if len(totals)>1 else 0,
                        ordinary_ledger_scans=scans, unique_query_plans=sorted(set(plans)), differential="PASS")
            entry["process_maxrss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report["datasets"][str(count)] = entry
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summarize", type=Path, help="summarize an existing /tmp raw report without a database")
    parser.add_argument("--targets", nargs="+", type=int, default=[376, 1000, 5000, 10000])
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()
    try:
        check_output(args.output)
    except ValueError as error:
        parser.error(str(error))
    if set(args.targets)-{376, 1000, 5000, 10000} or not 1 <= args.samples <= 30:
        parser.error("bounded synthetic targets/samples required")
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (1800, 1800))
    if args.summarize:
        if not args.summarize.resolve().is_relative_to(Path("/tmp")):
            parser.error("/tmp diagnostic input required")
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(summarize(json.loads(args.summarize.read_bytes())), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    else:
        run(args.output, args.targets, args.samples)

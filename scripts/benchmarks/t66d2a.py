"""Opt-in D2a algorithm benchmark. Fresh synthetic DBs only, no input DB path.

Not imported by startup/deployment. Large outputs and DBs stay in TemporaryDirectory.
Summary includes raw samples; never includes source row values or credentials.
"""

import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import platform
import resource
import sqlite3
import sys
import tempfile
import time
import tracemalloc
from unittest.mock import patch

from t66a import PARAMETERS, backend_imports, measure, seed


def run(output, targets, samples, verify_only=False, updates_only=False):
    with tempfile.TemporaryDirectory(prefix="money-note-d2a-") as tmp, patch.dict(os.environ):
        case_type, clock = backend_imports(Path(tmp))
        from app.db import session
        from app.services.snapshot import _validate_financial_relationships, export_snapshot_from_connection
        from isolated_sync.canonical import Context, Namespace, encode
        from isolated_sync.facts import build_facts, read_state, row_facts, validate_state
        from isolated_sync.patricia import Index
        from isolated_sync.raw import PRIMARY, TABLES, Row
        from isolated_sync.rebuild import rebuild
        from isolated_sync.segments import Tree
        from tests.isolated_sync_reference import audit_tree, facts_from_raw, patricia_root

        context = Context(Namespace("11111111-1111-4111-8111-111111111111",
                                    "22222222-2222-4222-8222-222222222222",
                                    "33333333-3333-4333-8333-333333333333"), "a"*64)
        report = dict(starting_commit="5277f7931bc3a4386832a3136d04bf373cd66709",
                      synthetic_descriptor=True, parameters=PARAMETERS,
                      environment=dict(python=sys.version, sqlite=sqlite3.sqlite_version,
                                       os=platform.platform(), cpu=platform.processor(),
                                       cpu_count=os.cpu_count()), datasets={})
        for target in targets:
            heavy = target == "confirmed-heavy"
            count = 1200 if heavy else int(target)
            with ExitStack() as stack:
                case = case_type()
                case.setUp()
                stack.callback(case.tearDown)
                seed(case, count, heavy=heavy)
                with session() as conn, patch("app.services.snapshot.datetime", clock):
                    before = tuple(conn.iterdump())
                    revision = conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
                    data = read_state(conn)
                    _validate_financial_relationships(conn)
                    assert not conn.execute("PRAGMA foreign_key_check").fetchall()
                    from datetime import date
                    _, snapshot = export_snapshot_from_connection(conn, date(2026, 10, 5))
                    full = rebuild(context, data)
                    for table in TABLES:
                        expected = sorted(snapshot["data"][table], key=lambda r: r[PRIMARY[table]])
                        assert [r["value"] for r in audit_tree(full.trees[table])] == expected == data[table]
                        full.trees[table].validate()
                    facts = list(full.index.facts())
                    assert {f.key: f.value for f in facts} == facts_from_raw(context, data)
                    assert full.index.object().ref() == patricia_root(context, facts)
                    assert full.index.validate() == len(facts)
                    assert tuple(conn.iterdump()) == before
                    assert conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0] == revision
                rows = {table: [Row.make(table, r) for r in data[table]] for table in TABLES}
                raw_bytes = sum(len(r.raw) for values in rows.values() for r in values)
                entry = dict(ledger_rows=len(data["ledger_entries"]),
                             archived_rows=sum(r["book_section"] == "archive" for r in data["ledger_entries"]),
                             confirmed_rows=sum(r["source_planned_entry_id"] is not None for r in data["ledger_entries"]),
                             rows={t: len(data[t]) for t in TABLES}, canonical_row_bytes=raw_bytes,
                             facts=len(facts), differential="PASS", stages={})
                if updates_only:
                    old_row = rows["ledger_entries"][0]
                    changed = Row.make("ledger_entries", {**old_row.value(), "title": "Synthetic changed title 😀"})
                    old_facts = {f.key: f for f in row_facts(context, old_row)}
                    new_facts = {f.key: f for f in row_facts(context, changed)}

                    def update_index():
                        updated = full.index
                        for key, fact in old_facts.items():
                            if fact != new_facts.get(key):
                                updated = updated.delete(json.loads(key))
                        for key, fact in new_facts.items():
                            if fact != old_facts.get(key):
                                updated = updated.put(fact)
                        return updated

                    updated_tree, entry["stages"]["tree_update"] = measure(
                        lambda: full.trees["ledger_entries"].put(changed, replace=True), 3, samples)
                    updated_index, entry["stages"]["facts_paths"] = measure(update_index, 3, samples)
                    target_data = {**data, "ledger_entries": [changed.value(), *data["ledger_entries"][1:]]}
                    assert updated_index.object() == Index.build(context, build_facts(context, target_data)).object()
                    assert [r["value"] for r in audit_tree(updated_tree)] == target_data["ledger_entries"]
                    old_hashes = {o.hash for o in full.trees["ledger_entries"].objects()} | {o.hash for o in full.index.objects()}
                    changed_objects = [o for o in [*updated_tree.objects(), *updated_index.objects()] if o.hash not in old_hashes]
                    entry.update(changed_objects=len(changed_objects), changed_object_bytes=sum(len(o.raw) for o in changed_objects))
                elif not verify_only:
                    # Large CPU costs justify 5 samples; retain every observation.
                    n = samples if count < 5000 else min(samples, 5)
                    stages = {
                        "c1_encode": lambda: [encode(r) for t in TABLES for r in data[t]],
                        "row_admission": lambda: [Row.make(t, r) for t in TABLES for r in data[t]],
                        "row_hash": lambda: [r.hash(context) for t in TABLES for r in rows[t]],
                        "tree_build": lambda: {t: Tree.build(context, t, rows[t]) for t in TABLES},
                        "facts_catalog": lambda: build_facts(context, data),
                        "patricia_build": lambda: Index.build(context, facts),
                        "structural_validate": lambda: validate_state(data),
                    }
                    for name, action in stages.items():
                        _, entry["stages"][name] = measure(action, 3, n)
                    tracemalloc.start()
                    started = time.perf_counter()
                    measured = rebuild(context, data)
                    _, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    objects = [obj for tree in measured.trees.values() for obj in tree.objects()] + list(measured.index.objects()) + [measured.raw]
                    entry.update(peak_python_bytes=peak, memory_probe_ms=(time.perf_counter()-started)*1000,
                                 objects=len(objects), object_bytes=sum(len(obj.raw) for obj in objects),
                                 process_maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
                report["datasets"][str(target)] = entry
        if output:
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--targets", nargs="+", default=["376", "1000", "5000", "10000", "confirmed-heavy"])
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--updates-only", action="store_true")
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        parser.error("raw benchmark output must be outside checkout")
    if not 1 <= args.samples <= 100 or set(args.targets) - {"376", "1000", "5000", "10000", "confirmed-heavy"}:
        parser.error("bounded supported targets/samples required")
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (1800, 1800))
    if args.verify_only and args.updates_only:
        parser.error("choose verification or update measurement")
    run(args.output, args.targets, args.samples, args.verify_only, args.updates_only)

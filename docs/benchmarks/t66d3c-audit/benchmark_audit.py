"""독립 합성 storage·10k GC·HTTP access-plan 측정. Production 경로를 받지 않는다."""

import json
from pathlib import Path
import sqlite3
import statistics
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_audit as a


def physical(db):
    with sqlite3.connect(db.path) as c:
        return dict(
            main_file_bytes=db.path.stat().st_size,
            wal_bytes=Path(str(db.path) + "-wal").stat().st_size
            if Path(str(db.path) + "-wal").exists()
            else 0,
            page_count=c.execute("PRAGMA page_count").fetchone()[0],
            freelist_count=c.execute("PRAGMA freelist_count").fetchone()[0],
            page_size=c.execute("PRAGMA page_size").fetchone()[0],
        )


def profile(size):
    with a.RetentionSandbox() as db:
        with db.connect() as c:
            a.seed(c, history=size - 1)
        db.install()
        db.bootstrap()
        repo = a.repository(db)
        a.create(repo)
        for n in (1, 2, 3):
            a.mutate(db, n)
        current = a.create(repo)
        expected = a.oracle(db)
        financial = a.financial(db)
        certificates = a.certificates(db)
        before = physical(db)
        start = time.monotonic()
        result = a.Collector(repo).collect(apply=True, batch=1024, max_batches=64)
        total = time.monotonic() - start
        after = physical(db)
        assert set(a.load(db)) == expected["reachable"]
        deleted_bytes = sum(
            len(expected["stored"][h][1]) for h in expected["candidates"]
        ) + sum(len(expected["cache"][h]) for h in expected["row_candidates"])
        assert result["logical_bytes_reclaimed"] == deleted_bytes
        assert result["objects_deleted"] == len(expected["candidates"]) and result[
            "rows_deleted"
        ] == len(expected["row_candidates"])
        assert a.financial(db) == financial and a.certificates(db) == certificates
        a.check_current(db)
        second = a.Collector(repo).collect(apply=True, batch=1024)
        assert second["objects_deleted"] == second["rows_deleted"] == 0
        app = a.http.create_app(repo)
        graph = a.load(db)
        raw = current["target"]["raw_ref"]["hash"]
        root = graph[raw][2]
        descriptor = next(
            x["root"] for x in root["tables"] if x["name"] == "ledger_entries"
        )
        path = [raw, descriptor["ref"]["hash"]]
        while graph[path[-1]][2]["kind"] == "snapshot-node":
            path.append(graph[path[-1]][2]["children"][0]["ref"]["hash"])
        cells = []
        for name, body, endpoint in [
            (
                "manifest_retry",
                dict(
                    protocol=1,
                    request_id=current["request_id"],
                    base=None,
                    inline_bytes=0,
                ),
                a.URL,
            ),
            (
                "raw_root",
                a.request_body([[raw]]),
                a.URL + "/" + current["observation_id"] + "/objects",
            ),
            (
                "leaf",
                a.request_body([path]),
                a.URL + "/" + current["observation_id"] + "/objects",
            ),
        ]:
            timings = []
            counts = []
            plans = {}
            for trial in range(7):
                queries = []
                real = a.RetentionConnection.execute

                def traced(conn, sql, params=()):
                    queries.append((sql, params))
                    return real(conn, sql, params)

                started = time.monotonic()
                with patch.object(a.RetentionConnection, "execute", traced):
                    events = a.asyncio.run(a.asgi(app, endpoint, body))
                elapsed = (time.monotonic() - started) * 1000
                assert a.status(events) == 200
                if trial >= 2:
                    timings.append(elapsed)
                    counts.append(len(queries))
                with db.connect() as conn:
                    for sql, params in queries:
                        if (
                            sql.lstrip().upper().startswith("SELECT")
                            and sql not in plans
                        ):
                            plans[sql] = [
                                r[3]
                                for r in conn.execute(
                                    "EXPLAIN QUERY PLAN " + sql, params
                                )
                            ]
                scans = {
                    sql: rows
                    for sql, rows in plans.items()
                    if any(
                        "SCAN sync_objects" in p
                        or "SCAN sync_commits" in p
                        or "SCAN ledger_entries" in p
                        for p in rows
                    )
                }
                if scans:
                    Path("/tmp/mn-d3c-audit/hot-scan-plans.json").write_text(
                        json.dumps(scans, ensure_ascii=False, indent=2)
                    )
                    assert all("LIMIT 0" in sql.upper() for sql in scans)
            cells.append(
                dict(
                    workload=name,
                    samples=5,
                    median_ms=statistics.median(timings),
                    sql_statement_counts=sorted(set(counts)),
                    query_plans=plans,
                )
            )
        return dict(
            ledger_rows=size,
            stored_objects_before=len(expected["stored"]),
            reachable_objects=len(expected["reachable"]),
            expected_unreachable=len(expected["candidates"]),
            actual=result,
            total_gc_seconds=total,
            max_deletion_write_lock_ms=max(
                (x["lock_ms"] for x in result["batches"]), default=0
            ),
            independently_counted_logical_bytes=deleted_bytes,
            physical_before=before,
            physical_after=after,
            physical_main_delta=after["main_file_bytes"] - before["main_file_bytes"],
            second_gc=second,
            current_reconstruction="PASS",
            historical_evidence="PRESERVED",
            eleven_tables=11,
            hot_cells=cells,
        )


if __name__ == "__main__":
    results = []
    for size in (376, 10000):
        results.append(profile(size))
        Path("/tmp/mn-d3c-audit/performance.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2)
        )
        print(
            json.dumps(
                {
                    k: v
                    for k, v in results[-1].items()
                    if k
                    in (
                        "ledger_rows",
                        "total_gc_seconds",
                        "max_deletion_write_lock_ms",
                        "independently_counted_logical_bytes",
                        "physical_main_delta",
                    )
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

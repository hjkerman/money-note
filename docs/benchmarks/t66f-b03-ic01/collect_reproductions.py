"""동일 실제 SQLite/parse/lease 실험의 before/after aggregate. 역사 출력 불변."""

import asyncio
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sql_cases(cost):
    result = {}
    for name, statements in {
        "IA01": [
            "BEGIN",
            "SAVEPOINT s",
            "INSERT INTO t VALUES ('a',x'01')",
            "SAVEPOINT s",
            "INSERT INTO t VALUES ('b',x'0203')",
            "ROLLBACK TO s",
            "RELEASE s",
            "COMMIT",
        ],
        "IA02": [
            "BEGIN",
            "INSERT INTO t VALUES ('prior',x'01')",
            "INSERT OR FAIL INTO t VALUES ('a',x'0203'),('prior',x'040506')",
            "COMMIT",
        ],
        "IA03": ["/* independent audit */ INSERT INTO t VALUES ('a',x'0102')"],
    }.items():
        c = cost.Collector()
        d = sqlite3.connect(
            ":memory:", isolation_level=None, factory=cost.observed_factory()
        )
        d.execute("CREATE TABLE t(k TEXT PRIMARY KEY,b BLOB)")
        errors = []
        try:
            with c.stage("calibration"):
                for statement in statements:
                    try:
                        d.execute(statement)
                    except sqlite3.IntegrityError as error:
                        errors.append(error.sqlite_errorcode)
            # Native SQLite, not the wrapper's counter, supplies the oracle.
            rows = sqlite3.Connection.execute(
                d, "SELECT k,length(b) FROM t ORDER BY k"
            ).fetchall()
            result[name] = {
                "native_rows": rows,
                "expected_committed_blob_bytes": sum(row[1] for row in rows),
                "actual_committed_blob_bytes": c.values[
                    "calibration/t/INSERT/committed/blob_bytes"
                ],
                "errors": errors,
                "counters": c.snapshot(),
            }
        finally:
            d.close()
    c = cost.Collector()
    from isolated_sync import canonical

    with cost.instrument(), c.stage("calibration"):
        canonical.decode_c1(b"{}")
        with cost.instrument():
            canonical.decode_c1(b"{}")
        canonical.decode_c1(b"{}")
    result["IA04"] = {
        "expected_calls": 3,
        "expected_submitted_bytes": 6,
        "actual_calls": c.values["calibration/json/calls"],
        "actual_submitted_bytes": c.values["calibration/json/submitted_bytes"],
    }
    return result


async def rejected(cost):
    from isolated_sync.workers import WorkerBudget

    c = cost.Collector()
    done = []
    budget = WorkerBudget(1)
    lease = budget.acquire()
    lease.close()
    with cost.instrument_workers(), c.stage("transfer"):
        try:
            await lease.run(lambda: None)
        except RuntimeError as error:
            assert str(error) == "closed worker lease"
    c.finish_when_idle(lambda c: done.append(c.snapshot()))
    return {
        "pending": c.pending,
        "completion_count": len(done),
        "closed": c.closed,
        "native_budget": budget.snapshot(),
    }


def owners(cost):
    c = None
    d = sqlite3.connect(
        ":memory:", isolation_level=None, factory=cost.observed_factory()
    )
    try:
        d.execute("CREATE TABLE t(k TEXT,b BLOB)")
        d.execute("BEGIN")
        rejected_at = None
        for n in range(1000):
            c = cost.Collector()
            try:
                with c.stage("calibration"):
                    d.execute("INSERT INTO t VALUES (?,?)", (str(n), b"x"))
            except RuntimeError as error:
                rejected_at = {"index": n, "error": str(error)}
                break
            c.close()
        before = len(d._cost_pending)
        rows = sqlite3.Connection.execute(d, "SELECT count(*) FROM t").fetchone()[0]
        d.execute("ROLLBACK")
        return {
            "attempted_scopes": 1000,
            "native_rows_before_rollback": rows,
            "pending_keys_before": before,
            "rejected": rejected_at,
            "pending_keys_after": len(d._cost_pending),
            "owners_after": len(getattr(d, "_cost_owners", [])),
        }
    finally:
        d.close()


def main():
    result = {}
    for label, path in [
        ("historical", HERE / "historical/counters.py"),
        ("current", HERE.parent / "t66f-b03/counters.py"),
    ]:
        cost = load(path, "ic01_" + label)
        result[label] = sql_cases(cost)
        result[label]["IA05"] = asyncio.run(rejected(cost))
        result[label]["IA06"] = owners(cost)
    result["IA07"] = json.loads(
        (HERE / "evidence/current-server-oracle.json").read_text()
    )
    (HERE / "evidence/reproductions.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        "same SQLite/parse/closed-lease experiment: historical defects and current corrections captured"
    )


if __name__ == "__main__":
    main()

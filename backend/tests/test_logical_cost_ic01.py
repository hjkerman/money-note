"""IC01 현재 구현 oracle. 원 감사의 결함-existence assertion과 분리한다."""

import asyncio
from contextlib import closing
import hashlib
import importlib.util
from pathlib import Path
import sqlite3
from unittest.mock import patch

import pytest
from isolated_sync import canonical

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "ic01_cost", ROOT / "docs/benchmarks/t66f-b03/counters.py"
)
cost = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cost)


def database():
    d = sqlite3.connect(":memory:", isolation_level=None, factory=cost.observed_factory())
    d.execute("CREATE TABLE t(k TEXT PRIMARY KEY,b BLOB)")
    return d


def test_readonly_cte_never_installs_write_observers():
    with closing(database()) as d:
        d.execute("PRAGMA query_only=ON")
        assert d.execute("WITH x AS (SELECT 1) SELECT * FROM x").fetchall() == [(1,)]
        assert not d._cost_tables


def blob(c, outcome):
    return c.values["calibration/t/INSERT/" + outcome + "/blob_bytes"]


@pytest.mark.parametrize("name", ["s", '"S p"', "'s''p'", "`s`", "[s]"])
def test_nearest_same_name_savepoint_native_oracle(name):
    c = cost.Collector()
    with closing(database()) as d, c.stage("calibration"):
        for sql in [
            "BEGIN",
            "SAVEPOINT " + name,
            "INSERT INTO t VALUES ('a',x'01')",
            "SAVEPOINT " + name,
            "INSERT INTO t VALUES ('b',x'0203')",
            "ROLLBACK TRANSACTION TO SAVEPOINT " + name,
            "RELEASE SAVEPOINT " + name,
            "COMMIT",
        ]:
            d.execute(sql)
        assert d.execute("SELECT k,length(b) FROM t").fetchall() == [("a", 1)]
        assert (blob(c, "committed"), blob(c, "rolled_back")) == (1, 2)
        assert not d._cost_pending and not d._cost_savepoints and not d._cost_owners


@pytest.mark.parametrize(
    "mode,committed,rollback", [("FAIL", 3, 0), ("ABORT", 1, 2), ("ROLLBACK", 0, 3)]
)
@pytest.mark.parametrize("explicit", [False, True])
def test_partial_statement_real_sqlite_conflict(mode, committed, rollback, explicit):
    c = cost.Collector()
    with closing(database()) as d, c.stage("calibration"):
        if explicit:
            d.execute("BEGIN")
        d.execute("INSERT INTO t VALUES ('prior',x'01')")
        with pytest.raises(sqlite3.IntegrityError):
            d.execute(f"INSERT OR {mode} INTO t VALUES ('a',x'0203'),('prior',x'040506')")
        if d.in_transaction:
            d.execute("COMMIT")
        expected = committed if explicit else (3 if mode == "FAIL" else 1)
        assert sum(r[0] for r in d.execute("SELECT length(b) FROM t")) == expected
        assert blob(c, "committed") == expected
        assert blob(c, "attempted") == 6
        if explicit:
            assert blob(c, "rolled_back") + blob(c, "statement_rolled_back") == rollback


@pytest.mark.parametrize(
    "prefix", ["-- INSERT ignored\n", " /* UPDATE */ ", "\n-- DELETE\n/* REPLACE */ --x\n"]
)
def test_first_comment_dml_is_observed(prefix):
    c = cost.Collector()
    with closing(database()) as d, c.stage("calibration"):
        d.execute(prefix + "INSERT INTO t VALUES ('a',x'0102')")
        assert d.execute("SELECT sum(length(b)) FROM t").fetchone()[0] == 2
    assert blob(c, "committed") == 2


@pytest.mark.parametrize("rollback", ["ROLLBACK", "ROLLBACK TRANSACTION"])
def test_fail_prefix_can_still_be_rolled_back(rollback):
    c = cost.Collector()
    with closing(database()) as d, c.stage("calibration"):
        d.execute("BEGIN")
        d.execute("INSERT INTO t VALUES ('prior',x'01')")
        with pytest.raises(sqlite3.IntegrityError):
            d.execute("INSERT OR FAIL INTO t VALUES ('a',x'0203'),('prior',x'040506')")
        d.execute(rollback)
        assert d.execute("SELECT count(*) FROM t").fetchone()[0] == 0
        assert blob(c, "committed") == 0 and blob(c, "rolled_back") == 3
        # TEMP observers created inside the rolled-back transaction must reinstall.
        d.execute("INSERT INTO t VALUES ('next',x'04050607')")
        assert blob(c, "committed") == 4


def test_nested_install_counts_once_and_restores_original():
    original = canonical._parse_json
    c = cost.Collector()
    with cost.instrument(), c.stage("calibration"):
        canonical.decode_c1(b"{}")
        with cost.instrument():
            canonical.decode_c1(b"{}")
        canonical.decode_c1(b"{}")
    assert (c.values["calibration/json/calls"], c.values["calibration/json/submitted_bytes"]) == (
        3,
        6,
    )
    assert canonical._parse_json is original and hashlib.sha256 is cost.NATIVE_HASH
    assert not cost.INSTALLATIONS


def test_partial_install_failure_restores_prior_observers():
    original = canonical._parse_json
    enter = cost.patch.object

    def broken(target, name, value):
        if name == "encode":
            raise RuntimeError("synthetic install failure")
        return enter(target, name, value)

    with patch.object(cost.patch, "object", broken):
        with pytest.raises(RuntimeError, match="install failure"), cost.instrument():
            pass
    assert canonical._parse_json is original and not cost.INSTALLATIONS


@pytest.mark.parametrize("failure", ["closed", "scheduling"])
def test_rejected_dispatch_exact_once_release(failure):
    from isolated_sync.workers import WorkerBudget

    async def run():
        c, done = cost.Collector(), []
        budget = WorkerBudget(1)
        lease = budget.acquire()
        if failure == "closed":
            lease.close()
        with cost.instrument_workers(), c.stage("transfer"):
            if failure == "scheduling":
                with patch(
                    "isolated_sync.workers.asyncio.create_task",
                    side_effect=RuntimeError("dispatch"),
                ):
                    with pytest.raises(RuntimeError):
                        await lease.run(lambda: None)
                lease.close()
            else:
                with pytest.raises(RuntimeError, match="closed worker lease"):
                    await lease.run(lambda: None)
        c.finish_when_idle(lambda value: done.append(value.snapshot()))
        assert c.pending == 0 and c.closed and len(done) == 1
        assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)

    asyncio.run(run())


def test_owner_capacity_rejects_before_sql_and_cleans_transaction():
    with closing(database()) as d:
        d.execute("BEGIN")
        for n in range(cost.TRANSACTION_OWNER_LIMIT):
            c = cost.Collector()
            with c.stage("calibration"):
                d.execute("INSERT INTO t VALUES (?,?)", (str(n), b"x"))
            c.close()
        overflow = cost.Collector()
        with (
            overflow.stage("calibration"),
            pytest.raises(RuntimeError, match="measurement incomplete"),
        ):
            d.execute("INSERT INTO t VALUES ('overflow',x'01')")
        assert len(d._cost_owners) == 32
        assert d.execute("SELECT count(*) FROM t").fetchone()[0] == 32
        d.execute("ROLLBACK")
        assert not d._cost_pending and not d._cost_savepoints and not d._cost_owners
        with overflow.stage("calibration"):
            d.execute("INSERT INTO t VALUES ('after',x'0102')")
        assert blob(overflow, "committed") == 2


def test_schema_fail_is_explicit_unsupported_before_operation():
    with closing(database()) as d:
        d.execute("CREATE TABLE unsupported(k TEXT UNIQUE ON CONFLICT FAIL)")
        with pytest.raises(RuntimeError, match="unsupported schema conflict"):
            d.execute("INSERT INTO t VALUES ('no',x'01')")
        assert d.execute("SELECT count(*) FROM t").fetchone()[0] == 0


@pytest.mark.parametrize("explicit", [False, True])
def test_executemany_iterator_failure_keeps_completed_prefix(explicit):
    c = cost.Collector()

    def rows():
        yield ("a", b"1")
        yield ("b", b"22")
        raise ValueError("input iterator, not SQLite rollback")

    with closing(database()) as d, c.stage("calibration"):
        if explicit:
            d.execute("BEGIN")
        with pytest.raises(ValueError, match="iterator"):
            d.executemany("INSERT INTO t VALUES (?,?)", rows())
        if d.in_transaction:
            d.execute("COMMIT")
        assert d.execute("SELECT sum(length(b)) FROM t").fetchone()[0] == 3
        assert blob(c, "committed") == 3
        assert blob(c, "statement_rolled_back") == 0


def test_failed_commit_does_not_discard_pending_or_report_durable():
    c = cost.Collector()
    with closing(database()) as d, c.stage("calibration"):
        d.execute("PRAGMA foreign_keys=ON")
        d.execute("CREATE TABLE parent(k TEXT PRIMARY KEY)")
        d.execute(
            "CREATE TABLE child(k TEXT REFERENCES parent(k) DEFERRABLE INITIALLY DEFERRED,b BLOB)"
        )
        d.execute("BEGIN")
        d.execute("INSERT INTO child VALUES ('missing',x'0102')")
        with pytest.raises(sqlite3.IntegrityError):
            d.commit()
        assert d.in_transaction and d._cost_pending
        assert c.values["calibration/child/INSERT/committed/blob_bytes"] == 0
        d.rollback()
        assert c.values["calibration/child/INSERT/rolled_back/blob_bytes"] == 2
        assert not d._cost_owners

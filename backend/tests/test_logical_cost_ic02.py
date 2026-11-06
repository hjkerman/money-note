"""N01/N02 diagnostic-only regressions with independent SQLite/span oracles."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import sys
from threading import Condition, Event, Lock

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from isolated_sync import canonical  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "b03_ic02_cost", ROOT / "docs/benchmarks/t66f-b03/counters.py"
)
cost = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cost)


def database():
    connection = sqlite3.connect(":memory:", isolation_level=None, factory=cost.observed_factory())
    connection.execute("CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)")
    return connection


def metric(collector, operation, outcome):
    key = f"generation/payload/{operation}/{outcome}/blob_bytes"
    return collector.values.get(key, 0)


@pytest.mark.parametrize(
    "ddl_statements,insert,expected,oracle",
    [
        (
            ["ALTER TABLE payload ADD COLUMN extra BLOB"],
            "INSERT INTO payload VALUES('next',x'0203',x'040506')",
            6,
            "SELECT sum(length(b))+sum(COALESCE(length(extra),0)) FROM payload",
        ),
        (
            [
                "DROP TABLE payload",
                "CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)",
            ],
            "INSERT INTO payload VALUES('next',x'020304')",
            4,
            "SELECT 1+sum(length(b)) FROM payload",
        ),
    ],
)
def test_n01_original_payload_bytes_survive_schema_refresh(
    ddl_statements, insert, expected, oracle
):
    collector = cost.Collector()
    with closing(database()) as db, collector.stage("generation"):
        db.execute("INSERT INTO payload VALUES('initial',x'01')")
        for statement in ddl_statements:
            db.execute(statement)
        db.execute(insert)
        native_payload_bytes = db.execute(oracle).fetchone()[0]
        assert native_payload_bytes == expected
    assert all(
        metric(collector, "INSERT", outcome) == expected
        for outcome in ("attempted", "effective", "committed")
    )


def test_n01_schema_refresh_covers_create_update_delete_and_upsert():
    collector = cost.Collector()
    with closing(database()) as db, collector.stage("generation"):
        db.execute("INSERT INTO payload VALUES('initial',x'01')")
        db.execute("ALTER TABLE payload ADD COLUMN extra BLOB")
        db.execute("UPDATE payload SET b=x'0203', extra=x'04' WHERE k='initial'")
        db.execute(
            "INSERT INTO payload VALUES('next',x'05',x'0607') "
            "ON CONFLICT(k) DO UPDATE SET b=excluded.b,extra=excluded.extra"
        )
        db.execute("DELETE FROM payload WHERE k='next'")
        assert db.execute("SELECT b,extra FROM payload").fetchall() == [(b"\x02\x03", b"\x04")]
    assert metric(collector, "UPDATE", "attempted") == 3
    assert metric(collector, "UPDATE", "effective") == 3
    assert metric(collector, "UPDATE", "committed") == 3
    assert metric(collector, "INSERT", "attempted") == 4
    assert metric(collector, "INSERT", "effective") == 4
    assert metric(collector, "INSERT", "committed") == 4
    assert metric(collector, "DELETE", "committed") == 0


def test_n01_transactional_ddl_rollback_keeps_trigger_metadata_current():
    collector = cost.Collector()
    with closing(database()) as db, collector.stage("generation"):
        db.execute("BEGIN")
        db.execute("INSERT INTO payload VALUES('initial',x'01')")
        db.execute("SAVEPOINT schema_change")
        db.execute("ALTER TABLE payload ADD COLUMN extra BLOB")
        db.execute("INSERT INTO payload VALUES('rolled',x'0203',x'04')")
        db.execute("ROLLBACK TO schema_change")
        db.execute("RELEASE schema_change")
        db.execute("COMMIT")
        db.execute("INSERT INTO payload VALUES('next',x'0607')")
        assert db.execute("SELECT sum(length(b)) FROM payload").fetchone()[0] == 3
    assert metric(collector, "INSERT", "attempted") == 6
    assert metric(collector, "INSERT", "effective") == 6
    assert metric(collector, "INSERT", "committed") == 3
    assert metric(collector, "INSERT", "rolled_back") == 3


@pytest.mark.parametrize("replace", [False, True])
def test_n01_external_schema_is_explicitly_incomplete_before_dml(tmp_path, replace):
    for refresh_read in (False, True):
        collector = cost.Collector()
        path = tmp_path / f"schema-{refresh_read}.sqlite"
        with (
            closing(
                sqlite3.connect(path, isolation_level=None, factory=cost.observed_factory())
            ) as db,
            closing(sqlite3.connect(path, isolation_level=None)) as other,
            collector.stage("generation"),
        ):
            db.execute("CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)")
            db.execute("INSERT INTO payload VALUES('initial',x'01')")
            if replace:
                other.execute("DROP TABLE payload")
                other.execute("CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)")
                statement = "INSERT INTO payload VALUES('next',x'020304')"
            else:
                other.execute("ALTER TABLE payload ADD COLUMN extra BLOB")
                statement = "INSERT INTO payload VALUES('next',x'0203',x'040506')"
            if refresh_read:
                db.execute("SELECT * FROM payload").fetchall()
            # The observer cannot safely reprepare somebody else's schema:
            # doing so may turn a native stale-schema error into success.
            with pytest.raises(
                RuntimeError, match="external schema change; measurement incomplete"
            ):
                db.execute(statement)
            assert db.execute("SELECT count(*) FROM payload WHERE k='next'").fetchone()[0] == 0
        for outcome in ("attempted", "effective", "committed"):
            assert metric(collector, "INSERT", outcome) == 1
        assert collector.values["generation/coverage/external_schema_change"] == 1


def test_n01_failed_ddl_and_new_table_do_not_leave_stale_registry():
    collector = cost.Collector()
    with closing(database()) as db, collector.stage("generation"):
        db.execute("INSERT INTO payload VALUES('initial',x'01')")
        with pytest.raises(sqlite3.OperationalError):
            db.execute("ALTER TABLE missing ADD COLUMN extra BLOB")
        db.execute("CREATE TABLE fresh(b BLOB)")
        db.execute("INSERT INTO fresh VALUES(x'0203')")
        db.execute("INSERT INTO payload VALUES('next',x'040506')")
        assert db.execute("SELECT sum(length(b)) FROM payload").fetchone()[0] == 4
        assert db.execute("SELECT sum(length(b)) FROM fresh").fetchone()[0] == 2
    for outcome in ("attempted", "effective", "committed"):
        assert metric(collector, "INSERT", outcome) == 4
        assert collector.values[f"generation/fresh/INSERT/{outcome}/blob_bytes"] == 2


@pytest.mark.parametrize("scope_count", [2, 4])
def test_n02_concurrent_first_install_waits_for_all_wrappers(scope_count, monkeypatch):
    first_patch_entered, release_first_patch = Event(), Event()
    all_waiters_blocked = Event()
    wait_condition = Condition(Lock())
    waiting = 0
    original_install_patch = cost.install_patch
    original_wait = cost.wait_for_installation

    def controlled_patch(stack, target, name, value):
        if name == "_parse_json" and not first_patch_entered.is_set():
            first_patch_entered.set()
            assert release_first_patch.wait(10)
        return original_install_patch(stack, target, name, value)

    def observed_wait(state):
        nonlocal waiting
        with wait_condition:
            waiting += 1
            if waiting == scope_count - 1:
                all_waiters_blocked.set()
        return original_wait(state)

    monkeypatch.setattr(cost, "install_patch", controlled_patch)
    monkeypatch.setattr(cost, "wait_for_installation", observed_wait)
    inputs = [b"{}", b'{"n":1}', b'{"n":22}', b'{"n":333}'][:scope_count]

    def parse(index, raw):
        collector = cost.Collector()
        with cost.instrument(), collector.stage("generation"):
            canonical.decode_c1(raw)
        return index, collector.snapshot(), len(raw)

    with ThreadPoolExecutor(scope_count) as pool:
        futures = [pool.submit(parse, 0, inputs[0])]
        assert first_patch_entered.wait(10)
        futures.extend(pool.submit(parse, i, raw) for i, raw in enumerate(inputs[1:], 1))
        assert all_waiters_blocked.wait(10)
        release_first_patch.set()
        results = [future.result(timeout=15) for future in futures]

    assert len(results) == scope_count
    for _, snapshot, expected_bytes in results:
        assert snapshot["generation/json/calls"] == "1"
        assert snapshot["generation/json/submitted_bytes"] == str(expected_bytes)
        assert snapshot["generation/json/completed_bytes"] == str(expected_bytes)
    assert not cost.INSTALLATIONS


def test_n02_failed_first_install_rejects_waiter_without_lost_scope(monkeypatch):
    first_patch_entered, release_first_patch = Event(), Event()
    waiter_entered = Event()
    original_install_patch = cost.install_patch
    original_wait = cost.wait_for_installation
    original_parse = canonical._parse_json

    def fail_first_patch(stack, target, name, value):
        if name == "encode":
            first_patch_entered.set()
            assert release_first_patch.wait(10)
            raise RuntimeError("controlled installation failure")
        return original_install_patch(stack, target, name, value)

    def observed_wait(state):
        waiter_entered.set()
        return original_wait(state)

    monkeypatch.setattr(cost, "install_patch", fail_first_patch)
    monkeypatch.setattr(cost, "wait_for_installation", observed_wait)

    def parse(collector):
        with cost.instrument(), collector.stage("generation"):
            canonical.decode_c1(b"{}")

    first, second = cost.Collector(), cost.Collector()
    with ThreadPoolExecutor(2) as pool:
        first_future = pool.submit(parse, first)
        assert first_patch_entered.wait(10)
        second_future = pool.submit(parse, second)
        assert waiter_entered.wait(10)
        release_first_patch.set()
        with pytest.raises(RuntimeError, match="controlled installation failure"):
            first_future.result(timeout=15)
        with pytest.raises(RuntimeError, match="installation failed"):
            second_future.result(timeout=15)
    assert first.snapshot() == second.snapshot() == {}
    assert not cost.INSTALLATIONS
    assert canonical._parse_json is original_parse
    monkeypatch.setattr(cost, "install_patch", original_install_patch)
    recovered = cost.Collector()
    parse(recovered)
    assert recovered.values["generation/json/calls"] == 1
    assert recovered.values["generation/json/submitted_bytes"] == 2
    assert not cost.INSTALLATIONS

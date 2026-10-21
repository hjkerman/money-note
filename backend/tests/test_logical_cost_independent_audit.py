"""독립 B03 oracle와 결함 재현. 결함 재현의 PASS는 계측 정확성 PASS가 아니다."""

import asyncio
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
from threading import Event

import pytest

from isolated_sync import canonical

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/benchmarks/t66f-b03-independent/evidence"
SPEC = importlib.util.spec_from_file_location(
    "independent_b03_cost", ROOT / "docs/benchmarks/t66f-b03/counters.py"
)
cost = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cost)
SHA = hashlib.sha256


def evidence(name, value):
    OUT.mkdir(exist_ok=True)
    # 동일 테스트의 full regression 재실행은 별도 runner/JUnit에 남는다.
    (OUT / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def db():
    result = sqlite3.connect(":memory:", isolation_level=None, factory=cost.observed_factory())
    result.execute("CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)")
    return result


@pytest.mark.parametrize("raw", [b"", b"{}", '"한😀e\u0301"'.encode(), b"a" * 4097])
def test_independent_hash_repeated_and_streaming_oracle(raw):
    c = cost.Collector()
    prefix = b"money-note.sync.v1/hot\x00"
    expected = SHA(prefix + raw).digest()
    with cost.instrument(), c.stage("transfer"):
        assert bytes.fromhex(canonical.hash_bytes("hot", raw)) == expected
        h = hashlib.sha256(prefix)
        h.update(memoryview(raw)[:1])
        h.update(memoryview(raw)[1:])
        assert h.digest() == expected
    assert int(c.snapshot()["transfer/sha256/hash_input_bytes"]) == 2 * (len(prefix) + len(raw))
    assert int(c.snapshot()["transfer/sha256/calls"]) == 2
    assert hashlib.sha256 is SHA


@pytest.mark.parametrize(
    "raw,parsed,accepted",
    [
        (b"{}", True, True),
        (b"{ }", True, False),
        (b'{"x":', False, False),
        (b'"\\ud800"', True, False),
        (b"\xffunvisited", False, False),
        (b'{"x":1,"x":2}', False, False),
    ],
)
def test_independent_validation_primary_span(raw, parsed, accepted):
    c = cost.Collector()
    with cost.instrument(), c.stage("observation"):
        for _ in range(2):
            if accepted:
                canonical.decode_c1(raw)
            else:
                with pytest.raises(canonical.CanonicalError):
                    canonical.decode_c1(raw)
    values = c.values
    assert values["observation/json/submitted_bytes"] == 2 * len(raw)
    assert values["observation/json/completed_bytes"] == (2 * len(raw) if parsed else 0)
    assert values["observation/json/failed_submitted_bytes"] == (0 if parsed else 2 * len(raw))


def test_independent_unicode_update_ignore_unique_savepoints_commit():
    c = cost.Collector()
    with closing(db()) as d, c.stage("generation"):
        d.execute("BEGIN")
        d.execute("INSERT INTO payload VALUES (?,?)", ("한😀", b"12"))
        d.execute("INSERT OR IGNORE INTO payload VALUES (?,?)", ("한😀", b"ignored"))
        d.execute("SAVEPOINT outer_scope")
        d.execute("SAVEPOINT inner_scope")
        d.execute("UPDATE payload SET b=?", (b"123456",))
        d.execute("ROLLBACK TO inner_scope")
        d.execute("RELEASE inner_scope")
        d.execute("RELEASE outer_scope")
        d.execute("COMMIT")
        rows = d.execute("SELECT length(CAST(k AS BLOB)),length(b) FROM payload").fetchall()
        assert rows == [(7, 2)]
    assert c.values["generation/payload/INSERT/attempted/blob_bytes"] == 9
    assert c.values["generation/payload/INSERT/committed/blob_bytes"] == 2
    assert c.values["generation/payload/INSERT/committed/text_bytes"] == 7
    assert c.values["generation/payload/UPDATE/rolled_back/blob_bytes"] == 6


def test_reproduce_duplicate_nested_savepoint_committed_mismatch():
    c = cost.Collector()
    with closing(db()) as d, c.stage("calibration"):
        for sql in [
            "BEGIN",
            "SAVEPOINT s",
            "INSERT INTO payload VALUES ('a',x'01')",
            "SAVEPOINT s",
            "INSERT INTO payload VALUES ('b',x'0203')",
            "ROLLBACK TO s",
            "RELEASE s",
            "COMMIT",
        ]:
            d.execute(sql)
        oracle = d.execute("SELECT k,length(b) FROM payload ORDER BY k").fetchall()
        actual = c.values["calibration/payload/INSERT/committed/blob_bytes"]
        assert oracle == [("a", 1)]
        assert actual == 0  # 결함 재현: SQLite는 가장 가까운 동일 이름을 선택한다.
        assert actual != sum(row[1] for row in oracle)
        evidence(
            "finding-savepoint-backend",
            dict(
                oracle_rows=oracle,
                expected_committed=1,
                actual_committed=actual,
                expected_rollback=2,
                counters=c.snapshot(),
            ),
        )


def test_reproduce_fail_statement_preserved_rows_mislabeled_rollback():
    c = cost.Collector()
    with closing(db()) as d, c.stage("generation"):
        d.execute("BEGIN")
        d.execute("INSERT INTO payload VALUES ('prior',x'01')")
        with pytest.raises(sqlite3.IntegrityError):
            d.execute("INSERT OR FAIL INTO payload VALUES ('a',x'0203'),('prior',x'040506')")
        d.execute("COMMIT")
        oracle = d.execute("SELECT k,length(b) FROM payload ORDER BY k").fetchall()
        actual = c.values["generation/payload/INSERT/committed/blob_bytes"]
        assert oracle == [("a", 2), ("prior", 1)]
        assert actual == 1 and actual != sum(row[1] for row in oracle)
        evidence(
            "finding-fail-sql-backend",
            dict(
                oracle_rows=oracle,
                expected_committed=3,
                actual_committed=actual,
                counters=c.snapshot(),
            ),
        )


def test_reproduce_comment_prefixed_first_dml_silent_omission():
    c = cost.Collector()
    with closing(db()) as d, c.stage("generation"):
        d.execute("/* independent audit */ INSERT INTO payload VALUES ('a',x'0102')")
        expected = d.execute("SELECT sum(length(b)) FROM payload").fetchone()[0]
        assert expected == 2
        assert c.values["generation/payload/INSERT/committed/blob_bytes"] == 0
        evidence(
            "finding-comment-sql-backend",
            dict(expected_committed=expected, actual_committed=0, counters=c.snapshot()),
        )


def test_reproduce_nested_activation_double_validation():
    c = cost.Collector()
    with cost.instrument(), c.stage("transfer"):
        canonical.decode_c1(b"{}")
        with cost.instrument():
            canonical.decode_c1(b"{}")
        canonical.decode_c1(b"{}")
    assert c.values["transfer/json/submitted_bytes"] == 8
    evidence(
        "finding-nested-install",
        dict(
            expected_calls=3,
            expected_bytes=6,
            actual_calls=c.values["transfer/json/calls"],
            counters=c.snapshot(),
        ),
    )
    assert canonical.hashlib.sha256 is SHA


def test_independent_started_native_worker_cancellation_and_exception_tail():
    from isolated_sync.workers import WorkerBudget

    entered, release, measured = Event(), Event(), Event()
    first, second = cost.Collector(), cost.Collector()
    completed = []

    def worker():
        canonical.hash_bytes("hot", b"123")
        entered.set()
        assert release.wait(10)
        canonical.hash_bytes("hot", b"1234567")
        raise ValueError("independent late native exception")

    def finished(c):
        completed.append(c.snapshot())
        measured.set()

    async def run():
        budget = WorkerBudget(1)
        lease = budget.acquire()
        with first.stage("transfer"):
            task = asyncio.create_task(lease.run(worker))
            assert await asyncio.to_thread(entered.wait, 10)
            task.cancel()
            result = await asyncio.gather(task, return_exceptions=True)
            assert isinstance(result[0], asyncio.CancelledError)
        lease.close()
        first.finish_when_idle(finished)
        assert first.pending == 1 and not measured.is_set()
        with second.stage("observation"):
            canonical.hash_bytes("hot", b"other-run")
            release.set()
            assert await asyncio.to_thread(measured.wait, 10)
            await asyncio.sleep(0.05)
        assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)

    with cost.instrument(), cost.instrument_workers():
        asyncio.run(run())
    assert len(completed) == 1
    assert first.closed and first.pending == 0
    assert first.values["transfer/sha256/hash_input_bytes"] == 2 * 23 + 10
    assert second.values["observation/sha256/hash_input_bytes"] == 23 + 9
    evidence(
        "native-late-independent",
        dict(
            first=first.snapshot(),
            second=second.snapshot(),
            closed=first.closed,
            pending=first.pending,
            completion_count=len(completed),
        ),
    )


def test_independent_capacity_reports_error_and_integer_does_not_wrap():
    c = cost.Collector()
    with closing(db()) as d, c.stage("calibration"):
        for i in range(128):
            d.execute(f"CREATE TABLE extra_{i}(a TEXT)")
        with pytest.raises(RuntimeError, match="table capacity"):
            d.execute("INSERT INTO payload VALUES ('a',x'01')")
        assert d.execute("SELECT count(*) FROM payload").fetchone()[0] == 0
    c.add("calibration/sha256/hash_input_bytes", 10**100)
    assert c.snapshot()["calibration/sha256/hash_input_bytes"] == str(10**100)


def test_independent_savepoint_capacity_is_explicit():
    with closing(db()) as d:
        d.execute("BEGIN")
        for i in range(32):
            d.execute(f"SAVEPOINT independent_{i}")
        with pytest.raises(RuntimeError, match="savepoint capacity"):
            d.execute("SAVEPOINT over_limit")
        d.execute("ROLLBACK")

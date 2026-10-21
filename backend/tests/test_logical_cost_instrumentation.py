"""B03: literal/stdlib/별도 SQLite oracle, synthetic source만 사용한다."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import ModuleType
from threading import Event

import pytest

from isolated_sync import canonical
from isolated_sync.store import Store

SPEC = importlib.util.spec_from_file_location(
    "b03_counters", Path(__file__).resolve().parents[2] / "docs/benchmarks/t66f-b03/counters.py"
)
cost = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cost)


def count(c, key):
    return c.values[key]


@pytest.mark.parametrize("raw", [b"", b"a", b"abc", "한😀e\u0301".encode()])
def test_hash_exact_preimage_and_duplicate_work(raw):
    expected = hashlib.sha256(b"money-note.sync.v1/hot\0" + raw).hexdigest()
    c = cost.Collector()
    with cost.instrument(), c.stage("generation"):
        assert canonical.hash_bytes("hot", raw) == expected
        assert canonical.hash_bytes("hot", raw) == expected
    assert count(c, "generation/sha256/hash_input_bytes") == 2 * (23 + len(raw))
    assert count(c, "generation/sha256/calls") == 2


def test_streamed_hash_copy_does_not_rehash_old_input():
    c = cost.Collector()
    with cost.instrument(), c.stage("calibration"):
        h = canonical.hashlib.sha256(b"ab")
        h.update(b"c")
        clone = h.copy()
        clone.update(b"d")
        assert clone.digest() == cost.NATIVE_HASH(b"abcd").digest()
    assert count(c, "calibration/sha256/hash_input_bytes") == 4
    assert count(c, "calibration/sha256/calls") == 1


def test_late_import_uses_actual_hash_and_canonical_primitives(monkeypatch):
    c = cost.Collector()
    with cost.instrument(), c.stage("calibration"):
        module = ModuleType("isolated_sync.b03_late_synthetic")
        monkeypatch.setitem(sys.modules, module.__name__, module)
        exec(
            "from hashlib import sha256\nfrom isolated_sync.canonical import encode, decode_c1\n"
            "def run():\n raw=encode({'한': '😀'})\n decode_c1(raw)\n return raw, sha256(raw).digest()",
            module.__dict__,
        )
        raw, digest = module.run()
        assert digest == cost.NATIVE_HASH(raw).digest()
    assert count(c, "calibration/sha256/hash_input_bytes") == len(raw)
    assert count(c, "calibration/json/completed_bytes") == len(raw)
    assert hashlib.sha256 is cost.NATIVE_HASH
    assert module.sha256 is cost.NATIVE_HASH
    assert module.encode is canonical.encode


def test_closed_scope_stream_updates_and_new_run_are_isolated():
    a, b = cost.Collector(), cost.Collector()
    with cost.instrument(), a.stage("transfer"):
        h = canonical.hashlib.sha256(b"a")
        a.close()
        before = a.snapshot()
        with b.stage("generation"):
            h.update(b"stale")
            canonical.hash_bytes("hot", b"new")
            with cost.authentication_hashes():
                canonical.hashlib.sha256(b"synthetic").digest()
        canonical.hash_bytes("hot", b"closed")
    assert a.snapshot() == before
    assert count(b, "generation/sha256/calls") == 1
    assert count(b, "generation/sha256/hash_input_bytes") == 26
    assert count(b, "generation/authentication_sha256/hash_input_bytes") == 9


def test_read_only_sql_has_no_temp_observer_installation():
    c = cost.Collector()
    with c.stage("transfer"), closing(connection()) as db:
        assert db.execute("SELECT count(*) FROM objects").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM sqlite_temp_master").fetchone()[0] == 0
        db.execute("INSERT INTO objects VALUES ('a', x'01')")
        assert db.execute("SELECT count(*) FROM sqlite_temp_master").fetchone()[0] == 6
    assert count(c, "transfer/objects/INSERT/committed/blob_bytes") == 1


def test_cancelled_request_counts_native_tail_until_exact_worker_exit():
    from isolated_sync.workers import WorkerBudget

    a, b = cost.Collector(), cost.Collector()
    entered, release, measured = Event(), Event(), Event()
    final = []

    def operation():
        canonical.hash_bytes("hot", b"a")
        entered.set()
        assert release.wait(10)
        canonical.hash_bytes("hot", b"bc")

    def complete(c):
        final.append(c.snapshot())
        measured.set()

    async def run():
        budget = WorkerBudget(1)
        lease = budget.acquire()
        with a.stage("transfer"):
            task = asyncio.create_task(lease.run(operation))
            assert await asyncio.to_thread(entered.wait, 10)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        lease.close()
        a.finish_when_idle(complete)
        assert not measured.is_set()
        with b.stage("generation"):
            canonical.hash_bytes("hot", b"other")
        release.set()
        assert await asyncio.to_thread(measured.wait, 10)
        assert budget.snapshot()["leases"] == 0

    with cost.instrument(), cost.instrument_workers():
        asyncio.run(run())
    assert len(final) == 1
    assert count(a, "transfer/sha256/calls") == 2
    assert count(a, "transfer/sha256/hash_input_bytes") == 49
    assert count(b, "generation/sha256/calls") == 1
    assert a.closed and a.pending == 0


@pytest.mark.parametrize(
    "raw,completed", [(b"{}", 2), (b"{ }", 3), (b"\xfftail", 0), (b'{"x":', 0)]
)
def test_validation_submitted_completed_and_failed(raw, completed):
    c = cost.Collector()
    with cost.instrument(), c.stage("transfer"):
        try:
            canonical.decode_c1(raw)
        except canonical.CanonicalError:
            pass
    assert count(c, "transfer/json/submitted_bytes") == len(raw)
    assert count(c, "transfer/json/completed_bytes") == completed


def test_verified_ref_reuse_counts_no_new_hash():
    raw = b'{"kind":"hot"}'
    c = cost.Collector()
    with cost.instrument(), c.stage("calibration"):
        obj = canonical.Object("hot", raw)
        for _ in range(5):
            obj.ref()
        obj.body()
    assert count(c, "calibration/sha256/calls") == 1
    assert count(c, "calibration/json/completed_bytes") == 2 * len(raw)


def test_concurrent_thread_collectors_are_independent():
    a, b = cost.Collector(), cost.Collector()

    def run(c, n):
        with c.stage("transfer"):
            for _ in range(n):
                canonical.hash_bytes("hot", b"x")

    with cost.instrument(), ThreadPoolExecutor(2) as executor:
        list(executor.map(lambda pair: run(*pair), [(a, 31), (b, 63)]))
    assert count(a, "transfer/sha256/calls") == 31
    assert count(b, "transfer/sha256/calls") == 63


def test_async_cancellation_does_not_contaminate_other_scope():
    a, b = cost.Collector(), cost.Collector()

    async def run(c, fail):
        with c.stage("transfer"):
            await asyncio.sleep(0)
            canonical.hash_bytes("hot", b"x")
            if fail:
                raise asyncio.CancelledError

    async def campaign():
        return await asyncio.gather(run(a, True), run(b, False), return_exceptions=True)

    with cost.instrument():
        asyncio.run(campaign())
    assert count(a, "transfer/sha256/calls") == count(b, "transfer/sha256/calls") == 1
    assert cost.ACTIVE.get() is None


def connection():
    db = sqlite3.connect(":memory:", factory=cost.observed_factory(), isolation_level=None)
    db.execute("CREATE TABLE objects(k TEXT PRIMARY KEY,body BLOB) WITHOUT ROWID")
    return db


def test_insert_ignore_literal_metadata_and_commit_oracle():
    c = cost.Collector()
    with c.stage("generation"), closing(connection()) as db:
        db.execute("BEGIN")
        for _ in range(2):
            db.execute("INSERT OR IGNORE INTO objects VALUES ('한',?)", (b"abc",))
        assert count(c, "generation/objects/INSERT/committed/blob_bytes") == 0
        db.execute("COMMIT")
        assert tuple(
            db.execute("SELECT length(CAST(k AS BLOB)),length(body) FROM objects").fetchone()
        ) == (3, 3)
    assert count(c, "generation/objects/INSERT/attempted/blob_bytes") == 6
    assert count(c, "generation/objects/INSERT/effective/blob_bytes") == 3
    assert count(c, "generation/objects/INSERT/committed/text_bytes") == 3


def test_update_delete_trigger_and_rollback_oracle():
    c = cost.Collector()
    with c.stage("generation"), closing(connection()) as db:
        db.execute("CREATE TABLE pins(k TEXT,reason TEXT)")
        db.execute(
            "CREATE TRIGGER pin AFTER INSERT ON objects BEGIN INSERT INTO pins VALUES (NEW.k,'frozen'); END"
        )
        db.execute("BEGIN")
        db.execute("INSERT INTO objects VALUES (?,?)", ("x", b"abc"))
        db.execute("UPDATE objects SET body=? WHERE k=?", (b"12345", "x"))
        db.execute("DELETE FROM pins WHERE k=?", ("x",))
        db.execute("ROLLBACK")
        assert db.execute("SELECT count(*) FROM objects").fetchone()[0] == 0
    assert count(c, "generation/pins/INSERT/rolled_back/text_bytes") == 7
    assert count(c, "generation/objects/UPDATE/rolled_back/blob_bytes") == 5
    assert count(c, "generation/pins/DELETE/effective/rows") == 1


def test_statement_abort_and_savepoint_do_not_count_committed_bytes():
    c = cost.Collector()
    with c.stage("generation"), closing(connection()) as db:
        db.execute("BEGIN")
        db.execute("INSERT INTO objects VALUES ('a',x'01')")
        db.execute("SAVEPOINT part")
        db.execute("INSERT INTO objects VALUES ('b',x'0203')")
        db.execute("ROLLBACK TO part")
        db.execute("RELEASE part")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO objects VALUES ('a',x'040506')")
        db.execute("COMMIT")
        assert db.execute("SELECT count(*) FROM objects").fetchone()[0] == 1
    assert count(c, "generation/objects/INSERT/committed/blob_bytes") == 1
    assert count(c, "generation/objects/INSERT/rolled_back/blob_bytes") == 2
    assert count(c, "generation/objects/INSERT/attempted/blob_bytes") == 6


def test_connection_close_rolls_back_pending_writes():
    c = cost.Collector()
    with c.stage("generation"):
        db = connection()
        db.execute("BEGIN")
        db.execute("INSERT INTO objects VALUES ('a',x'0102')")
        db.close()
        db.close()  # repository finally may close an already-closed context manager
    assert count(c, "generation/objects/INSERT/committed/blob_bytes") == 0
    assert count(c, "generation/objects/INSERT/rolled_back_on_close/blob_bytes") == 2


def test_exact_production_store_boundary_and_cached_object():
    ctx = canonical.Context(
        canonical.Namespace(*(["12345678-1234-4234-8234-123456789abc"] * 3)), "a" * 64
    )
    raw = canonical.encode(dict(kind="index-empty", **ctx.fields(), structural=1, count="0"))
    c = cost.Collector()
    with cost.instrument(), c.stage("generation"), closing(connection()) as db:
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE sync_objects(hash TEXT PRIMARY KEY,kind TEXT,body BLOB)")
        db.execute("CREATE TABLE sync_object_edges(parent TEXT,child TEXT)")
        store = Store(db, ctx)
        obj = canonical.Object("index-empty", raw)
        db.execute("BEGIN")
        store.put(obj)
        store.put(obj)
        store.get(obj.ref(), {"index-empty"})
        db.execute("COMMIT")
        assert db.execute("SELECT body FROM sync_objects").fetchone()[0] == raw
    assert count(c, "generation/sync_objects/INSERT/committed/blob_bytes") == len(raw)
    assert count(c, "generation/sha256/calls") == 1


def test_uninstrumented_context_neutral_and_arithmetic_unbounded():
    c = cost.Collector()
    with cost.instrument():
        before = canonical.hash_bytes("hot", b"x")
        with c.stage("calibration"):
            c.add("calibration/sha256/hash_input_bytes", 2**63)
            after = canonical.hash_bytes("hot", b"x")
        assert after == before
    assert count(c, "calibration/sha256/hash_input_bytes") > 2**63
    assert len(c.snapshot()) == 2


def test_executemany_counts_each_bind_and_retains_prior_success():
    c = cost.Collector()
    with c.stage("generation"), closing(connection()) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.executemany(
                "INSERT INTO objects VALUES (?,?)", [("a", b"1"), ("b", b"22"), ("a", b"333")]
            )
        assert count(c, "generation/objects/INSERT/committed/blob_bytes") == 3
        assert count(c, "generation/sql/bind_blob_bytes") == 6
        assert db.execute("SELECT count(*) FROM objects").fetchone()[0] == 2


def test_actual_process_kill_does_not_fabricate_committed_bytes(tmp_path):
    target = tmp_path / "synthetic.sqlite"
    with sqlite3.connect(target) as db:
        db.execute("CREATE TABLE objects(k TEXT PRIMARY KEY,body BLOB)")
        db.execute("INSERT INTO objects VALUES ('prior',x'01')")
    script = """
import json, sqlite3, sys, time
sys.path.insert(0, sys.argv[1])
from counters import Collector, observed_factory
c = Collector()
with c.stage("generation"):
    db = sqlite3.connect(sys.argv[2], isolation_level=None, factory=observed_factory())
    db.execute("BEGIN IMMEDIATE")
    db.execute("INSERT INTO objects VALUES ('pending',x'0203')")
    print(json.dumps(c.snapshot()), flush=True)
    time.sleep(30)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(Path(SPEC.origin).parent), str(target)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        import json

        measured = json.loads(process.stdout.readline())
        assert measured["generation/objects/INSERT/effective/blob_bytes"] == "2"
        assert "generation/objects/INSERT/committed/blob_bytes" not in measured
        process.kill()
        assert process.wait(timeout=10) == -9
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT k,body FROM objects").fetchall() == [("prior", b"\x01")]
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

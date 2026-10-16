"""B01's actual SQLite/HTTP budget comparator; no sleep or status relaxation."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from threading import Event
from time import perf_counter
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from isolated_sync import http  # noqa: E402
from isolated_sync.observation import Limits, ObservationRepository  # noqa: E402
from isolated_sync.observation_schema import ObservationConnection  # noqa: E402
from isolated_sync.transfer import TransferLimits  # noqa: E402
from tests.test_isolated_sync_transfer import EVAL, NOW, URL, headers, error  # noqa: E402

pytest_plugins = ["tests.test_isolated_sync_transfer"]


def body():
    return dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)


def configured_client(db, wait=1000, concurrent=8):
    repo = ObservationRepository(
        db, clock=lambda: NOW, evaluation=lambda: EVAL, limits=Limits(lock_wait_ms=wait)
    )
    return TestClient(
        http.create_app(repo, limits=TransferLimits(concurrent_requests=concurrent))
    )


def state(db):
    with sqlite3.connect(db.path) as conn:
        return dict(
            observations=conn.execute(
                "SELECT request_id,status FROM sync_observations ORDER BY request_id"
            ).fetchall(),
            pins=conn.execute(
                "SELECT observation_id,role,hash,active FROM sync_observation_pins ORDER BY 1,2"
            ).fetchall(),
            objects=conn.execute(
                "SELECT hash,length(body) FROM sync_objects ORDER BY hash"
            ).fetchall(),
            current=conn.execute("SELECT * FROM sync_current").fetchall(),
            foreign_keys=conn.execute("PRAGMA foreign_key_check").fetchall(),
        )


def save(name, data):
    output = Path(os.environ.get("B01_OUTPUT", "/tmp/mn-t66f-b01-targeted"))
    output.mkdir(parents=True, exist_ok=True)
    (output / (name + ".json")).write_text(json.dumps(data, indent=2) + "\n")


def test_default_deadline_and_quota_budget_wait_on_same_writer(db, monkeypatch):
    waiting = Event()
    execute = ObservationConnection.execute
    marks = []

    def observed(conn, sql, parameters=()):
        if sql == "BEGIN IMMEDIATE":
            # Event is emitted by SQLite, not by a sleep before entering SQL.
            conn.set_trace_callback(
                lambda statement: (
                    waiting.set() if statement == "BEGIN IMMEDIATE" else None
                )
            )
            mark = perf_counter()
            try:
                return execute(conn, sql, parameters)
            except sqlite3.OperationalError as exc:
                marks.append(
                    dict(
                        wait_seconds=perf_counter() - mark,
                        code=exc.sqlite_errorcode,
                        name=exc.sqlite_errorname,
                        error=str(exc),
                    )
                )
                raise
        return execute(conn, sql, parameters)

    monkeypatch.setattr(ObservationConnection, "execute", observed)
    short, long = body(), body()
    before = state(db)
    with (
        configured_client(db) as normal,
        configured_client(db, 5000) as quota,
        sqlite3.connect(db.path) as blocker,
    ):
        blocker.execute("BEGIN IMMEDIATE")
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(quota.post, URL, json=long, headers=headers())
            try:
                assert waiting.wait(5)
                failed = normal.post(URL, json=short, headers=headers())
                error(failed, 503, "ROOT_NOT_READY")
                assert failed.json()["request_id"] == short["request_id"]
                assert failed.json()["error"] == dict(
                    code="ROOT_NOT_READY",
                    action="retry_same",
                    retry_after_ms=100,
                    current_ns=None,
                )
                assert not future.done(), (
                    "The longer quota budget must still be waiting."
                )
                assert state(db) == before
            finally:
                blocker.rollback()
            success = future.result(10)
        assert success.status_code == 201, success.text
        retry = normal.post(URL, json=short, headers=headers())
        duplicate = normal.post(URL, json=short, headers=headers())
        assert retry.status_code == 201 and duplicate.status_code == 200
        assert retry.content == duplicate.content
    after = state(db)
    assert len(after["observations"]) == 2 and len(after["pins"]) == 10
    assert after["current"] == before["current"] and after["foreign_keys"] == []
    assert len(marks) == 1 and marks[0]["code"] == sqlite3.SQLITE_BUSY
    save(
        "budget-comparator",
        dict(
            default_wait_ms=Limits().lock_wait_ms,
            quota_wait_ms=5000,
            failed_status=failed.status_code,
            failed_body=failed.json(),
            long_status=success.status_code,
            retry_status=retry.status_code,
            duplicate_status=duplicate.status_code,
            sqlite_errors=marks,
            persisted_observations=after["observations"],
            pins=len(after["pins"]),
        ),
    )


@pytest.mark.parametrize("iteration", [0, 1])
def test_busy_and_invalid_requests_release_all_permits_on_disposable_lifespan(
    db, monkeypatch, iteration
):
    adapters = []
    original = http.Adapter

    def capture(*args, **kwargs):
        adapter = original(*args, **kwargs)
        adapters.append(adapter)
        return adapter

    monkeypatch.setattr(http, "Adapter", capture)
    before = state(db)
    with configured_client(db, concurrent=1) as c, sqlite3.connect(db.path) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        try:
            busy = c.post(URL, json=body(), headers=headers())
            error(busy, 503, "ROOT_NOT_READY")
        finally:
            blocker.rollback()
        assert state(db) == before
        invalid = c.post(URL, json=dict(body(), protocol=2), headers=headers())
        error(invalid, 422, "UNSUPPORTED_CONTRACT")
        assert state(db) == before
        valid = c.post(URL, json=body(), headers=headers())
        assert valid.status_code == 201, valid.text
    assert adapters[0].workers.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)
    after = state(db)
    assert after["current"] == before["current"] and after["foreign_keys"] == []
    save(
        "lifecycle-" + str(iteration),
        dict(
            busy=busy.json(),
            invalid=invalid.json(),
            success=valid.status_code,
            permits=adapters[0].workers.snapshot(),
            pins=len(after["pins"]),
        ),
    )


def test_original_quota_status_and_pin_assertions_remain_byte_exact():
    import ast
    import subprocess

    path = "backend/tests/test_isolated_sync_transfer.py"
    original = subprocess.check_output(
        ["git", "show", "c479a379b54e196439c522c1fdf56eca713ca8ad:" + path]
    ).decode()
    current = (ROOT / path).read_text()

    def assertions(source):
        function = next(
            n
            for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef)
            and n.name == "test_bounded_concurrent_quota_and_same_request_status"
        )
        lines = source.splitlines(keepends=True)
        return [
            "".join(lines[n.lineno - 1 : n.end_lineno])
            for n in ast.walk(function)
            if isinstance(n, ast.Assert)
        ]

    assert assertions(current) == assertions(original)
    assert len(assertions(current)) == 3
    assert Limits().lock_wait_ms == 1000
    assert Limits(lock_wait_ms=5000).lock_wait_ms == 5000
    with pytest.raises(ValueError, match="INVALID_LIMITS"):
        Limits(lock_wait_ms=5001)
    save(
        "assertions",
        dict(
            assertions_sha256=hashlib.sha256(
                "".join(assertions(current)).encode()
            ).hexdigest(),
            assertions=assertions(current),
            default_lock_wait_ms=1000,
            test_lock_wait_ms=5000,
        ),
    )

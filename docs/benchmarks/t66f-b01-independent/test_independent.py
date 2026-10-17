"""새 독립 B01 사례. 원 assertion·제품 SQL·제품 timeout은 수정하지 않는다."""

import ast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
import hashlib
from pathlib import Path
import sqlite3
import subprocess
import sys
from threading import Barrier, Event
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).parent))

from isolated_sync import http  # noqa: E402
from isolated_sync.canonical import encode  # noqa: E402
from isolated_sync.observation import Limits, ObservationRepository  # noqa: E402
from isolated_sync.observation_schema import ObservationSandbox  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionSandbox  # noqa: E402
from isolated_sync.transfer import TransferLimits  # noqa: E402
from tests import test_isolated_sync_transfer as original  # noqa: E402
from observer import Observer, database_fds, save  # noqa: E402

pytest_plugins = ["tests.test_isolated_sync_transfer"]


@contextmanager
def cloned(template, retention=False):
    with RetentionSandbox() if retention else ObservationSandbox() as db:
        with (
            closing(sqlite3.connect(template.path)) as source,
            closing(sqlite3.connect(db.path)) as dest,
        ):
            source.backup(dest)
        if retention:
            db.install()
        yield db


@pytest.fixture
def owned(template):
    with cloned(template) as db:
        yield db


def request():
    return dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)


def client(db, *, wait=5000, capacity=8, fault=None, repo=None):
    repository = repo or ObservationRepository(
        db,
        clock=lambda: original.NOW,
        evaluation=lambda: original.EVAL,
        limits=Limits(lock_wait_ms=wait),
    )
    return TestClient(
        http.create_app(
            repository, limits=TransferLimits(concurrent_requests=capacity), fault=fault
        )
    )


def snapshot(db):
    with closing(sqlite3.connect(db.path, timeout=0.1)) as conn:
        result = {
            table: conn.execute("SELECT * FROM " + table + " ORDER BY 1").fetchall()
            for table in [
                "sync_observations",
                "sync_observation_pins",
                "sync_objects",
                "sync_current",
                "sync_observation_budget",
            ]
        }
        # Full financial comparison stays outside the observed product operation.
        result["financial_sha256"] = hashlib.sha256(
            repr(
                [
                    (
                        table,
                        conn.execute(
                            "SELECT * FROM " + table + " ORDER BY 1"
                        ).fetchall(),
                    )
                    for table in original.TABLES
                ]
            ).encode()
        ).hexdigest()
        result["journal"] = conn.execute("PRAGMA journal_mode").fetchone()[0]
        result["integrity"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
        result["foreign_keys"] = conn.execute("PRAGMA foreign_key_check").fetchall()
        assert result["integrity"] == "ok" and result["foreign_keys"] == []
        return result


def compact(state):
    return {
        k: {"count": len(v), "sha256": hashlib.sha256(repr(v).encode()).hexdigest()}
        if isinstance(v, list)
        else v
        for k, v in state.items()
    }


def post(c, body, observer, token=original.TOKEN_A):
    return observer.capture(
        c.post(original.URL, json=body, headers=original.headers(token))
    )


def error(response, status, code, action):
    assert response.status_code == status, response.text
    assert response.json()["protocol"] == 1
    assert response.json()["error"] == dict(
        code=code,
        action=action,
        retry_after_ms=100 if action == "retry_same" else None,
        current_ns=None,
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_I01_exact_assertions_scope_and_supported_budget():
    path = "backend/tests/test_isolated_sync_transfer.py"
    old = subprocess.check_output(
        ["git", "show", "c479a379:" + path], cwd=ROOT, text=True
    )
    new = (ROOT / path).read_text()
    name = "test_bounded_concurrent_quota_and_same_request_status"

    def functions(source):
        return {
            f.name: f for f in ast.parse(source).body if isinstance(f, ast.FunctionDef)
        }

    oldf, newf = functions(old), functions(new)
    a = [
        ast.get_source_segment(old, n)
        for n in ast.walk(oldf[name])
        if isinstance(n, ast.Assert)
    ]
    b = [
        ast.get_source_segment(new, n)
        for n in ast.walk(newf[name])
        if isinstance(n, ast.Assert)
    ]
    assert a == b and len(a) == 3
    assert a[0] == "assert sorted(r.status_code for r in results) == [201]*4+[429]"
    for other in oldf.keys() - {name}:
        assert ast.dump(oldf[other]) == ast.dump(newf[other]), other
    assertion = next(n for n in ast.walk(newf[name]) if isinstance(n, ast.Assert))
    expression = compile(ast.Expression(assertion.test), "strict assertion", "eval")

    class Response:
        def __init__(self, code):
            self.status_code = code

    vectors = [
        [201, 201, 201, 201, 429],
        [201, 201, 201, 429, 503],
        [201, 201, 201, 201, 503],
    ]
    assert [
        eval(expression, {"results": [Response(c) for c in codes]}) for codes in vectors
    ] == [True, False, False]
    assert not newf[name].decorator_list
    assert Limits().lock_wait_ms == 1000
    assert Limits(lock_wait_ms=5000).lock_wait_ms == 5000
    for invalid in [0, 5001, True]:
        with pytest.raises(ValueError, match="INVALID_LIMITS"):
            Limits(lock_wait_ms=invalid)
    prior = subprocess.check_output(
        ["git", "show", "c479a379:backend/tests/test_isolated_sync_observation.py"],
        cwd=ROOT,
        text=True,
    )
    assert "limits=Limits(lock_wait_ms=5000)" in prior
    product = subprocess.check_output(
        [
            "git",
            "diff",
            "c479a379",
            "f4ae582",
            "--",
            "backend/app",
            "backend/isolated_sync",
            "mobile/lib",
            "frontend",
        ],
        cwd=ROOT,
        text=True,
    )
    assert product == ""
    save(
        "I01",
        dict(
            assertions_before=a,
            assertions_after=b,
            status_vectors=vectors,
            strict_results=[True, False, False],
            default=1000,
            supported_max=5000,
            product_diff=product,
        ),
    )


def test_I02_five_long_waiters_and_one_short_probe_preserve_exact_quota(owned):
    before, requests = snapshot(owned), [request() for _ in range(5)]
    initial_fds = database_fds(owned.path)
    with (
        Observer() as observed,
        client(owned) as long,
        client(owned, wait=1000) as short,
        closing(sqlite3.connect(owned.path)) as blocker,
    ):
        waits = [Event() for _ in requests]
        observed.native_begin.update(
            {r["request_id"]: e for r, e in zip(requests, waits)}
        )
        blocker.execute("BEGIN IMMEDIATE")
        observed.record("external_writer_acquired")
        with ThreadPoolExecutor(5) as pool:
            futures = [pool.submit(post, long, r, observed) for r in requests]
            try:
                assert all(e.wait(10) for e in waits)
                probe = request()
                failed = post(short, probe, observed)
                error(failed, 503, "ROOT_NOT_READY", "retry_same")
                assert failed.json()["request_id"] == probe["request_id"]
                assert snapshot(owned) == before
                assert all(not f.done() for f in futures)
            finally:
                blocker.rollback()
                observed.record("external_writer_released")
            responses = [f.result(15) for f in futures]
        assert sorted(r.status_code for r in responses) == [201] * 4 + [429]
        for response in responses:
            if response.status_code == 429:
                error(response, 429, "LEASE_LIMIT", "retry_same")
            else:
                value = response.json()
                assert (
                    value["status"] == "available"
                    and value["target"]["principal_id"] == 1
                )
                assert response.content == encode(value)
        after = snapshot(owned)
        assert (
            len(after["sync_observations"]) == 4
            and len(after["sync_observation_pins"]) == 20
        )
        assert (
            before["sync_current"] == after["sync_current"]
            and before["financial_sha256"] == after["financial_sha256"]
        )
        errors = [
            e
            for e in observed.events
            if e["event"] == "execute_error" and e.get("sqlite_code") == 5
        ]
        assert len(errors) == 1 and errors[0]["sql"] == "BEGIN IMMEDIATE"
        assert errors[0]["elapsed_us"] >= 900_000
        observed.permits_free(8)
    assert all(row["closed"] for row in observed.handles.values())
    assert len(database_fds(owned.path)) == len(initial_fds)
    save(
        "I02",
        dict(
            before=compact(before),
            after=compact(after),
            native_fd_before=initial_fds,
            native_fd_after=database_fds(owned.path),
            **observed.result(),
        ),
    )


def test_I03_auth_is_rechecked_after_supported_lock_wait(owned):
    body, reached = request(), Event()
    before = snapshot(owned)
    with (
        Observer() as observed,
        client(owned) as c,
        closing(sqlite3.connect(owned.path)) as blocker,
    ):
        observed.native_begin[body["request_id"]] = reached
        blocker.execute("BEGIN IMMEDIATE")
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(post, c, body, observed)
            try:
                assert reached.wait(10)
                blocker.execute(
                    "DELETE FROM auth_sessions WHERE session_token_hash=?",
                    (original.auth._hash_session_token(original.TOKEN_A),),
                )
                blocker.commit()
                observed.record("credential_revoked_before_waiter_acquired")
            finally:
                blocker.rollback()
            denied = future.result(15)
        error(denied, 401, "AUTH_REQUIRED", "reauthenticate")
        assert snapshot(owned) == before
        good = post(c, request(), observed, original.TOKEN_NEW)
        assert good.status_code == 201
        observed.permits_free(8)
    save(
        "I03",
        dict(
            before=compact(before), after=compact(snapshot(owned)), **observed.result()
        ),
    )


def test_I04_duplicate_and_conflicting_nonce_cannot_expand_quota(owned):
    body, barrier = request(), Barrier(2)
    with Observer() as observed, client(owned) as c:

        def send():
            barrier.wait(10)
            return post(c, body, observed)

        with ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(lambda _: send(), range(2)))
        assert sorted(r.status_code for r in responses) == [200, 201]
        assert responses[0].content == responses[1].content
        one = snapshot(owned)
        assert (
            len(one["sync_observations"]) == 1
            and len(one["sync_observation_pins"]) == 5
        )
        conflict = post(c, dict(body, inline_bytes=1), observed)
        error(conflict, 409, "REQUEST_CONFLICT", "blocked")
        assert snapshot(owned) == one
        for _ in range(3):
            assert post(c, request(), observed).status_code == 201
        full = snapshot(owned)
        rejected = post(c, request(), observed)
        error(rejected, 429, "LEASE_LIMIT", "retry_same")
        assert snapshot(owned) == full
        assert post(c, body, observed).status_code == 200
        assert (
            len(full["sync_observations"]) == 4
            and len(full["sync_observation_pins"]) == 20
        )
        observed.permits_free(8)
    save("I04", dict(one=compact(one), full=compact(full), **observed.result()))


@pytest.mark.parametrize("boundary", ["authenticated", "sqlite_wait"])
def test_I05_cancelled_native_operation_keeps_permit_until_native_exit(owned, boundary):
    before, body = snapshot(owned), request()
    entered, release = Event(), Event()

    def fault(stage, ticket):
        if boundary == "authenticated" and stage == "authenticated":
            entered.set()
            assert release.wait(15)

    async def run(observed):
        repo = ObservationRepository(
            owned,
            clock=lambda: original.NOW,
            evaluation=lambda: original.EVAL,
            limits=Limits(lock_wait_ms=5000),
        )
        app = http.create_app(
            repo, limits=TransferLimits(concurrent_requests=1), fault=fault
        )
        with closing(sqlite3.connect(owned.path)) as blocker:
            if boundary == "sqlite_wait":
                blocker.execute("BEGIN IMMEDIATE")
            if boundary == "sqlite_wait":
                observed.native_begin[body["request_id"]] = entered
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://synthetic.invalid",
            ) as c:
                task = asyncio.create_task(
                    c.post(original.URL, json=body, headers=original.headers())
                )
                try:
                    assert await asyncio.to_thread(entered.wait, 10)
                    task.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await task
                    blocked = observed.capture(
                        await c.post(
                            original.URL, json=request(), headers=original.headers()
                        )
                    )
                    error(blocked, 503, "ROOT_NOT_READY", "retry_same")
                    assert observed.adapters[-1].workers.snapshot()["running"] == 1
                finally:
                    release.set()
                    blocker.rollback()
                assert await asyncio.to_thread(observed.native_finished.wait, 10)
                assert snapshot(owned) == before
                valid = observed.capture(
                    await c.post(
                        original.URL, json=request(), headers=original.headers()
                    )
                )
                assert valid.status_code == 201

    with Observer() as observed:
        asyncio.run(run(observed))
        observed.permits_free(1)
    assert all(row["closed"] for row in observed.handles.values())
    save(
        "I05-" + boundary,
        dict(
            before=compact(before), after=compact(snapshot(owned)), **observed.result()
        ),
    )


@pytest.mark.parametrize("committed", [False, True])
def test_I06_pre_and_post_commit_failures_have_distinct_durable_results(
    owned, committed
):
    body, before = request(), snapshot(owned)

    class FaultRepository(ObservationRepository):
        armed = True

        def create(self, *args, **kwargs):
            def fail(stage, conn):
                if self.armed and stage == (
                    "after_commit" if committed else "before_commit"
                ):
                    self.armed = False
                    # A real native SQLite error at a supported synthetic fault hook.
                    conn.execute("SELECT missing_b01_column FROM sync_current")

            return super().create(*args, **kwargs, fault=fail)

    repo = FaultRepository(
        owned,
        clock=lambda: original.NOW,
        evaluation=lambda: original.EVAL,
        limits=Limits(lock_wait_ms=5000),
    )
    with Observer() as observed, client(owned, repo=repo) as c:
        failed = post(c, body, observed)
        assert failed.status_code == 500
        assert failed.json()["error"]["code"] == "STORAGE_FAILED"
        after_error = snapshot(owned)
        if committed:
            assert (
                len(after_error["sync_observations"]) == 1
                and len(after_error["sync_observation_pins"]) == 5
            )
        else:
            assert after_error == before
        observed.permits_free(8)
        retry = post(c, body, observed)
        assert retry.status_code == (200 if committed else 201)
        assert post(c, body, observed).status_code == 200
        final = snapshot(owned)
        assert (
            len(final["sync_observations"]) == 1
            and len(final["sync_observation_pins"]) == 5
        )
        assert final["financial_sha256"] == before["financial_sha256"]
        observed.permits_free(8)
    save(
        "I06-" + str(committed),
        dict(
            before=compact(before),
            after_error=compact(after_error),
            final=compact(final),
            **observed.result(),
        ),
    )


@pytest.mark.parametrize("boundary", ["authenticated", "serialized"])
def test_I07_stale_A_request_never_acts_on_replacement_B(template, boundary):
    with cloned(template, True) as a, cloned(template, True) as b:
        a_before, b_before = snapshot(a), snapshot(b)
        entered, release, body = Event(), Event(), request()

        def fault(stage, ticket):
            if stage == boundary:
                entered.set()
                assert release.wait(15)

        repo_a = RetentionRepository(
            a,
            clock=lambda: original.NOW,
            evaluation=lambda: original.EVAL,
            limits=Limits(lock_wait_ms=5000),
        )
        repo_b = RetentionRepository(
            b, clock=lambda: original.NOW, evaluation=lambda: original.EVAL
        )
        with (
            Observer() as observed,
            client(a, repo=repo_a, fault=fault) as ca,
            client(b, repo=repo_b) as cb,
        ):
            with ThreadPoolExecutor(1) as pool:
                future = pool.submit(post, ca, body, observed)
                assert entered.wait(10)
                saved = a.path.with_name("independent-owned-A.sqlite3")
                a.path.rename(saved)
                a.path.symlink_to(b.path)
                try:
                    release.set()
                    denied = future.result(15)
                    assert (
                        denied.status_code == 500
                        and denied.json()["error"]["code"] == "STORAGE_FAILED"
                    )
                    assert snapshot(b) == b_before
                    assert post(cb, request(), observed).status_code == 201
                finally:
                    a.path.unlink()
                    saved.rename(a.path)
            a_after = snapshot(a)
            assert len(a_after["sync_observations"]) == (
                1 if boundary == "serialized" else 0
            )
            # The same original request is retried only after restoring A's actual inode.
            assert post(ca, body, observed).status_code == (
                200 if boundary == "serialized" else 201
            )
            observed.permits_free(8)
        save(
            "I07-" + boundary,
            dict(
                A_before=compact(a_before),
                A_after_rejection=compact(a_after),
                B_before=compact(b_before),
                B_after_valid_own_request=compact(snapshot(b)),
                A_identity=a._owned_file,
                B_identity=b._owned_file,
                **observed.result(),
            ),
        )


@pytest.mark.parametrize("ordering", [[5000, 1000], [1000, 5000]])
def test_I08_fixture_order_does_not_change_another_repository_budget(
    template, ordering
):
    rows = []
    for wait in ordering:
        with cloned(template) as db, Observer() as observed, client(db, wait=wait) as c:
            assert post(c, request(), observed).status_code == 201
            pragmas = [
                e["sql"]
                for e in observed.events
                if e["event"] == "execute_enter"
                and e.get("sql", "").startswith("PRAGMA busy_timeout=")
            ]
            assert pragmas == [f"PRAGMA busy_timeout={wait}"] * 2
            observed.permits_free(8)
            assert all(row["closed"] for row in observed.handles.values())
            rows.append(
                dict(
                    wait=wait,
                    pragmas=pragmas,
                    handles=len(observed.handles),
                    state=compact(snapshot(db)),
                )
            )
        assert Limits().lock_wait_ms == 1000
    save(
        "I08-" + str(ordering[0]),
        dict(order=ordering, phases=rows, global_default=Limits().lock_wait_ms),
    )


@pytest.mark.parametrize("wait", [1000, 5000])
def test_I09_native_busy_timeout_and_close_are_connection_local(owned, wait):
    baseline = database_fds(owned.path)
    # Compare the original backup fixture's context-manager semantics directly.
    with sqlite3.connect(owned.path) as backup_style:
        assert not backup_style.in_transaction
    assert backup_style.execute("SELECT 1").fetchone() == (1,)
    backup_style.close()
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        backup_style.execute("SELECT 1")
    repository = ObservationRepository(
        owned,
        clock=lambda: original.NOW,
        evaluation=lambda: original.EVAL,
        limits=Limits(lock_wait_ms=wait),
    )
    with closing(owned.connect()) as initial:
        assert initial.execute("PRAGMA busy_timeout").fetchone()[0] == 100
    with repository._connection() as (connection, retired):
        assert (
            connection.in_transaction
            and connection.execute("PRAGMA busy_timeout").fetchone()[0] == wait
        )
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA recursive_triggers").fetchone()[0] == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")
    with closing(owned.connect()) as after:
        assert after.execute("PRAGMA busy_timeout").fetchone()[0] == 100
        after.execute("BEGIN IMMEDIATE")
        after.rollback()
    assert len(database_fds(owned.path)) == len(baseline)
    save(
        "I09-" + str(wait),
        dict(
            connection_admission_ms=100,
            repository_budget_ms=wait,
            default_after=Limits().lock_wait_ms,
            sqlite_context_manager_closes_handle=False,
            fd_before=baseline,
            fd_after=database_fds(owned.path),
            state=compact(snapshot(owned)),
        ),
    )

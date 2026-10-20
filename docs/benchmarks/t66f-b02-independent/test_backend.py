"""새 독립 backend 반례. 실제 retention HTTP와 원 strict resolver를 비교한다."""

from contextlib import closing
from datetime import timedelta
import base64
import hashlib
import json
import random
import sqlite3
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from isolated_sync import canonical, transfer, http
from isolated_sync.retention import RetentionRepository
from isolated_sync.retention_schema import RetentionSandbox
from tests.test_isolated_sync_observation import NOW, EVAL
from tests.test_isolated_sync_transfer import (
    URL,
    TOKEN_A,
    TOKEN_B,
    TOKEN_NEW,
    headers,
    observe,
    graph,
)

pytest_plugins = ("tests.test_isolated_sync_transfer",)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


@pytest.fixture
def owned(template):
    with RetentionSandbox() as value:
        with (
            closing(sqlite3.connect(template.path)) as src,
            closing(sqlite3.connect(value.path)) as dst,
        ):
            src.backup(dst)
        value.install()
        yield value


def app_client(db, **kwargs):
    clock = kwargs.pop("clock", lambda: NOW)
    return TestClient(
        http.create_app(
            RetentionRepository(db, clock=clock, evaluation=lambda: EVAL), **kwargs
        )
    )


def packet(rows):
    return {
        "protocol": 1,
        "request_id": str(uuid4()),
        "items": [
            {"path": list(v[1]), "offset": "0", "length": len(v[2])} for v in rows
        ],
    }


def send(c, m, p, token=TOKEN_A):
    return c.post(
        f"{URL}/{m['observation_id']}/objects", json=p, headers=headers(token)
    )


def leaves(db, m):
    return [v for v in graph(db, m).values() if v[3]["kind"] == "index-leaf"][:64]


def strict_class():
    name = "b02_audit_original_transfer"
    module = types.ModuleType(name)
    sys.modules[name] = module
    raw = subprocess.check_output(
        [
            "git",
            "show",
            "6282c1c3577c42bba9382d786745d583a5d88236:backend/isolated_sync/transfer.py",
        ],
        cwd=ROOT,
    )
    exec(compile(raw, "git-original-transfer", "exec"), module.__dict__)

    class Strict(module.PathResolver):
        prefix_hits = prefix_misses = prefix_peak = prefix_byte_peak = 0

        def __init__(self, *a, **kwargs):
            super().__init__(*a)

        def clear_prefixes(self):
            pass

    return Strict


STRICT = strict_class()


@pytest.mark.parametrize("shape", ["siblings", "repeat", "reverse", "spread"])
def test_response_exact_bytes_and_validation_counts(owned, shape):
    metrics = []
    c = app_client(owned, metrics=metrics.append)
    m = observe(c).json()
    v = leaves(owned, m)
    if shape == "repeat":
        v = [v[3]] * 64
    if shape == "reverse":
        v = v[::-1]
    if shape == "spread":
        v = v[::4]
    p = packet(v)
    with patch.object(transfer, "PathResolver", STRICT):
        old = send(c, m, p)
        old_m = dict(metrics[-1])
    new = send(c, m, p)
    new_m = dict(metrics[-1])
    assert new.status_code == old.status_code == 200
    assert new.content == old.content
    assert [
        base64.b64decode(x["data_base64"], validate=True) for x in new.json()["chunks"]
    ] == [x[2] for x in v]
    assert (
        new_m["object_reads"] >= len(v)
        and new_m["object_reads"] < old_m["object_reads"]
    )
    assert new_m["prefix_cache_hits"] > 0
    assert (
        new_m["prefix_cache_peak"] <= 32768
        and new_m["prefix_cache_peak_bytes"] <= 1048576
    )
    # A later request must allocate its own resolver and validate metadata again.
    again = send(c, m, p)
    assert again.content == new.content
    assert metrics[-1]["prefix_validations"] == new_m["prefix_validations"]
    (HERE / f"response-{shape}.json").write_text(
        json.dumps({"old": old_m, "new": new_m}, indent=2) + "\n"
    )


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("child", (422, "INVALID_REQUEST")),
        ("cycle", (422, "INVALID_REQUEST")),
        ("offset", (422, "INVALID_REQUEST")),
        ("corrupt_parent", (500, "STORAGE_FAILED")),
        ("corrupt_leaf", (500, "STORAGE_FAILED")),
        ("wrong_type", (500, "STORAGE_FAILED")),
        ("missing", (410, "OBSERVATION_INCOMPLETE")),
        ("wrong_hash", (422, "INVALID_REQUEST")),
        ("principal", (403, "PRINCIPAL_OR_SESSION_CHANGED")),
        ("credential", (403, "PRINCIPAL_OR_SESSION_CHANGED")),
        ("epoch", (409, "EPOCH_CHANGED")),
        ("dataset", (409, "EPOCH_CHANGED")),
        ("expiry", (410, "OBSERVATION_EXPIRED")),
        ("observation", (410, "OBSERVATION_INCOMPLETE")),
    ],
)
def test_cached_prefix_negative_http_and_state(owned, fault, expected, monkeypatch):
    clock = [NOW]
    c = app_client(owned, clock=lambda: clock[0])
    m = observe(c).json()
    v = leaves(owned, m)[:2]
    p = packet(v)
    assert send(c, m, p).status_code == 200
    backup = None
    if fault in {"child", "wrong_hash"}:
        p["items"][1]["path"][-1] = "0" * 64
    elif fault == "cycle":
        p["items"][1]["path"].append(p["items"][1]["path"][0])
    elif fault == "offset":
        p["items"][1]["offset"] = "99999999"
    elif fault in {"corrupt_parent", "corrupt_leaf", "wrong_type", "missing"}:
        digest = v[1][1][-2] if fault == "corrupt_parent" else v[1][0]["hash"]
        with sqlite3.connect(owned.path) as db:
            backup = db.execute(
                "SELECT * FROM sync_objects WHERE hash=?", (digest,)
            ).fetchone()
            if fault == "missing":
                original_get = transfer.Store.get

                def missing_get(self, ref, kinds):
                    if ref["hash"] == digest:
                        raise canonical.CanonicalError("REJECT_OBJECT_MISSING")
                    return original_get(self, ref, kinds)

                monkeypatch.setattr(transfer.Store, "get", missing_get)
            elif fault == "wrong_type":
                db.execute("UPDATE sync_objects SET kind='hot' WHERE hash=?", (digest,))
            else:
                db.execute(
                    "UPDATE sync_objects SET body=? WHERE hash=?",
                    (bytes(backup[2]) + b" ", digest),
                )
    elif fault in {"epoch", "dataset"}:
        with sqlite3.connect(owned.path) as db:
            value = json.loads(
                db.execute("SELECT namespace FROM sync_current").fetchone()[0]
            )
            value["epoch" if fault == "epoch" else "dataset_id"] = str(uuid4())
            db.execute("UPDATE sync_current SET namespace=?", (json.dumps(value),))
    elif fault == "expiry":
        clock[0] += timedelta(seconds=901)
    elif fault == "observation":
        m = dict(m, observation_id=str(uuid4()))
    auth = (
        TOKEN_B
        if fault == "principal"
        else TOKEN_NEW
        if fault == "credential"
        else TOKEN_A
    )
    old = None
    with patch.object(transfer, "PathResolver", STRICT):
        old = send(c, m, p, auth)
    new = send(c, m, p, auth)
    assert (new.status_code, new.json()["error"]["code"]) == expected
    assert (old.status_code, old.json()) == (new.status_code, new.json())
    assert new.headers["cache-control"] == "no-store" and "chunks" not in new.json()
    with sqlite3.connect(owned.path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert (
            db.execute(
                'SELECT count(*)FROM sync_commits WHERE status!="complete"'
            ).fetchone()[0]
            == 0
        )
    (HERE / f"negative-{fault}.json").write_text(
        json.dumps(
            {
                "status": new.status_code,
                "body": new.json(),
                "original_strict_equal": True,
                "missing_storage_read_injection": fault == "missing",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    # Packet defects do not poison later correct requests.
    if fault in {"child", "cycle", "offset", "wrong_hash"}:
        assert send(c, m, packet(v)).status_code == 200


@pytest.mark.parametrize(
    "capacity,budget",
    [(0, 0), (1, 1048576), (2, 1024), (16, 1048576), (32768, 1048576)],
)
def test_capacity_fallback_remains_strict(owned, capacity, budget):
    c = app_client(owned)
    m = observe(c).json()
    v = leaves(owned, m)[:8]
    repo = RetentionRepository(owned, clock=lambda: NOW, evaluation=lambda: EVAL)
    from app.services.authoritative_state import BundleCredential

    credential = BundleCredential(hashlib.sha256(TOKEN_A.encode()).hexdigest(), 1)
    with repo._connection() as (conn, retired):
        target = repo._lookup(
            conn, retired, m["observation_id"], credential, lambda: credential
        )["target"]
        r = transfer.PathResolver(
            conn, repo, target, prefix_capacity=capacity, prefix_bytes=budget
        )
        for _, path, raw, _ in v:
            assert r.resolve(path).raw == raw
        assert len(r._prefixes) <= capacity and r._prefix_size <= budget
        if capacity == 1:
            assert r.prefix_misses > 1
        r.clear_prefixes()
        assert len(r._prefixes) == r._prefix_size == 0


def test_quota_release_and_request_cancel(owned):
    metrics = []
    repo = RetentionRepository(owned, clock=lambda: NOW, evaluation=lambda: EVAL)
    app = http.create_app(repo, metrics=metrics.append)
    with TestClient(app) as c:
        values = [observe(c) for _ in range(5)]
        assert [r.status_code for r in values] == [201] * 4 + [429]
        assert values[-1].json()["error"]["code"] == "LEASE_LIMIT"
        m = values[0].json()
        assert (
            c.delete(URL + "/" + m["observation_id"], headers=headers()).status_code
            == 204
        )
        assert observe(c).status_code == 201
        m = values[1].json()
        p = packet(leaves(owned, m)[:2])

        def fault(stage, ticket):
            if stage == "objects_prepared":
                ticket.cancelled.set()

        with patch.object(
            next(
                r.endpoint.__closure__[0].cell_contents
                for r in app.routes
                if r.path == URL
            ),
            "fault",
            fault,
        ):
            response = send(c, m, p)
        assert (
            response.status_code == 403
            and response.json()["error"]["code"] == "PRINCIPAL_OR_SESSION_CHANGED"
        )
        assert send(c, m, p).status_code == 200


def test_database_replacement_after_cache_prepare_is_fenced(owned):
    c0 = app_client(owned)
    m = observe(c0).json()
    p = packet(leaves(owned, m)[:4])
    saved = owned.path.with_name("audit-original.sqlite3")
    swapped = []
    with RetentionSandbox() as replacement:
        with (
            closing(sqlite3.connect(owned.path)) as src,
            closing(sqlite3.connect(replacement.path)) as dst,
        ):
            src.backup(dst)
        before = replacement.path.read_bytes()

        def fault(stage, ticket):
            if stage == "serialized" and ticket.observation_id and not swapped:
                owned.path.rename(saved)
                owned.path.symlink_to(replacement.path)
                swapped.append(True)

        try:
            with app_client(owned, fault=fault) as c:
                r = send(c, m, p)
                assert (
                    r.status_code == 500
                    and r.json()["error"]["code"] == "STORAGE_FAILED"
                )
            assert replacement.path.read_bytes() == before
        finally:
            if swapped:
                owned.path.unlink()
                saved.rename(owned.path)
        assert send(c0, m, p).status_code == 200


def test_c1_old_new_full_admission_differential():
    module = types.ModuleType("original_c1")
    sys.modules[module.__name__] = module
    raw = subprocess.check_output(
        [
            "git",
            "show",
            "6282c1c3577c42bba9382d786745d583a5d88236:backend/isolated_sync/canonical.py",
        ],
        cwd=ROOT,
    )
    exec(compile(raw, "git-original-c1", "exec"), module.__dict__)
    corpus = [
        b"null",
        b"{}",
        b'{"a":1,"a":2}',
        b"1e-400",
        b"1.0",
        b"-0.0",
        b"9223372036854775808",
        b'"\\ud800"',
        b'{"\\udfff":0}',
        b' {"x":1} ',
        b"NaN",
        b"1.1",
        b"[true,null,1]",
    ]
    rng = random.Random(662602)
    for _ in range(2000):
        corpus.append(
            json.dumps(
                {
                    "한글😀": [
                        rng.randrange(-100000, 100000),
                        None,
                        True,
                        "\x1c+0001000.00\x1f",
                    ]
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode()
        )
    for name in ["decode_json", "decode_c1"]:
        for raw in corpus:
            values = []
            for implementation in [module, canonical]:
                try:
                    values.append(("value", getattr(implementation, name)(raw)))
                except ValueError as e:
                    values.append(("error", str(e)))
            assert values[0] == values[1]

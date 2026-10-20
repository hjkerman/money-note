"""B02-A01: real HTTP/SQLite differential against the preserved strict resolver.

The before source is evidence, never imported by product code. Terminal object
bytes/order and strict error semantics are independent of prefix-cache metrics.
"""

import base64
from datetime import timedelta
import gzip
import json
from pathlib import Path
import sqlite3
import types
from unittest.mock import patch
from uuid import uuid4

import pytest

from isolated_sync import transfer
from isolated_sync.observation import ObservationError
from tests.test_isolated_sync_observation import NOW, repository
from tests.test_isolated_sync_transfer import (
    TOKEN_B,
    TOKEN_NEW,
    URL,
    client,
    graph,
    headers,
    observe,
)

pytest_plugins = ("tests.test_isolated_sync_transfer",)
SOURCE = (
    Path(__file__).resolve().parents[2]
    / "docs/benchmarks/t66f-b02-a01-correction/transfer.py.before.gz"
)
before = types.ModuleType("b02_a01_strict_before")
exec(compile(gzip.decompress(SOURCE.read_bytes()), str(SOURCE), "exec"), before.__dict__)


class StrictBefore(before.PathResolver):
    """Keep the original algorithm; adapt ONLY its metric/interface shape."""

    prefix_hits = prefix_misses = prefix_peak = prefix_byte_peak = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

    def clear_prefixes(self):
        pass


def packet(values):
    return dict(
        protocol=1,
        request_id=str(uuid4()),
        items=[dict(path=path, offset="0", length=len(raw)) for _, path, raw, _ in values],
    )


def send(c, m, body, *, strict=False, auth=None):
    with patch.object(transfer, "PathResolver", StrictBefore if strict else transfer.PathResolver):
        return c.post(
            URL + "/" + m["observation_id"] + "/objects", json=body, headers=auth or headers()
        )


def leaves(db, m):
    return [v for v in graph(db, m).values() if v[3]["kind"] == "index-leaf"][:64]


@pytest.mark.parametrize("shape", ["shared", "repeated", "root_only"])
def test_exact_http_output_equivalence(db, shape):
    seen = []
    c = client(db, metrics=seen.append)
    m = observe(c).json()
    values = leaves(db, m)
    if shape == "repeated":
        values = [values[0]] * 64
    elif shape == "root_only":
        values = [v for v in graph(db, m).values() if len(v[1]) == 1]
    body = packet(values)
    old = send(c, m, body, strict=True)
    old_metric = seen[-1]
    new = send(c, m, body)
    metric = seen[-1]
    assert (old.status_code, new.status_code) == (200, 200)
    assert old.content == new.content
    assert [base64.b64decode(v["data_base64"], validate=True) for v in new.json()["chunks"]] == [
        v[2] for v in values
    ]
    assert old_metric["object_reads"] == sum(len(v[1]) for v in values)
    if shape == "root_only":
        assert metric["prefix_cache_hits"] == 0
        assert metric["object_reads"] == len(values)
    else:
        assert metric["prefix_cache_hits"] > 0
        assert metric["object_reads"] < old_metric["object_reads"]
        # Each requested terminal remains strictly read/validated, even repeated.
        assert metric["object_reads"] >= len(values)
    assert metric["prefix_cache_peak_bytes"] <= transfer.MIB
    assert metric["prefix_cache_peak"] <= 64 * 512


@pytest.mark.parametrize(
    "defect", ["descendant", "guessed_root", "hash", "cycle", "offset", "items", "bytes"]
)
def test_cached_prefix_does_not_authorize_invalid_packet(db, defect):
    c = client(db)
    m = observe(c).json()
    body = packet(leaves(db, m)[:2])
    if defect in {"descendant", "hash"}:
        body["items"][1]["path"][-1] = "0" * 64
    elif defect == "guessed_root":
        body["items"][1]["path"][0] = "0" * 64
    elif defect == "cycle":
        body["items"][1]["path"].append(body["items"][1]["path"][0])
    elif defect == "offset":
        body["items"][1]["offset"] = "999999999"
    elif defect == "items":
        body["items"] *= 33
    else:
        body["items"][1]["length"] = transfer.MIB
    old, new = send(c, m, body, strict=True), send(c, m, body)
    assert old.status_code == new.status_code == (413 if defect in {"items", "bytes"} else 422)
    assert old.content == new.content
    assert "chunks" not in new.json()
    # Failed prefix/leaf work cannot poison a later request.
    valid = packet(leaves(db, m)[:2])
    assert send(c, m, valid).status_code == 200


@pytest.mark.parametrize("defect", ["missing", "prefix", "leaf", "kind"])
def test_corruption_after_common_prefix_remains_strict(db, defect):
    c = client(db)
    m = observe(c).json()
    values = leaves(db, m)[:2]
    digest = values[1][1][-2 if defect == "prefix" else -1]
    with sqlite3.connect(db.path) as conn:
        if defect == "missing":
            conn.execute("DELETE FROM sync_objects WHERE hash=?", (digest,))
        elif defect == "kind":
            conn.execute("UPDATE sync_objects SET kind='snapshot-leaf' WHERE hash=?", (digest,))
        else:
            raw = conn.execute("SELECT body FROM sync_objects WHERE hash=?", (digest,)).fetchone()[
                0
            ]
            conn.execute("UPDATE sync_objects SET body=? WHERE hash=?", (raw + b" ", digest))
    body = packet(values)
    a, b = send(c, m, body, strict=True), send(c, m, body)
    assert a.status_code == b.status_code == (410 if defect == "missing" else 500)
    assert a.json() == b.json()
    assert "chunks" not in b.json()


@pytest.mark.parametrize("defect", ["principal", "credential", "expiry", "epoch", "dataset"])
def test_request_local_context_is_always_readmitted(db, defect):
    seen = []
    c = client(db, metrics=seen.append)
    m = observe(c).json()
    body = packet(leaves(db, m)[:4])
    assert send(c, m, body).status_code == 200
    if defect in {"epoch", "dataset"}:
        with sqlite3.connect(db.path) as conn:
            ns = json.loads(conn.execute("SELECT namespace FROM sync_current").fetchone()[0])
            ns["epoch" if defect == "epoch" else "dataset_id"] = str(uuid4())
            conn.execute("UPDATE sync_current SET namespace=?", (json.dumps(ns),))
    auth = (
        headers(TOKEN_B if defect == "principal" else TOKEN_NEW)
        if defect in {"principal", "credential"}
        else None
    )
    if defect == "expiry":
        c = client(db, clock=lambda: NOW + timedelta(seconds=900))
    new = send(c, m, body, auth=auth)
    assert (
        new.status_code
        == {"principal": 403, "credential": 403, "expiry": 410, "epoch": 409, "dataset": 409}[
            defect
        ]
    )
    assert "chunks" not in new.json()


def test_cache_is_new_for_every_request_and_observation(db):
    metrics = []
    c = client(db, metrics=metrics.append)
    m = observe(c).json()
    body = packet(leaves(db, m)[:12])
    for manifest in (m, m, observe(c).json()):
        assert send(c, manifest, body).status_code == 200
    rows = metrics[-3:]
    assert len({r["object_reads"] for r in rows}) == 1
    assert all(r["prefix_validations"] > 0 for r in rows)


@pytest.mark.parametrize("capacity,budget", [(1, transfer.MIB), (2, transfer.MIB), (64 * 512, 1)])
def test_bounded_eviction_and_oversized_fallback(db, capacity, budget):
    m = observe(client(db)).json()
    values = leaves(db, m)[:12]
    repo = repository(db)
    with repo._connection() as (conn, retired):
        r = transfer.PathResolver(
            conn, repo, m["target"], prefix_capacity=capacity, prefix_bytes=budget
        )
        for _, path, raw, _ in values:
            assert r.resolve(path).raw == raw
        assert r.prefix_peak <= capacity
        assert r.prefix_byte_peak <= budget
        r.clear_prefixes()
        assert not r._prefixes and r._prefix_size == 0


def test_context_key_includes_every_typed_edge_field(db):
    from dataclasses import replace

    m = observe(client(db)).json()
    repo = repository(db)
    edge = transfer.Edge(m["target"]["index_ref"], frozenset({"index-root"}), root=True)
    with repo._connection() as (conn, retired):
        r = transfer.PathResolver(conn, repo, m["target"])
        base = r._prefix_key([edge.ref["hash"]], 0, edge)
        for changed in (
            replace(edge, table="ledger_entries"),
            replace(edge, kinds=frozenset({"raw-root"})),
            replace(edge, count=2),
            replace(edge, parent_count=3),
            replace(edge, prefix="0"),
            replace(edge, root=False),
            replace(edge, ref=dict(edge.ref, bytes="1")),
        ):
            assert r._prefix_key([edge.ref["hash"]], 0, changed) != base


def test_transaction_loss_cannot_reuse_verified_prefix(db):
    m = observe(client(db)).json()
    repo = repository(db)
    values = leaves(db, m)[:2]
    # A private request transaction must not be swapped out under a resolver.
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        r = transfer.PathResolver(
            conn, repo, m["target"], prefix_capacity=64, prefix_bytes=transfer.MIB
        )
        r.resolve(values[0][1])
        conn.rollback()
        with pytest.raises(ObservationError, match="REQUIRED_METADATA_INVALID"):
            r.resolve(values[1][1])
        assert not r._prefixes


@pytest.mark.parametrize("change", ["cancel", "expire", "error"])
def test_warmed_cache_is_discarded_before_terminal_failure(db, change):
    clock = [NOW]
    m = observe(client(db)).json()
    values = leaves(db, m)[:12]
    instances = []
    real = transfer.PathResolver

    class Observed(real):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            instances.append(self)

    def fault(stage, ticket):
        if stage != "objects_prepared":
            return
        assert instances[-1].prefix_hits > 0
        assert not instances[-1]._prefixes
        if change == "cancel":
            ticket.cancelled.set()
        elif change == "expire":
            clock[0] = NOW + timedelta(seconds=900)
        else:
            raise RuntimeError("synthetic terminal failure")

    with patch.object(transfer, "PathResolver", Observed):
        result = send(client(db, clock=lambda: clock[0], fault=fault), m, packet(values))
    assert result.status_code == {"cancel": 403, "expire": 410, "error": 500}[change]
    assert "chunks" not in result.json()
    assert all(not r._prefixes for r in instances)
    # A distinct admitted request does not inherit the canceled cache or permit.
    fresh = observe(client(db)).json()
    assert send(client(db), fresh, packet(values)).status_code == 200

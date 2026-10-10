from copy import deepcopy
import hashlib

import pytest

from isolated_sync.canonical import CanonicalError, encode
from isolated_sync.roots import sync_root, u64
from tests.test_isolated_sync_segments import CTX


def target():
    return dict(ns=CTX.ns.wire(), principal_id=1,
                versions=dict(sync=1, canon=1, structural=1, snapshot=7, recurring_ownership=1,
                              raw_schema=CTX.raw_schema, projection_schema="b"*64, policy_registry="c"*64),
                revision="123", context=dict(evaluation_date="2026-10-05", timezone_offset_minutes=540,
                                             financial_engine="d"*64),
                **{name: dict(hash=f"{i}"*64, bytes=str(i)) for i, name in
                   enumerate(("raw_ref", "index_ref", "hot_ref", "control_ref"), 1)})


def test_global_view_hash_binds_versions_context_refs_and_identity():
    body = target()
    digest = sync_root(body)
    assert digest == hashlib.sha256(b"money-note.sync.v1/view\0" + encode(body)).hexdigest()
    for path, value in [("revision", "125"), ("principal_id", 2),
                         (("ns", "epoch"), "44444444-4444-4444-8444-444444444444"),
                         (("context", "evaluation_date"), "2026-11-01"),
                         (("versions", "raw_schema"), "f"*64),
                         (("versions", "policy_registry"), "f"*64),
                         (("raw_ref", "hash"), "f"*64), (("hot_ref", "bytes"), "999")]:
        changed = deepcopy(body)
        if isinstance(path, tuple):
            changed[path[0]][path[1]] = value
        else:
            changed[path] = value
        assert sync_root(changed) != digest
    with pytest.raises(CanonicalError):
        sync_root({**body, "sync_root": digest})  # do not recursively hash itself


@pytest.mark.parametrize("value", ["-0", "01", "-1", "9223372036854775808", "", 1, None, "1e3"])
def test_metadata_u64_fail_closed(value):
    with pytest.raises(CanonicalError):
        u64(value)


def test_metadata_u64_edges():
    assert u64("0") == "0" and u64("9223372036854775807") == "9223372036854775807"

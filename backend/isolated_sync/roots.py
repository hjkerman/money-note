"""T6.6C §9 view hashing only; NOT an authority producer or D2b finalizer.

Caller must establish all referenced objects, complete global constraints,
release descriptor compatibility, coherent revision and financial evaluation.
This helper cannot turn a D1 capture certificate into an authoritative state.
"""

import re

from isolated_sync.canonical import HASH, MAX_I64, Namespace, encode, fail, hash_bytes, integer
from isolated_sync.raw import valid_date


def u64(value):
    if type(value) is not str or not re.fullmatch(r"0|[1-9][0-9]*", value):
        fail("REJECT_U64")
    if len(value) > 19 or int(value) > MAX_I64:
        fail("REJECT_U64")
    return value


def _hash(value):
    if type(value) is not str or not HASH.fullmatch(value):
        fail("REJECT_HASH")


def sync_root(target):
    """Hash exact Target WITHOUT sync_root, after envelope-shape admission."""
    required = {"ns", "principal_id", "versions", "revision", "context",
                "raw_ref", "index_ref", "hot_ref", "control_ref"}
    if type(target) is not dict or set(target) != required:
        fail("REJECT_TARGET_SHAPE")
    ns = target["ns"]
    if type(ns) is not dict or set(ns) != {"server_id", "dataset_id", "epoch"}:
        fail("REJECT_NAMESPACE")
    Namespace(**ns)
    if integer(target["principal_id"]) <= 0:
        fail("REJECT_PRINCIPAL")
    u64(target["revision"])
    versions = target["versions"]
    fixed = dict(sync=1, canon=1, structural=1, snapshot=7, recurring_ownership=1)
    hashes = {"raw_schema", "projection_schema", "policy_registry"}
    if type(versions) is not dict or set(versions) != set(fixed) | hashes:
        fail("REJECT_VERSIONS")
    for key, expected in fixed.items():
        if type(versions[key]) is not int or versions[key] != expected:
            fail("REJECT_VERSION")
    for key in hashes:
        _hash(versions[key])
    context = target["context"]
    if type(context) is not dict or set(context) != {"evaluation_date", "timezone_offset_minutes", "financial_engine"}:
        fail("REJECT_EVALUATION_CONTEXT")
    offset = context["timezone_offset_minutes"]
    if not valid_date(context["evaluation_date"]) or type(offset) is not int or not -1439 <= offset <= 1439:
        fail("REJECT_EVALUATION_CONTEXT")
    _hash(context["financial_engine"])
    for name in ("raw_ref", "index_ref", "hot_ref", "control_ref"):
        value = target[name]
        if type(value) is not dict or set(value) != {"hash", "bytes"}:
            fail("REJECT_REF")
        _hash(value["hash"])
        u64(value["bytes"])
    return hash_bytes("view", encode(target))

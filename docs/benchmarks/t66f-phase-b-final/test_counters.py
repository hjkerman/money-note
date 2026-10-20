"""알려진 원문·stdlib SHA·별도 SQLite SELECT를 oracle로 사용한다."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from isolated_sync import canonical
from isolated_sync.store import Store
from counters import Counters, InsertConnection, observe_c1

HERE = Path(__file__).resolve().parent
RESULTS = []
RAW = b'{"kind":"hot","x":"\xed\x95\x9c"}'
PREIMAGE = b"money-note.sync.v1/hot\0" + RAW


@pytest.fixture(autouse=True)
def evidence(request):
    yield
    RESULTS.append(request.node.name)


@pytest.fixture(scope="session", autouse=True)
def save_evidence():
    yield
    (HERE / "evidence/calibration-observations.json").write_text(
        json.dumps({"executed_cases": RESULTS}, indent=2) + "\n"
    )


def test_hash_actual_preimage_and_repetition():
    c = Counters()
    with observe_c1(c):
        assert canonical.hash_bytes("hot", RAW) == hashlib.sha256(PREIMAGE).hexdigest()
        assert canonical.hash_bytes("hot", RAW) == hashlib.sha256(PREIMAGE).hexdigest()
    assert c.values["hash_input_bytes"] == 2 * len(PREIMAGE)
    assert c.values["hash_calls"] == 2


def test_hash_chunked_update_counts_each_actual_input():
    c = Counters()
    with observe_c1(c):
        h = canonical.hashlib.sha256(b"ab")
        h.update(b"c")
        h.update(b"c")
        assert h.digest() == hashlib.sha256(b"abcc").digest()
    assert c.values["hash_input_bytes"] == 4


def test_object_ref_reuse_skips_hash_but_body_decodes_again():
    c = Counters()
    with observe_c1(c):
        obj = canonical.Object("hot", RAW)
        for _ in range(3):
            assert obj.ref()["hash"] == hashlib.sha256(PREIMAGE).hexdigest()
        obj.body()
        obj.body()
    assert c.values["hash_calls"] == 1
    assert c.values["validation_completed_input_bytes"] == 3 * len(RAW)


def test_validation_full_buffer_success_and_duplicates():
    c = Counters()
    with observe_c1(c):
        assert canonical.decode_c1(RAW) == {"kind": "hot", "x": "한"}
        canonical.decode_c1(RAW)
    assert c.values["validation_completed_input_bytes"] == 2 * len(RAW)


def test_failed_canonical_equality_still_completed_json_boundary():
    c = Counters()
    with observe_c1(c), pytest.raises(canonical.CanonicalError):
        canonical.decode_c1(b"{ }")
    assert c.values["validation_completed_input_bytes"] == 3


def test_failed_utf8_has_submitted_bytes_but_no_completed_bytes():
    c = Counters()
    with observe_c1(c), pytest.raises(canonical.CanonicalError):
        canonical.decode_c1(b"\xfftrailing")
    assert c.values["validation_failed_submitted_bytes"] == 9
    assert c.values["validation_completed_input_bytes"] == 0


def test_hash_and_validation_are_distinct_not_summed():
    c = Counters()
    with observe_c1(c):
        canonical.Object("hot", RAW)
    assert c.values["hash_input_bytes"] == len(PREIMAGE)
    assert c.values["validation_completed_input_bytes"] == len(RAW)


def test_concurrent_actual_calls_do_not_lose_counts():
    c = Counters()
    with observe_c1(c), ThreadPoolExecutor(max_workers=4) as pool:
        actual = list(pool.map(lambda _: canonical.hash_bytes("hot", RAW), range(64)))
    assert set(actual) == {hashlib.sha256(PREIMAGE).hexdigest()}
    assert c.values["hash_calls"] == 64
    assert c.values["hash_input_bytes"] == 64 * len(PREIMAGE)


def test_counter_above_signed64_does_not_saturate():
    c = Counters()
    c.add(hash_input_bytes=2**63 - 1)
    with observe_c1(c):
        canonical.hash_bytes("hot", RAW)
    assert c.values["hash_input_bytes"] == 2**63 - 1 + len(PREIMAGE)


def test_cleanup_after_failure_restores_exact_functions():
    previous_hashlib, previous_parse = canonical.hashlib, canonical._parse_json
    with pytest.raises(RuntimeError), observe_c1(Counters()):
        raise RuntimeError("합성 실패")
    assert canonical.hashlib is previous_hashlib
    assert canonical._parse_json is previous_parse


def connection():
    db = sqlite3.connect(":memory:", factory=InsertConnection, isolation_level=None)
    db.execute("CREATE TABLE objects(k TEXT PRIMARY KEY, body BLOB)")
    return db


def test_insert_utf8_blob_committed_and_independent_length():
    with closing(connection()) as db:
        db.execute("BEGIN")
        db.execute("INSERT INTO objects VALUES (?,?)", ("한", b"abc"))
        assert db.meter.values["attempted_blob_bytes"] == 3
        assert db.meter.values["committed_blob_bytes"] == 0
        db.execute("COMMIT")
        assert db.execute(
            "SELECT length(CAST(k AS BLOB)),length(body) FROM objects"
        ).fetchone() == (3, 3)
        assert db.meter.values["committed_text_utf8_bytes"] == 3
        assert db.meter.values["committed_blob_bytes"] == 3


def test_insert_or_ignore_attempted_vs_effective():
    with closing(connection()) as db:
        for _ in range(2):
            db.execute("INSERT OR IGNORE INTO objects VALUES (?,?)", ("a", b"123"))
        assert db.meter.values["attempted_blob_bytes"] == 6
        assert db.meter.values["effective_insert_rows"] == 1
        assert db.meter.values["committed_blob_bytes"] == 3
        assert db.execute("SELECT count(*) FROM objects").fetchone()[0] == 1


def test_rollback_and_retry_are_distinct():
    with closing(connection()) as db:
        db.execute("BEGIN")
        db.execute("INSERT INTO objects VALUES (?,?)", ("a", b"123"))
        db.execute("ROLLBACK")
        assert db.execute("SELECT count(*) FROM objects").fetchone()[0] == 0
        db.execute("BEGIN")
        db.execute("INSERT INTO objects VALUES (?,?)", ("a", b"123"))
        db.execute("COMMIT")
        assert db.meter.values["rolled_back_blob_bytes"] == 3
        assert db.meter.values["committed_blob_bytes"] == 3
        assert db.meter.values["attempted_blob_bytes"] == 6


def test_metadata_and_pin_text_not_object_content():
    with closing(connection()) as db:
        db.execute("CREATE TABLE pins(k TEXT, reason TEXT)")
        db.execute("INSERT INTO pins VALUES (?,?)", ("a" * 64, "accepted"))
        assert db.meter.values["attempted_text_utf8_bytes"] == 72
        assert db.meter.values["attempted_blob_bytes"] == 0


def test_unobserved_update_is_explicit_not_zero_cost():
    with closing(connection()) as db:
        db.execute("UPDATE objects SET body=? WHERE k=?", (b"abc", "a"))
        assert db.meter.values["unobserved_dml"] == 1


def test_actual_production_store_cache_and_write_boundary():
    context = canonical.Context(
        canonical.Namespace(*(["12345678-1234-4234-8234-123456789abc"] * 3)), "a" * 64
    )
    raw = json.dumps(
        {"kind": "index-empty", **context.fields(), "structural": 1, "count": "0"},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    c = Counters()
    with closing(
        sqlite3.connect(":memory:", factory=InsertConnection, isolation_level=None)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute(
            "CREATE TABLE sync_objects(hash TEXT PRIMARY KEY,kind TEXT,body BLOB)"
        )
        db.execute("CREATE TABLE sync_object_edges(parent TEXT,child TEXT)")
        store = Store(db, context)
        with observe_c1(c):
            obj = canonical.Object("index-empty", raw)
            db.execute("BEGIN")
            store.put(obj)
            store.put(obj)
            store.get(obj.ref(), {"index-empty"})
            db.execute("COMMIT")
        assert c.values["hash_calls"] == 1
        assert db.meter.values["insert_attempts"] == 1
        assert db.meter.values["committed_blob_bytes"] == len(raw)
        assert bytes(db.execute("SELECT body FROM sync_objects").fetchone()[0]) == raw
        observation = dict(c.values)
        observation.update(db.meter.values)
        (HERE / "evidence/backend-small-observed.json").write_text(
            json.dumps(
                {
                    "boundary": "실제 Object/Store의 단일 index-empty 생성·중복 put·cached get; 전층 grid 아님",
                    "canonical_bytes": len(raw),
                    "observed": observation,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )

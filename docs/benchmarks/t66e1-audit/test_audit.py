"""독립 E1 감사: 새 process와 직접 SQLite/hashlib oracle만 사용한다.

실행: .venv/bin/python -m pytest -q docs/benchmarks/t66e1-audit/test_audit.py
실패한 normative assertion은 감사 반례이며 implementation을 수정하지 않는다.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import sqlite3
import subprocess
import sys
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
FIXTURE = HERE / "server-fixture.json"
DATA = json.loads(FIXTURE.read_text())
DART = os.environ.get("DART", "/home/hjkerman/.flutter/bin/dart")
COMMAND = [DART, "--packages=" + str(ROOT / "mobile/.dart_tool/package_config.json"),
           str(HERE / "worker.dart")]
EMPTY = next(o for o in DATA["objects"] if o["kind"] == "index-empty")
RAW = next(o for o in DATA["objects"] if o["kind"] == "raw-root")
HOT = next(o for o in DATA["objects"] if o["kind"] == "hot")
STAGE = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def blob(item):
    return base64.b64decode(item["data_base64"])


def rehash(item, edit):
    body = json.loads(blob(item))
    edit(body)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode()
    return dict(item, ref=dict(hash=hashlib.sha256(
        b"money-note.sync.v1/" + body["kind"].encode() + b"\0" + raw).hexdigest(),
        bytes=str(len(raw))), data_base64=base64.b64encode(raw).decode())


class Harness:
    def __init__(self, directory):
        self.directory = directory
        self.root = directory / "private"

    def job(self, action, objects=(), **options):
        spec = dict(action=action, objects=list(objects), root=str(self.root),
                    fixture=str(FIXTURE), **options)
        path = self.directory / (str(uuid4()) + ".json")
        path.write_text(json.dumps(spec))
        return path

    def call(self, action, objects=(), **options):
        proc = subprocess.run(COMMAND + [str(self.job(action, objects, **options))],
                              capture_output=True, text=True, timeout=40, cwd=ROOT)
        assert proc.returncode == 0, proc.stderr[-3000:]
        result = json.loads(proc.stdout.splitlines()[-1])
        assert "unexpected" not in result, result
        return result

    def start(self, action, objects=(), **options):
        proc = subprocess.Popen(COMMAND + [str(self.job(action, objects, **options))],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, cwd=ROOT)
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        ready = selector.select(timeout=30)
        selector.close()
        assert ready, "Dart barrier timeout"
        line = proc.stdout.readline()
        value = json.loads(line)
        assert value.get("ready"), value
        return proc

    @staticmethod
    def finish(proc):
        stdout, stderr = proc.communicate("continue\n", timeout=40)
        assert proc.returncode == 0, stderr[-3000:]
        result = json.loads(stdout.splitlines()[-1])
        assert "unexpected" not in result, result
        return result

    def database(self):
        files = list(self.root.glob("segmented-store-v1/*.sqlite"))
        assert len(files) == 1
        return files[0]

    def sql(self, statements):
        with sqlite3.connect(self.database(), timeout=2) as connection:
            connection.executescript(statements)

    def rows(self, statement):
        with sqlite3.connect(self.database(), timeout=2) as connection:
            return connection.execute(statement).fetchall()

    def persisted(self, expected):
        with sqlite3.connect(self.database(), timeout=2) as connection:
            rows = connection.execute("SELECT hash,kind,body FROM objects").fetchall()
            actual = {h: bytes(raw) for h, _, raw in rows}
            assert actual == {o["ref"]["hash"]: blob(o) for o in expected}
            for identity, kind, raw in rows:
                assert hashlib.sha256(b"money-note.sync.v1/" + kind.encode()
                                      + b"\0" + raw).hexdigest() == identity
            assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
            count, payload = connection.execute("SELECT objects,payload FROM usage").fetchone()
            assert count == len(actual)
            assert payload == sum(map(len, actual.values()))
            connection.execute("BEGIN IMMEDIATE")
            connection.rollback()


@pytest.fixture
def audit(tmp_path):
    return Harness(tmp_path)


def test_server_c1_128_independent_vectors(audit):
    result = audit.call("canonical", vectors=DATA["vectors"])
    assert all(row["ok"] and row["bytes"] == source["expected"]
               and row["hash"] == source["hash"]
               for row, source in zip(result["results"], DATA["vectors"], strict=True))


@pytest.mark.parametrize("raw", [b'{"b":0,"a":0}', b'{"a":1,"a":2}',
    b'{"a":1,"\\u0061":2}', b'{"a":-0}', b'{"a":1e0}', b'{"a":1.0000000000000001}',
    b'{"a":-1e-400}', b'{"a":"\\ud800"}', b'\xff', b'{"a":9223372036854775808}',
    b'{"a":NaN}', b'[' * 129 + b'0' + b']' * 129])
def test_malformed_canonical_inputs(audit, raw):
    result = audit.call("canonical", vectors=[dict(raw=base64.b64encode(raw).decode())])
    assert not result["results"][0]["ok"]


def test_all_nine_server_object_kinds_and_hashes(audit):
    assert len({o["kind"] for o in DATA["objects"]}) == 9
    result = audit.call("verify", DATA["objects"])
    assert all(r["ok"] and r["bytes"] == o["data_base64"]
               for r, o in zip(result["results"], DATA["objects"], strict=True))


@pytest.mark.parametrize("damage", ["protocol", "lease", "timestamp", "unknown", "version",
                                   "engine", "revision", "ref_bytes", "chunk"])
def test_independent_malformed_manifest_rejected(audit, damage):
    value = json.loads(base64.b64decode(DATA["manifest_base64"]))
    target = value["target"]
    if damage == "protocol":
        value["protocol"] = True
    elif damage == "lease":
        value["expires_at"] = "2026-10-12T00:15:01Z"
    elif damage == "timestamp":
        value["validated_at"] = "2026-02-30T00:00:00Z"
    elif damage == "unknown":
        value["extra"] = "not permitted"
    elif damage == "version":
        target["versions"]["sync"] = 2
    elif damage == "engine":
        target["context"]["financial_engine"] = "0" * 64
    elif damage == "revision":
        target["revision"] = 1
    elif damage == "ref_bytes":
        target["raw_ref"]["bytes"] = 100
    else:
        value["inline_objects"] = [dict(ref=RAW["ref"], offset="0", length=1, data_base64="YQ==\n")]
    unsigned = {k: v for k, v in target.items() if k != "sync_root"}
    raw = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    target["sync_root"] = hashlib.sha256(b"money-note.sync.v1/view\0" + raw).hexdigest()
    result = audit.call("manifest", manifest_base64=base64.b64encode(json.dumps(value).encode()).decode())
    assert not result["ok"], result


@pytest.mark.parametrize("item", DATA["settings"], ids=lambda o: o["label"])
def test_every_server_admitted_money_string_is_accepted(audit, item):
    # 기대값을 Dart에서 만들지 않고 server Row.make/leaf의 exact bytes를 대조한다.
    result = audit.call("verify", [item])["results"][0]
    assert result["ok"], {"server_money_string": repr(item["money_string"]), "dart": result}
    assert result["bytes"] == item["data_base64"]


def test_server_rejected_bom_money_is_rejected(audit):
    sys.path.insert(0, str(ROOT / "backend"))
    from isolated_sync.canonical import CanonicalError
    from isolated_sync.raw import setting_money
    text = "\ufeff1000\ufeff"
    with pytest.raises(CanonicalError, match="REJECT_SETTING_MONEY"):
        setting_money(text)
    item = rehash(DATA["settings"][0], lambda b: b["rows"][0]["value"].update(value=text))
    result = audit.call("verify", [item])["results"][0]
    assert not result["ok"], "서버가 거부한 BOM 금액 문자열을 E1이 검증 성공으로 반환함"


def test_unicode_bytes_are_not_normalized(audit):
    assert audit.call("put", DATA["unicode_objects"])["ok"]
    audit.persisted(DATA["unicode_objects"])
    assert all(audit.call("read", [o])["results"] == [o["data_base64"]]
               for o in DATA["unicode_objects"])


def test_write_reopen_and_direct_payload_hash_oracle(audit):
    assert audit.call("put", DATA["objects"])["ok"]
    audit.persisted(DATA["objects"])
    result = audit.call("read", DATA["objects"])
    assert result["results"] == [o["data_base64"] for o in DATA["objects"]]


def test_duplicate_insert_is_idempotent(audit):
    for _ in range(2):
        assert audit.call("put", [RAW, RAW])["ok"]
    audit.persisted([RAW])


@pytest.mark.parametrize("mutation", ["conflict", "truncated", "version", "epoch", "unknown"])
def test_invalid_object_keeps_prior_committed_data(audit, mutation):
    assert audit.call("put", [EMPTY])["ok"]
    if mutation == "conflict":
        item = dict(RAW, data_base64=base64.b64encode(b"!" + blob(RAW)[1:]).decode())
    elif mutation == "truncated":
        item = dict(RAW, data_base64=base64.b64encode(blob(RAW)[:-1]).decode())
    else:
        def edit(body):
            if mutation == "version":
                body["canon"] = 2
            elif mutation == "epoch":
                body["ns"]["epoch"] = STAGE
            else:
                body["unexpected"] = True
        item = rehash(RAW, edit)
    assert not audit.call("put", [item])["ok"]
    audit.persisted([EMPTY])


@pytest.mark.parametrize("damage", ["body", "kind", "validator", "edge", "missing", "usage"])
def test_persisted_corruption_fails_closed(audit, damage):
    assert audit.call("put", [RAW])["ok"]
    statements = {
        "body": "DROP TRIGGER immutable_body; UPDATE objects SET body=zeroblob(length(body));",
        "kind": "DROP TRIGGER immutable_body; UPDATE objects SET kind='hot';",
        "validator": "DROP TRIGGER immutable_body; UPDATE objects SET validator='unknown';",
        "edge": "DELETE FROM edges WHERE position=0;",
        "missing": "DELETE FROM objects;",
        "usage": "UPDATE usage SET payload=0;",
    }
    audit.sql(statements[damage])
    assert not audit.call("read", [RAW])["ok"]


def test_missing_schema_trigger_is_rejected_before_writes(audit):
    assert audit.call("open")["ok"]
    audit.sql("DROP TRIGGER object_usage;")
    # 같은 8개 table/user_version/현재 usage만으로 schema를 수락하면 이후 quota가 무력화된다.
    result = audit.call("put", [EMPTY, HOT], limits=dict(objectCount=1))
    actual = audit.rows("SELECT count(*),sum(length(body)) FROM objects")
    counters = audit.rows("SELECT objects,payload FROM usage")
    assert not result["ok"] and actual[0][0] <= 1, {
        "expected_maximum": 1, "actual": actual, "usage": counters, "dart": result}


def test_unknown_schema_version_preserves_existing_data(audit):
    assert audit.call("put", [RAW])["ok"]
    audit.sql("PRAGMA user_version=99;")
    assert audit.call("open")["error"] == "UNSUPPORTED_STORAGE_SCHEMA"
    assert audit.rows("PRAGMA user_version") == [(99,)]
    audit.persisted([RAW])


def test_progress_requires_payload_and_never_activates(audit):
    assert audit.call("stage", id=STAGE)["state"] == "staged"
    assert audit.call("progress", [RAW], id=STAGE)["error"] == "OBJECT_MISSING"
    assert audit.call("put", [RAW])["ok"]
    assert audit.call("progress", [RAW, RAW], id=STAGE)["ok"]
    state = audit.call("load_stage", id=STAGE)
    assert state["stage"]["state"] == "staged" and state["stage"]["count"] == 1
    assert audit.rows("SELECT role FROM staging_roots ORDER BY role") == [
        ("control",), ("hot",), ("index",), ("raw",)]
    assert not audit.rows("SELECT name FROM sqlite_master WHERE name IN ('active','accepted','generations')")
    # RAW 하나는 전체 graph가 아니어도 개별 integrity만 검증되어 저장된다.
    assert audit.rows("SELECT count(*) FROM refs") [0][0] > 1
    audit.persisted([RAW])


def test_staging_checksum_corruption_is_rejected(audit):
    assert audit.call("stage", id=STAGE)["ok"]
    audit.sql("UPDATE staging SET checksum='" + "0" * 64 + "';")
    assert audit.call("load_stage", id=STAGE)["error"] == "STAGING_CORRUPT"


def test_staging_root_corruption_is_rejected(audit):
    assert audit.call("stage", id=STAGE)["ok"]
    audit.sql("UPDATE staging_roots SET role='internal' WHERE role='raw';")
    assert audit.call("load_stage", id=STAGE)["error"] == "STAGING_CORRUPT"


def test_orphan_file_is_never_accepted_or_removed(audit):
    assert audit.call("open")["ok"]
    orphan = audit.database().parent / "unknown.pending"
    orphan.write_bytes(b"synthetic incomplete object")
    assert audit.call("health")["healthy"]
    assert audit.call("read", [RAW])["results"] == [None]
    assert orphan.read_bytes() == b"synthetic incomplete object"


@pytest.mark.parametrize("action,point,committed", [
    ("put", "after_edges_insert", False), ("put", "after_commit", True),
    ("stage", "after_staging_insert", False), ("stage", "after_commit", True),
    ("progress", "after_progress_insert", False), ("progress", "after_commit", True),
    ("cleanup", "before_commit", False), ("cleanup", "after_commit", True),
])
def test_real_sigkill_boundaries_with_fresh_process(audit, action, point, committed):
    assert audit.call("put", [EMPTY])["ok"]
    if action in ("progress", "cleanup"):
        assert audit.call("stage", id=STAGE)["ok"]
        if action == "cleanup":
            assert audit.call("progress", [EMPTY], id=STAGE)["ok"]
    proc = audit.start(action, [HOT] if action == "put" else [EMPTY], id=STAGE, kill_at=point)
    proc.send_signal(signal.SIGKILL)
    proc.communicate(timeout=10)
    assert proc.returncode == -signal.SIGKILL
    expected = [EMPTY, HOT] if action == "put" and committed else [EMPTY]
    audit.persisted(expected)
    assert audit.call("health")["healthy"]
    stages = audit.rows("SELECT count(*) FROM staging")[0][0]
    progress = audit.rows("SELECT count(*) FROM staging_objects")[0][0]
    if action == "stage":
        assert stages == int(committed)
    if action == "progress":
        assert stages == 1 and progress == int(committed)
    if action == "cleanup":
        assert stages == progress == int(not committed)
    assert audit.call("put", [RAW])["ok"]


def test_four_concurrent_identical_writers(audit):
    assert audit.call("open")["ok"]
    workers = [audit.start("put", [RAW], barrier=True) for _ in range(4)]
    for worker in workers:
        worker.stdin.write("continue\n")
        worker.stdin.flush()
    results = [audit.finish(worker) for worker in workers]
    assert all(row["ok"] for row in results), results
    audit.persisted([RAW])


def test_concurrent_conflicting_writers_cannot_replace_payload(audit):
    assert audit.call("open")["ok"]
    bad = dict(RAW, data_base64=base64.b64encode(b"!" + blob(RAW)[1:]).decode())
    workers = [audit.start("put", [item], barrier=True) for item in [RAW, bad, RAW, bad]]
    for worker in workers:
        worker.stdin.write("continue\n")
        worker.stdin.flush()
    results = [audit.finish(worker) for worker in workers]
    assert [r["ok"] for r in results] == [True, False, True, False]
    audit.persisted([RAW])


def test_reader_does_not_see_uncommitted_payload(audit):
    assert audit.call("put", [EMPTY])["ok"]
    reader = audit.start("read", [EMPTY, RAW], barrier=True)
    writer = audit.start("put", [RAW], kill_at="after_edges_insert")
    result = audit.finish(reader)
    assert result["results"] == [EMPTY["data_base64"], None]
    assert audit.finish(writer)["ok"]
    audit.persisted([EMPTY, RAW])


def test_busy_error_then_recovery_keeps_good_data(audit):
    assert audit.call("put", [EMPTY])["ok"]
    with sqlite3.connect(audit.database()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert audit.call("put", [RAW], limits=dict(busyMilliseconds=50))["error"] == "STORE_BUSY"
        connection.rollback()
    assert audit.call("put", [RAW])["ok"]
    audit.persisted([EMPTY, RAW])


def test_object_and_metadata_budgets_rollback_atomically(audit):
    assert audit.call("put", [EMPTY])["ok"]
    assert audit.call("put", [HOT], limits=dict(objectCount=1))["error"] == "LOCAL_STORAGE_BUDGET"
    assert audit.call("stage", id=STAGE, limits=dict(manifestBytes=128, metadataBytes=1024))["error"] == "LOCAL_METADATA_BUDGET"
    audit.persisted([EMPTY])


def test_payload_budget_is_distinct_from_chunk_limit(audit):
    assert audit.call("put", [EMPTY])["ok"]
    assert audit.call("put", [RAW], limits=dict(objectBytes=256))["error"] == "LOCAL_OBJECT_BUDGET"
    audit.persisted([EMPTY])
    def enlarge(body):
        body["rows"][0]["value"]["value"] = "가" * 400000
        body["oversized"] = True
    large = rehash(DATA["unicode_objects"][0], enlarge)
    assert len(blob(large)) > 1048576
    assert audit.call("put", [large])["ok"]
    audit.persisted([EMPTY, large])


def test_real_sqlite_full_does_not_damage_previous_object(audit):
    assert audit.call("put", [EMPTY], limits=dict(databasePages=64))["ok"]
    template = DATA["unicode_objects"][0]
    def enlarge(body):
        body["rows"][0]["value"]["value"] = "a" * 400000
        body["oversized"] = True
    large = rehash(template, enlarge)
    result = audit.call("put", [large], limits=dict(databasePages=64))
    assert result["error"] == "PERSISTENCE_FAILED" and result["storageCode"] == 13, result
    audit.persisted([EMPTY])


def test_staging_cleanup_preserves_objects_and_recovers_quota(audit):
    assert audit.call("put", [RAW])["ok"]
    assert audit.call("stage", id=STAGE, limits=dict(stagingCount=1))["ok"]
    assert audit.call("progress", [RAW], id=STAGE)["ok"]
    assert audit.call("cleanup", id=STAGE)["removed"]
    assert not audit.call("cleanup", id=STAGE)["removed"]
    assert audit.call("stage", id=str(uuid4()), limits=dict(stagingCount=1))["ok"]
    audit.persisted([RAW])


def test_namespace_separation_and_offline_files_unchanged(audit):
    # 별도 소유 디렉터리의 기존 opaque baseline/J/Snapshot bytes에 E1이 접근하지 않는지 검증한다.
    originals = {"offline-mode/baseline.json": b'{"schema_version":4,"synthetic":true}',
                 "offline-mode/journal.ndjson": b'{"synthetic":"frozen J"}\n',
                 "snapshots/synthetic.json": b'{"format_version":7,"synthetic":true}'}
    for name, raw in originals.items():
        path = audit.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    assert audit.call("put", [RAW, HOT])["ok"]
    assert audit.call("stage", id=STAGE)["ok"]
    assert audit.call("cleanup", id=STAGE)["ok"]
    assert all((audit.root / name).read_bytes() == raw for name, raw in originals.items())


def test_normal_runtime_has_no_segmented_imports_or_server_diff():
    for path in (ROOT / "mobile/lib").rglob("*.dart"):
        if "segmented" not in path.parts:
            assert "segmented/" not in path.read_text(), str(path)
    changed = subprocess.check_output(["git", "diff", "--name-only", "9ee495e", "141e011"],
                                      text=True, cwd=ROOT).splitlines()
    assert not any(p.startswith("backend/") for p in changed)
    assert not any(p.startswith("mobile/lib/") and "/segmented/" not in p for p in changed)

"""독립 targeted 재감사: long-lived Dart handle와 fresh Python SQLite oracle."""

import base64
from contextlib import closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = Path(os.environ.get("E1_REAUDIT_OUTPUT", "/tmp/mn-e1-a01-a02-reaudit"))
OUT.mkdir(parents=True, exist_ok=True)
FIXTURE = ROOT / "mobile/test/fixtures/segmented_server_golden.json"
DATA = json.loads(FIXTURE.read_text())
OBJECTS = {o["kind"]: o for o in DATA["objects"]}
COMMAND = [os.environ.get("DART", "/home/hjkerman/.flutter/bin/dart"),
           "--packages=" + str(ROOT / "mobile/.dart_tool/package_config.json"), str(HERE / "session_worker.dart")]
TRIGGERS = ["object_usage", "refs_usage", "refs_release", "edge_usage", "staging_usage", "staging_release",
            "root_usage", "root_release", "progress_usage", "progress_release", "immutable_body"]


def json_value(value):
    if isinstance(value, bytes):
        return dict(base64=base64.b64encode(value).decode())
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    if isinstance(value, dict):
        return {k: json_value(v) for k, v in value.items()}
    return value


def evidence(name, **values):
    directory = OUT / "new-cases"
    directory.mkdir(exist_ok=True)
    (directory / (name + ".json")).write_text(json.dumps(json_value(values), ensure_ascii=False, indent=2)+"\n")


class Session:
    def __init__(self, root, **options):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        job = root / "job.json"
        job.write_text(json.dumps(dict(root=str(root / "private"), fixture=str(FIXTURE), **options)))
        self.process = subprocess.Popen(COMMAND + [str(job)], cwd=ROOT, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        self.opened = self.receive()
        self.path = self.opened.get("path")

    def receive(self):
        selector = selectors.DefaultSelector()
        selector.register(self.process.stdout, selectors.EVENT_READ)
        ready = selector.select(timeout=120)
        selector.close()
        assert ready, "Dart protocol deadline"
        line = self.process.stdout.readline()
        assert line, self.process.stderr.read()[-3000:]
        return json.loads(line)

    def send(self, action, **options):
        self.process.stdin.write(json.dumps(dict(action=action, **options))+"\n")
        self.process.stdin.flush()

    def call(self, action, **options):
        self.send(action, **options)
        return self.receive()

    def resume(self, abort=False):
        self.process.stdin.write("abort\n" if abort else "resume\n")
        self.process.stdin.flush()
        return self.receive()

    def close(self):
        if self.process.poll() is None and self.opened.get("event") == "opened":
            assert self.call("close")["ok"]
        _, stderr = self.process.communicate(timeout=15)
        assert self.process.returncode == 0, stderr[-3000:]

    def connect(self):
        return sqlite3.connect(self.path, timeout=0)

    def change(self, sql):
        with closing(self.connect()) as conn:
            conn.executescript(sql)

    def snapshot(self):
        with closing(self.connect()) as conn:
            names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {name: conn.execute('SELECT * FROM "' + name + '" ORDER BY 1,2').fetchall() for name in names}

    def definition(self, name):
        with closing(self.connect()) as conn:
            return conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()[0]

    def persisted(self, expected):
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT hash,kind,body FROM objects ORDER BY hash").fetchall()
            assert {r[0]: r[2] for r in rows} == {o["ref"]["hash"]: base64.b64decode(o["data_base64"]) for o in expected}
            for identity, kind, raw in rows:
                assert hashlib.sha256(b"money-note.sync.v1/" + kind.encode() + b"\0" + raw).hexdigest() == identity
            assert conn.execute("SELECT objects,payload FROM usage").fetchone() == (len(rows), sum(len(r[2]) for r in rows))
            assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
            conn.execute("BEGIN IMMEDIATE")
            conn.rollback()


@pytest.fixture
def session(tmp_path):
    s = Session(tmp_path)
    assert s.opened["event"] == "opened", s.opened
    yield s
    s.close()


def schema_error(result):
    assert result == dict(ok=False, error="STORE_SCHEMA_CORRUPT", sqlite_code=None), result


def test_independent_monetary_differential_and_persisted_bytes(tmp_path):
    spec = importlib.util.spec_from_file_location("reaudit_money", HERE / "make_corpus.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    corpus = module.build()
    path = OUT / "money-corpus.json"
    path.write_text(json.dumps(corpus, ensure_ascii=True, separators=(",", ":")))
    s = Session(tmp_path, count=100000, seed=False)
    try:
        result = s.call("money", corpus=str(path))
        assert result["ok"]
        mismatches = []
        accepted = {}
        for source, actual in zip(corpus["cases"], result["results"], strict=True):
            if source["accepted"] != actual["accepted"] or (source["accepted"] and (
                    not actual["preserved"] or actual["hash"] != source["ref"]["hash"])):
                mismatches.append(dict(source=source, actual=actual))
            if source["accepted"]:
                accepted[source["ref"]["hash"]] = source
        s.persisted(accepted.values())
        with closing(s.connect()) as conn:
            for identity, raw in conn.execute("SELECT hash,body FROM objects"):
                source = accepted[identity]
                assert json.loads(raw)["rows"][0]["value"]["value"] == source["value"]
        evidence("money-differential", total=len(corpus["cases"]), reported=165,
                 additional=corpus["additional_count"], accepted=sum(c["accepted"] for c in corpus["cases"]),
                 rejected=sum(not c["accepted"] for c in corpus["cases"]), whitespace=corpus["whitespace"],
                 boundary_codepoints=corpus["boundary_codepoints"], unique_committed_objects=len(accepted),
                 corpus_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), mismatches=mismatches,
                 sqlite=s.opened["sqlite"])
        assert not mismatches, mismatches[:5]
    finally:
        s.close()
    # 별도 process의 open/health가 committed metadata와 payload를 다시 검증한다.
    recovered = Session(tmp_path, count=100000, seed=False)
    try:
        assert recovered.call("health")["healthy"]
    finally:
        recovered.close()


@pytest.mark.parametrize("trigger", TRIGGERS)
def test_changed_condition_for_each_mandatory_trigger(session, trigger):
    before = session.snapshot()
    original = session.definition(trigger)
    changed = original.replace(" BEGIN", " WHEN 0 BEGIN", 1)
    session.change("DROP TRIGGER " + trigger + ";" + changed + ";")
    schema_error(session.call("duplicate"))
    schema_error(session.call("cleanup"))
    assert session.snapshot() == before
    assert not session.call("health")["healthy"]
    assert session.call("read")["data_base64"] == OBJECTS["index-empty"]["data_base64"]
    session.persisted([OBJECTS["index-empty"]])
    evidence("condition-" + trigger, expected="쓰기 전 거부 및 기존 전체 행 보존",
             observed="duplicate/cleanup 거부, read 정상, 전체 행 동일", original=original, changed=changed)


@pytest.mark.parametrize("action", ["put", "duplicate", "stage", "progress", "cleanup"])
def test_late_schema_replacement_protects_every_mutator(session, action):
    # 성공한 선행 write와 schema 변경 사이에 handle을 닫지 않는다.
    assert session.call("duplicate")["ok"]
    before = session.snapshot()
    session.change("DROP TRIGGER object_usage;")
    schema_error(session.call(action))
    assert session.snapshot() == before
    session.persisted([OBJECTS["index-empty"]])
    evidence("mutator-" + action, expected="schema 재검증 후 거부", observed="STORE_SCHEMA_CORRUPT",
             committed_objects=1, unauthorized_additional_committed_objects=0)


def test_original_one_object_then_trigger_drop_and_reopen(session, tmp_path):
    before = session.snapshot()
    session.change("DROP TRIGGER object_usage;")
    result = session.call("put")
    schema_error(result)
    session.persisted([OBJECTS["index-empty"]])
    assert session.snapshot() == before
    assert not session.call("health")["healthy"]
    session.close()
    reopened = Session(tmp_path, seed=False)
    assert reopened.opened == dict(ok=False, error="STORE_SCHEMA_CORRUPT")
    reopened.close()
    session.persisted([OBJECTS["index-empty"]])
    evidence("original-one-object", configured_limit=1, committed_before=1, committed_after=1,
             unauthorized_additional_committed_objects=0, insertion=result, reopen=reopened.opened)


@pytest.mark.parametrize("kind", ["format", "extra-view", "extra-index", "missing-index", "altered-table"])
def test_closed_schema_identity_policy(session, kind):
    before = session.snapshot()
    if kind == "format":
        sql = session.definition("object_usage").replace(" BEGIN ", "\nBEGIN\n")
        session.change("DROP TRIGGER object_usage;" + sql + ";")
    elif kind == "extra-view":
        session.change("CREATE VIEW audit_view AS SELECT hash FROM objects;")
    elif kind == "extra-index":
        session.change("CREATE INDEX audit_index ON objects(kind);")
    elif kind == "missing-index":
        session.change("DROP INDEX edge_children;")
    else:
        session.change("ALTER TABLE refs ADD COLUMN audit_column TEXT;")
    schema_error(session.call("duplicate"))
    if kind != "altered-table":
        assert session.snapshot() == before
    session.persisted([OBJECTS["index-empty"]])
    evidence("closed-schema-" + kind, expected="문서화된 exact schema 정책에 따른 거부", observed="STORE_SCHEMA_CORRUPT")


@pytest.mark.parametrize("action,point", [("put", "before_object_insert"), ("put", "after_object_insert"),
    ("put", "after_edges_insert"), ("put", "before_commit"), ("duplicate", "before_commit"),
    ("stage", "after_staging_insert"), ("progress", "after_progress_insert"), ("cleanup", "before_commit")])
def test_ddl_cannot_commit_between_validation_and_commit(tmp_path, action, point):
    s = Session(tmp_path, count=2)
    try:
        s.send(action, pause_at=point)
        assert s.receive() == dict(event="barrier", point=point)
        with closing(s.connect()) as conn:
            with pytest.raises(sqlite3.OperationalError) as blocked:
                conn.execute("DROP TRIGGER object_usage")
            assert blocked.value.sqlite_errorcode == sqlite3.SQLITE_BUSY
        assert s.resume()["ok"]
        expected = [OBJECTS["index-empty"], OBJECTS["raw-root"]] if action == "put" else [OBJECTS["index-empty"]]
        s.persisted(expected)
        s.change("DROP TRIGGER object_usage;")
        schema_error(s.call("duplicate"))
        s.persisted(expected)
        evidence("commit-fence-" + action + "-" + point, ddl_during_transaction="SQLITE_BUSY(5)",
                 protected_operation="COMMIT", ddl_after_commit="성공", following_write="STORE_SCHEMA_CORRUPT",
                 actual_objects=len(expected), unauthorized_additional_committed_objects=0)
    finally:
        s.close()


@pytest.mark.parametrize("finish", ["ROLLBACK", "COMMIT"])
def test_schema_writer_before_begin_blocks_admission(session, finish):
    before = session.snapshot()
    with closing(session.connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DROP TRIGGER object_usage")
        assert session.call("duplicate")["error"] == "STORE_BUSY"
        conn.execute(finish)
    if finish == "ROLLBACK":
        assert session.call("duplicate")["ok"]
    else:
        schema_error(session.call("duplicate"))
    assert session.snapshot() == before
    evidence("ddl-before-begin-" + finish, expected="write lock 경합 시 미변경, DDL 종료 뒤 재검증",
             observed="STORE_BUSY 이후 " + ("정상 재시도" if finish == "ROLLBACK" else "schema 거부"))


def test_shared_reader_blocks_commit_and_retry_is_atomic(tmp_path):
    s = Session(tmp_path, count=2)
    try:
        before = s.snapshot()
        reader = s.connect()
        reader.execute("BEGIN")
        reader.execute("SELECT * FROM objects").fetchall()
        s.send("put", pause_at="before_commit")
        assert s.receive()["event"] == "barrier"
        result = s.resume()
        assert result["error"] == "STORE_BUSY", result
        reader.rollback()
        reader.close()
        assert s.snapshot() == before
        s.persisted([OBJECTS["index-empty"]])
        assert s.call("put")["ok"]
        s.persisted([OBJECTS["index-empty"], OBJECTS["raw-root"]])
        evidence("commit-busy-retry", first=result, actual_objects_after_failed_commit=1,
                 actual_objects_after_valid_retry=2, partial_commit=False)
    finally:
        s.close()


def test_exact_schema_restore_requires_no_implementation_repair(session):
    before = session.snapshot()
    sql = session.definition("object_usage")
    session.change("DROP TRIGGER object_usage;")
    schema_error(session.call("put"))
    assert session.definition("refs_usage")
    # 합성 fixture를 감사자가 원래 DDL로 복원한다. 제품의 자동 repair가 아니다.
    session.change(sql + ";")
    assert session.call("duplicate")["ok"]
    assert session.call("put")["error"] == "LOCAL_STORAGE_BUDGET"
    assert session.snapshot() == before
    evidence("exact-restore", before_failure="STORE_SCHEMA_CORRUPT", restored_duplicate="성공",
             restored_second_object="LOCAL_STORAGE_BUDGET", committed_objects=1)


def test_cached_connection_revalidates_after_repeated_success(session):
    for _ in range(4):
        assert session.call("duplicate")["ok"]
    before = session.snapshot()
    sql = session.definition("object_usage").replace("objects=objects+1", "objects=objects-1")
    session.change("DROP TRIGGER object_usage;" + sql + ";")
    for _ in range(3):
        schema_error(session.call("duplicate"))
    assert session.snapshot() == before
    evidence("reused-connection", previous_valid_writes=4, subsequent_rejections=3, committed_objects=1)


def test_object_payload_corruption_detected_with_exact_schema_intact(session):
    sql = session.definition("immutable_body")
    session.change("DROP TRIGGER immutable_body; UPDATE objects SET body=zeroblob(length(body));" + sql + ";")
    result = session.call("read")
    assert not result["ok"] and result["error"] != "STORE_SCHEMA_CORRUPT"
    assert not session.call("health")["healthy"]
    evidence("payload-with-intact-schema", read=result, schema_definition_restored=True)


def test_bounded_schema_check_benchmark(tmp_path):
    corpus_path = OUT / "money-corpus.json"
    if not corpus_path.exists():
        spec = importlib.util.spec_from_file_location("reaudit_money_benchmark", HERE / "make_corpus.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        corpus_path.write_text(json.dumps(module.build(), ensure_ascii=True, separators=(",", ":")))
    s = Session(tmp_path, count=100000)
    try:
        result = s.call("benchmark", corpus=str(corpus_path))
        assert result["ok"] and result["catalog_definitions"] == 20
        assert len(result["insert_us"]) == len(result["duplicate_put_us"]) == 200
        (OUT / "performance.json").write_text(json.dumps(result, indent=2)+"\n")
        evidence("performance", samples_per_cell=200, cells=4, catalog_definitions=20,
                 schema_queries_per_transaction=2)
    finally:
        s.close()

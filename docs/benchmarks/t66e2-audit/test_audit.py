"""실제 서버 fixture, 외부 HTTP trace와 fresh SQLite로 E2를 독립 감사한다."""

import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import sqlite3
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = Path(os.environ.get("E2_AUDIT_OUTPUT", "/tmp/mn-e2-audit"))
OUT.mkdir(parents=True, exist_ok=True)
DART = os.environ.get("DART", "/home/hjkerman/.flutter/bin/dart")
COMMAND = [
    DART,
    "--packages=" + str(ROOT / "mobile/.dart_tool/package_config.json"),
    str(HERE / "worker.dart"),
]


def canonical(v):
    return json.dumps(
        v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def digest(kind, raw):
    return hashlib.sha256(
        b"money-note.sync.v1/" + kind.encode() + b"\0" + raw
    ).hexdigest()


def save(name, **values):
    p = OUT / "cases"
    p.mkdir(exist_ok=True)
    (p / (name + ".json")).write_text(
        json.dumps(dict(scenario=name, **values), ensure_ascii=False, indent=2) + "\n"
    )


def server_fixture():
    process = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), str(HERE / "audit_backend.py")],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    line = process.stdout.readline()
    assert line, process.stderr.read()[-3000:]
    first = json.loads(line)
    _, error = process.communicate('{"command":"exit"}\n', timeout=15)
    assert process.returncode == 0, error[-3000:]
    return first["fixture"]


@pytest.fixture(scope="session")
def fixture(tmp_path_factory):
    value = server_fixture()
    p = tmp_path_factory.mktemp("e2-independent-server") / "fixture.json"
    p.write_text(json.dumps(value))
    return value, p


def start(tmp_path, fixture, plan, **options):
    _, path = fixture
    job = tmp_path / (plan + ".json")
    job.write_text(
        json.dumps(
            dict(
                plan=plan,
                root=str(tmp_path / "private"),
                fixture=str(path),
                repo=str(ROOT),
                **options,
            )
        )
    )
    return subprocess.Popen(
        COMMAND + [str(job)],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def run(tmp_path, fixture, plan, **options):
    process = start(tmp_path, fixture, plan, **options)
    out, error = process.communicate(timeout=300)
    assert process.returncode == 0, error[-3500:]
    return json.loads(out)


def persisted(path, expected=None, allow_corrupt=False):
    with closing(sqlite3.connect(path, timeout=0)) as conn:
        rows = conn.execute("SELECT hash,kind,body FROM objects").fetchall()
        raw = {h: bytes(b) for h, _, b in rows}
        corrupt = []
        for h, kind, b in rows:
            if digest(kind, b) != h:
                corrupt.append(h)
        assert not corrupt or allow_corrupt
        assert conn.execute("SELECT objects,payload FROM usage").fetchone() == (
            len(rows),
            sum(len(b) for b in raw.values()),
        )
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert (
            conn.execute(
                "SELECT name FROM sqlite_master WHERE name LIKE '%active%' OR name LIKE '%accepted%'"
            ).fetchall()
            == []
        )
        states = conn.execute(
            "SELECT staging_id,state,error_code FROM acquisition ORDER BY staging_id"
        ).fetchall()
        if expected is not None:
            for o in expected["objects"]:
                assert raw[o["ref"]["hash"]] == base64.b64decode(o["data_base64"])
        conn.execute("BEGIN IMMEDIATE")
        conn.rollback()
        return dict(
            objects=len(rows), hashes=sorted(raw), states=states, corrupt=corrupt
        )


def closure(result, expected):
    assert result["ok"], result
    refs = {o["ref"]["hash"]: o for o in expected["objects"]}
    assert {o["hash"] for o in result["graph"]} == set(refs)
    assert result["target"] == expected["manifest"]["target"]
    state = persisted(result["path"], expected)
    with closing(sqlite3.connect(result["path"])) as conn:
        staged = {
            r[0]
            for r in conn.execute(
                "SELECT hash FROM staging_objects WHERE staging_id=?",
                (result["stage"],),
            )
        }
        assert staged == set(refs)
        assert conn.execute(
            "SELECT state,error_code FROM acquisition WHERE staging_id=?",
            (result["stage"],),
        ).fetchone() == ("graph_verified", None)
        manifest = conn.execute(
            "SELECT manifest FROM staging WHERE id=?", (result["stage"],)
        ).fetchone()[0]
        assert json.loads(manifest) == result["manifest"]
        checksum = conn.execute(
            "SELECT checksum FROM staging WHERE id=?", (result["stage"],)
        ).fetchone()[0]
        assert hashlib.sha256(manifest).hexdigest() == checksum
    return state


def observations(trace):
    return [
        r
        for r in trace
        if r["method"] == "POST" and r["path"].endswith("/observations")
    ]


def requests(trace):
    return [r for r in trace if r["path"].endswith("/objects")]


@pytest.mark.parametrize(
    "plan",
    [
        "cold",
        "chunked",
        "retry-reset",
        "retry-timeout",
        "retry-503",
        "expiry-manifest",
        "expiry-transfer",
        "expiry-terminal",
    ],
)
def test_authorized_closure_and_lifecycle(tmp_path, fixture, plan):
    expected, _ = fixture
    result = run(tmp_path, fixture, plan)
    state = closure(result | {"path": result["path"]}, expected)
    trace = result["trace"]
    objects = requests(trace)
    assert all(r["authorization_matches"] for r in trace)
    assert {r["request"]["items"][0]["path"][-1] for r in objects} == set(
        state["hashes"]
    )
    assert result["http"]["max_active_sends"] <= 1
    if plan == "cold":
        assert len(objects) == len(expected["objects"])
        assert len(observations(trace)) == 2
        assert sum(r["request"]["items"][0]["length"] for r in objects) == sum(
            int(o["ref"]["bytes"]) for o in expected["objects"]
        )
    if plan.startswith("retry-"):
        initial = observations(trace)[:3]
        assert (
            len(initial) == 3 and len({canonical(r["request"]) for r in initial}) == 1
        )
    if plan.startswith("expiry-"):
        assert len({r["request"]["request_id"] for r in observations(trace)}) >= 2
    save(
        plan,
        expected="인증된 단일 graph의 전체 바이트와 closure 및 제한된 재시도",
        observed="정확한 graph·staging·SQLite 및 HTTP trace 일치",
        verdict="PASS",
        http=result["http"],
        graph_objects=len(result["graph"]),
        persisted=state,
        trace=trace,
    )


@pytest.mark.parametrize(
    "plan",
    [
        "manifest-protocol",
        "manifest-nonce",
        "manifest-id",
        "manifest-root",
        "manifest-lease",
        "manifest-extra",
        "manifest-inline",
        "terminal-change",
        "transfer-protocol",
        "transfer-nonce",
        "transfer-observation",
        "transfer-ref",
        "transfer-offset",
        "transfer-length",
        "transfer-base64",
        "transfer-bitflip",
        "transfer-json-truncated",
        "transfer-oversized",
        "http-truncated",
        "permanent-401",
        "permanent-422",
        "missing-descendant",
        "retry-exhaust",
        "credential-switch",
        "cancel-before-response",
        "cancel-midstream",
        "cancel-progress",
        "cancel-before",
        "storage-count",
        "storage-full",
        "graph-budget",
        "edge-budget",
        "depth-budget",
        "schema-trigger",
    ],
)
def test_protocol_resource_and_cancellation_fail_closed(tmp_path, fixture, plan):
    result = run(tmp_path, fixture, plan)
    assert not result["ok"], result
    # 검증 대상 단계의 정확한 오류를 요구한다. 무관한 fixture 실패는 PASS가 아니다.
    expected_codes = {
        "manifest-protocol": "MANIFEST_INVALID",
        "manifest-nonce": "MANIFEST_BINDING_INVALID",
        "manifest-id": "UUID_INVALID",
        "manifest-root": "TARGET_HASH_INVALID",
        "manifest-lease": "LEASE_INVALID",
        "manifest-extra": "SHAPE_INVALID",
        "manifest-inline": "SHAPE_INVALID",
        "terminal-change": "IMMUTABLE_MANIFEST_CHANGED",
        "transfer-protocol": "TRANSFER_BINDING_INVALID",
        "transfer-nonce": "TRANSFER_BINDING_INVALID",
        "transfer-observation": "TRANSFER_BINDING_INVALID",
        "transfer-ref": "CHUNK_BINDING_INVALID",
        "transfer-offset": "CHUNK_INVALID",
        "transfer-length": "CHUNK_INVALID",
        "transfer-base64": "CHUNK_INVALID",
        "transfer-bitflip": "OBJECT_HASH_INVALID",
        "transfer-json-truncated": "REPRESENTATION_INVALID",
        "transfer-oversized": "RESPONSE_SIZE_EXCEEDED",
        "http-truncated": "RESPONSE_TRUNCATED",
        "permanent-401": "AUTH_REQUIRED",
        "permanent-422": "INVALID_REQUEST",
        "missing-descendant": "OBSERVATION_INCOMPLETE",
        "retry-exhaust": "TRANSPORT_UNAVAILABLE",
        "credential-switch": "AUTHENTICATION_CHANGED",
        "cancel-before-response": "ACQUISITION_CANCELLED",
        "cancel-midstream": "ACQUISITION_CANCELLED",
        "cancel-progress": "ACQUISITION_CANCELLED",
        "cancel-before": "ACQUISITION_CANCELLED",
        "storage-count": "GRAPH_OBJECT_BUDGET",
        "storage-full": "PERSISTENCE_FAILED",
        "graph-budget": "GRAPH_OBJECT_BUDGET",
        "edge-budget": "GRAPH_EDGE_BUDGET",
        "depth-budget": "GRAPH_DEPTH_BUDGET",
        "schema-trigger": "STORE_SCHEMA_CORRUPT",
    }
    assert result["error"] == expected_codes[plan]
    state = persisted(result["path"])
    assert all(s[1] != "graph_verified" for s in state["states"]), state
    trace = result["trace"]
    if plan in [
        "manifest-protocol",
        "manifest-nonce",
        "manifest-id",
        "manifest-root",
        "manifest-lease",
        "manifest-extra",
        "manifest-inline",
        "permanent-401",
        "permanent-422",
        "retry-exhaust",
        "cancel-before",
    ]:
        assert not requests(trace)
        assert state["objects"] == 0
    if plan in ["permanent-401", "permanent-422"]:
        assert len(observations(trace)) == 1
    if plan == "retry-exhaust":
        assert len(observations(trace)) == 3
    if plan == "missing-descendant":
        assert len(observations(trace)) == 3
    if plan == "storage-count":
        assert state["objects"] == 1
    if plan == "cancel-progress":
        assert state["objects"] == 1
    if plan == "cancel-midstream":
        assert state["objects"] == 0
    save(
        plan,
        expected="실패를 명시하고 불완전 후보를 완료로 게시하지 않음",
        observed=result["error"],
        verdict="PASS",
        error=result["error"],
        action=result["action"],
        http=result["http"],
        persisted=state,
        trace=trace,
    )


def variant(original, change):
    value = json.loads(json.dumps(original))
    objects = {o["ref"]["hash"]: o for o in value["objects"]}
    edited = False
    new = {}
    remap = {}

    def visit(ref):
        nonlocal edited
        if ref["hash"] in remap:
            return remap[ref["hash"]]
        body = json.loads(base64.b64decode(objects[ref["hash"]]["data_base64"]))
        kind = body["kind"]
        if kind == "raw-root":
            for t in body["tables"]:
                t["root"]["ref"] = visit(t["root"]["ref"])
        elif kind == "snapshot-node":
            for d in body["children"]:
                d["ref"] = visit(d["ref"])
        elif kind == "index-root":
            body["facts"] = visit(body["facts"])
        elif kind == "index-node":
            for side in ["left", "right"]:
                body[side] = visit(body[side])
        if not edited and (
            (
                change in ["version", "context", "noncanonical", "descriptor"]
                and kind == "raw-root"
            )
            or (change == "index-count" and kind == "index-root")
            or (change == "patricia" and kind == "index-node")
            or (change == "hot-context" and kind == "hot")
        ):
            edited = True
            if change == "version":
                body["canon"] = 2
            if change == "context":
                body["ns"]["epoch"] = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
            if change == "descriptor":
                body["tables"][0]["count"] = str(int(body["tables"][0]["count"]) + 1)
                body["tables"][0]["root"]["count"] = body["tables"][0]["count"]
            if change == "index-count":
                body["count"] = str(int(body["count"]) + 1)
            if change == "patricia":
                body["prefix"] = "1" if body["prefix"] != "1" else "0"
            if change == "hot-context":
                body["context"]["evaluation_date"] = "2026-10-06"
        raw = (
            json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode()
            if change == "noncanonical" and kind == "raw-root"
            else canonical(body)
        )
        reference = dict(hash=digest(kind, raw), bytes=str(len(raw)))
        new[reference["hash"]] = dict(
            ref=reference, kind=kind, data_base64=base64.b64encode(raw).decode()
        )
        remap[ref["hash"]] = reference
        return reference

    target = value["manifest"]["target"]
    if change == "wrong-type":
        target["raw_ref"] = target["index_ref"]
    elif change.startswith("manifest-context-"):
        field = change.removeprefix("manifest-context-")
        if field == "principal":
            target["principal_id"] = 2
        else:
            target["ns"][field] = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    else:
        for role in ["raw", "index", "hot", "control"]:
            target[role + "_ref"] = visit(target[role + "_ref"])
        value["objects"] = list(new.values())
    preimage = {k: v for k, v in target.items() if k != "sync_root"}
    target["sync_root"] = digest("view", canonical(preimage))
    return value


@pytest.mark.parametrize(
    "change",
    [
        "wrong-type",
        "version",
        "context",
        "noncanonical",
        "descriptor",
        "index-count",
        "patricia",
        "hot-context",
        "manifest-context-principal",
        "manifest-context-dataset_id",
        "manifest-context-epoch",
    ],
)
def test_independently_rehashed_invalid_graph(tmp_path, fixture, change):
    original, original_path = fixture
    v = variant(original, change)
    path = tmp_path / "variant.json"
    path.write_text(json.dumps(v))
    result = run(
        tmp_path, (v, path), "negative-graph", cache_fixture=str(original_path)
    )
    assert not result["ok"], result
    expected = {
        "wrong-type": "OBJECT_KIND_INVALID",
        "version": "UNSUPPORTED_CONTRACT",
        "context": "CACHE_CONTEXT_MISMATCH",
        "noncanonical": "CANONICAL_INVALID",
        "descriptor": "GRAPH_DESCRIPTOR_INVALID",
        "index-count": "GRAPH_INDEX_COUNT",
        "patricia": "GRAPH_PATRICIA_INVALID",
        "hot-context": "GRAPH_CONTEXT_INVALID",
    }
    assert result["error"] == expected.get(change, "CACHE_CONTEXT_MISMATCH")
    state = persisted(result["path"])
    assert all(s[1] != "graph_verified" for s in state["states"])
    save(
        "graph-" + change,
        expected="hash-valid도 context/type/graph 관계가 잘못되면 거부",
        observed=result["error"],
        verdict="PASS",
        persisted=state,
        http=result["http"],
    )


def test_identical_cache_revalidation_and_nonmember_exclusion(tmp_path, fixture):
    expected, path = fixture
    leaf = next(
        o
        for o in expected["objects"]
        if o["kind"] == "snapshot-leaf"
        and json.loads(base64.b64decode(o["data_base64"]))["table"] == "ledger_entries"
    )
    body = json.loads(base64.b64decode(leaf["data_base64"]))
    body["rows"][0]["value"]["title"] = "현재 graph 밖의 합성 cache 객체"
    raw = canonical(body)
    extra = {
        "ref": {"hash": digest(body["kind"], raw), "bytes": str(len(raw))},
        "data_base64": base64.b64encode(raw).decode(),
    }
    result = run(tmp_path, fixture, "identical", seed=True, extra=extra)
    state = closure(result, expected)
    assert state["objects"] == len(expected["objects"]) + 1
    assert extra["ref"]["hash"] not in {o["hash"] for o in result["graph"]}
    assert len(requests(result["trace"])) == 0 and result["http"]["payload_bytes"] == 0
    save(
        "identical-cache",
        expected="fresh observation과 terminal만 요청, payload 0",
        observed="object requests 0",
        verdict="PASS",
        http=result["http"],
    )


@pytest.mark.parametrize("plan", ["corrupt-cache", "cache-delete"])
def test_actual_cache_byte_mutation_and_missing_cache(tmp_path, fixture, plan):
    result = run(tmp_path, fixture, plan)
    if plan == "corrupt-cache":
        assert not result["ok"]
        state = persisted(result["path"], allow_corrupt=True)
        assert len(state["corrupt"]) == 1
        assert len(requests(result["trace"])) == 0
    else:
        closure(result, fixture[0])
        state = persisted(result["path"])
        assert len(requests(result["trace"])) == 1
    save(
        plan,
        expected="손상은 거부, 누락은 실제 필요한 객체 하나만 취득",
        observed=result.get("error", "정상 closure"),
        verdict="PASS",
        persisted=state,
        http=result["http"],
    )


def test_concurrent_session_admission(tmp_path, fixture):
    result = run(tmp_path, fixture, "concurrent")
    assert result["first"]["ok"] and result["second"]["error"] == "ACQUISITION_BUSY"
    assert len(observations(result["trace"])) == 2
    state = persisted(result["path"], fixture[0])
    save(
        "concurrent",
        expected="대기 queue 없이 두번째 session 거부",
        observed="첫 session 정상, 두번째 ACQUISITION_BUSY",
        verdict="PASS",
        persisted=state,
    )


@pytest.mark.parametrize(
    "point",
    [
        "crash-manifest",
        "crash-transfer",
        "crash-before-persist",
        "crash-after-persist",
        "crash-progress",
        "crash-graph-state",
        "crash-return",
    ],
)
def test_real_sigkill_and_fresh_process_resume(tmp_path, fixture, point):
    process = start(tmp_path, fixture, point)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    assert selector.select(180), "barrier deadline"
    message = json.loads(process.stdout.readline())
    selector.close()
    assert message == {"barrier": point}, message
    process.send_signal(signal.SIGKILL)
    _, error = process.communicate(timeout=15)
    assert process.returncode == -signal.SIGKILL, error[-1500:]
    paths = list((tmp_path / "private").glob("segmented-store-v1/*.sqlite"))
    assert len(paths) == 1
    before = persisted(paths[0])
    if point in ["crash-manifest", "crash-transfer", "crash-before-persist"]:
        assert before["objects"] == 0
    if point in ["crash-after-persist", "crash-progress"]:
        assert before["objects"] == 1
    resume = before["states"][0][0] if before["states"] else None
    result = run(tmp_path, fixture, "resume", resume=resume)
    after = closure(result, fixture[0])
    assert (
        len(requests(result["trace"])) == len(fixture[0]["objects"]) - before["objects"]
    )
    save(
        point,
        expected="SIGKILL 후 fresh process에서 committed byte만 재사용",
        observed="원자성·정확한 missing set·최종 closure 일치",
        verdict="PASS",
        before=before,
        after=after,
        http=result["http"],
    )


def test_actual_asgi_incremental_churn_and_resume(tmp_path, fixture):
    result = run(tmp_path, fixture, "live")
    measured = result["measurements"]
    assert len(measured) == 5
    cold, identical, changed, interrupted, resumed = measured
    previous_objects = set()
    previous_count = 0
    trace_end = 0
    cells = []
    for name, value in zip(
        ["cold", "identical", "incremental", "interrupted", "resumed"],
        measured,
        strict=True,
    ):
        phase_trace = result["trace"][trace_end : value["trace_end"]]
        trace_end = value["trace_end"]
        phase_objects = requests(phase_trace)
        if name == "interrupted":
            assert len([e for e in phase_objects if e.get("status") == 200]) == 2
            assert not value["ok"] and value["error"] == "ACQUISITION_CANCELLED"
            cells.append(dict(name=name, ok=False, error=value["error"]))
            continue
        oracle = value["oracle"]
        assert (
            oracle is not None
            and oracle["patricia"] == "PASS"
            and oracle["tables"] == 11
        )
        closure(value | {"path": result["path"]}, oracle)
        refs = {o["ref"]["hash"] for o in oracle["objects"]}
        calls = value["http"]["object_requests"] - previous_count
        expected_missing = refs - previous_objects
        if name in ["cold", "identical", "incremental"]:
            assert calls == len(expected_missing)
        if name == "identical":
            assert calls == 0 and value["metrics"]["payload_bytes"] == 0
        if name == "incremental":
            assert 0 < calls < len(cold["graph"]) and refs & previous_objects
        if name == "resumed":
            expected_missing = refs - set(interrupted["cached_hashes"])
            assert value["metrics"]["object_requests"] == len(expected_missing)
        assert len(phase_objects) == len(expected_missing)
        assert {
            e["request"]["items"][0]["path"][-1] for e in phase_objects
        } == expected_missing
        assert all(e.get("status") == 200 for e in phase_objects)
        cells.append(
            dict(
                name=name,
                ok=True,
                http=value["http"],
                metrics=value["metrics"],
                actual_graph=len(refs),
                new_refs=len(expected_missing),
                independent_http_objects=len(phase_objects),
                independent_http_response_bytes=sum(
                    e["response_bytes"] for e in phase_trace
                ),
                target=value["target"],
                eleven_tables=11,
                patricia="PASS",
            )
        )
        previous_objects |= refs
        previous_count = value["http"]["object_requests"]
    assert changed["target"]["sync_root"] != cold["target"]["sync_root"]
    assert all(e["authorization_matches"] for e in result["trace"])
    (OUT / "live-raw.json").write_text(json.dumps(result))
    save(
        "actual-asgi",
        expected="실제 server graph·11 tables·Patricia·HTTP count 일치, G1/G2를 혼합하지 않음",
        observed="cold/identical/incremental/cancel/resume 검증",
        verdict="PASS",
        cells=cells,
    )


def test_empty_server_graph(tmp_path):
    process = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), str(HERE / "audit_backend.py"), "--empty"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    line = process.stdout.readline()
    assert line, process.stderr.read()[-3000:]
    expected = json.loads(line)["fixture"]
    _, error = process.communicate('{"command":"exit"}\n', timeout=15)
    assert process.returncode == 0, error[-3000:]
    assert all(
        not rows for name, rows in expected["source"].items() if name != "app_settings"
    )
    assert {r["key"] for r in expected["source"]["app_settings"]} == {
        "scheduled_income",
        "cash_flow_balance",
        "card_limit",
    }
    path = tmp_path / "empty.json"
    path.write_text(json.dumps(expected))
    result = run(tmp_path, (expected, path), "cold")
    state = closure(result, expected)
    assert result["table_rows"] == {
        name: str(len(rows)) for name, rows in expected["source"].items()
    }
    assert len(requests(result["trace"])) == len(expected["objects"])
    save(
        "empty-graph",
        expected="10개 빈 raw table와 필수 settings의 정확한 graph closure",
        observed="서버 직접 row·C1·Patricia와 SQLite graph가 일치",
        verdict="PASS",
        objects=state["objects"],
        tables=11,
        patricia=expected["patricia"],
    )


@pytest.mark.parametrize(
    "plan", ["live-expiry-terminal", "live-expiry-transfer", "live-revocation"]
)
def test_actual_server_expiry_and_revocation(tmp_path, fixture, plan):
    result = run(tmp_path, fixture, plan)
    state = persisted(result["path"])
    trace = result["trace"]
    assert all(r["authorization_matches"] for r in trace)
    if plan == "live-revocation":
        assert not result["ok"] and result["action"] == "reauthenticate"
        assert state["objects"] == 2
        assert all(s[1] != "graph_verified" for s in state["states"])
        assert any(e.get("status") == 401 for e in trace)
    else:
        closure(result, result["oracle"])
        assert len({o["request"]["request_id"] for o in observations(trace)}) == 2
        assert any(e.get("status") == 410 for e in trace)
        assert len(requests(trace)) == len(result["oracle"]["objects"]) + (
            1 if plan.endswith("transfer") else 0
        )
    save(
        plan,
        expected="실제 서버의 정확한 lease 경계·철회가 다음 요청에서 적용",
        observed="401은 중단, 410은 새 관측과 기존 검증 byte 재사용",
        verdict="PASS",
        http=result["http"],
        persisted=state,
        statuses=[
            e.get("status") for e in trace if e.get("status") not in [200, 201, 204]
        ],
    )


@pytest.fixture(scope="session")
def native_results(tmp_path_factory, fixture):
    root = tmp_path_factory.mktemp("e2-native-https")
    cert, key = root / "cert.pem", root / "key.pem"
    generated = subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
        ],
        capture_output=True,
        text=True,
    )
    assert generated.returncode == 0, generated.stderr[-2000:]
    job = root / "job.json"
    job.write_text(
        json.dumps(
            dict(
                cert=str(cert),
                key=str(key),
                fixture=str(fixture[1]),
                root=str(root / "store"),
            )
        )
    )
    run = subprocess.run(
        COMMAND[:-1] + [str(HERE / "native_transport.dart"), str(job)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 0, run.stderr[-2500:]
    results = json.loads(run.stdout)
    (OUT / "native-transport.json").write_text(json.dumps(results, indent=2))
    return {v["mode"]: v for v in results}


@pytest.mark.parametrize("mode", ["positive", "auth", "redirect", "oversized"])
def test_native_ioclient_header_rejection_cleans_connection(native_results, mode):
    result = native_results[mode]
    expected = {
        "positive": "HTTP_200",
        "auth": "SegmentedException(AUTHENTICATION_CHANGED)",
        "redirect": "SegmentedException(REDIRECT_REJECTED)",
        "oversized": "SegmentedException(RESPONSE_SIZE_EXCEEDED)",
    }
    assert result["first"] == expected[mode]
    good = (
        result["second"] == "HTTP_200"
        and result["server_requests"] == 2
        and result["active_after_first"] == 0
    )
    save(
        "native-" + mode,
        expected="정상 또는 거부 응답 처리 뒤 연결을 해제하고 후속 요청 성공",
        observed=result,
        verdict="PASS" if good else "FAIL",
        oracle="실제 loopback HTTPS/IOClient/server connectionsInfo",
    )
    assert good, result


def test_native_repeated_acquisition_has_no_abandoned_connections(native_results):
    result = native_results["repeated-acquisition"]
    state = persisted(result["path"])
    assert state["objects"] == 0 and not state["states"]
    assert result["errors"] == ["RESPONSE_SIZE_EXCEEDED"] * 6
    good = result["active_after_each_failure"] == [0] * 6
    save(
        "native-repeated",
        expected="6회 실패 후 매번 native 연결 0, SQLite object/stage 0",
        observed=result,
        verdict="PASS" if good else "FAIL",
        oracle="실제 IOClient/acquire·서버 socket 계수·fresh SQLite",
    )
    assert good, result

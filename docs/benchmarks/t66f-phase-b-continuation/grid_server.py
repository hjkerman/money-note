"""감사 전용 실제 TLS loopback 서버. NEW RetentionSandbox만 소유한다.

stdin은 합성 fixture 조작·barrier 제어, stdout은 private oracle pipe다.
HTTP는 실제 isolated_sync.http.create_app handler와 Uvicorn TCP/TLS를 사용한다.
정상 app.main, configured DB, .env, production credential은 사용하지 않는다.
"""

import base64
from collections import Counter
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import secrets
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts/benchmarks")]

import uvicorn  # noqa: E402
from app import auth  # noqa: E402
from app.services.authoritative_state import _construct, _prepare, BundleCredential  # noqa: E402
from app.services.snapshot import (  # noqa: E402
    _build_manifest,
    _snapshot_metadata,
    snapshot_state_fingerprint,
)
from isolated_sync.http import create_app  # noqa: E402
from isolated_sync.raw import MONEY_SETTINGS  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionSandbox  # noqa: E402
from tests.test_isolated_sync_capture import ROWS, insert  # noqa: E402
from tests.test_isolated_sync_observation import NOW, EVAL  # noqa: E402
from t66e2_server import oracle  # noqa: E402

MONEY = "\x1c+0001000.00\x1f"


class Wire:
    def __init__(self, app):
        self.app = app
        self.records = []
        self.manifest = None
        self.fault = None
        self.pause = None
        self.pause_remaining = 0
        self.entered = threading.Event()
        self.release = threading.Event()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request, messages = bytearray(), []

        async def recv():
            value = await receive()
            if value["type"] == "http.request":
                request.extend(value.get("body", b""))
            return value

        async def capture(value):
            messages.append(value)

        started = time.perf_counter()
        await self.app(scope, recv, capture)
        path = scope["path"]
        start = next(m for m in messages if m["type"] == "http.response.start")
        raw = b"".join(
            m.get("body", b"") for m in messages if m["type"] == "http.response.body"
        )
        body = json.loads(raw) if raw else None
        if path.endswith("/observations") and start["status"] in (200, 201):
            self.manifest = body
        hashes, decoded = [], 0
        if path.endswith("/objects") and start["status"] == 200:
            hashes = [c["ref"]["hash"] for c in body["chunks"]]
            decoded = sum(
                len(base64.b64decode(c["data_base64"], validate=True))
                for c in body["chunks"]
            )
        event = dict(
            method=scope["method"],
            path=path,
            status=start["status"],
            request_bytes=len(request),
            response_bytes=len(raw),
            response_sha256=hashlib.sha256(raw).hexdigest(),
            objects=hashes,
            decoded_bytes=decoded,
            elapsed_ms=(time.perf_counter() - started) * 1000,
            headers={k.decode(): v.decode() for k, v in start["headers"]},
        )
        self.records.append(event)
        if self.pause and self.pause in path and self.pause_remaining > 0:
            self.pause_remaining -= 1
        elif self.pause and self.pause in path:
            self.pause = None
            self.entered.set()
            import asyncio

            while not self.release.is_set():
                await asyncio.sleep(0.005)
        if self.fault and scope["method"] == "POST":
            mode, wanted = self.fault
            if wanted in path:
                self.fault = None
                if mode == "oversized":
                    # 실제 handler가 DB 의존성을 끝낸 뒤 HTTP header만 거부시킨다.
                    # body를 drain해야 끝나는 서버가 아니라 disconnect까지 stall한다.
                    start["headers"] = [
                        (k, v) for k, v in start["headers"] if k != b"content-length"
                    ] + [(b"content-length", b"16777216")]
                    event["injected"] = mode
                    event["response_bytes"] = 0
                    event["declared_length"] = 16777216
                    await send(start)
                    import asyncio

                    async with asyncio.timeout(10):
                        while (await receive())["type"] != "http.disconnect":
                            pass
                    return
                if mode == "truncated":
                    event["injected"] = mode
                    event["response_bytes"] = len(raw) // 2
                    await send(start)
                    await send(
                        {
                            "type": "http.response.body",
                            "body": raw[: len(raw) // 2],
                            "more_body": True,
                        }
                    )
                    raise ConnectionResetError("synthetic truncated response")
                if mode == "wrong_principal":
                    body["target"]["principal_id"] = 2
                elif mode == "wrong_epoch":
                    body["target"]["ns"]["epoch"] = (
                        "11111111-1111-4111-8111-111111111111"
                    )
                elif mode == "unsupported":
                    body["protocol"] = 9
                elif mode == "wrong_root":
                    body["target"]["raw_ref"]["hash"] = "0" * 64
                elif mode == "bad_object":
                    c = body["chunks"][0]
                    data = bytearray(base64.b64decode(c["data_base64"]))
                    data[len(data) // 2] ^= 1
                    c["data_base64"] = base64.b64encode(data).decode()
                elif mode == "wrong_object":
                    body["chunks"][0]["ref"]["hash"] = "0" * 64
                elif mode == "wrong_observation":
                    body["observation_id"] = "11111111-1111-4111-8111-111111111111"
                elif mode == "malformed":
                    body = None
                elif mode == "missing":
                    start["status"] = 410
                    nonce = json.loads(request)["request_id"]
                    body = dict(
                        protocol=1,
                        request_id=nonce,
                        error=dict(
                            code="OBSERVATION_INCOMPLETE",
                            action="new_observation",
                            retry_after_ms=None,
                            current_ns=None,
                        ),
                    )
                else:
                    raise AssertionError(mode)
                raw = (
                    b"{"
                    if body is None
                    else json.dumps(
                        body, ensure_ascii=False, separators=(",", ":")
                    ).encode()
                )
                start["headers"] = [
                    (k, v) for k, v in start["headers"] if k != b"content-length"
                ] + [(b"content-length", str(len(raw)).encode())]
                messages = [start, {"type": "http.response.body", "body": raw}]
                event["injected"] = mode
                event["response_bytes"] = len(raw)
                event["response_sha256"] = hashlib.sha256(raw).hexdigest()
        for value in messages:
            await send(value)


def expected(db, manifest, credential):
    result = oracle(db, manifest)
    control = next(
        json.loads(base64.b64decode(o["data_base64"]))
        for o in result["objects"]
        if json.loads(base64.b64decode(o["data_base64"]))["kind"] == "control"
    )
    with db.connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        with (
            patch(
                "app.services.authoritative_state.CURRENT_SCHEMA_VERSION",
                conn.execute("PRAGMA user_version").fetchone()[0],
            ),
            patch("app.services.authoritative_state._validate_revision_triggers"),
            patch(
                "app.services.authoritative_state.app_today", return_value=EVAL.today
            ),
        ):
            bundle, _, _ = _construct(conn, credential)
            wire = json.loads(_prepare(bundle).body)
        conn.rollback()
    # exporter 자체가 SQL ORDER BY를 수행한다. E4 comparator를 oracle로 쓰지 않는다.
    snapshot = dict(
        schema_version=7,
        recurring_ownership_version=1,
        exported_at=control["exported_at"],
        range=control["range"],
        card_charge_policy=control["card_charge_policy"],
        data=wire["snapshot"]["data"],
    )
    snapshot["manifest"] = _build_manifest(
        snapshot["data"],
        empty_table_columns=control["columns"],
        policy_context=control["card_charge_policy"],
        snapshot_metadata=_snapshot_metadata(snapshot),
    )
    snapshot["snapshot_id"] = snapshot["manifest"]["content_sha256"]
    result.update(
        expected_snapshot=snapshot,
        expected_fingerprint=snapshot_state_fingerprint(snapshot),
        expected_hot=wire["state"],
        source_db_bytes=db.path.stat().st_size,
    )
    return result


def main():
    history = int(sys.argv[1])
    empty = history == -1
    history = max(history, 0)
    assert history in (1000, 5000, 10000, 50000, 100000)  # 감사용 전체 N grid
    clock, token, other_token = (
        [NOW],
        secrets.token_urlsafe(32),
        secrets.token_urlsafe(32),
    )
    with (
        tempfile.TemporaryDirectory(prefix="mn-f-tls-") as tls,
        RetentionSandbox() as db,
    ):
        with db.connect() as conn:
            for table, source in ({} if empty else ROWS).items():
                row = dict(source)
                if "title" in row:
                    row["title"] += " 한글 😀 e\u0301"
                if table == "cash_flows":
                    row["amount_value"] = -50
                insert(conn, table, row)
            for n in range(history):
                insert(
                    conn,
                    "ledger_entries",
                    dict(
                        id=1000 + n,
                        book_section="archive",
                        entry_kind="expense",
                        entry_date=None if n % 3 == 0 else "2026-07-03",
                        title="역사 😀 e\u0301 " + str(n),
                        amount_value=1000,
                        sort_order=n,
                        payment_key="f-history-" + str(n),
                    ),
                )
            for key in MONEY_SETTINGS:
                conn.execute(
                    "INSERT OR REPLACE INTO app_settings(key,value) VALUES (?,?)",
                    (key, MONEY if key == "cash_flow_balance" else "0"),
                )
            for key in ("\ue000", "😀", "e\u0301"):
                conn.execute(
                    "INSERT OR REPLACE INTO app_labels(key,value) VALUES (?,?)",
                    (key, "원문 " + key),
                )
            conn.execute(
                "INSERT INTO users(id,username,password_hash) VALUES (1,'synthetic-f','unused')"
            )
            conn.execute(
                "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",
                (auth._hash_session_token(token),),
            )
            conn.execute(
                "INSERT INTO users(id,username,password_hash) VALUES (2,'synthetic-f-other','unused')"
            )
            conn.execute(
                "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (2,?,'2026-12-31T00:00:00Z')",
                (auth._hash_session_token(other_token),),
            )
        db.install()
        db.bootstrap()
        # SQLite 자체의 expanded-statement trace다. 제품 metrics를 읽지 않는다.
        # trigger 진입에 따른 반복 trace는 VM instruction/row count와 구별한다.
        statements, trace_enabled = Counter(), [True]
        original_open = db._open

        def traced_open():
            conn = original_open()
            conn.set_trace_callback(
                lambda sql: (
                    statements.update(
                        [re.sub(r"x'[0-9A-Fa-f]*'|'(?:''|[^'])*'|\b[0-9]+\b", "?", sql)]
                    )
                    if trace_enabled[0]
                    else None
                )
            )
            return conn

        db._open = traced_open
        repo = RetentionRepository(db, clock=lambda: clock[0], evaluation=lambda: EVAL)
        credential = BundleCredential(auth._hash_session_token(token), 1)
        key, cert = str(Path(tls) / "key.pem"), str(Path(tls) / "cert.pem")
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-keyout",
                key,
                "-out",
                cert,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        wire = Wire(create_app(repo))
        server = uvicorn.Server(
            uvicorn.Config(
                wire,
                host="127.0.0.1",
                port=port,
                ssl_keyfile=key,
                ssl_certfile=cert,
                log_level="critical",
                access_log=False,
            )
        )
        with patch(
            "app.services.judgment.common._MESSAGE_RANDOM.randrange", return_value=0
        ):
            worker = threading.Thread(
                target=server.run, kwargs={"sockets": [listener]}, daemon=True
            )
            worker.start()
            deadline = time.monotonic() + 30
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            manifest = repo.create(
                credential,
                request_id="22222222-2222-4222-8222-222222222222",
                guard=lambda: credential,
            )
            initial = expected(db, manifest, credential)
            repo.release(
                manifest["observation_id"], credential, guard=lambda: credential
            )
            print(
                json.dumps(
                    dict(
                        origin=f"https://127.0.0.1:{port}",
                        token=token,
                        fixture=initial,
                        owned_db_path=str(db.path),
                    )
                ),
                flush=True,
            )
            for line in sys.stdin:
                request = json.loads(line)
                command = request["command"]
                if command == "oracle":
                    trace_enabled[0] = False
                    result = expected(db, wire.manifest, credential)
                    trace_enabled[0] = True
                elif command == "stats":
                    result = dict(
                        records=wire.records,
                        backend_sql_trace=dict(statements),
                        backend_sql_trace_events=sum(statements.values()),
                    )
                    if request.get("reset"):
                        wire.records = []
                        statements.clear()
                elif command == "mutate":
                    op = request.get("op", "update")
                    before_statements = statements.copy()
                    with sqlite3.connect(db.path) as independent:
                        before_objects = {
                            r[0]
                            for r in independent.execute(
                                "SELECT hash FROM sync_objects"
                            )
                        }
                    with db.connect() as conn:
                        conn.begin_capture()
                        if op == "update":
                            conn.execute(
                                "UPDATE ledger_entries SET title=? WHERE id=?",
                                (
                                    request.get("title", "합성 변경"),
                                    request.get("id", 100),
                                ),
                            )
                        elif op == "delete":
                            conn.execute(
                                "DELETE FROM ledger_entries WHERE id=?",
                                (request.get("id", 1000),),
                            )
                        elif op == "insert":
                            for n in range(request.get("count", 1)):
                                insert(
                                    conn,
                                    "ledger_entries",
                                    dict(
                                        id=20000 + n,
                                        book_section="archive",
                                        entry_kind="expense",
                                        entry_date="2026-07-03",
                                        title="새 경계 " + str(n),
                                        amount_value=1000,
                                        sort_order=n,
                                        payment_key="f-added-" + str(n),
                                    ),
                                )
                        elif op == "cash":
                            conn.execute(
                                "UPDATE cash_flows SET title=? WHERE id=100",
                                (request.get("title", "합성 현금 변경"),),
                            )
                        elif op == "delete_added":
                            conn.execute(
                                "DELETE FROM ledger_entries WHERE id>=20000 AND id<20512"
                            )
                        else:
                            raise AssertionError(op)
                        conn.finalize()
                    with sqlite3.connect(db.path) as independent:
                        after_objects = {
                            r[0]
                            for r in independent.execute(
                                "SELECT hash FROM sync_objects"
                            )
                        }
                    delta = statements - before_statements
                    result = dict(
                        ok=True,
                        new_immutable_objects=len(after_objects - before_objects),
                        existing_immutable_objects=len(before_objects),
                        sql_trace_events=sum(delta.values()),
                        sql_trace=dict(delta),
                    )
                elif command == "advance":
                    clock[0] += timedelta(seconds=request["seconds"])
                    result = dict(ok=True)
                elif command == "fault":
                    wire.fault = (request["mode"], request.get("path", "/observations"))
                    result = dict(ok=True)
                elif command == "pause":
                    wire.entered.clear()
                    wire.release.clear()
                    wire.pause = request["path"]
                    wire.pause_remaining = request.get("skip", 0)
                    result = dict(ok=True)
                elif command == "entered":
                    result = dict(entered=wire.entered.is_set())
                elif command == "release":
                    wire.release.set()
                    result = dict(ok=True)
                elif command == "revoke":
                    with db.connect() as conn:
                        conn.execute("DELETE FROM auth_sessions")
                    result = dict(ok=True)
                elif command == "other_principal":
                    result = dict(token=other_token)
                elif command == "rotate_epoch":
                    db.bootstrap()
                    result = dict(ok=True)
                elif command == "exit":
                    print('{"ok":true}', flush=True)
                    break
                else:
                    raise AssertionError(command)
                print(
                    json.dumps(result, ensure_ascii=True, separators=(",", ":")),
                    flush=True,
                )
        server.should_exit = True
        worker.join(timeout=15)
        assert not worker.is_alive()


if __name__ == "__main__":
    main()

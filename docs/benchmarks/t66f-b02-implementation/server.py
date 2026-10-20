"""B02 폐기용 실제 TLS 서버. 실제 clock/900초 lease, 기존 fixed-H seed.

Backend object catalog를 E1으로 복사하지 않는다. stdout은 합성 credential을
전달하는 private pipe이며 저장/출력 증거에는 credential을 기록하지 않는다.
"""

from collections import Counter
from contextlib import closing
from datetime import date
import importlib.util
import json
from pathlib import Path
import resource
import secrets
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts/benchmarks")]
import uvicorn  # noqa: E402
from app import auth  # noqa: E402
from app.services.authoritative_state import BundleCredential  # noqa: E402
from isolated_sync.http import create_app  # noqa: E402
from isolated_sync.inputs import BoundedInputs  # noqa: E402
from isolated_sync.observation import Evaluation  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionSandbox  # noqa: E402
from t66d2b_writers import seed  # noqa: E402
from tests.d2b_financial_reference import projections  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "b02_original_graph_oracle", ROOT / "docs/benchmarks/t66f-b02/generate.py"
)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class Wire:
    def __init__(self, app, out):
        self.app, self.out = app, out
        self.counts = Counter()
        self.last_manifest = None
        self.failures = []

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_bytes = 0
        messages = []

        async def recv():
            nonlocal request_bytes
            message = await receive()
            request_bytes += len(message.get("body", b""))
            return message

        async def capture(message):
            messages.append(message)

        started = time.perf_counter_ns()
        await self.app(scope, recv, capture)
        self.counts["handler_ns"] += time.perf_counter_ns() - started
        start = next(m for m in messages if m["type"] == "http.response.start")
        raw = b"".join(m.get("body", b"") for m in messages)
        path, status = scope["path"], start["status"]
        self.counts["requests"] += 1
        self.counts["request_entity_bytes"] += request_bytes
        self.counts["response_entity_bytes"] += len(raw)
        self.counts[f"status_{status}"] += 1
        if path.endswith("/objects") and status == 200:
            body = json.loads(raw)
            chunks = body["chunks"]
            self.counts["object_requests"] += 1
            self.counts["chunks"] += len(chunks)
            self.counts["decoded_object_bytes"] += sum(c["length"] for c in chunks)
        elif path.endswith("/observations") and status in (200, 201):
            self.counts["observation_requests"] += 1
            self.last_manifest = json.loads(raw)
            write(self.out / "last-http-manifest.json", self.last_manifest)
        elif scope["method"] == "DELETE":
            self.counts["release_requests"] += 1
        if status >= 400:
            failure = dict(
                status=status,
                method=scope["method"],
                path=path,
                body=json.loads(raw),
                wall_time=time.time(),
            )
            self.failures.append(failure)
            write(self.out / "http-failures.json", self.failures)
        # Bounded periodic evidence, not an unbounded per-object record list.
        if self.counts["requests"] % 1000 == 0 or status >= 400:
            write(self.out / "wire-progress.json", dict(self.counts))
        for message in messages:
            await send(message)


def main():
    n, out = int(sys.argv[1]), Path(sys.argv[2])
    assert n in (1000, 50000, 100000)
    out.mkdir(parents=True, exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    token = secrets.token_urlsafe(32)
    credential = BundleCredential(auth._hash_session_token(token), 1)
    # RetentionSandbox path is new and private; all clocks remain real.
    with (
        RetentionSandbox() as db,
        patch("app.services.judgment.common._MESSAGE_RANDOM.randrange", return_value=0),
    ):
        with db.connect() as conn:
            seed(conn, n)
            conn.execute(
                "INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order,is_primary_income) VALUES (101,'2026-10-05','fixed-width-cash',-50,2,0)"
            )
            conn.execute(
                "INSERT INTO users(id,username,password_hash) VALUES (1,'b02-synthetic','unused')"
            )
            conn.execute(
                "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",
                (credential.token_hash,),
            )
        db.install()
        watch = time.perf_counter()
        db.bootstrap()
        bootstrap_seconds = time.perf_counter() - watch
        repo = RetentionRepository(
            db, evaluation=lambda: Evaluation(date(2026, 10, 5), 540)
        )
        initial = repo.create(
            credential, request_id=str(uuid4()), guard=lambda: credential
        )
        with closing(sqlite3.connect(db.path)) as conn:
            graph_hashes, graph = oracle.walk(conn, initial["target"])
        assert graph["objects"] == {1000: 4132, 50000: 200331, 100000: 400532}[n]
        assert sum(graph["raw_rows"].values()) == n + 35
        repo.release(initial["observation_id"], credential, guard=lambda: credential)
        write(
            out / "backend-fixture.json",
            dict(
                n=n,
                graph=graph,
                bootstrap_seconds=bootstrap_seconds,
                manifest=initial,
                max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                backend_db_bytes=db.path.stat().st_size,
            ),
        )
        key, cert = out / "synthetic-key.pem", out / "synthetic-cert.pem"
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
                str(key),
                "-out",
                str(cert),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        measurements = Counter()

        def measured(row):
            measurements["operations"] += 1
            for field in (
                "admission_ms",
                "resolution_ms",
                "terminal_serialization_ms",
                "prepared_ms",
                "object_reads",
                "object_bytes_read",
                "path_edges",
                "decoded_bytes",
            ):
                measurements[field] += row.get(field, 0)

        wire = Wire(create_app(repo, metrics=measured), out)
        server = uvicorn.Server(
            uvicorn.Config(
                wire,
                host="127.0.0.1",
                port=port,
                ssl_keyfile=str(key),
                ssl_certfile=str(cert),
                log_level="critical",
                access_log=False,
            )
        )
        worker = threading.Thread(
            target=server.run, kwargs={"sockets": [listener]}, daemon=True
        )
        worker.start()
        deadline = time.monotonic() + 30
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        print(
            json.dumps(
                dict(
                    origin=f"https://127.0.0.1:{port}",
                    token=token,
                    fixture=dict(manifest=initial, graph=graph),
                )
            ),
            flush=True,
        )
        try:
            for line in sys.stdin:
                request = json.loads(line)
                command = request["command"]
                if command == "stats":
                    value = dict(
                        wire=dict(wire.counts),
                        failures=wire.failures,
                        backend_measurements=dict(measurements),
                    )
                elif command == "mutate":
                    # Test-only oracle preparation, outside publication timing.
                    before = graph_hashes
                    ids = [1002, 1010] if request.get("multiple") else [1002]
                    with db.connect() as conn:
                        conn.begin_capture()
                        writer = BoundedInputs(conn)
                        for key in ids:
                            writer.execute(
                                "UPDATE ledger_entries SET amount_value=? WHERE id=?",
                                (request["amount"], key),
                            )
                        projections(writer)
                        conn.finalize()
                        conn.commit()
                    prepared = repo.create(
                        credential, request_id=str(uuid4()), guard=lambda: credential
                    )
                    with closing(sqlite3.connect(db.path)) as conn:
                        conn.row_factory = sqlite3.Row
                        graph_hashes, changed_graph = oracle.walk(
                            conn, prepared["target"]
                        )
                        row = dict(
                            conn.execute(
                                "SELECT * FROM ledger_entries WHERE id=1002"
                            ).fetchone()
                        )
                        delta = graph_hashes - before
                        changed_bytes = sum(
                            conn.execute(
                                "SELECT length(body) FROM sync_objects WHERE hash=?",
                                (h,),
                            ).fetchone()[0]
                            for h in delta
                        )
                    repo.release(
                        prepared["observation_id"], credential, guard=lambda: credential
                    )
                    value = dict(
                        target=prepared["target"],
                        graph=changed_graph,
                        new_objects=len(delta),
                        new_bytes=changed_bytes,
                        reused_objects=len(graph_hashes & before),
                        expected_row=row,
                    )
                    write(out / f"mutation-{request['amount']}.json", value)
                elif command == "exit":
                    print('{"ok":true}', flush=True)
                    break
                else:
                    raise ValueError(command)
                print(json.dumps(value), flush=True)
        finally:
            write(out / "wire-final.json", dict(wire.counts))
            server.should_exit = True
            worker.join(timeout=15)
            assert not worker.is_alive()


if __name__ == "__main__":
    main()

"""별도 HTTPS 서버·Linux /proc socket inode·독립 hashlib로 교정 경계를 검사한다."""

import base64
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import selectors
import ssl
import subprocess
import threading

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = Path(os.environ.get("E2_REAUDIT_OUTPUT", "/tmp/mn-e2-a01-reaudit/new"))


def read_json(process):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        assert selector.select(8), "감사 worker 응답 상한 초과"
        line = process.stdout.readline()
    assert line, "감사 worker가 예기치 않게 종료됨"
    return json.loads(line)


def socket_fds(pid, port):
    """현재 worker FD inode와 TCP remote port를 교차 검증한다. 서버 FD는 제외한다."""
    owned = {}
    for fd in Path(f"/proc/{pid}/fd").iterdir():
        try:
            target = fd.readlink().as_posix()
        except FileNotFoundError:
            continue
        if target.startswith("socket:["):
            owned[target[8:-1]] = int(fd.name)
    result = []
    for table in ("tcp", "tcp6"):
        for row in Path(f"/proc/{pid}/net/{table}").read_text().splitlines()[1:]:
            fields = row.split()
            inode = fields[9]
            if inode in owned and int(fields[2].split(":")[1], 16) == port:
                result.append(
                    dict(
                        fd=owned[inode], inode=inode, state=fields[3], remote=fields[2]
                    )
                )
    return sorted(result, key=lambda row: row["fd"])


@pytest.fixture(scope="session")
def material(tmp_path_factory):
    root = tmp_path_factory.mktemp("e2-a01-independent-tls")
    cert, key = root / "cert.pem", root / "key.pem"
    run = subprocess.run(
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
    assert run.returncode == 0, run.stderr[-1500:]
    golden = ROOT / "mobile/test/fixtures/segmented_server_golden.json"
    value = json.loads(golden.read_text())
    obj = next(o for o in value["objects"] if o["kind"] == "raw-root")
    raw = base64.b64decode(obj["data_base64"])
    decoded = json.loads(raw)
    assert (
        raw
        == json.dumps(
            decoded, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )
    digest = hashlib.sha256(b"money-note.sync.v1/raw-root\0" + raw).hexdigest()
    assert digest == obj["ref"]["hash"]
    return cert, key, golden, raw, digest


@contextmanager
def environment(tmp_path, material, limit=1):
    cert, key, golden, raw, digest = material
    stop, hold_started, hold_release = (
        threading.Event(),
        threading.Event(),
        threading.Event(),
    )
    requests = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            mode = self.headers["X-Audit-Mode"]
            requests.append(mode)
            if mode in ("valid", "hold-valid", "tampered", "wrong-hash"):
                payload = raw
                if mode == "tampered":
                    payload = raw[:-1] + b" "
                elif mode == "wrong-hash":
                    assert b'"canon":1' in raw
                    payload = raw.replace(b'"canon":1', b'"canon":2', 1)
                    assert (
                        hashlib.sha256(
                            b"money-note.sync.v1/raw-root\0" + payload
                        ).hexdigest()
                        != digest
                    )
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if mode == "hold-valid":
                    self.wfile.write(payload[:1])
                    self.wfile.flush()
                    hold_started.set()
                    hold_release.wait(6)
                    payload = payload[1:]
                try:
                    self.wfile.write(payload)
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
                    pass
                return
            self.send_response(200 if mode in ("oversized", "huge", "auth") else 307)
            if mode == "redirect-empty":
                self.send_header("Content-Length", "0")
            elif mode == "redirect-chunked":
                self.send_header("Transfer-Encoding", "chunked")
            else:
                self.send_header(
                    "Content-Length",
                    str(
                        2**40
                        if mode == "huge"
                        else 1048577
                        if mode == "oversized"
                        else 1048576
                    ),
                )
            self.end_headers()
            try:
                if mode != "redirect-empty":
                    self.wfile.write(
                        b"400\r\n" + b"A" * 1024 + b"\r\n"
                        if mode == "redirect-chunked"
                        else b"A" * 1024
                    )
                    self.wfile.flush()
                    stop.wait(
                        10
                    )  # body를 완료하지 않는다. client cleanup은 이를 기다리면 안 된다.
            except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    job = tmp_path / "job.json"
    job.write_text(
        json.dumps(
            dict(
                origin=f"https://127.0.0.1:{server.server_port}",
                golden=str(golden),
                limit=limit,
            )
        )
    )
    err = (tmp_path / "worker-errors.log").open("w")
    process = subprocess.Popen(
        [
            "/home/hjkerman/.flutter/bin/dart",
            "--packages=" + str(ROOT / "mobile/.dart_tool/package_config.json"),
            str(HERE / "probe.dart"),
            str(job),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=err,
        text=True,
        bufsize=1,
    )
    ready = read_json(process)
    assert ready["pid"] == process.pid
    evidence = dict(
        pid=process.pid,
        port=server.server_port,
        limit=limit,
        samples=[],
        requests=requests,
    )

    def command(**fields):
        process.stdin.write(json.dumps(fields) + "\n")
        process.stdin.flush()
        result = read_json(process)
        result["tcp_fds"] = socket_fds(process.pid, server.server_port)
        evidence["samples"].append(dict(command=fields, **result))
        return result

    try:
        yield command, evidence, hold_started, hold_release
    finally:
        hold_release.set()
        stop.set()
        if process.poll() is None:
            process.stdin.write('{"action":"exit"}\n')
            process.stdin.flush()
            try:
                process.wait(5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(3)
        err.close()
        server.shutdown()
        server.server_close()
        thread.join(2)
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / (tmp_path.name + ".json")).write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
        )
        assert process.returncode == 0, (tmp_path / "worker-errors.log").read_text()[
            -2000:
        ]


@pytest.mark.parametrize(
    "mode,error",
    [
        ("auth", "AUTHENTICATION_CHANGED"),
        ("redirect", "REDIRECT_REJECTED"),
        ("oversized", "RESPONSE_SIZE_EXCEEDED"),
        ("huge", "RESPONSE_SIZE_EXCEEDED"),
        ("redirect-chunked", "REDIRECT_REJECTED"),
        ("redirect-empty", "REDIRECT_REJECTED"),
    ],
)
def test_six_rejections_then_verified_object_same_pool(tmp_path, material, mode, error):
    with environment(tmp_path, material) as (command, evidence, _, __):
        for _ in range(6):
            result = command(action="request", mode=mode)
            assert result["result"] == f"SegmentedException({error})"
            assert result["client_close_calls"] == 0
            assert not result["tcp_fds"], result
            assert result["milliseconds"] < 3000
        result = command(action="request", mode="valid")
        assert result["result"] == "VERIFIED", result
        assert result["client_close_calls"] == 0
        assert base64.b64decode(result["bytes"]) == material[3]
        assert result["hash"] == material[4]
        assert len(result["tcp_fds"]) == 1  # 정상 응답의 idle pooled socket은 허용한다.
        assert evidence["requests"] == [mode] * 6 + ["valid"]


def test_rejection_does_not_destroy_another_live_response(tmp_path, material):
    with environment(tmp_path, material, limit=2) as (
        command,
        evidence,
        started,
        release,
    ):
        command(action="begin-valid")
        assert started.wait(4)
        result = command(action="request", mode="redirect-chunked")
        assert result["result"] == "SegmentedException(REDIRECT_REJECTED)"
        assert result["client_close_calls"] == 0
        assert (
            len(result["tcp_fds"]) == 1
        )  # 다른 요청의 actual native response는 계속 살아 있다.
        release.set()
        result = command(action="finish-valid")
        assert result["result"] == "VERIFIED", result
        assert result["hash"] == material[4]
        assert evidence["requests"] == ["hold-valid", "redirect-chunked"]


@pytest.mark.parametrize(
    "mode,error",
    [("tampered", "REPRESENTATION_INVALID"), ("wrong-hash", "OBJECT_HASH_INVALID")],
)
def test_valid_path_rejects_corruption_and_remains_reusable(
    tmp_path, material, mode, error
):
    with environment(tmp_path, material) as (command, _, __, ___):
        bad = command(action="request", mode=mode)
        assert bad["result"] == f"SegmentedException({error})", bad
        good = command(action="request", mode="valid")
        assert good["result"] == "VERIFIED"
        assert good["client_close_calls"] == 0
        assert good["hash"] == material[4]

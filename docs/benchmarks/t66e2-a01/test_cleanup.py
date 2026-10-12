"""원본 native 시나리오를 보존하고 해당 client의 실제 TCP FD도 함께 계측한다."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "docs/benchmarks/t66e2-audit"
OUT = Path(os.environ.get("E2_A01_OUTPUT", "/tmp/money-note-e2-a01-tcp"))


@pytest.fixture(scope="session")
def measured(tmp_path_factory):
    root = tmp_path_factory.mktemp("e2-a01-tcp")
    process = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), str(AUDIT / "audit_backend.py")],
        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True,
    )
    first = json.loads(process.stdout.readline())
    _, error = process.communicate('{"command":"exit"}\n', timeout=15)
    assert process.returncode == 0, error[-2000:]
    fixture = root / "fixture.json"
    fixture.write_text(json.dumps(first["fixture"]))
    cert, key = root / "cert.pem", root / "key.pem"
    run = subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(key), "-out", str(cert), "-days", "1", "-subj", "/CN=localhost"],
        capture_output=True, text=True,
    )
    assert run.returncode == 0, run.stderr[-2000:]
    job = root / "job.json"
    job.write_text(json.dumps(dict(cert=str(cert), key=str(key), fixture=str(fixture), root=str(root / "store"))))
    # Use the original scenario with the approved connection-ownership oracle.
    # Requests, errors, server barriers and maxConnectionsPerHost are unchanged.
    source = (AUDIT / "native_transport.dart").read_text()
    worker = root / "measured.dart"
    worker.write_text(source)
    package_config = ROOT / "mobile/.dart_tool/package_config.json"
    baseline = os.environ.get("E2_A01_BASELINE_COMMIT")
    if baseline:
        # Reproduce the exact old library without changing the working tree or
        # the historical audit. Only tracked Dart library sources are read.
        config = json.loads(package_config.read_text())
        paths = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", baseline,
             "mobile/lib"], cwd=ROOT, text=True,
        ).splitlines()
        assert paths and all(p.startswith("mobile/lib/") for p in paths)
        for path in paths:
            destination = root / "baseline" / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(subprocess.check_output(
                ["git", "show", f"{baseline}:{path}"], cwd=ROOT,
            ))
        for package in config["packages"]:
            uri = package["rootUri"]
            if ":" not in uri:
                package["rootUri"] = (package_config.parent / uri).resolve().as_uri() + "/"
            if package["name"] == "money_note_mobile":
                package["rootUri"] = (root / "baseline/mobile").as_uri() + "/"
        assets = package_config.with_name("native_assets.yaml").read_bytes()
        package_config = root / "baseline/mobile/.dart_tool/package_config.json"
        package_config.parent.mkdir(parents=True, exist_ok=True)
        package_config.write_text(json.dumps(config))
        package_config.with_name("native_assets.yaml").write_bytes(assets)
    run = subprocess.run(
        ["/home/hjkerman/.flutter/bin/dart",
         "--packages=" + str(package_config), str(worker), str(job)],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert run.returncode == 0, run.stderr[-2500:]
    results = json.loads(run.stdout)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "native-tcp.json").write_text(json.dumps(results, indent=2))
    return {v["mode"]: v for v in results}


@pytest.mark.parametrize("mode", ["auth", "redirect", "oversized"])
def test_native_rejection_releases_client_tcp_fd_and_pool(measured, mode):
    result = measured[mode]
    expected = dict(auth="AUTHENTICATION_CHANGED", redirect="REDIRECT_REJECTED", oversized="RESPONSE_SIZE_EXCEEDED")
    assert result["first"] == f"SegmentedException({expected[mode]})"
    assert result["client_fd_after_first"] == 0, result
    assert result["second"] == "HTTP_200", result
    assert result["server_requests"] == 2
    # One reusable idle connection for the successful second request is valid.
    assert result["client_fd_after_second"] == 1


def test_native_repeated_acquisition_releases_every_client_tcp_fd(measured):
    result = measured["repeated-acquisition"]
    assert result["errors"] == ["RESPONSE_SIZE_EXCEEDED"] * 6
    assert result["client_fd_after_each_failure"] == [0] * 6, result
    with closing(sqlite3.connect(result["path"])) as db:
        for table in ("objects", "staging", "acquisition"):
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone() == (0,)
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.execute("PRAGMA foreign_key_check").fetchall()


def test_native_valid_response_preserves_reusable_idle_socket(measured):
    result = measured["positive"]
    assert result["first"] == result["second"] == "HTTP_200"
    assert result["server_requests"] == 2
    assert result["client_fd_after_first"] == result["client_fd_after_second"] == 1
    assert result["total_connections"] == 1

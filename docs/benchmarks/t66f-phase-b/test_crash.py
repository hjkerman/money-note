"""실제 TLS D→E child SIGKILL 및 새 Flutter process의 DATA 복구."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = Path(os.environ.get("F_CRASH_OUTPUT", "/tmp/mn-t66f-phase-b/crash"))
FLUTTER = "/home/hjkerman/.flutter/bin/flutter"


@pytest.mark.parametrize(
    "boundary",
    [
        "after_e3_acceptance",
        "before_source_rename",
        "native_before_commit",
        "after_e4_installation",
    ],
)
def test_real_d_to_e_process_termination(boundary, tmp_path):
    OUT.mkdir(parents=True, exist_ok=True)
    server_log = (OUT / (boundary + "-server.log")).open("w")
    server = subprocess.Popen(
        [str(ROOT / ".venv/bin/python"), str(HERE / "server.py"), "3"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=server_log,
        text=True,
    )
    child = None
    root = None
    try:
        backend = json.loads(server.stdout.readline())
        barrier = tmp_path / "barrier.json"
        config = tmp_path / "input.json"
        ready, proceed = tmp_path / "ready.json", tmp_path / "continue"
        config.write_text(
            json.dumps(
                dict(
                    backend=backend,
                    boundary=boundary,
                    barrier=str(barrier),
                    ready=str(ready),
                    **{"continue": str(proceed)},
                )
            )
        )
        with (OUT / (boundary + "-child.log")).open("w") as log:
            child = subprocess.Popen(
                [
                    FLUTTER,
                    "test",
                    "--no-pub",
                    "--machine",
                    "--dart-define=F_CRASH_INPUT=" + str(config),
                    str(HERE / "crash_child_test.dart"),
                ],
                cwd=ROOT / "mobile",
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            deadline = time.monotonic() + 480
            while (
                not barrier.exists()
                and child.poll() is None
                and time.monotonic() < deadline
            ):
                if ready.exists() and not proceed.exists():
                    server.stdin.write(
                        json.dumps(
                            dict(command="mutate", title="SIGKILL G2 " + boundary)
                        )
                        + "\n"
                    )
                    server.stdin.flush()
                    assert json.loads(server.stdout.readline())["ok"]
                    proceed.write_text("G2 COMMITTED")
                time.sleep(0.025)
            assert barrier.exists(), (OUT / (boundary + "-child.log")).read_text()[
                -2500:
            ]
            observed = json.loads(barrier.read_text())
            root = Path(observed["root"])
            os.kill(observed["pid"], signal.SIGKILL)
            child.wait(timeout=30)
            assert child.returncode != 0
        inp, output = tmp_path / "fresh.json", tmp_path / "fresh-output.json"
        inp.write_text(
            json.dumps(
                dict(
                    root=str(root),
                    target=observed["target"],
                    origin=backend["origin"],
                    frozen=observed["initial"]["frozen"],
                )
            )
        )
        with (OUT / (boundary + "-fresh.log")).open("w") as log:
            result = subprocess.run(
                [
                    FLUTTER,
                    "test",
                    "--no-pub",
                    "--machine",
                    "--dart-define=F_REOPEN=" + str(inp),
                    "--dart-define=F_REOPEN_OUTPUT=" + str(output),
                    str(HERE / "fresh_test.dart"),
                ],
                cwd=ROOT / "mobile",
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=480,
            )
        assert result.returncode == 0, (OUT / (boundary + "-fresh.log")).read_text()[
            -2500:
        ]
        fresh = json.loads(output.read_text())
        assert fresh["frozen_fingerprint"] == observed["initial"]["fingerprint"]
        for key, name in [
            ("baseline_sha256", "baseline.json"),
            ("pending_sha256", "online-write-1.json"),
        ]:
            assert (
                hashlib.sha256(
                    (root / "segmented-e4-workspace/offline-mode" / name).read_bytes()
                ).hexdigest()
                == observed["initial"][key]
            )
        spec = importlib.util.spec_from_file_location(
            "phase_b_state_oracle", ROOT / "docs/benchmarks/t66e4-audit/state_oracle.py"
        )
        oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        durable = oracle.inspect(Path(observed["db"]), root / "segmented-e4-workspace")
        (OUT / (boundary + ".json")).write_text(
            json.dumps(
                dict(
                    barrier=observed,
                    actual_signal="SIGKILL",
                    fresh=fresh,
                    durable=durable,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        if child and child.poll() is None:
            child.terminate()
            child.wait(timeout=30)
        if server.poll() is None:
            server.stdin.write('{"command":"exit"}\n')
            server.stdin.flush()
            server.communicate(timeout=30)
        server_log.close()
        if root:
            shutil.rmtree(root)

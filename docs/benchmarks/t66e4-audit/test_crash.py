"""G1이 이미 설치된 교차 저장소에서 G2 handoff를 실제 SIGKILL한다."""
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import pytest
from state_oracle import inspect

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = Path(os.environ.get("E4_AUDIT_OUTPUT", "/tmp/mn-e4-phase-a-audit"))
BOUNDARIES = ["after_frozen_prepare", "after_legacy_commit", "after_frozen_install", "after_e4_installation", "native_after_segmented_install_pointer", "native_during_installation_readback"]


def command(root, mode, boundary):
    return ["/home/hjkerman/.flutter/bin/flutter", "test", "--no-pub", "--machine",
            "--dart-define=AUDIT_E4_ROOT=" + str(root),
            "--dart-define=AUDIT_E4_MODE=" + mode,
            "--dart-define=AUDIT_E4_BOUNDARY=" + boundary,
            str(HERE / "crash_child_test.dart")]


@pytest.mark.parametrize("boundary", BOUNDARIES)
def test_g1_g2_process_crash(tmp_path, boundary):
    root = tmp_path / "new-owned-store"
    root.mkdir()
    (root / "owned").write_text("independent synthetic E4")
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / ("crash-" + boundary + ".log")).open("w") as log:
        child = subprocess.Popen(command(root, "crash", boundary), cwd=ROOT / "mobile", stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 180
            while not (root / "barrier.json").exists():
                assert child.poll() is None, "child stopped before its barrier"
                assert time.monotonic() < deadline, "bounded barrier timeout"
                time.sleep(.03)
            barrier = json.loads((root / "barrier.json").read_text())
            os.kill(barrier["pid"], signal.SIGKILL)
            assert child.wait(timeout=45) != 0
        finally:
            # Only this newly created child process group; backend synthetic worker included.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    before = json.loads((root / "before.json").read_text())
    immediate = inspect(Path(before["store_path"]))
    with (OUT / ("recovery-" + boundary + ".log")).open("w") as log:
        reopened = subprocess.run(command(root, "recover", boundary), cwd=ROOT / "mobile", stdout=log, stderr=subprocess.STDOUT, timeout=180)
    assert reopened.returncode == 0
    assert (root / "recovered").read_text() == "data only"
    workspace = root / "segmented-e4-workspace"
    after = inspect(Path(before["store_path"]), workspace)
    marker = (workspace / "offline-mode/online-write-1.json").read_bytes()
    assert marker == base64.b64decode(before["marker"])
    baseline = (workspace / "offline-mode/baseline.json").read_bytes()
    if boundary == "after_frozen_prepare" or boundary.startswith("native_"):
        assert baseline == base64.b64decode(before["baseline"])
        assert after["frozen"][0]["id"] == before["frozen"]
    else:
        assert baseline != base64.b64decode(before["baseline"])
        assert len(after["frozen"]) == 1 and after["frozen"][0]["state"] == "installed"
    if boundary == "native_after_segmented_install_pointer":
        assert after["pointers"]["installed"]["generation_id"] == before["g1"]
    (OUT / ("crash-" + boundary + ".json")).write_text(json.dumps(dict(boundary=boundary, immediate=immediate, recovered=after, marker_sha256=hashlib.sha256(marker).hexdigest(), baseline_sha256=hashlib.sha256(baseline).hexdigest()), ensure_ascii=False, indent=2)+"\n")

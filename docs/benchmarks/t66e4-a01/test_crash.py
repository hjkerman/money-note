"""E4-A01의 source 복원/COMMIT 및 stale recovery 경계에서 실제 SIGKILL."""
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "t66e4-audit"))
from state_oracle import inspect  # noqa: E402

OUT = Path(os.environ.get("E4_A01_OUTPUT", "/tmp/mn-e4-a01/crash"))
BOUNDARIES = ["stale_before_release", "stale_after_conflict",
              "source_restore_before_commit", "source_restore_after_commit",
              "native_source_restore_before_commit", "native_only_source_restore_before_commit"]


def command(root, mode, boundary):
    return ["/home/hjkerman/.flutter/bin/flutter", "test", "--no-pub", "--machine",
            "--dart-define=A01_ROOT=" + str(root), "--dart-define=A01_MODE=" + mode,
            "--dart-define=A01_BOUNDARY=" + boundary, str(HERE / "crash_child_test.dart")]


@pytest.mark.parametrize("boundary", BOUNDARIES)
def test_a01_process_death(tmp_path, boundary):
    root = tmp_path / "owned-e4-a01"
    root.mkdir()
    (root / "owned").write_text("synthetic E4-A01")
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / (boundary + ".log")).open("w") as log:
        child = subprocess.Popen(command(root, "crash", boundary), cwd=ROOT / "mobile",
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 180
            while not (root / "barrier.json").exists():
                assert child.poll() is None, "worker exited before boundary"
                assert time.monotonic() < deadline, "worker boundary timeout"
                time.sleep(.01)
            barrier = json.loads((root / "barrier.json").read_text())
            saved = json.loads((root / "expected.json").read_text())
            if boundary.endswith("source_restore_before_commit"):
                # Observe actual file replacement while the synchronous native
                # COMMIT waits for the other SQLite reader, before killing PID.
                deadline = time.monotonic() + .8
                source = root / "segmented-e4-workspace/e4-source.json"
                while json.loads(source.read_text()) != saved["restored_source"]:
                    assert time.monotonic() < deadline, "source replace not observed"
                    time.sleep(.001)
            os.kill(barrier["pid"], signal.SIGKILL)
            assert child.wait(timeout=45) != 0
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    saved = json.loads((root / "expected.json").read_text())
    immediate_source = (root / "segmented-e4-workspace/e4-source.json").read_bytes()
    immediate = inspect(Path(saved["store_path"]))
    if boundary.endswith("source_restore_before_commit"):
        assert json.loads(immediate_source) == saved["restored_source"], "kill must follow file restore, not completed error compensation"
        assert any(f["id"] == saved["abandoned"] and f["state"] == "prepared"
                   for f in immediate["frozen"]), "kill must precede SQL COMMIT"
    else:
        assert all(f["id"] != saved["abandoned"] for f in immediate["frozen"])
    with (OUT / (boundary + "-reopen.log")).open("w") as log:
        result = subprocess.run(command(root, "recover", boundary), cwd=ROOT / "mobile",
                                stdout=log, stderr=subprocess.STDOUT, timeout=180)
    assert result.returncode == 0
    workspace = root / "segmented-e4-workspace"
    after = inspect(Path(saved["store_path"]), workspace)
    if saved["frozen"] is not None:
        assert len(after["frozen"]) == 1 and after["frozen"][0]["id"] == saved["frozen"]
    else:
        assert not after["frozen"] and after["pointers"]["installed"]["generation_id"] == saved["native_generation"]
    for field, name in [("baseline", "baseline.json"), ("pending", "online-write-1.json")]:
        file = workspace / "offline-mode" / name
        if saved[field] is None:
            assert not file.exists()
        else:
            assert file.read_bytes() == base64.b64decode(saved[field])
    source = (workspace / "e4-source.json").read_bytes()
    current = json.loads(source)
    assert current.get("legacy_frozen", current.get("frozen")) == saved["frozen"]
    if boundary.startswith("stale_"):
        assert source == base64.b64decode(saved["source"])
    evidence = dict(boundary=boundary, expected_frozen=saved["frozen"],
                    immediate_source_sha256=hashlib.sha256(immediate_source).hexdigest(),
                    source_sha256=hashlib.sha256(source).hexdigest(),
                    immediate_frozen=immediate["frozen"], recovered_frozen=after["frozen"],
                    pointers=after["pointers"], objects=after["objects"], pins=after["pins"],
                    legacy=after.get("legacy"), pending_preserved=True, r1_gate="CLOSED")
    (OUT / (boundary + ".json")).write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")

"""소유한 합성 root의 실제 native source/COMMIT 경계에서 tester를 SIGKILL한다."""
import base64
import hashlib
import importlib.util
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

spec = importlib.util.spec_from_file_location("reaudit_collect", HERE.parent / "t66e4-a01-reaudit/collect.py")
compact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compact)
OUT = Path(os.environ.get("E4_RA01_OUTPUT", "/tmp/mn-e4-ra01/crash"))
BOUNDARIES = ["before_source", "after_pointer_before_commit", "after_commit", "during_readback",
              "invalid_rejected", "recovery_before_commit", "recovery_after_commit"]


def command(root, mode, boundary):
    return ["/home/hjkerman/.flutter/bin/flutter", "test", "--no-pub", "--machine",
            "--dart-define=RA01_ROOT=" + str(root), "--dart-define=RA01_MODE=" + mode,
            "--dart-define=RA01_BOUNDARY=" + boundary, str(HERE / "crash_child_test.dart")]


@pytest.mark.parametrize("boundary", BOUNDARIES)
def test_native_source_process_death(tmp_path, boundary):
    root = tmp_path / "owned-ra01"
    root.mkdir()
    (root / "owned").write_text("synthetic E4-RA01")
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / (boundary + ".log")).open("w") as log:
        child = subprocess.Popen(command(root, "crash", boundary), cwd=ROOT / "mobile",
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 180
            while not (root / "barrier.json").exists():
                assert child.poll() is None, "worker exited before durable boundary"
                assert time.monotonic() < deadline, "worker boundary timeout"
                time.sleep(.01)
            barrier = json.loads((root / "barrier.json").read_text())
            saved = json.loads((root / "expected.json").read_text())
            os.kill(barrier["pid"], signal.SIGKILL)
            assert child.wait(timeout=45) != 0
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    workspace = root / "segmented-e4-workspace"
    immediate_source = json.loads((workspace / "e4-source.json").read_text())
    immediate = inspect(Path(saved["store_path"]))
    expected_installed = saved["new_generation"] if boundary in ["after_commit", "during_readback"] else saved["old_installed"]
    assert immediate["pointers"]["installed"]["generation_id"] == expected_installed
    if boundary == "after_pointer_before_commit":
        assert immediate_source["generation"] == saved["new_generation"]
        assert immediate_source["previous_source"] is not None
    with (OUT / (boundary + "-reopen.log")).open("w") as log:
        result = subprocess.run(command(root, "recover", boundary), cwd=ROOT / "mobile",
                                stdout=log, stderr=subprocess.STDOUT, timeout=180)
    assert result.returncode == 0
    after = inspect(Path(saved["store_path"]), workspace)
    recovered = json.loads((root / "recovered.json").read_text())
    assert recovered["frozen_read"] and recovered["r1_gate"] == "CLOSED"
    assert after["pointers"]["installed"]["generation_id"] == expected_installed
    assert len(after["frozen"]) == 1 and after["frozen"][0]["id"] == saved["frozen"]
    for field, name in [("baseline", "baseline.json"), ("pending", "online-write-1.json")]:
        assert (workspace / "offline-mode" / name).read_bytes() == base64.b64decode(saved[field])
    source = (workspace / "e4-source.json").read_bytes()
    association = json.loads(source)
    assert association.get("legacy_frozen", association.get("frozen")) == saved["frozen"]
    if boundary == "invalid_rejected":
        assert recovered["recovery_error"] == "SOURCE_PROVENANCE_REQUIRED"
        assert hashlib.sha256(source).hexdigest() == saved["rejected_source_sha256"]
    elif boundary not in ["after_commit", "during_readback"]:
        # The writer stores a one-level recovery copy with obsolete hints cleared.
        assert association["frozen"] == saved["frozen"]
        assert recovered["recovery_error"] is None
    evidence = dict(boundary=boundary, expected_installed=expected_installed,
                    immediate_source=immediate_source, recovered=recovered,
                    source_sha256=hashlib.sha256(source).hexdigest(),
                    baseline_preserved=True, pending_preserved=True,
                    before_reopen=compact.graph(immediate), after_reopen=compact.graph(after))
    (OUT / (boundary + ".json")).write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")

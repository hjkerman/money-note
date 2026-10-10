"""Actual migrated fixtures, old exporter and independent graph/index oracle."""

from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("target", ["376", "1000", "5000", "10000", "confirmed-heavy"])
def test_full_state_sqlite_snapshot_differential(tmp_path, target):
    harness = Path(__file__).resolve().parents[2] / "scripts/benchmarks/t66d2a.py"
    result = subprocess.run([sys.executable, str(harness), "--output", str(tmp_path / "summary.json"),
                             "--targets", target, "--verify-only"], capture_output=True, text=True, timeout=150)
    assert result.returncode == 0, result.stderr[-4000:]

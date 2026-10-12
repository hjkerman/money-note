"""Recheck the committed differential oracle against the actual backend."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from t66e1_money_vectors import vectors  # noqa: E402


def test_committed_server_money_vectors_are_current():
    stored = json.loads((ROOT / "mobile/test/fixtures/segmented_money_vectors.json").read_text())
    assert stored == vectors()

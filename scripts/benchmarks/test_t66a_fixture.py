"""Actual endpoint reproducibility gate, using freshly migrated synthetic DBs."""

import os
from unittest.mock import patch

from t66a import backend_imports, capture, seed


def test_fixed_context_and_seed_produce_identical_actual_endpoint_bytes(tmp_path):
    with patch.dict(os.environ):
        case_type, clock = backend_imports(tmp_path)
        bodies = []
        for _ in range(2):
            case = case_type()
            case.setUp()
            try:
                seed(case, 376)
                with patch("app.services.snapshot.datetime", clock):
                    response = capture(case)
                wire = response.json()
                assert len(wire["snapshot"]["data"]["ledger_entries"]) == 376
                assert wire["authority"]["evaluation_date"] == "2026-10-05"
                assert wire["snapshot"]["schema_version"] == 7
                assert len(wire["state"]["confirmed_planned_entries"]) == 1
                bodies.append(response.content)
            finally:
                case.tearDown()
        assert bodies[0] == bodies[1]

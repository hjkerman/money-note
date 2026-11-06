"""원 Phase B 16개 보정의 assertion은 그대로, 출력만 분리한다."""

from pathlib import Path
import sys
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "backend"))


class OutputOnly:
    def pytest_collection_modifyitems(self, items):
        for item in items:
            item.module.HERE = HERE / "old-calibration"
            (item.module.HERE / "evidence").mkdir(parents=True, exist_ok=True)


raise SystemExit(
    pytest.main(
        [
            "-q",
            "../docs/benchmarks/t66f-phase-b-final/test_counters.py",
            "--junitxml=" + str(HERE / "evidence/old-calibration-final.xml"),
        ],
        plugins=[OutputOnly()],
    )
)

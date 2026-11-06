"""P03: 현재 교정 회귀만 실행하고 과거 evidence는 덮어쓰지 않는다."""

from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


class Output:
    def pytest_collection_modifyitems(self, items):
        for item in items:
            if item.module.__name__.endswith("test_logical_cost_independent_audit"):
                item.module.OUT = HERE / "evidence/current-original"
                item.module.OUT.mkdir(exist_ok=True)


if __name__ == "__main__":
    raise SystemExit(
        pytest.main(
            [
                "-q",
                "tests/test_logical_cost_ic01.py",
                "tests/test_logical_cost_instrumentation.py",
                "tests/test_logical_cost_independent_audit.py",
                "-k",
                "not test_reproduce_",
                "--junitxml=" + str(HERE / "evidence/backend-targeted.xml"),
            ],
            plugins=[Output()],
        )
    )

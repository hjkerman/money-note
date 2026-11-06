"""원 IC01 assertion 및 승인된 역사 분리를 새 출력 경로로 실행."""

import importlib.util
from pathlib import Path
import sys
import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "p01_original_test_runner", HERE.parent / "t66f-b03-ic01/original_backend.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Output(module.OutputOnly):
    def pytest_collection_modifyitems(self, items):
        for item in items:
            if item.module.__name__.endswith("test_logical_cost_independent_audit"):
                item.module.OUT = HERE / "evidence/current-original"
                item.module.OUT.mkdir(exist_ok=True)


if __name__ == "__main__":
    sys.argv.append("--current")
    raise SystemExit(
        pytest.main(
            [
                "-q",
                *(
                    []
                    if "--full" in sys.argv
                    else [
                        "tests/test_logical_cost_ic01.py",
                        "tests/test_logical_cost_instrumentation.py",
                        "tests/test_logical_cost_independent_audit.py",
                    ]
                ),
                "--junitxml="
                + str(
                    HERE
                    / (
                        "evidence/backend-full.xml"
                        if "--full" in sys.argv
                        else "evidence/backend-targeted.xml"
                    )
                ),
            ],
            plugins=[Output()],
        )
    )

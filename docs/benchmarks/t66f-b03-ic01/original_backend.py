"""원 독립 assertion은 그대로 실행하고 evidence 출력 경로만 분리한다."""

from pathlib import Path
import importlib.util
import sys
import pytest

HERE = Path(__file__).resolve().parent


class OutputOnly:
    def pytest_collection_modifyitems(self, items):
        for item in items:
            if item.module.__name__.endswith("test_logical_cost_independent_audit"):
                item.module.OUT = (
                    HERE
                    / "evidence"
                    / (
                        "current-original"
                        if "--current" in sys.argv
                        else "baseline-original"
                    )
                )
                item.module.OUT.mkdir(exist_ok=True)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        historical = (
            "--current" in sys.argv
            and item.module.__name__.endswith("test_logical_cost_independent_audit")
            and item.name.startswith("test_reproduce_")
        )
        if historical:
            spec = importlib.util.spec_from_file_location(
                "ic01_historical_cost", HERE / "historical/counters.py"
            )
            frozen = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(frozen)
            current = item.module.cost
            item.module.cost = frozen
        try:
            yield
        finally:
            if historical:
                item.module.cost = current


if __name__ == "__main__":
    args = ["-q"]
    if "--full" not in sys.argv:
        args += (
            [
                "tests/test_logical_cost_independent_audit.py",
                "tests/test_logical_cost_ic01.py",
                "tests/test_logical_cost_instrumentation.py",
            ]
            if "--current" in sys.argv
            else ["tests/test_logical_cost_independent_audit.py"]
        )
    name = (
        "backend-final"
        if "--final" in sys.argv
        else "backend-full"
        if "--full" in sys.argv
        else ("current-original" if "--current" in sys.argv else "baseline-original")
    )
    if "--sealed" in sys.argv:
        name = "backend-sealed"
    raise SystemExit(
        pytest.main(
            args + ["--junitxml=" + str(HERE / "evidence" / (name + ".xml"))],
            plugins=[OutputOnly()],
        )
    )

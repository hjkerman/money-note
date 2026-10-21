"""독립 감사 실행기. 원 증거를 덮어쓰지 않고 합성 환경만 전달한다."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    "independent_bounded_runner", HERE.parent / "t66f-phase-b-final/run_checks.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.OUT = HERE / "evidence"
runner.OUT.mkdir(exist_ok=True)
runner.COMMANDS["backend-full"] = (
    "backend",
    [
        runner.PYTHON,
        "-m",
        "pytest",
        "-q",
        "--junitxml=" + str(runner.OUT / "backend-full.xml"),
    ],
)
runner.COMMANDS["backend-calibration"] = (
    "backend",
    [
        runner.PYTHON,
        "-m",
        "pytest",
        "-q",
        "tests/test_logical_cost_instrumentation.py",
        "tests/test_logical_cost_independent_audit.py",
        "../docs/benchmarks/t66f-phase-b-final/test_counters.py",
        "--junitxml=" + str(runner.OUT / "backend-calibration.xml"),
    ],
)
runner.COMMANDS["flutter-independent"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        "test/segmented_logical_cost_independent_audit_test.dart",
    ],
)
runner.COMMANDS["flutter-calibration"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        "--concurrency=2",
        "--dart-define=B03_OUTPUT=" + str(runner.OUT / "fresh"),
        "test/segmented_logical_cost_test.dart",
        "test/segmented_logical_cost_lineage_test.dart",
        "test/segmented_logical_cost_boundaries_test.dart",
        "test/segmented_logical_cost_http_test.dart",
        "test/segmented_logical_cost_source_lock_test.dart",
        "test/segmented_adapter_isolation_test.dart",
    ],
)
runner.COMMANDS["authority"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        "--dart-define=B03_STALE_OUTPUT=" + str(runner.OUT / "authority"),
        str(HERE.parent / "t66f-b03/authority_test.dart"),
    ],
)
runner.COMMANDS["independent-http"] = (
    "mobile",
    [runner.FLUTTER, "test", "--no-pub", "--machine", str(HERE / "http_test.dart")],
)
runner.COMMANDS["independent-http-serial"] = runner.COMMANDS["independent-http"]
runner.COMMANDS["overhead-python"] = (".", [runner.PYTHON, str(HERE / "overhead.py")])
runner.COMMANDS["overhead-python-final"] = runner.COMMANDS["overhead-python"]
runner.COMMANDS["overhead-python-complete"] = runner.COMMANDS["overhead-python"]
runner.COMMANDS["overhead-flutter"] = (
    "mobile",
    [runner.FLUTTER, "test", "--no-pub", "--machine", str(HERE / "overhead_test.dart")],
)
runner.COMMANDS["overhead-flutter-complete"] = runner.COMMANDS["overhead-flutter"]
runner.COMMANDS["ruff"] = (
    ".",
    [
        str(ROOT / ".venv/bin/ruff"),
        "check",
        "backend/app",
        "backend/isolated_sync",
        "backend/tests",
        "scripts",
        str(HERE),
        str(HERE.parent / "t66f-b03"),
    ],
)
runner.COMMANDS["compileall"] = (
    ".",
    [
        runner.PYTHON,
        "-m",
        "compileall",
        "-q",
        "backend/app",
        "backend/isolated_sync",
        "backend/tests",
        "scripts",
        str(HERE),
        str(HERE.parent / "t66f-b03"),
    ],
)
runner.COMMANDS["ruff-final"] = runner.COMMANDS["ruff"]
runner.COMMANDS["compileall-final"] = runner.COMMANDS["compileall"]
runner.COMMANDS["python-format"] = (
    ".",
    [
        str(ROOT / ".venv/bin/ruff"),
        "format",
        "--check",
        str(HERE),
        "backend/tests/test_logical_cost_independent_audit.py",
    ],
)
runner.COMMANDS["dart-format"] = (
    ".",
    [
        "/home/hjkerman/.flutter/bin/dart",
        "format",
        "--output=none",
        "--set-exit-if-changed",
        "mobile/test/segmented_logical_cost_independent_audit_test.dart",
        str(HERE / "http_test.dart"),
        str(HERE / "overhead_test.dart"),
    ],
)
runner.COMMANDS["probe-analyze"] = (
    ".",
    [
        "/home/hjkerman/.flutter/bin/dart",
        "--packages=mobile/.dart_tool/package_config.json",
        "analyze",
        str(HERE / "http_test.dart"),
        str(HERE / "overhead_test.dart"),
    ],
)
runner.COMMANDS["diff-check"] = (".", ["git", "diff", "--check"])
if __name__ == "__main__":
    sys.exit(runner.run(sys.argv[1]))

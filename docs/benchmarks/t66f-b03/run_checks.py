"""기존 bounded runner를 재사용하며 B03 증거 경로만 분리한다."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    "b03_bounded_runner", HERE.parent / "t66f-phase-b-final/run_checks.py"
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
    ],
)
runner.COMMANDS["format"] = (
    ".",
    [
        str(ROOT / ".venv/bin/ruff"),
        "format",
        "--check",
        str(HERE),
        "backend/tests/test_logical_cost_instrumentation.py",
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
    ],
)
for mode in ["analyze", "ruff", "format", "compileall"]:
    runner.COMMANDS["final-" + mode] = runner.COMMANDS[mode]
runner.COMMANDS["final-dart-format"] = (
    "mobile",
    [
        "/home/hjkerman/.flutter/bin/dart",
        "format",
        "--output=none",
        "--set-exit-if-changed",
        "lib/src/app_state.dart",
        "lib/src/authoritative_bundle_validation.dart",
        "lib/src/segmented/c1.dart",
        "lib/src/segmented/store.dart",
        "lib/src/diagnostics/logical_cost.dart",
        "lib/src/offline/offline_store.dart",
        "test/segmented_logical_cost_test.dart",
        "test/segmented_logical_cost_http_test.dart",
        "test/segmented_logical_cost_overhead_test.dart",
        "test/segmented_logical_cost_lineage_test.dart",
        "test/segmented_logical_cost_boundaries_test.dart",
        "test/segmented_logical_cost_source_lock_test.dart",
        "test/segmented_adapter_isolation_test.dart",
        "test/support/logical_cost_reopen.dart",
        "test/support/logical_cost_sqlite.dart",
        "test/support/logical_cost_files.dart",
        "test/support/logical_cost_source_lock.dart",
        "../docs/benchmarks/t66f-b03/fresh_frozen_test.dart",
        "../docs/benchmarks/t66f-b03/authority_test.dart",
    ],
)
runner.COMMANDS["final-diff-check"] = (".", ["git", "diff", "--check"])
runner.COMMANDS["approved-backend-full"] = (
    "backend",
    [
        runner.PYTHON,
        "-m",
        "pytest",
        "-q",
        "--junitxml=" + str(runner.OUT / "approved-backend-full.xml"),
    ],
)
runner.COMMANDS["approved-flutter-full"] = runner.COMMANDS["flutter-full"]
for mode in ["analyze", "build", "frontend", "ruff", "format", "compileall"]:
    runner.COMMANDS["approved-" + mode] = runner.COMMANDS[mode]
    runner.COMMANDS["lineage-" + mode] = runner.COMMANDS[mode]
runner.COMMANDS["lineage-backend-full"] = (
    "backend",
    [
        runner.PYTHON,
        "-m",
        "pytest",
        "-q",
        "--junitxml=" + str(runner.OUT / "lineage-backend-full.xml"),
    ],
)
runner.COMMANDS["lineage-flutter-full"] = runner.COMMANDS["flutter-full"]
runner.COMMANDS["lineage-dart-format"] = runner.COMMANDS["final-dart-format"]
for mode in ["ruff", "format", "compileall"]:
    runner.COMMANDS["closing-" + mode] = runner.COMMANDS[mode]
runner.COMMANDS["closing-authority-analyze"] = (
    ".",
    [
        "/home/hjkerman/.flutter/bin/dart",
        "--packages=mobile/.dart_tool/package_config.json",
        "analyze",
        "docs/benchmarks/t66f-b03/authority_test.dart",
        "docs/benchmarks/t66f-b03/fresh_frozen_test.dart",
    ],
)
for mode in [
    "flutter-full",
    "analyze",
    "build",
    "frontend",
    "ruff",
    "format",
    "compileall",
]:
    runner.COMMANDS["sealed-" + mode] = runner.COMMANDS[mode]
runner.COMMANDS["sealed-dart-format"] = runner.COMMANDS["final-dart-format"]
runner.COMMANDS["sealed-authority-analyze"] = runner.COMMANDS[
    "closing-authority-analyze"
]

if __name__ == "__main__":
    sys.exit(runner.run(sys.argv[1]))

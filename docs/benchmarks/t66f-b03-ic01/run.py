"""IC01 합성 실행. 역사 감사의 로그·assertion을 덮어쓰지 않는다."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    "ic01_bounded_runner", HERE.parent / "t66f-phase-b-final/run_checks.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.OUT = HERE / "evidence"
runner.OUT.mkdir(exist_ok=True)
runner.COMMANDS["baseline-backend"] = (
    "backend",
    [runner.PYTHON, str(HERE / "original_backend.py")],
)
runner.COMMANDS["baseline-flutter"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        "test/segmented_logical_cost_independent_audit_test.dart",
    ],
)
runner.COMMANDS["baseline-direct"] = (
    ".",
    [runner.PYTHON, str(HERE / "original_direct.py")],
)
runner.COMMANDS["backend-current"] = (
    "backend",
    [runner.PYTHON, str(HERE / "original_backend.py"), "--current"],
)
runner.COMMANDS["backend-full"] = (
    "backend",
    [runner.PYTHON, str(HERE / "original_backend.py"), "--current", "--full"],
)
runner.COMMANDS["flutter-full"] = (".", [runner.PYTHON, str(HERE / "flutter_full.py")])
runner.COMMANDS["flutter-current"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        "test/segmented_logical_cost_ic01_test.dart",
        "test/segmented_logical_cost_test.dart",
    ],
)
runner.COMMANDS["independent-http"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        str(HERE / "current_http_test.dart"),
    ],
)
runner.COMMANDS["overhead-flutter"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        str(HERE / "current_overhead_test.dart"),
    ],
)
runner.COMMANDS["high-n-sample"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        str(HERE / "high_n_sample_test.dart"),
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
runner.COMMANDS["backend-final"] = (
    "backend",
    [
        runner.PYTHON,
        str(HERE / "original_backend.py"),
        "--current",
        "--full",
        "--final",
    ],
)
runner.COMMANDS["flutter-final"] = (
    ".",
    [runner.PYTHON, str(HERE / "flutter_full.py"), "--final"],
)
runner.COMMANDS["backend-sealed"] = (
    "backend",
    [
        runner.PYTHON,
        str(HERE / "original_backend.py"),
        "--current",
        "--full",
        "--sealed",
    ],
)
runner.COMMANDS["flutter-sealed"] = (
    ".",
    [runner.PYTHON, str(HERE / "flutter_full.py"), "--sealed"],
)
runner.COMMANDS["flutter-current-11"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        "test/segmented_logical_cost_independent_audit_test.dart",
        "--name",
        r"^(?!.*independent SQL defect reproducer).*$",
    ],
)
runner.COMMANDS["high-n-sample-final"] = runner.COMMANDS["high-n-sample"]
runner.COMMANDS["historical-final"] = (
    "mobile",
    [
        runner.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        str(HERE / "historical_flutter_test.dart"),
        "--plain-name",
        "independent SQL defect reproducer",
    ],
)
if __name__ == "__main__":
    sys.exit(runner.run(sys.argv[1]))

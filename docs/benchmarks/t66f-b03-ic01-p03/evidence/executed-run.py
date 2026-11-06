"""P03 유한 runner: 원 evidence 불변, 실제 exit/resource guard 보존."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "p03_runner", HERE.parent / "t66f-phase-b-final/run_checks.py"
)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
r.OUT = HERE / "evidence"
r.COMMANDS["backend-targeted"] = ("backend", [r.PYTHON, str(HERE / "preflight.py")])
r.COMMANDS["flutter-targeted"] = (
    "mobile",
    [
        r.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        "test/segmented_logical_cost_ic01_test.dart",
        "test/segmented_logical_cost_p02_test.dart",
        "test/segmented_logical_cost_test.dart",
        "test/segmented_logical_cost_boundaries_test.dart",
        "test/segmented_logical_cost_lineage_test.dart",
        "test/segmented_logical_cost_source_lock_test.dart",
    ],
)
for name in ["small-http", "real-path"]:
    r.COMMANDS[name] = (
        "mobile",
        [
            r.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            str(HERE / (name.replace("-", "_") + "_test.dart")),
        ],
    )
r.COMMANDS["harness-smoke"] = ("mobile", [r.FLUTTER, "test", "--no-pub", "--machine", "--dart-define=P03_SMOKE=true", str(HERE/"real_path_test.dart")])
if __name__ == "__main__":
    raise SystemExit(r.run(sys.argv[1]))

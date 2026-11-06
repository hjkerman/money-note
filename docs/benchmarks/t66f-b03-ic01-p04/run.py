"""P04 유한 진단 runner. 새100k cold 명령은 제공하지 않는다."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "p04_runner", HERE.parent / "t66f-phase-b-final/run_checks.py"
)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
r.OUT = HERE / "evidence"
r.COMMANDS.clear()
r.COMMANDS["backend-targeted"] = ("backend", [r.PYTHON, str(HERE / "backend_tests.py")])
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
        "test/segmented_fetch_test.dart",
        "test/segmented_authority_test.dart",
    ],
)
for mode, name in [
    ("component", "component_test.dart"),
    ("small-http", "small_http_test.dart"),
    ("namespace", "namespace_test.dart"),
]:
    r.COMMANDS[mode] = (
        "mobile",
        [r.FLUTTER, "test", "--no-pub", "--machine", str(HERE / name)],
    )
r.COMMANDS["frontend"] = ("frontend", ["npm", "run", "build"])

if __name__ == "__main__":
    raise SystemExit(r.run(sys.argv[1]))

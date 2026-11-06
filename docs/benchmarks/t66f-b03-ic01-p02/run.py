"""P02 bounded runner: 기존 evidence를 덮어쓰지 않는다."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "p02_runner", HERE.parent / "t66f-phase-b-final/run_checks.py"
)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
r.OUT = HERE / "evidence"
for name, file in {
    "new-tests": "../../../mobile/test/segmented_logical_cost_p02_test.dart",
    "components": "components_test.dart",
    "preparation": "prepare_cost_test.dart",
    "cleanup": "cleanup_test.dart",
    "small-http": "small_http_test.dart",
}.items():
    r.COMMANDS[name] = (
        "mobile",
        [r.FLUTTER, "test", "--no-pub", "--machine", str((HERE / file).resolve())],
    )
r.COMMANDS["flutter-targeted"] = (
    "mobile",
    [
        r.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        "test/segmented_logical_cost_ic01_test.dart",
        "test/segmented_logical_cost_test.dart",
        "test/segmented_logical_cost_boundaries_test.dart",
        "test/segmented_logical_cost_lineage_test.dart",
        "test/segmented_logical_cost_source_lock_test.dart",
    ],
)
r.COMMANDS["current-independent"] = (
    "mobile",
    [
        r.FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        "test/segmented_logical_cost_independent_audit_test.dart",
        "--name",
        r"^(?!.*independent SQL defect reproducer).*$",
    ],
)
r.COMMANDS["backend-targeted"] = ("backend", [r.PYTHON, str(HERE / "backend_tests.py")])
r.COMMANDS["backend-full"] = (
    "backend",
    [r.PYTHON, str(HERE / "backend_tests.py"), "--full"],
)
r.COMMANDS["flutter-full"] = (".", [r.PYTHON, str(HERE / "flutter_full.py")])
if __name__ == "__main__":
    r.COMMANDS["new-tests-final"] = r.COMMANDS["new-tests"]
    r.COMMANDS["new-tests-corrected"] = r.COMMANDS["new-tests"]
    r.COMMANDS["new-tests-sealed"] = r.COMMANDS["new-tests"]
    r.COMMANDS["cached-busy"] = (
        "mobile",
        [
            r.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            str(HERE / "cached_busy_test.dart"),
        ],
    )
    r.COMMANDS["cached-busy-final"] = r.COMMANDS["cached-busy"]
    r.COMMANDS["small-http-final"] = r.COMMANDS["small-http"]
    r.COMMANDS["components-final"] = (
        "mobile",
        [
            r.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            "--dart-define=P02_FINAL=true",
            str(HERE / "components_test.dart"),
        ],
    )
    r.COMMANDS["preparation-final"] = (
        "mobile",
        [
            r.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            "--dart-define=P02_FINAL=true",
            str(HERE / "prepare_cost_test.dart"),
        ],
    )
    r.COMMANDS["independent-overhead"] = (
        "mobile",
        [
            r.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            str(HERE / "independent_overhead_test.dart"),
        ],
    )
    r.COMMANDS["authority"] = (
        "mobile",
        [
            r.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            "--dart-define=B03_STALE_OUTPUT=" + str(r.OUT / "authority"),
            str(HERE.parent / "t66f-b03/authority_test.dart"),
        ],
    )
    for mode, closed in [("cleanup-open", "false"), ("cleanup-closed", "true")]:
        r.COMMANDS[mode] = (
            "mobile",
            [
                r.FLUTTER,
                "test",
                "--no-pub",
                "--machine",
                "--dart-define=P02_CLOSE_CLIENT=" + closed,
                str(HERE / "cleanup_test.dart"),
            ],
        )
        r.COMMANDS[mode + "-final"] = (
            "mobile",
            [
                r.FLUTTER,
                "test",
                "--no-pub",
                "--machine",
                "--dart-define=P02_FINAL=true",
                "--dart-define=P02_CLOSE_CLIENT=" + closed,
                str(HERE / "cleanup_test.dart"),
            ],
        )
    raise SystemExit(r.run(sys.argv[1]))

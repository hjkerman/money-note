"""P01 유한 실행. 기존 IC01 evidence는 수정하지 않는다."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "p01_bounded_runner", HERE.parent / "t66f-phase-b-final/run_checks.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.OUT = HERE / "evidence"
module.OUT.mkdir(exist_ok=True)
module.COMMANDS.update(
    {
        "backend-targeted": (
            "backend",
            [module.PYTHON, str(HERE / "backend_tests.py")],
        ),
        "flutter-targeted": (
            "mobile",
            [
                module.FLUTTER,
                "test",
                "--no-pub",
                "--machine",
                "test/segmented_logical_cost_ic01_test.dart",
                "test/segmented_logical_cost_test.dart",
            ],
        ),
        "current-independent": (
            "mobile",
            [
                module.FLUTTER,
                "test",
                "--no-pub",
                "--machine",
                "test/segmented_logical_cost_independent_audit_test.dart",
                "--name",
                r"^(?!.*independent SQL defect reproducer).*$",
            ],
        ),
        "small-http": (
            "mobile",
            [
                module.FLUTTER,
                "test",
                "--no-pub",
                "--machine",
                str(HERE / "small_http_test.dart"),
            ],
        ),
        "components": (
            "mobile",
            [
                module.FLUTTER,
                "test",
                "--no-pub",
                "--machine",
                str(HERE / "components_test.dart"),
            ],
        ),
    }
)
if __name__ == "__main__":
    module.COMMANDS["preparation"] = (
        "mobile",
        [
            module.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            str(HERE / "prepare_cost_test.dart"),
        ],
    )
    module.COMMANDS["boundaries"] = (
        "mobile",
        [
            module.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            "test/segmented_logical_cost_boundaries_test.dart",
            "test/segmented_logical_cost_lineage_test.dart",
            "test/segmented_logical_cost_source_lock_test.dart",
        ],
    )
    module.COMMANDS["components-final"] = module.COMMANDS["components"]
    module.COMMANDS["components-no-profile"] = (
        "mobile",
        [
            module.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            "--dart-define=P01_PROFILE=false",
            str(HERE / "components_test.dart"),
        ],
    )
    module.COMMANDS["cost-parts"] = (
        "mobile",
        [
            module.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            str(HERE / "cost_parts_test.dart"),
        ],
    )
    module.COMMANDS["cost-parts-final"] = module.COMMANDS["cost-parts"]
    module.COMMANDS["cleanup"] = (
        "mobile",
        [
            module.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            str(HERE / "cleanup_test.dart"),
        ],
    )
    module.COMMANDS["historical-3"] = (
        "mobile",
        [
            module.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            str(HERE / "historical_flutter_test.dart"),
            "--plain-name",
            "independent SQL defect reproducer",
        ],
    )
    module.COMMANDS["packets"] = (
        "mobile",
        [
            module.FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            str(HERE / "packets_test.dart"),
        ],
    )
    raise SystemExit(module.run(sys.argv[1]))

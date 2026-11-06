"""최종 진단 소스 정적 검증과 실제 exit/log 기록."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("p02_static", HERE / "run.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
r = module.r
paths = [
    "backend/app",
    "backend/isolated_sync",
    "backend/tests",
    "scripts",
    "docs/benchmarks/t66f-b03/counters.py",
    "docs/benchmarks/t66f-b03/server.py",
    str(HERE),
]
live_dart = [str(p) for p in HERE.glob("*.dart") if p.name != "original_sqlite.dart"]
live_dart += [
    "mobile/test/support/logical_cost_sqlite.dart",
    "mobile/test/segmented_logical_cost_p02_test.dart",
]
r.COMMANDS.update(
    {
        "ruff-final": (".", [str(r.ROOT / ".venv/bin/ruff"), "check", *paths]),
        "compileall-final": (".", [r.PYTHON, "-m", "compileall", "-q", *paths]),
        "python-format-final": (
            ".",
            [
                str(r.ROOT / ".venv/bin/ruff"),
                "format",
                "--check",
                str(HERE),
                "docs/benchmarks/t66f-b03/counters.py",
                "docs/benchmarks/t66f-b03/server.py",
            ],
        ),
        "dart-format-final": (
            ".",
            [
                "/home/hjkerman/.flutter/bin/dart",
                "format",
                "--output=none",
                "--set-exit-if-changed",
                *live_dart,
            ],
        ),
        "frozen-format-final": (
            ".",
            [
                "/home/hjkerman/.flutter/bin/dart",
                "format",
                "--language-version=3.3",
                "--output=none",
                "--set-exit-if-changed",
                str(HERE / "original_sqlite.dart"),
            ],
        ),
        "diagnostic-analyze-final": (
            ".",
            [
                "/home/hjkerman/.flutter/bin/dart",
                "--packages=mobile/.dart_tool/package_config.json",
                "analyze",
                str(HERE),
            ],
        ),
        "diff-check-final": (".", ["git", "diff", "--check"]),
    }
)
if __name__ == "__main__":
    r.COMMANDS["dart-format-corrected"] = r.COMMANDS["dart-format-final"]
    defaults = [
        "ruff-final",
        "compileall-final",
        "python-format-final",
        "dart-format-final",
        "frozen-format-final",
        "diagnostic-analyze-final",
        "diff-check-final",
    ]
    if "--sealed" in sys.argv or "--closing" in sys.argv:
        suffix = "-closing" if "--closing" in sys.argv else "-sealed"
        for mode in defaults:
            r.COMMANDS[mode + suffix] = r.COMMANDS[mode]
        modes = [mode + suffix for mode in defaults]
    else:
        modes = [sys.argv[1]] if len(sys.argv) > 1 else defaults
    results = [r.run(mode) for mode in modes]
    raise SystemExit(int(any(results)))

"""읽기 전용 Git/format/static 최종 확인. stage/commit/push는 하지 않는다."""

import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"
PYTHON = str(ROOT / ".venv/bin/python")
RUFF = str(ROOT / ".venv/bin/ruff")
DART = "/home/hjkerman/.flutter/bin/cache/dart-sdk/bin/dart"


def main():
    live_python = [str(p.relative_to(ROOT)) for p in HERE.glob("*.py")]
    checks = {
        "ruff": [
            RUFF,
            "check",
            "backend",
            "scripts",
            "docs/benchmarks/t66f-b03",
            str(HERE),
        ],
        "compileall": [
            PYTHON,
            "-m",
            "compileall",
            "-q",
            "backend",
            "scripts",
            "docs/benchmarks/t66f-b03",
            str(HERE),
        ],
        "python_format": [
            RUFF,
            "format",
            "--check",
            "docs/benchmarks/t66f-b03/counters.py",
            "docs/benchmarks/t66f-b03/server.py",
            "backend/tests/test_logical_cost_ic01.py",
            *live_python,
        ],
        "dart_format": [
            DART,
            "format",
            "--output=none",
            "--set-exit-if-changed",
            "mobile/test/support/logical_cost_sqlite.dart",
            "mobile/test/segmented_logical_cost_ic01_test.dart",
            str(HERE / "high_n_sample_test.dart"),
            str(HERE / "current_http_test.dart"),
            str(HERE / "current_overhead_test.dart"),
        ],
        "historical_adapter_format": [
            DART,
            "format",
            "--language-version=3.3",
            "--output=none",
            "--set-exit-if-changed",
            str(HERE / "historical_flutter_test.dart"),
        ],
        "high_n_analyze": [
            DART,
            "--packages=mobile/.dart_tool/package_config.json",
            "analyze",
            str(HERE / "high_n_sample_test.dart"),
        ],
        "diff_check": ["git", "diff", "--check"],
        "sealed_source": [PYTHON, str(HERE / "freeze.py")],
        "historical_preservation": [PYTHON, str(HERE / "inventory.py")],
    }
    results = {}
    for label, command in checks.items():
        with (OUT / ("final-" + label + ".log")).open("w") as log:
            r = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        results[label] = {"command": command, "exit_code": r.returncode}
    git = {}
    for label, command in {
        "refs": ["git", "rev-parse", "HEAD", "main", "origin/main"],
        "actual_remote_main": ["git", "ls-remote", "origin", "refs/heads/main"],
        "status": ["git", "status", "--short"],
        "staged": ["git", "diff", "--cached", "--name-only"],
        "stat": ["git", "diff", "--stat"],
    }.items():
        r = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=60
        )
        git[label] = {
            "command": command,
            "exit_code": r.returncode,
            "output": r.stdout,
            "error": r.stderr,
        }
    value = {
        "checks": results,
        "git": git,
        "commit": "NONE",
        "push": "NOT PERFORMED",
        "worktree": "DIRTY — INTENTIONAL",
        "reason": "100k enabled observation lease readiness remains INCONCLUSIVE",
    }
    (OUT / "final-state.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({k: v["exit_code"] for k, v in results.items()}))
    if any(v["exit_code"] for v in results.values()) or any(
        v["exit_code"] for v in git.values()
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

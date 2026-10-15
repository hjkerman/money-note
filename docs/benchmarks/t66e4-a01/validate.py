"""격리 checkout의 비배포 정적 검사/빌드 exit와 시간을 수집한다."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]


def main(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    flutter = "/home/hjkerman/.flutter/bin/flutter"
    dart = "/home/hjkerman/.flutter/bin/dart"
    python = str(ROOT / ".venv/bin/python")
    checks = [
        ("analyze", [flutter, "analyze", "--no-pub"], "mobile"),
        ("build", [flutter, "build", "apk", "--debug", "--no-pub", "--dart-define=MONEY_NOTE_API_BASE_URL=https://a01.invalid"], "mobile"),
        ("format", [dart, "format", "--output=none", "--set-exit-if-changed", "mobile/lib/src/segmented/workspace.dart",
                    "mobile/lib/src/segmented/store_frozen.dart", "mobile/test/segmented_e4_a01_test.dart",
                    "docs/benchmarks/t66e4-a01/crash_child_test.dart",
                    "docs/benchmarks/t66e4-a01/concurrent_recovery_test.dart"], "."),
        ("ruff", [python, "-m", "ruff", "check", "backend/app", "backend/tests", "scripts/local_deploy.py",
                  "scripts/tests", "docs/benchmarks/t66e4-a01"], "."),
        ("compileall", [python, "-m", "compileall", "-q", "backend/app", "backend/tests", "scripts", "docs/benchmarks/t66e4-a01"], "."),
        ("frontend_test", ["npm", "--prefix", "frontend", "test"], "."),
        ("frontend_build", ["npm", "--prefix", "frontend", "run", "build"], "."),
        ("p0_preservation", [python, "docs/benchmarks/t66e4-targeted/verify_preservation.py"], "."),
        ("historical_hashes", ["sha256sum", "-c", "docs/benchmarks/t66e4-p0/preserved-history.sha256"], "."),
        ("diff_check", ["git", "diff", "--check"], "."),
    ]
    results = {}
    for name, command, cwd in checks:
        start = time.monotonic()
        with (folder / (name + "-validated.log")).open("w") as log:
            p = subprocess.run(command, cwd=ROOT / cwd, stdout=log, stderr=subprocess.STDOUT, timeout=600)
        results[name] = dict(exit=p.returncode, seconds=time.monotonic() - start, command=command)
        if p.returncode:
            print(name, "FAIL", "\n".join((folder / (name + "-validated.log")).read_text().splitlines()[-12:]))
    (folder / "checks.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({k: v["exit"] for k, v in results.items()}))
    return int(any(v["exit"] for v in results.values()))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))

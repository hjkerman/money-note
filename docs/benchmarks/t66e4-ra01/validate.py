"""비배포 정적 검사·build 및 기존 P0/역사적 증거 보존을 기록한다."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRODUCT = {"mobile/lib/src/app_state.dart", "mobile/lib/src/segmented/store_frozen.dart",
           "mobile/lib/src/segmented/workspace.dart"}


def preservation():
    inventory = json.loads((HERE / "baseline-inventory.json").read_text())
    unchanged, changed = [], []
    for row in inventory["files"]:
        path = row["path"]
        digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        if path in PRODUCT:
            changed.append(path)
        else:
            assert digest == row["sha256"], path
            unchanged.append(path)
    assert set(changed) == PRODUCT
    return dict(unchanged=unchanged, authorized_product_paths=changed)


def main(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    flutter, dart = "/home/hjkerman/.flutter/bin/flutter", "/home/hjkerman/.flutter/bin/dart"
    python = str(ROOT / ".venv/bin/python")
    checks = [
        ("analyze", [flutter, "analyze", "--no-pub"], "mobile"),
        ("build", [flutter, "build", "apk", "--debug", "--no-pub",
                   "--dart-define=MONEY_NOTE_API_BASE_URL=https://ra01.invalid"], "mobile"),
        ("format", [dart, "format", "--output=none", "--set-exit-if-changed",
                    *sorted(PRODUCT), "mobile/test/segmented_e4_ra01_test.dart",
                    "docs/benchmarks/t66e4-ra01/crash_child_test.dart",
                    "docs/benchmarks/t66e4-ra01/cost_test.dart",
                    "docs/benchmarks/t66e4-ra01/corruption_selector_test.dart"], "."),
        ("ruff", [python, "-m", "ruff", "check", "backend/app", "backend/tests",
                  "scripts/local_deploy.py", "scripts/tests", "docs/benchmarks/t66e4-ra01"], "."),
        ("compileall", [python, "-m", "compileall", "-q", "backend/app", "backend/tests",
                        "scripts", "docs/benchmarks/t66e4-ra01"], "."),
        ("frontend_test", ["npm", "--prefix", "frontend", "test"], "."),
        ("frontend_build", ["npm", "--prefix", "frontend", "run", "build"], "."),
        ("p0_preservation", [python, "docs/benchmarks/t66e4-targeted/verify_preservation.py"], "."),
        ("historical_hashes", ["sha256sum", "-c", "docs/benchmarks/t66e4-p0/preserved-history.sha256"], "."),
        ("scripts", [python, "-m", "pytest", "-q", "scripts/tests",
                     "--junitxml=" + str(folder / "scripts.xml")], "."),
        ("diff_check", ["git", "diff", "--check"], "."),
    ]
    results = {}
    for name, command, cwd in checks:
        start = time.monotonic()
        with (folder / (name + ".log")).open("w") as log:
            p = subprocess.run(command, cwd=ROOT / cwd, stdout=log,
                               stderr=subprocess.STDOUT, timeout=900)
        results[name] = dict(exit=p.returncode, seconds=time.monotonic() - start, command=command)
        if p.returncode:
            print(name, "FAIL", "\n".join((folder / (name + ".log")).read_text().splitlines()[-12:]))
    results["preservation"] = preservation()
    (folder / "checks.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({k: v["exit"] for k, v in results.items() if "exit" in v}))
    return int(any(v["exit"] for v in results.values() if "exit" in v))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))

"""감사 회귀의 명령·실제 exit·전체 JUnit/machine evidence를 보존한다."""

import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
out = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
out.mkdir(parents=True, exist_ok=True)
flutter = "/home/hjkerman/.flutter/bin/flutter"
commands = {
    "backend-full": (
        ROOT / "backend",
        [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "pytest",
            "-q",
            "--junitxml=" + str(out / "backend-full.xml"),
        ],
    ),
    "flutter-full": (
        ROOT / "mobile",
        [flutter, "test", "--no-pub", "--machine", "--concurrency=2"],
    ),
    "analyze": (ROOT / "mobile", [flutter, "analyze", "--no-pub"]),
    "build": (
        ROOT / "mobile",
        [
            flutter,
            "build",
            "apk",
            "--debug",
            "--no-pub",
            "--dart-define=MONEY_NOTE_API_BASE_URL=https://continuation.invalid",
        ],
    ),
    "ruff": (
        ROOT,
        [
            str(ROOT / ".venv/bin/ruff"),
            "check",
            "backend/app",
            "backend/isolated_sync",
            "backend/tests",
            "scripts",
            "docs/benchmarks/t66f-phase-b-continuation",
        ],
    ),
    "compileall": (
        ROOT,
        [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "compileall",
            "-q",
            "backend/app",
            "backend/isolated_sync",
            "backend/tests",
            "scripts",
            "docs/benchmarks/t66f-phase-b-continuation",
        ],
    ),
    "frontend": (ROOT, ["npm", "--prefix", "frontend", "run", "build"]),
    "format-python": (
        ROOT,
        [
            str(ROOT / ".venv/bin/ruff"),
            "format",
            "--check",
            "docs/benchmarks/t66f-phase-b-continuation",
        ],
    ),
    "format-dart": (
        ROOT,
        [
            "/home/hjkerman/.flutter/bin/dart",
            "format",
            "--output=none",
            "--set-exit-if-changed",
            "docs/benchmarks/t66f-phase-b-continuation",
        ],
    ),
}
cwd, command = commands[mode]
start = time.time()
record = dict(command=command, cwd=str(cwd), start_unix=start, status="RUNNING")
(out / (mode + "-process.json")).write_text(json.dumps(record, indent=2))
with (out / (mode + ".log")).open("w") as log:
    result = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
record.update(
    end_unix=time.time(),
    seconds=time.time() - start,
    exit=result.returncode,
    status="PASS" if result.returncode == 0 else "FAIL",
)
(out / (mode + "-process.json")).write_text(json.dumps(record, indent=2))
print(json.dumps(record))
if result.returncode:
    print("\n".join((out / (mode + ".log")).read_text().splitlines()[-20:]))
sys.exit(result.returncode)

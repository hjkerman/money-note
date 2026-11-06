"""승인된 분리로 모든 default Flutter case 실행. SKIP/XFAIL 추가 없음."""

import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = (
    "sealed-" if "--sealed" in sys.argv else ("final-" if "--final" in sys.argv else "")
)
FLUTTER = "/home/hjkerman/.flutter/bin/flutter"
original = "test/segmented_logical_cost_independent_audit_test.dart"
files = sorted(
    str(p.relative_to(ROOT / "mobile"))
    for p in (ROOT / "mobile/test").rglob("*_test.dart")
    if str(p.relative_to(ROOT / "mobile")) != original
)
commands = [
    [FLUTTER, "test", "--no-pub", "--machine", "--concurrency=4", *files],
    [
        FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        original,
        "--name",
        r"^(?!.*independent SQL defect reproducer).*$",
    ],
    [
        FLUTTER,
        "test",
        "--no-pub",
        "--machine",
        str(HERE / "historical_flutter_test.dart"),
        "--plain-name",
        "independent SQL defect reproducer",
    ],
]
results = []
for i, command in enumerate(commands):
    target = HERE / "evidence" / f"{PREFIX}flutter-full-part-{i}.jsonl"
    started = time.monotonic()
    with target.open("w") as log:
        result = subprocess.run(
            command, cwd=ROOT / "mobile", stdout=log, stderr=subprocess.STDOUT
        )
    results.append(
        {
            "command": command,
            "exit_code": result.returncode,
            "seconds": time.monotonic() - started,
            "output": target.name,
        }
    )
    print(json.dumps({"part": i, "exit_code": result.returncode}), flush=True)
(HERE / f"evidence/{PREFIX}flutter-full-parts.json").write_text(
    json.dumps(results, indent=2) + "\n"
)
sys.exit(int(any(r["exit_code"] for r in results)))

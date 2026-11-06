"""최종 회귀가 실제로 검증한 diagnostic source의 exact revision 기록."""

import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
paths = [
    "docs/benchmarks/t66f-b03/counters.py",
    "docs/benchmarks/t66f-b03/server.py",
    "mobile/test/support/logical_cost_sqlite.dart",
    "backend/tests/test_logical_cost_ic01.py",
    "mobile/test/segmented_logical_cost_ic01_test.dart",
]
value = {
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT)
    .decode()
    .strip(),
    "files": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
}
target = HERE / "evidence/sealed-source.json"
if target.exists():
    assert json.loads(target.read_text()) == value, "실행 중 source가 바뀌었다"
else:
    target.write_text(json.dumps(value, indent=2) + "\n")
print("sealed source exact", len(paths))

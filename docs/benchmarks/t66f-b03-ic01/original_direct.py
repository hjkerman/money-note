"""원 직접 실험의 세 code block을 수정 없이 별도 child에서 재실행한다."""

import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
raw = (HERE.parent / "t66f-b03-independent/evidence/direct-experiments.md").read_text()
blocks = re.findall(r"```python\n(.*?)```", raw, flags=re.S)
assert len(blocks) == 3
results = []
for finding, block in zip(["IA05", "IA06", "IA07"], blocks):
    result = subprocess.run(
        [sys.executable, "-c", block],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    results.append(
        dict(
            finding=finding,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
    )
(HERE / "evidence/baseline-direct-results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps(results, ensure_ascii=False))
assert all(row["exit_code"] == 0 for row in results)

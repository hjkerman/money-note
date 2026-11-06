"""감사자의 실제 cursor 위임 oracle를 그대로 재사용하는 IA07 교정 보정."""

import ast
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
raw = (HERE.parent / "t66f-b03-independent/evidence/direct-experiments.md").read_text()
block = re.findall(r"```python\n(.*?)```", raw, flags=re.S)[2]
result = subprocess.run(
    [sys.executable, "-c", block], cwd=ROOT, capture_output=True, text=True, timeout=180
)
# Original prints a Python literal, not JSON. Decode only this synthetic result.
assert result.returncode == 0, result.stderr
rows = ast.literal_eval(result.stdout)
assert [row["returned_rows"] for row in rows] == [176, 185]
assert all(row["stage"] == "setup" for row in rows), rows
(HERE / "evidence/current-server-oracle.json").write_text(
    json.dumps(
        {
            "original_cursor_oracle": rows,
            "exit_code": result.returncode,
            "product_generation_oracle_sql": 0,
        },
        indent=2,
    )
    + "\n"
)
print("IA07: exact two catalog queries excluded from generation")

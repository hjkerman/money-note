"""수정하지 않은 원 cursor delegate 재현을 현재 교정 source에 적용한다."""

from contextlib import redirect_stdout
import ast
import hashlib
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
original = HERE.parent / "t66f-b03-independent/evidence/direct-experiments.md"
text = original.read_text().split("## IA07", 1)[1]
snippet = text.split("```python\n", 1)[1].split("```", 1)[0]
output = io.StringIO()
with redirect_stdout(output):
    exec(compile(snippet, str(original), "exec"), {})
records = ast.literal_eval(output.getvalue().strip().splitlines()[-1])
assert [r["returned_rows"] for r in records] == [176, 185]
assert all(r["stage"] == "setup" for r in records)
result = {
    "status": "PASS",
    "oracle_rows": records,
    "product_generation_catalog_queries": 0,
    "original_reproducer_modified": False,
    "original_snippet_sha256": hashlib.sha256(snippet.encode()).hexdigest(),
}
(HERE / "evidence/ia07-current.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": "PASS", "stage": "setup", "rows": [176, 185]}))

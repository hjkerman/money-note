"""원 assertion·IC01 source는 유지하고 새 출력 adapter만 생성."""

import ast
import asyncio
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"
source = HERE.parent / "t66f-b03-ic01"
for old, new in [
    ("current_http_test.dart", "small_http_test.dart"),
    ("historical_flutter_test.dart", "historical_flutter_test.dart"),
]:
    raw = (
        (source / old)
        .read_text()
        .replace(
            "/docs/benchmarks/t66f-b03-ic01/evidence",
            "/docs/benchmarks/t66f-b03-ic01-p01/evidence",
        )
    )
    raw = raw.replace(
        "'historical/logical_cost_sqlite.dart'",
        "'../t66f-b03-ic01/historical/logical_cost_sqlite.dart'",
    )
    (HERE / new).write_text(raw)
raw = (HERE.parent / "t66f-b03-independent/evidence/direct-experiments.md").read_text()
code = re.findall(r"```python\n(.*?)```", raw, re.S)[2]
r = subprocess.run(
    [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=180
)
assert r.returncode == 0, r.stderr
rows = ast.literal_eval(r.stdout)
assert [r["returned_rows"] for r in rows] == [176, 185]
assert all(r["stage"] == "setup" for r in rows)
(OUT / "ia07.json").write_text(
    json.dumps({"actual_rows": rows, "product_generation_oracle_queries": 0}, indent=2)
    + "\n"
)

spec = importlib.util.spec_from_file_location(
    "p01_ic01_reproductions", source / "collect_reproductions.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
current = m.load(HERE.parent / "t66f-b03/counters.py", "p01_current")
result = m.sql_cases(current)
result["IA05"] = asyncio.run(m.rejected(current))
result["IA06"] = m.owners(current)
(OUT / "current-finding-values.json").write_text(json.dumps(result, indent=2) + "\n")

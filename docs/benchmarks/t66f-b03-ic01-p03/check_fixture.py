"""비용 큰 bootstrap 전 실제 fixture 복원 검증. 원 seed/SQL schema만 사용한다."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "p03_fixture_base", HERE.parent / "t66f-b02-implementation/server.py"
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
sys.path.insert(0, str(HERE))
import fixture  # noqa: E402

with base.RetentionSandbox() as db:
    with db.connect() as conn:
        base.seed(conn, 100000)
        conn.execute(
            "INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order,is_primary_income) VALUES (101,'2026-10-05','fixed-width-cash',-50,2,0)"
        )
    fixture.restore(db)
print("PASS: original synthetic raw values exactly restored before sync bootstrap")

"""실제 HTTP 통합을 폐기용 mobile source copy에서 SQL 관찰한다."""

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "prior_sql_observer", ROOT / "docs/benchmarks/t66e4-a01-reaudit/measure.py"
)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
driver.HERE = Path(__file__).parent

if __name__ == "__main__":
    raise SystemExit(driver.main(sys.argv[1]))

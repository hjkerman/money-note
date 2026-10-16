"""원 독립 SQL driver를 재사용하되 새 시나리오와 새 fixture 규모를 측정한다."""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'independent_sql_driver', HERE.parent / 't66e4-a01-reaudit/measure.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
driver.HERE = HERE

if __name__ == '__main__':
    raise SystemExit(driver.main(sys.argv[1]))

"""검증된 SQL observer를 제품의 폐기용 copy에만 연결한다."""

import importlib.util
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
original = ROOT / "docs/benchmarks/t66e4-a01-reaudit/measure.py"
spec = importlib.util.spec_from_file_location("temporary_sql_copy", original)
driver = importlib.util.module_from_spec(spec)
source = original.read_text()
assert source.count("timeout=1500") == 1
needle = 'str(HERE / "cost_test.dart"),'
assert source.count(needle) == 1
test_file = os.environ.get("COST_TEST", "cost_test.dart")
assert test_file in ["cost_test.dart", "unique_cost_test.dart"]
source = source.replace("cost_test.dart", test_file)
needle = 'str(HERE / "' + test_file + '"),'
n = int(os.environ.get("COST_N", "1000"))
assert n in [1000, 5000, 10000, 50000, 100000]
source = source.replace("timeout=1500", "timeout=43200").replace(
    needle, f'"--dart-define=COST_N={n}", ' + needle
)
exec(compile(source, str(original), "exec"), driver.__dict__)
driver.HERE = Path(__file__).parent
if __name__ == "__main__":
    raise SystemExit(driver.main(sys.argv[1]))

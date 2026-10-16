"""원 SQL observer를 변경하지 않고 RA01 시험을 폐기용 source copy에 연결한다."""
import importlib.util
import inspect
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "original_e4_cost", HERE.parent / "t66e4-a01-reaudit/measure.py"
)
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
original.HERE = HERE

# Extend ONLY the disposable SQL observer with exact root-pin owner/hash IDs.
# No body/credential parameters are logged. Original execution/counters remain.
source = inspect.getsource(original.main)
needle = '        store.with_name("audit_trace.dart").write_text(trace)'
assert source.count(needle) == 1
extra = '''        trace = trace.replace("'rows_changed': inner.updatedRows,", "'rows_changed': inner.updatedRows,\\n        if (normalized.startsWith('INSERT INTO generation_roots') || normalized.startsWith('DELETE FROM generations')) 'pin_parameters': List<Object?>.of(parameters),")
'''
exec(compile(source.replace(needle, extra + needle), str(Path(__file__).resolve()), "exec"), original.__dict__)

if __name__ == "__main__":
    raise SystemExit(original.main(sys.argv[1]))

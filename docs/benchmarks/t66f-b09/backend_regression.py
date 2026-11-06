"""현재 회귀를 실행하고 역사 reproducer와 출력 경로만 기존 IC06 방식대로 분리한다."""
import importlib.util,os,sys
from pathlib import Path
import pytest
R=Path(os.environ['B05A_TREE']);E=Path(os.environ['B05A_EVIDENCE']);W=Path(os.environ['B05A_SCRATCH'])
spec=importlib.util.spec_from_file_location('b05_historical',R/'docs/benchmarks/t66f-b03-ic01/original_backend.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Output(m.OutputOnly):
 def pytest_collection_modifyitems(self,items):
  for item in items:
   if item.module.__name__.endswith('test_logical_cost_ic04'):
    item.module.__file__=str(W/'disposable/output-root/backend/tests/test_logical_cost_ic04.py')
   if item.module.__name__.endswith('test_logical_cost_independent_audit'):
    item.module.OUT=E/'original-independent-backend';item.module.OUT.mkdir(exist_ok=True)
args=sys.argv[1:];sys.argv.append('--current')
raise SystemExit(pytest.main(args,plugins=[Output()]))

"""역사 결함존재 assertion과 현재 회귀를 구별하고 출력만 IC06으로 보낸다."""
import importlib.util, os, sys
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[3];O=Path(__file__).parent/'evidence';S=R/'work/t66f-b03-ic06'
spec=importlib.util.spec_from_file_location('ic06_historical',R/'docs/benchmarks/t66f-b03-ic01/original_backend.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Output(m.OutputOnly):
 def pytest_collection_modifyitems(self,items):
  for item in items:
   if item.module.__name__.endswith('test_logical_cost_ic04'):
    item.module.__file__=str(S/'output-root/backend/tests/test_logical_cost_ic04.py')
   if item.module.__name__.endswith('test_logical_cost_independent_audit'):
    item.module.OUT=O/'original-independent-backend';item.module.OUT.mkdir(exist_ok=True)
args=sys.argv[1:];sys.argv.append('--current')
raise SystemExit(pytest.main(args,plugins=[Output()]))

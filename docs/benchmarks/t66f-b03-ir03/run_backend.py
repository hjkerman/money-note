import importlib.util,sys,json
from pathlib import Path
import pytest
ROOT=Path('/tmp/money-note-ir03-20261023'); tree=ROOT/'candidate';out=ROOT/'evidence/backend-original';out.mkdir(exist_ok=True)
class AuditOutput:
 def pytest_collection_modifyitems(self,items):
  for item in items:
   if item.module.__name__.endswith('test_logical_cost_independent_audit'):item.module.OUT=out
 @pytest.hookimpl(hookwrapper=True)
 def pytest_runtest_call(self,item):
  historical=item.module.__name__.endswith('test_logical_cost_independent_audit') and item.name.startswith('test_reproduce_')
  if historical:
   spec=importlib.util.spec_from_file_location('ir03_historical',tree/'docs/benchmarks/t66f-b03-ic01/historical/counters.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);current=item.module.cost;item.module.cost=mod
  try:yield
  finally:
   if historical:item.module.cost=current
args=sys.argv[1:]
raise SystemExit(pytest.main(args,plugins=[AuditOutput()]))

import importlib.util,pytest
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023')
class Control:
 def pytest_collection_modifyitems(self,items):
  for item in items:
   spec=importlib.util.spec_from_file_location('history_ddl',r/'candidate/docs/benchmarks/t66f-b03-ic01/historical/counters.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);item.module.cost=mod;item.module.OUT=r/'evidence/ddl-historical';item.module.OUT.mkdir(exist_ok=True)
raise SystemExit(pytest.main([str(r/'evidence/test_ir03_oracles.py'),'-k','ddl_observer','-q','-p','no:cacheprovider','--junitxml='+str(r/'evidence/ddl-historical.xml')],plugins=[Control()]))

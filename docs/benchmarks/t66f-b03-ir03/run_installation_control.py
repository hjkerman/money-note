import importlib.util,pytest
from pathlib import Path
ROOT=Path('/tmp/money-note-ir03-20261023')
class History:
 def pytest_collection_modifyitems(self,items):
  for item in items:
   spec=importlib.util.spec_from_file_location('history_install',ROOT/'candidate/docs/benchmarks/t66f-b03-ic01/historical/counters.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);item.module.cost=mod
raise SystemExit(pytest.main([str(ROOT/'evidence/test_ir03_installation.py'),'-q','-p','no:cacheprovider','--junitxml='+str(ROOT/'evidence/installation-historical.xml')],plugins=[History()]))

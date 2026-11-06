from pathlib import Path
import importlib.util,sys,pytest
A=Path('/tmp/money-note-ir05-20261024');T=A/'candidate';E=A/'evidence';spec=importlib.util.spec_from_file_location('ir05_original_runner',T/'docs/benchmarks/t66f-b03-ic01/original_backend.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
class Output(old.OutputOnly):
 def pytest_collection_modifyitems(self,items):
  for item in items:
   if item.module.__name__.endswith('test_logical_cost_independent_audit'):item.module.OUT=E/'original-backend';item.module.OUT.mkdir(exist_ok=True)
sys.argv.append('--current')
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp='+str(A/'pytest-focused'),'--junitxml='+str(E/'backend-affected.xml'),'tests/test_logical_cost_ic01.py','tests/test_logical_cost_ic02.py','tests/test_logical_cost_ic03.py','tests/test_logical_cost_instrumentation.py','tests/test_logical_cost_independent_audit.py','tests/test_isolated_sync_transfer_cancellation.py',str(T/'docs/benchmarks/t66f-b03-ic02/test_cached_dml.py')],plugins=[Output()]))

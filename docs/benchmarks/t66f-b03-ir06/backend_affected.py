"""최초 감사의 결함존재 assertion은 동결된 역사 wrapper에서 분리 실행한다."""
import importlib.util
import os
from pathlib import Path
import sys
import pytest

tree=Path(os.environ['IR06_TREE'])
out=Path(os.environ['IR06_EVIDENCE'])
spec=importlib.util.spec_from_file_location('ir06_historical_split',tree/'docs/benchmarks/t66f-b03-ic01/original_backend.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class Output(module.OutputOnly):
    def pytest_collection_modifyitems(self,items):
        for item in items:
            if item.module.__name__.endswith('test_logical_cost_independent_audit'):
                item.module.OUT=out/'original-independent-backend';item.module.OUT.mkdir(exist_ok=True)
sys.argv.append('--current')
targets=['test_logical_cost_independent_audit.py','test_logical_cost_instrumentation.py','test_logical_cost_ic01.py','test_logical_cost_ic02.py','test_logical_cost_ic03.py','test_logical_cost_ic04.py','test_logical_cost_ic05.py','test_isolated_sync_transfer.py']
raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','--basetemp='+str(tree.parent/'pytest-regression'),'--junitxml='+str(out/'backend-affected.xml'),*[str(tree/'backend/tests'/n) for n in targets]],plugins=[Output()]))

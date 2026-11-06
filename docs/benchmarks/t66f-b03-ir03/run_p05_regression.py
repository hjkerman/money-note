import sys,pytest
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');source=r/'candidate/docs/benchmarks/t66f-b03-ic01-p05';sys.path[:0]=[str(source),str(r/'candidate/backend')];out=r/'p05-scratch';out.mkdir();case=out/'run';case.mkdir();(case/'artifacts').mkdir()
class Output:
 def pytest_collection_modifyitems(self,items):
  for item in items:
   item.module.EVIDENCE=out;item.module.CASE=case;item.module.ARTIFACTS=case/'artifacts'
raise SystemExit(pytest.main([str(source/'test_handoff.py'),'-q','-p','no:cacheprovider','--basetemp='+str(r/'p05-pytest'),'--junitxml='+str(r/'evidence/p05.xml')],plugins=[Output()]))

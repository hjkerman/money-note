from pathlib import Path
import pytest,sys
class Output:
 def pytest_collection_modifyitems(self,items):
  for item in items:
   if item.module.__name__.endswith("test_ir03_triggers"):
    item.module.r=Path("/tmp/money-note-ic02.8Z1pd5")
raise SystemExit(pytest.main(["-q","-p","no:cacheprovider",*sys.argv[1:]],plugins=[Output()]))

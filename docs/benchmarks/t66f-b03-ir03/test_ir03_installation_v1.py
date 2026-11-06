"""설치 첫 caller가 preempt된 deterministic thread schedule. 제품 primitive 입력은 불변."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util,json,sys
from pathlib import Path
from threading import Event,current_thread
from unittest.mock import patch
import pytest
TREE=Path('/tmp/money-note-ir03-20261023/candidate');sys.path.insert(0,str(TREE/'backend'))
from isolated_sync import canonical
spec=importlib.util.spec_from_file_location('ir03_install',TREE/'docs/benchmarks/t66f-b03/counters.py');cost=importlib.util.module_from_spec(spec);spec.loader.exec_module(cost)

def test_concurrent_first_install_is_ready_before_second_scope_returns():
 entered=Event();resume=Event();first=cost.Collector();second=cost.Collector();NativeStack=cost.ExitStack
 class PausedStack(NativeStack):
  def enter_context(self,cm):
   if not entered.is_set():
    entered.set();assert resume.wait(10)
   return super().enter_context(cm)
 def owner1():
  with cost.instrument(),first.stage('transfer'):canonical.decode_c1(b'{}')
 def owner2():
  assert entered.wait(10)
  try:
   with cost.instrument(),second.stage('observation'):canonical.decode_c1(b'{}')
  finally:resume.set()
 with patch.object(cost,'ExitStack',PausedStack),ThreadPoolExecutor(2) as pool:
  a=pool.submit(owner1);b=pool.submit(owner2);a.result(timeout=15);b.result(timeout=15)
 record={'expected_second_calls':1,'expected_second_span':2,'first':first.snapshot(),'second':second.snapshot(),'registries_after':dict(cost.INSTALLATIONS)}
 (Path(__file__).parent/'concurrent-installation.json').write_text(json.dumps(record,indent=2)+'\n')
 assert second.values['observation/json/calls']==1
 assert second.values['observation/json/submitted_bytes']==2
 assert not cost.INSTALLATIONS

"""독립 scheduling oracle: 원 parser를 변경하지 않고 설치 진입/patch 경계만 정지한다."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from threading import Event,Lock,current_thread
from pathlib import Path
from unittest.mock import patch
import importlib.util,json,sys
import pytest
A=Path('/tmp/money-note-ir05-20261024');T=A/'candidate';sys.path.insert(0,str(T/'backend'))
from isolated_sync import canonical

def load():
 spec=importlib.util.spec_from_file_location('ir04_independent_cost',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def emit(name,value):(A/'evidence'/(name+'.json')).write_text(json.dumps(value,indent=2))

@pytest.mark.parametrize('count',[2,4])
def test_real_first_patch_waiters_exact_ownership(count):
 m=load();paused=Event();resume=Event();waiting=Event();lock=Lock();n=[0];real_patch=m.install_patch;real_wait=m.wait_for_installation
 native_parse=canonical._parse_json;native_encode=canonical.encode
 def controlled(stack,target,name,value):
  if target is canonical and name=='_parse_json':paused.set();assert resume.wait(10)
  return real_patch(stack,target,name,value)
 def wait(state):
  with lock:
   n[0]+=1
   if n[0]==count-1:waiting.set()
  return real_wait(state)
 collectors=[m.Collector() for _ in range(count)];payload=[json.dumps({'v':'한😀'+'x'*i},ensure_ascii=False,separators=(',',':')).encode() for i in range(count)]
 def work(i):
  with m.instrument(),collectors[i].stage('transfer'):assert canonical.decode_c1(payload[i])['v']=='한😀'+'x'*i
 with patch.object(m,'install_patch',controlled),patch.object(m,'wait_for_installation',wait),ThreadPoolExecutor(count) as pool:
  futures=[pool.submit(work,0)];assert paused.wait(10)
  futures += [pool.submit(work,i) for i in range(1,count)];assert waiting.wait(10)
  assert all(not f.done() for f in futures);resume.set()
  for f in futures:f.result(timeout=15)
 observed=[c.snapshot() for c in collectors];emit('first-install-'+str(count),{'payload_lengths':list(map(len,payload)),'counters':observed,'registry_empty':not m.INSTALLATIONS})
 for i,c in enumerate(collectors):assert c.values['transfer/json/calls']==1 and c.values['transfer/json/submitted_bytes']==len(payload[i])
 assert not m.INSTALLATIONS and canonical._parse_json is native_parse and canonical.encode is native_encode


def test_install_failure_waiter_cleanup_then_new_scope():
 m=load();paused=Event();resume=Event();waiting=Event();real=m.install_patch;real_wait=m.wait_for_installation;native=canonical._parse_json
 def install(stack,target,name,value):
  if target is canonical and name=='encode':paused.set();assert resume.wait(10);raise RuntimeError('IR04 injected installation failure')
  return real(stack,target,name,value)
 def wait(state):waiting.set();return real_wait(state)
 def work():
  with m.instrument():pytest.fail('failed installer body must never execute')
 with patch.object(m,'install_patch',install),patch.object(m,'wait_for_installation',wait),ThreadPoolExecutor(2) as pool:
  a=pool.submit(work);assert paused.wait(10);b=pool.submit(work);assert waiting.wait(10);resume.set()
  with pytest.raises(RuntimeError,match='IR04 injected'):a.result(timeout=15)
  with pytest.raises(RuntimeError,match='installation failed'):b.result(timeout=15)
 assert not m.INSTALLATIONS and canonical._parse_json is native
 c=m.Collector()
 with m.instrument(),c.stage('transfer'):canonical.decode_c1(b'{}')
 assert c.values['transfer/json/submitted_bytes']==2 and c.values['transfer/json/calls']==1
 emit('install-failure-cleanup',{'counters':c.snapshot(),'registry_empty':not m.INSTALLATIONS})


def test_previous_close_overlaps_next_activation_exactly_once():
 m=load();captured=Event();resume=Event();original_installation=m.installation;native_parse=canonical._parse_json;native_encode=canonical.encode;c=m.Collector()
 # A is installed. B captures the delegates, then is preempted immediately before
 # registering its installation reference. This seam is after capture, before lock.
 @contextmanager
 def controlled(name):
  if name=='primitives' and current_thread().name.startswith('ir04-rollover'):
   captured.set();assert resume.wait(10)
  with original_installation(name) as stack:yield stack
 a=m.instrument();a.__enter__()
 def b():
  with m.instrument(),c.stage('observation'):assert canonical.decode_c1(b'{}')=={}
 try:
  with patch.object(m,'installation',controlled),ThreadPoolExecutor(1,thread_name_prefix='ir04-rollover') as pool:
   f=pool.submit(b);assert captured.wait(10);a.__exit__(None,None,None);a=None;resume.set();f.result(timeout=15)
 finally:
  resume.set()
  if a is not None:a.__exit__(None,None,None)
 result={'expected_calls':1,'expected_bytes':2,'actual_calls':c.values['observation/json/calls'],'actual_bytes':c.values['observation/json/submitted_bytes'],'snapshot':c.snapshot(),'registry_empty':not m.INSTALLATIONS,'parser_restored':canonical._parse_json is native_parse,'encoder_restored':canonical.encode is native_encode}
 emit('installation-generation-rollover',result)
 assert result['actual_calls']==1 and result['actual_bytes']==2
 assert not m.INSTALLATIONS and result['parser_restored'] and result['encoder_restored']

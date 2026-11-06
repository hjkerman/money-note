"""IR05 새 수명 oracle. native code entry와 소유권 identity를 기록하고 실제 순서를 Event/trace로 고정한다."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from contextvars import copy_context
from threading import Event,Lock
from pathlib import Path
import asyncio,gc,hashlib,importlib.util,inspect,json,signal,sqlite3,sys,weakref
from unittest.mock import _patch
import pytest
A=Path('/tmp/money-note-ir05-20261024');T=A/'candidate';sys.path.insert(0,str(T/'backend'))
from isolated_sync import canonical
from isolated_sync.workers import NativeJob,WorkerBudget,WorkerLease

def emit(name,v):(A/'evidence'/(name+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def line_of(fn,text):
 lines,start=inspect.getsourcelines(fn);return start+next(i for i,s in enumerate(lines) if text in s)
@pytest.fixture
def cost():
 spec=importlib.util.spec_from_file_location('ir05_lifecycle',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 originals=canonical._parse_json,canonical.encode,hashlib.sha256,sqlite3.connect,NativeJob.__init__,NativeJob._finish,WorkerLease.run;patches=list(_patch._active_patches)
 yield m
 try:
  assert not m.INSTALLATIONS
  assert (canonical._parse_json,canonical.encode,hashlib.sha256,sqlite3.connect,NativeJob.__init__,NativeJob._finish,WorkerLease.run)==originals
  assert list(_patch._active_patches)==patches
 finally:
  for p in list(reversed(_patch._active_patches)):
   if p not in patches:p.stop()

def exact(c,stage,payloads):
 assert c.values[f'{stage}/json/calls']==len(payloads)
 assert c.values[f'{stage}/json/submitted_bytes']==sum(map(len,payloads))
 assert c.values[f'{stage}/json/completed_bytes']==sum(map(len,payloads))
 assert not any(k.endswith('/json/calls') and not k.startswith(stage+'/') for k in c.values)

@pytest.mark.parametrize('count',[3,7])
def test_first_cohort_distinct_scopes_identical_real_events(cost,count):
 m=cost;native=canonical._parse_json;paused=Event();resume=Event();all_waiting=Event();lock=Lock();waiting=[];bodies=[];gate=__import__('threading').Barrier(count)
 payloads=[json.dumps([i,'한😀'+'x'*i],ensure_ascii=False,separators=(',',':')).encode() for i in range(count)];cs=[m.Collector() for _ in range(count)];stages=['setup','generation','observation','transfer','calibration'];seen=[[] for _ in cs];ids=[]
 def work(i):
  def trace(frame,event,arg):
   if event=='call' and frame.f_code is native.__code__:seen[i].append(bytes(frame.f_locals['raw']))
   if i==0 and event=='call' and frame.f_code is m.install_patch.__code__ and frame.f_locals['name']=='_parse_json':paused.set();assert resume.wait(10)
   if i and event=='call' and frame.f_code is m.wait_for_installation.__code__:
    with lock:
     waiting.append(i)
     if len(waiting)==count-1:all_waiting.set()
   return trace
  sys.settrace(trace)
  try:
   with m.instrument(),cs[i].stage(stages[i%len(stages)]):
    with lock:bodies.append(i);ids.append(id(canonical._parse_json))
    assert canonical._parse_json.__wrapped__ is native;gate.wait(10)
    canonical.decode_c1(payloads[i]);canonical.decode_c1(payloads[i])
  finally:sys.settrace(None)
 with ThreadPoolExecutor(count) as pool:
  fs=[pool.submit(work,0)];assert paused.wait(10);fs += [pool.submit(work,i) for i in range(1,count)]
  try:
   assert all_waiting.wait(10);assert not bodies;assert m.INSTALLATIONS['primitives']['refs']==count;assert not m.INSTALLATIONS['primitives']['ready'].is_set()
  finally:resume.set()
  for f in fs:f.result(timeout=15)
 for i,c in enumerate(cs):assert seen[i]==[payloads[i],payloads[i]];exact(c,stages[i%len(stages)],seen[i])
 assert len(set(ids))==1
 emit('lifecycle-cohort-'+str(count),{'payload_bytes':list(map(len,payloads)),'native_calls':[len(v) for v in seen],'shared_wrapper_count':len(set(ids)),'snapshots':[c.snapshot() for c in cs],'registry_empty':not m.INSTALLATIONS})

@pytest.mark.parametrize('phase',['before_restore','after_restore'])
def test_new_generation_cannot_enter_until_locked_teardown_completes(cost,phase):
 m=cost;native=canonical._parse_json;old=m.instrument();old.__enter__();state=m.INSTALLATIONS['primitives'];old_wrapper=canonical._parse_json;closed_paused=Event();release_close=Event();attempted=Event();new_body=Event();continue_body=Event();c=m.Collector();new_ids=[];native_calls=[]
 fn=m.installation.__wrapped__;close_line=line_of(fn,'state["stack"].close()');after_line=line_of(fn,'if INSTALLATIONS.get(name) is state:');acquire_line=line_of(fn,'with INSTALL_LOCK:')
 def close():
  def trace(frame,event,arg):
   if event=='line' and frame.f_code is fn.__code__ and frame.f_lineno==(close_line if phase=='before_restore' else after_line):closed_paused.set();assert release_close.wait(10)
   return trace
  sys.settrace(trace)
  try:old.__exit__(None,None,None)
  finally:sys.settrace(None)
 def activate():
  def trace(frame,event,arg):
   if event=='line' and frame.f_code is fn.__code__ and frame.f_lineno==acquire_line:attempted.set()
   if event=='call' and frame.f_code is native.__code__:native_calls.append(bytes(frame.f_locals['raw']))
   return trace
  sys.settrace(trace)
  try:
   with m.instrument(),c.stage('transfer'):
    new_ids.extend([id(m.INSTALLATIONS['primitives']),id(canonical._parse_json)]);new_body.set();assert continue_body.wait(10)
    assert canonical._parse_json.__wrapped__ is native
    canonical.decode_c1(b'{}');canonical.decode_c1(b'{}')
  finally:sys.settrace(None)
 with ThreadPoolExecutor(2) as pool:
  a=pool.submit(close);assert closed_paused.wait(10);b=pool.submit(activate)
  try:
   assert attempted.wait(10);assert not new_body.is_set();assert state['refs']==0
   assert (canonical._parse_json is native)==(phase=='after_restore')
  finally:release_close.set()
  try:
   a.result(timeout=15);assert new_body.wait(10);assert m.INSTALLATIONS['primitives'] is not state;assert id(canonical._parse_json)==new_ids[1]
  finally:continue_body.set()
  b.result(timeout=15)
 assert native_calls==[b'{}',b'{}'];exact(c,'transfer',native_calls)
 emit('lifecycle-handoff-'+phase,{'old_state':id(state),'new_state':new_ids[0],'old_wrapper':id(old_wrapper),'new_wrapper':new_ids[1],'native_calls':len(native_calls),'snapshot':c.snapshot(),'registry_empty':not m.INSTALLATIONS})


def test_native_parse_inflight_survives_other_holder_release(cost):
 m=cost;native=canonical._parse_json;a=m.instrument();a.__enter__();wrapper=canonical._parse_json;entered=Event();resume=Event();c=m.Collector();seen=[];payload='"한😀"'.encode()
 def b():
  def trace(frame,event,arg):
   if event=='call' and frame.f_code is native.__code__:seen.append(bytes(frame.f_locals['raw']));entered.set();assert resume.wait(10)
   return trace
  sys.settrace(trace)
  try:
   with m.instrument(),c.stage('observation'):canonical.decode_c1(payload)
  finally:sys.settrace(None)
 with ThreadPoolExecutor(1) as pool:
  f=pool.submit(b)
  try:
   assert entered.wait(10);assert m.INSTALLATIONS['primitives']['refs']==2;a.__exit__(None,None,None);assert m.INSTALLATIONS['primitives']['refs']==1;assert canonical._parse_json is wrapper
  finally:resume.set()
  f.result(timeout=15)
 assert seen==[payload];exact(c,'observation',seen);emit('lifecycle-inflight-release',{'native_calls':1,'bytes':len(payload),'snapshot':c.snapshot(),'registry_empty':not m.INSTALLATIONS})


def test_250_generations_no_wrapper_depth_or_strong_retention(cost):
 m=cost;native=canonical._parse_json;refs=[];calls=0
 for i in range(250):
  c=m.Collector();other=m.Collector()
  with m.instrument(),c.stage('generation'):
   assert canonical._parse_json.__wrapped__ is native;refs.append(weakref.ref(canonical._parse_json));canonical.decode_c1(b'{}')
   with m.instrument(),m.instrument(),other.stage('transfer'):canonical.decode_c1(b'[]')
   canonical.decode_c1(b'{}')
  exact(c,'generation',[b'{}',b'{}']);exact(other,'transfer',[b'[]']);calls+=3;assert canonical._parse_json is native and not m.INSTALLATIONS
 gc.collect();assert sum(r() is not None for r in refs)==0
 emit('lifecycle-250-generations',{'real_calls':calls,'cycles':250,'retained_wrappers':0,'max_live_registry_kinds':1,'restored_after_every_cycle':True})


def test_mixed_families_three_threads_connection_and_worker_ownership(cost):
 m=cost;functions=[m.instrument,m.instrument_connections,m.instrument_workers];orders=[[0,1,2],[1,2,0],[2,0,1]];gate=__import__('threading').Barrier(3);cs=[m.Collector() for _ in orders];payloads=[b'{}',b'[1]',b'"abcd"'];states=[]
 def work(i):
  async def run():
   with ExitStack() as stack:
    for k in orders[i]:stack.enter_context(functions[k]())
    with cs[i].stage('generation'):
     gate.wait(10);states.append(sorted(m.INSTALLATIONS));budget=WorkerBudget(1);lease=budget.acquire()
     try:assert await lease.run(lambda:canonical.decode_c1(payloads[i]))==__import__('json').loads(payloads[i])
     finally:lease.close()
     assert budget.snapshot()==dict(leases=0,jobs=0,running=0,tasks=0);assert cs[i].pending==0
     d=sqlite3.connect(':memory:',isolation_level=None)
     try:
      d.execute('CREATE TABLE p(b BLOB)');d.execute('INSERT INTO p VALUES(?)',(bytes(range(i+1)),));assert sqlite3.Connection.execute(d,'SELECT length(b) FROM p').fetchone()==(i+1,)
     finally:d.close()
     assert cs[i].values['generation/p/INSERT/committed/blob_bytes']==i+1
  asyncio.run(run())
 with ThreadPoolExecutor(3) as pool:
  fs=[pool.submit(work,i) for i in range(3)]
  for f in fs:f.result(timeout=20)
 for i,c in enumerate(cs):exact(c,'generation',[payloads[i]])
 assert all(s==['connections','primitives','workers'] for s in states)
 emit('lifecycle-mixed-families',{'states':states,'snapshots':[c.snapshot() for c in cs],'pending':[c.pending for c in cs],'registry_empty':not m.INSTALLATIONS})


def test_sigint_before_patch_mutation_is_clean_control(cost):
 m=cost;native=canonical._parse_json;fn=m.install_patch;seam=line_of(fn,'patcher.start()');sent=[]
 def trace(frame,event,arg):
  if event=='line' and frame.f_code is fn.__code__ and frame.f_lineno==seam and not sent:sent.append(True);signal.raise_signal(signal.SIGINT)
  return trace
 sys.settrace(trace)
 try:
  with pytest.raises(KeyboardInterrupt):
   with m.instrument():pytest.fail('cancelled body entered')
 finally:sys.settrace(None)
 assert sent and canonical._parse_json is native and not m.INSTALLATIONS;c=m.Collector()
 with m.instrument(),c.stage('transfer'):canonical.decode_c1(b'{}')
 exact(c,'transfer',[b'{}']);emit('lifecycle-sigint-before-start-control',{'clean':True,'snapshot':c.snapshot()})


def test_async_cancellation_of_one_holder_preserves_surviving_scope(cost):
 m=cost;native=canonical._parse_json;a=m.Collector();b=m.Collector()
 async def run():
  entered=asyncio.Event();release=asyncio.Event()
  async def first():
   with m.instrument(),a.stage('generation'):canonical.decode_c1(b'{}');entered.set();await release.wait()
  task=asyncio.create_task(first());await entered.wait()
  with m.instrument(),b.stage('transfer'):
   wrapper=canonical._parse_json;canonical.decode_c1(b'[]');task.cancel()
   result=await asyncio.gather(task,return_exceptions=True);assert isinstance(result[0],asyncio.CancelledError)
   assert canonical._parse_json is wrapper and m.INSTALLATIONS['primitives']['refs']==1;canonical.decode_c1(b'[]')
 asyncio.run(run());exact(a,'generation',[b'{}']);exact(b,'transfer',[b'[]',b'[]']);assert canonical._parse_json is native
 emit('lifecycle-async-cancel-holder',{'first':a.snapshot(),'survivor':b.snapshot(),'registry_empty':not m.INSTALLATIONS})


def test_late_closed_context_cannot_charge_new_scope(cost):
 m=cost;a=m.Collector();b=m.Collector()
 with a.stage('observation'):late=copy_context()
 a.close();before=a.snapshot()
 with m.instrument(),b.stage('transfer'):
  late.run(canonical.decode_c1,b'{}');canonical.decode_c1(b'[1,2]');canonical.decode_c1(b'[1,2]')
 assert a.snapshot()==before;exact(b,'transfer',[b'[1,2]',b'[1,2]']);assert m.ACTIVE.get() is None
 emit('lifecycle-closed-context',{'closed_snapshot_unchanged':True,'new_snapshot':b.snapshot(),'registry_empty':not m.INSTALLATIONS})

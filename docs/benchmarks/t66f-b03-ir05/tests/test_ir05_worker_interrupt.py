"""공유 설치 helper의 실제 취소가 native worker hold에 미치는 영향을 별도 검증한다."""
from pathlib import Path
import asyncio,importlib.util,inspect,json,signal,sys
from unittest.mock import _patch
import pytest
A=Path('/tmp/money-note-ir05-20261024');T=A/'candidate';sys.path.insert(0,str(T/'backend'))
from isolated_sync.workers import NativeJob,WorkerBudget,WorkerLease

def line_of(fn,text):
 lines,start=inspect.getsourcelines(fn);return start+next(i for i,s in enumerate(lines) if text in s)
@pytest.mark.parametrize('phase',['install','teardown'])
@pytest.mark.parametrize('rejected',[False,True])
def test_interrupted_worker_installation_has_no_orphan_hold(phase,rejected):
 spec=importlib.util.spec_from_file_location('ir05_worker_interrupt',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);native=(NativeJob.__init__,NativeJob._finish,WorkerLease.run);patches=list(_patch._active_patches);sent=[];c=m.Collector();native_init=[]
 if phase=='install':fn=m.install_patch;seam=line_of(fn,'stack.callback(patcher.stop)')
 else:fn=m.installation.__wrapped__;seam=line_of(fn,'state["stack"].close()')
 def trace(frame,event,arg):
  selected=(frame.f_locals.get('target') is NativeJob and frame.f_locals.get('name')=='__init__') if phase=='install' else frame.f_locals.get('name')=='workers'
  if event=='line' and frame.f_code is fn.__code__ and frame.f_lineno==seam and selected and not sent:sent.append(seam);signal.raise_signal(signal.SIGINT)
  return trace
 try:
  if phase=='teardown':ctx=m.instrument_workers();ctx.__enter__()
  sys.settrace(trace)
  try:
   with pytest.raises(KeyboardInterrupt):
    if phase=='install':
     with m.instrument_workers():pytest.fail('cancelled body entered')
    else:ctx.__exit__(None,None,None)
  finally:sys.settrace(None)
  leaked=(NativeJob.__init__,NativeJob._finish,WorkerLease.run)!=native
  def witness(frame,event,arg):
   if event=='call' and frame.f_code is native[0].__code__:native_init.append(1)
  async def run():
   budget=WorkerBudget(1);lease=budget.acquire()
   with m.instrument_workers(),c.stage('transfer'):
    if rejected:
     lease.close()
     with pytest.raises(RuntimeError,match='closed worker lease'):await lease.run(lambda:17)
    else:assert await lease.run(lambda:17)==17;lease.close()
   return budget.snapshot()
  sys.setprofile(witness)
  try:native_state=asyncio.run(run())
  finally:sys.setprofile(None)
  completions=[];c.finish_when_idle(lambda x:completions.append(x.snapshot()))
  result={'phase':phase,'rejected_dispatch':rejected,'actual_signal':'SIGINT','seam':seam,'signal_delivered':bool(sent),'methods_leaked_after_cancel':leaked,'native_init_calls':len(native_init),'native_budget':native_state,'expected_pending':0,'actual_pending':c.pending,'expected_completions':1,'actual_completions':len(completions),'collector_closed':c.closed,'registry_empty':not m.INSTALLATIONS,'extra_active_patches':len([p for p in _patch._active_patches if p not in patches])}
  (A/'evidence'/f'worker-interrupt-{phase}-{rejected}.json').write_text(json.dumps(result,indent=2)+'\n')
  assert sent and len(native_init)==1 and native_state==dict(leases=0,jobs=0,running=0,tasks=0)
  assert c.pending==0 and c.closed and len(completions)==1
  assert not leaked
 finally:
  sys.settrace(None);sys.setprofile(None)
  for p in list(reversed(_patch._active_patches)):
   if p not in patches:p.stop()
  assert (NativeJob.__init__,NativeJob._finish,WorkerLease.run)==native

"""반복 취소의 native 호출 및 실제 보존 wrapper chain을 검사한다."""
from pathlib import Path
import importlib.util,inspect,json,signal,sys
from unittest.mock import _patch
import pytest
A=Path('/tmp/money-note-ir05-20261024');T=A/'candidate';sys.path.insert(0,str(T/'backend'))
from isolated_sync import canonical

def test_repeated_cancelled_starts_do_not_accumulate_wrapper_chain():
 spec=importlib.util.spec_from_file_location('ir05_growth',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);native=canonical._parse_json;patches=list(_patch._active_patches);fn=m.install_patch;lines,start=inspect.getsourcelines(fn);seam=start+next(i for i,s in enumerate(lines) if 'stack.callback(patcher.stop)' in s);history=[];seen=[];c=m.Collector()
 try:
  for i in range(8):
   sent=[]
   def trace(frame,event,arg):
    if event=='line' and frame.f_code is fn.__code__ and frame.f_lineno==seam and frame.f_locals.get('target') is canonical and frame.f_locals.get('name')=='_parse_json' and not sent:sent.append(True);signal.raise_signal(signal.SIGINT)
    return trace
   sys.settrace(trace)
   try:
    with pytest.raises(KeyboardInterrupt):
     with m.instrument():pytest.fail('cancelled body entered')
   finally:sys.settrace(None)
   depth=0;f=canonical._parse_json
   while f is not native and hasattr(f,'__wrapped__'):depth+=1;f=f.__wrapped__
   history.append({'cancelled_starts':i+1,'wrapper_depth':depth,'extra_active_patches':len([p for p in _patch._active_patches if p not in patches]),'registry_empty':not m.INSTALLATIONS})
  def witness(frame,event,arg):
   if event=='call' and frame.f_code is native.__code__:seen.append(bytes(frame.f_locals['raw']))
   return witness
  sys.settrace(witness)
  try:
   with m.instrument(),c.stage('transfer'):canonical.decode_c1(b'{}')
  finally:sys.settrace(None)
  result={'history':history,'native_calls':len(seen),'expected_calls':1,'expected_bytes':2,'actual_calls':c.values['transfer/json/calls'],'actual_bytes':c.values['transfer/json/submitted_bytes'],'counters':c.snapshot()}
  (A/'evidence/interrupted-wrapper-growth.json').write_text(json.dumps(result,indent=2)+'\n')
  assert seen==[b'{}']
  assert history[-1]['wrapper_depth']==0 and history[-1]['extra_active_patches']==0
  assert c.values['transfer/json/calls']==1 and c.values['transfer/json/submitted_bytes']==2
 finally:
  sys.settrace(None)
  for p in list(reversed(_patch._active_patches)):
   if p not in patches:p.stop()
  assert canonical._parse_json is native

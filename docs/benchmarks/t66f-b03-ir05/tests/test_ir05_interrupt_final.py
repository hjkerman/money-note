"""기존 함수 patch 없이 실제 SIGINT를 설치 등록 사이에 전달한다. 테스트 뒤 audit probe만 정리한다."""
from pathlib import Path
import importlib.util,inspect,json,signal,sys
from unittest.mock import _patch
import pytest
A=Path('/tmp/money-note-ir05-20261024');T=A/'candidate';sys.path.insert(0,str(T/'backend'))
from isolated_sync import canonical

def test_sigint_after_native_patch_before_cleanup_registration():
 spec=importlib.util.spec_from_file_location('ir05_interrupt',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 native=canonical._parse_json;before=list(_patch._active_patches);f=m.install_patch;lines,start=inspect.getsourcelines(f);seam=start+next(i for i,line in enumerate(lines) if 'stack.callback(patcher.stop)' in line);interrupts=[];native_calls=[];c=m.Collector()
 def trace(frame,event,arg):
  if event=='line' and frame.f_code is f.__code__ and frame.f_lineno==seam and frame.f_locals['target'] is canonical and frame.f_locals['name']=='_parse_json' and not interrupts:
   interrupts.append({'line':seam,'parser_already_wrapped':canonical._parse_json is not native,'refs':m.INSTALLATIONS['primitives']['refs']});signal.raise_signal(signal.SIGINT)
  return trace
 try:
  sys.settrace(trace)
  try:
   with pytest.raises(KeyboardInterrupt):
    with m.instrument():pytest.fail('cancelled activation must not execute its body')
  finally:sys.settrace(None)
  leaked_after_error=canonical._parse_json is not native
  def witness(frame,event,arg):
   if event=='call' and frame.f_code is native.__code__:native_calls.append(bytes(frame.f_locals['raw']))
   return witness
  sys.settrace(witness)
  try:
   with m.instrument(),c.stage('transfer'):assert canonical.decode_c1(b'{}')=={}
  finally:sys.settrace(None)
  result={'signal':'SIGINT','interrupts':interrupts,'native_calls':len(native_calls),'native_inputs_hex':[b.hex() for b in native_calls],'parser_leaked_after_cancel':leaked_after_error,'parser_restored_after_retry':canonical._parse_json is native,'registry_empty_after':not m.INSTALLATIONS,'extra_active_patches':len([x for x in _patch._active_patches if x not in before]),'expected_calls':1,'expected_bytes':2,'actual_calls':c.values['transfer/json/calls'],'actual_bytes':c.values['transfer/json/submitted_bytes'],'counters':c.snapshot()}
  (A/'evidence/interrupt-after-start-current-final.json').write_text(json.dumps(result,indent=2)+'\n')
  assert interrupts and native_calls==[b'{}']
  assert not leaked_after_error
  assert c.values['transfer/json/calls']==1 and c.values['transfer/json/submitted_bytes']==2
  assert canonical._parse_json is native and not m.INSTALLATIONS
 finally:
  sys.settrace(None)
  for p in list(reversed(_patch._active_patches)):
   if p not in before:p.stop()
  assert canonical._parse_json is native


def test_sigint_during_last_reference_teardown_does_not_retire_wrapped_delegate():
 spec=importlib.util.spec_from_file_location('ir05_teardown_interrupt',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 native=canonical._parse_json;before=list(_patch._active_patches);fn=m.installation.__wrapped__;lines,start=inspect.getsourcelines(fn);seam=start+next(i for i,line in enumerate(lines) if 'state["stack"].close()' in line);interrupts=[];native_calls=[];c=m.Collector();ctx=m.instrument();ctx.__enter__();old=m.INSTALLATIONS['primitives'];retiring=canonical._parse_json
 def trace(frame,event,arg):
  if event=='line' and frame.f_code is fn.__code__ and frame.f_lineno==seam and frame.f_locals.get('name')=='primitives' and not interrupts:
   interrupts.append({'line':seam,'refs':old['refs'],'wrapper_still_installed':canonical._parse_json is retiring});signal.raise_signal(signal.SIGINT)
  return trace
 try:
  sys.settrace(trace)
  try:
   with pytest.raises(KeyboardInterrupt):ctx.__exit__(None,None,None)
  finally:sys.settrace(None)
  retired_registry_empty=not m.INSTALLATIONS;restored_after_error=canonical._parse_json is native
  def witness(frame,event,arg):
   if event=='call' and frame.f_code is native.__code__:native_calls.append(bytes(frame.f_locals['raw']))
   return witness
  sys.settrace(witness)
  try:
   with m.instrument(),c.stage('observation'):assert canonical.decode_c1(b'{}')=={}
  finally:sys.settrace(None)
  result={'signal':'SIGINT','interrupts':interrupts,'retired_registry_empty':retired_registry_empty,'parser_restored_after_cancelled_teardown':restored_after_error,'native_calls':len(native_calls),'native_inputs_hex':[x.hex() for x in native_calls],'registry_empty_after_retry':not m.INSTALLATIONS,'extra_active_patches':len([x for x in _patch._active_patches if x not in before]),'expected_calls':1,'expected_bytes':2,'actual_calls':c.values['observation/json/calls'],'actual_bytes':c.values['observation/json/submitted_bytes'],'counters':c.snapshot()}
  (A/'evidence/interrupt-last-release-current-final.json').write_text(json.dumps(result,indent=2)+'\n')
  assert interrupts and native_calls==[b'{}']
  assert restored_after_error
  assert c.values['observation/json/calls']==1 and c.values['observation/json/submitted_bytes']==2
 finally:
  sys.settrace(None)
  for patcher in list(reversed(_patch._active_patches)):
   if patcher not in before:patcher.stop()
  assert canonical._parse_json is native

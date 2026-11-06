"""진단 함수 patch 없이 Python trace로 자연스러운 preemption을 강제한다."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path
import importlib.util,inspect,json,sys
import pytest
A=Path('/tmp/money-note-ir05-20261024');T=A/'candidate';sys.path.insert(0,str(T/'backend'))
from isolated_sync import canonical
@pytest.mark.parametrize('payload',[b'{}','"한😀"'.encode()])
def test_unmodified_installation_generation_rollover_native_parse_once(payload):
 spec=importlib.util.spec_from_file_location('ir04_rollover_native',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 original=canonical._parse_json;fn=m.instrument.__wrapped__;lines,start=inspect.getsourcelines(fn);seam=start+next(i for i,s in enumerate(lines) if 'with installation("primitives")' in s)
 entered=Event();resume=Event();native_calls=[];c=m.Collector()
 outer=m.instrument();outer.__enter__()
 def worker():
  stopped=False
  def trace(frame,event,arg):
   nonlocal stopped
   if event=='call' and frame.f_code is original.__code__:native_calls.append(bytes(frame.f_locals['raw']))
   if not stopped and event=='line' and frame.f_code is fn.__code__ and frame.f_lineno==seam:
    stopped=True;entered.set();assert resume.wait(10)
   return trace
  sys.settrace(trace)
  try:
   with m.instrument(),c.stage('transfer'):return canonical.decode_c1(payload)
  finally:sys.settrace(None)
 try:
  with ThreadPoolExecutor(1) as pool:
   future=pool.submit(worker);assert entered.wait(10);outer.__exit__(None,None,None);outer=None;resume.set();value=future.result(timeout=15)
 finally:
  resume.set()
  if outer:outer.__exit__(None,None,None)
 result={'source_line':seam,'payload_hex':payload.hex(),'native_parser_calls':len(native_calls),'native_parser_inputs_hex':[x.hex() for x in native_calls],'actual_calls':c.values['transfer/json/calls'],'actual_bytes':c.values['transfer/json/submitted_bytes'],'expected_calls':1,'expected_bytes':len(payload),'snapshot':c.snapshot(),'registry_empty':not m.INSTALLATIONS,'parser_restored':canonical._parse_json is original,'parsed_value':value}
 (A/'evidence'/('rollover-native-'+str(len(payload))+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 assert native_calls==[payload]
 assert result['actual_calls']==1 and result['actual_bytes']==len(payload)
 assert result['registry_empty'] and result['parser_restored']

"""PEP 669의 free_tool_id는 event/callback을 해제하지 않는다."""
import importlib.util
import json
import os
from pathlib import Path
import sys

tree=Path(os.environ['IR06_TREE'])
sys.path.insert(0,str(tree/'backend'))
from isolated_sync import canonical
spec=importlib.util.spec_from_file_location('ir06_pep_probe',tree/'docs/benchmarks/t66f-b03/counters.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
native=canonical._parse_json
context=m.instrument();tool=next(i for i in range(6) if sys.monitoring.get_tool(i) is None)
code=m.OwnershipContext.__enter__.__code__;fired=[];acquisition=[]
def callback(code,offset,value):
    frame=sys._getframe(1)
    if frame.f_code is code and frame.f_locals.get('self') is context:
        fired.append(True)
        acquisition.append({'refs':{k:v['refs'] for k,v in m.INSTALLATIONS.items()},'wrapper_published':canonical._parse_json is not native})
        raise RuntimeError('IR06 released-ID entry return interruption')
sys.monitoring.use_tool_id(tool,'IR06 released tool')
sys.monitoring.register_callback(tool,sys.monitoring.events.PY_RETURN,callback)
sys.monitoring.set_local_events(tool,code,sys.monitoring.events.PY_RETURN)
sys.monitoring.free_tool_id(tool)
result={'tool_name_after_free':sys.monitoring.get_tool(tool),'local_events_after_free':sys.monitoring.get_local_events(tool,code),'body_entered':False}
try:
    try:
        with context:result['body_entered']=True
    except BaseException as error:
        result['exception']=str(error)
    result.update(callback_fired=len(fired),state_at_callback=acquisition,refs_after_interruption={k:v['refs'] for k,v in m.INSTALLATIONS.items()},wrapper_restored_after_interruption=canonical._parse_json is native)
finally:
    # free_tool_id 뒤에도 남은 설정을 명시 해제한다. 실패 상태 기록 뒤 소유 context만 수동 정리한다.
    sys.monitoring.set_local_events(tool,code,0)
    sys.monitoring.register_callback(tool,sys.monitoring.events.PY_RETURN,None)
    context.close()
result['manual_cleanup_restored']=canonical._parse_json is native and not m.INSTALLATIONS
print(json.dumps(result,ensure_ascii=False))
assert result.get('exception')=='B03 monitoring entry observer unsupported; measurement incomplete',result
assert result['refs_after_interruption']=={} and result['wrapper_restored_after_interruption'],result

"""해제된 PEP669 ID의 실제 callback, 취소 scope, 반복 소유권을 분리 기록한다."""
import asyncio
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import sys

tree=Path(os.environ['IR06_TREE']);sys.path.insert(0,str(tree/'backend'))
from isolated_sync import canonical
from isolated_sync.workers import WorkerBudget
spec=importlib.util.spec_from_file_location('ir06_monitor_matrix',tree/'docs/benchmarks/t66f-b03/counters.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
family=sys.argv[1];rounds=int(sys.argv[2]);contexts=[];interrupted=[];at_return=[];target=None;native=canonical._parse_json;cancelled=m.Collector();valid=m.Collector();seen=[];budget_after=None
outer=ExitStack();outer.enter_context(m.instrument());outer.enter_context(valid.stage('generation'))
baseline={k:v['refs'] for k,v in m.INSTALLATIONS.items()}
tool=next(i for i in range(6) if sys.monitoring.get_tool(i) is None);code=m.OwnershipContext.__enter__.__code__
def callback(code,offset,value):
    frame=sys._getframe(1)
    if frame.f_code is code and frame.f_locals.get('self') is target:
        at_return.append({'refs':{k:v['refs'] for k,v in m.INSTALLATIONS.items()},'cancelled_stage_active':m.ACTIVE.get()[0] is cancelled})
        raise RuntimeError('IR06 monitored return interruption')
sys.monitoring.use_tool_id(tool,'IR06 matrix')
sys.monitoring.register_callback(tool,sys.monitoring.events.PY_RETURN,callback)
sys.monitoring.set_local_events(tool,code,sys.monitoring.events.PY_RETURN)
sys.monitoring.free_tool_id(tool)
try:
    for i in range(rounds):
        target={'instrument':m.instrument,'instrument_workers':m.instrument_workers,'stage':lambda:cancelled.stage('transfer')}[family]()
        contexts.append(target)
        try:
            with target:raise AssertionError('cancelled entry body reached')
        except RuntimeError as error:interrupted.append(str(error))
    result={'family':family,'rounds':rounds,'baseline_refs':baseline,'tool_name':sys.monitoring.get_tool(tool),'active_event_mask':sys.monitoring.get_local_events(tool,code),'at_return':at_return,'exceptions':interrupted,'refs_after':{k:v['refs'] for k,v in m.INSTALLATIONS.items()},'cancelled_stage_active_after':m.ACTIVE.get()[0] is cancelled}
    sys.monitoring.use_tool_id(tool,'IR06 matrix cleanup')
    sys.monitoring.set_local_events(tool,code,0);sys.monitoring.register_callback(tool,sys.monitoring.events.PY_RETURN,None);sys.monitoring.free_tool_id(tool)
    def witness(frame,event,arg):
        if event=='call' and frame.f_code is native.__code__:seen.append(bytes(frame.f_locals['raw']))
    sys.setprofile(witness)
    try:
        canonical.decode_c1(b'{}');canonical.decode_c1(b'{}')
    finally:sys.setprofile(None)
    if family=='instrument_workers':
        async def worker():
            budget=WorkerBudget(1);lease=budget.acquire()
            try:
                with m.instrument_workers(),valid.stage('observation'):
                    assert await lease.run(lambda:7)==7
            finally:lease.close()
            for _ in range(100):
                if not budget.snapshot()['tasks']:break
                await asyncio.sleep(.001)
            return budget.snapshot()
        budget_after=asyncio.run(worker())
    result.update(native_inputs_hex=[x.hex() for x in seen],native_calls=len(seen),valid_snapshot=valid.snapshot(),cancelled_snapshot=cancelled.snapshot(),native_pending=valid.pending,native_budget_after=budget_after)
finally:
    if sys.monitoring.get_tool(tool) is None:sys.monitoring.use_tool_id(tool,'IR06 final cleanup')
    sys.monitoring.set_local_events(tool,code,0);sys.monitoring.register_callback(tool,sys.monitoring.events.PY_RETURN,None);sys.monitoring.free_tool_id(tool)
    for context in reversed(contexts):context.close()
    outer.close()
result['manual_cleanup_baseline']=not m.INSTALLATIONS and m.ACTIVE.get() is None and canonical._parse_json is native
print(json.dumps(result,ensure_ascii=False))
assert result['refs_after']==baseline and not result['cancelled_stage_active_after'],result
assert valid.values['generation/json/calls']==2 and cancelled.values['transfer/json/calls']==0,result

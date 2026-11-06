"""이 runtime에서 해제 ID의 setter 도달성을 실제 공개 API로 확인한다."""
import json,sys
m=sys.monitoring;tool=next(i for i in range(6) if m.get_tool(i) is None and m.get_events(i)==0)
def subject():return 1
code=subject.__code__;rows=[]
m.use_tool_id(tool,'IC06 setter reachability');m.free_tool_id(tool)
try:
 for name,args in [('set_events',(tool,m.events.PY_RETURN)),('set_local_events',(tool,code,m.events.PY_RETURN))]:
  try:getattr(m,name)(*args)
  except ValueError as error:rows.append(dict(api=name,result='NOT REACHABLE',exception=type(error).__name__,message=str(error)))
  else:raise AssertionError(name+' accepted released ID unexpectedly')
finally:
 m.use_tool_id(tool,'IC06 setter cleanup');m.set_events(tool,0);m.set_local_events(tool,code,0);m.free_tool_id(tool)
print(json.dumps(dict(runtime=sys.version,tool_id=tool,rows=rows),ensure_ascii=False))

"""실제 CPython monitoring의 할당·해제·재사용과 이벤트 전달을 관측한다."""
import json, sys
m=sys.monitoring; ev=m.events; rows=[]
for scope in ['global','local']:
 tool=next(i for i in range(6) if m.get_tool(i) is None);seen=[]
 def subject():return 7
 code=subject.__code__
 def cb(c,*args):
  if c is code:seen.append('PY_RETURN')
 m.use_tool_id(tool,'IC06 semantics')
 m.register_callback(tool,ev.PY_RETURN,cb)
 setter=(lambda value:m.set_events(tool,value)) if scope=='global' else (lambda value:m.set_local_events(tool,code,value))
 try:
  setter(ev.PY_RETURN)
  for phase in ['allocated-active','released-active','reused-inherited','reused-inactive','released-inactive']:
   if phase.startswith('released'):m.free_tool_id(tool)
   if phase=='reused-inherited':m.use_tool_id(tool,'IC06 reused')
   if phase=='reused-inactive':setter(0)
   before=len(seen);assert subject()==7
   rows.append(dict(scope=scope,phase=phase,tool=tool,name=m.get_tool(tool),global_mask=m.get_events(tool),local_mask=m.get_local_events(tool,code),delivered=len(seen)-before))
  m.use_tool_id(tool,'IC06 callback inspection')
  previous=m.register_callback(tool,ev.PY_RETURN,None)
  assert previous is cb
  rows.append(dict(scope=scope,callback_survived_release_and_reuse=True))
 finally:
  if m.get_tool(tool) is None:m.use_tool_id(tool,'IC06 semantics cleanup')
  setter(0);m.register_callback(tool,ev.PY_RETURN,None);m.free_tool_id(tool)
print(json.dumps(dict(python=sys.version,implementation=sys.implementation.name,events={k:getattr(ev,k) for k in dir(ev) if k.isupper()},rows=rows),ensure_ascii=False))
assert all(r['delivered']==(1 if 'active' in r['phase'] and 'inactive' not in r['phase'] or r['phase']=='reused-inherited' else 0) for r in rows if 'phase' in r)

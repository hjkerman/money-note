"""IR07 독립 PEP669 oracle. 각 상태는 새 CPython process에서 구성한다."""
import concurrent.futures, gc, hashlib, importlib.util, json, os, pathlib, subprocess, sys, threading
T=pathlib.Path(os.environ['IR07_TREE']);E=pathlib.Path(os.environ['IR07_EVIDENCE'])
sys.path.insert(0,str(T/'backend'))

def child(config):
 from isolated_sync import canonical
 from isolated_sync.workers import NativeJob,WorkerLease
 from unittest.mock import _patch
 spec=importlib.util.spec_from_file_location('ir07_cost',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 native=canonical._parse_json;entry=m.OwnershipContext.__enter__.__code__;mon=sys.monitoring;event=mon.events.PY_RETURN
 original=(canonical._parse_json,canonical.encode,hashlib.sha256,NativeJob.__init__,NativeJob._finish,WorkerLease.run);patches=list(_patch._active_patches)
 callbacks=[];used=[];c=m.Collector();r={'configuration':config,'python':sys.version,'implementation':sys.implementation.name}
 def sentinel():return 73
 def callback(code,offset,value):
  if code is sentinel.__code__:callbacks.append(value)
 def clean():
  for tool in used:
   if mon.get_tool(tool) is None:mon.use_tool_id(tool,'IR07 정리')
   mon.set_events(tool,0);mon.set_local_events(tool,entry,0);mon.set_local_events(tool,sentinel.__code__,0);mon.register_callback(tool,event,None);mon.free_tool_id(tool)
 def baseline():
  assert not m.INSTALLATIONS and m.ACTIVE.get() is None and c.pending==0
  assert (canonical._parse_json,canonical.encode,hashlib.sha256,NativeJob.__init__,NativeJob._finish,WorkerLease.run)==original
  assert list(_patch._active_patches)==patches
 def exact():
  raws=[b'{}',b'{}','"한😀"'.encode()];seen=[];inner=m.Collector()
  def profile(frame,event,arg):
   if event=='call' and frame.f_code is native.__code__:seen.append(bytes(frame.f_locals['raw']))
  sys.setprofile(profile)
  try:
   with m.instrument(),c.stage('generation'):
    canonical.decode_c1(raws[0])
    with m.instrument(),inner.stage('transfer'):canonical.decode_c1(raws[2])
    canonical.decode_c1(raws[1])
  finally:sys.setprofile(None)
  assert seen==[raws[0],raws[2],raws[1]]
  assert c.values['generation/json/calls']==2 and c.values['generation/json/submitted_bytes']==4
  assert inner.values['transfer/json/calls']==1 and inner.values['transfer/json/submitted_bytes']==9
  r['recovery']={'native_inputs_hex':[x.hex() for x in seen],'native_calls':3,'native_bytes':13,'generation_calls':2,'generation_bytes':4,'transfer_calls':1,'transfer_bytes':9,'pending':c.pending}
  baseline()
 mode=config['mode'];tool=config.get('tool',0);unsafe=False;acquired=[]
 try:
  if mode not in ['none','inspection','stress','concurrent']:
   used.append(tool);mon.use_tool_id(tool,'IR07 최초')
   if mode!='active_no_callback':mon.register_callback(tool,event,callback)
   active=mode in ['allocated_active','released_active','reused_active','active_no_callback','mixed']
   if mode=='unrelated_local':mon.set_local_events(tool,sentinel.__code__,event)
   elif active:
    mon.set_local_events(tool,entry,event);mon.set_local_events(tool,sentinel.__code__,event)
   if mode=='global_released':mon.set_events(tool,event);active=True
   if mode.startswith('released') or mode=='global_released' or mode=='active_no_callback':mon.free_tool_id(tool)
   if mode.startswith('reused'):
    # 재사용은 남은 활성 mask를 먼저 상속하고 현재 mask를 변경한다.
    mon.set_local_events(tool,entry,event);mon.free_tool_id(tool);mon.use_tool_id(tool,'IR07 재사용')
    r['reuse_inherited_mask']=mon.get_local_events(tool,entry)
    mon.set_local_events(tool,entry,event if active else 0);mon.set_local_events(tool,sentinel.__code__,event if active else 0)
   if mode=='mixed':
    other=(tool+1)%6;used.append(other);mon.use_tool_id(other,'IR07 두번째');mon.register_callback(other,event,callback);mon.set_events(other,event);mon.free_tool_id(other)
    mon.set_local_events(tool,entry,0);mon.set_local_events(tool,sentinel.__code__,0)
   sentinel();unsafe=active
   r.update(tool_id=tool,tool_name=mon.get_tool(tool),global_mask=mon.get_events(tool),entry_local_mask=mon.get_local_events(tool,entry),callback_registered=mode!='active_no_callback',effective_callback_deliveries=len(callbacks),all_tool_masks=[{'id':i,'name':mon.get_tool(i),'global':mon.get_events(i),'entry_local':mon.get_local_events(i,entry)} for i in range(6)])
   assert len(callbacks)==(1 if (active and mode!='active_no_callback') or mode=='unrelated_local' else 0)
  original_install=m.installation
  def track(name):acquired.append(name);return original_install(name)
  m.installation=track
  if mode=='inspection':
   api=config['api'];old=getattr(mon,api) if api!='namespace' else mon
   def bad(*args):raise ValueError('IR07 독립 inspection fault')
   if api=='namespace':sys.monitoring=None
   else:setattr(mon,api,bad)
   try:
    try:
     with m.instrument():raise AssertionError('검사 오류 뒤 본문 실행')
    except RuntimeError as e:assert str(e)=='B03 monitoring state unavailable; measurement incomplete';r['rejection']=str(e)
   finally:
    if api=='namespace':sys.monitoring=old
    else:setattr(mon,api,old)
   assert acquired==[];baseline();r['preacquisition']=True
  elif mode=='stress':
   contexts=[];gc.disable();tool=5;used.append(tool);mon.use_tool_id(tool,'IR07 반복');mon.register_callback(tool,event,callback);mon.set_local_events(tool,entry,event);mon.free_tool_id(tool)
   peak=0
   for i in range(128):
    for factory in [m.instrument,m.instrument_workers,lambda:c.stage('transfer')]:
     context=factory();contexts.append(context)
     try:
      with context:raise AssertionError('거부 본문 실행')
     except RuntimeError as e:assert 'monitoring entry observer unsupported' in str(e)
     baseline();peak=max(peak,len(m.INSTALLATIONS))
   assert acquired==[];r.update(rejections=384,retained_contexts=len(contexts),gc_disabled=True,peak_installations=peak,preacquisition=True)
   clean();used.clear();exact()
   for context in contexts:context.close()
   baseline();gc.enable()
  elif mode=='concurrent':
   gate=threading.Barrier(4);collectors=[m.Collector() for _ in range(4)]
   def worker(i):
    raw=json.dumps({'i':i,'s':'한'*(i+1)},ensure_ascii=False,separators=(',',':')).encode()
    with m.instrument(),collectors[i].stage('observation'):
     gate.wait(timeout=10)
     for _ in range(17):canonical.decode_c1(raw)
     gate.wait(timeout=10)
    assert collectors[i].values['observation/json/calls']==17 and collectors[i].values['observation/json/submitted_bytes']==17*len(raw)
    return {'calls':17,'raw_bytes':len(raw),'recorded_bytes':int(collectors[i].values['observation/json/submitted_bytes'])}
   with concurrent.futures.ThreadPoolExecutor(4) as pool:r['concurrent']=list(pool.map(worker,range(4)))
   baseline()
  else:
   if unsafe:
    try:
     with m.instrument():raise AssertionError('지원 밖 상태의 본문 실행')
    except RuntimeError as e:assert str(e)=='B03 monitoring entry observer unsupported; measurement incomplete';r['rejection']=str(e)
    assert acquired==[];baseline();r['preacquisition']=True
   else:
    with m.instrument(),c.stage('observation'):canonical.decode_c1(b'{}')
    assert c.values['observation/json/calls']==1 and c.values['observation/json/submitted_bytes']==2
    baseline();r['activation']={'calls':1,'bytes':2}
   clean();used.clear();exact()
  r.update(final_refs={},final_active=None,final_pending=c.pending,wrapper_original=canonical._parse_json is native,patch_registry_delta=len(_patch._active_patches)-len(patches),result='PASS')
 finally:clean()
 return r

if __name__=='__main__':
 if sys.argv[1:2]==['child']:print(json.dumps(child(json.loads(sys.argv[2])),ensure_ascii=False))
 else:
  configs=[{'mode':'none'}]
  for tool in range(6):
   for mode in ['allocated_active','released_active','global_released','released_inactive','allocated_inactive','reused_active','reused_inactive','active_no_callback','unrelated_local','mixed']:
    configs.append({'mode':mode,'tool':tool})
  configs.extend({'mode':'inspection','api':api} for api in ['get_events','get_local_events','namespace'])
  configs.extend([{'mode':'stress'},{'mode':'concurrent'}]);results=[]
  for config in configs:
   p=subprocess.run([sys.executable,__file__,'child',json.dumps(config)],capture_output=True,text=True)
   assert p.returncode==0,{'config':config,'stdout':p.stdout,'stderr':p.stderr}
   results.append(json.loads(p.stdout))
  (E/'monitoring-state-matrix.json').write_text(json.dumps({'python':sys.version,'cases':results,'pass':len(results),'fail':0,'skip':0,'not_reachable':[]},ensure_ascii=False,indent=2)+'\n')
  print(json.dumps({'PASS':len(results),'FAIL':0,'SKIP':0},ensure_ascii=False))

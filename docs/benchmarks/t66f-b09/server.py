"""B09 전용 실제 TLS fixture. 동결 제품/B03 모듈을 그대로 호출한다."""
from contextlib import ExitStack,closing
from datetime import date
from pathlib import Path
from threading import Condition,Thread
from unittest.mock import patch
from uuid import uuid4
import hashlib,importlib.util,json,os,resource,secrets,socket,sqlite3,subprocess,sys,time
R=Path(os.environ['B05A_TREE']); O=Path(sys.argv[2]); N=int(sys.argv[1]);assert N in (1000,5000)
sys.path[:0]=[str(R/'backend'),str(R/'scripts/benchmarks'),str(R/'docs/benchmarks/t66f-b03')]
import counters as cost
from probe import CTX,install,cache_info,calibration
install()
import uvicorn
from app import auth
from app.services.authoritative_state import BundleCredential
from isolated_sync.inputs import BoundedInputs
from isolated_sync.observation import Evaluation
from isolated_sync.retention import RetentionRepository
from isolated_sync.retention_schema import RetentionSandbox
from isolated_sync.http import create_app
from t66d2b_writers import seed
from tests.d2b_financial_reference import projections
s=importlib.util.spec_from_file_location('b05a_oracle',R/'docs/benchmarks/t66f-b02-independent/oracle.py');oracle=importlib.util.module_from_spec(s);s.loader.exec_module(oracle)
O.mkdir(parents=True,exist_ok=False);resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
def json_default(v):
 if isinstance(v,bytes):return {'hex':v.hex()}
 raise TypeError(type(v).__name__)
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=json_default)+'\n')
lock=Condition();state={'on':False,'label':'setup','issued':0,'closed':0};stack=None;cohort=[];records=[];native_auth=auth._hash_session_token

def measured_auth(token):
 with cost.authentication_hashes():return native_auth(token)
def mode(on):
 global stack
 if stack:stack.close();stack=None
 state['on']=on
 diag.clear()
 if on:
  stack=ExitStack();stack.enter_context(patch.object(auth,'_hash_session_token',measured_auth))
  for cm in (cost.instrument(),cost.instrument_connections(),cost.instrument_workers()):stack.enter_context(cm)
def settled():
 with lock:
  assert lock.wait_for(lambda:state['issued']==state['closed'],timeout=30),'collector cohort pending'
def snapshot():
 settled();agg=cost.Collector()
 for r in cohort:
  if r['counters']:
   for k,v in r['counters'].items():agg.add(k,int(v))
 return {'lookup':dict(diag),'backend_peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'measurement_complete':True,'issued':len(cohort),'closed':len(cohort),'counters':agg.snapshot() if state['on'] else None,'requests':list(cohort)}

class Wire:
 def __init__(self,app,repo):self.app=app;self.repo=repo;self.latest=None;self.trace=(O/'requests.jsonl').open('x',buffering=1)
 async def __call__(self,scope,receive,send):
  if scope['type']!='http':return await self.app(scope,receive,send)
  with lock:
   state['issued']+=1;serial=state['issued'];on=state['on'];label=state['label']
  assert serial<=30000
  c=cost.Collector();path=scope['path'];stage='transfer' if path.endswith('/objects') else 'observation';messages=[];rb=0
  async def recv():
   nonlocal rb
   m=await receive();rb+=len(m.get('body',b''));return m
  async def capture(m):messages.append(m)
  schema_profile={'timings':{},'connections':0,'opens':0,'closes':0,'actual_schema_inspections':0,'contract_compilations':0,'cache_before':cache_info()}
  schema_token=CTX.set(schema_profile)
  start=time.perf_counter_ns();cpu=time.process_time_ns();error=None
  try:
   if on:
    with c.stage(stage):await self.app(scope,recv,capture)
   else:await self.app(scope,recv,capture)
  except BaseException as e:error=type(e).__name__;raise
  finally:
   end=time.perf_counter_ns();cpu_ns=time.process_time_ns()-cpu
   schema_profile['cache_after']=cache_info();CTX.reset(schema_token)
   first=next((m for m in messages if m['type']=='http.response.start'),{});status=first.get('status');raw=b''.join(m.get('body',b'') for m in messages)
   parsed=json.loads(raw) if raw else {};manifest=None
   if path.endswith('/observations') and status in (200,201):self.latest=parsed;manifest=parsed
   def finish(done):
    row={'schema_profile':schema_profile,'serial':serial,'label':label,'on':on,'method':scope['method'],'path':path,'status':status,'start_ns':start,'end_ns':end,'wall_ns':end-start,'process_cpu_ns':cpu_ns,'request_entity_bytes':rb,'response_entity_bytes':len(raw),'chunks':len(parsed.get('chunks',[])),'canonical_transferred_bytes':sum(x['length'] for x in parsed.get('chunks',[])),'manifest':manifest,'error':error,'collector_closed':done.closed,'pending':done.pending,'completion_error':done.completion_error,'counters':done.snapshot() if on else None,'generation_metrics':dict(self.repo.metrics) if path.endswith('/observations') and status==201 else None}
    with lock:cohort.append(row);records.append(row);state['closed']+=1;self.trace.write(json.dumps(row,separators=(',',':'))+'\n');lock.notify_all()
   c.finish_when_idle(finish)
  for m in messages:await send(m)


import collections,contextvars
from isolated_sync.observation import ObservationRepository
from isolated_sync.canonical import Object
inside=contextvars.ContextVar('b05a_lookup',default=False);diag=collections.Counter()
native_lookup=ObservationRepository._lookup;native_body=Object.body;native_constructor=Object.__post_init__
def lookup(*a,**kw):
 token=inside.set(True);t=time.perf_counter_ns()
 try:return native_lookup(*a,**kw)
 finally:diag['lookup_calls']+=1;diag['lookup_ns']+=time.perf_counter_ns()-t;inside.reset(token)
def body(obj):
 if obj.kind!='hot' or not inside.get():return native_body(obj)
 t=time.perf_counter_ns()
 try:return native_body(obj)
 finally:diag['hot_body_calls']+=1;diag['hot_body_decode_ns']+=time.perf_counter_ns()-t;diag['hot_body_input_bytes']+=len(obj.raw)
def constructed(obj):
 if obj.kind=='hot' and inside.get():diag['hot_constructor_calls']+=1
 return native_constructor(obj)
ObservationRepository._lookup=lookup;Object.body=body;Object.__post_init__=constructed

def main():
 fixture_root=Path(os.environ['B05A_FIXTURE']);variant=os.environ['B05A_VARIANT'];fixture=json.loads((fixture_root/'fixture.json').read_text());selected=fixture[variant]
 token='synthetic-B05A-owned-fixed-credential'
 with RetentionSandbox() as db,patch('app.services.judgment.common._MESSAGE_RANDOM.randrange',return_value=0):
  with closing(sqlite3.connect(fixture_root/'template-combined.sqlite')) as a,closing(sqlite3.connect(db.path)) as b:a.backup(b)
  repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540))
  key=O/'synthetic-key.pem';cert=O/'synthetic-cert.pem'
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-keyout',str(key),'-out',str(cert)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1];assert port not in (18080,18081)
  d3=[]
  def metrics(v):
   d3.append(v)
   for k in ('object_reads','object_bytes_read','prefix_cache_hits','prefix_validations','path_edges','decoded_bytes','response_bytes'):
    if k in v:cost.add('existing_d3',k,v[k])
  wire=Wire(create_app(repo,metrics=metrics),repo);server=uvicorn.Server(uvicorn.Config(wire,host='127.0.0.1',port=port,ssl_keyfile=str(key),ssl_certfile=str(cert),log_level='critical',access_log=False));worker=Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);worker.start();deadline=time.monotonic()+30
  while not server.started and time.monotonic()<deadline:time.sleep(.01)
  assert server.started
  init={'origin':f'https://127.0.0.1:{port}','token':token,'fixture':{'manifest':selected['manifest'],'graph':selected['graph'],'N':N,'hot_bytes':selected['manifest']['target']['hot_ref']['bytes'],'control_bytes':selected['manifest']['target']['control_ref']['bytes'],'fixture_sha256':hashlib.sha256(oracle.encode(selected['graph']['raw_value_sha256'])).hexdigest(),'template_sha256':fixture['template_sha256']},'variant':variant}
  init['B09_probe_calibration']=calibration()
  print(json.dumps(init),flush=True)
  try:
   for line in sys.stdin:
    req=json.loads(line);cmd=req['command'];settled()
    if cmd=='mode':mode(bool(req['on']));state['label']=req['label'];cohort.clear();d3.clear();value={'ok':True}
    elif cmd=='snapshot':value={**snapshot(),'d3':list(d3)}
    elif cmd=='finish':
     with closing(sqlite3.connect(db.path)) as c:
      value={'quick_check':c.execute('PRAGMA quick_check').fetchall(),'foreign_key_check':c.execute('PRAGMA foreign_key_check').fetchall(),'observations':c.execute('SELECT status,count(*) FROM sync_observations GROUP BY status').fetchall()}
     save(O/'final-state.json',value)
    elif cmd=='exit':print('{"ok":true}',flush=True);break
    else:raise ValueError(cmd)
    print(json.dumps(value),flush=True)
  finally:
   settled();mode(False);server.should_exit=True;worker.join(timeout=20);assert not worker.is_alive();wire.trace.close()
   with closing(sqlite3.connect(db.path)) as a,closing(sqlite3.connect(O/'backend-final.sqlite')) as b:a.backup(b);assert b.execute('PRAGMA quick_check').fetchone()[0]=='ok'
   key.unlink()
if __name__=='__main__':main()

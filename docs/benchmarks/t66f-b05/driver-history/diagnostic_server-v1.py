"""B05 전용 실제 TLS fixture. 동결 제품/B03 모듈을 그대로 호출한다."""
from contextlib import ExitStack,closing
from datetime import date
from pathlib import Path
from threading import Condition,Thread
from unittest.mock import patch
from uuid import uuid4
import hashlib,importlib.util,json,os,resource,secrets,socket,sqlite3,subprocess,sys,time,contextvars,collections
from uuid import UUID
R=Path(os.environ['B05_TREE']); O=Path(sys.argv[2]); N=int(sys.argv[1]);assert N == 1000
sys.path[:0]=[str(R/'backend'),str(R/'scripts/benchmarks'),str(R/'docs/benchmarks/t66f-b03')]
import counters as cost
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
s=importlib.util.spec_from_file_location('b05_oracle',R/'docs/benchmarks/t66f-b02-independent/oracle.py');oracle=importlib.util.module_from_spec(s);s.loader.exec_module(oracle)
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
 return {'lookup_diagnostic':dict(diag),'measurement_complete':True,'issued':len(cohort),'closed':len(cohort),'counters':agg.snapshot() if state['on'] else None,'requests':list(cohort)}

class Wire:
 def __init__(self,app):self.app=app;self.latest=None;self.trace=(O/'requests.jsonl').open('x',buffering=1)
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
  start=time.perf_counter_ns();cpu=time.process_time_ns();error=None
  try:
   if on:
    with c.stage(stage):await self.app(scope,recv,capture)
   else:await self.app(scope,recv,capture)
  except BaseException as e:error=type(e).__name__;raise
  finally:
   end=time.perf_counter_ns();cpu_ns=time.process_time_ns()-cpu
   first=next((m for m in messages if m['type']=='http.response.start'),{});status=first.get('status');raw=b''.join(m.get('body',b'') for m in messages)
   parsed=json.loads(raw) if raw else {};manifest=None
   if path.endswith('/observations') and status in (200,201):self.latest=parsed;manifest=parsed
   def finish(done):
    row={'serial':serial,'label':label,'on':on,'method':scope['method'],'path':path,'status':status,'start_ns':start,'end_ns':end,'wall_ns':end-start,'process_cpu_ns':cpu_ns,'request_entity_bytes':rb,'response_entity_bytes':len(raw),'chunks':len(parsed.get('chunks',[])),'canonical_transferred_bytes':sum(x['length'] for x in parsed.get('chunks',[])),'manifest':manifest,'error':error,'collector_closed':done.closed,'pending':done.pending,'completion_error':done.completion_error,'counters':done.snapshot() if on else None}
    with lock:cohort.append(row);records.append(row);state['closed']+=1;self.trace.write(json.dumps(row,separators=(',',':'))+'\n');lock.notify_all()
   c.finish_when_idle(finish)
  for m in messages:await send(m)

# 모든 조건에 동일한 경량 timer/count; 큰 객체별 로그를 남기지 않는다.
from isolated_sync.observation import ObservationRepository
from isolated_sync.canonical import Object
from isolated_sync import canonical
diag=collections.Counter();tag=contextvars.ContextVar('b05_diag',default=None)
_native_lookup=ObservationRepository._lookup;_native_decode=canonical.decode_c1

def object_phase(fn,phase):
 def wrapped(obj,*a,**kw):
  token=tag.set((obj.kind,phase))
  try:return fn(obj,*a,**kw)
  finally:tag.reset(token)
 return wrapped
Object.__post_init__=object_phase(Object.__post_init__,'constructor')
Object.body=object_phase(Object.body,'body')
def decoded(raw):
 category=tag.get()
 if category is None:return _native_decode(raw)
 key='/'.join(category);t=time.perf_counter_ns()
 try:return _native_decode(raw)
 finally:
  diag[key+'/calls']+=1;diag[key+'/bytes']+=len(raw);diag[key+'/decode_ns']+=time.perf_counter_ns()-t
canonical.decode_c1=decoded

def looked(*a,**kw):
 t=time.perf_counter_ns()
 try:return _native_lookup(*a,**kw)
 finally:diag['lookup/calls']+=1;diag['lookup/elapsed_ns']+=time.perf_counter_ns()-t
ObservationRepository._lookup=looked

def main():
 token='synthetic-B05-only-fixed-credential';credential=BundleCredential(native_auth(token),1)
 with RetentionSandbox() as db,patch('app.services.judgment.common._MESSAGE_RANDOM.randrange',return_value=0),patch('isolated_sync.finalization.uuid4',side_effect=[UUID(int=i,version=4) for i in range(1,65)]):
  with db.connect() as conn:
   seed(conn,N);conn.execute("INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order,is_primary_income) VALUES (101,'2026-10-05','fixed-width-cash',-50,2,0)")
   conn.execute("INSERT INTO users(id,username,password_hash) VALUES (1,'b05-synthetic','unused')")
   conn.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",(credential.token_hash,))
   from tests.test_isolated_sync_capture import freeze_timestamps
   freeze_timestamps(conn)
  db.install();mode(True);c=cost.Collector();t=time.perf_counter_ns();cpu=time.process_time_ns()
  with c.stage('generation'):db.bootstrap()
  c.finish_when_idle(lambda _:None);assert c.closed and not c.pending
  save(O/'bootstrap.json',{'on':True,'wall_ns':time.perf_counter_ns()-t,'process_cpu_ns':time.process_time_ns()-cpu,'counters':c.snapshot(),'closed':c.closed,'pending':c.pending});mode(False)
  repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540));initial=repo.create(credential,request_id=str(uuid4()),guard=lambda:credential)
  with closing(sqlite3.connect(db.path)) as conn:hashes,graph=oracle.walk(conn,initial['target'])
  assert graph['raw_rows']['ledger_entries']==N and sum(graph['raw_rows'].values())==N+35
  repo.release(initial['observation_id'],credential,guard=lambda:credential)
  fixture={'n':N,'manifest':initial,'graph':graph,'fixture_sha256':hashlib.sha256(oracle.encode(graph['raw_value_sha256'])).hexdigest(),'hot_bytes':initial['target']['hot_ref']['bytes'],'control_bytes':initial['target']['control_ref']['bytes'],'db_path':str(db.path)}
  save(O/'fixture.json',fixture)
  key=O/'synthetic-key.pem';cert=O/'synthetic-cert.pem'
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-keyout',str(key),'-out',str(cert)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1];assert port not in (18080,18081)
  d3=[]
  def metrics(v):
   d3.append(v)
   for k in ('object_reads','object_bytes_read','prefix_cache_hits','prefix_validations','path_edges','decoded_bytes','response_bytes'):
    if k in v:cost.add('existing_d3',k,v[k])
  wire=Wire(create_app(repo,metrics=metrics));server=uvicorn.Server(uvicorn.Config(wire,host='127.0.0.1',port=port,ssl_keyfile=str(key),ssl_certfile=str(cert),log_level='critical',access_log=False));worker=Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);worker.start();deadline=time.monotonic()+30
  while not server.started and time.monotonic()<deadline:time.sleep(.01)
  assert server.started
  print(json.dumps({'origin':f'https://127.0.0.1:{port}','token':token,'fixture':fixture}),flush=True)
  try:
   for line in sys.stdin:
    req=json.loads(line);cmd=req['command'];settled()
    if cmd=='mode':
     mode(bool(req['on']));state['label']=req['label'];cohort.clear();d3.clear();value={'ok':True,'on':state['on']}
    elif cmd=='snapshot':value={**snapshot(),'d3':list(d3)}
    elif cmd=='mutate':
     mode(True);c=cost.Collector();t=time.perf_counter_ns();cpu=time.process_time_ns();table='ledger_entries' if req['kind']=='card' else 'cash_flows';keyid=1002 if req['kind']=='card' else 101
     with c.stage('generation'):
      with db.connect() as conn:
       conn.begin_capture();w=BoundedInputs(conn);w.execute(f'UPDATE {table} SET amount_value=? WHERE id=?',(req['amount'],keyid));projections(w);conn.finalize();conn.commit()
     elapsed=time.perf_counter_ns()-t;used=time.process_time_ns()-cpu;c.finish_when_idle(lambda _:None);assert c.closed and not c.pending;mode(False)
     prepared=repo.create(credential,request_id=str(uuid4()),guard=lambda:credential)
     with closing(sqlite3.connect(db.path)) as conn:
      next_hashes,g=oracle.walk(conn,prepared['target']);new=next_hashes-hashes
      nb=sum(conn.execute('SELECT length(body) FROM sync_objects WHERE hash=?',(h,)).fetchone()[0] for h in new)
     repo.release(prepared['observation_id'],credential,guard=lambda:credential);hashes=next_hashes
     value={'kind':req['kind'],'amount':req['amount'],'target':prepared['target'],'graph':g,'new_immutable_objects':len(new),'new_immutable_bytes':nb,'generation':{'on':True,'wall_ns':elapsed,'process_cpu_ns':used,'counters':c.snapshot(),'closed':c.closed,'pending':c.pending}}
     save(O/f"{req['label']}-mutation.json",value)
    elif cmd=='finish':
     mode(False)
     with closing(sqlite3.connect(db.path)) as conn:
      value={'quick_check':conn.execute('PRAGMA quick_check').fetchall(),'foreign_key_check':conn.execute('PRAGMA foreign_key_check').fetchall(),'observations':conn.execute('SELECT status,count(*) FROM sync_observations GROUP BY status').fetchall(),'current':dict(conn.execute('SELECT * FROM sync_current').description and zip([v[0] for v in conn.execute('SELECT * FROM sync_current').description],conn.execute('SELECT * FROM sync_current').fetchone()))}
      dst=sqlite3.connect(O/'backend-final.sqlite');conn.backup(dst);dst.close()
     value['backup']='backend-final.sqlite';save(O/'final-state.json',value)
    elif cmd=='exit':print('{"ok":true}',flush=True);break
    else:raise ValueError(cmd)
    print(json.dumps(value,default=json_default),flush=True)
  finally:
   with closing(sqlite3.connect(db.path)) as source,closing(sqlite3.connect(O/'backend-terminal.sqlite')) as destination:source.backup(destination)
   settled();mode(False);server.should_exit=True;worker.join(timeout=20);assert not worker.is_alive();wire.trace.close();key.unlink()
if __name__=='__main__':main()

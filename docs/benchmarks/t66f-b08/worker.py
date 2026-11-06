"""원 source 또는 B08 source를 별도 process에서 실행하는 B08 전용 도구."""
import sys,os,pathlib,json,sqlite3,hashlib,contextlib,time,threading,base64,gzip,resource
from datetime import date,datetime,timezone
from uuid import uuid4
from unittest.mock import patch
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b08';W=pathlib.Path('/tmp/money-note-t66f-b08-20261026');MODE=sys.argv[1];V=sys.argv[2];T=W/('baseline' if V=='A' else 'candidate')
sys.path[:0]=[str(T/'backend'),str(T/'docs/benchmarks/t66f-b03')]
import counters as cost
from probe import CTX,install,cache_info,calibration
from starlette.testclient import TestClient
from isolated_sync.observation import Evaluation,engine_artifact
from isolated_sync.retention_schema import RetentionSandbox
from isolated_sync.retention import RetentionRepository
from isolated_sync.http import create_app
from app import auth
from app.services.authoritative_state import BundleCredential
from tests.test_isolated_sync_transfer import graph
from app import db_migrations as mig
resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
TOKEN='synthetic-B05A-owned-fixed-credential';SOURCEFIX=json.loads((R/'docs/benchmarks/t66f-b05a/fixture-n1000.json').read_text());ENGINE=hashlib.sha256(engine_artifact()).hexdigest();START=time.monotonic()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def reply(d):print(json.dumps(d,separators=(',',':')),flush=True)
def backup(a,path):
 assert not path.exists()
 with contextlib.closing(sqlite3.connect(a))as x,contextlib.closing(sqlite3.connect(path))as y:x.backup(y)
def rows_digest(c):
 out={}
 for table in SOURCEFIX['A']['graph']['raw_rows']:
  rs=[list(r)for r in c.execute('SELECT * FROM '+table)];out[table]=hashlib.sha256(json.dumps(sorted(rs,key=repr),ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
 return out

def prepare():
 assert V=='B'
 with RetentionSandbox()as db,patch('app.services.judgment.common._MESSAGE_RANDOM.randrange',return_value=0):
  with contextlib.closing(sqlite3.connect(W/'template-n1000.sqlite'))as a,contextlib.closing(sqlite3.connect(db.path))as b:a.backup(b)
  fixed=datetime.fromisoformat(SOURCEFIX['control_exported_at'].replace('Z','+00:00'));repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540),clock=lambda:fixed);cred=BundleCredential(auth._hash_session_token(TOKEN),1)
  with contextlib.closing(sqlite3.connect(db.path))as c:before=rows_digest(c)
  # 두 repository 작업도 보수적으로 총32 operation 예산과 watchdog에 포함한다.
  journal=(E/'preparation-attempts.jsonl').open('x',buffering=1)
  journal.write(json.dumps({'operation':1,'method':'repository.create','variant':V})+'\n');t=time.perf_counter_ns();m=repo.create(cred,request_id=str(uuid4()),guard=lambda:cred);create_ns=time.perf_counter_ns()-t
  journal.write(json.dumps({'operation':2,'method':'repository.release','variant':V})+'\n');t=time.perf_counter_ns();repo.release(m['observation_id'],cred,guard=lambda:cred);release_ns=time.perf_counter_ns()-t;journal.close()
  with contextlib.closing(sqlite3.connect(db.path))as c:
   after=rows_digest(c);assert before==after
   a=SOURCEFIX['A']['manifest']['target'];b=m['target'];assert all(a[k]==b[k]for k in ['ns','principal_id','versions','revision','raw_ref','index_ref','control_ref']);assert a['hot_ref']['bytes']==b['hot_ref']['bytes']
   ah=json.loads(c.execute('SELECT body FROM sync_objects WHERE hash=?',(a['hot_ref']['hash'],)).fetchone()[0]);bh=json.loads(c.execute('SELECT body FROM sync_objects WHERE hash=?',(b['hot_ref']['hash'],)).fetchone()[0]);assert ah['state']==bh['state']
  gg=graph(db,m);assert len(gg)==4132 and sum(len(v[2])for v in gg.values())==2749721
  backup(db.path,W/'prepared-common.sqlite');sha=hashlib.sha256((W/'prepared-common.sqlite').read_bytes()).hexdigest()
  d={'N':1000,'preserved_template_sha256':SOURCEFIX['template_sha256'],'prepared_common_sha256':sha,'derived_only_engine_views':True,'preserved_financial_rows':before,'A':{'manifest':SOURCEFIX['A']['manifest']},'B':{'manifest':m},'canonical_financial_state_identical':True,'target_differences':['context.financial_engine','hot_ref.hash','sync_root'],'preparatory_repository_operations':2,'preparation_B03':'OFF; not a paired performance sample','create_ns':create_ns,'release_ns':release_ns,'control_time_fixed_only_during_preparation':SOURCEFIX['control_exported_at']}
  save(E/'prepared-fixture.json',d);reply({'ready':True,'prepared_sha':sha,'repository_operations':2})

class Wire:
 def __init__(self,app):self.app=app
 async def __call__(self,scope,receive,send):
  if scope['type']!='http':return await self.app(scope,receive,send)
  assert len(records)<15
  row={'variant':V,'ordinal':len(records),'engine':ENGINE,'fixture_sha':prepared['prepared_common_sha256'],**config,'timings':{},'connections':0,'opens':0,'closes':0,'actual_schema_inspections':0,'start_utc':datetime.now(timezone.utc).isoformat(),'cache_before':cache_info(),'error':None};records.append(row);done=threading.Event();collector=cost.Collector();messages=[];token=CTX.set(row);t=time.perf_counter_ns();cpu=time.process_time_ns()
  async def capture(m):messages.append(m)
  try:
   with collector.stage('transfer' if scope['path'].endswith('/objects')else'observation'):await self.app(scope,receive,capture)
  except BaseException as ex:row['error']=type(ex).__name__;raise
  finally:
   row.update(handler_ns=time.perf_counter_ns()-t,handler_cpu_ns=time.process_time_ns()-cpu,cache_after=cache_info());CTX.reset(token)
   row['status']=next((v['status']for v in messages if v['type']=='http.response.start'),None);raw=b''.join(v.get('body',b'')for v in messages);row['response_bytes']=len(raw)
   def close(c):
    row.update(collector_closed=c.closed,pending=c.pending,completion_error=c.completion_error,counters=c.snapshot());tape.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n');done.set()
   collector.finish_when_idle(close)
  events.append(done)
  for v in messages:await send(v)

records=[];events=[];config={};prepared=None;tape=None

def serve():
 global prepared,tape
 install();prepared=json.loads((E/'prepared-fixture.json').read_text());tape=(E/f'packets-{V}.jsonl').open('x',buffering=1)
 with RetentionSandbox()as db,patch('app.services.judgment.common._MESSAGE_RANDOM.randrange',return_value=0):
  with contextlib.closing(sqlite3.connect(W/'prepared-common.sqlite'))as a,contextlib.closing(sqlite3.connect(db.path))as b:a.backup(b)
  selected=prepared[V]['manifest'];g=graph(db,selected);values=list(g.values());roots=[g[selected['target'][role+'_ref']['hash']]for role in ['hot','control','raw','index']];leaf=max((v for v in values if v[3]['kind']=='snapshot-leaf'),key=lambda v:len(v[2]));bundles=[[v]for v in roots]+[[leaf],[v for v in values if v[3]['kind']=='index-leaf'][:64],[v for v in values if v[3]['kind']=='index-node'][:64]]
  repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540));d3=[]
  def metrics(v):
   d3.append(v)
   for k in ['object_reads','object_bytes_read','prefix_cache_hits','prefix_validations','path_edges','decoded_bytes','response_bytes']:
    if k in v:cost.add('existing_d3',k,v[k])
  native_auth=auth._hash_session_token
  def auth_hash(v):
   with cost.authentication_hashes():return native_auth(v)
  with contextlib.ExitStack()as st:
   st.enter_context(patch.object(auth,'_hash_session_token',auth_hash))
   for cm in [cost.instrument(),cost.instrument_connections(),cost.instrument_workers()]:st.enter_context(cm)
   app=create_app(repo,metrics=metrics)
   with TestClient(Wire(app),base_url='https://b08.invalid')as client:
    reply({'ready':True,'variant':V,'engine':ENGINE,'cache_start':cache_info()});manifest=None
    for line in sys.stdin:
     cmd=json.loads(line)
     if cmd['op']=='finish':break
     assert time.monotonic()-START<110 and len(records)<15
     config.clear();config.update(global_sequence=cmd['global_sequence'],request_type=cmd['op'],slot=cmd.get('slot'),block=cmd.get('block'))
     headers={'Authorization':'Bearer '+TOKEN}
     if cmd['op']=='manifest':
      response=client.post('/api/sync/v1/observations',json=dict(protocol=1,request_id=str(uuid4()),base=None,inline_bytes=0),headers=headers);assert response.status_code==201,response.text;manifest=response.json();assert manifest['target']==selected['target']
     elif cmd['op']=='objects':
      batch=bundles[cmd['slot']];body=dict(protocol=1,request_id=str(uuid4()),items=[dict(path=v[1],offset='0',length=len(v[2]))for v in batch]);response=client.post('/api/sync/v1/observations/'+manifest['observation_id']+'/objects',json=body,headers=headers);assert response.status_code==200,response.text
      for part,v in zip(response.json()['chunks'],batch,strict=True):assert part['ref']==v[0] and part['offset']=='0' and part['length']==len(v[2]) and base64.b64decode(part['data_base64'],validate=True)==v[2]
     else:
      assert cmd['op']=='release';response=client.delete('/api/sync/v1/observations/'+manifest['observation_id'],headers=headers);assert response.status_code==204,response.text
     assert events[-1].wait(3);r=records[-1];assert r['collector_closed']and r['pending']==0 and r['completion_error']is None and r['error']is None
     reply({'complete':True,'variant':V,'global_sequence':cmd['global_sequence'],'handler_ns':r['handler_ns']})
   cc=cost.Collector()
   with cc.stage('calibration'):cal=calibration()
   cc.close();assert cc.closed and cc.pending==0
  with contextlib.closing(sqlite3.connect(db.path))as c:
   assert rows_digest(c)==prepared['preserved_financial_rows']
   assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok'and not c.execute('PRAGMA foreign_key_check').fetchall()
  backup(db.path,W/f'after-{V}.sqlite')
  save(E/f'worker-{V}.json',{'variant':V,'engine':ENGINE,'requests':len(records),'d3':d3,'cache_end':cache_info(),'calibration':cal,'target':manifest['target'],'financial_rows_preserved':True,'B03_mode':'ON all actual D3 requests','fixture_sha':prepared['prepared_common_sha256']})
 tape.close();reply({'finished':True,'variant':V})
if __name__=='__main__':
 if MODE=='prepare':prepare()
 else:serve()

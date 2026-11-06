"""원 B03 N1k 실제 ASGI D3 handler, 총30요청. 외부 watchdog 아래 한 번만 실행."""
import os,sys,pathlib,time,json,hashlib,sqlite3,base64,gzip,threading,contextlib,resource,platform
from datetime import date,datetime,timezone
from uuid import uuid4
from unittest.mock import patch
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b07';W=pathlib.Path('/tmp/money-note-t66f-b07-20261026');T=W/'baseline';START=time.monotonic()
sys.path[:0]=[str(T/'backend'),str(T/'docs/benchmarks/t66f-b03')]
import counters as cost
from probe import CTX,install,restore,ORIGINALS
from starlette.testclient import TestClient
from app import auth,db_migrations
from isolated_sync import retention_schema as rs,capture as cap
from isolated_sync.retention import RetentionRepository
from isolated_sync.observation import Evaluation,engine_artifact
from isolated_sync.http import create_app
from tests.test_isolated_sync_transfer import graph

resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
fixture=json.loads((R/'docs/benchmarks/t66f-b05a/fixture-n1000.json').read_text());pre=json.loads((E/'preflight.json').read_text())
assert hashlib.sha256(engine_artifact()).hexdigest()==pre['engine_sha'] and sys.version.startswith('3.12.3') and sqlite3.sqlite_version=='3.45.1'
assert sys.getprofile() is None and sys.gettrace() is None
rawfile=(E/'packets.jsonl').open('x',buffering=1);requestsfile=(E/'requests.jsonl').open('x',buffering=1)
rows=[];config={};d3=[];first_request=True

def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def utc():return datetime.now(timezone.utc).isoformat()

class Wire:
 def __init__(self,app):self.app=app
 async def __call__(self,scope,receive,send):
  global first_request
  if scope['type']!='http':return await self.app(scope,receive,send)
  assert len(rows)<30 and time.monotonic()-START<110
  row={'sequence':len(rows)+1,**config,'start_utc':utc(),'method':scope['method'],'path':scope['path'],'source_payload':pre['payload_sha256'],'engine_sha':pre['engine_sha'],'fixture_sha':pre['fixture']['template_sha256'],'metrics':{},'connect_calls':0,'open_calls':0,'close_calls':0,'fresh_open_intervals':0,'connect_intervals':[],'process_first_request':first_request,'error':None,'sql_timing_scope':'RetentionConnection.execute only; excludes cursor fetch and in-memory SQL; includes inner B03 SQL calls'}
  first_request=False;rows.append(row);c=cost.Collector();messages=[];event=threading.Event();token=CTX.set(row)
  # dispatch를 시작하기 전에 영구 journal에 attempt를 기록한다.
  requestsfile.write(json.dumps({'sequence':row['sequence'],'probe':row['probe'],'request_type':row['request_type'],'start_utc':row['start_utc']})+'\n')
  start=time.perf_counter_ns();cpu=time.process_time_ns()
  async def capture(m):messages.append(m)
  try:
   with c.stage('transfer' if scope['path'].endswith('/objects') else 'observation'):
    await self.app(scope,receive,capture)
  except BaseException as e:row['error']=type(e).__name__;raise
  finally:
   row.update(handler_ns=time.perf_counter_ns()-start,handler_process_cpu_ns=time.process_time_ns()-cpu,end_utc=utc())
   CTX.reset(token);row['response_status']=next((m.get('status') for m in messages if m['type']=='http.response.start'),None)
   body=b''.join(m.get('body',b'') for m in messages)
   row['response_sha256']=hashlib.sha256(body).hexdigest();row['response_bytes']=len(body)
   def done(collector):
    row.update(collector_closed=collector.closed,pending=collector.pending,completion_error=collector.completion_error,counters=collector.snapshot())
    rawfile.write(json.dumps({k:v for k,v in row.items() if not k.startswith('_')},ensure_ascii=False,separators=(',',':'))+'\n');event.set()
   c.finish_when_idle(done);row['_event']=event
  for m in messages:await send(m)

def packet(client,method,path,body,*,probe,label,block=None,slot=None):
 assert time.monotonic()-START<110 and len(rows)<30
 config.clear();config.update(probe=probe,request_type=label,block=block,slot=slot,B03_instrumentation='ON',connection_state='fresh per source call; process/OS caches warm after setup')
 kwargs={'headers':{'Authorization':'Bearer synthetic-B05A-owned-fixed-credential'}}
 if body is not None:kwargs['json']=body
 response=client.request(method,path,**kwargs);row=rows[-1];assert row['_event'].wait(3),'collector pending';del row['_event']
 assert row['collector_closed'] and row['pending']==0 and row['completion_error'] is None and row['error'] is None
 assert response.status_code in (200,201,204),(response.status_code,response.text[:300])
 return response

def main():
 install()
 with rs.RetentionSandbox() as db,patch('app.services.judgment.common._MESSAGE_RANDOM.randrange',return_value=0):
  with contextlib.closing(sqlite3.connect(W/'template-n1000.sqlite')) as a,contextlib.closing(sqlite3.connect(db.path)) as b:a.backup(b)
  # 보존 source graph로부터 독립 hash 확인된 경로를 만든다. HTTP 취득이 아니다.
  g=graph(db,fixture['A']['manifest']);assert len(g)==4132 and sum(len(v[2]) for v in g.values())==2749721
  items=list(g.values());roots=[g[fixture['A']['manifest']['target'][role+'_ref']['hash']] for role in ['hot','control','raw','index']]
  rawleaf=max((v for v in items if v[3]['kind']=='snapshot-leaf'),key=lambda v:len(v[2]))
  leaves=[v for v in items if v[3]['kind']=='index-leaf'][:64];nodes=[v for v in items if v[3]['kind']=='index-node'][:64]
  bundles=[[v] for v in roots]+[[rawleaf],leaves,nodes];assert len(bundles)==7
  plan=[{'slot':i,'items':[{'path':v[1],'offset':'0','length':len(v[2]),'ref':v[0],'kind':v[3]['kind'],'sha256':hashlib.sha256(v[2]).hexdigest()} for v in vs]} for i,vs in enumerate(bundles)]
  write(E/'packet-plan.json',{'N':1000,'bundles':plan,'blocks':['control1','probe1','probe2','control2'],'initial_manifest':1,'object_packets':28,'release':1,'total_planned':30,'not_full_cold':True})
  repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540))
  def metrics(v):
   d3.append(v)
   for k in ['object_reads','object_bytes_read','prefix_cache_hits','prefix_validations','path_edges','decoded_bytes','response_bytes']:
    if k in v:cost.add('existing_d3',k,v[k])
  native_auth=auth._hash_session_token
  def auth_hash(v):
   with cost.authentication_hashes():return native_auth(v)
  lifecycle={}
  with contextlib.ExitStack() as stack:
   stack.enter_context(patch.object(auth,'_hash_session_token',auth_hash))
   for cm in [cost.instrument(),cost.instrument_connections(),cost.instrument_workers()]:stack.enter_context(cm)
   app=create_app(repo,metrics=metrics)
   with TestClient(Wire(app),base_url='https://b07.invalid') as client:
    request=dict(protocol=1,request_id=str(uuid4()),base=None,inline_bytes=0)
    m=packet(client,'POST','/api/sync/v1/observations',request,probe=True,label='manifest').json()
    assert m['target']==fixture['A']['manifest']['target'] and m['status']=='available'
    lifecycle={'observation_id':m['observation_id'],'validated_at':m['validated_at'],'expires_at':m['expires_at'],'target':m['target']}
    for block,probe in [('control1',False),('probe1',True),('probe2',True),('control2',False)]:
     for slot,batch in enumerate(bundles):
      body=dict(protocol=1,request_id=str(uuid4()),items=[dict(path=v[1],offset='0',length=len(v[2])) for v in batch])
      reply=packet(client,'POST',f"/api/sync/v1/observations/{m['observation_id']}/objects",body,probe=probe,label='objects',block=block,slot=slot).json()
      assert reply['observation_id']==m['observation_id'] and reply['request_id']==body['request_id']
      for part,v in zip(reply['chunks'],batch,strict=True):
       decoded=base64.b64decode(part['data_base64'],validate=True);assert part['ref']==v[0] and decoded==v[2] and part['offset']=='0' and part['length']==len(v[2])
    packet(client,'DELETE',f"/api/sync/v1/observations/{m['observation_id']}",None,probe=True,label='release')
  # 실제 요청이 모두 끝난 뒤 일관 backup과 원 source/DB 불변성을 보존한다.
  end=time.monotonic();lifecycle.update(requests=len(rows),execution_inside_child_s=end-START,d3=d3)
  with contextlib.closing(sqlite3.connect(db.path)) as c,contextlib.closing(sqlite3.connect(W/'backend-after.sqlite')) as b:
   assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
   lifecycle['after_observations']=[list(v) for v in c.execute('SELECT id,status FROM sync_observations')]
   gg=graph(db,fixture['A']['manifest']);assert set(gg)==set(g) and all(gg[k][2]==g[k][2] for k in g)
   c.backup(b)
  lifecycle.update(status='COMPLETED',fixture_graph_unchanged=True,collector_closed=all(v['collector_closed'] for v in rows),runtime={'python':sys.version,'sqlite':sqlite3.sqlite_version,'platform':platform.platform()},caches={'retention_metadata':next(fn for obj,name,fn in ORIGINALS if obj is rs and name=='metadata_contract').cache_info()._asdict(),'capture_schema':'original lru_cache preserved; not cleared'},benchmark_clock_scope='child startup/import/setup through all requests; outer elapsed separately recorded')
  write(E/'execution.json',lifecycle)
 restore();rawfile.close();requestsfile.close()
 print(json.dumps({'status':'COMPLETED','packets':len(rows),'child_s':time.monotonic()-START}),flush=True)
if __name__=='__main__':main()

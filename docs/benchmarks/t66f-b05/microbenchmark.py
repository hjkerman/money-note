"""동일 current 계약/DB에서 원 함수와 후보 함수의 ON/OFF 교차 진단. 전체 source A/B cold가 아니다."""
import collections,gc,hashlib,importlib.util,json,os,pathlib,statistics,sys,time,tracemalloc
from datetime import date
from unittest.mock import patch
from uuid import uuid4
R=pathlib.Path(os.environ['B05_TREE']);E=pathlib.Path(os.environ['B05_EVIDENCE']);assert not (E/'microbenchmark.json').exists()
sys.path[:0]=[str(R/'backend'),str(R/'scripts/benchmarks'),str(R/'docs/benchmarks/t66f-b03')]
import counters as cost
from app.services.authoritative_state import BundleCredential
from isolated_sync import observation
from isolated_sync.observation import Evaluation,ObservationRepository
from isolated_sync.retention import RetentionRepository
from isolated_sync.retention_schema import RetentionSandbox
from t66d2b_writers import seed
ns={};exec(compile((E/'lookup_before.py').read_text(),str(E/'lookup_before.py'),'exec'),observation.__dict__,ns)
fns={'A':ns['_lookup'],'B':ObservationRepository._lookup}
rows=[];memory=[]
with RetentionSandbox() as db,patch('app.services.judgment.common._MESSAGE_RANDOM.randrange',return_value=0):
 with db.connect() as c:
  seed(c,1000);c.execute("INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order,is_primary_income) VALUES (101,'2026-10-05','fixed-width-cash',-50,2,0)")
  c.execute("INSERT INTO users(id,username,password_hash) VALUES (1,'b05-synthetic','unused')");cred=BundleCredential(hashlib.sha256(b'b05-micro').hexdigest(),1)
  c.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",(cred.token_hash,))
 db.install();db.bootstrap();repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540));manifest=repo.create(cred,request_id=str(uuid4()),guard=lambda:cred)
 for variant in ['A','B']:
  with patch.object(ObservationRepository,'_lookup',fns[variant]):
   for _ in range(2):assert repo.lookup(manifest['observation_id'],cred,guard=lambda:cred)==manifest
 order=[('A',False),('B',False),('B',True),('A',True),('A',True),('B',True),('B',False),('A',False)]
 for ordinal,(variant,on) in enumerate(order):
  inner=[];public=[];collector=cost.Collector();fn=fns[variant]
  def timed(*args,**kwargs):
   t=time.perf_counter_ns()
   try:return fn(*args,**kwargs)
   finally:inner.append(time.perf_counter_ns()-t)
  from contextlib import ExitStack
  with ExitStack() as stack:
   stack.enter_context(patch.object(ObservationRepository,'_lookup',timed))
   if on:
    for cm in [cost.instrument(),cost.instrument_connections(),collector.stage('transfer')]:stack.enter_context(cm)
   start=time.time()
   for _ in range(10):
    t=time.perf_counter_ns();assert repo.lookup(manifest['observation_id'],cred,guard=lambda:cred)==manifest;public.append(time.perf_counter_ns()-t)
  collector.close();assert collector.closed
  rows.append({'ordinal':ordinal,'variant':variant,'on':on,'start_unix':start,'end_unix':time.time(),'status':'COMPLETED','calls':10,'lookup_ns':inner,'public_ns':public,'lookup_median_ns':statistics.median(inner),'public_median_ns':statistics.median(public),'counters':collector.snapshot() if on else None,'collector_closed':collector.closed})
 for variant in ['A','B']:
  gc.collect();tracemalloc.start()
  with patch.object(ObservationRepository,'_lookup',fns[variant]):
   assert repo.lookup(manifest['observation_id'],cred,guard=lambda:cred)==manifest
  current,peak=tracemalloc.get_traced_memory();tracemalloc.stop();memory.append({'variant':variant,'tracemalloc_current':current,'tracemalloc_peak':peak,'timing_used':False})
 repo.release(manifest['observation_id'],cred,guard=lambda:cred)
summary=[]
for on in [False,True]:
 a=[v for x in rows if x['variant']=='A' and x['on']==on for v in x['lookup_ns']];b=[v for x in rows if x['variant']=='B' and x['on']==on for v in x['lookup_ns']]
 summary.append({'on':on,'A_lookup_median_ns':statistics.median(a),'B_lookup_median_ns':statistics.median(b),'B_over_A':statistics.median(b)/statistics.median(a),'A_range_ns':[min(a),max(a)],'B_range_ns':[min(b),max(b)],'samples_per_variant':len(a)})
(E/'microbenchmark.json').write_text(json.dumps({'role':'DIAGNOSTIC_ONLY; 동일 current 엔진을 쓰는 알고리즘 격리; 실제 client cold 아님','N':1000,'hot_bytes':manifest['target']['hot_ref']['bytes'],'context':manifest['target']['context'],'fixture_target':manifest['target'],'fixture_digest':hashlib.sha256(json.dumps(manifest['target'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'rows':rows,'summary':summary,'memory':memory,'limitations':['동일 DB/OS warm cache','2개 순서 블록/조건; 독립 시행 20개로 해석하지 않음','한 호스트/CPython 3.12.3','tracemalloc 별도 실행; Android 메모리 아님']},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'summary':summary,'memory':memory}))

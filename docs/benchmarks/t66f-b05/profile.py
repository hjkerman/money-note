"""작은 실제 _lookup의 native decode 횟수·시간을 진단한다. 객체별 로그 없음."""
import collections,contextvars,hashlib,json,os,pathlib,statistics,sys,time
from contextlib import ExitStack
from datetime import date
from unittest.mock import patch
from uuid import uuid4
R=pathlib.Path(sys.argv[1]);OUT=pathlib.Path(sys.argv[2]);assert not OUT.exists()
sys.path[:0]=[str(R/'backend'),str(R/'scripts/benchmarks')]
from isolated_sync.retention_schema import RetentionSandbox
from isolated_sync.retention import RetentionRepository
from isolated_sync.observation import Evaluation,ObservationRepository
from isolated_sync.canonical import Object
from isolated_sync import canonical
from app.services.authoritative_state import BundleCredential
from t66d2b_writers import seed
origin=(Object.body,Object.__post_init__,canonical.decode_c1,ObservationRepository._lookup)
ctx=contextvars.ContextVar('b05_object',default=None);count=collections.Counter();lookup=[];decode_ns=collections.Counter();sizes=collections.Counter()
def tagged(fn,phase):
 def wrapped(self,*args,**kw):
  token=ctx.set((self.kind,phase,self.hash if phase=='body' else 'constructing'))
  try:return fn(self,*args,**kw)
  finally:ctx.reset(token)
 return wrapped

def decoded(raw):
 c=ctx.get();key='/'.join(c[:2]) if c else 'other';count[key]+=1;sizes[(key,len(raw))]+=1;t=time.perf_counter_ns()
 try:return origin[2](raw)
 finally:decode_ns[key]+=time.perf_counter_ns()-t

def looked(self,*args,**kw):
 t=time.perf_counter_ns()
 try:return origin[3](self,*args,**kw)
 finally:lookup.append(time.perf_counter_ns()-t)

with RetentionSandbox() as db,patch('app.services.judgment.common._MESSAGE_RANDOM.randrange',return_value=0):
 with db.connect() as c:
  seed(c,1000);c.execute("INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order,is_primary_income) VALUES (101,'2026-10-05','fixed-width-cash',-50,2,0)")
  c.execute("INSERT INTO users(id,username,password_hash) VALUES (1,'b05-synthetic','unused')")
  cred=BundleCredential(hashlib.sha256(b'b05-owned-profile').hexdigest(),1)
  c.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",(cred.token_hash,))
 db.install();db.bootstrap();repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540));manifest=repo.create(cred,request_id=str(uuid4()),guard=lambda:cred)
 for _ in range(3):assert repo.lookup(manifest['observation_id'],cred,guard=lambda:cred)==manifest
 plain=[]
 for _ in range(20):
  t=time.perf_counter_ns();assert repo.lookup(manifest['observation_id'],cred,guard=lambda:cred)==manifest;plain.append(time.perf_counter_ns()-t)
 with patch.object(Object,'body',tagged(origin[0],'body')),patch.object(Object,'__post_init__',tagged(origin[1],'constructor')),patch.object(canonical,'decode_c1',decoded),patch.object(ObservationRepository,'_lookup',looked):
  timed=[]
  for _ in range(20):
   t=time.perf_counter_ns();assert repo.lookup(manifest['observation_id'],cred,guard=lambda:cred)==manifest;timed.append(time.perf_counter_ns()-t)
 repo.release(manifest['observation_id'],cred,guard=lambda:cred)
result={'source':str(R),'source_file_sha256':hashlib.sha256((R/'backend/isolated_sync/observation.py').read_bytes()).hexdigest(),'N':1000,'H_current_rows':105,'lookups':len(lookup),'decode_counts':dict(count),'decode_ns':dict(decode_ns),'body_size_distribution':[{'operation':k[0],'bytes':k[1],'calls':v} for k,v in sorted(sizes.items())],'lookup_total_ns':sum(lookup),'lookup_median_ns':statistics.median(lookup),'public_lookup_plain_median_ns':statistics.median(plain),'public_lookup_profiled_median_ns':statistics.median(timed),'profile_observed_ratio':statistics.median(timed)/statistics.median(plain),'hot_ref_bytes':int(manifest['target']['hot_ref']['bytes']),'actual_engine':manifest['target']['context']['financial_engine'],'instrumentation':'B03 OFF; function wrappers only for bounded20-call diagnostic','limits':'profile wrappers add timers/ContextVar/count work; ratio is observer+order variation, no causal overhead isolation','source_canonical_result':'exact manifest equality for all43 calls'}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('lookups','decode_counts','lookup_median_ns','public_lookup_plain_median_ns','profile_observed_ratio')}))

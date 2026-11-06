"""N1k/5k용 공유 raw DB와 engine별 view를 지원 API/SQLite backup으로 준비한다."""
import base64,contextlib,hashlib,importlib.util,json,os,pathlib,sqlite3,sys,time
from datetime import date,datetime
from unittest.mock import patch
from uuid import UUID,uuid4
R=pathlib.Path(os.environ['B05A_TREE']);E=pathlib.Path(os.environ['B05A_EVIDENCE']);W=pathlib.Path(os.environ['B05A_SCRATCH']);N=int(sys.argv[2]);assert N in [1000,5000]
sys.path[:0]=[str(R/'backend'),str(R/'scripts/benchmarks'),str(R/'docs/benchmarks/t66f-b03')]
import counters as cost
from app import auth
from app.services.authoritative_state import BundleCredential
from isolated_sync.observation import Evaluation
from isolated_sync.retention_schema import RetentionSandbox
from isolated_sync.retention import RetentionRepository
from t66d2b_writers import seed
from tests.test_isolated_sync_capture import freeze_timestamps
spec=importlib.util.spec_from_file_location('b05a_oracle',R/'docs/benchmarks/t66f-b02-independent/oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
TOKEN='synthetic-B05A-owned-fixed-credential';cred=BundleCredential(auth._hash_session_token(TOKEN),1);out=W/f'fixtures-n{N}';out.mkdir(exist_ok=True)
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def backup(db,path):
 assert not path.exists()
 with contextlib.closing(sqlite3.connect(db.path)) as a,contextlib.closing(sqlite3.connect(path)) as b:a.backup(b);assert b.execute('PRAGMA quick_check').fetchone()[0]=='ok'
mode=sys.argv[1]
with RetentionSandbox() as db,patch('app.services.judgment.common._MESSAGE_RANDOM.randrange',return_value=0):
 if mode=='A':
  with db.connect() as c:
   seed(c,N);c.execute("INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order,is_primary_income) VALUES (101,'2026-10-05','fixed-width-cash',-50,2,0)")
   c.execute("INSERT INTO users(id,username,password_hash) VALUES (1,'b05a-synthetic','unused')");c.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",(cred.token_hash,));freeze_timestamps(c)
  db.install();collector=cost.Collector();t=time.perf_counter_ns();cpu=time.process_time_ns()
  with patch('isolated_sync.finalization.uuid4',side_effect=[UUID(int=i,version=4) for i in range(1,65)]),cost.instrument(),cost.instrument_connections(),cost.instrument_workers(),collector.stage('generation'):db.bootstrap()
  collector.close();assert collector.closed and collector.pending==0
  generation={'on':True,'wall_ns':time.perf_counter_ns()-t,'CPU_ns':time.process_time_ns()-cpu,'counters':collector.snapshot(),'closed':collector.closed}
  repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540));m=repo.create(cred,request_id=str(uuid4()),guard=lambda:cred)
  with sqlite3.connect(db.path) as c:
   _,g=oracle.walk(c,m['target']);control=json.loads(c.execute('SELECT body FROM sync_objects WHERE hash=?',(m['target']['control_ref']['hash'],)).fetchone()[0])
  repo.release(m['observation_id'],cred,guard=lambda:cred);backup(db,out/'template-A.sqlite')
  value={'A':{'manifest':m,'graph':g},'control_exported_at':control['exported_at'],'N':N,'generation':generation};save(out/'fixture-A.json',value)
 elif mode=='B':
  value=json.loads((out/'fixture-A.json').read_text())
  with contextlib.closing(sqlite3.connect(out/'template-A.sqlite')) as a,contextlib.closing(sqlite3.connect(db.path)) as b:a.backup(b)
  # fixture 생성 중 control timestamp만 맞춘다. 측정 server는 항상 실제 utc_now를 사용한다.
  fixed=datetime.fromisoformat(value['control_exported_at'].replace('Z','+00:00'))
  repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540),clock=lambda:fixed);t=time.perf_counter_ns();m=repo.create(cred,request_id=str(uuid4()),guard=lambda:cred)
  creation=time.perf_counter_ns()-t
  with sqlite3.connect(db.path) as c:_,g=oracle.walk(c,m['target'])
  repo.release(m['observation_id'],cred,guard=lambda:cred)
  a=value['A']['manifest']['target'];b=m['target']
  assert all(a[k]==b[k] for k in ['ns','principal_id','versions','revision','raw_ref','index_ref','control_ref']);assert a['context']['financial_engine']!=b['context']['financial_engine'];assert value['A']['graph']['raw_value_sha256']==g['raw_value_sha256']
  value['B']={'manifest':m,'graph':g,'preparatory_hot_creation_ns':creation};backup(db,out/'template-combined.sqlite');value['template_sha256']=hashlib.sha256((out/'template-combined.sqlite').read_bytes()).hexdigest();save(out/'fixture.json',value);save(E/f'fixture-n{N}.json',value)
 else:raise ValueError(mode)
print(json.dumps({'N':N,'mode':mode,'prepared':True}))

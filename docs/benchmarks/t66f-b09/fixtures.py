"""보존 합성 fixture에 B08 engine view만 준비. cold timing 밖이며 금융 행은 불변."""
import contextlib,gzip,hashlib,importlib.util,json,os,sqlite3,sys
from pathlib import Path
from datetime import date,datetime
from uuid import uuid4
from unittest.mock import patch
R=Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=Path('/tmp/money-note-t66f-b09-20261026');N=int(sys.argv[1]);assert N in (1000,5000)
C=W/'candidate';sys.path[:0]=[str(C/'backend'),str(C/'scripts/benchmarks')]
from isolated_sync.retention_schema import RetentionSandbox
from isolated_sync.retention import RetentionRepository
from isolated_sync.observation import Evaluation,engine_artifact
from app.services.authoritative_state import BundleCredential
from app import auth
s=importlib.util.spec_from_file_location('oracle',C/'docs/benchmarks/t66f-b02-independent/oracle.py');oracle=importlib.util.module_from_spec(s);s.loader.exec_module(oracle)
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
source=json.loads((R/f'docs/benchmarks/t66f-b05a/fixture-n{N}.json').read_text());F=W/f'fixtures-n{N}';assert not (F/'template-combined.sqlite').exists()
assert sha(engine_artifact())=='5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c'
assert sha((F/'original-template.sqlite').read_bytes())==source['template_sha256']
def rows(c):
 return {t:sha(json.dumps(sorted([list(r) for r in c.execute('SELECT * FROM '+t)],key=repr),ensure_ascii=False,separators=(',',':')).encode()) for t in source['A']['graph']['raw_rows']}
with RetentionSandbox() as db,patch('app.services.judgment.common._MESSAGE_RANDOM.randrange',return_value=0):
 with contextlib.closing(sqlite3.connect(F/'original-template.sqlite')) as a,contextlib.closing(sqlite3.connect(db.path)) as b:a.backup(b)
 with contextlib.closing(sqlite3.connect(db.path)) as c:before=rows(c)
 fixed=datetime.fromisoformat(source['control_exported_at'].replace('Z','+00:00'));cred=BundleCredential(auth._hash_session_token('synthetic-B05A-owned-fixed-credential'),1)
 repo=RetentionRepository(db,evaluation=lambda:Evaluation(date(2026,10,5),540),clock=lambda:fixed)
 m=repo.create(cred,request_id=str(uuid4()),guard=lambda:cred);repo.release(m['observation_id'],cred,guard=lambda:cred)
 a=source['A']['manifest']['target'];b=m['target'];assert all(a[k]==b[k] for k in ['ns','principal_id','versions','revision','raw_ref','index_ref','control_ref'])
 with contextlib.closing(sqlite3.connect(db.path)) as c:
  assert before==rows(c)
  hot=lambda ref:json.loads(c.execute('SELECT body FROM sync_objects WHERE hash=?',(ref['hash'],)).fetchone()[0])['state']
  assert hot(a['hot_ref'])==hot(b['hot_ref'])
  _,ga=oracle.walk(c,a,client=False,sql_values=True);_,gb=oracle.walk(c,b,client=False,sql_values=True)
  assert ga['objects']==gb['objects']==source['A']['graph']['objects'];assert ga['raw_value_sha256']==gb['raw_value_sha256'];assert ga['canonical_bytes']==gb['canonical_bytes']
  with contextlib.closing(sqlite3.connect(F/'template-combined.sqlite')) as target:c.backup(target)
 data=(F/'template-combined.sqlite').read_bytes()
 d={'N':N,'template_sha256':sha(data),'preserved_template_sha256':source['template_sha256'],'control_exported_at':source['control_exported_at'],'A':{'manifest':source['A']['manifest'],'graph':ga},'B':{'manifest':m,'graph':gb},'financial_rows_before_after':before,'semantic_equivalence':True,'engine_dependent_differences':['context.financial_engine','hot_ref.hash','sync_root'],'prepared_outside_cold':True,'observation_policy_unchanged':True}
 save(F/'fixture.json',d);save(E/f'fixture-n{N}.json',d)
 (E/f'template-n{N}.sqlite.gz').write_bytes(gzip.compress(data,mtime=0))
 print(json.dumps({'N':N,'objects':ga['objects'],'canonical_bytes':ga['canonical_bytes'],'financial_equivalent':True,'template_sha':sha(data)}))

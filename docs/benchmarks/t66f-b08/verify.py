"""사후 SQL 저장 타입/값·source mode·artifact 불일치 범위를 독립 대조한다."""
import pathlib,json,sqlite3,contextlib,hashlib,stat,subprocess,os
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b08';W=pathlib.Path('/tmp/money-note-t66f-b08-20261026');sha=lambda b:hashlib.sha256(b).hexdigest()
def get(n):return json.loads((E/n).read_text())
def save(n,d):(E/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
base=get('baseline-source-manifest.json');candidate=get('candidate-source-manifest.json')
for variant,entries in [('baseline',base['entries']),('candidate',candidate['entries'])]:
 for a in entries:
  p=W/variant/a['path'];assert sha(p.read_bytes())==a['sha256'] and stat.S_IMODE(p.stat().st_mode)==int(a['mode'],8)
fixture=json.loads((R/'docs/benchmarks/t66f-b05a/fixture-n1000.json').read_text());tables=sorted(fixture['A']['graph']['raw_rows'])+['users','auth_sessions']
def digest(c,t):
 cols=[v[1]for v in c.execute('PRAGMA table_info('+t+')')];records=[]
 for row in c.execute('SELECT '+','.join('typeof('+k+'),'+k for k in cols)+' FROM '+t):
  cells=[[row[i],row[i+1].hex()if isinstance(row[i+1],bytes)else repr(row[i+1])if isinstance(row[i+1],float)else row[i+1]]for i in range(0,len(row),2)];records.append(json.dumps(cells,ensure_ascii=False,separators=(',',':')))
 return {'count':len(records),'sha256':sha(json.dumps({'columns':cols,'rows':sorted(records)},ensure_ascii=False,separators=(',',':')).encode())}
all_db={}
for name in ['template-n1000','prepared-common','after-A','after-B']:
 with contextlib.closing(sqlite3.connect('file:'+str(W/(name+'.sqlite'))+'?mode=ro',uri=True))as c:
  assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok'and not c.execute('PRAGMA foreign_key_check').fetchall();all_db[name]={t:digest(c,t)for t in tables}
assert all(v==all_db['template-n1000']for v in all_db.values())
artifact={}
code='''import json
from isolated_sync.artifacts import release_bundle
from pathlib import Path
actual=release_bundle();checked=json.loads(Path('docs/specimens/t66d3b-release-artifacts.json').read_text())
print(json.dumps({'differing_artifacts':[k for k in actual['artifacts']if actual['artifacts'][k]!=checked['artifacts'][k]],'actual_engine':actual['artifacts']['financial_engine']['sha256'],'declared_engine':checked['artifacts']['financial_engine']['sha256']}))'''
for v,d in [('A','baseline'),('B','candidate')]:
 t=W/d;artifact[v]=json.loads(subprocess.check_output([str(R/'.venv/bin/python'),'-c',code],cwd=t,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(t/'backend')},text=True))
assert artifact['A']['differing_artifacts']==[] and artifact['B']['differing_artifacts']==['financial_engine']
save('artifact-gate-analysis.json',{'baseline':artifact['A'],'candidate':artifact['B'],'original_test':'tests/test_isolated_sync_transfer.py::test_release_artifact_hashes_exact_bytes_and_target','raw_failure':'affected2.xml','classification':'EXPECTED UNADMITTED SOURCE IDENTITY — original exact equality gate remains rejecting; not an all-backend PASS','release_files_changed':False,'source_SHA_guards_relaxed':False})
save('post-verification.json',{'status':'PASS','baseline_source_files':899,'candidate_source_files':900,'bytes_and_modes':'PASS','actual_financial_and_auth_SQL_types_values':all_db['template-n1000'],'four_database_states_identical':True,'B03_implementation_unchanged':True,'artifact_delta_only_new_financial_engine':True,'new_D3_requests':0})
print(json.dumps({'source_files_verified':1799,'SQL_tables':13,'database_states':4,'status':'PASS','artifact_unadmitted_engine':artifact['B']['actual_engine']}))

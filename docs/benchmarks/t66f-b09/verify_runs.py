"""종료한 실제 run을 독립 graph/row oracle 및 지원 SQLite backup으로 보존한다."""
import argparse,contextlib,gzip,hashlib,importlib.util,json,pathlib,sqlite3,time
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=pathlib.Path('/tmp/money-note-t66f-b09-20261026')
spec=importlib.util.spec_from_file_location('b05a_independent_oracle',R/'docs/benchmarks/t66f-b02-independent/oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
parser=argparse.ArgumentParser();parser.add_argument('N',type=int,choices=[1000,5000]);args=parser.parse_args();N=args.N
plan=json.loads((E/f'plan-n{N}.json').read_text());verified=[]
for cfg in plan['runs']:
 out=pathlib.Path(cfg['out']);d=json.loads((out/'run.json').read_text());completion=json.loads((out/'completion.json').read_text());assert completion=={'status':'COMPLETED','server_exit':0};assert d['status']=='COMPLETED' and d['valid_completed'] and all(d[k] for k in ['E1','E2','E3','E4'])
 target=d['accepted_after']['target'];assert target['context']['financial_engine']==cfg['engine_sha'];expected=json.loads((E/f'fixture-n{N}.json').read_text())[cfg['variant']]['graph']
 assert d['accepted_before']['id'] is None and d['db_before']['objects']==0 and d['accepted_after']['sequence']==1 and d['accepted_after']['previous_id'] is None
 result={};sets={}
 client=pathlib.Path(d['client_db_path']);assert str(client).startswith(str(W)+'/disposable/')
 for role,path in [('client',client),('backend',out/'server/backend-final.sqlite')]:
  with contextlib.closing(sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)) as c:
   assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
   hashes,graph=oracle.walk(c,target,client=role=='client',sql_values=role=='backend');sets[role]=hashes
   assert graph['raw_value_sha256']==expected['raw_value_sha256'];assert graph['objects']==expected['objects']==d['completed_objects']
   if role=='client':
    current=c.execute('SELECT current_id,previous_id,sequence FROM accepted WHERE id=1').fetchone();assert current==(d['accepted_after']['id'],None,1)
    assert c.execute('SELECT count(*) FROM objects').fetchone()[0]==graph['objects']
    h=hashlib.sha256(oracle.encode(json.loads(c.execute('SELECT body FROM objects WHERE hash=?',(target['hot_ref']['hash'],)).fetchone()[0])['state'])).hexdigest();assert h==d['semantic_digest']['financial_state_sha256']
   backup=out/(role+'-consistent.sqlite');assert not backup.exists()
   with contextlib.closing(sqlite3.connect(backup)) as dst:c.backup(dst)
  data=backup.read_bytes();result[role]={'graph':graph,'backup_sha256':hashlib.sha256(data).hexdigest(),'backup_bytes':len(data)}
  # raw evidence 위치에는 파일을 고유 이름으로만 생성한다.
  (out/(role+'-consistent.sqlite.gz')).write_bytes(gzip.compress(data,mtime=0));backup.unlink()
 assert sets['client']==sets['backend'];assert d['semantic_digest']['raw_value_sha256']==expected['raw_value_sha256']
 assert d['collector_closed'] and not d['observation_expired'];requests=d['backend']['requests'];assert all(v['collector_closed'] and v['pending']==0 and v['completion_error'] is None and v['error'] is None for v in requests)
 save(out/'independent-verification.json',{'status':'PASS','matched_client_backend':True,'accepted_native':list(current),'objects':len(sets['client']),'details':result,'E4_semantics':d['semantic_digest']});verified.append(d)
 for name in ['requests.jsonl']:
  p=out/'server'/name;(out/'server'/(name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0));p.unlink()
 # 보존할 SQLite 원본은 일관 backup gzip으로 대체했다. 서버 종료·독립 검증 후에만 제거한다.
 (out/'server/backend-final.sqlite').unlink()
 client.unlink()
for variant in ['A','B']:
 a=[d for d in verified if d['variant']==variant];assert len({d['accepted_after']['target']['sync_root'] for d in a})==1
 assert len({d['semantic_digest']['financial_state_sha256'] for d in a})==1
assert len({json.dumps(d['semantic_digest'],sort_keys=True) for d in verified})==1
allmetrics=[]
for d in verified:
 dst=E/'raw'/d['id'];assert not dst.exists();dst.parent.mkdir(exist_ok=True)
 import shutil
 shutil.copytree(pathlib.Path(d['out']),dst)
 allmetrics.append({'id':d['id'],'N':N,'variant':d['variant'],'on':d['on'],'rep':d['rep'],'seconds':d['end_to_end_with_bounded_E4_us']/1e6,'objects':d['completed_objects'],'accepted_id':d['accepted_after']['id'],'raw':str(dst.relative_to(R)/'run.json'),'valid_completed':True})
save(E/f'cohort-n{N}.json',{'status':'PASS','runs':allmetrics,'within_engine_ON_OFF':'PASS' if N==1000 else 'NOT MEASURED — ON only','cross_engine_raw_financial':'PASS','independent_graph_oracle':'PASS','N50k':0,'N100k':0})
print(json.dumps({'N':N,'valid_completed':len(verified),'semantic_equivalence':'PASS','end_to_end_s':[v['seconds'] for v in allmetrics]}))

"""완료된 B04 cohort의 일관 DB·독립 oracle·정리 영수증."""
import gzip,hashlib,importlib.util,json,os,pathlib,shutil,sqlite3,subprocess,sys,time
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b04';W=pathlib.Path('/tmp/money-note-t66f-b04-20261026');T=W/'tree';cohort=sys.argv[1];O=E/'raw'/cohort;A=E/'artifacts'/cohort;A.mkdir(parents=True,exist_ok=True);assert not (A/'manifest.json').exists() and not list(A.glob('*.gz'))
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
s=importlib.util.spec_from_file_location('b04_independent_oracle',T/'docs/benchmarks/t66f-b02-independent/oracle.py');oracle=importlib.util.module_from_spec(s);s.loader.exec_module(oracle)
rows=[]
for p in O.glob('*.json'):
 d=json.loads(p.read_text())
 if 'run_id' in d and d['status']=='COMPLETED':rows.append(d)
rows.sort(key=lambda x:x['end_utc']);last={d['on']:d for d in rows};record={'cohort':cohort,'status':'PRESERVED','artifacts':[],'matches':{},'cleanup':[],'time':time.time()}
backend=O/'server/backend-final.sqlite';backend_graph=None
if backend.exists() and last:
 target=rows[-1]['accepted_after']['target'];c=sqlite3.connect(f'file:{backend}?mode=ro',uri=True)
 _,backend_graph=oracle.walk(c,target);c.close();record['backend_graph']=backend_graph

def capture(source,name,target=None,client=False):
 assert source.is_file();before=source.stat();check=subprocess.run(['fuser',str(source)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);assert check.returncode==1 and not check.stdout and not check.stderr,(source,'active or unavailable fuser')
 tmp=W/'disposable'/f'{cohort}-{name}-backup.sqlite';assert not tmp.exists();src=sqlite3.connect(f'file:{source}?mode=ro',uri=True);dst=sqlite3.connect(tmp);src.backup(dst);src.close()
 qc=dst.execute('PRAGMA quick_check').fetchall();fk=dst.execute('PRAGMA foreign_key_check').fetchall();assert qc==[('ok',)] and not fk
 graph=None
 if target:
  _,graph=oracle.walk(dst,target,client=client,sql_values=not client)
  if backend_graph is not None:
   for k in ('objects','canonical_bytes','kinds','raw_rows','raw_value_sha256','audit_reachable_hash_set_sha256'):assert graph[k]==backend_graph[k],(name,k)
 dst.close();digest=sha(tmp.read_bytes());out=A/f'{name}.sqlite.gz'
 with tmp.open('rb') as a,out.open('xb') as b:
  with gzip.GzipFile(filename='',mode='wb',fileobj=b,mtime=0,compresslevel=6) as g:shutil.copyfileobj(a,g)
 with gzip.open(out,'rb') as g:assert sha(g.read())==digest
 item={'name':name,'source':str(source),'source_inode':before.st_ino,'backup_api':True,'sqlite_sha256':digest,'sqlite_bytes':tmp.stat().st_size,'gzip_sha256':sha(out.read_bytes()),'gzip_path':str(out.relative_to(R)),'quick_check':qc,'foreign_key_check':fk,'graph':graph}
 record['artifacts'].append(item);tmp.unlink();return item
if backend.exists():capture(backend,'backend',rows[-1]['accepted_after']['target'] if rows else None)
for on,d in last.items():
 capture(pathlib.Path(d['database_path']),'client-on' if on else 'client-off',d['accepted_after']['target'],True);record['matches'][str(on)]={'accepted':d['accepted_after'],'backend_target':d['expected_target'],'all_raw_values_and_reachable_objects_equal':True}
save(A/'manifest.json',record)
# 검증·압축·manifest 기록이 끝난 자기 소유 비활성 backup만 삭제한다.
if backend.exists():
 st=backend.stat();assert not subprocess.run(['fuser','-s',str(backend)]).returncode==0
 record['cleanup'].append({'path':str(backend),'bytes':st.st_size,'allocated_bytes':st.st_blocks*512,'reason':'verified gzip backup and graph oracle retained'});backend.unlink()

# 측정이 끝나고 matched backup/oracle이 보존된 client의 자기 소유 DB만 정리한다.
for on,d in last.items():
 source=pathlib.Path(d['database_path']);root=source.parent.parent
 assert root.parent==W/'disposable' and root.name.startswith('n')
 files=[p for p in root.rglob('*') if p.is_file()]
 assert not any(p.is_symlink() for p in root.rglob('*'))
 for p in files:
  check=subprocess.run(['fuser',str(p)],capture_output=True,text=True);assert check.returncode==1 and not check.stdout and not check.stderr,(p,'active')
  if p.suffix=='.sqlite' and p!=source:
   c=sqlite3.connect(f'file:{p}?mode=ro',uri=True)
   assert c.execute('SELECT count(*) FROM objects').fetchone()[0]==0 and c.execute('SELECT sequence FROM accepted').fetchone()[0]==0
   c.close()
  if '.sqlite' not in p.name:
   dst=A/('client-on-files' if on else 'client-off-files')/p.relative_to(root);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
  st=p.stat();record['cleanup'].append({'path':str(p),'bytes':st.st_size,'allocated_bytes':st.st_blocks*512,'reason':'matched DB gzip/oracle or disposable empty initialization; companion files retained'})
 save(A/'manifest.json',record)
 shutil.rmtree(root)

save(A/'manifest.json',record);print(json.dumps({'cohort':cohort,'preserved':len(record['artifacts']),'matched':len(record['matches'])}))

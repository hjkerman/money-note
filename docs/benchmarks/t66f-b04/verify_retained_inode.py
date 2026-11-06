"""측정 종료 뒤 emergency inode와 authoritative online backup의 전체 SQL 값 대조."""
import base64,gzip,hashlib,json,pathlib,shutil,sqlite3,subprocess
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b04';W=pathlib.Path('/tmp/money-note-t66f-b04-20261026')
assert json.loads((E/'execution-n50000-v3.json').read_text())['status']=='COMPLETED'
assert json.loads((E/'retention-n50000-v3.json').read_text())['exit']==0
m=json.loads((E/'failure-retention.json').read_text());raw=pathlib.Path(m['retained_inode_path']);assert raw.stat().st_ino==m['inode']
f=subprocess.run(['fuser',str(raw)],capture_output=True,text=True);assert f.returncode==1 and not f.stdout and not f.stderr
manifest=json.loads((E/'artifacts/n50000-v3/manifest.json').read_text());entry=next(x for x in manifest['artifacts'] if x['name']=='backend');dest=W/'disposable/verified-backend-final.sqlite'
assert not dest.exists()
with gzip.open(R/entry['gzip_path'],'rb') as a,dest.open('xb') as b:shutil.copyfileobj(a,b)
assert hashlib.sha256(dest.read_bytes()).hexdigest()==entry['sqlite_sha256']
def quote(s):return '"'+s.replace('"','""')+'"'
def digest(path,immutable=False):
 conn=sqlite3.connect(f'file:{path}?mode=ro'+('&immutable=1' if immutable else ''),uri=True)
 assert conn.execute('PRAGMA quick_check').fetchall()==[('ok',)] and not conn.execute('PRAGMA foreign_key_check').fetchall()
 out={};schema=list(conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"));sd=hashlib.sha256(json.dumps(schema,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
 for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
  cols=conn.execute(f'PRAGMA table_info({quote(name)})').fetchall();pk=[v[1] for v in sorted(cols,key=lambda v:v[5]) if v[5]];order=','.join(quote(v) for v in pk) if pk else 'rowid';h=hashlib.sha256();count=0
  for row in conn.execute(f'SELECT * FROM {quote(name)} ORDER BY {order}'):
   values=[{'blob':base64.b64encode(v).decode()} if isinstance(v,bytes) else v for v in row];h.update(json.dumps(values,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()+b'\n');count+=1
  out[name]={'count':count,'typed_values_sha256':h.hexdigest()}
 conn.close();return {'schema_sha256':sd,'tables':out}
a=digest(raw,True);b=digest(dest);assert a==b
r={'same_device_inode_as_measured_backend':True,'active_processes':False,'method':'after normal exit; read-only immutable raw inode vs independently supported SQLite backup, full schema/all-table typed-value streaming digests','all_logical_SQL_values_equal':True,'raw_inode':str(raw),'authoritative_backup':entry['gzip_path'],'digest':a,'disposable_comparison_bytes':dest.stat().st_size,'not_physical_IO_or_power_loss_proof':True}
(E/'failure-retention-final.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');dest.unlink();print(json.dumps({'all_tables_equal':True,'tables':len(a['tables']),'raw_inode_can_be_disposed_after_verified_backup':True}))

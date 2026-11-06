"""B05-A의 일관 backup·raw·source 동결 확인 후 비활성 scratch만 제거한다."""
import gzip,hashlib,json,os,pathlib,shutil,time
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05a';W=pathlib.Path('/tmp/money-note-t66f-b05a-20261026')
assert W.parent==pathlib.Path('/tmp') and W.name=='money-note-t66f-b05a-20261026'
manifest=json.loads((E/'run-manifest.json').read_text());assert len(manifest['runs'])==12 and manifest['valid_completed_cold']==12
backups=[]
for p in sorted((E/'raw').glob('*/**/*-consistent.sqlite.gz')):
 b=gzip.decompress(p.read_bytes());assert b.startswith(b'SQLite format 3\0');backups.append({'path':str(p.relative_to(E)),'gzip_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'SQLite_sha256':hashlib.sha256(b).hexdigest(),'SQLite_bytes':len(b)})
assert len(backups)==24
(E/'retained-backups.json').write_text(json.dumps({'matched_pairs':12,'backups':backups,'fixture_templates':2,'verification':'각 run independent-verification.json; native accepted+graph+row+FK/quick_check 후 backup'},ensure_ascii=False,indent=2)+'\n')
f=json.loads((E/'freeze.json').read_text());assert f['reconstruction']=='PASS' and hashlib.sha256(pathlib.Path(f['archive']).read_bytes()).hexdigest()==f['archive_sha256']
active=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:
  if os.readlink(p/'cwd').startswith(str(W)+'/'):active.append((p.name,'cwd'))
 except OSError:pass
 try:
  for fd in (p/'fd').iterdir():
   try:
    if os.readlink(fd).startswith(str(W)+'/'):active.append((p.name,'fd'))
   except OSError:pass
 except OSError:pass
assert not active,active
allocated=0;logical=0;files=0
for root,dirs,names in os.walk(W,followlinks=False):
 dirs[:]=[p for p in dirs if not (pathlib.Path(root)/p).is_symlink()]
 for name in names:
  p=pathlib.Path(root)/name
  if not p.is_symlink():
   s=p.stat();allocated+=s.st_blocks*512;logical+=s.st_size;files+=1
before=shutil.disk_usage(W).free;shutil.rmtree(W);assert not W.exists()
result={'scratch':str(W),'removed':True,'removed_files':files,'observed_removed_allocated_bytes':allocated,'observed_removed_logical_bytes':logical,'active_users':active,'matched_SQLite_backups_retained':24,'template_backups_retained':2,'source_archive_retained':f['archive'],'retained_evidence_bytes':sum(p.stat().st_size for p in E.rglob('*') if p.is_file()),'preexisting_files_deleted':0,'historical_evidence_deleted':0,'external_cache_deleted':False,'active_DB_WAL_deleted':False,'free_before':before,'free_after':shutil.disk_usage(R).free,'time_unix':time.time(),'note':'st_blocks 관찰 합이다. free 변화에는 호스트의 다른 쓰기가 섞인다.'}
(E/'cleanup.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))

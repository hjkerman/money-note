"""후속 검증에 필요한 B05 증거를 확인한 뒤 비활성 task scratch만 정리한다."""
import gzip,hashlib,json,os,pathlib,shutil,sys,time
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05';W=pathlib.Path('/tmp/money-note-t66f-b05-20261026')
assert W.name=='money-note-t66f-b05-20261026' and W.parent==pathlib.Path('/tmp')
for n in ['profile-baseline.log','profile-optimized.log']:
 (E/(n+'.gz')).write_bytes(gzip.compress((W/'raw'/n).read_bytes(),mtime=0))
freeze=json.loads((E/'experimental-freeze.json').read_text());assert freeze['reconstruction']=='PASS';assert hashlib.sha256((E/'experimental-source.tar.gz').read_bytes()).hexdigest()==freeze['archive_sha256']
backup_manifest=[]
for p in sorted(E.glob('backend-*-backend.sqlite.gz')):
 b=gzip.decompress(p.read_bytes());assert b.startswith(b'SQLite format 3\0');backup_manifest.append({'path':p.name,'gzip_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sqlite_sha256':hashlib.sha256(b).hexdigest(),'sqlite_bytes':len(b)})
assert len(backup_manifest)==8
(E/'retained-backend-backups.json').write_text(json.dumps({'method':'지원 SQLite backup + quick_check + gzip; 실행 완료 후 생성','client_backup':None,'records':backup_manifest},ensure_ascii=False,indent=2)+'\n')
active=[];prefix=str(W)+'/'
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid():continue
 try:
  if os.readlink(p/'cwd').startswith(prefix):active.append({'pid':p.name,'kind':'cwd'})
 except OSError:pass
 try:
  for fd in (p/'fd').iterdir():
   try:
    if os.readlink(fd).startswith(prefix):active.append({'pid':p.name,'kind':'open_fd'})
   except OSError:pass
 except OSError:pass
assert not active,active
allocated=0;logical=0;files=0
for root,dirs,names in os.walk(W,followlinks=False):
 dirs[:]=[a for a in dirs if not (pathlib.Path(root)/a).is_symlink()]
 for n in names:
  p=pathlib.Path(root)/n
  if not p.is_symlink():
   s=p.stat();allocated+=s.st_blocks*512;logical+=s.st_size;files+=1
free_before=shutil.disk_usage(W).free;shutil.rmtree(W);assert not W.exists()
result={'scratch':str(W),'scratch_removed':True,'removed_files':files,'observed_removed_allocated_bytes':allocated,'observed_removed_logical_bytes':logical,'active_owned_users_at_delete':active,'retained_evidence_bytes':sum(p.stat().st_size for p in E.rglob('*') if p.is_file()),'retained_backups':8,'retained_source_archive':True,'retained_raw_logs':True,'historical_files_deleted':0,'frozen_B03_modified':False,'external_cache_deleted':False,'active_DB_WAL_deleted':False,'free_before':free_before,'free_after':shutil.disk_usage(R).free,'time_unix':time.time(),'limitations':'전후 free 변화는 호스트 다른 쓰기와 섞임. 관찰 st_blocks 합만 task 제거량으로 기록.'}
(E/'cleanup.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))

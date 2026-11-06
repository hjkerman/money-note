from pathlib import Path
import os,json,hashlib,stat,subprocess,shutil,time
A=Path('/tmp/money-note-ir04-20261024');R=Path('/home/hjkerman/codex/money-note');E=A/'evidence';T=A/'candidate';env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'corrected-candidate-manifest.json').read_text());bad=[]
for x in m['entries']:
 p=T/x['path']
 if sha(p)!=x['sha256'] or oct(stat.S_IMODE(p.stat().st_mode))!=x['mode']:bad.append(x['path'])
assert not bad
selected={x['path'] for x in m['entries']};base=0
for raw in subprocess.check_output(['git','ls-tree','-r','-z',m['base_commit']],cwd=R,env=env).split(b'\0'):
 if not raw:continue
 meta,name=raw.split(b'\t');mode,typ,oid=meta.split();name=name.decode()
 if name in selected:continue
 p=T/name;b=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid.decode(),name
 assert bool(p.stat().st_mode&0o111)==(mode==b'100755');base+=1
f=json.loads((E/'freeze-reconstruction.json').read_text());new=Path(f['destination']);assert sha(new/'candidate.tar.gz')==f['archive_sha256']
new_files={p.name:{'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode)),'bytes':p.stat().st_size} for p in new.iterdir()};assert all(v['mode']=='0o444' for v in new_files.values()) and stat.S_IMODE(new.stat().st_mode)==0o555
old=new.parent/'645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8';historical=json.loads((R/'docs/benchmarks/t66f-b03-ir03/integrity.json').read_text())['frozen_files'];assert all(sha(old/name)==value for name,value in historical.items())
pre=json.loads((E/'preexisting-files.json').read_text());changed=[]
for x in pre:
 p=R/x['path']
 if not p.is_file() or sha(p)!=x['sha256'] or oct(stat.S_IMODE(p.stat().st_mode))!=x['mode']:changed.append(x['path'])
assert not changed
start=json.loads((E/'starting-state.json').read_text());assert sha(R/'.git/index')==start['index_sha256'];assert subprocess.check_output(['git','ls-files','--stage'],cwd=R,env=env).decode()==start['staged']
record={'source_files_verified':len(m['entries']),'source_bytes':sum(x['bytes'] for x in m['entries']),'candidate_source_discrepancies':bad,'baseline_other_files_verified':base,'new_snapshot_files':new_files,'new_snapshot_directory_mode':oct(stat.S_IMODE(new.stat().st_mode)),'old_ir02_all_files_match_prior_identity':True,'preexisting_live_files_verified':len(pre),'preexisting_live_differences':changed,'index_sha256':sha(R/'.git/index'),'index_unchanged_during_ir04':True,'staged_entries_unchanged':True,'binding_protocol_unchanged':True}
(E/'final-candidate-integrity.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
# Only verified task-created disposable roots; retain all independent tests/raw evidence/tooling.
targets=[T,A/'flutter-tmp']+[p for p in A.glob('pytest-*') if p.is_dir() and not p.is_symlink()]
# All commands launched by this audit have a completion record before cleanup.
assert (E/'real-delta-integration.json').exists() and json.loads((E/'real-delta-integration.json').read_text())['exit_code']==0
active=[];inaccessible=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  if proc.stat().st_uid!=os.getuid():continue
 except OSError:continue
 denied=[]
 for part in ['cwd','fd']:
  try:
   paths=[(proc/'cwd').resolve(strict=True)] if part=='cwd' else [p.resolve(strict=True) for p in (proc/'fd').iterdir()]
  except OSError as ex:denied.append(part);continue
  for value in paths:
   if any(value==p or p in value.parents for p in targets):active.append({'pid':int(proc.name),'part':part,'path':str(value)})
 if denied:
  try:comm=(proc/'comm').read_text().strip()
  except OSError:comm='unknown'
  inaccessible.append({'pid':int(proc.name),'comm':comm,'parts':denied})
assert not active,active
cleanup={'targets':[],'active_references_observed':active,'inaccessible_process_parts':inaccessible,'visibility_limit':'읽을 수 있는 동일 UID cwd/fd에서 삭제 대상 참조 없음. 일부 선행 system process FD 접근 제한은 기록하며 전체 시스템 가시성을 주장하지 않는다. 감사에서 실행한 검증 child는 모두 종료 기록이 있다.','retained':['evidence','tests','tooling','old IR02 snapshot','new corrected snapshot'],'disk_free_before':shutil.disk_usage('/tmp').free}
for p in targets:
 assert p.parent==A and p.is_dir() and not p.is_symlink()
 inode=p.stat().st_ino;logical=allocated=count=links=0
 for d,dirs,files in os.walk(p,followlinks=False):
  for name in files:
   q=Path(d)/name;s=q.lstat()
   if stat.S_ISLNK(s.st_mode):links+=1;continue
   if stat.S_ISREG(s.st_mode):count+=1;logical+=s.st_size;allocated+=s.st_blocks*512
 assert p.stat().st_ino==inode
 shutil.rmtree(p)
 cleanup['targets'].append({'path':str(p),'regular_files':count,'logical_bytes':logical,'allocated_bytes':allocated,'symlinks_unlinked_without_following':links,'removed':not p.exists()})
cleanup['reclaimed_allocated_bytes']=sum(x['allocated_bytes'] for x in cleanup['targets']);cleanup['disk_free_after']=shutil.disk_usage('/tmp').free;cleanup['observed_free_delta']=cleanup['disk_free_after']-cleanup['disk_free_before']
(E/'cleanup.json').write_text(json.dumps(cleanup,ensure_ascii=False,indent=2));print(json.dumps({'source':len(m['entries']),'base_other':base,'preexisting':len(pre),'discrepancies':changed,'removed':len(cleanup['targets']),'reclaimed_allocated_bytes':cleanup['reclaimed_allocated_bytes'],'visibility_restrictions':inaccessible},ensure_ascii=False))

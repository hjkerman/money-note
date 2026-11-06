from pathlib import Path
import os,json,hashlib,stat,subprocess,shutil
A=Path('/tmp/money-note-ir05-20261024');R=Path('/home/hjkerman/codex/money-note');E=A/'evidence';T=A/'candidate';env=dict(os.environ,GIT_OPTIONAL_LOCKS='0');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((E/'candidate-source-manifest.json').read_text());selected={x['path'] for x in m['entries']}
for x in m['entries']:
 p=T/x['path'];assert sha(p)==x['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==x['mode'],x['path']
base_verified=0
for raw in subprocess.check_output(['git','ls-tree','-r','-z',m['base_commit']],cwd=R,env=env).split(b'\0'):
 if not raw:continue
 meta,name=raw.split(b'\t');mode,typ,oid=meta.split();name=name.decode()
 if name in selected:continue
 p=T/name;b=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid.decode();assert bool(p.stat().st_mode&0o111)==(mode==b'100755');base_verified+=1
snapshots=json.loads((E/'starting-frozen-identities.json').read_text())
for folder,v in snapshots.items():
 p=Path(folder);assert oct(stat.S_IMODE(p.stat().st_mode))==v['directory_mode']
 for name,x in v['files'].items():q=p/name;assert sha(q)==x['sha256'] and oct(stat.S_IMODE(q.stat().st_mode))==x['mode']
pre=json.loads((E/'preexisting-files.json').read_text());bad=[]
for x in pre:
 p=R/x['path']
 if not p.is_file() or sha(p)!=x['sha256'] or oct(stat.S_IMODE(p.stat().st_mode))!=x['mode']:bad.append(x['path'])
assert not bad
s=json.loads((E/'starting-state.json').read_text());assert sha(R/'.git/index')==s['index_sha256'];assert subprocess.check_output(['git','ls-files','--stage'],cwd=R,env=env).decode()==s['staged']
# Preserve exact source facts needed after disposable reconstruction cleanup.
publication=(T/'mobile/lib/src/segmented/store_publication.dart').read_text();assert "finalAuthorityFence();\n      _db.execute('COMMIT');" in publication
proof={'source_files_verified':850,'source_bytes':9247384,'baseline_other_files_verified':base_verified,'source_discrepancies':[],'frozen_directories_preserved':list(snapshots),'frozen_files_preserved':sum(len(v['files']) for v in snapshots.values()),'preexisting_files_verified':len(pre),'preexisting_changes':bad,'index_sha256':sha(R/'.git/index'),'index_preserved_during_ir05':True,'staged_content_preserved':True,'final_E3_guard_commit_adjacent':True,'current_source_payload_sha256':m['candidate_source_digest_sha256']};(E/'final-candidate-integrity.json').write_text(json.dumps(proof,indent=2))
# Runtime completion records cover every launched test/build. Only our unique
# disposable roots are eligible; leave any target with observable active refs.
for name in ['real-sync-integration','flutter-affected','flutter-original-current','flutter-original-historical','backend-affected','frontend-build','flutter-analyze']:
 v=json.loads((E/(name+'.json')).read_text());assert v['exit_code']==0
names=['candidate','failed-reconstruction','context','failed-context','flutter-tmp','pytest-focused','pytest-preserved'];targets=[A/name for name in names if (A/name).exists()];active=[];denied=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  if proc.stat().st_uid!=os.getuid():continue
 except OSError:continue
 missing=[]
 try:observed=[('cwd',(proc/'cwd').resolve(strict=True))]
 except OSError:observed=[];missing.append('cwd')
 try:
  fds=list((proc/'fd').iterdir())
  for fd in fds:
   try:observed.append(('fd',fd.resolve(strict=True)))
   except OSError:pass
 except OSError:missing.append('fd')
 for part,p in observed:
  if any(p==t or t in p.parents for t in targets):active.append({'pid':int(proc.name),'part':part,'path':str(p)})
 if missing:
  try:comm=(proc/'comm').read_text().strip()
  except OSError:comm='unknown'
  denied.append({'pid':int(proc.name),'comm':comm,'parts':missing})
cleanup={'targets':[],'observable_active_references':active,'visibility_limits':denied,'basis':'모든 IR05 child 완료와 독점 생성한 task-owned 경로를 확인. 읽을 수 있는 cwd/fd를 대조했으며 접근 제한 프로세스의 전체 가시성을 주장하지 않음.','disk_free_before':shutil.disk_usage('/tmp').free,'retained':['evidence','tests','tooling','all pre-existing scratch','all frozen snapshots']}
for p in targets:
 assert p.parent==A and p.is_dir() and not p.is_symlink();logical=allocated=count=links=0
 for d,dirs,files in os.walk(p,followlinks=False):
  for name in files:
   q=Path(d)/name;v=q.lstat()
   if stat.S_ISLNK(v.st_mode):links+=1
   elif stat.S_ISREG(v.st_mode):count+=1;logical+=v.st_size;allocated+=v.st_blocks*512
 refs=[x for x in active if Path(x['path'])==p or p in Path(x['path']).parents]
 if not refs:shutil.rmtree(p)
 cleanup['targets'].append({'path':str(p),'regular_files':count,'logical_bytes':logical,'allocated_bytes':allocated,'external_symlinks_not_followed':links,'removed':not p.exists(),'active_references':refs})
cleanup['reclaimed_allocated_bytes']=sum(x['allocated_bytes'] for x in cleanup['targets'] if x['removed']);cleanup['disk_free_after']=shutil.disk_usage('/tmp').free;cleanup['observed_free_delta']=cleanup['disk_free_after']-cleanup['disk_free_before'];(E/'cleanup.json').write_text(json.dumps(cleanup,ensure_ascii=False,indent=2));print(json.dumps({'source850':'unchanged','baseline_other':base_verified,'preexisting':len(pre),'frozen_files':proof['frozen_files_preserved'],'removed_paths':sum(x['removed'] for x in cleanup['targets']),'reclaimed_allocated_bytes':cleanup['reclaimed_allocated_bytes'],'active_refs':active},ensure_ascii=False))

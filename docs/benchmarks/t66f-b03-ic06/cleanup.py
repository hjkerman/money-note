"""필요 oracle를 보관한 뒤 확인된 IC06 생성 scratch만 정리한다."""
import gzip,hashlib,json,os,shutil,tarfile
from pathlib import Path
R=Path(__file__).resolve().parents[3];O=Path(__file__).parent/'evidence';S=R/'work/t66f-b03-ic06'
def size(p):return sum(f.stat().st_size for f in p.rglob('*') if f.is_file() and not f.is_symlink())
migration=json.loads((O/'scratch-migration.json').read_text())
assert S.parent==R/'work' and S.is_symlink() and S.resolve()==Path(migration['physical_scratch'])
assert S.resolve()==Path('/tmp/money-note-t66f-b03-ic06-20261025')
assert (O/'freeze-reconstruction.json').exists() and (O/'frozen-smoke.json').exists()
assert json.loads((O/'frozen-smoke.json').read_text())['exit_code']==0
# Only these names were created by recorded IC06 invocations. Preserve any
# unknown path; do not infer ownership merely from residing under scratch.
names=['originals','pytest-matrix','pytest-matrix-final','pytest-focused','pytest-focused-final','pytest-historical','pytest-ir06','pre-edit-subject','pytest-complete','pytest-supported-complete','pytest-differential','candidate','pytest-smoke','http','output-root','format-initial.log','format-tests.log','reconstruction-verify']
for p in Path('/proc').glob('[0-9]*/cmdline'):
 if int(p.parent.name) in {os.getpid(),os.getppid()}:continue
 try:command=p.read_bytes().replace(b'\0',b' ')
 except (OSError,ProcessLookupError):continue
 assert str(S).encode() not in command and str(S.resolve()).encode() not in command, 'scratch 사용 프로세스가 남아 있다'
free_before=os.statvfs(R).f_bavail*os.statvfs(R).f_frsize
removed=[];kept=[]
if (O/'early-cache-cleanup.json').exists():
 early=json.loads((O/'early-cache-cleanup.json').read_text())
 removed.append(dict(path=early['path'],bytes=early['bytes']))
for name in ['originals','http','output-root']:
 p=S/name
 if p.exists():
  archive=O/(name+'-scratch.tar.gz')
  if not archive.exists():
   with tarfile.open(archive,'w:gz') as t:
    for f in sorted(p.rglob('*')):
     if f.is_file() and not f.is_symlink():t.add(f,arcname=str(f.relative_to(p)),recursive=False)
  with tarfile.open(archive) as t:
   for member in t.getmembers():assert hashlib.sha256(t.extractfile(member).read()).hexdigest()==hashlib.sha256((p/member.name).read_bytes()).hexdigest()
  kept.append(dict(path=str(archive.relative_to(R)),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
for name in names:
 p=S/name
 if p.is_symlink():raise AssertionError('unexpected root symlink '+str(p))
 if p.exists():
  n=size(p) if p.is_dir() else p.stat().st_size
  if p.is_dir():shutil.rmtree(p)
  else:p.unlink()
  removed.append(dict(path=str(p.relative_to(R)),bytes=n))
remaining=[str(p.relative_to(R)) for p in S.iterdir()]
d=dict(removed=removed,logical_bytes_removed=sum(e['bytes'] for e in removed),filesystem_free_delta_bytes=os.statvfs(R).f_bavail*os.statvfs(R).f_frsize-free_before,retained=kept,remaining_uncertain_paths_preserved=remaining,prior_artifacts_deleted=False,task_scratch=str(S),frozen_candidate_retained=True)
(O/'cleanup.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:d[k] for k in ['logical_bytes_removed','remaining_uncertain_paths_preserved','prior_artifacts_deleted']},ensure_ascii=False))

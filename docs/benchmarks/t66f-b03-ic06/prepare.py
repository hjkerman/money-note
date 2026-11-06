"""IC06 시작 상태와 역사 소스를 읽기 전용으로 대조한다."""
import gzip, hashlib, json, os, stat, subprocess, tarfile
from pathlib import Path
R=Path(__file__).resolve().parents[3]; O=Path(__file__).parent/'evidence'
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks',*a],cwd=R,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
def desc(p):
 b=p.read_bytes();return dict(path=str(p.relative_to(R)),mode=oct(stat.S_IMODE(p.stat().st_mode)),bytes=len(b),sha256=sha(b))
S=Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5')
m=json.loads((S/'source-manifest.json').read_text()); entries=m['entries']
assert sha(json.dumps(entries,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())==S.name
assert sha((S/'candidate.tar.gz').read_bytes())=='970c195b817d6ec8811b7a35bc1db547f65cdcdca84428fcffda126d8f7ec1f7'
diff=[]
with tarfile.open(S/'candidate.tar.gz') as t:
 for e in entries:
  b=t.extractfile('source/'+e['path']).read();assert sha(b)==e['sha256']
  if desc(R/e['path'])!=e:diff.append(dict(path=e['path'],frozen=e,current=desc(R/e['path'])))
files=set(git('ls-files','-z').decode().split('\0')+git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))-{''}
files={p for p in files if not p.startswith('docs/benchmarks/t66f-b03-ic06/')}
record=dict(head=git('rev-parse','HEAD').decode().strip(),branch=git('branch','--show-current').decode().strip(),staged=git('ls-files','--stage').decode(),staged_sha256=sha(git('ls-files','--stage')),index_sha256=sha((R/'.git/index').read_bytes()),status=git('status','--porcelain=v1','--untracked-files=all').decode(),tracked_diff_stat=git('diff','--stat').decode(),historical_candidate=str(S),historical_archive_sha256=sha((S/'candidate.tar.gz').read_bytes()),historical_files=len(entries),historical_bytes=sum(e['bytes'] for e in entries),current_differences_from_ic05=diff,preexisting=[desc(R/p) for p in sorted(files) if (R/p).is_file() and not (R/p).is_symlink()],scratch=str(R/'work/t66f-b03-ic06'),frozen_files=[dict(path=str(p.relative_to(S)),sha256=sha(p.read_bytes()),mode=oct(stat.S_IMODE(p.stat().st_mode))) for p in S.rglob('*') if p.is_file()],disk_free=os.statvfs(R).f_bavail*os.statvfs(R).f_frsize)
with gzip.open(O/'starting-state.json.gz','wt') as f:json.dump(record,f,ensure_ascii=False,indent=2)
with gzip.open(O/'baseline-counters.py.gz','wb') as f:f.write((R/'docs/benchmarks/t66f-b03/counters.py').read_bytes())
print(json.dumps({k:record[k] for k in ['head','branch','staged_sha256','index_sha256','historical_files','historical_bytes','current_differences_from_ic05','disk_free']}));print('preexisting',len(record['preexisting']))
for n in ['pep669-released-tool-confirmed','monitoring-instrument','monitoring-instrument_workers','monitoring-stage','flutter-affected-recovered','historical-python','frontend-build']:
 d=json.loads((R/'docs/benchmarks/t66f-b03-ir06/evidence'/f'{n}.json').read_text());print(n,json.dumps({k:d.get(k) for k in ['command','cwd','env','counts','exit_code']}))

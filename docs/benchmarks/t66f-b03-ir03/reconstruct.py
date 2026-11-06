import hashlib,json,os,subprocess,tarfile,io,stat
from pathlib import Path,PurePosixPath
root=Path('/tmp/money-note-ir03-20261023'); ev=root/'evidence';ev.mkdir()
live=Path('/home/hjkerman/codex/money-note'); frozen=Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8')
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(live),*a])
paths=git('ls-files','-z','--cached','--others','--exclude-standard').split(b'\0')
pre={}
for raw in paths:
 if not raw:continue
 p=live/os.fsdecode(raw)
 if p.is_file():pre[os.fsdecode(raw)]={'sha256':sha(p.read_bytes()),'mode':oct(stat.S_IMODE(p.stat().st_mode)),'bytes':p.stat().st_size}
index=live/'.git/index'
prestate={'head':git('rev-parse','HEAD').decode().strip(),'index_sha256':sha(index.read_bytes()),'status':git('status','--porcelain=v1','--untracked-files=all').decode(),'files':pre}
(ev/'original-state.json').write_text(json.dumps(prestate,ensure_ascii=False,indent=2)+'\n')
archive=frozen/'candidate.tar.gz'; raw=archive.read_bytes(); digest=sha(raw)
assert digest=='87b1e68975ce1c0682f7b7954d322734181aeb56dae1c123a29767132f266d01'
integrity=json.loads((frozen/'snapshot-integrity.json').read_text()); expected={m['path']:m for m in integrity['members']}
contents={}; modes={}
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tf:
 for m in tf.getmembers():
  p=PurePosixPath(m.name)
  assert m.isfile() and not p.is_absolute() and '..' not in p.parts and '\\' not in m.name
  assert m.name not in contents
  b=tf.extractfile(m).read(); contents[m.name]=b;modes[m.name]=m.mode & 0o777
  assert expected[m.name]==dict(path=m.name,bytes=len(b),mode=oct(m.mode & 0o777),sha256=sha(b))
assert set(contents)==set(expected)
manifest=json.loads(contents['metadata/ir01/candidate-source-manifest.json']); entries=manifest['entries']
payload=sha(json.dumps(entries,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
assert payload=='645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8'
assert len(entries)==819 and sum(e['worktree']['bytes'] for e in entries)==9085052
base=manifest['committed_base']; assert base=='ebcbd54d90eeee194a04b9eea6367f446ee2fd28'
assert git('cat-file','commit',base)==contents['metadata/base-commit.txt']
freeze=json.loads(contents['metadata/freeze.json']);assert freeze['tracked_deletions']==[] and freeze['staged']==''
tree=root/'candidate';tree.mkdir()
with tarfile.open(fileobj=io.BytesIO(git('archive','--format=tar',base))) as tf:tf.extractall(tree,filter='data')
for e in entries:
 path=e['path'];b=contents['source/'+path];v=e['worktree']
 assert sha(b)==v['sha256'] and len(b)==v['bytes'] and oct(modes['source/'+path])==v['mode']
 p=tree/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);p.chmod(int(v['mode'],8))
for e in entries:
 p=tree/e['path'];assert sha(p.read_bytes())==e['worktree']['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==e['worktree']['mode']
metadata=root/'metadata';metadata.mkdir()
for name,b in contents.items():
 if name.startswith('metadata/'):
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
locks=json.loads((tree/'docs/benchmarks/t66f-b03/source-lock-review.json').read_text());results={}
for path,v in locks['files'].items():
 b=(tree/path).read_bytes();assert sha(b)==v['reviewed_sha256']
 if v.get('historical_sha256'):
  s=b.decode()
  for repl in v['exact_replacements']:
   assert s.count(repl['reviewed'])==1;s=s.replace(repl['reviewed'],repl['historical'],1)
  assert sha(s.encode())==v['historical_sha256']
 results[path]='PASS'
report=dict(status='PASS',archive_sha256=digest,payload_sha256=payload,files=len(entries),payload_bytes=sum(e['worktree']['bytes'] for e in entries),archive_members=len(contents),baseline=base,tracked_deletions=freeze['tracked_deletions'],source_locks=results,workspace=str(tree),index_sha256=prestate['index_sha256'],frozen_files={p.name:sha(p.read_bytes()) for p in frozen.iterdir() if p.is_file()})
(ev/'integrity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['source_locks','frozen_files']}))

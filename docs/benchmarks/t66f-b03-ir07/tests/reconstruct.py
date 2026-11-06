"""IR07 독립 무결성 검사와 동결 source 복원. 제품 source를 읽어 복사하지 않는다."""
import hashlib, io, json, os, pathlib, stat, subprocess, tarfile
R=pathlib.Path('/home/hjkerman/codex/money-note')
S=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8')
W=pathlib.Path('/tmp/money-note-t66f-b03-ir07-20261025'); T=W/'tree'; E=R/'docs/benchmarks/t66f-b03-ir07'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*args],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
def safe(p):
 p=pathlib.PurePosixPath(p);assert not p.is_absolute() and '..' not in p.parts;return p
assert not T.exists()
m=json.loads((S/'source-manifest.json').read_bytes());f=json.loads((S/'freeze.json').read_bytes()); entries=m['entries']
archive=sha((S/'candidate.tar.gz').read_bytes());assert archive=='fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5'
payload=sha(json.dumps(entries,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode());assert payload==S.name==m['candidate_source_digest_sha256']==f['payload_sha256']
assert len(entries)==m['files']==899 and sum(x['bytes'] for x in entries)==m['source_bytes']==9801906
assert [e['path'] for e in entries]==sorted(set(e['path'] for e in entries))
for line in (S/'SHA256SUMS').read_text().splitlines():
 h,p=line.split();assert sha((S/safe(p)).read_bytes())==h
base='ebcbd54d90eeee194a04b9eea6367f446ee2fd28';assert git('rev-parse',base).decode().strip()==m['base_commit']==f['base_commit']==base
assert git('rev-parse',base+'^{tree}').decode().strip()==f['base_tree']
T.mkdir()
with tarfile.open(fileobj=io.BytesIO(git('archive',base))) as t:t.extractall(T,filter='data')
for p in f['tracked_deletions']:(T/safe(p)).unlink()
with tarfile.open(S/'candidate.tar.gz') as t:
 names=[x.name for x in t];assert len(names)==len(set(names))==len(entries)+len(f['context'])+2
 assert json.loads(t.extractfile('metadata/source-manifest.json').read())==m
 assert json.loads(t.extractfile('metadata/freeze.json').read())==f
 for prefix,records,root in [('source',entries,T),('context',f['context'],W/'context')]:
  for e in records:
   a=t.getmember(prefix+'/'+e['path']);b=t.extractfile(a).read()
   assert a.isfile() and a.mode==int(e['mode'],8) and len(b)==e['bytes'] and sha(b)==e['sha256']
   p=root/safe(e['path']);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);p.chmod(a.mode)
baseline=[];untouched=0;selected={e['path'] for e in entries}
for rec in git('ls-tree','-r','-z',base).split(b'\0'):
 if not rec:continue
 meta,p=rec.split(b'\t');mode,kind,oid=meta.decode().split();p=p.decode();assert kind=='blob'
 baseline.append(dict(path=p,git_mode=mode,git_blob=oid))
 if p in selected or p in f['tracked_deletions']:continue
 a=T/safe(p);assert a.read_bytes()==git('cat-file','blob',oid)
 assert bool(a.stat().st_mode&0o111)==(mode=='100755');untouched+=1
assert baseline==f['baseline_inventory']
for e in entries:
 a=T/e['path'];assert sha(a.read_bytes())==e['sha256'] and stat.S_IMODE(a.stat().st_mode)==int(e['mode'],8)
assert all(not (T/p).exists() for p in f['tracked_deletions'])
assert set(f['required_untracked'])<=selected
index=(R/'.git/index').read_bytes(); staged=git('ls-files','--stage')
assert staged==pathlib.Path('/tmp/ir07-index-before.txt').read_bytes()
(E/'starting-index.txt').write_bytes(staged)
record=dict(payload_sha256=payload,archive_sha256=archive,files=len(entries),bytes=sum(x['bytes'] for x in entries),base_commit=base,base_tree=f['base_tree'],baseline_files=len(baseline),untouched_baseline_files=untouched,tracked_deletions=f['tracked_deletions'],required_untracked=len(f['required_untracked']),all_archive_modes_and_hashes_verified=True,index_sha256=sha(index),staged_sha256=sha(staged),tree=str(T),context=str(W/'context'),live_worktree_source_copied=False)
(E/'candidate-integrity.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False))

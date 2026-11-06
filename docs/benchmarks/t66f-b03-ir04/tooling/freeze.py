from pathlib import Path
import os,stat,subprocess,json,hashlib,tarfile,io,tempfile
R=Path('/home/hjkerman/codex/money-note');A=Path('/tmp/money-note-ir04-20261024');E=A/'evidence';env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(R),*args],env=env)
m=json.loads((R/'docs/benchmarks/t66f-b03-ic02/corrected-candidate-manifest.json').read_text());entries=m['entries'];digest=sha(json.dumps(entries,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode());assert digest==m['candidate_source_digest_sha256']
assert git('rev-parse','HEAD').decode().strip()==m['base_commit'];staged=git('ls-files','--stage');assert not git('diff','--cached','--name-only');tree=git('ls-tree','-r','-z',m['base_commit']);tracked={}
for record in tree.split(b'\0'):
 if not record:continue
 meta,p=record.split(b'\t');mode,typ,oid=meta.split();tracked[p.decode()]={'mode':mode.decode(),'oid':oid.decode()}
assert all((R/p).exists() for p in tracked),'tracked deletion requires explicit resolution'
for x in entries:
 p=R/x['path'];assert p.is_file() and not p.is_symlink();b=p.read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==x['mode']
# Record all existing visible repository artifacts, plus ignored audit evidence, without build/cache trees.
paths=set(git('ls-files','-z').decode().split('\0'))|set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))
for base in [R/'docs/benchmarks',R/'docs']:
 paths.update(str(p.relative_to(R)) for p in base.rglob('*') if p.is_file() and not p.is_symlink() and not any(y in p.parts for y in ('__pycache__','node_modules','.dart_tool','build')))
preserved=[]
for name in sorted(paths-{''}):
 p=R/name
 if p.is_file() and not p.is_symlink():preserved.append({'path':name,'bytes':p.stat().st_size,'mode':oct(stat.S_IMODE(p.stat().st_mode)),'sha256':sha(p.read_bytes())})
(E/'preexisting-files.json').write_text(json.dumps(preserved,indent=2));(E/'staged-logical.txt').write_bytes(staged)
metadata={'base_commit':m['base_commit'],'source_digest':digest,'source_files':len(entries),'source_bytes':sum(x['bytes'] for x in entries),'tracked_deletions':[],'required_untracked':[x['path'] for x in entries if x['path'] not in tracked],'staged_entries_sha256':sha(staged),'staged_content_equals_head':True,'staged_tree':git('rev-parse',m['base_commit']+'^{tree}').decode().strip(),'index_file_sha256':sha((R/'.git/index').read_bytes()),'parent_ir02_archive_sha256':m['parent_ir02_archive_sha256'],'modes':'source manifest POSIX bits; base Git executable semantics preserved','immutability':'read-only permissions and digests; owner/root hardware WORM protection absent'}
root=Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03');dest=root/digest;assert not dest.exists(),'do not overwrite existing snapshot'
stage=Path(tempfile.mkdtemp(prefix='.ir04-',dir=root));archive=stage/'candidate.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=6) as t:
 def add(name,b,mode=0o444):
  h=tarfile.TarInfo(name);h.size=len(b);h.mode=mode;h.mtime=0;t.addfile(h,io.BytesIO(b))
 for x in entries:add('source/'+x['path'],(R/x['path']).read_bytes(),int(x['mode'],8))
 add('metadata/source-manifest.json',json.dumps(m,ensure_ascii=False,indent=2).encode())
 add('metadata/freeze.json',json.dumps(metadata,ensure_ascii=False,indent=2).encode())
archive_digest=sha(archive.read_bytes());(stage/'source-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));(stage/'freeze.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2));(stage/'SHA256SUMS').write_text(archive_digest+'  candidate.tar.gz\n')
(stage/'HANDOFF.md').write_text(f'''# IR04 교정 후보 독립 동결\n\n구현 소스를 수정하지 않고 IC02의 기존 bytes를 동결했다. 감사 결과는 별도 IR04 보고서에 기록한다.\n\n- 기준 commit: `{m['base_commit']}`\n- source payload: `{digest}`\n- source: {len(entries)}개 / {metadata['source_bytes']}B\n- archive SHA-256: `{archive_digest}`\n- tracked deletions: 0\n\n검증은 archive SHA-256 대조 후 source-manifest의 entries를 경로순 JSON UTF8 ensure_ascii=False, sort_keys=True, separators=(',',':')로 직렬화하여 SHA-256을 비교한다. 각 파일 bytes와 POSIX mode도 비교한다. 기준 commit의 git archive를 별도 임시 공간에 해제하고 source/를 overlay한다. 현재 live source는 참조하지 않는다. stage된 내용은 HEAD tree와 같고 required untracked는 freeze.json에 기록한다. Python/Flutter 의존성은 기존 도구를 사용하되 package root는 새 재구성본으로 지정한다. 원 IR02와 IR03 FAIL 증거는 보존한다.\n\nread-only 권한은 관리자/소유자의 변조를 물리적으로 막는 WORM이 아니다. 고정 digest가 동일성을 판정한다. 새 full N=100k cold, 비용 grid, R1, 배포는 허가되지 않았다.\n''')
# Verify archive independently before atomic rename.
with tarfile.open(archive) as t:
 for x in entries:
  h=t.getmember('source/'+x['path']);b=t.extractfile(h).read();assert sha(b)==x['sha256'] and h.mode==int(x['mode'],8)
for p in stage.iterdir():p.chmod(0o444)
stage.chmod(0o555);stage.rename(dest)
# Reconstruct only immutable Git object bytes and frozen archive source payload.
candidate=A/'candidate';candidate.mkdir()
p=subprocess.run(['git','-C',str(R),'archive',m['base_commit']],env=env,stdout=subprocess.PIPE,check=True)
with tarfile.open(fileobj=io.BytesIO(p.stdout)) as t:t.extractall(candidate,filter='data')
with tarfile.open(dest/'candidate.tar.gz') as t:
 for x in entries:
  h=t.getmember('source/'+x['path']);p=candidate/x['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(h).read());p.chmod(h.mode)
for x in entries:
 p=candidate/x['path'];assert sha(p.read_bytes())==x['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==x['mode']
selected={x['path'] for x in entries};base_verified=0
for name,x in tracked.items():
 if name in selected:continue
 p=candidate/name;native_blob=sha(b'blob '+str(p.stat().st_size).encode()+b'\0'+p.read_bytes()) # SHA-256 not git SHA-1; compare native Git object bytes below
 blob=git('cat-file','blob',x['oid']);assert p.read_bytes()==blob
 assert bool(p.stat().st_mode&0o111)==(x['mode']=='100755');base_verified+=1
record={'source_digest':digest,'archive_sha256':archive_digest,'destination':str(dest),'candidate':str(candidate),'source_files':len(entries),'source_bytes':metadata['source_bytes'],'baseline_other_files_verified':base_verified,'tracked_deletions':[],'required_untracked':len(metadata['required_untracked']),'preexisting_files_recorded':len(preserved),'PASS':True}
(E/'freeze-reconstruction.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))

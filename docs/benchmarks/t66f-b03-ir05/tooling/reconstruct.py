from pathlib import Path
import json,hashlib,os,stat,subprocess,tarfile,io
A=Path('/tmp/money-note-ir05-20261024');R=Path('/home/hjkerman/codex/money-note');E=A/'evidence';F=Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370');env=dict(os.environ,GIT_OPTIONAL_LOCKS='0');sha=lambda b:hashlib.sha256(b).hexdigest();git=lambda *a:subprocess.check_output(['git',*a],cwd=R,env=env)
archive=F/'candidate.tar.gz';digest=sha(archive.read_bytes());assert digest=='145f26c17d87276da054225d4149c30c76c74eb9505ef8f034b3237fabfe0a21';m=json.loads((F/'source-manifest.json').read_text());entries=m['entries'];assert entries==sorted(entries,key=lambda e:e['path']);payload=sha(json.dumps(entries,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode());assert payload==F.name and len(entries)==850 and sum(x['bytes'] for x in entries)==9247384
freeze=json.loads((F/'freeze.json').read_text());base=m['base_commit'];assert base=='ebcbd54d90eeee194a04b9eea6367f446ee2fd28' and git('rev-parse','HEAD').decode().strip()==base;assert git('rev-parse',base+'^{tree}').decode().strip()==freeze['base_tree'];assert freeze['tracked_deletions']==[]
# Preserve all pre-existing tracked/untracked source and audit artifacts, without cache traversal.
paths=set(git('ls-files','-z').decode().split('\0'))|set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))
paths.update(str(p.relative_to(R)) for p in (R/'docs').rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts)
pre=[]
for name in sorted(paths-{''}):
 p=R/name
 if p.is_file() and not p.is_symlink():pre.append({'path':name,'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size,'mode':oct(stat.S_IMODE(p.stat().st_mode))})
(E/'preexisting-files.json').write_text(json.dumps(pre,indent=2))
snapshot_ids={}
for folder in [F,F.parent/'645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8',F.parent/'27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3']:
 snapshot_ids[str(folder)]={'directory_mode':oct(stat.S_IMODE(folder.stat().st_mode)),'files':{p.name:{'sha256':sha(p.read_bytes()),'mode':oct(stat.S_IMODE(p.stat().st_mode)),'bytes':p.stat().st_size} for p in folder.iterdir() if p.is_file()}}
(E/'starting-frozen-identities.json').write_text(json.dumps(snapshot_ids,indent=2))
T=A/'candidate';T.mkdir();context=A/'context';context.mkdir()
with tarfile.open(fileobj=io.BytesIO(git('archive',base))) as tar:tar.extractall(T,filter='data')
with tarfile.open(archive) as tar:
 names=tar.getnames();assert len(names)==860 and len(names)==len(set(names)) and all(x.isfile() for x in tar)
 assert json.load(tar.extractfile('metadata/source-manifest.json'))==m;assert json.load(tar.extractfile('metadata/freeze.json'))==freeze
 expected={'source/'+x['path'] for x in entries}|{'context/'+x['path'] for x in freeze['context']}|{'metadata/source-manifest.json','metadata/freeze.json'};assert set(names)==expected
 for x in entries:
  assert not Path(x['path']).is_absolute() and '..' not in Path(x['path']).parts
  h=tar.getmember('source/'+x['path']);b=tar.extractfile(h).read();assert sha(b)==x['sha256'] and len(b)==x['bytes'] and h.mode==int(x['mode'],8)
  p=T/x['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);p.chmod(h.mode)
 for x in freeze['context']:
  h=tar.getmember('context/'+x['path']);b=tar.extractfile(h).read();assert sha(b)==x['sha256'] and len(b)==x['bytes'] and h.mode==0o444
  p=context/x['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);p.chmod(h.mode)
selected={x['path'] for x in entries};base_other=0;tracked=set()
for raw in git('ls-tree','-r','-z',base).split(b'\0'):
 if not raw:continue
 meta,name=raw.split(b'\t');mode,typ,oid=meta.split();name=name.decode();tracked.add(name)
 if name in selected:continue
 p=T/name;b=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid.decode();assert bool(p.stat().st_mode&0o111)==(mode==b'100755');base_other+=1
assert sorted(selected-tracked)==sorted(freeze['required_untracked']);assert set(freeze['tracked_modifications'])<=selected
for x in entries:
 p=T/x['path'];assert sha(p.read_bytes())==x['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==x['mode']
# Independent source-lock current and inverse check against pinned immutable Git bytes.
locks=json.loads((T/'docs/benchmarks/t66f-b03/source-lock-review.json').read_text());checks={}
for name,v in locks['files'].items():
 b=(T/name).read_bytes();assert sha(b)==v['reviewed_sha256'];check={'current_exact_sha':True}
 if v.get('historical_sha256'):
  s=b.decode()
  for rep in v['exact_replacements']:assert s.count(rep['reviewed'])==1;s=s.replace(rep['reviewed'],rep['historical'],1)
  assert s.encode()==git('show',locks['baseline']+':'+name) and sha(s.encode())==v['historical_sha256'];check['inverse_exact_git_bytes']=True
 checks[name]=check
(E/'source-lock-independent.json').write_text(json.dumps(checks,indent=2));(E/'candidate-source-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));(E/'freeze-metadata.json').write_text(json.dumps(freeze,ensure_ascii=False,indent=2))
result={'PASS':True,'archive_sha256':digest,'payload_sha256':payload,'source_files':850,'source_bytes':9247384,'archive_regular_members':860,'baseline':base,'baseline_other_files_verified':base_other,'tracked_deletions':[],'required_untracked':len(selected-tracked),'source_lock_files':len(checks),'workspace':str(T),'context':str(context),'preexisting_files_recorded':len(pre),'frozen':str(F)};(E/'reconstruction.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

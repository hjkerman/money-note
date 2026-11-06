"""B04 전용 복원·보존 기록. 기존 파일을 수정하지 않는다."""
import hashlib,io,json,os,pathlib,stat,subprocess,tarfile,time,sys
R=pathlib.Path('/home/hjkerman/codex/money-note'); E=R/'docs/benchmarks/t66f-b04'; W=pathlib.Path('/tmp/money-note-t66f-b04-20261026'); T=W/'tree'
S=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8')
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
def save(n,v):(E/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def safe(p):
 p=pathlib.PurePosixPath(p);assert not p.is_absolute() and '..' not in p.parts;return p
def inventory():
 paths=set(git('ls-files','-z').split(b'\0'))|set(git('ls-files','--others','--exclude-standard','-z').split(b'\0'))
 out={}
 for p in sorted(paths):
  if not p:continue
  p=p.decode()
  if p.startswith('docs/benchmarks/t66f-b04/') or p=='docs/t66f-b04-phase-b-measurement-feasibility.md':continue
  a=R/p
  if a.is_file():out[p]={'sha256':sha(a.read_bytes()),'mode':oct(stat.S_IMODE(a.stat().st_mode)),'bytes':a.stat().st_size}
 return out
m=json.loads((S/'source-manifest.json').read_bytes());f=json.loads((S/'freeze.json').read_bytes());entries=m['entries'];base=m['base_commit']
def verify():
 errors=[];selected={e['path'] for e in entries}
 for e in entries:
  p=T/e['path']
  if not p.is_file() or sha(p.read_bytes())!=e['sha256'] or stat.S_IMODE(p.stat().st_mode)!=int(e['mode'],8):errors.append(e['path'])
 for e in f['baseline_inventory']:
  if e['path'] in selected or e['path'] in f['tracked_deletions']:continue
  p=T/e['path']; blob=hashlib.sha1(b'blob '+str(p.stat().st_size).encode()+b'\0'+p.read_bytes()).hexdigest()
  if blob!=e['git_blob'] or bool(p.stat().st_mode&0o111)!=(e['git_mode']=='100755'):errors.append(e['path'])
 return errors
if sys.argv[1]=='prepare':
 assert not W.exists() and not (E/'preservation-before.json').exists();W.mkdir();(W/'disposable').mkdir();(W/'build').mkdir();(W/'raw').mkdir()
 save('preservation-before.json',{'head':git('rev-parse','HEAD').decode().strip(),'index_sha256':sha((R/'.git/index').read_bytes()),'index_entries_sha256':sha(git('ls-files','--stage','-z')),'status':git('status','--porcelain=v1').decode(),'files':inventory(),'time':time.time()})
 assert sha((S/'candidate.tar.gz').read_bytes())=='fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5'
 assert sha(json.dumps(entries,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())==S.name
 assert len(entries)==899 and sum(e['bytes'] for e in entries)==9801906
 for line in (S/'SHA256SUMS').read_text().splitlines():
  h,p=line.split();assert sha((S/safe(p)).read_bytes())==h
 T.mkdir()
 with tarfile.open(fileobj=io.BytesIO(git('archive',base))) as t:t.extractall(T,filter='data')
 for p in f['tracked_deletions']:(T/safe(p)).unlink()
 with tarfile.open(S/'candidate.tar.gz') as t:
  names=[a.name for a in t];assert len(names)==len(set(names))
  assert json.loads(t.extractfile('metadata/source-manifest.json').read())==m
  for e in entries:
   a=t.getmember('source/'+e['path']);b=t.extractfile(a).read();assert a.isfile() and sha(b)==e['sha256'] and len(b)==e['bytes'] and a.mode==int(e['mode'],8)
   p=T/safe(e['path']);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);p.chmod(a.mode)
 assert not verify()
 diffs=[e['path'] for e in entries if not (R/e['path']).is_file() or sha((R/e['path']).read_bytes())!=e['sha256']]
 (T/'.venv').symlink_to(R/'.venv',target_is_directory=True)
 (T/'frontend/node_modules').symlink_to(R/'frontend/node_modules',target_is_directory=True)
 save('source-identity.json',{'base_commit':base,'base_tree':f['base_tree'],'payload_sha256':S.name,'archive_sha256':sha((S/'candidate.tar.gz').read_bytes()),'selected_files':899,'selected_bytes':9801906,'baseline_files':len(f['baseline_inventory']),'reconstruction':str(T),'all_source_bytes_and_modes_verified':True,'live_payload_differences':diffs,'measurement_source':'frozen reconstruction','product_source_modified':False})
 print(json.dumps({'identity':'VERIFIED','live_differences':diffs,'scratch':str(W)}))
elif sys.argv[1]=='check':
 errors=verify();before=json.loads((E/'preservation-before.json').read_text());now=inventory();changed=[p for p,v in before['files'].items() if now.get(p)!=v]
 result={'source_mismatches':errors,'preexisting_changed':changed,'index_preserved':before['index_sha256']==sha((R/'.git/index').read_bytes()),'index_entries_preserved':before['index_entries_sha256']==sha(git('ls-files','--stage','-z')),'head':git('rev-parse','HEAD').decode().strip(),'time':time.time()}
 save('preservation-after.json',result);print(json.dumps(result));assert not errors and not changed and result['index_preserved'] and result['index_entries_preserved']

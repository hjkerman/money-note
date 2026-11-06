"""B05-A 출입 source와 기존 Git/증거의 bytes/mode를 보존한다."""
import hashlib,io,json,os,pathlib,stat,subprocess,sys,tarfile,time,shutil
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05a';W=pathlib.Path('/tmp/money-note-t66f-b05a-20261026');S=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8')
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*args],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def inventory():
 paths=set(git('ls-files','-z').split(b'\0'))|set(git('ls-files','--others','--exclude-standard','-z').split(b'\0'));d={}
 for b in sorted(paths):
  if not b:continue
  p=b.decode()
  if p.startswith('docs/benchmarks/t66f-b05a/') or p=='docs/t66f-b05a-engine-admission-real-flutter-ab.md':continue
  q=R/p
  if q.is_file():d[p]={'sha256':sha(q.read_bytes()),'mode':format(stat.S_IMODE(q.stat().st_mode),'04o'),'bytes':q.stat().st_size}
 return d

def restore(archive,T,expected):
 T.mkdir();body=git('archive','ebcbd54d90eeee194a04b9eea6367f446ee2fd28')
 with tarfile.open(fileobj=io.BytesIO(body)) as t:t.extractall(T,filter='data')
 with tarfile.open(archive) as t:
  m=json.loads(t.extractfile('metadata/source-manifest.json').read());entries=m['entries'];assert sha(json.dumps(entries,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())==expected
  names=t.getnames();assert len(names)==len(set(names))
  for a in entries:
   p=pathlib.PurePosixPath(a['path']);assert not p.is_absolute() and '..' not in p.parts
   member=t.getmember('source/'+a['path']);b=t.extractfile(member).read();assert sha(b)==a['sha256'] and len(b)==a['bytes'] and member.mode==int(a['mode'],8)
   q=T/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);q.chmod(member.mode)
 for a in entries:
  q=T/a['path'];assert sha(q.read_bytes())==a['sha256'] and stat.S_IMODE(q.stat().st_mode)==int(a['mode'],8)
 freeze=json.loads((S/'freeze.json').read_text());selected={a['path'] for a in entries}
 for a in freeze['baseline_inventory']:
  if a['path'] in selected:continue
  q=T/a['path'];data=q.read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==a['git_blob']
 (T/'.venv').symlink_to(R/'.venv',target_is_directory=True);(T/'frontend/node_modules').symlink_to(R/'frontend/node_modules',target_is_directory=True)
 return {'payload':expected,'files':len(entries),'verified':True,'path':str(T)}
if sys.argv[1]=='prepare':
 assert not W.exists() and not (E/'preservation-before.json').exists();W.mkdir()
 for p in ['raw','disposable','build']:(W/p).mkdir()
 save(E/'preservation-before.json',{'head':git('rev-parse','HEAD').decode().strip(),'branch':git('branch','--show-current').decode().strip(),'index_sha256':sha((R/'.git/index').read_bytes()),'staged_entries':git('ls-files','--stage','-z').decode().split('\0'),'staged_entries_sha256':sha(git('ls-files','--stage','-z')),'files':inventory(),'disk':shutil.disk_usage(W)._asdict(),'time_unix':time.time()})
 assert sha((S/'candidate.tar.gz').read_bytes())=='fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5'
 assert sha((R/'docs/benchmarks/t66f-b05/experimental-source.tar.gz').read_bytes())=='745246e7d4bf6f945987e8043fe097e47056554d39a6e2f24d419d77f9aafe1e'
 a=restore(S/'candidate.tar.gz',W/'baseline',S.name);b=restore(R/'docs/benchmarks/t66f-b05/experimental-source.tar.gz',W/'candidate','d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae')
 save(E/'source-reconstruction.json',{'A':a,'B05_before_admission':b,'no_frozen_archive_modified':True});print(json.dumps({'source_reconstruction':'PASS','A_files':a['files'],'B_files':b['files']}))
elif sys.argv[1]=='check':
 before=json.loads((E/'preservation-before.json').read_text());now=inventory();approved=json.loads((E/'authorized-change-inventory.json').read_text())['existing_paths'];changed=[p for p,a in before['files'].items() if now.get(p)!=a];unexpected=[p for p in changed if p not in approved]
 result={'head':git('rev-parse','HEAD').decode().strip(),'branch':git('branch','--show-current').decode().strip(),'changed_preexisting_paths':changed,'unexpected_changes':unexpected,'index_preserved':sha((R/'.git/index').read_bytes())==before['index_sha256'],'staged_entries_preserved':sha(git('ls-files','--stage','-z'))==before['staged_entries_sha256'],'historical_evidence_preserved':not any(p.startswith(('docs/benchmarks/t66f-b03','docs/benchmarks/t66f-b04','docs/benchmarks/t66f-b05/')) for p in changed),'time_unix':time.time()}
 save(E/'preservation-after.json',result);print(json.dumps(result));assert not unexpected and result['index_preserved'] and result['staged_entries_preserved'] and result['historical_evidence_preserved']

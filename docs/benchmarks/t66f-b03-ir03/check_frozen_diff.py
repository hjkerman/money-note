import hashlib,json,subprocess,tarfile,tempfile
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');ev=r/'evidence';repo=Path('/home/hjkerman/codex/money-note');archive=Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8/candidate.tar.gz');base='ebcbd54d90eeee194a04b9eea6367f446ee2fd28';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='87b1e68975ce1c0682f7b7954d322734181aeb56dae1c123a29767132f266d01'
manifest=json.loads((r/'metadata/ir01/candidate-source-manifest.json').read_text());results=[]
with tempfile.TemporaryDirectory(prefix='diff-check-',dir=r) as temp,tarfile.open(archive) as tar:
 before=Path(temp)/'before';after=Path(temp)/'after'
 for entry in manifest['entries']:
  path=entry['path'];body=tar.extractfile('source/'+path).read();old=subprocess.run(['git','--no-optional-locks','-C',str(repo),'show',base+':'+path],capture_output=True)
  prior=old.stdout if old.returncode==0 else b''
  if prior==body:continue
  before.write_bytes(prior);after.write_bytes(body)
  cmd=['git','diff','--no-index','--check',str(before),str(after)];p=subprocess.run(cmd,capture_output=True,text=True)
  results.append({'path':path,'invocation':cmd,'exit_code':p.returncode,'output':p.stdout+p.stderr})
result={'status':'PASS' if all(x['exit_code'] in (0,1) and not x['output'] for x in results) else 'FAIL','checked_changed_or_untracked_files':len(results),'results':results,'scratch_removed':True}
(ev/'diff-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'checked':len(results)}))

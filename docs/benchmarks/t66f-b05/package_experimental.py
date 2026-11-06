"""미자격 실험 source만 패키징·복원한다. IR07 또는 채택 승인을 의미하지 않는다."""
import gzip,hashlib,io,json,os,pathlib,stat,subprocess,tarfile
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05';W=pathlib.Path('/tmp/money-note-t66f-b05-20261026');S=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8')
m=json.loads((E/'candidate-source-manifest.json').read_text());entries=m['entries'];digest=hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();assert digest==m['canonical_payload_sha256']
archive=E/'experimental-source.tar.gz';assert not archive.exists()
def add(t,path,body,mode=0o644):
 a=tarfile.TarInfo(path);a.size=len(body);a.mode=mode;a.mtime=0;a.uid=a.gid=0;t.addfile(a,io.BytesIO(body))
with archive.open('xb') as dest,gzip.GzipFile(fileobj=dest,mode='wb',mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as t:
 for a in entries:
  p=R/a['path'];body=p.read_bytes();assert hashlib.sha256(body).hexdigest()==a['sha256'] and len(body)==a['bytes'];add(t,'source/'+a['path'],body,int(a['mode'],8))
 add(t,'metadata/source-manifest.json',(E/'candidate-source-manifest.json').read_bytes())
 add(t,'metadata/optimization.patch',(E/'optimization.patch').read_bytes())
record={'status':'EXPERIMENTAL — LOCALLY EFFECTIVE, SYSTEM BENEFIT UNPROVEN; NOT ADOPTED','payload_sha256':digest,'archive':str(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(entries),'source_bytes':sum(a['bytes'] for a in entries),'baseline_payload':S.name,'base_commit':m['base_commit'],'tracked_deletions':json.loads((S/'freeze.json').read_text())['tracked_deletions'],'independent_IR07_for_new_source':False,'full_backend_artifact_gate':'FAIL; 미승인 source-release artifact 차이','full_client_AB':'NOT RUN — exact engine admission 차단','external_audit_candidate_path':None}
record['full_backend_artifact_gate']='FAIL — 미승인 source-release artifact 차이'
T=W/'reconstructed';assert not T.exists();T.mkdir()
body=subprocess.check_output(['git','--no-optional-locks','-C',str(R),'archive',m['base_commit']],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
with tarfile.open(fileobj=io.BytesIO(body)) as t:t.extractall(T,filter='data')
for p in record['tracked_deletions']:(T/p).unlink()
with tarfile.open(archive) as t:
 for a in entries:
  path=pathlib.PurePosixPath(a['path']);assert not path.is_absolute() and '..' not in path.parts
  body=t.extractfile('source/'+a['path']).read();p=T/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body);p.chmod(int(a['mode'],8))
for a in entries:
 p=T/a['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'] and p.stat().st_size==a['bytes'] and stat.S_IMODE(p.stat().st_mode)==int(a['mode'],8)
record.update(reconstruction='PASS',reconstruction_files=len(entries),reconstruction_path=str(T),method='git archive base + recorded deletions + all payload files; SHA256/bytes/modes independently read back')
engine=subprocess.check_output([str(R/'.venv/bin/python'),'-c','from isolated_sync.artifacts import release_bundle; print(release_bundle()["artifacts"]["financial_engine"]["sha256"])'],env={**os.environ,'PYTHONPATH':str(T/'backend'),'PYTHONDONTWRITEBYTECODE':'1'},cwd=T,text=True).strip();assert engine==m['engine'];record['reconstructed_engine']=engine
(E/'experimental-freeze.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:record[k] for k in ['status','payload_sha256','archive_sha256','reconstruction']}))

"""입장·실제 경로 자격 통과 source만 별도 B05-A 후보로 동결·복원한다."""
import gzip,hashlib,io,json,os,pathlib,stat,subprocess,tarfile
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05a';W=pathlib.Path('/tmp/money-note-t66f-b05a-20261026');sha=lambda b:hashlib.sha256(b).hexdigest()
parent=json.loads((R/'docs/benchmarks/t66f-b05/candidate-source-manifest.json').read_text());entries={a['path']:dict(a) for a in parent['entries']}
changed=json.loads((E/'authorized-change-inventory.json').read_text())['existing_paths'];added=['backend/tests/test_engine_admission_b05a.py','mobile/test/segmented_engine_admission_b05a_test.dart','docs/benchmarks/t66f-b05a/source-lock-review.json','docs/benchmarks/t66f-b05a/mutation-witness.json']
for p in changed+added:
 f=R/p;entries[p]={'path':p,'mode':format(stat.S_IMODE(f.stat().st_mode),'04o'),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())}
entries=sorted(entries.values(),key=lambda a:a['path']);digest=sha(json.dumps(entries,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
assert digest not in [parent['canonical_payload_sha256'],'f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3']
m={'base_commit':'ebcbd54d90eeee194a04b9eea6367f446ee2fd28','baseline_payload':'8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8','parent_B05_payload':parent['canonical_payload_sha256'],'canonical_payload_sha256':digest,'entries':entries,'baseline_engine':'7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c','optimized_engine':'f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3','admission_changes':changed,'new_direct_test_inputs':added,'tracked_deletions':[],'release_artifact_sha256':sha((R/'docs/specimens/t66d3b-release-artifacts.json').read_bytes()),'source_lock_exception':'docs/benchmarks/t66f-b05a/source-lock-review.json','qualification':'PASS — ADMISSION AND REAL-PATH QUALIFICATION COMPLETE','performance':'OFF 개선 관찰; N5k ON 이득 미입증','independently_audited_IR07':False,'production_authorized':False,'evidence':{'regressions_sha256':sha((E/'regressions.json').read_bytes()),'run_manifest_sha256':sha((E/'run-manifest.json').read_bytes()),'runs':12,'N':[1000,5000]}}
(E/'candidate-source-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
F=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b05a')/digest;F.mkdir(parents=True,exist_ok=False)
(F/'source-manifest.json').write_bytes((E/'candidate-source-manifest.json').read_bytes());(F/'admission.patch').write_bytes((E/'admission.patch').read_bytes());(F/'optimization.patch').write_bytes((R/'docs/benchmarks/t66f-b05/optimization.patch').read_bytes())
def add(t,path,b,mode=0o644):
 a=tarfile.TarInfo(path);a.mode=mode;a.mtime=0;a.uid=a.gid=0;a.size=len(b);t.addfile(a,io.BytesIO(b))
archive=F/'candidate.tar.gz'
with archive.open('xb') as dest,gzip.GzipFile(fileobj=dest,mode='wb',mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as t:
 for a in entries:
  b=(R/a['path']).read_bytes();assert sha(b)==a['sha256'];add(t,'source/'+a['path'],b,int(a['mode'],8))
 add(t,'metadata/source-manifest.json',(E/'candidate-source-manifest.json').read_bytes())
T=W/'reconstructed';T.mkdir();body=subprocess.check_output(['git','--no-optional-locks','-C',str(R),'archive',m['base_commit']],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
with tarfile.open(fileobj=io.BytesIO(body)) as t:t.extractall(T,filter='data')
with tarfile.open(archive) as t:
 assert len(t.getnames())==len(set(t.getnames()))
 for a in entries:
  p=pathlib.PurePosixPath(a['path']);assert not p.is_absolute() and '..' not in p.parts;b=t.extractfile('source/'+a['path']).read();f=T/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b);f.chmod(int(a['mode'],8))
for a in entries:
 f=T/a['path'];assert sha(f.read_bytes())==a['sha256'] and f.stat().st_size==a['bytes'] and stat.S_IMODE(f.stat().st_mode)==int(a['mode'],8)
code='import json,pathlib;from isolated_sync.artifacts import release_bundle; b=release_bundle(); assert b==json.loads(pathlib.Path("docs/specimens/t66d3b-release-artifacts.json").read_text()); assert pathlib.Path("docs/specimens/t66d3b-release-artifacts.json").read_bytes()==pathlib.Path("mobile/assets/segmented/isolated-release-artifacts.json").read_bytes(); print(b["artifacts"]["financial_engine"]["sha256"])'
engine=subprocess.check_output([str(R/'.venv/bin/python'),'-c',code],cwd=T,env={**os.environ,'PYTHONPATH':str(T/'backend'),'PYTHONDONTWRITEBYTECODE':'1'},text=True).strip();assert engine==m['optimized_engine']
record={'snapshot':str(F),'archive':str(archive),'archive_sha256':sha(archive.read_bytes()),'payload_sha256':digest,'files':len(entries),'bytes':sum(a['bytes'] for a in entries),'reconstruction':'PASS','reconstructed_engine':engine,'reconstructed_artifact_consistency':'PASS','scope':'구현 측 입장·실제 HOST cold 자격; 새 IR07 독립 통과/production/50k/100k 주장 없음'}
(F/'freeze.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');(E/'freeze.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');(F/'SHA256SUMS').write_text('\n'.join(sha(p.read_bytes())+'  '+p.name for p in sorted(F.iterdir()) if p.is_file() and p.name!='SHA256SUMS')+'\n')
print(json.dumps(record,ensure_ascii=False))

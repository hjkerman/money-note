"""B08 + 승인된 exact admission만 source-only archive로 보존하고 재구성 검증한다."""
from pathlib import Path
import gzip,hashlib,io,json,os,stat,subprocess,tarfile
R=Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=Path('/tmp/money-note-t66f-b09-20261026');C=W/'candidate';sha=lambda b:hashlib.sha256(b).hexdigest()
reg=json.loads((E/'regressions.json').read_text());assert reg['backend']['exit_code']==0 and reg['flutter_affected']['exit_code']==0
runs=json.loads((E/'cold-ab-results.json').read_text());assert runs['N1000_complete']==4
parent=json.loads((E/'source-reconstruction.json').read_text())['variants']['B'];entries={v['path']:dict(v) for v in parent['source_manifest_entries']}
changed=['mobile/lib/src/segmented/protocol.dart','mobile/assets/segmented/isolated-release-artifacts.json','docs/specimens/t66d3b-release-artifacts.json','mobile/test/segmented_adapter_isolation_test.dart']
added=['mobile/test/segmented_engine_admission_b09_test.dart','docs/benchmarks/t66f-b09/B08-mutation-witness.json','mobile/test/segmented_engine_admission_b05a_test.dart','backend/tests/test_engine_admission_b09.py','docs/benchmarks/t66f-b05a/source-lock-review.json','docs/benchmarks/t66f-b05a/mutation-witness.json','docs/benchmarks/t66f-b09/source-lock-review.json']
for p in changed+added:
 f=C/p;entries[p]={'path':p,'mode':format(stat.S_IMODE(f.stat().st_mode),'04o'),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())}
entries=sorted(entries.values(),key=lambda a:a['path']);digest=sha(json.dumps(entries,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode());m={'canonical_payload_sha256':digest,'base_commit':'ebcbd54d90eeee194a04b9eea6367f446ee2fd28','B03_payload':'8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8','B08_payload':parent['payload'],'engine':parent['engine'],'entries':entries,'changed_admission_artifacts':changed,'direct_test_inputs':added,'tracked_deletions':[],'isolated_candidate_only':True,'live_product_modified':False,'B05_lookup_included':False,'B03_independent_IR07_applies':False,'release_artifact_sha256':sha((C/changed[1]).read_bytes()),'source_lock_exception':'docs/benchmarks/t66f-b09/source-lock-review.json','qualification':'PASS — ADMISSION AND REAL-PATH QUALIFICATION COMPLETE','production_authorized':False}
(E/'candidate-source-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
a=E/'integration-source.tar.gz';assert not a.exists()
def add(t,p,b,mode=0o644):
 h=tarfile.TarInfo(p);h.mode=mode;h.size=len(b);h.uid=h.gid=h.mtime=0;t.addfile(h,io.BytesIO(b))
with a.open('xb') as dest,gzip.GzipFile(fileobj=dest,filename='',mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as t:
 for v in entries:
  b=(C/v['path']).read_bytes();assert sha(b)==v['sha256'];add(t,'source/'+v['path'],b,int(v['mode'],8))
 add(t,'metadata/source-manifest.json',(E/'candidate-source-manifest.json').read_bytes())
T=W/'reconstructed';assert not T.exists();T.mkdir()
base=subprocess.check_output(['git','--no-optional-locks','-C',str(R),'archive',m['base_commit']],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
with tarfile.open(fileobj=io.BytesIO(base)) as t:t.extractall(T,filter='data')
with tarfile.open(a) as t:
 for v in entries:
  b=t.extractfile('source/'+v['path']).read();f=T/v['path'];f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b);f.chmod(int(v['mode'],8))
for v in entries:
 f=T/v['path'];assert sha(f.read_bytes())==v['sha256'] and stat.S_IMODE(f.stat().st_mode)==int(v['mode'],8)
code="import json,pathlib;from isolated_sync.artifacts import release_bundle;b=release_bundle();assert b==json.loads(pathlib.Path('docs/specimens/t66d3b-release-artifacts.json').read_text());assert pathlib.Path('mobile/assets/segmented/isolated-release-artifacts.json').read_bytes()==pathlib.Path('docs/specimens/t66d3b-release-artifacts.json').read_bytes();print(b['artifacts']['financial_engine']['sha256'])"
engine=subprocess.check_output([str(R/'.venv/bin/python'),'-c',code],cwd=T,env={**os.environ,'PYTHONPATH':str(T/'backend'),'PYTHONDONTWRITEBYTECODE':'1'},text=True).strip();assert engine==m['engine']
(E/'candidate-reconstruction.json').write_text(json.dumps({'status':'PASS','payload_sha256':digest,'engine':engine,'files':len(entries),'archive':str(a.relative_to(R)),'archive_sha256':sha(a.read_bytes()),'reconstructed_bytes_modes':'PASS','artifact_consistency':'PASS','independent_IR07':False},ensure_ascii=False,indent=2)+'\n');print(json.dumps({'payload':digest,'files':len(entries),'reconstruction':'PASS'}))

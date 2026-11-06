"""완료된 B09 소유 scratch만 보존 검증 뒤 제거한다."""
from pathlib import Path
import gzip,hashlib,json,os,shutil,subprocess,time
R=Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=Path('/tmp/money-note-t66f-b09-20261026');sha=lambda b:hashlib.sha256(b).hexdigest()
rec=json.loads((E/'candidate-reconstruction.json').read_text());assert rec['status']=='PASS';assert sha((R/rec['archive']).read_bytes())==rec['archive_sha256']
m=json.loads((E/'run-manifest.json').read_text());assert m['valid_completed']==4
for run in m['runs']:
 out=R/run['raw'];p=out.parent;v=json.loads((p/'independent-verification.json').read_text());assert v['status']=='PASS'
 for role in ['client','backend']:
  z=p/(role+'-consistent.sqlite.gz');assert sha(gzip.decompress(z.read_bytes()))==v['details'][role]['backup_sha256']
 assert json.loads((p/'completion.json').read_text())=={'status':'COMPLETED','server_exit':0}
assert not json.loads((E/'escalation-decision.json').read_text())['gate_open']
# Only running executables tied to this scratch matter; command lines of this check itself are excluded.
active=[]
for line in subprocess.check_output(['ps','-eo','pid,comm,args'],text=True).splitlines():
 parts=line.strip().split(None,2)
 if len(parts)<3:continue
 pid,comm,args=parts
 if str(W) in args and comm in ['flutter_tester','dart:frontend_s','dart:flutter_to','dart','uvicorn']:
  active.append(line)
 if str(W) in args and comm in ['python','python3'] and ('server.py' in args or 'backend_regression.py' in args):active.append(line)
assert not active,active
size=sum(p.stat().st_size for p in W.rglob('*')if p.is_file()and not p.is_symlink())
shutil.rmtree(W)
cache=E/'__pycache__';cache_bytes=0
if cache.exists():cache_bytes=sum(p.stat().st_size for p in cache.rglob('*')if p.is_file());shutil.rmtree(cache)
c=json.loads((E/'cleanup.json').read_text());c.update({'final_scratch_removed':True,'removed_root':str(W),'final_scratch_bytes':size,'analysis_pycache_removed_bytes':cache_bytes,'active_B09_processes':active,'matched_client_backend_backups':'8 gzip SQLite consistent backups verified against independent SHA','candidate_archive':'integration-source.tar.gz — reconstructed engine and artifacts PASS','retained':'raw timing/counters, independent verification, paired DB backups, source archive/manifest/diff, fixture gzip, regressions, tools','pending':None,'time_unix':time.time()});(E/'cleanup.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
m['scratch_root_removed']=True;m['scratch_paths_are_provenance_only']=True;m['authoritative_evidence_root']='docs/benchmarks/t66f-b09/';m['fixture_artifacts']=['docs/benchmarks/t66f-b09/fixture-n1000.json','docs/benchmarks/t66f-b09/template-n1000.sqlite.gz'];m['candidate_source_manifest']='docs/benchmarks/t66f-b09/candidate-source-manifest.json';m['candidate_archive']=rec['archive'];m['escalation_decision']='docs/benchmarks/t66f-b09/escalation-decision.json';m['planned_but_not_executed']=[{'N':5000,'on':True,'variant':v,'status':'NOT RUN — predeclared gate closed'}for v in ['A','B']];m['new_candidate_payload_sha']=rec['payload_sha256'];(E/'run-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'removed_scratch_bytes':size,'raw_backups_retained':8,'candidate_reconstruction':'PASS'}))

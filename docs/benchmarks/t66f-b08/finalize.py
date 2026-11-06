"""새 실행 없이 B08 증거·산술·신원·보고서 링크를 검증하고 봉인한다."""
import pathlib,json,hashlib,gzip,tarfile,io,re,math
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b08';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def get(n):return json.loads((E/n).read_text())
def save(n,d):(E/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
m=get('run-manifest.json');c=get('packet-comparison.json');pres=get('preservation-after.json');freeze=get('candidate-freeze.json');source=get('candidate-source-manifest.json');checks=[]
def check(n,v):assert v,n;checks.append(n)
check('30 ASGI +2 prep within32/120',m['actual_ASGI_requests']==30 and m['conservative_total_budget_count']==32 and m['budget']['wall_s']<120 and not m['budget']['watchdog_fired'])
check('all30 closed',m['valid_closed_ASGI']==30 and m['incomplete_ASGI']==m['error_ASGI']==0)
check('compilation and actual checks',c['A']['all_compilations']==46 and c['B']['all_compilations']==1 and c['A']['actual_DB_schema_inspections']==c['B']['actual_DB_schema_inspections']==46)
check('both orders local benefit',all(x['reduction_s']>0 for x in c['paired_blocks']))
check('preserved Git and existing files',not pres['preexisting_changed'] and not pres['new_visible_outside_B08'] and pres['index_preserved']and pres['staged_entries_preserved']and pres['preexisting_files_checked']==6199)
check('no scratch remaining',not pathlib.Path('/tmp/money-note-t66f-b08-20261026').exists())
check('actual SQL types/values',get('post-verification.json')['four_database_states_identical'])
check('unchanged guard rejects experimental engine',get('artifact-gate-analysis.json')['candidate']['differing_artifacts']==['financial_engine'] and not get('artifact-gate-analysis.json')['source_SHA_guards_relaxed'])
check('no real cold claim',c['actual_end_to_end_speedup']=='NOT VERIFIED')
archive=R/freeze['experimental_archive'];check('archive SHA',sha(archive)==freeze['archive_sha256'])
with tarfile.open(archive)as t:
 mm=json.load(t.extractfile('metadata/source-manifest.json'));check('archive manifest',mm==source)
 for a in mm['entries']:
  entry=t.getmember('source/'+a['path']);b=t.extractfile(entry).read();assert entry.isfile()and entry.mode==int(a['mode'],8)and hashlib.sha256(b).hexdigest()==a['sha256']and len(b)==a['bytes']
 check('900file payload digest',len(mm['entries'])==900 and hashlib.sha256(json.dumps(mm['entries'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==m['candidate_payload'])
for v in get('retained-databases.json'):
 p=R/v['path'];check(v['path'],sha(p)==v['compressed_sha256']and hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()==v['source_sha256'])
for v in ['A','B']:
 check('raw '+v,sha(E/c[v]['raw'])==c[v]['raw_sha256'])
check('30 per-request summaries',len(c['per_request'])==30 and len({r['global_sequence']for r in c['per_request']})==30)
for r in c['per_request']:check('request'+str(r['global_sequence']),r['status']=='COMPLETED'and r['collector_closed']and r['connections']==3)
m['tooling']={p.name:sha(p)for p in E.glob('*.py')};m['measurement_tooling']={name:m['tooling'][name]for name in ['probe.py','worker.py','coordinator.py','run.py']};m['tooling_digest_capture']='offline; measured driver files unchanged after execution';save('run-manifest.json',m)
inputs=['AGENTS.md','docs/development-artifact-hygiene.md','docs/project-state.md','docs/domain-model.md','docs/known-issues.md','docs/t66/c/t66c-delta-sync-protocol.md','docs/t66f-b03-ir07-independent-pep669-closure.md','docs/t66f-b06-cold-acquisition-critical-path-analysis.md','docs/t66f-b07-bounded-connect-schema-attribution.md','docs/benchmarks/t66f-b07/evidence-manifest.json','docs/benchmarks/t66f-b07/packet-timings.json','docs/benchmarks/t66f-b07/call-path-attribution.json','docs/benchmarks/t66f-b05a/fixture-n1000.json','docs/benchmarks/t66f-b05a/fixture-template-n1000.sqlite.gz','docs/benchmarks/t66f-b05a/raw/n5000-1-A-on/run.json','docs/benchmarks/t66f-b05b/raw/n5000-0-A-on/run.json']
archiveA=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/candidate.tar.gz');check('original frozen archive preserved',sha(archiveA)=='fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5')
save('evidence-manifest.json',{'task':'T6.6F-B08','classification':m['classification'],'source_payload':m['candidate_payload'],'engine':m['candidate_engine'],'inputs':[{'path':p,'sha256':sha(R/p)}for p in inputs],'original_archive':{'path':str(archiveA),'sha256':sha(archiveA)},'run_manifest':'run-manifest.json','source_diff':'source-diff-summary.json','safety':'cache-safety-verification.json','comparison':'packet-comparison.json','decision':'next-action-decision.json','artifact_guard_status':'unadmitted exact identity failure preserved; no full-backend PASS','candidate':'candidate-freeze.json','cleanup':'cleanup.json','Git_preservation':'preservation-after.json','source_archive':freeze['experimental_archive'],'output_SHA':'SHA256SUMS'})
report=R/'docs/t66f-b08-expected-revision-contract-reuse.md';body=report.read_text();missing=[p for p in re.findall(r'\]\(([^)]+)\)',body)if not p.startswith('http') and not(report.parent/p).exists()];check('report local links',not missing);check('Korean report without Japanese prose',not re.search(r'[\u3040-\u30ff]',body))
save('final-verification.json',{'status':'PASS','checks_count':len(checks),'checks':checks,'new_requests':0,'artifact_release_gate':'UNADMITTED — NOT RESOLVED IN B08','full_backend':'NOT RUN','footer_scope':'safe cache and local ASGI benefit; whole cold NOT VERIFIED'})
files=sorted([p for p in E.iterdir()if p.is_file()and p.name!='SHA256SUMS']+[report]);(E/'SHA256SUMS').write_text('\n'.join(sha(p)+'  '+p.relative_to(R).as_posix()for p in files)+'\n');print(json.dumps({'final_checks':len(checks),'sealed_outputs':len(files),'actual_ASGI':30,'conservative_count':32,'wall_s':m['budget']['wall_s'],'Git_preserved':True,'classification':m['classification'],'evidence_bytes':sum(p.stat().st_size for p in E.iterdir()if p.is_file())}))

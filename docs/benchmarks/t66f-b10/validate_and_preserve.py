"""B10 산출물 정합·기존 파일/Git/외부 archive 보존 검사. 수정은 B10 manifest뿐."""
from pathlib import Path
import hashlib,json,subprocess,re,datetime,stat
R=Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b10';REPORT='docs/t66f-b10-independent-phase-b-closure-adjudication.md'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(name):return json.loads((E/name).read_text())
def write(name,data):(E/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def git(*a):return subprocess.check_output(['git','--no-optional-locks',*a],cwd=R)
M=read('requirements-evidence-matrix.json');D=read('closure-decision.json');S=read('source-certification-boundaries.json');B=read('preservation-before.json');V=read('evidence-review.json')
required=['requirements-evidence-matrix.json','source-certification-boundaries.json','residual-risk-register.json','closure-decision.json','handoff-conditions.json']
for name in required:assert (E/name).is_file();read(name)
assert M['coverage']['total_rows']==len(M['rows'])==144
old=json.loads((R/'docs/benchmarks/t66f-phase-b-final/coverage.json').read_text());assert {x['id'] for x in old['rows']} <= {x['id'] for x in M['rows']}
fields=['requirement_id','authoritative_location','requirement','classification','applicable_scale_runtime_ko','evidence_reports','raw_manifests','source_identity','execution_environment','verified_result','residual_limitation_ko','closure_status','deferral_explicitly_authorized','blocks_phase_b_closure','blocks_T66F_closure','later_T69_can_address','required_reverification_after_change_ko']
for row in M['rows']:
 assert all(k in row for k in fields),row['id'];assert row['closure_status'] in ['PASS','FAIL','PARTIAL','UNVERIFIED','NOT APPLICABLE'];w=row['authoritative_location'];assert (R/w['path']).is_file();assert w['line']<=len((R/w['path']).read_text().splitlines())
 for p in row['evidence_reports']+row['raw_manifests']:assert (R/p).is_file(),(row['id'],p)
 if row['blocks_phase_b_closure']:assert not row['deferral_explicitly_authorized'] and row['closure_status'] in ['PARTIAL','UNVERIFIED']
assert not D['phase_B_waiver_or_deferral_authorized'] and D['selected_option']=='D' and D['formal_T66F_closure']=='NOT AUTHORIZED'
assert read('handoff-conditions.json')['execution']=='DEFERRED'
assert all(x['assigned_person_or_risk_acceptor'] is None for x in read('residual-risk-register.json')['risks'])
report=(R/REPORT).read_text();assert not re.search('[\u3040-\u30ff]',report);assert read('closure-decision.json')['minimum_next_action_ko'] in report
broken=[]
for target in re.findall(r'\]\(([^\)]+)\)',report):
 path=target.split('#')[0];path=re.sub(r':\d+$','',path)
 if path.startswith('https:'):continue
 p=Path(path) if path.startswith('/') else (R/'docs'/path)
 if not p.exists() and p not in [E/'preservation-after.json',E/'evidence-manifest.json']:broken.append(target)
assert not broken,broken
for item in V['input_files']:assert sha(R/item['path'])==item['sha256']
mismatches=[]
for f in B['files']:
 p=R/f['path']
 if not p.is_file():mismatches.append({'path':f['path'],'reason':'missing'});continue
 s=p.stat()
 if sha(p)!=f['sha256'] or s.st_mode!=f['mode'] or s.st_size!=f['size'] or s.st_mtime_ns!=f['mtime_ns'] or s.st_ino!=f['inode']:mismatches.append({'path':f['path'],'reason':'bytes/mode/size/mtime/inode'})
assert not mismatches,mismatches
assert git('rev-parse','HEAD').decode().strip()==B['head'];assert git('branch','--show-current').decode().strip()==B['branch']
assert sha(R/'.git/index')==B['index_sha256'];assert hashlib.sha256(git('ls-files','--stage','-z')).hexdigest()==B['index_entries_sha256'];assert git('ls-files','--stage').decode().splitlines()==B['index_entries']
assert hashlib.sha256(git('diff','--cached','--raw','-z')).hexdigest()==B['staged_diff_sha256']
external=[]
for s in S['frozen_sources']:
 p=Path(s['archive']);assert sha(p)==s['archive_sha256'];external.append({'path':str(p),'sha256':s['archive_sha256'],'preserved':True})
all_files=[x.decode() for x in git('ls-files','--cached','--others','--exclude-standard','-z').split(b'\0') if x]
start={x['path'] for x in B['files']};new=[p for p in all_files if p not in start]
assert all(p==REPORT or p.startswith('docs/benchmarks/t66f-b10/') for p in new),new
pres={'task':'T6.6F-B10','head':B['head'],'branch':B['branch'],'preexisting_files_checked':len(B['files']),'preexisting_bytes_checked':sum(f['size'] for f in B['files']),'mismatches':[],'compared_fields':['SHA-256','mode','bytes','mtime_ns','inode'],'Git_index_sha256':B['index_sha256'],'Git_index_entries_sha256':B['index_entries_sha256'],'index_entries':len(B['index_entries']),'staged_path_mode_blob_stage_preserved':True,'index_bytes_preserved':True,'staged_changes':0,'Git_index_modified_by_B10':False,'product_source_modified':False,'binding_protocol_modified':False,'engine_admission_modified':False,'release_artifacts_modified':False,'historical_evidence_preserved':True,'frozen_archives':external,'new_paths_scope_ko':'본 보고서와 docs/benchmarks/t66f-b10/만 추가','commit':None,'push':False,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
write('preservation-after.json',pres)
validation={'task':'T6.6F-B10','status':'PASS','required_JSON_outputs':required,'JSON_valid':True,'matrix_rows':144,'prior_matrix_rows_preserved':123,'required_fields_complete':True,'source_report_and_manifest_paths_valid':True,'report_links_valid':True,'Japanese_explanatory_prose':False,'single_disposition':'D — BLOCKED PENDING SPECIFIC REQUIRED EVIDENCE','phase_B_current_evidence':'INCONCLUSIVE','formal_closure':'NOT AUTHORIZED','waiver_self_authorized':False,'retained_raw_input_SHA_verified':len(V['input_files']),'preexisting_file_SHA_mode_size_mtime_inode_verified':len(B['files']),'historical_product_tests_rerun':0,'new_cold_or_benchmark':0,'new_frontend_build':0,'validation_is_not_product_gate_PASS':True}
write('validation.json',validation)
write('cleanup.json',{'task':'T6.6F-B10','large_disposable_artifacts':'NOT APPLICABLE','database_or_WAL_created':False,'build_or_candidate_tree_created':False,'scratch_created':False,'files_deleted':0,'reclaimed_bytes':0,'preexisting_files_deleted':0,'cache_deleted':0,'historical_evidence_preserved':True,'retained_ko':'한국어 보고서, 판정 JSON, 읽기 전용 재현 도구와 초기 도구 오류 원문, 보존/증거 manifest','next_cleanup_review_items':[]})
# 자기 참조 digest를 제외하고 최종 산출물과 규범/원 report를 해시 결합한다.
input_reports=['AGENTS.md','docs/project-state.md','docs/domain-model.md','docs/known-issues.md','docs/architecture.md','docs/development-artifact-hygiene.md',M['authority']['path'],'docs/t66/b/t66b-hot-cold-design.md','docs/runbook.md','docs/t66f-phase-b-independent-verification.md','docs/t66f-phase-b-continuation.md','docs/t66f-phase-b-final-evidence-closure.md']+list({p for r in M['rows'] for p in r['evidence_reports']})
input_reports+=['docs/t66f-b05-lookup-hot-body-decode-optimization.md','docs/t66f-b05a-engine-admission-real-flutter-ab.md','docs/t66f-b05b-independent-5k-on-ab-replication.md','docs/t66f-b06-cold-acquisition-critical-path-analysis.md','docs/t66f-b07-bounded-connect-schema-attribution.md','docs/t66f-b08-expected-revision-contract-reuse.md','docs/t66e3-independent-audit.md','docs/t66e3-implementation.md']
input_reports=sorted(set(input_reports));manifest={'task':'T6.6F-B10','self_excluded':True,'reproduction_order':['verify_sources.py','review_evidence.py','adjudicate.py','refine_decision.py','write_report.py','validate_and_preserve.py'],'reproduction_ko':'모두 기존 source/archive/JSON/JUnit을 읽는 감사 도구이며 제품 import·API·benchmark 없음. preservation-before는 최초 상태이므로 재생성하지 않음. manifest의 raw 입력 및 archive는 별도 JSON에서 해시 연결','authority_and_reports':[{'path':p,'sha256':sha(R/p),'bytes':(R/p).stat().st_size} for p in input_reports],'outputs':[]}
for p in sorted([R/REPORT]+[p for p in E.iterdir() if p.is_file() and p.name!='evidence-manifest.json']):manifest['outputs'].append({'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size})
write('evidence-manifest.json',manifest)
for target in re.findall(r'\]\(([^\)]+)\)',report):
 path=re.sub(r':\d+$','',target.split('#')[0]);p=Path(path) if path.startswith('/') else R/'docs'/path
 if not path.startswith('https:'):assert p.exists(),target
print(json.dumps({'validation':'PASS','original_files_preserved':len(B['files']),'index_preserved':True,'rows':144,'outputs':len(manifest['outputs']),'new_product_runs':0,'new_cold':0}))

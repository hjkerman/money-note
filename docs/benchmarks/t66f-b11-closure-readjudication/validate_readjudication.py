"""문서/JSON/해시만 읽고 이 재판정의 자기 산출물만 작성한다. 제품 import/실행 없음."""
from pathlib import Path
import collections, datetime, hashlib, json, os, stat, subprocess

ROOT = Path('/home/hjkerman/codex/money-note')
OUT = ROOT / 'docs/benchmarks/t66f-b11-closure-readjudication'
REPORT = ROOT / 'docs/t66f-b11-post-amendment-closure-readjudication.md'
C = 'docs/t66/c/t66c-delta-sync-protocol.md'
B = 'docs/t66/b/t66b-hot-cold-design.md'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
checks = []

def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(d): return json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def load(p): return json.loads((ROOT / p).read_text())
def save(name, data):
    p = OUT / name
    assert p.parent == OUT and p.suffix == '.json'
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
def identity(p):
    p = ROOT / p
    b = p.read_bytes()
    return {'path':str(p.relative_to(ROOT)), 'sha256':sha(b), 'bytes':len(b), 'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def check(id, passed, details=None):
    checks.append({'id':id, 'pass':bool(passed), 'details':details})
    if not passed: raise AssertionError(id)
def ref(path, section, first, last=None):
    lines = (ROOT / path).read_text().splitlines(keepends=True)
    excerpt = ''.join(lines[first-1:(last or first)])
    return {'path':path,'section':section,'line_start':first,'line_end':last or first,'excerpt_sha256':sha(excerpt.encode()),'exact_excerpt':excerpt}

authorization = load('docs/benchmarks/t66f-b11-application/authorization-decision.json')
application = load('docs/benchmarks/t66f-b11-application/application-record.json')
original = load('docs/benchmarks/t66f-b11/proposed-amendment-record.json')
supplement = load('docs/benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json')
active = load('docs/benchmarks/t66f-b11-application/active-transfer-obligation-register.json')
history = load('docs/benchmarks/t66f-b11/transfer-obligation-register.json')
consistency = load('docs/benchmarks/t66f-b11-application-consistency/decision.json')
consistency_manifest = load('docs/benchmarks/t66f-b11-application-consistency/evidence-manifest.json')
matrix = load('docs/benchmarks/t66f-b10/requirements-evidence-matrix.json')
b10decision = load('docs/benchmarks/t66f-b10/closure-decision.json')
start = load('docs/benchmarks/t66f-b11-closure-readjudication/input-snapshot.json')
ids = ['T35-100K-NC','T35-100K-CARD','T35-100K-CASH','T35-ROWS','T35-NET','T35-GZIP','I25-E3-100K','I25-BOOKKEEPING-100K']
statuses = ['UNVERIFIED']*3 + ['PARTIAL']*3 + ['UNVERIFIED']*2
check('owner.explicit_authorization', authorization['approved'] is True)
check('owner.no_execution_GO', authorization['execution_GO'] is False)
check('owner.supplement_quote', authorization['supplement_approval_quote'] == '좋아. 승인할게.')
check('owner.supplement_exact_scope', [x['id'] for x in supplement['changes']] == ['GOV01','GOV02','REF01'])
for field, path in [
    ('approved_original_report_sha256','docs/t66f-b11-normative-deferral-proposal.md'),
    ('approved_original_amendment_record_sha256','docs/benchmarks/t66f-b11/proposed-amendment-record.json'),
    ('approved_supplement_file_sha256','docs/benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json')]:
    check('owner.' + field, authorization[field] == identity(path)['sha256'])
for label, source in [('approval',authorization),('original',original),('active',active),('history',history)]:
    check(label + '.eight_ids_exact', source['transferred_obligation_ids'] == ids)
check('consistency.PASS', consistency['verdict'] == 'PASS' and consistency['material_finding_count'] == 0)
check('consistency.not_measurement_acceptance', consistency['obligations']['evidence_accepted_count'] == 0 and consistency['new_measurements'] == 0 and consistency['F_closure_readjudication_performed'] is False)
for item in consistency_manifest['files']:
    check('consistency.manifest.' + item['path'], identity(item['path']) == item)

applied_by_id = {x['id']:x for x in application['amendments']}
reconciled_by_id = {x['id']:x for x in supplement['reconciled_amendments']}
exact_results = []
reverse = {p:(ROOT/p).read_text() for p in [C,B]}
for item in original['amendments']:
    id = item['id']; expected = item['proposed_addition_ko']
    changes = [x for x in supplement['changes'] if x['amendment_id'] == id]
    for change in changes:
        check(id + '.replacement_once.' + change['id'], expected.count(change['old']) == 1)
        expected = expected.replace(change['old'], change['new'])
    applied = applied_by_id[id]; current = (ROOT/item['target_path']).read_text()
    check(id + '.approved_exact', expected == reconciled_by_id[id]['proposed_reconciled_addition_ko'] == applied['applied_addition_ko'])
    check(id + '.addition_hash', sha(expected.encode()) == applied['applied_addition_sha256'])
    check(id + '.current_once', current.count(expected) == 1)
    first = current[:current.index(expected)].count('\n')+1
    exact_results.append({'id':id,'path':item['target_path'],'current_start_line':first,'current_end_line':first+len(expected.splitlines())-1,'sha256':sha(expected.encode()),'approved_replacements':[x['id']for x in changes],'verdict':'PASS — DOCUMENT APPLICATION ONLY'})
    reverse[item['target_path']] = reverse[item['target_path']].replace('\n'+expected+'\n','',1)
for record in application['files']:
    p = record['path']; before = ROOT/'docs/benchmarks/t66f-b11-application'/(Path(p).stem+'.before.md')
    check(p + '.current_sha', identity(p)['sha256'] == record['after_sha256'])
    check(p + '.reverse_exact', reverse[p].encode() == before.read_bytes() and sha(before.read_bytes()) == record['before_sha256'])
check('application.zero_measurements', application['new_measurements'] == 0)
check('historical.B10_D_unchanged', b10decision['selected_option'] == 'D' and b10decision['formal_T66F_closure'] == 'NOT AUTHORIZED')

current_refs = [
    ref(C,'§4',49,70),ref(C,'§16/16-S',321,384),ref(C,'§17–18',386,415),
    ref(C,'§23–25',486,531),ref(C,'§26',533,541),ref(C,'§31',612,641),
    ref(C,'§32',643,649),ref(C,'§33',651,659),ref(C,'§34',661,679),
    ref(C,'§34-B11',681,693),ref(C,'§35',697,716),ref(C,'§35-T69',718,745),
    ref(C,'§36 I23/I24/I25',775,779),ref(C,'§38.7–12',834,843),
    ref(B,'§27',484,494),ref(B,'§29',513,534),
    ref('docs/architecture.md','서버 authority와 클라이언트 신뢰 경계',14,115)]
current_line_by_id = dict(zip(ids,[722,722,722,723,724,725,726,727]))
protected_fields = ['tracking_id_policy_ko','category','title_ko','source_requirement_ids','exact_normative_references','original_acceptance_criterion_ko','required_workload_scales','workloads','required_source_runtime_identity','required_fixture_identity','existing_evidence','missing_evidence_ko','historical_failure_or_blocker_ko','deadline_or_blocking_milestone','verification_method_ko','consequence_if_incomplete_ko','proposed_transfer','acceptance_semantics','B10_aliases','status']
origin_by_id = {x['id']:x for x in history['obligations']}
transfers = []
check('active.exact_eight_objects', [x['id']for x in active['obligations']] == ids)
check('active.future_contract_unchanged', active['future_acceptance_contract'] == history['future_acceptance_contract'])
for x, status in zip(active['obligations'],statuses):
    id = x['id']; old = origin_by_id[id]
    check(id + '.status_preserved', x['status'] == x['current_evidence_status'] == status == old['status'])
    check(id + '.mandatory_pending', x['transfer_status'] == 'TRANSFERRED — MANDATORY EVIDENCE PENDING')
    check(id + '.criterion_source_fixture_preserved', all(x[k] == old[k]for k in protected_fields))
    assignment = x['current_responsibility_assignment']
    check(id + '.explicit_independent_roles', assignment['role_assignment_complete'] is True and assignment['named_individual_required'] is False and assignment['execution_role'] == authorization['execution_responsibility'] and assignment['independent_acceptance_role'] == authorization['independent_acceptance_responsibility'])
    transfers.append({
        'id':id,'mandatory':True,'evidence_status':status,'disposition':'TRANSFERRED — MANDATORY EVIDENCE PENDING','independently_accepted':False,
        'current_normative_location':{'path':C,'section':'§35-T69','line':current_line_by_id[id]},
        'original_requirement':{k:x[k]for k in protected_fields if k not in ['status','acceptance_semantics']},
        'historical_line_reference_policy_ko':'original_requirement의 exact_normative_references는 적용 전 이력. 현재 위치는 별도 current_normative_location 및 현행 §35 716/I25 777/§38 834·839행에 연결한다.',
        'responsibility':assignment,'authorized_timing_transfer':x['existing_deferral_authorization'],
        'blocks_phase_B_quantitative_acceptance':True,'blocks_formal_F_exit':True,'blocks_final_T69_acceptance':True,'blocks_R1_activation_rollout_production':True,
        'administrative_disposition_effect_ko':'승인된 조건 아래 행정 종결 가능. 증거 완료나 criterion 면제는 아님.'})

open_rows = [x for x in matrix['rows'] if x['closure_status'] in ['PARTIAL','UNVERIFIED','FAIL']]
coverage_by_id = {x['B10_id']:x for x in history['B10_incomplete_row_coverage']}
check('B10.matrix_rows_144', len(matrix['rows']) == 144)
check('B10.open_rows_exact_37', len(open_rows) == len(coverage_by_id) == 37 and {x['id']for x in open_rows} == set(coverage_by_id))
row_dispositions = []
for row in open_rows:
    x = coverage_by_id[row['id']]
    check('B10.preserved_row.'+row['id'], row == x['B10_row_preserved'])
    mapped = x['canonical_obligation_ids']; moved = [id for id in mapped if id in ids]; remaining = [id for id in mapped if id not in ids]
    row_dispositions.append({'B10_id':row['id'],'requirement_id':row['requirement_id'],'historical_status':row['closure_status'],'current_evidence_status':row['closure_status'],'historical_row_canonical_sha256':sha(canonical(row)),'historical_matrix':'docs/benchmarks/t66f-b10/requirements-evidence-matrix.json','transferred_ids':moved,'nontransferred_ids':remaining,'current_disposition_ko':'원 evidence status 보존. 이관 부분은 미완료 mandatory T6.9-E, 비이관 하위 의무는 원 gate에 유지. 혼합 parent 전체를 수용하지 않음.','historical_phase_B_blocker':row['blocks_phase_b_closure'],'historical_formal_F_blocker':row['blocks_formal_t66f_closure'],'historical_rollout_blocker':row['blocks_rollout'],'historical_row_modified':False})
nontransferred = []
for x in history['obligations']:
    if x['id'] in ids: continue
    id = x['id']
    whole = id in ['F-ANDROID-DURABILITY','F-RECOVERY','F-MIGRATION','F-BACKUP','F-WHOLE-EXIT']
    nontransferred.append({'id':id,'historical_status':x['status'],'status':x['status'],'requirement_ids':x['source_requirement_ids'],'criterion_ko':x['original_acceptance_criterion_ko'],'missing_evidence_ko':x['missing_evidence_ko'],'consequence_ko':x['consequence_if_incomplete_ko'],'timing_transferred_by_B11':False,'blocks_formal_F':whole,'device_performance_is_post_T66':id=='E-DEVICE-PERFORMANCE','standalone_new_cold_MUST':False if id=='B-COLD-100K' else None})
check('nontransferred.nine_retained', len(nontransferred) == 9)

scopes = [
    {'id':'bounded_work','status':'COMPLETED — SCOPED WORK ONLY','evidence':['docs/t66f-b04-phase-b-measurement-feasibility.md','docs/benchmarks/t66f-b04/run-manifest.json','docs/benchmarks/t66f-b10/closure-decision.json'],'basis':[{'path':C,'section':'§34-B11','line':687}],'meaning_ko':'제한된 B04 및 종료된 B05/B08 캠페인·인계 작업의 완료; quantitative 또는 whole-F 완료 아님.'},
    {'id':'phase_B_administrative','status':'ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED','issued_by_this_readjudication':True,'evidence':['docs/benchmarks/t66f-b11-application/authorization-decision.json','docs/benchmarks/t66f-b11-application/active-transfer-obligation-register.json','docs/benchmarks/t66f-b11-application-consistency/decision.json'],'basis':[{'path':C,'section':'§34-B11','line':687}],'meaning_ko':'유효 승인·적용·정합성 검토 및 mandatory 인수 기록에 따른 조건부 행정 처분. 철회/조건 위반 시 효력 중단과 원 gate 복원.'},
    {'id':'phase_B_quantitative','status':'INCONCLUSIVE — NOT ACCEPTED','five_point_grid':'PARTIAL','N100k_normal_I25':'UNVERIFIED','E3_I25_large_N':'PARTIAL','basis':[{'path':C,'section':'§34-B11','line':687},{'path':C,'section':'§35-T69','line':745}],'meaning_ko':'8개 전부 미완료. 규범 적용 PASS를 정량 PASS로 바꾸지 않음.'},
    {'id':'T69_E_evidence','status':'MANDATORY EVIDENCE PENDING — NOT ACCEPTED','accepted_count':0,'entry_contract':'COLLECTION-ONLY','execution_GO':False,'basis':[{'path':C,'section':'§35-T69','line':720},{'path':B,'section':'§29','line':532}],'meaning_ko':'F exit 전 수집 subgate는 유효. source/runtime/fixture/계측/accepted provenance 독립 admission과 별도 실행 GO 미발급.'},
    {'id':'formal_T66F_closure','status':'NOT AUTHORIZED — BLOCKED PENDING SPECIFIC REQUIRED EVIDENCE','basis':[{'path':C,'section':'§34-B11','line':689},{'path':C,'section':'§38','line':843}],'meaning_ko':'8개 독립 수용과 비이관 §26/31–34·I23/I24·§38.8–11 및 나머지 통합 proof 전 종결 불가.'},
    {'id':'whole_F_proof','status':'INCOMPLETE / NOT VERIFIED AS A WHOLE','basis':[{'path':C,'section':'§26','line':539},{'path':C,'section':'§31','line':641},{'path':C,'section':'§32','line':645},{'path':C,'section':'§33','line':655},{'path':C,'section':'§38.8–11','line':835}],'meaning_ko':'R1 큰 restore/MW·native Frozen-B·legacy/migration/rollback·Android durability·30 backup/artifact/pin/GC·interop/full-resync/crash 별도 proof 미완료.'},
    {'id':'final_T69_acceptance','status':'BLOCKED','basis':[{'path':C,'section':'§34-B11','line':689},{'path':B,'section':'§29','line':532}],'meaning_ko':'8개 및 나머지 선행 gate 독립 수용 전 최종 완료 금지. 기존 confirmed-heavy/hot 대량/initial/full/restore/crash 범위도 유지.'},
    {'id':'R1_user_activation','status':'CLOSED','basis':[{'path':C,'section':'§34-B11','line':691}],'meaning_ko':'별도 R1 구현 stage와 사용자 활성화 구분. 본 판정이 구현/활성화 GO를 발급하지 않음.'},
    {'id':'real_device_performance','status':'POST-T6.6 — UNVERIFIED; EXECUTION DEFERRED','formal_F_independent_blocker':False,'basis':[{'path':C,'section':'§35','line':716},{'path':C,'section':'§38.12','line':839}],'meaning_ko':'기존 성능 단계 분리. Android durability의 whole-F/rollout proof는 별개. 정식 entry·실행 승인·새 ms/전력/thermal 합격선 없음.'},
    {'id':'segmented_rollout','status':'NOT AUTHORIZED','basis':[{'path':C,'section':'§34-B11','line':691}],'meaning_ko':'전체 proof·기기 gate·별도 명시 승인 필요.'},
    {'id':'production_deployment','status':'NOT AUTHORIZED','basis':[{'path':C,'section':'§34-B11','line':691}],'meaning_ko':'배포 요청/허가 없음. 증거 완료도 별도 운영 승인을 대신하지 않음.'},
    {'id':'T67_T68_implementation_cleanup','status':'NOT AUTHORIZED BY THIS AMENDMENT OR READJUDICATION','basis':[{'path':C,'section':'§34-B11','line':691}],'meaning_ko':'행정 종결을 자동 entry/PASS나 기존 full consumer/store·복구 경로 제거 근거로 쓸 수 없음.'}]

b04 = load('docs/benchmarks/t66f-b04/run-manifest.json')
p03 = load('docs/benchmarks/t66f-b04/historical-p03.json')
check('B04.bounded_original', b04['valid_controlled_completed_runs']==80 and b04['valid_controlled_pairs']==40 and b04['unexecuted_binding_points']==[100000] and b04['N100k_cold_attempts']==0)
check('P03.history_FAIL', p03['staged']==397146 and p03['required']==400532 and p03['elapsed_s']==2699.957907 and not p03['E3_completed'] and not p03['E4_completed'])
source = active['future_acceptance_contract']['source']
check('source.original_payload', source['payload_sha256']=='8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8')
check('source.original_engine', source['engine_sha256']=='7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c')
check('source.new_cold_not_required', active['future_acceptance_contract']['new_cold_required'] is False)
check('source.future_source_no_substitution', active['future_acceptance_contract']['later_source_can_discharge_original_without_B03_evidence'] is False)
check('source.no_new_cold_needed_if_legal_normal_evidence', active['future_acceptance_contract']['later_same_B03_normal_evidence_can_discharge_without_fresh_B03_cold'] is True)
check('report.exact_engine', source['engine_sha256'] in REPORT.read_text())

save('authority-and-normative-evidence.json', {'schema_version':1,'task':'T6.6F-B11 post-amendment closure readjudication','authority_decision':authorization,'authority_record_sha256':identity('docs/benchmarks/t66f-b11-application/authorization-decision.json')['sha256'],'authorization_effect_ko':'원 B03 8개 수집 시점·행정 상태만 변경. 기존 정량 criterion·실패·whole-F gate·실행 승인에는 확장하지 않음.','approval_timestamp_limit_ko':'사용자 메시지 시각은 제공되지 않아 null. 기록 시각과 실제 발언 시각을 동일시하지 않음.','application_record_is_immutable_history':True,'latest_consistency_decision':'docs/benchmarks/t66f-b11-application-consistency/decision.json','consistency_PASS_scope_ko':consistency['verdict_scope_ko'],'prior_document_checks':110,'exact_current_application':exact_results,'current_normative_excerpts':current_refs,'new_execution_approval':False})
save('scope-dispositions.json', {'schema_version':1,'reviewed_at_utc':NOW,'scopes':scopes,'failure_revocation_policy':{'missing_failed_impossible_ko':'실행 책임 역할이 차단 상태와 증거를 기록해 소유자에게 보고. 자동 연장/수용/요구 소거/waiver 없음.','actual_full_N_violation_ko':'해당 구현 거부·별도 수정/재자격 사유. 결측은 PARTIAL/UNVERIFIED.','revocation_or_condition_breach_ko':'행정 종결 효력 중단, 원 종결 gate 복원. 유일/역사 증거 보존.','blocking_milestone_ko':'formal F exit 재심사 및 최종 T6.9 acceptance 중 먼저 도래하는 시점 이전 8개 독립 수용; R1 활성화/rollout/production도 계속 차단.','execution_GO_is_separate':True}})
save('evidence-dispositions.json', {'schema_version':1,'transferred_count':8,'accepted_count':0,'status_counts':dict(collections.Counter(statuses)),'transferred_obligations':transfers,'B10_matrix_total':144,'B10_open_row_count':37,'B10_open_row_dispositions':row_dispositions,'nontransferred_obligations':nontransferred,'historical_results_rewritten':False,'historical_B10_Option_D_rewritten':False,'tracking_id_policy_ko':'T35 등은 B11 추적 ID, S/P/COST/GRID 등은 감사 별칭. 원 규범 I1–I25를 대체하지 않음.','evidence_acceptance_criteria_weakened':False})
save('historical-source-boundaries.json', {'schema_version':1,'original_B03_source':source,'original_B03_correctness':'CLOSED — IR07, ORIGINAL SOURCE AND SUPPORTED RUNTIME','new_material_refutation':False,'closed_correctness_reopened':False,'new_measurements':0,'B02_100k_functional':{'status':'CLOSED — ORIGINAL SOURCE FUNCTIONAL ONLY','base_commit':'1cabf319f0ac2c2069e804b47cb527b55e3374db','objects':400532,'bytes':261543083,'substitute_for_B03_ON_cost':False},'historical_P03':{'status':'FAIL — HISTORICAL IC01/P02 SOURCE','staged':p03['staged'],'required':p03['required'],'elapsed_s':p03['elapsed_s'],'observations_expired':3,'E3_completed':False,'E4_completed':False,'final_IR07_payload_applies':False,'cause_instrumentation_alone_proven':False,'evidence':['docs/benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json','docs/benchmarks/t66f-b03-ic01-p03/evidence/ic01-p02-source-review.json','docs/benchmarks/t66f-b04/historical-p03.json']},'original_B03_100k_instrumented_full_cold':{'status':'UNVERIFIED','retry':'NO-GO','standalone_MUST_gate':False,'new_attempts':0},'B04':{'status':'PASS — BOUNDED','normal_ON_completed':36,'valid_controlled_completed_runs':80,'pairs':40,'scales':[1000,5000,10000,50000],'five_point_grid':'PARTIAL','full_counters_zero_claim_scope':'OBSERVED NORMAL ON CELLS ONLY','new_100k_cold_runs':0},'accepted_100k_baseline':{'availability_certified_by_this_review':False,'whole_filesystem_absence_claimed':False,'independent_admission_required':True,'requirements_ko':'원 source/runtime/fixture·계측 지원, complete objects/11 tables/global index/receipts·NS/principal/Versions/Target/same-connection provenance/generation 및 실제 accepted 경로 확인. 확보 불가면 blocked 기록.'},'actual_acceptance_path_ko':'authenticated D3→HTTP/TLS→Flutter E2/E1→원 AppState E3 accepted publication/readback→E4. OFF/backend-only/ASGI/prepare-discard/실패·취소 대체 금지.','authority_fence_ko':'마지막 guard 바로 다음 동기 COMMIT. 중간 await/hook/callback 금지.','I25_counters':active['future_acceptance_contract']['I25_counters'],'limits':active['future_acceptance_contract']['limits'],'fixture_and_comparison_contract':active['future_acceptance_contract']['fixture'],'future_source_policy_ko':active['future_acceptance_contract']['source_change_policy_ko'],'future_source_additional_qualification_ko':'별도 채택 승인·exact release/admission·변경 영향 계측 oracle/구조/provenance/authority/durability/legacy proof 및 그 source 전체 다섯 점. 호환 proof 없는 validator/schema 변경은 full revalidation.','B05':'EXPERIMENTAL — NOT ADOPTED','B08':'EXPERIMENTAL — NOT ADOPTED','B09_admission_real_path':'PASS — SCOPED','B09_performance':'MIXED','no_new_H_D_sample_latency_or_NAND_obligations':True,'server_financial_authority_preserved':True,'new_mobile_canonical_financial_engine_required':False,'host_is_not_device_proof':True})

decision = {'schema_version':1,'task':'T6.6F-B11 POST-AMENDMENT INDEPENDENT CLOSURE READJUDICATION','reviewer_task':'/root/b11_post_amendment_closure_readjudication','reviewed_at_utc':NOW,'change_id':'T66F-B11-TRANSFER-01','supplement_id':supplement['supplement_id'],'independence':{'verdict':'SATISFIED','original_amendment_authorship':False,'application_participation':False,'immediately_prior_consistency_review_participation':False,'B01_B09_implementation_or_measurement_performed_in_this_session':False,'delegated':False,'basis_ko':'제공된 이력상 별도 새 세션. 외부 인적 신원/UI reasoning 설정 인증은 아님.'},'adjudication_completed':True,'material_findings':[],'material_finding_count':0,'existing_open_gate_is_new_material_finding':False,'administrative_disposition_issued':True,'bounded_work_completion':'COMPLETED — SCOPED WORK ONLY','phase_B_administrative_closure':'ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED','phase_B_quantitative_evidence_status':'INCONCLUSIVE','phase_B_quantitative_acceptance':'NOT ACCEPTED','five_point_grid':'PARTIAL','N100k_normal_I25':'UNVERIFIED','E3_I25_large_N':'PARTIAL','eight_obligations':'TRANSFERRED — MANDATORY EVIDENCE PENDING','transferred_obligation_ids':ids,'evidence_accepted_count':0,'T69_E_entry_contract':'COLLECTION-ONLY; INDEPENDENT ADMISSION AND SEPARATE EXECUTION GO REQUIRED','T69_E_execution_GO':False,'formal_T66F_closure':'NOT AUTHORIZED','formal_closure_disposition':'BLOCKED PENDING SPECIFIC REQUIRED EVIDENCE','formal_remaining_obligations':['8개 원 B03 mandatory 증거 독립 수용','C §26 Android durability / §38.8','C §31 recovery/MW / I23 / §38.10','C §33 legacy/migration/rollback / §38.9','C §32 backup/artifact/pin/GC / I24 / §38.11','C §34의 R1·interop/full-resync/crash 및 나머지 whole-F proof/독립 재심사'],'whole_F_proof':'INCOMPLETE / NOT VERIFIED AS A WHOLE','final_T69_acceptance':'BLOCKED','R1_activation':'CLOSED','real_device_preparation':'PRIOR READ-ONLY DOCUMENT HANDOFF SCOPE RETAINED; NO FORMAL ENTRY PASS','real_device_execution':'DEFERRED / NOT AUTHORIZED HERE','segmented_rollout':'NOT AUTHORIZED','production_deployment':'NOT AUTHORIZED','T67_T68_cleanup':'NOT AUTHORIZED BY THIS AMENDMENT OR READJUDICATION','historical_B10_Option_D':'PRESERVED — NOT RETROACTIVELY MODIFIED','original_B03_IR07':'CLOSED — ORIGINAL SOURCE / SUPPORTED RUNTIME','historical_P03':'FAIL — HISTORICAL SOURCE; FINAL IR07 COLD SUCCESS UNVERIFIED','instrumented_100k_cold_is_standalone_MUST':False,'baseline_availability_certified':False,'B05':'EXPERIMENTAL — NOT ADOPTED','B08':'EXPERIMENTAL — NOT ADOPTED','new_measurements':0,'new_full_cold_runs':0,'npm_backend_Flutter_benchmark_API_device_emulator_executions':0,'product_imports':0,'new_waivers_or_execution_activation_deployment_approvals_issued':0,'binding_or_existing_files_modified':False,'git_index_modified':False,'failure_revocation_policy':'scope-dispositions.json#failure_revocation_policy','evidence':['authority-and-normative-evidence.json','scope-dispositions.json','evidence-dispositions.json','historical-source-boundaries.json','preservation-verification.json','validation-summary.json','evidence-manifest.json'],'scope_limit_ko':'현행 규범 아래 종결 상태에 대한 독립 문서 판정. 규범 적용 PASS를 정량/runtime PASS로 해석하지 않음.','next_step_ko':'새 행정 상태와 정량/whole-F 차단을 함께 기록. T6.9-E 수집은 별도 계획/독립 source·fixture·runtime·계측·accepted provenance admission과 명시 GO 후만 실행. 8개와 비이관 선행 proof 수용 뒤 formal F 새 재심사; 활성화/배포는 별도 명시 승인.','report':str(REPORT.relative_to(ROOT))}
save('closure-decision.json', decision)

for item in start['files']:
    check('preserve.' + item['path'], identity(item['path']) == item)
env = dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(*args): return subprocess.run(['git',*args],cwd=ROOT,env=env,check=True,capture_output=True).stdout
check('preserve.HEAD', git('rev-parse','HEAD').decode().strip() == start['head'])
check('preserve.index_bytes', identity('.git/index') == start['index_file'])
check('preserve.index_entries', sha(git('ls-files','--stage','-z')) == start['index_entries_sha256'])
check('preserve.staged', git('diff','--cached','--name-only').decode() == start['staged_name_only'] == '')
check('preserve.application_index_bytes', identity('.git/index')['sha256'] == load('docs/benchmarks/t66f-b11-application/starting-state.json')['index_file_sha256'])
save('preservation-verification.json', {'schema_version':1,'verdict':'PASS — DOCUMENT/JSON/HASH SCOPE','input_files_checked':len(start['files']),'changed':[],'missing':[],'mode_changes':[],'HEAD':start['head'],'index_entry_count':start['index_entry_count'],'index_file_sha256':start['index_file']['sha256'],'index_bytes_and_entries_preserved':True,'application_baseline_index_bytes_preserved':True,'staged_changes':0,'reviewer_modified_existing_files':False,'scope_ko':'65개 입력 문서/JSON·HEAD/index 해시의 이번 전후 대조. 제품·ignored runtime·production·외부 archive 전체 새 감사 아님. 기존 정합성 검토의 6461개 보존 결과는 그 검토의 원 증거로만 인용.','artifact_hygiene':{'large_disposable_artifacts':'NOT APPLICABLE','deleted_bytes':0,'deleted_preexisting_files':0},'bwrap_incident_ko':'초기 loopback RTM_NEWADDR 오류 뒤 승인 검토된 read/자기 산출물 쓰기 경로만 사용. 자동 승인 거절 없음.'})
for p in OUT.glob('*.json'):
    json.loads(p.read_text())
check('self.JSON_parse', True)
check('self.report_exists', REPORT.is_file())
check('self.report_key_dispositions', all(t in REPORT.read_text()for t in [decision['phase_B_administrative_closure'],'INCONCLUSIVE','NOT AUTHORIZED','SATISFIED','NO-GO']))
save('validation-summary.json', {'schema_version':1,'verdict':'PASS — DOCUMENT/JSON/HASH CHECKS ONLY','check_count':len(checks),'failed_checks':0,'checks':checks,'new_runtime_measurements':0,'new_product_tests':0,'product_imports':0,'note_ko':'대조 개수는 금융·runtime·성능 PASS 개수가 아니다. 의미/종결 판단은 보고서와 scope disposition의 독립 판단이다.'})
artifacts = [REPORT] + sorted(p for p in OUT.iterdir()if p.is_file() and p.name != 'evidence-manifest.json')
save('evidence-manifest.json', {'schema_version':1,'task':'T6.6F-B11 POST-AMENDMENT CLOSURE READJUDICATION','self_hash_excluded':True,'files':[identity(str(p.relative_to(ROOT)))for p in artifacts],'material_finding_count':0,'new_measurements':0,'existing_files_modified_by_reviewer':False,'artifact_hygiene':'NOT APPLICABLE — no large disposable artifacts; deleted 0B'})
for item in load('docs/benchmarks/t66f-b11-closure-readjudication/evidence-manifest.json')['files']:
    assert identity(item['path']) == item
print(json.dumps({'document_checks':len(checks),'failures':0,'preserved_input_documents':len(start['files']),'manifest_artifacts':len(artifacts),'administrative':decision['phase_B_administrative_closure'],'quantitative':decision['phase_B_quantitative_evidence_status'],'formal_F':decision['formal_T66F_closure'],'material_findings':0,'new_measurements':0},ensure_ascii=False))

"""승인된 B11 AM01–05와 보충안 세 치환만 적용. Git·제품·계측 변경 없음."""
import pathlib,json,hashlib,datetime,os
R=pathlib.Path('/home/hjkerman/codex/money-note');D=R/'docs/benchmarks/t66f-b11-application'
def j(p):return json.loads((R/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
original=j('docs/benchmarks/t66f-b11/proposed-amendment-record.json')
supplement=j('docs/benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json')
base=j('docs/benchmarks/t66f-b11-application/starting-state.json')
assert not (D/'application-record.json').exists(),'이미 적용 기록이 있음'
report=(R/'docs/t66f-b11-normative-deferral-proposal.md').read_text()
expected={x['path']:x for x in base['preexisting_files']}
finals={a['id']:a for a in supplement['reconciled_amendments']}
prepared={}; entries=[]
for a in original['amendments']:
 p=R/a['target_path'];before=p.read_bytes();assert sha(before)==expected[a['target_path']]['sha256']
 ref=a['current_reference'];lines=before.decode().splitlines(keepends=True)
 context='\n'.join(before.decode().splitlines()[ref['line_start']-1:ref['line_end']])
 assert context==a['current_normative_statement'] and a['proposed_addition_ko'] in report
 f=finals[a['id']];text=f['proposed_reconciled_addition_ko']
 assert sha(text.encode())==f['proposed_reconciled_addition_sha256']
 computed=a['proposed_addition_ko']
 for c in supplement['changes']:
  if c['amendment_id']==a['id']:
   assert computed.count(c['old'])==1;computed=computed.replace(c['old'],c['new'])
 assert text==computed
 assert text not in before.decode(),'기존 추가문 중복 삽입 금지'
 prepared.setdefault(a['target_path'],{'before':before,'lines':lines,'insertions':[]})['insertions'].append((ref['line_end'],'\n'+text+'\n',a['id']))
 entries.append({'id':a['id'],'target_path':a['target_path'],'target_section':a['target_section'],'original_context_reference':ref,'original_context_sha256':sha(context.encode()),'original_B11_addition_sha256':sha(a['proposed_addition_ko'].encode()),'applied_addition_sha256':sha(text.encode()),'applied_addition_ko':text,'approved_supplement_changes':[c['id'] for c in supplement['changes'] if c['amendment_id']==a['id']]})
for path,x in prepared.items():
 lines=list(x['lines'])
 for end,text,i in sorted(x['insertions'],reverse=True):lines.insert(end,text)
 after=''.join(lines).encode();stripped=after.decode()
 for _,text,i in x['insertions']:
  assert stripped.count(text)==1;stripped=stripped.replace(text,'',1)
 assert stripped.encode()==x['before'],'승인 추가문 외 변경 금지'
 x['after']=after
# 모든 사전 대조가 끝난 뒤 두 파일을 atomic replace한다.
for path,x in prepared.items():
 p=R/path;tmp=D/(p.name+'.approved.tmp');tmp.write_bytes(x['after']);tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p)
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
authorization={'schema_version':1,'change_id':original['change_id'],'option':'OPTION 3 — TRANSFER WITH SAFEGUARDS','approval_authority':'Money Note 프로젝트 소유자 — 사용자 명시 승인','primary_authorization_quote':'I am explicitly approving **T66F-B11-TRANSFER-01, Option 3 — Transfer With Safeguards**, in my capacity as the Money Note project owner, subject to the authority and responsibility requirements recorded in B11.','primary_authorization_evidence':'docs/benchmarks/t66f-b11-approval-preflight/authorization-received.json','supplement_id':supplement['supplement_id'],'supplement_approval_quote':'좋아. 승인할게.','supplement_approval_context':'바로 앞 응답에서 GOV01·GOV02 역할 책임과 REF01 줄 참조 교정을 묶은 제한 보충안에 대해 별도 승인을 요청했고 사용자가 승인했다.','approved':True,'recorded_at_utc':now,'user_message_timestamp':None,'timestamp_policy_ko':'사용자 메시지 시각은 제공되지 않아 발명하지 않음. recorded_at은 적용 증거 기록 시각.','approved_original_report_sha256':sha((R/'docs/t66f-b11-normative-deferral-proposal.md').read_bytes()),'approved_original_amendment_record_sha256':sha((R/'docs/benchmarks/t66f-b11/proposed-amendment-record.json').read_bytes()),'approved_supplement_file_sha256':sha((R/'docs/benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json').read_bytes()),'execution_responsibility':'T6.9 구현·측정 워크스트림','independent_acceptance_responsibility':'해당 구현·측정에 관여하지 않은 별도 T6.9 감사 세션','final_approval_authority':'프로젝트 소유자','named_individual_invented':False,'transferred_obligation_ids':original['transferred_obligation_ids'],'blocking_milestones':['formal T6.6F exit 재심사 및 최종 T6.9 acceptance 전 8개 독립 수용','R1 활성화·segmented rollout·production 전 이관 증거·whole-F proof·기기 gate·별도 승인 충족'],'reporting_responsibility_ko':'T6.9 실행 책임 역할은 누락·실패·수행 불능 및 차단 상태·증거를 소유자에게 보고하며 자동 연장/waiver/수용을 발급하지 않는다.','risk_acceptance_scope_ko':'수집 시점의 조건부 이관과 행정 상태 분리만 수락. 실제 full-N 위반·소스 대체·실패/미계측 PASS는 불허.','execution_GO':False,'R1_activation':'CLOSED','production_deployment':'NOT AUTHORIZED'}
save('authorization-decision.json',authorization)
record={'schema_version':1,'task':'T6.6F-B11 승인 개정 적용','change_id':original['change_id'],'supplement_id':supplement['supplement_id'],'status':'APPLIED — INDEPENDENT REVIEWS PENDING','applied_at_utc':now,'head':base['head'],'amendments':entries,'files':[{'path':path,'before_sha256':sha(x['before']),'after_sha256':sha(x['after']),'before_lines':len(x['before'].decode().splitlines()),'after_lines':len(x['after'].decode().splitlines()),'inserted_lines':len(x['after'].decode().splitlines())-len(x['before'].decode().splitlines()),'original_bytes_recoverable_by_removing_exact_additions':True} for path,x in prepared.items()],'historical_B11_unchanged':True,'product_source_modified':False,'instrumentation_modified':False,'engine_admission_modified':False,'release_artifacts_modified':False,'git_index_modified':False,'acceptance_criteria_weakened':False,'new_measurements':0,'post_application_review_status':'PENDING','closure_readjudication_status':'PENDING'}
save('application-record.json',record)
register=j('docs/benchmarks/t66f-b11/transfer-obligation-register.json')
active=[]
for x in register['obligations']:
 if x['id'] in original['transferred_obligation_ids']:
  y=dict(x);y.update({'transfer_status':'TRANSFERRED — MANDATORY EVIDENCE PENDING','current_evidence_status':x['status'],'execution_owner_role':authorization['execution_responsibility'],'independent_acceptance_role':authorization['independent_acceptance_responsibility'],'final_approval_authority':'프로젝트 소유자','assigned_person':None,'existing_deferral_authorization':{'change_id':original['change_id'],'supplement_id':supplement['supplement_id'],'record':'docs/benchmarks/t66f-b11-application/authorization-decision.json','normative_clauses':['T6.6C §34-B11','T6.6C §35-T69','T6.6C §36 I25 추가문','T6.6C §38.7–12 추가문','T6.6B §29 추가문']},'historical_origin':'docs/benchmarks/t66f-b11/transfer-obligation-register.json','historical_evidence_result_rewritten':False});active.append(y)
save('active-transfer-obligation-register.json',{'schema_version':1,'change_id':original['change_id'],'supplement_id':supplement['supplement_id'],'status':'BINDING TRANSFER — EVIDENCE NOT ACCEPTED','transferred_obligation_ids':original['transferred_obligation_ids'],'obligations':active,'future_acceptance_contract':register['future_acceptance_contract'],'B10_open_row_coverage_origin':'docs/benchmarks/t66f-b11/transfer-obligation-register.json','nontransferred_whole_F_dependencies_origin':'docs/benchmarks/t66f-b11/transfer-obligation-register.json','historical_register_unchanged':True,'owner_policy_ko':'이 승인으로 지정된 실재 역할이 현재 책임. 역사 원 등록부의 개인 null/기명 승인 전 조건은 소급 편집하지 않음.','T69_detailed_contract_location':'docs/t66/c/t66c-delta-sync-protocol.md §35-T69','T69_entry':'COLLECTION-ONLY; source/runtime/fixture/instrumentation/accepted baseline 독립 사전심사와 별도 실행 GO 전 실행 불가','formal_F_closure':'NOT AUTHORIZED','quantitative_phase_B':'INCONCLUSIVE','R1_activation':'CLOSED','production_deployment':'NOT AUTHORIZED'})
print(json.dumps({'status':record['status'],'applied_amendments':len(entries),'changed_governing_files':len(prepared),'obligations_transferred':len(active),'new_measurements':0},ensure_ascii=False))

"""승인 사전 대조·제한 수정안 작성만 수행. 구속 문서는 쓰지 않는다."""
import pathlib,json,hashlib,datetime,subprocess,os,re
R=pathlib.Path('/home/hjkerman/codex/money-note');D=R/'docs/benchmarks/t66f-b11-approval-preflight'
REPORT=R/'docs/t66f-b11-approval-preflight.md'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(n,j):(D/n).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
old=json.loads((R/'docs/benchmarks/t66f-b11/proposed-amendment-record.json').read_text())
original_report=(R/'docs/t66f-b11-normative-deferral-proposal.md').read_text()
checks=[]
for a in old['amendments']:
 ref=a['current_reference'];cur='\n'.join((R/a['target_path']).read_text().splitlines()[ref['line_start']-1:ref['line_end']])
 checks.append({'id':a['id'],'target_path':a['target_path'],'current_context_matches':cur==a['current_normative_statement'],'proposal_matches_B11_report':a['proposed_addition_ko'] in original_report,'current_file_sha256':digest(R/a['target_path']),'proposed_addition_sha256':hashlib.sha256(a['proposed_addition_ko'].encode()).hexdigest()})
assert all(x['current_context_matches'] and x['proposal_matches_B11_report'] for x in checks)
manifest=json.loads((R/'docs/benchmarks/t66f-b11/evidence-manifest.json').read_text())
assert all(digest(R/x['path'])==x['sha256'] for x in manifest['files'])
save('redline-check.json',{'task':'T6.6F-B11 승인 사전 검토','change_id':old['change_id'],'B11_report_sha256':digest(R/'docs/t66f-b11-normative-deferral-proposal.md'),'B11_proposed_amendment_record_sha256':digest(R/'docs/benchmarks/t66f-b11/proposed-amendment-record.json'),'all_5_contexts_exact_match':True,'all_5_proposals_exactly_present_in_B11_report':True,'B11_manifest_members_preserved':len(manifest['files']),'checks':checks,'material_conflict_ko':'AM01/AM05와 보고서 §10은 기명 책임자/owner를 요구하지만 새 소유자 승인은 워크스트림·독립 감사 세션에 책임을 배정하며 개인 이름을 발명하지 말라고 지시한다. 이를 충족했다고 선언하려면 원 초안의 책임 형식을 바꾸는 결정이 필요하다.','editorial_issue_ko':'AM04의 796행은 현재 원문 줄번호다. 앞 절 추가 후 다른 위치를 가리키므로 논리 절/원칙 참조로 바꾸어야 한다.','binding_files_modified':False,'application_performed':False})
received={'task':'T6.6F-B11 승인 사전 검토','change_id':old['change_id'],'decision':'PROJECT OWNER APPROVAL RECEIVED','recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authority':'Project owner — 이번 사용자의 명시 승인','authority_status':'ESTABLISHED BY EXPLICIT USER AUTHORIZATION','execution_responsibility':'T6.9 implementation/measurement workstream','independent_acceptance_responsibility':'별도의 implementation/measurement 비참여 T6.9 audit session','final_approval_authority':'프로젝트 소유자','invented_named_individual':False,'transferred_obligation_ids':old['transferred_obligation_ids'],'conditions_ko':['8개 의무의 구속력·개별 추적 유지','미래 source로 historical B03 결측 소급 대체 금지','구현·측정 비참여 독립 수용','이관 증거·whole-F·device·별도 승인 전 R1 activation/production 금지','B05/B08 실험·미채택 유지','역사 증거·동결 후보·source locks·staged content 보존','행정 종결과 cost PASS/whole-F 완료 구분'],'original_earlier_blocking_milestones_retained_ko':'formal F exit 재심사 및 최종 T6.9 acceptance 전 이관 증거 수용 의무도 제거하지 않는다.','approval_scope':'8개 의무의 보호 조건부 규범 이관 준비·적용; 결측 증거 인증·production activation 승인 아님','pre_application_stop_instruction_ko':'exact B11 redline 대조에서 중대한 모호성/충돌/더 넓은 변경이 있으면 적용 전에 중단하고 별도 명시 결정을 요청한다.','application_status':'HELD — RESPONSIBILITY WORDING CONFLICT','supplement_approval_status':'NOT REQUESTED IN EARLIER OWNER APPROVAL; PENDING SEPARATE DECISION','original_approval_revoked':False}
save('authorization-received.json',received)
changes=[
 {'id':'GOV01','amendment_id':'AM01','B11_report_line':135,'old':'T6.9-E 기명 책임자와 독립 증거 수용자','new':'T6.9-E 실행 책임 역할과 독립 증거 수용 역할(실행: T6.9 구현·측정 워크스트림, 수용: 해당 구현·측정에 관여하지 않은 별도 T6.9 감사 세션, 최종 승인: 프로젝트 소유자)','classification':'책임 지정 형식의 제한 규범 수정 — 별도 명시 결정 필요','reason':'소유자가 지정한 실재 역할에 책임을 결합하고 개인 이름을 발명하지 않는다.'},
 {'id':'GOV02','amendment_id':'AM05','B11_report_line':262,'old':'기명 owner/독립 수용자','new':'§34-B11 승인 기록에 명시된 실행 책임 역할/구현·측정 비참여 독립 수용 역할','classification':'동일 책임 요건의 상위 도식 문구 정합 수정 — 별도 명시 결정 필요','reason':'AM01의 역할 지정과 AM05의 수집 entry 조건을 일치시킨다.'},
 {'id':'REF01','amendment_id':'AM04','B11_report_line':229,'old':'796행의 원칙대로','new':'이 절의 구현 증명 실패 시 구현/rollout 차단 및 별도 명세 변경 감사 원칙에 따라','classification':'줄 이동에 대한 편집상 참조 교정','reason':'원 규범 §38의 기존 원칙을 그대로 식별하며 새 줄번호를 추정하지 않는다.'}
]
proposed=[]
for a in old['amendments']:
 t=a['proposed_addition_ko']
 for c in changes:
  if c['amendment_id']==a['id']:
   assert t.count(c['old'])==1
   t=t.replace(c['old'],c['new'])
 proposed.append({'id':a['id'],'target_path':a['target_path'],'target_section':a['target_section'],'original_B11_addition_sha256':hashlib.sha256(a['proposed_addition_ko'].encode()).hexdigest(),'proposed_reconciled_addition_sha256':hashlib.sha256(t.encode()).hexdigest(),'changed':t!=a['proposed_addition_ko'],'proposed_reconciled_addition_ko':t,'applied':False})
proposal={'task':'T6.6F-B11 승인 사전 검토','supplement_id':'T66F-B11-TRANSFER-01-RESPONSIBILITY-SUPPLEMENT','parent_change_id':old['change_id'],'status':'DRAFT ONLY — NOT APPLIED','changes':changes,'reconciled_amendments':proposed,'unchanged_amendments':['AM02','AM03'],'transferred_obligation_ids':old['transferred_obligation_ids'],'acceptance_criteria_weakened':False,'source_constraints_changed':False,'release_gates_changed':False,'named_individual_required_after_supplement':False,'responsibility_roles_are_explicit_and_non_optional':True,'historical_B11_report_to_be_preserved':True,'if_approved_ko':'원 B11 이력은 그대로 보존하고, 이 보충 결정과 원 소유자 승인을 함께 새 적용 기록에 결합하여 AM01–05를 한 번에 적용한다. 이후 별도 독립 정합성 검토와 별도 F 종결 재판정을 순서대로 수행한다.','if_rejected_ko':'기명 책임 조건의 해소 방법을 소유자가 달리 지정하기 전 적용 보류. 원 승인 자체를 철회한 것으로 해석하지 않는다.'}
save('responsibility-supplement-proposal.json',proposal)
parts=['''# T6.6F-B11 — 소유자 승인 접수와 적용 전 책임 지정 충돌 검토

**소유자 승인은 접수했다. 구속 개정은 적용하지 않았다.** 원 B11 개정문의 책임 지정 형식과 이번 승인의 역할 지정 사이에 충돌이 있어, 사용자가 지정한 ‘충돌 시 적용 전에 중단하고 별도 명시 결정 요청’ 절차를 따른다. 승인 권한이 없어서 중단한 것은 아니다. 현재 승인 권한자는 이번에 명시적으로 승인한 프로젝트 소유자다.

## 1. 승인 범위와 현재 상태

변경 ID는 `T66F-B11-TRANSFER-01`, 선택은 Option 3이다. 실행 책임은 T6.9 구현·측정 워크스트림, 독립 수용 책임은 해당 구현·측정에 관여하지 않은 별도 T6.9 감사 세션이며 최종 승인 권한은 프로젝트 소유자다. 개인 이름을 만들지 않았다. 승인 원칙과 8개 이관 의무는 [authorization-received.json](benchmarks/t66f-b11-approval-preflight/authorization-received.json)에 기록했다.

이전 B11의 미승인/미적용 표시는 그 당시의 역사 기록으로 보존한다. 이번 소유자 승인 기록으로 덮어쓰지 않았다. 현재 상태는 ‘승인 접수, 책임 형식 충돌 해소 전 적용 보류’다. 행정 종결은 아직 발급하지 않았다.

## 2. exact redline 대조

B11 JSON의 AM01–05 모두 현재 대상 문서의 원문과 정확히 일치한다. 5개 추가문 모두 B11 보고서에 정확히 들어 있으며 B11 산출물 manifest의 12개 항목도 보존돼 있다. 원문 drift가 원인은 아니다. [redline-check.json](benchmarks/t66f-b11-approval-preflight/redline-check.json)에 원문·제안 해시와 검사를 기록했다.

''']
parts.append(f"- B11 보고서 SHA-256: `{digest(R/'docs/t66f-b11-normative-deferral-proposal.md')}`\n- B11 제안 JSON SHA-256: `{digest(R/'docs/benchmarks/t66f-b11/proposed-amendment-record.json')}`\n\n")
parts.append('''## 3. 중대한 충돌과 제한 수정안

[B11 AM01](/home/hjkerman/codex/money-note/docs/t66f-b11-normative-deferral-proposal.md:135)은 ‘기명 책임자’를, [AM05](/home/hjkerman/codex/money-note/docs/t66f-b11-normative-deferral-proposal.md:262)는 ‘기명 owner’를 요구한다. [B11 §10](/home/hjkerman/codex/money-note/docs/t66f-b11-normative-deferral-proposal.md:289)도 개인 이름이 비어 있는 승인 필드를 채우도록 설명했다. 이번 승인은 역할을 분명히 지정했지만 이름을 발명하지 말라고 지시했다. 역할 배정만으로 원 기명 조건이 충족됐다고 임의 판정하지 않는다.

권고 보충 결정 ID는 `T66F-B11-TRANSFER-01-RESPONSIBILITY-SUPPLEMENT`다. 다음 세 부분만 고치는 안이며 아직 적용하지 않았다.

''')
for c in changes:
 parts.append(f"### {c['id']} — {c['amendment_id']}\n\n사유: {c['reason']} 분류: {c['classification']}.\n\n기존 제안:\n\n> {c['old']}\n\n교체 제안:\n\n> {c['new']}\n\n")
parts.append('''AM04의 ‘796행’은 앞 절에 추가문을 삽입하면 더는 해당 원칙을 가리키지 않는 편집상 문제다. REF01은 기존 §38 원칙의 의미를 바꾸지 않고 논리 절 참조로 바꾼다. AM02·AM03 및 그 밖의 모든 문장은 그대로다. 정확한 최종 추가문 5개와 전후 SHA는 [responsibility-supplement-proposal.json](benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json)에 있다.

## 4. 그대로 유지할 의무와 차단

이관 목록은 T35-100K-NC, T35-100K-CARD, T35-100K-CASH, T35-ROWS, T35-NET, T35-GZIP, I25-E3-100K, I25-BOOKKEEPING-100K다. 이 보충안은 책임의 지정 형식과 줄 참조만 조정한다. 다섯 규모·비교 열·I25 기준·원 B03 소스 경계·독립 수용·최종 소유자 승인·실패 처분을 바꾸지 않는다.

formal F exit 재심사 및 최종 T6.9 수용 전의 증거 의무도 유지한다. 모든 이관 증거와 whole-F proof, 기기 gate 및 별도 승인 전 R1 활성화와 production 배포는 금지된다. B05/B08은 실험·미채택이다. benchmark·구현·기기 실행 허가는 추가하지 않는다.

적용하지 않았으므로 Phase B 증거 상태는 INCONCLUSIVE, formal T6.6F closure는 NOT AUTHORIZED, R1 activation은 CLOSED, production deployment는 NOT AUTHORIZED다. 이는 새 독립 F 종결 판정이 아니라 변경되지 않은 현재 상태의 확인이다.

## 5. 적용 이후 요청된 심사의 순서

보충 결정을 승인받아 구속 개정을 적용한 뒤에만 별도 독립 정합성 검토를 수행하고, 그 다음 별도 T6.6F 종결 재판정을 진행한다. 이번 적용 전 대조를 적용 후 독립 검토나 종결 재판정으로 바꾸어 부르지 않는다. 적용을 보류한 지금 두 후속 심사는 미실행이다.

## 6. 보존과 분석 검증

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이며 staged 변경은 0개다. 2,693개 index path/mode/blob/stage와 실제 index bytes SHA, 사전 파일 6,453개의 SHA/mode/길이를 기록했다. 새 파일은 이 보고서와 전용 증거 디렉터리뿐이다. 구속 문서·제품·계측·admission·release·source lock·원 B11 및 B01–B10 이력은 변경하지 않았다.

검증은 새 JSON·정확한 원문/제안 일치·단 세 부분 치환·필수 필드·기존 파일/index·동결 후보 해시 확인만 수행한다. npm build·backend/Flutter 회귀·full cold·실기기·API 요청은 실행하지 않는다. 대형 임시 산출물 정리는 해당 없음이며 삭제/회수는 0B다. 결과는 [validation-and-preservation.json](benchmarks/t66f-b11-approval-preflight/validation-and-preservation.json), 산출물 해시는 [evidence-manifest.json](benchmarks/t66f-b11-approval-preflight/evidence-manifest.json)에 보존한다.

권고하는 단일 다음 결정: 프로젝트 소유자는 위 GOV01·GOV02의 역할 기반 책임 지정과 REF01의 줄 참조 교정을 묶은 제한 보충안을 별도로 명시 승인하십시오.
''')
REPORT.write_text(''.join(parts))
# 신규 문서의 분석 및 보존만 검사한다.
base=json.loads((D/'starting-state.json').read_text());errors=[]
for row in base['preexisting_files']:
 p=R/row['path']
 if not p.is_file() or p.stat().st_size!=row['bytes'] or oct(p.stat().st_mode&0o777)!=row['mode'] or digest(p)!=row['sha256']: errors.append(row['path'])
env=dict(os.environ,GIT_OPTIONAL_LOCKS='0');git=lambda *a:subprocess.check_output(['git',*a],cwd=R,env=env)
indexok=digest(R/'.git/index')==base['index_file_sha256'] and hashlib.sha256(git('ls-files','--stage','-z')).hexdigest()==base['index_entries_sha256']
assert indexok and not errors
assert git('rev-parse','HEAD').decode().strip()==base['head'] and not git('diff','--cached','--name-only').strip()
archives=[]
for a in json.loads((R/'docs/benchmarks/t66f-b10/source-certification-boundaries.json').read_text())['frozen_sources']:
 h=digest(pathlib.Path(a['archive']));assert h==a['archive_sha256'];archives.append({'id':a['id'],'path':a['archive'],'sha256':h})
assert all(x['applied'] is False for x in proposed)
assert sum(x['changed'] for x in proposed)==3
assert not re.search('[\u3040-\u30ff]',REPORT.read_text())
save('validation-and-preservation.json',{'task':'T6.6F-B11 승인 사전 검토','status':'PASS — PREFLIGHT ARTIFACTS AND PRESERVATION ONLY','head':base['head'],'preexisting_files_preserved':len(base['preexisting_files']),'preexisting_file_changes':errors,'index_entries_preserved':len(base['index_entries']),'index_file_sha256':base['index_file_sha256'],'index_preserved':indexok,'staged_changes':0,'B11_manifest_members_preserved':12,'archives_preserved':archives,'redline_context_checks':5,'proposed_text_checks':5,'limited_replacements':3,'binding_amendment_applied':False,'product_runs':0,'new_benchmarks':0,'real_device_runs':0,'post_application_independent_review':'NOT PERFORMED — APPLICATION HELD','new_T66F_closure_readjudication':'NOT PERFORMED — APPLICATION HELD','git_mutations':False,'deleted_bytes':0})
for p in D.glob('*.json'):json.loads(p.read_text())
artifacts=sorted([p for p in D.rglob('*') if p.is_file() and p.name!='evidence-manifest.json']+[REPORT])
save('evidence-manifest.json',{'task':'T6.6F-B11 승인 사전 검토','self_hash_excluded':True,'files':[{'path':str(p.relative_to(R)),'sha256':digest(p),'bytes':p.stat().st_size} for p in artifacts]})
print(json.dumps({'redline_contexts_match':5,'report_proposal_matches':5,'preexisting_files_preserved':len(base['preexisting_files']),'index_entries_preserved':len(base['index_entries']),'limited_supplement_replacements':3,'binding_changes':0,'status':'소유자 승인 접수·책임 지정 충돌로 적용 보류'},ensure_ascii=False))

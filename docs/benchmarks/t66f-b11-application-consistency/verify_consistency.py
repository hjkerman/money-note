#!/usr/bin/env python3
"""문서 전용 독립 대조. 제품·계측·API 코드를 import/실행하지 않는다."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
os.chdir(ROOT)
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')

def git(*args):
    return subprocess.check_output(['git', *args], env=ENV)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def readj(p):
    return json.loads(Path(p).read_text())

def writej(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def ident(p):
    p = Path(p)
    s = p.stat()
    return {'path': str(p), 'sha256': sha(p.read_bytes()), 'bytes': s.st_size, 'mode': oct(stat.S_IMODE(s.st_mode))}

def index_entries():
    rows = []
    for part in git('ls-files', '--stage', '-z').split(b'\0'):
        if part:
            identity, path = part.decode().split('\t', 1)
            rows.append({'path': path, 'identity': identity})
    return rows

def inventory():
    paths = sorted(set(p.decode() for p in git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0') if p))
    return [ident(p) for p in paths if Path(p).is_file() and not p.startswith('docs/benchmarks/t66f-b11-application-consistency/') and p != 'docs/t66f-b11-applied-amendment-independent-consistency-review.md']

idxpath = Path(git('rev-parse', '--git-path', 'index').decode().strip())
start = OUT / 'starting-state.json'
if not start.exists():
    writej('starting-state.json', {'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'head': git('rev-parse', 'HEAD').decode().strip(), 'index_file_sha256': sha(idxpath.read_bytes()), 'index_entries': index_entries(), 'staged_changes': git('diff', '--cached', '--name-status').decode(), 'preexisting_files': inventory(), 'scope': 'visible tracked/nonignored files; ignored runtime/production not scanned'})

base = 'docs/benchmarks/'
proposal = readj(base + 't66f-b11/proposed-amendment-record.json')
supplement = readj(base + 't66f-b11-approval-preflight/responsibility-supplement-proposal.json')
authorization = readj(base + 't66f-b11-application/authorization-decision.json')
application = readj(base + 't66f-b11-application/application-record.json')
original = readj(base + 't66f-b11/transfer-obligation-register.json')
active = readj(base + 't66f-b11-application/active-transfer-obligation-register.json')
prior = readj(base + 't66f-b11-application/starting-state.json')
expected_ids = ['T35-100K-NC','T35-100K-CARD','T35-100K-CASH','T35-ROWS','T35-NET','T35-GZIP','I25-E3-100K','I25-BOOKKEEPING-100K']
checks = []

def check(key, value, evidence=None):
    checks.append({'id': key, 'pass': bool(value), 'evidence': evidence})

check('approval.authorized', authorization['approved'] is True)
check('approval.original_report_sha', sha(Path('docs/t66f-b11-normative-deferral-proposal.md').read_bytes()) == authorization['approved_original_report_sha256'])
check('approval.original_record_sha', sha(Path(base+'t66f-b11/proposed-amendment-record.json').read_bytes()) == authorization['approved_original_amendment_record_sha256'])
check('approval.supplement_sha', sha(Path(base+'t66f-b11-approval-preflight/responsibility-supplement-proposal.json').read_bytes()) == authorization['approved_supplement_file_sha256'])
check('supplement.exact_three', [x['id'] for x in supplement['changes']] == ['GOV01','GOV02','REF01'])
expected_text = {}
exact_rows = []
for am in proposal['amendments']:
    text = am['proposed_addition_ko']
    changes = [x for x in supplement['changes'] if x['amendment_id'] == am['id']]
    for change in changes:
        check(am['id']+'.replacement_once.'+change['id'], text.count(change['old']) == 1)
        text = text.replace(change['old'], change['new'])
    expected_text[am['id']] = text
    rec = next(x for x in supplement['reconciled_amendments'] if x['id'] == am['id'])
    applied = next(x for x in application['amendments'] if x['id'] == am['id'])
    target = Path(am['target_path']).read_text()
    context = am['current_normative_statement']
    before_path = base+'t66f-b11-application/'+Path(am['target_path']).name.replace('.md','.before.md')
    before = Path(before_path).read_text()
    ref=am['current_reference']
    context_lines='\n'.join(before.splitlines()[ref['line_start']-1:ref['line_end']])
    check(am['id']+'.original_context_reference', context_lines == context)
    check(am['id']+'.original_context_once', before.count(context) == 1)
    check(am['id']+'.original_context_sha', sha(context.encode()) == applied['original_context_sha256'])
    check(am['id']+'.original_addition_sha', sha(am['proposed_addition_ko'].encode()) == rec['original_B11_addition_sha256'] == applied['original_B11_addition_sha256'])
    check(am['id']+'.reconciled_exact', text == rec['proposed_reconciled_addition_ko'] == applied['applied_addition_ko'])
    check(am['id']+'.reconciled_sha', sha(text.encode()) == rec['proposed_reconciled_addition_sha256'] == applied['applied_addition_sha256'])
    check(am['id']+'.target_context_addition_once', target.count(context+'\n\n'+text) == 1)
    exact_rows.append({'id':am['id'],'target':am['target_path'],'section':am['target_section'],'supplement_changes':[x['id'] for x in changes],'original_addition_sha256':sha(am['proposed_addition_ko'].encode()),'expected_applied_addition_sha256':sha(text.encode()),'current_start_line':target[:target.index(text)].count('\n')+1,'current_end_line':target[:target.index(text)+len(text)].count('\n')+1})
file_rows=[]
for file in application['files']:
    path=file['path']; current=Path(path).read_bytes(); forward=Path(base+'t66f-b11-application/'+Path(path).name.replace('.md','.before.md')).read_bytes(); recovered=current
    for am in proposal['amendments']:
        if am['target_path']==path:
            context=am['current_normative_statement'].encode(); addition=expected_text[am['id']].encode()
            forward=forward.replace(context,context+b'\n\n'+addition,1)
            recovered=recovered.replace(context+b'\n\n'+addition,context,1)
    before=Path(base+'t66f-b11-application/'+Path(path).name.replace('.md','.before.md')).read_bytes()
    check(path+'.forward_exact',forward==current)
    check(path+'.reverse_exact',recovered==before)
    check(path+'.before_sha_record',sha(before)==file['before_sha256'])
    check(path+'.after_sha_record',sha(current)==file['after_sha256'])
    original_file=next(x for x in prior['preexisting_files'] if x['path']==path)
    check(path+'.before_application_baseline_sha',sha(before)==original_file['sha256'])
    file_rows.append({'path':path,'before_sha256':sha(before),'current_sha256':sha(current),'forward_exact':forward==current,'reverse_exact':recovered==before,'before_bytes':len(before),'after_bytes':len(current),'original_lines':len(before.splitlines()),'current_lines':len(current.splitlines())})
writej('exact-application-verification.json',{'method_ko':'원 B11 각 추가문에 승인된 GOV01/GOV02/REF01만 적용해 기대 bytes를 독립 생성. before 원문에 전방 삽입 및 현재 원문에서 추가문 제거를 각각 수행. 저장된 application 주장만 신뢰하지 않음.','amendments':exact_rows,'files':file_rows,'checks':[x for x in checks]})

for name,doc in [('proposal',proposal),('original_register',original),('authorization',authorization),('supplement',supplement),('active',active)]:
    check('IDs.'+name,doc['transferred_obligation_ids']==expected_ids)
check('active.exact_eight',[x['id'] for x in active['obligations']]==expected_ids)
check('active.contract_unchanged',active['future_acceptance_contract']==original['future_acceptance_contract']==proposal['future_acceptance_contract'])
trace=[]
original_by_id={x['id']:x for x in original['obligations']}
roles={'execution_role':'T6.9 구현·측정 워크스트림','independent_acceptance_role':'해당 구현·측정에 관여하지 않은 별도 T6.9 감사 세션','final_approval_authority':'프로젝트 소유자'}
for ob in active['obligations']:
    old=original_by_id[ob['id']]
    unchanged={k:ob.get(k)==v for k,v in old.items() if k not in ['existing_deferral_authorization','proposed_future_owner']}
    role=ob['current_responsibility_assignment']
    check(ob['id']+'.original_criteria_evidence_preserved',all(unchanged.values()),[k for k,v in unchanged.items() if not v])
    check(ob['id']+'.roles_assigned',all(role[k]==v for k,v in roles.items()) and role['role_assignment_complete'] is True and role['named_individual_required'] is False and role['assigned_person'] is None)
    check(ob['id']+'.no_stale_personal_appointment_condition','proposed_future_owner' not in ob)
    check(ob['id']+'.evidence_not_accepted',ob['status']==ob['current_evidence_status']==old['status'] and ob['transfer_status']=='TRANSFERRED — MANDATORY EVIDENCE PENDING')
    check(ob['id']+'.authorization_bound',ob['existing_deferral_authorization']['change_id']==authorization['change_id'] and ob['existing_deferral_authorization']['supplement_id']==authorization['supplement_id'])
    trace.append({k:ob[k] for k in ['id','source_requirement_ids','exact_normative_references','original_acceptance_criterion_ko','required_workload_scales','workloads','missing_evidence_ko','verification_method_ko','deadline_or_blocking_milestone','consequence_if_incomplete_ko','current_evidence_status','current_responsibility_assignment']})
check('original.B10_37_rows',len(original['B10_incomplete_row_coverage'])==original['B10_incomplete_row_count']==37)
writej('obligation-traceability.json',{'scope_ko':'8개 기준·source/runtime/fixture·기존/결측 증거·status·검증·deadline·불이행 처분을 원 등록부와 exact 비교. historical line 참조는 적용 전 원문 기준이며 before.md로 검증 가능.','contract_unchanged':active['future_acceptance_contract']==original['future_acceptance_contract'],'obligations':trace,'B10_incomplete_rows_retained':37,'nontransferred_ids':[x['id'] for x in original['obligations'] if x['id'] not in expected_ids]})

changed=[]; missing=[]; mode_changed=[]
for old in prior['preexisting_files']:
    p=Path(old['path'])
    if not p.is_file():missing.append(old['path']);continue
    now=ident(p)
    if now['mode']!=old['mode']:mode_changed.append(old['path'])
    if any(now[k]!=old[k] for k in ['sha256','bytes','mode']):changed.append({'before':old,'current':now})
allowed=set(prior['allowed_existing_mutations'])
check('preservation.original_preexisting_only_two_amendments',set(x['before']['path'] for x in changed)==allowed,{'compared':len(prior['preexisting_files']),'changed':[x['before']['path'] for x in changed]})
check('preservation.original_missing_zero',not missing,missing)
check('preservation.original_mode_changes_zero',not mode_changed,mode_changed)
check('preservation.HEAD',git('rev-parse','HEAD').decode().strip()==prior['head'])
check('preservation.index_bytes',sha(idxpath.read_bytes())==prior['index_file_sha256'])
check('preservation.index_entries',index_entries()==prior['index_entries'])
check('preservation.staged',git('diff','--cached','--name-status').decode()==prior['staged_changes'])
historical_manifest=readj(base+'t66f-b11/evidence-manifest.json')
manifest_bad=[]
for x in historical_manifest['files']:
    if ident(x['path'])!=x:manifest_bad.append(x['path'])
check('preservation.historical_B11_manifest',not manifest_bad,manifest_bad)
audit_start=readj(start); audit_drift=[]
for x in audit_start['preexisting_files']:
    if not Path(x['path']).is_file() or ident(x['path'])!=x:audit_drift.append(x['path'])
check('preservation.audit_preexisting_unchanged',not audit_drift,audit_drift)
critical=[x for x in audit_start['preexisting_files'] if any(s in x['path'] for s in ['t66f-b03-ic01-p03/','t66f-b03-ir02/','t66f-b03-ir07/','t66f-b11/','t66f-b11-approval-preflight/','t66f-b11-application/'])]
writej('preservation-verification.json',{'application_baseline_compared_files':len(prior['preexisting_files']),'application_baseline_changed_files':changed,'missing':missing,'mode_changes':mode_changed,'review_start_compared_files':len(audit_start['preexisting_files']),'review_start_drift':audit_drift,'HEAD':git('rev-parse','HEAD').decode().strip(),'index_file_sha256':sha(idxpath.read_bytes()),'index_entries_count':len(index_entries()),'index_preserved':sha(idxpath.read_bytes())==prior['index_file_sha256'] and index_entries()==prior['index_entries'],'historical_B11_manifest_entries_verified':len(historical_manifest['files']),'critical_evidence_files':critical,'scope_limitation_ko':'visible tracked/nonignored baseline의 bytes/size/mode·Git HEAD/index 대조. ignored runtime·production·전체 filesystem 부재를 주장하지 않음. 대형 source archive를 실행/복원하지 않음.'})
writej('mechanical-checks.json',{'checked_at_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'passed':sum(x['pass'] for x in checks),'failed':[x for x in checks if not x['pass']],'new_measurements':0,'product_execution_count':0})
print(json.dumps({'document_checks':len(checks),'failed_checks':sum(not x['pass'] for x in checks),'baseline_files':len(prior['preexisting_files']),'changed_existing':[x['before']['path'] for x in changed],'audit_drift':audit_drift},ensure_ascii=False))
raise SystemExit(0 if all(x['pass'] for x in checks) else 1)

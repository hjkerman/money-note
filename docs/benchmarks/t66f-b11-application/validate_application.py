"""승인 규범 추가문·새 JSON/보고서·역사/인덱스 보존만 검사한다."""
import pathlib,json,hashlib,subprocess,os,datetime,re,sys
R=pathlib.Path('/home/hjkerman/codex/money-note');D=R/'docs/benchmarks/t66f-b11-application'
ENV=dict(os.environ,GIT_OPTIONAL_LOCKS='0');checks=[]
def check(n,v,detail=None):checks.append({'check':n,'pass':bool(v),'detail':detail})
def load(p):return json.loads((R/p).read_text())
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=R,env=ENV)
base=load('docs/benchmarks/t66f-b11-application/starting-state.json');app=load('docs/benchmarks/t66f-b11-application/application-record.json');auth=load('docs/benchmarks/t66f-b11-application/authorization-decision.json');supp=load('docs/benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json');reg=load('docs/benchmarks/t66f-b11-application/active-transfer-obligation-register.json');orig=load('docs/benchmarks/t66f-b11/proposed-amendment-record.json')
check('소유자·보충안 명시 승인 기록',auth['approved'] and auth['supplement_approval_quote']=='좋아. 승인할게.' and auth['supplement_id']==supp['supplement_id'])
check('승인된 exact 원본·보충안 SHA',digest(R/'docs/t66f-b11-normative-deferral-proposal.md')==auth['approved_original_report_sha256'] and digest(R/'docs/benchmarks/t66f-b11/proposed-amendment-record.json')==auth['approved_original_amendment_record_sha256'] and digest(R/'docs/benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json')==auth['approved_supplement_file_sha256'])
finals={a['id']:a for a in supp['reconciled_amendments']}
check('AM01–05 exact identity',len(app['amendments'])==5 and all(x['applied_addition_sha256']==finals[x['id']]['proposed_reconciled_addition_sha256'] and x['applied_addition_ko']==finals[x['id']]['proposed_reconciled_addition_ko'] for x in app['amendments']))
for f in app['files']:
 p=R/f['path'];now=p.read_bytes();s=now.decode()
 for a in app['amendments']:
  if a['target_path']==f['path']:
   insertion='\n'+a['applied_addition_ko']+'\n';check('추가문 유일 '+a['id'],s.count(insertion)==1);s=s.replace(insertion,'',1)
 check('현재 승인 후 SHA '+f['path'],digest(p)==f['after_sha256'])
 check('추가문 제거로 원문 bytes 복구 '+f['path'],hashlib.sha256(s.encode()).hexdigest()==f['before_sha256'])
check('구속 파일 2개만 변경',len(app['files'])==2 and {x['path'] for x in app['files']}==set(base['allowed_existing_mutations']))
check('의무 8개 exact 보존',reg['transferred_obligation_ids']==orig['transferred_obligation_ids']==auth['transferred_obligation_ids'] and len(reg['obligations'])==8)
check('이관 의무 미수용 상태 유지',all(x['transfer_status']=='TRANSFERRED — MANDATORY EVIDENCE PENDING' and x['current_evidence_status'] in ['PARTIAL','UNVERIFIED'] for x in reg['obligations']))
check('역할 책임 배정·개인 발명 없음',all(x['current_responsibility_assignment']['role_assignment_complete'] and not x['current_responsibility_assignment']['named_individual_required'] and x['current_responsibility_assignment']['assigned_person'] is None and 'proposed_future_owner' not in x for x in reg['obligations']))
check('원 source·fixture·기준 계약 불변',reg['future_acceptance_contract']==load('docs/benchmarks/t66f-b11/transfer-obligation-register.json')['future_acceptance_contract'])
check('F·R1·production 차단 유지',reg['formal_F_closure']=='NOT AUTHORIZED' and reg['quantitative_phase_B']=='INCONCLUSIVE' and reg['R1_activation']=='CLOSED' and reg['production_deployment']=='NOT AUTHORIZED' and not auth['execution_GO'])
# 역사 B11/preflight 증거의 기존 manifest는 재생성하지 않는다.
for path in ['docs/benchmarks/t66f-b11/evidence-manifest.json','docs/benchmarks/t66f-b11-approval-preflight/evidence-manifest.json']:
 m=load(path);check('역사 manifest 보존 '+path,all(digest(R/x['path'])==x['sha256'] for x in m['files']))
expected_after={x['path']:x['after_sha256'] for x in app['files']};changes=[];approved=[]
for x in base['preexisting_files']:
 p=R/x['path']
 if not p.is_file():changes.append({'path':x['path'],'reason':'MISSING'});continue
 h=digest(p)
 if x['path'] in expected_after:
  approved.append(x['path'])
  if h!=expected_after[x['path']] or oct(p.stat().st_mode&0o777)!=x['mode']:changes.append({'path':x['path'],'reason':'UNAPPROVED_NORMATIVE_CHANGE'})
 elif h!=x['sha256'] or p.stat().st_size!=x['bytes'] or oct(p.stat().st_mode&0o777)!=x['mode']:changes.append({'path':x['path'],'reason':'UNAUTHORIZED_CHANGE'})
check('사전 6461파일 승인 범위 외 불변',not changes,{'count':len(base['preexisting_files']),'approved_existing_changes':approved,'unexpected_changes':changes})
idxhash=digest(R/'.git/index');check('index bytes 보존',idxhash==base['index_file_sha256'],idxhash)
check('index path/mode/blob/stage 보존',hashlib.sha256(git('ls-files','--stage','-z')).hexdigest()==base['index_entries_sha256'],len(base['index_entries']))
check('HEAD 및 staged 보존',git('rev-parse','HEAD').decode().strip()==base['head'] and not git('diff','--cached','--name-status').strip())
archives=[]
for x in load('docs/benchmarks/t66f-b10/source-certification-boundaries.json')['frozen_sources']:
 h=digest(pathlib.Path(x['archive']));archives.append({'id':x['id'],'path':x['archive'],'sha256':h,'pass':h==x['archive_sha256']})
check('5개 동결 후보 보존',all(x['pass'] for x in archives))
# 독립 검토·새 종결 판정 산출물의 존재/독립성/결론은 root의 최종 보고서와 함께 검증한다.
review_paths=['docs/t66f-b11-applied-amendment-independent-consistency-review.md','docs/benchmarks/t66f-b11-application-consistency/decision.json','docs/t66f-b11-post-amendment-closure-readjudication.md','docs/benchmarks/t66f-b11-closure-readjudication/closure-decision.json']
for p in review_paths:check('별도 심사 산출물 '+p,(R/p).is_file())
reports=[R/'docs/t66f-b11-approved-amendment-application.md',R/review_paths[0],R/review_paths[2]]
for p in reports:
 if p.is_file():
  s=p.read_text();check('한국어 보고서 일본어 설명 없음 '+p.name,not re.search('[\u3040-\u30ff]',s))
# 이 작업 및 두 독립 세션의 전용 경로만 추가한다.
known={x['path'] for x in base['preexisting_files']};current={x.decode() for x in git('ls-files','--cached','--others','--exclude-standard','-z').split(b'\0') if x}
new=sorted(current-known)
def allowed(p):return any(p.startswith(x) for x in ['docs/benchmarks/t66f-b11-application/','docs/benchmarks/t66f-b11-application-consistency/','docs/benchmarks/t66f-b11-closure-readjudication/']) or p in ['docs/t66f-b11-approved-amendment-application.md',*review_paths[0::2]]
check('신규 파일은 이번 적용·독립 심사 경로만',all(allowed(p) for p in new),new)
for p in D.glob('*.json'):
 load(str(p.relative_to(R)));check('JSON parse '+p.name,True)
errors=[x for x in checks if not x['pass']]
result={'schema_version':1,'task':'T6.6F-B11 승인 개정 적용 검증','recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not errors else 'FAIL','checks':checks,'errors':errors,'preexisting_files':len(base['preexisting_files']),'approved_existing_file_changes':approved,'unapproved_existing_file_changes':changes,'index_entries':len(base['index_entries']),'index_file_sha256':idxhash,'frozen_archives':archives,'new_paths':new,'new_full_cold_runs':0,'regression_suites':0,'builds_run':0,'real_device_runs':0,'product_source_modified':False,'engine_admission_modified':False,'commit':'NONE','push':'NOT PERFORMED','temporary_cleanup':'NOT APPLICABLE','deleted_bytes':0}
(D/'validation-and-preservation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
artifacts=sorted([p for p in D.rglob('*') if p.is_file() and p.name!='evidence-manifest.json']+[reports[0]])
(D/'evidence-manifest.json').write_text(json.dumps({'schema_version':1,'task':'T6.6F-B11 승인 개정 적용','self_hash_excluded':True,'files':[{'path':str(p.relative_to(R)),'sha256':digest(p),'bytes':p.stat().st_size,'mode':oct(p.stat().st_mode&0o777)} for p in artifacts],'independent_review_manifest_paths':['docs/benchmarks/t66f-b11-application-consistency/evidence-manifest.json','docs/benchmarks/t66f-b11-closure-readjudication/evidence-manifest.json']},ensure_ascii=False,indent=2)+'\n')
if errors:print(json.dumps({'status':'FAIL','errors':errors},ensure_ascii=False,indent=2));sys.exit(1)
print(json.dumps({'status':'PASS','checks':len(checks),'preexisting_files':len(base['preexisting_files']),'approved_normative_file_changes':len(approved),'index_entries_preserved':len(base['index_entries']),'frozen_candidates_preserved':len(archives),'new_measurements':0},ensure_ascii=False))

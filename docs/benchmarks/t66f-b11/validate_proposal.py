"""B11 분석 산출물·보존 검사만 수행. 제품 import/실행 및 Git 쓰기 없음."""
import datetime,hashlib,json,os,pathlib,re,subprocess,sys
ROOT=pathlib.Path('/home/hjkerman/codex/money-note')
D=ROOT/'docs/benchmarks/t66f-b11'
REPORT=ROOT/'docs/t66f-b11-normative-deferral-proposal.md'
ENV=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
checks=[]
def check(name,ok,detail=None):
 checks.append({'check':name,'pass':bool(ok),'detail':detail})
def load(p):return json.loads(p.read_text())
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,env=ENV)
required=['normative-dependency-map.json','transfer-obligation-register.json','option-comparison.json','proposed-amendment-record.json','authorization-decision.json']
for n in required:
 j=load(D/n);check('JSON/task '+n,j['task']=='T6.6F-B11')
register=load(D/required[1]); amendment=load(D/required[3]); auth=load(D/required[4]); dep=load(D/required[0])
ids=register['transferred_obligation_ids']; allids={x['id'] for x in register['obligations']}
check('8개 고유 이관 ID',len(ids)==len(set(ids))==8)
check('문서 간 이관 목록',ids==amendment['transferred_obligation_ids']==auth['transferred_obligation_ids'])
fields=['source_requirement_ids','exact_normative_references','original_acceptance_criterion_ko','required_workload_scales','required_source_runtime_identity','existing_evidence','missing_evidence_ko','historical_failure_or_blocker_ko','existing_deferral_authorization','proposed_future_owner','deadline_or_blocking_milestone','verification_method_ko','consequence_if_incomplete_ko','acceptance_semantics']
check('모든 의무 필수 열',all(all(f in x for f in fields) for x in register['obligations']))
check('의무 semantics 구분',all(not x['acceptance_semantics']['quantitative_or_correctness_criterion_changed'] for x in register['obligations']))
original=load(ROOT/'docs/benchmarks/t66f-b10/requirements-evidence-matrix.json')
openrows={x['id']:x for x in original['rows'] if x['verified_result'] in ['PARTIAL','UNVERIFIED','FAIL']}
cov=register['B10_incomplete_row_coverage']
check('B10 전체 미완료 37행',len(openrows)==len(cov)==37 and {x['B10_id'] for x in cov}==set(openrows))
check('B10 원 행·모든 하위 연결 보존',all(x['B10_row_preserved']==openrows[x['B10_id']] and x['canonical_obligation_ids'] and set(x['canonical_obligation_ids'])<=allids for x in cov))
check('five-point exact',register['future_acceptance_contract']['scales']==[1000,5000,10000,50000,100000])
check('source 대체 금지·fresh cold 별도 MUST 없음',not register['future_acceptance_contract']['new_cold_required'] and not register['future_acceptance_contract']['later_source_can_discharge_original_without_B03_evidence'] and register['future_acceptance_contract']['later_same_B03_normal_evidence_can_discharge_without_fresh_B03_cold'])
check('미승인·미적용',auth['explicit_approval']=='NOT GRANTED' and auth['approval_authority'] is None and not amendment['binding_protocol_modified'] and not amendment['T69_specification_modified'] and all(not x['applied'] for x in amendment['amendments']))
check('최소 제안 세 개',len(load(D/'option-comparison.json')['options'])==3)
check('T6.9 상세 명세 자동 가정 없음',dep['separate_T69_governing_spec_found'] is False)
check('proposal 정량·금지 기준 불변',not amendment['acceptance_criteria_weakened'] and amendment['completion_semantics_changed_if_approved'])
for x in amendment['amendments']:
 ref=x['current_reference']; actual='\n'.join((ROOT/x['target_path']).read_text().splitlines()[ref['line_start']-1:ref['line_end']])
 check('exact current quotation '+x['id'],actual==x['current_normative_statement'])
 check('원문 포함 '+x['id'],x['current_normative_statement'] in REPORT.read_text() and x['proposed_addition_ko'] in REPORT.read_text())
for x in load(D/'requirements-source-manifest.json')['files']:
 check('source manifest '+x['path'],digest(ROOT/x['path'])==x['sha256'])
# report local citations와 줄 번호. 자체 생성할 두 파일만 pending 허용한 뒤 아래 작성한다.
report=REPORT.read_text();pending={D/'evidence-manifest.json',D/'validation-and-preservation.json'}
local_links=[]
for raw in re.findall(r'\]\(([^)]+)\)',report):
 if raw.startswith(('https://','http://')): continue
 raw=raw.split('#',1)[0]; line=None
 if re.search(r':\d+$',raw): raw,num=raw.rsplit(':',1);line=int(num)
 p=pathlib.Path(raw) if raw.startswith('/') else REPORT.parent/raw
 ok=p.exists() or p in pending
 if line and p.is_file():ok=ok and 0<line<=len(p.read_text().splitlines())
 local_links.append({'target':str(p),'line':line,'pass':ok})
check('로컬 인용 경로·줄 번호',all(x['pass'] for x in local_links),len(local_links))
check('일본어 설명 없음',not re.search('[\u3040-\u30ff]',report))
# Markdown fence: 원문 인용 내 3-backtick은 4-backtick 외부 fence를 닫지 않는다.
fence=None
for line in report.splitlines():
 m=re.match(r'^(`{3,})(.*)$',line)
 if m:
  n=len(m.group(1));tail=m.group(2).strip()
  if fence is None:fence=n
  elif n>=fence and not tail:fence=None
check('Markdown fence 균형',fence is None)
check('필수 footer exact 포함',(D/'required-footer.txt').read_text() in report)
base=load(D/'starting-state.json');changes=[]
for row in base['preexisting_files']:
 p=ROOT/row['path']
 if not p.is_file():changes.append({'path':row['path'],'reason':'MISSING'});continue
 if p.stat().st_size!=row['size'] or oct(p.stat().st_mode&0o777)!=row['mode'] or digest(p)!=row['sha256']:changes.append({'path':row['path'],'reason':'IDENTITY_CHANGED'})
check('기존 6440 파일 내용·mode 보존',not changes,{'count':len(base['preexisting_files']),'bytes':sum(x['size'] for x in base['preexisting_files']),'changes':changes})
head=git('rev-parse','HEAD').decode().strip(); index=git('ls-files','--stage','-z'); idxfile=digest(ROOT/'.git/index')
check('HEAD 보존',head==base['head'],head)
check('index 실제 bytes SHA 보존',idxfile==base['index_file_sha256'],idxfile)
check('index path/mode/blob/stage 보존',hashlib.sha256(index).hexdigest()==base['index_entries_sha256'],len(base['index_entries']))
check('staged 변경 0',not git('diff','--cached','--name-only').strip())
prepaths={x['path'] for x in base['preexisting_files']}
paths={p.decode() for p in git('ls-files','--cached','--others','--exclude-standard','-z').split(b'\0') if p}
new=sorted(paths-prepaths)
allowed=lambda p:p=='docs/t66f-b11-normative-deferral-proposal.md' or p.startswith('docs/benchmarks/t66f-b11/')
check('B11 소유 경로만 추가',all(allowed(p) for p in new),new)
archives=[]
for x in load(ROOT/'docs/benchmarks/t66f-b10/source-certification-boundaries.json')['frozen_sources']:
 p=pathlib.Path(x['archive']); observed=digest(p)
 archives.append({'id':x['id'],'archive':str(p),'expected_B10_sha256':x['archive_sha256'],'observed_sha256':observed,'pass':observed==x['archive_sha256']})
check('B03/B05/B05-A/B08/B09 동결 archive 보존',all(x['pass'] for x in archives))
# 일반 build/회귀 대신 B11 문서 분석 범위만 실행했다.
errors=[x for x in checks if not x['pass']]
result={'schema_version':1,'task':'T6.6F-B11','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not errors else 'FAIL','checks':checks,'errors':errors,'head':head,'index_file_sha256':idxfile,'index_entries_sha256':hashlib.sha256(index).hexdigest(),'preexisting_file_changes':changes,'new_paths':new,'archives':archives,'validation_scope_ko':'B11 문서/JSON 분석·read-only 해시·Git 보존 검사; 제품 코드/벤치마크 실행 아님','new_full_cold_runs':0,'regression_suites_run':0,'real_device_runs':0,'builds_run':0,'git_index_modified':False if idxfile==base['index_file_sha256'] else True,'large_temporary_cleanup':'NOT APPLICABLE','deleted_bytes':0,'initial_tool_environment_failure_ko':'기본 bwrap loopback 초기화 실패로 첫 read 명령 미실행; 승인 검토된 경로 사용. 자동 승인 거절 없음.'}
(D/'validation-and-preservation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
artifacts=sorted([p for p in D.rglob('*') if p.is_file() and p.name!='evidence-manifest.json']+[REPORT])
manifest={'schema_version':1,'task':'T6.6F-B11','status':'DRAFT ONLY — NOT APPLIED','self_hash_excluded':True,'files':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p),'bytes':p.stat().st_size,'mode':oct(p.stat().st_mode&0o777)} for p in artifacts],'binding_protocol_modified':False,'T69_specification_modified':False}
(D/'evidence-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
if errors:
 print(json.dumps({'status':'FAIL','errors':errors},ensure_ascii=False,indent=2));sys.exit(1)
print(json.dumps({'status':'PASS','checks':len(checks),'existing_files_preserved':len(base['preexisting_files']),'staged_entries_preserved':len(base['index_entries']),'external_and_historical_archives_preserved':len(archives),'B10_open_rows_preserved':len(cov),'manifest_members':len(artifacts),'product_or_benchmark_runs':0},ensure_ascii=False))

"""B11 문서·JSON 작성 전용. 제품 import·실행·Git mutation 없음."""
import json, pathlib, hashlib, datetime, subprocess
ROOT=pathlib.Path('/home/hjkerman/codex/money-note')
D=ROOT/'docs/benchmarks/t66f-b11'
P='docs/t66/c/t66c-delta-sync-protocol.md'
B='docs/t66/b/t66b-hot-cold-design.md'
A='docs/t66/a/t66a-payload-attribution.md'
REPORT='docs/t66f-b11-normative-deferral-proposal.md'
CHANGE='T66F-B11-TRANSFER-01'
HEAD='ebcbd54d90eeee194a04b9eea6367f446ee2fd28'
PAYLOAD='8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8'
ENGINE='7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c'
ARCHIVE='fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5'
def read(p): return (ROOT/p).read_text()
def js(p):return json.loads(read(p))
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def save(n,j):(D/n).write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def loc(path,sec,start,end=None):return {'path':path,'section':sec,'line_start':start,'line_end':end or start}
def quote(path,start,end):return '\n'.join(read(path).splitlines()[start-1:end])
def link(path,sec,line):return f'[{sec}](/home/hjkerman/codex/money-note/{path}:{line})'
base=js('docs/benchmarks/t66f-b11/starting-state.json')
b10=js('docs/benchmarks/t66f-b10/requirements-evidence-matrix.json')
b04=js('docs/benchmarks/t66f-b04/run-manifest.json')
source={'base_commit':HEAD,'payload_sha256':PAYLOAD,'engine_sha256':ENGINE,'archive_sha256':ARCHIVE,'selected_files':899,'selected_bytes':9801906,'runtime':{'python':'CPython 3.12.3','backend_sqlite':'3.45.1','client_sqlite':'3.53.4','flutter':'3.47.4','dart':'3.13.3'},'monitoring_boundary':'IR07 지원 환경의 안정된 monitoring 설정; unsafe/미지원 환경은 measurement incomplete로 거부','basis':['docs/benchmarks/t66f-b04/source-identity.json','docs/benchmarks/t66f-b04/environment.json','docs/benchmarks/t66f-b03-ir07/monitoring-contract-decision.json','docs/benchmarks/t66f-b10/source-certification-boundaries.json'],'live_worktree_is_reference':False}
fixture={'normative_numeric_H':None,'normative_numeric_D':None,'normative_sample_count':None,'normative_latency_threshold':None,'scale_labels':[1000,5000,10000,50000,100000],'experimental_seed':662602,'evaluation_date':'2026-10-05','timezone_offset_minutes':540,'current_ledger_rows':105,'other_table_rows':35,'initial_hot_bytes':87364,'initial_control_bytes':3178,'scale_label_semantics_ko':'ledger 총 N; archive N−105, 전체 authoritative rows N+35. 규범 N 정의와 fixture label 차이를 함께 보고한다.','D':{'no-change':0,'card':1,'cash':1},'mutation_ko':'B04 카드 id1002 / 현금 id101 UPDATE, trial 1001/1002/1003원 및 −51/−52/−53원. 이는 기존 실험 입력이며 새 전역 규범 상수가 아니다.','existing_fixture_digests':{str(n):sorted({x['fixture_digest'] for x in b04['runs'] if x['N']==n and x.get('valid_for_binding_cost')}) for n in [1000,5000,10000,50000]},'future_100k_fixture_digest':None,'future_fixture_admission_ko':'N100k exact bytes·descriptor·행 값·Target/NS/principal·허용된 scale 차이·변경 전후 digest를 실행 전 freeze. 기존 4점과 동일 구성/입력임을 독립 대조; 새 NS의 root 문자열 동일성은 요구하지 않음.'}
metrics=['backend/client rows-read 및 실제 반환 행/SQL/query-plan 경계','D1–D3 generation/request와 E1/E2/E3Verify/E3Prepare/E3Commit/E4의 실제 hash 입력 bytes·횟수','primary UTF8/JSON/C1 submitted/completed/failed spans; backend JSON 완료와 Dart C1 완료 분리','SQL NEW TEXT UTF8/BLOB attempted/effective/committed/rollback 및 scalar/row 수; object/edge/stage/receipt/manifest/pointer/pin 비용','HTTP method/path·금융/auxiliary·request/response entity·decoded canonical·base64/JSON framing·headers·RTT dependency stages/cache misses','memory 관찰 방식·샘플링/peak 한계; HOST process RSS와 단말 heap 분리','반복 workload raw 표본·warmup/sample·median/p95 추정법·IQR 및 포함 timing 경계','full history fetch/hash/serialize/write=0; flat P control 목록 없음; leaf/hash-path/affected facts 증가','E3 full_recoveries/full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds 및 incremental/tree/index/hot row counters','lease/GC/refcount/root pin의 정상 hidden full graph/history scan 없음','동일 DB/Context·source/fixture의 full gzip 비교: representative/less-repetitive, bytes·codec CPU·parser/validation·write 분리']
refs=[loc(P,'§4',49,70),loc(P,'§16–18',321,415),loc(P,'§23–26',486,541),loc(P,'§31–34',612,681),loc(P,'§35',683,702),loc(P,'§36 I25',734),loc(P,'§38.7–12',789,796),loc(B,'§27',484,494),loc(B,'§29',513,532),loc(A,'§18',364,370)]
nodes=[
('SOURCE','소스·engine·release identity',refs[0],'모르는 version/engine best-effort 금지; immutable artifact와 source·allowlist 일치'),
('BASE','정당한 accepted baseline과 게시',refs[2],'complete target/guard→동기 COMMIT/readback; validator 변경 시 지원 compatibility 없으면 full 재검증'),
('GRID','다섯 규모 정상 비용',refs[4],'H/D 고정 1k/5k/10k/50k/100k no-change/card/cash 반복과 rows/bytes/HTTP/RTT/memory/median/p95'),
('I25','steady-state full-N 금지',refs[5],'instrumented rows/bytes 직접 증거; E3와 D/E integration에 적용'),
('P7','lease/GC/refcount 비용',loc(P,'§38.7',789),'정상 refresh hidden O(N) 없음'),
('COMPARE','framing/full gzip 비교',refs[6],'§15.3/35/38.12와 B §27의 rows·headers/base64/RTT·full gzip 비교'),
('PHASE-B','Phase B 증거 종결',loc('docs/t66f-b10-independent-phase-b-closure-adjudication.md','§7·9',118,157),'B10 Option D; 현재 비용/I25 이관 예외 없음'),
('R1-PROOF','R1 구현·복구·전이 증명',refs[3],'§31/33/34·I23/I24·§38.9–11은 whole-F 독립 의무'),
('ANDROID','Android 구현 proof',loc(P,'§26; §38.8',533,539),'실제 driver/VFS/fence/I/O/power-loss/previous recovery; 미검증 rollout 차단'),
('F-EXIT','formal T6.6F 전체 종결',loc(P,'§34',665,678),'R1/interop/full-resync/crash/performance→F 통합 감사→명시 rollout 승인'),
('T69-EXISTING','현재 T6.9 방향',loc(B,'§27·29',484,527),'대규모 감사 제안; 상세 독립 acceptance/이관 책임 규정 없음, 도식은 F 뒤'),
('DEVICE','post-T6.6 기기 성능',loc(P,'§35 마지막 문장; §38.12',702,794),'기존 시점 분리는 기기 성능에 한정; §26 durability나 HOST grid 면제 아님'),
('R1-ACTIVATION','R1 사용자 기능 활성화',loc(P,'§31 rollout dependency',641),'R1 stage 구현/시험과 활성화 구별; 복구·전체 F·명시 승인 전 닫힘'),
('DEPLOY','production deployment',loc('AGENTS.md','2. 규칙',25,29),'commit/push도 배포 승인 아님; 명시 운영 요청 필요')]
edges=[('SOURCE','BASE'),('BASE','GRID'),('BASE','I25'),('GRID','PHASE-B'),('I25','PHASE-B'),('P7','PHASE-B'),('COMPARE','PHASE-B'),('PHASE-B','F-EXIT'),('R1-PROOF','F-EXIT'),('ANDROID','F-EXIT'),('F-EXIT','R1-ACTIVATION'),('F-EXIT','DEPLOY'),('F-EXIT','T69-EXISTING'),('F-EXIT','DEVICE')]
dependency={'schema_version':1,'task':'T6.6F-B11','status':'ANALYSIS — NOT BINDING','source_references':refs,'nodes':[{'id':i,'title_ko':t,'reference':r,'contract_ko':c} for i,t,r,c in nodes],'edges':[{'prerequisite':a,'dependent':b,'kind':'현재 요구·B10 해석; T6.9 상세 entry는 미규정'} for a,b in edges],'T69_scope_ko':'A §18은 full 50k/100k scalability 승인을 T6.9 범위로 기술. B §27/29는 대규모 감사 제안과 F 이후 순서. 최신 C §35/36/38 의무를 자동 인수하지 않음. T6.7 UX 상세 entry 규정은 발견하지 못했고 C §33은 T6.8 이후 dead API 별도 consumer 감사만 명시.','separate_T69_governing_spec_found':False,'search_scope_ko':'Git tracked/nonignored visible repository 문서 및 README/AGENTS/.agents/.codex 관련 텍스트; B11 신규 파일 제외. T6.9/T6.7/T6.8 출처를 검색. 저장소 밖 승인 정책의 부재까지 단정하지 않음.','potential_cycle_ko':'F 완료→T6.9 entry라는 도식에 F 미완료 증거를 T6.9로 보내면 순환. 제안은 T6.9-E 증거수집 subgate만 formal F 전에 열고 최종 T6.9/F/rollout acceptance는 열지 않는다.','proposed_edges':[{'prerequisite':'승인된 개정·owner·동결 source·baseline/계측 사전심사','dependent':'T6.9-E collection-only'},{'prerequisite':'T6.9-E 독립 증거 수용 및 별도 R1/Android/whole-F proof','dependent':'formal F exit 재심사'},{'prerequisite':'formal F exit + 기기 gate + 별도 명시 승인','dependent':'R1 activation/production 심사'}],'already_authorized_deferrals':[{'reference':loc(P,'§35 마지막 문장; §38.12',702,794),'scope_ko':'post-T6.6 기기 성능; HOST cost/I25/Android durability 면제 없음'}],'authority_owner':None,'binding_change_applied':False}
save('normative-dependency-map.json',dependency)

transfers=[]
def transfer(i,cat,title,reference,scales,old,existing,missing,verify,aliases):
 transfers.append({'id':i,'tracking_id_policy_ko':'B11 추적 별칭이며 원 규범 ID가 아님','category':cat,'title_ko':title,'source_requirement_ids':[r['section'] for r in reference],'exact_normative_references':reference,'original_acceptance_criterion_ko':old,'required_workload_scales':scales,'workloads':['no-change','card','cash'],'required_source_runtime_identity':source,'required_fixture_identity':fixture,'existing_evidence':existing,'missing_evidence_ko':missing,'historical_failure_or_blocker_ko':'원 B03 N100k 정상 matched 계측 미확보; P03는 다른 역사 계측 source의 397146/400532·세 관측 만료·E3/E4 미완료. 원 B02 기능 성공은 비용 대체 불가. 현 accepted N100k baseline 존재를 인증하지 않음.','existing_deferral_authorization':None,'proposed_future_owner':{'stage':'T6.9-E','technical_role':'§36 D/E integration 및 §35 scaling 감사','assigned_person':None,'appointment_required_before_effective':True,'independent_acceptor':None},'deadline_or_blocking_milestone':'formal T6.6F exit 재심사 및 최종 T6.9 acceptance 중 먼저 도래하는 시점 이전; R1 activation/production도 계속 차단','verification_method_ko':verify,'consequence_if_incomplete_ko':'T6.9-E 수용 불가·Phase B 정량 상태 미완료·formal F/R1 activation/production 차단 지속. 행정 종결은 증거 수용이 아님.','proposed_transfer':True,'acceptance_semantics':{'quantitative_or_correctness_criterion_changed':False,'source_substitution_allowed':False,'evidence_timing_changed_if_approved':True,'administrative_completion_semantics_changed_if_approved':True,'proposal_changes_acceptance_semantics':True,'changed_scope_ko':'수집 시점·행정 상태만 변경; 정량/정확성 criterion과 원 source 범위는 유지'},'B10_aliases':aliases,'status':'UNVERIFIED' if '100K' in i else 'PARTIAL'})
for work,suffix in [('no-change','NC'),('card','CARD'),('cash','CASH')]:
 transfer('T35-100K-'+suffix,'C','N100k '+work+' 정상 비용',[loc(P,'§35',702),loc(P,'§38.12',794)],[100000],'고정 H/D에서 해당 workload를 반복하고 rows read/hashed·validated·written bytes/HTTP entity/RTT/memory/median/p95 실측. 전체 다섯 지점 곡선은 같은 source/fixture 경계.',['docs/benchmarks/t66f-b04/run-manifest.json','docs/benchmarks/t66f-b04/logical-costs.json','docs/benchmarks/t66f-b02-independent/summary.json'],'N100k 해당 정상 cell의 전체 지표·raw 반복·accepted generation E3/E4. 네 N의 실측을 외삽할 수 없음.','유효 accepted provenance 위에서 원 계측 ON 정상 실행; 독립 backend/native graph·행 digest와 E4/collector 종료 확인. 상기 metric별 결측은 수용 전 해소.',['GRID-100000-'+work,'COST-HASH','COST-VALIDATE','COST-WRITE','COST-MATCHED-GRID','COST-MEDIAN-P95','COST-RESOURCE'])
 transfers[-1]['workloads']=[work]
transfer('T35-ROWS','C','다섯 지점 rows-read 비교',[loc(P,'§35',702),loc(B,'§27',489,491)],[1000,5000,10000,50000,100000],'실제 backend/client SQL·반환 행·query plan·raw/index lookup 경계를 명시하여 다섯 규모 정상 비교를 완결.',['docs/benchmarks/t66f-b04/logical-costs.json','docs/benchmarks/t66f-b04/contract-matrix.json'],'기존 제한 반환 행/SQL 증거를 source·workload별로 연결하고 미계측 열을 실제 증거로 보완한 완결 rows-read 표. VM/pager/NAND 전수 계수는 새 의무가 아님.','보존 raw에서 정확히 복구 가능한 값은 경로/해시로 재집계. 나머지만 승인된 실행에서 수집; 반환 행을 모든 방문 행으로 광고 금지.',['COST-ROWS-READ'])
transfer('T35-NET','C','HTTP·RTT·headers·base64/JSON framing',[loc(P,'§15.3',315),loc(P,'§35',700,702),loc(P,'§38.12',794),loc(B,'§27',488)],[1000,5000,10000,50000,100000],'canonical·encoded/framed entity·HTTP headers 및 RTT dependency를 분리하고 full gzip과 같은 source/fixture 경계에서 비교.',['docs/benchmarks/t66f-b04/run-manifest.json','docs/benchmarks/t66f-b04/raw/n1000-v3/cash-2-on.json'],'실측 HTTP entity/요청 수가 있는 하위 N도 headers/framing/대조군 연결 전체가 완결된 것으로 보지 않음. 다섯 N 비교의 결측 열과 N100k 정상 전체.','method/path/상태/financial-aux·request/response entity·decoded bytes·base64/JSON·headers·RTT를 보존 원문에 결합; wire 미관측 값을 offline byte 계산으로 이름 바꿔 제출 금지.',['COST-HTTP-FRAMING'])
transfer('T35-GZIP','C','현 source/fixture의 full gzip 비교',[loc(P,'§35',700,702),loc(P,'§38.12',794),loc(B,'§27',494)],[1000,5000,10000,50000,100000],'full gzip을 비교군으로 유지하고 representative/less-repetitive에서 network/CPU/write 분리; base64/framing/compression CPU와 문자열 control 비교 보존.',['docs/t66f-phase-b-final-evidence-closure.md#12-compressionmedianp95','docs/benchmarks/t66f-b04/contract-matrix.json'],'과거 offline gzip6/Brotli4 다섯 점은 원 경계에 한정. 현재 segmented와 같은 source·fixture·Context의 full authoritative bytes 및 각 비교 열을 결합한 완결 증거.','gzip level6와 exact uncompressed SHA/length·codec 설정/버전·압축 bytes/CPU, decode/parse/validation·durable write를 따로 기록. 실제 HTTP가 아니면 offline으로 표기하여 wire 열 대체 금지. 다양성 fixture의 규모/입력은 실행 전 동결하고 같은 fixture끼리 비교.',['COST-COMPRESSION'])
transfer('I25-E3-100K','D','E3 large-N full-N 금지',[loc(P,'§36 I25',734),loc(P,'§35',702)],[100000],'steady-state full-N 작업 MUST NOT. 고정 H/D scaling의 실제 rows/bytes와 source 귀속으로 입증.',['docs/benchmarks/t66f-b04/logical-costs.json','docs/t66f-b04-phase-b-measurement-feasibility.md','docs/t66e3-independent-audit.md'],'원 B03 N100k 정상 세 workload의 E3Verify/Prepare/Commit counter 및 accepted publication/E4. 50k까지 36개 ON의 full-N 0으로 100k를 통과시킬 수 없음.','full_recoveries/full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds=0, tree/index/hot/changed rows·bytes·SQL·핀/CAS/readback을 단계별 귀속. cold/setup/recovery는 별도; guard 바로 다음 동기 COMMIT 유지.',['I25'])
transfer('I25-BOOKKEEPING-100K','D','D/E lease·GC·refcount hidden full-N 금지',[loc(P,'§38.7',789),loc(P,'§16',325),loc(P,'§16-S',382,384),loc(P,'§35',698,702)],[100000],'normal refresh에 lease/GC/refcount hidden O(N) 없음; flat P 목록/전체 graph mark 금지.',['docs/benchmarks/t66f-b04/logical-costs.json','docs/benchmarks/t66f-b10/evidence-review.json'],'N100k 정상 D/E 계측에서 root pin/bookkeeping/transfer 경계까지 full scan 부재를 직접 귀속하는 증거. maintenance full 검증은 정상 표본 밖으로 분리.','동일 정상 실행의 backend/client rows/bytes/path/pin/GC call과 source 경계를 결합; GC 자동 활성화·maintenance를 정상 counter에서 숨기기 금지.',['P7','I25'])
ids=[x['id'] for x in transfers]
other=[]
def obligation(i,cat,title,reference,old,scales,owner,missing,verify,consequence,status='UNVERIFIED',deferral=None):
 other.append({'id':i,'category':cat,'title_ko':title,'source_requirement_ids':[r['section'] for r in reference],'exact_normative_references':reference,'original_acceptance_criterion_ko':old,'required_workload_scales':scales,'required_source_runtime_identity':source if cat not in ['E','F'] else {'identity':'실제 선택한 R1/Android source·binary·driver·runtime; 원 B03 인증과 별개'},'existing_evidence':['docs/t66f-b10-independent-phase-b-closure-adjudication.md','docs/benchmarks/t66f-b10/requirements-evidence-matrix.json','docs/benchmarks/t66f-b10/residual-risk-register.json'],'missing_evidence_ko':missing,'historical_failure_or_blocker_ko':'B10에서 해당 범위 미검증 또는 부분 검증; 아래 개별 원 근거를 유지','existing_deferral_authorization':deferral,'proposed_future_owner':{'stage':owner,'assigned_person':None},'deadline_or_blocking_milestone':'해당 주장/수용/활성화 전; whole-F 항목은 formal F exit 전','verification_method_ko':verify,'consequence_if_incomplete_ko':consequence,'proposed_transfer':False,'acceptance_semantics':{'quantitative_or_correctness_criterion_changed':False,'evidence_timing_changed_if_approved':False},'status':status})
obligation('A-B02-FUNCTIONAL','A','N100k 비계측 기능 성공',[loc('docs/t66f-b02-independent-targeted-audit.md','§17–20',272,322)],'당시 source/환경의 실제 D→E/E3/E4·delta·restart 기능 증거',[100000],'기존 B02 CLOSED','이 범위의 새 결측 없음. 현 B03 instrumented cost로 승계하지 않음.','보존 원 summary/execution/final-state만 확인','재감사/이관 대상 아님','CLOSED')
other[-1]['required_source_runtime_identity']={'source_commit':'1cabf319f0ac2c2069e804b47cb527b55e3374db','source_report':'docs/t66f-b02-independent-targeted-audit.md','runtime':'원 B02 execution/environment 범위; B03와 동일 인증이라고 주장하지 않음'}
obligation('B-COLD-100K','B','원 B03 instrumented full cold 성공 미검증',[loc(P,'§18',407,415),loc(P,'§35 O(N) 예외',694)],'cold O(N) 허용; 모든 N의 instrumented cold 성공은 독립 MUST가 아님',[100000],'역사 증거 보존','최종 IR07 원 B03의 성공 미검증; P03는 다른 source에서 실패.','성공 주장하려면 별도 승인된 실제 complete acquisition→E3/E4 증거. 정상 비용에는 다른 적법 baseline/provenance 가능.','역사 실패 유지·재cold NO-GO; 단독 formal closure blocker로 새로 만들지 않음')
obligation('E-DEVICE-PERFORMANCE','E','기기 memory/전력/thermal/latency',[loc(P,'§35 마지막 문장',702),loc(P,'§38.12',794)],'단말 성능 gate는 post-T6.6; HOST를 phone 결과로 표현 금지',None,'post-T6.6 Real-Device Gate','실제 단말 성능·메모리·전력/thermal 미검증; 숫자 합격선·담당자 미지정.','실제 기기·선택 binary의 후속 승인 gate; runbook 주 대상 S23 FE/One UI8.5는 최소 RAM/SLA 정의가 아님.','기기 PASS 주장 불가; 이 제안으로 실행 승인 없음',deferral={'clauses':['§35 마지막 문장','§38.12'],'scope':'기기 성능 단계 분리만'})
obligation('F-ANDROID-DURABILITY','F','Android VFS·I/O·power-loss·previous recovery',[loc(P,'§26',533,541),loc(P,'§38.8',790)],'실제 driver pragmas/VFS·native fence·process death/disk-full/corruption/GC·전원 손실 범위 검증; 지원/검증 없으면 rollout 차단',None,'native store·선택 driver / 별도 gate','HOST DELETE/EXTRA·SIGKILL로 대체 불가. isolated Phase B 이전의 정확한 배치 시점은 원문에 없음.','실제 Android binary/driver/하드웨어 proof','whole-F proof 미완료·rollout 차단 지속')
obligation('F-RECOVERY','F','큰 restore/MW atomic recovery',[loc(P,'§31',612,641),loc(P,'§36 I23',732),loc(P,'§38.10',792)],'chunk/hash/quota/backup/idempotent receipt/Apply(B,J) 한 transaction/epoch; 작은 dataset 예외도 worst budget·명시 승인 필요',['>26214400B 복구 경계; 명문상 다섯 N 실행 수 없음'],'R1 구현·독립 recovery 감사','large native Frozen-B installation·chunk recovery budget·atomic commit/status proof 미완료.','해당 R1 contract 독립 검증','R1 구현 완료/activation 및 전체 F 통과 주장 불가')
obligation('F-MIGRATION','F','legacy·old B/J/pending·migration/rollback',[loc(P,'§29',585,593),loc(P,'§33',651,659),loc(P,'§38.9',791),loc(P,'§37 사례31',772)],'정확한 legacy materialization·source pin·ONLINE/no active J/pending·atomic discriminator·rollback compatibility',None,'R1 및 transition 감사','지원된 일부 HOST materialization과 미완료 R1 전이 proof를 구별.','migration interrupted/rollback·legacy hashes/ID/lineage·old binary compatibility','whole-F proof 미완료·activation 차단')
obligation('F-BACKUP','F','backup/artifact 30·GC·storage pressure',[loc(P,'§32',643,649),loc(P,'§36 I24',733),loc(P,'§38.11',793)],'30 standalone backup/artifact 의미·active/frozen/pending pins·ENOSPC/GC/repair 실패 보존',None,'R1·backup/GC integration','원 일부 HOST pins 증거로 retention/transition 전체를 통과시킬 수 없음.','실제 selected source의 30개·storage exhaustion/frozen repair·GC 경계','whole-F proof 미완료·activation 차단')
obligation('F-WHOLE-EXIT','F','whole-F 통합 proof·승인 순서',[loc(P,'§34',665,681)],'R1→interop/full-resync/crash→성능→독립 F 감사→명시 rollout 승인',None,'독립 통합 감사 / 권한 확인된 승인자','위 비용·I25·R1·Android를 모두 수용한 전체 F 증명과 명시 rollout 승인이 없음.','각 선행 의무를 identity별 join한 새 판정; 행정 종결과 구별','formal F NOT AUTHORIZED, R1 CLOSED, production NOT AUTHORIZED')
obligation('SOURCE-REQUALIFICATION','F','변경 source·runtime 재자격',[loc(P,'§4',68,70),loc(P,'§23',490,496),loc(P,'§25',519,531)],'다른 semantics를 old hash로 광고 금지; validator 변경에 호환 proof 없으면 full revalidation',None,'향후 source별 독립 검토','미래 source 미선택. payload/engine/binary/driver/계측/runtime 변경 영향 검증 미수행.','변경 inventory·exact release/admission·계측 oracle 및 영향 correctness/provenance/fence/복구 재검증. 성능 주장엔 새 source 다섯 점 곡선.','기존 인증 자동 승계 불가; 새 source 결과는 원 B03 이관 의무를 소거하지 않음','CONDITIONAL')
# 모든 B10 미완료 행을 보존하고 canonical 의무로 연결한다.
open_rows=[x for x in b10['rows'] if x['verified_result'] in ['PARTIAL','UNVERIFIED','FAIL']]
coverage=[]
for row in open_rows:
 i=row['id']
 targets=[x['id'] for x in transfers if i in x['B10_aliases']]
 if i in ['S34','S35','S38','P12']: targets+=ids
 if i in ['S34','S38','P12']:targets+=['F-WHOLE-EXIT']
 if i in ['S26','P8','DEVICE-F-STAGE']:targets+=['F-ANDROID-DURABILITY']
 if i in ['S31','I23','P10','N32','E4-FROZEN-LARGE','R1-F-DEPENDENCY']:targets+=['F-RECOVERY']
 if i in ['S29','S33','P9','N31']:targets+=['F-MIGRATION']
 if i in ['S15']:targets+=['F-RECOVERY','F-MIGRATION']
 if i in ['S32','I24','P11']:targets+=['F-BACKUP']
 if i=='DEVICE-PERFORMANCE':targets+=['E-DEVICE-PERFORMANCE']
 if i=='COLD-100K-INSTRUMENTED':targets+=['B-COLD-100K']
 if i in ['S34','S38']:targets+=['F-ANDROID-DURABILITY','F-RECOVERY','F-MIGRATION','F-BACKUP']
 assert targets,i
 coverage.append({'B10_id':i,'B10_row_preserved':row,'canonical_obligation_ids':sorted(set(targets)),'coverage_policy_ko':'parent/metric/scale 별칭은 중복 의무 추가가 아님; 혼합 parent의 비이관 하위 의무도 유지'})
contract={'scales':[1000,5000,10000,50000,100000],'workloads':['no-change','card','cash'],'numeric_H_D_sample_latency_policy':'원 규범에 없는 값은 새 상수로 발명하지 않는다. 동일 fixture의 실제 H bytes/rows, D, warmup/n/estimator/IQR를 실행 전 명시하고 freeze.','source':source,'fixture':fixture,'instrumentation':'IR07 인증 범위의 B03 ON; guards 유지, 미지원/불완전 측정은 실패/미검증. OFF는 overhead 대조용일 뿐 ON cost 대체 불가.','metrics':metrics,'baseline_admission_ko':'완전 accepted baseline·11 table·hash/graph/global index·validation receipts·NS/principal/Versions/Target·same connection provenance·generation을 독립 검증. 사용 가능한 N100k accepted DB는 아직 인증하지 않음. 새 source receipt로 옛 source를 가장하거나 counts만으로 복구 금지.','real_path_ko':'실제 authenticated D3→HTTP/TLS→Flutter E2/E1→AppState의 E3Verify/Prepare/Commit→accepted readback→E4. 준비/discard/ASGI/backend-only는 완료 cell 대체 불가. no-change accepted ID/sequence 유지도 정상 완료로 기록; mutation은 실제 변경 generation 확인.','independent_correctness_ko':'backend 실제 raw rows·presenters/context·native client complete graph/행 digest·hash/root·SQLite FK/readback와 E4를 대조. 모바일 금융 엔진 재계산 추가 없음. 원 closed correctness는 material 반증 없이 재개하지 않음.','I25_counters':['full_recoveries','full_verifications','full_raw_rows','full_fact_rows','canonical_full_builds'],'guard':'final authority fence 직후 동기 COMMIT; 사이 callback/hook/await 삽입 금지','full_gzip_method_ko':'원 B03의 같은 DB state/Context·projection과 대응하는 legacy full authoritative response exact bytes를 별도 비교군으로 freeze. gzip6(역사 비교 codec 설정, 새 제품 기능 아님) 입력 SHA/길이·codec/version·compressed bytes·CPU를 남김. representative/less-repetitive는 같은 family끼리 비교하며 규모·문자열 분포를 실행 전 명시. 과거 A의 108916B/다양성568847B 및 과거 다섯 점/Brotli4는 역사 칸으로 남기고 현 matched wire/CPU/write 열에 넣지 않음. 실제 HTTP 미수집이면 offline으로 표시하고 wire 수용은 별도 필요.','reuse_policy_ko':'동일 source/runtime/fixture 경계의 B04 4점은 실제 raw/manifest 해시로만 재사용. raw에 없는 metric은 null과 사유를 유지하고 수용 전 보완. 4+추정100k 금지.','source_change_policy_ko':'원 B03 이관 의무는 원 B03 source 및 지원 runtime에서만 수용. 다른 source는 원 의무를 대체하지 못함. 미래 최종 source의 성능 인증은 그 source 전체 다섯 점·same H/D와 독립 영향 재자격으로 별도 수립. 두 source의 financial state 동등성은 engine 동등성 증명이 아님.','new_cold_required':False,'later_source_can_discharge_original_without_B03_evidence':False,'later_same_B03_normal_evidence_can_discharge_without_fresh_B03_cold':True,'limits':{'observation_TTL_seconds_max':900,'existing_client_attempts':3,'existing_client_observations':3,'principal_max_available_leases':4,'policy':'900초 또는 기존 attempt/observation 수를 늘려 historical 비교 실행을 만들 수 없음. 네 Available와 세 client attempt는 다른 제한.'},'artifacts_ko':'command/cwd/exit/time·source/runtime/binary·fixture/Target/before-after accepted·개별 raw/실패/취소·counter·HTTP·표본·manifest SHA/mode/size를 보존. 일관 backend/client SQLite snapshot이 재검증에 필요하면 supported backup API로 보존 후만 task-owned disposable 정리. 유일한 matched DB를 먼저 삭제하지 않음.','failure_ko':'결측/중단/expired/incomplete collector는 PASS가 아니며 해당 cell 미수용. full-N 관측은 원인 귀속과 구현 거부/별도 수정·재자격 대상; 자동 waiver·더 큰 TTL·무제한 반복 금지. 전체 F/activation/deployment 차단 지속.','blocking_milestone':'T6.9-E 전 의무 독립 수용→formal F exit 재심사; 최종 T6.9 acceptance/R1 activation/production은 그 전에 불가.'}
save('transfer-obligation-register.json',{'schema_version':1,'task':'T6.6F-B11','proposal_status':'DRAFT ONLY — NOT APPLIED','authority_policy':'I1–I25만 원 invariant ID. T35/I25-E3 등은 B11 추적 ID.','transferred_obligation_ids':ids,'obligations':transfers+other,'B10_incomplete_row_count':len(open_rows),'B10_incomplete_row_coverage':coverage,'future_acceptance_contract':contract,'current_phase_B':'INCONCLUSIVE','formal_T66F_closure':'NOT AUTHORIZED'})

options=[{'id':1,'name_ko':'현행 유지','recommendation':'대안','normative_change':False,'phase_B_status':'INCONCLUSIVE / formal closure BLOCKED','cost_ko':'원 source에서 100k 정상 3 workload 및 전체 rows/network/gzip 결측 열을 기존 Phase B 안에서 확보해야 함. 적법 baseline 존재/취득 비용 미확정; cold 재시도는 자동 필수/허가 아님.','advantages_ko':'기존 요구와 순서 그대로; 새 entry·owner 계약 불필요','risks_ko':'현 측정 실현성 미해결로 제한 작업 종결·후속 증거 수집 계획이 계속 묶임','minimum_evidence_ids':ids,'R1_activation':'CLOSED','production':'NOT AUTHORIZED'},
{'id':2,'name_ko':'좁은 조건부 이관만 명시','recommendation':'단독 채택 비권고','normative_change':True,'phase_B_status':'승인 문구가 있으면 행정 종결 가능; 정량 INCONCLUSIVE','cost_ko':'위 8개만 T6.9에 할당; 증거 의무와 합격 기준은 동일','advantages_ko':'작업 단위와 증거 수용을 분리','risks_ko':'T6.9 상세 entry/소스/owner 미지정이면 F→T6.9→F 순환·새 source 대체·후속 구현의 PASS 오독 가능','safe_without_option3_safeguards':False,'R1_activation':'CLOSED','production':'NOT AUTHORIZED'},
{'id':3,'name_ko':'보호 조건을 포함한 이관','recommendation':'RECOMMENDED — 승인 전 미효력','normative_change':True,'phase_B_status':'유효 승인과 책임 배정 후만 ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED; 정량 INCONCLUSIVE 유지','cost_ko':'동일 8개 의무 + T6.9-E collection-only entry·원 source 제한·독립 수용·hard gate·명시 서명 기록','advantages_ko':'순환을 수집 전용 예외로 해소하고 original-source proof와 미래 제품 certification을 분리. 실패 시 구현 거부 가능','risks_ko':'일정 지연·owner 미배정·baseline 부재·계측 overhead·dual-source 비용은 해결되지 않음. 책임 수락과 별도 실행 GO 필요','safeguards':['원 B03 source/runtime/fixture 유지','T6.9-E collection-only 선행 진입 명시','원 의무 타 source 대체 금지','formal F/최종 T6.9/R1 activation/production 차단','기명 owner·independent acceptor·milestone/보고 의무','후속 T6.7/8 자동 entry 불허·legacy 경로 보존'],'R1_activation':'CLOSED','production':'NOT AUTHORIZED'}]
save('option-comparison.json',{'schema_version':1,'task':'T6.6F-B11','options':options,'recommended_option':3,'technical_feasibility':'CONDITIONAL','historical_claims_rewritten':False,'criteria_weakened':False,'completion_timing_and_administrative_semantics_changed_if_approved':True})

# 정확한 원문은 저장소에서 잘라 넣는다. 삭제는 없고 모두 미적용 추가문이다.
amendments=[]
def amend(i,path,section,start,end,addition,reason,effect):
 amendments.append({'id':i,'target_path':path,'target_section':section,'operation':'ADD_AFTER — EXISTING TEXT UNCHANGED','current_normative_statement':quote(path,start,end),'current_reference':loc(path,section,start,end),'proposed_addition_ko':addition,'reason_ko':reason,'effect_on_required_evidence_ko':effect,'effect_on_completion_ko':'유효 승인 후 명시 범위의 행정 종결/수집 시점만 변경; 정량 수용·formal F·activation·deployment와 분리','required_authorized_approval':'APPROVAL AUTHORITY NOT ESTABLISHED — EXPLICIT USER/PROJECT OWNER DECISION REQUIRED. 아래 승인 조건을 충족한 별도 기록 필요.','rollback_or_rejection_ko':'미승인/거절이면 원문 그대로. 승인 후 철회/조건 위반이면 transfer administrative status를 중단/철회하고 원 gate를 복원; 생성 증거·실패 이력은 보존.','applied':False})
text34='''### 34-B11. 제한 Phase B 행정 종결과 증거 이관 — 승인된 경우에만 효력

이 예외는 T66F-B11-TRANSFER-01의 별도 유효 승인 기록이 있는 경우에만 적용한다(MUST). 대상은 원 B03 source의 T35-100K-NC, T35-100K-CARD, T35-100K-CASH, T35-ROWS, T35-NET, T35-GZIP, I25-E3-100K, I25-BOOKKEEPING-100K의 미완료 증거 수집뿐이다. 이 ID는 본 예외의 추적 ID이며 기존 I25 등 규범 ID를 대체하지 않는다.

승인자는 권한 근거와 실제 승인자·일시·승인 대상 exact 문서 SHA 및 8개 의무, T6.9-E 기명 책임자와 독립 증거 수용자, hard blocking milestone, 보고 책임·위험 수락 범위를 한 결정 기록에 명시해야 한다(MUST). 누락·pending·draft·이의 없는 침묵은 유효 승인이 아니다(MUST NOT). 승인 자체는 새 benchmark/최적화/기기 실행·소스 변경 허가가 아니며 실행은 별도 계획·기존 제한의 명시 GO를 필요로 한다.

유효 승인 뒤 bounded work package는 완료, Phase B 행정 상태는 ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED로 기록할 수 있다. 동시에 Phase B 정량 증거 상태는 INCONCLUSIVE, 다섯 점은 PARTIAL, N100k 정상/I25는 UNVERIFIED로 유지해야 한다(MUST). 이 상태는 quantitative PASS 또는 formal T6.6F CLOSED가 아니다.

§35-T69의 증거 수집 전용 T6.9-E에 한해 formal F exit 전에 진입하도록 순서를 조정한다. R1 구현 proof·interop/full-resync/crash 및 다른 선행 의무는 제거하지 않는다. 모든 이관 의무의 독립 수용과 나머지 §26/31/32/33/34, I23/I24, §38.8–11 whole-F proof가 충족될 때까지 formal T6.6F exit 재심사를 통과시킬 수 없다(MUST NOT). 최종 T6.9 수용도 그 전에 완료로 표시할 수 없다.

T6.7/T6.8 구현·cleanup은 행정 종결을 PASS나 자동 entry로 사용할 수 없다(MUST NOT). 본 예외는 그 작업을 승인하지 않으며, 기존 legacy full consumer/store와 복구 경로를 제거할 근거가 아니다. T6.9-E 수집은 T6.7/8 구현 완료나 사용자 활성화를 요구하지 않는 격리 subgate다. 독립적인 R1 구현 작업 단계와 R1 사용자 활성화는 별개이며, R1 활성화·segmented rollout·production deployment는 전체 proof와 별도 명시 승인이 있을 때까지 계속 차단한다.

이관 누락·실패·수행 불능을 이유로 요구를 소거하거나 자동 연장/수용할 수 없다(MUST NOT). 책임자는 차단 상태와 증거를 기록하고 승인권자에게 보고해야 한다. 철회/조건 위반이면 행정 종결 효력을 중단하고 원 종결 gate를 복원한다. 후속 결과는 그 날짜/source의 새 증거이며 과거 실패·미측정 상태를 다시 쓰지 않는다.'''
text35='''### 35-T69. 이관 증거의 필수 완료 계약 — 승인된 경우에만 효력

§34-B11의 유효 승인 아래 T6.9-E는 아래 8개 미완료 의무를 인수하고 독립 수용 기록을 제출해야 한다(MUST). 수집 기한은 formal T6.6F exit 재심사 및 최종 T6.9 acceptance 중 먼저 도래하는 시점 이전이며, R1 활성화/rollout/production도 계속 차단한다. 날짜가 미정이라는 이유로 milestone 차단을 생략할 수 없다.

- T35-100K-NC/CARD/CASH: N=100000의 no-change/card/cash 정상 rebuild를 반복하여 §35의 rows read/bytes hashed·validated·written/HTTP entity/RTT/memory/median/p95를 실제 측정한다. D1–D3 generation/request, E1/E2, E3Verify/Prepare/Commit, E4 범위를 분리한다.
- T35-ROWS: N=1000/5000/10000/50000/100000의 세 정상 workload에 대해 실제 SQL/반환 행·raw/index lookup·query plan 경계의 결측 열을 보완하여 완결 비교를 제출한다. 반환 행을 모든 VM/pager 방문 행으로 표현하지 않는다.
- T35-NET: 동일 다섯 규모/workload에서 method/path·금융/auxiliary·request/response entity·decoded canonical bytes·base64/JSON framing·headers·RTT dependency/cache misses를 full 비교군과 결합한다. 4×ceil(decoded/3)의 산술은 실제 HTTP wire 관측의 대체가 아니다.
- T35-GZIP: 같은 source/DB state/Context·fixture의 full authoritative response를 full gzip 비교군으로 유지하고 representative/less-repetitive 문자열에서 network/codec CPU/parse·validation/write를 분리한다. 역사 gzip6과 대응하려면 codec level6·버전·입력 SHA/길이·압축 bytes/CPU를 기록한다. Brotli4 등 과거 비교 수치는 원 범위로 보존하며 새 matched wire 수치로 바꾸지 않는다. 오프라인 compression은 그렇게 표시하고 미관측 HTTP/RTT/headers를 채우지 못한다. 다양성 fixture의 규모·문자열 분포도 사전 계획에서 고정하며 서로 다른 family/입력을 한 곡선으로 합치지 않는다.
- I25-E3-100K: N100k 세 정상 workload의 E3Verify/Prepare/Commit rows/bytes·SQL·tree/index/pin/CAS/readback 귀속과 full_recoveries/full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds=0을 직접 입증한다. 초기/재시작/명시 full recovery는 정상 counter 밖의 별도 workload다.
- I25-BOOKKEEPING-100K: 같은 N100k 정상 D/E 흐름의 lease/GC/refcount/root pin/transfer bookkeeping에 hidden full graph/history scan이 없고 control에 flat P 목록이 없음을 source와 직접 counter로 입증한다. 명시 maintenance O(N/P)를 정상 refresh 안으로 숨기지 않는다.

원 B03의 base commit ebcbd54d90eeee194a04b9eea6367f446ee2fd28, canonical payload 8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8, engine 7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c, archive fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5를 기준으로 한다. runtime은 IR07/B04 지원 CPython3.12.3/backend SQLite3.45.1/Flutter3.47.4/Dart3.13.3/client SQLite3.53.4 및 안정된 monitoring 설정이다. payload/engine/archive/runtime의 의미를 혼동하거나 live 실험 tree를 기준으로 선택하지 않는다(MUST NOT).

H/D 숫자·표본 수·절대 latency 상한은 기존 규범에 없으므로 발명하지 않는다. 원 B04 재사용 구성은 seed662602·평가일2026-10-05·offset540·current ledger105·다른 table35·초기 hot87364B/control3178B, no-change D0/card·cash UPDATE D1이다. N label=ledger 총 N, 전체 authoritative rows=N+35를 명시한다. 각 scale의 실제 fixture SHA/행/descriptor/NS/Target/변경 전후 입력을 freeze한다. 기존 4점과 이어 붙이는 N100k는 동일 H/D·문자열/descriptor·변경 규칙임을 독립 대조해야 한다. B04 raw에 실제 존재하는 동종 metric만 재사용하고 결측은 수용 전 보완한다. 새 fixture/다른 H/D가 필요하면 별도 곡선이며 원 이관 의무를 대체하지 못한다.

계측은 IR07 범위의 B03 ON이며 source-SHA·monitoring/lifecycle/ownership/byte/SQL guards를 유지해야 한다(MUST). hash 실제 sink(domain/NUL·반복 포함), primary submitted/completed/failed span, SQL NEW TEXT UTF8/BLOB attempted/effective/committed/rollback·scalar/row를 구별한다. 미지원 환경/불완전 collector·취소·실패를 성공 0으로 제출하지 않는다. OFF·backend-only·ASGI·prepare/discard·다른 source의 기능 PASS는 ON 완료 cell의 대체가 아니다. warmup/n/median/p95 estimator/IQR·계측 교란/메모리 관찰 한계를 공개한다.

수집 전 독립 admission은 source/runtime/fixture·instrumentation 지원과 완전 accepted baseline/provenance를 확인해야 한다(MUST). 이 개정은 사용할 수 있는 N100k DB가 이미 있음을 인증하지 않는다. §18/23–25에 따라 complete objects/11 tables/global index/receipt/NS/principal/Versions/Target/same-connection provenance/generation을 확인한다. 적법 baseline을 확보하지 못하면 수집 차단을 기록한다. 새로운 instrumented full cold 성공은 별도 MUST로 추가하지 않으며, 적법 baseline 위의 원 B03 정상 증거로 이관 의무를 수용할 수 있다. 새 cold가 필요해지면 기존 NO-GO를 별도 명시 계획/허가 없이 뒤집지 못한다.

실제 authenticated D3→HTTP/TLS→Flutter E2/E1→원 AppState guard의 E3 accepted publication/readback→E4가 완료되어야 한다(MUST). no-change에서 ID/sequence가 그대로인 정상 완료와 mutation의 실제 generation 전진을 구별한다. backend 실제 rows/presenters·native complete graph/값 digest·SQLite FK·hash/root·accepted before/after를 독립 대조한다. 모바일 canonical 금융 엔진을 추가하지 않는다. E3 마지막 authority guard 바로 다음의 동기 COMMIT 사이에 await/hook/callback을 넣지 않는다.

§16 TTL 최대900초, 기존 client attempts3/observations3와 principal Available 최대4의 서로 다른 제한을 보존한다. 관측 수명이나 횟수를 늘려 과거와 비교 가능한 실행을 만들지 않는다(MUST NOT). 50k를100k로 외삽하거나 부분 N을 다섯 점 PASS로 바꾸거나 uninstrumented 기능으로 실패 계측을 대체할 수 없다. B05/B08 실험 최적화 채택, 금융 canonical data·source guard·release/admission 변경은 이 예외에 포함되지 않는다.

command/cwd/exit/time·source/runtime/binary·fixture/Target/accepted before/after·stage 완료·raw samples/counters/HTTP·실패/취소·manifest SHA/mode/size를 보존해야 한다(MUST). 재검증에 필요한 일관 backend/client SQLite snapshot은 supported backup API로 보존하고 검증하기 전 유일한 matched 자료를 삭제하지 않는다. docs/development-artifact-hygiene.md에 따라 검증된 task-owned disposable만 정리한다.

다른 engine/source/runtime의 나중 결과는 해당 미래 source의 주장만 성립시키며 원 B03 8개 의무를 소거하지 못한다(MUST NOT). 새 source를 채택/인증하려면 별도 승인·exact release/admission·변경 영향 계측 oracle/정확성/구조·provenance·authority fence·durability/legacy 복구 재검증과 그 source의 전체 다섯 점 곡선이 필요하다. 호환 proof 없는 validator/schema 변경은 §23에 따라 full revalidation한다. 금융 데이터 동등성은 engine 동등성이 아니다. 원 closed B01/B02/B03 감사는 material 반증 없이 재개하지 않으며 IR07 인증을 새 source로 자동 이전하지 않는다.

모든 metric/workload/scale 및 8개 의무가 원 source·경계에 맞게 완결되고 독립 수용자가 근거/해시/한계를 기록해야 T6.9-E EVIDENCE ACCEPTED를 발급할 수 있다(MUST). 결측·불완전 실행은 PARTIAL/UNVERIFIED, 실제 full-N 위반은 귀속된 구현 거부/별도 수정·재자격 사유이며 자동 waiver가 아니다. 정량 비용은 새 ms 목표로 채점하지 않고 기존 full-N 금지/bounded 경로와 측정 완결성을 적용한다. 모든 결과는 그 날짜/source의 후속 판정이며 역사 P03 FAIL·B04 4/5·B10 Option D를 소급 PASS로 바꾸지 않는다. T6.9-E 수용은 formal F 재심사의 필요조건일 뿐 R1/Android proof·기기 gate·별도 rollout/deployment 승인의 충분조건이 아니다.'''
text36='''I25의 steady-state full-N 작업 금지 및 D/E instrumented rows/bytes 의무는 계속 적용한다. §34-B11의 유효 승인이 있는 경우에만 §35-T69에 열거된 I25-E3-100K 및 I25-BOOKKEEPING-100K의 미완료 증거 수집 시점을 T6.9-E로 옮긴다. 이것은 I25 준수 의무의 일시 중지, 실제 위반 허용 또는 현재 PASS가 아니다. E3 즉시 guard-before-COMMIT, 필수 counters/귀속·proof 및 independent source-qualified acceptance를 유지한다.'''
text38='''위 7·12의 필수 proof 중 §35-T69가 지정한 8개 의무의 아직 비어 있는 증거 수집 시점만 §34-B11의 유효 승인 아래 T6.9-E로 이관할 수 있다. 완전한 다섯 점·rows/bytes/HTTP/framing/full gzip 및 I25 증명을 없애거나 추정으로 채울 수 없다. 8–11의 Android durability·legacy/migration·recovery·30 backup/artifact/GC 의무는 이 예외의 대상이 아니며 기존 whole-F/rollout 차단을 유지한다. 12의 기존 post-T6.6 실기기 성능 단계 분리도 그대로다. 구현 proof 실패는 796행의 원칙대로 해당 구현/rollout 차단과 별도 명세 변경 감사를 필요로 한다.'''
textB='''이 도식의 F 이후 T6.9 배치는 최종 수용 순서를 유지한다. 단, T6.6C §34-B11 및 §35-T69의 별도 유효 승인이 있는 경우 그 조항의 8개 원 B03 의무를 수집하는 격리 T6.9-E subgate에 한해 formal F exit 전에 진입할 수 있다. T6.9-E entry는 bounded 작업 인계·기명 owner/독립 수용자·source/fixture/runtime/계측·accepted provenance 사전심사와 별도 실행 GO를 요구한다. 전체 F PASS·R1 활성화·T6.7/8 완료를 수집의 전제로 요구하지 않지만 이들의 구현/활성화를 승인하지도 않는다. 최종 T6.9 acceptance, formal F exit 및 rollout/deployment에는 이관 증거의 독립 수용과 나머지 선행 gate가 여전히 필요하다. §27의 confirmed-heavy/한 달 hot 대량·initial/full/restore/crash 등 기존 T6.9 감사 방향은 이 8개 의무에 흡수하거나 면제하지 않는다. 상세 T6.9 명세가 별도로 제정되면 이 계약과 기존 범위를 명시적으로 수록·대조해야 하며, 현재 독립 상세 명세가 존재한다고 가정하지 않는다.'''
amend('AM01',P,'§34',665,679,text34,'상태 이름과 수집 전용 entry·hard gate를 명문화하여 행정 종결 오독과 순환 방지','8개만 시점 이관; R1/Android/whole-F 그대로')
amend('AM02',P,'§35',698,702,text35,'현재 T6.9 상세 인수 계약 부재를 정확한 원 source 완료 계약으로 보충','다섯 점 및 모든 metric/비교 의무 유지; cold를 별도 MUST로 추가하지 않음')
amend('AM03',P,'§36 I25',734,734,text36,'I25 불변과 증거 수집 시점 변경의 구별','금지/필수 counter/guard 불변')
amend('AM04',P,'§38.7–12 뒤',789,796,text38,'7/12와 8–11의 이관/비이관을 분리','device 성능 기존 분리만 유지; Android proof/R1 면제 없음')
amend('AM05',B,'§29 도식 뒤',513,530,textB,'F 이후 T6.9의 상위 도식과 수집 전용 예외의 관계 명확화','기존 T6.9 방향 유지·상세 인수/entry를 C 부록에 제정')
prohibitions=['B03 guards 비활성화','E3 guard→COMMIT 의미 변경','I25 counters/proof 삭제','subset grid·extrapolation의 PASS 승격','TTL/attempt 증가로 historical 비교 제조','비계측 기능으로 실패/미계측 비용 대체','실기기 미실행의 device PASS','B05/B08 채택','source-SHA guards 완화','canonical 금융 data 변경','R1 활성화','production deployment','과거 실패/미측정의 소급 성공 처리']
record={'schema_version':1,'task':'T6.6F-B11','change_id':CHANGE,'status':'DRAFT ONLY — NOT APPLIED','binding_protocol_modified':False,'T69_specification_modified':False,'recommended_option':3,'amendments':amendments,'transferred_obligation_ids':ids,'future_acceptance_contract':contract,'explicit_prohibitions_ko':prohibitions,'acceptance_criteria_weakened':False,'completion_semantics_changed_if_approved':True,'approval_authority':None,'required_authority_statement':'APPROVAL AUTHORITY NOT ESTABLISHED — EXPLICIT USER/PROJECT OWNER DECISION REQUIRED.','activation_conditions_ko':['권한 근거/승인자/일시/개정 exact SHA·8개 의무를 명시한 별도 승인','기명 T6.9-E 책임자·독립 증거 수용자·hard milestone·보고 의무 및 위험 수락','AM01–05를 한 일관된 변경으로 별도 적용·검토; 원문 drift면 재심사','실행 전 source/runtime/fixture/계측/정당 baseline 사전심사·별도 실행 GO'],'follow_up_not_performed_ko':'명시 승인 후 별도 문서 적용 작업에서 AM01–05 및 실제 발견되는 T6.9 governing 문서의 정합을 검토·적용하고, 수집 실행은 별도 승인된 계획에서 진행한다.','rejection_effect_ko':'binding 문서 불변; 현 Phase B INCONCLUSIVE/formal F NOT AUTHORIZED 유지. Option1의 증거 의무가 기존 Phase B gate에 남음.'}
save('proposed-amendment-record.json',record)
auth={'schema_version':1,'task':'T6.6F-B11','change_id':CHANGE,'B11_verdict':'PASS — NARROW TRANSFER PROPOSAL READY FOR AUTHORIZATION','proposal_review_succeeded':True,'recommended_option':3,'current_blocked_status':{'B10':'OPTION D — BLOCKED','phase_B':'INCONCLUSIVE','formal_T66F':'NOT AUTHORIZED','R1_activation':'CLOSED','production':'NOT AUTHORIZED'},'reason_ko':'현행은 필수 정상 비용/I25·비교 열 미완료로 종결 불가. 큰 cold 반복/미채택 최적화 없이 책임 있는 후속 증거 수집의 시점·entry만 분리하기 위한 규범 결정안.','transferred_obligation_ids':ids,'remaining_nontransfer_obligation_ids':[x['id'] for x in other if x['id']!='A-B02-FUNCTIONAL'],'technical_risks_ko':['100k 정상 계측·적법 baseline 확보 실현성 미입증','계측 교란과 후속 운영 일정 지연','행정 종결을 PASS로 잘못 소비하는 위험','owner/milestone 불명확하면 무기한 미이행 가능'],'source_version_risks_ko':['원 B03·live B05-A·B08/B09는 다른 identity','새 source 결과로 원 이관 의무 대체 불가; 두 트랙 비용 가능','runtime/monitoring·validator/driver 변경 시 영향 재자격'],'review_prerequisites_ko':['실제 승인 권한 확인','AM01–05와 8개 의무/비이관 whole-F 대조','기명 수집 책임자·독립 수용자와 milestone/보고 의무 수락','현재 원문 SHA와 개정안 SHA를 approval 기록에 결합'],'approval_authority':None,'approval_authority_status':'APPROVAL AUTHORITY NOT ESTABLISHED — EXPLICIT USER/PROJECT OWNER DECISION REQUIRED.','explicit_approval':'NOT GRANTED','approved_by':None,'approved_at':None,'risk_acceptance_issued':False,'draft_preparation_is_approval':False,'effect_of_rejection_ko':record['rejection_effect_ko'],'effect_of_approval_ko':'조건을 충족해 별도 적용된 경우에만 Phase B 행정 종결 및 T6.9-E 수집 전용 entry 허용. 정량 INCONCLUSIVE·formal F/activation/deployment 차단 유지. 이 기록은 실행 GO가 아님.','follow_up_implementation_task_not_performed_ko':record['follow_up_not_performed_ko'],'next_action_ko':'사용자 또는 프로젝트 소유자는 T66F-B11-TRANSFER-01의 보호 조건부 이관안과 승인 권한 근거·기명 책임자·독립 수용자·차단 마일스톤을 하나의 명시적 결정으로 승인하거나 거절하십시오.','reviewer_independence':'SATISFIED','independence_limit_ko':'제공된 이력상 B01–B10 구현/감사 참여 없는 새 세션; 외부 인적 정체나 UI reasoning 설정 검증 주장은 하지 않음. 위임 없음.','new_full_cold_runs':0,'regression_suites_run':0,'real_device_execution':'DEFERRED','commit':'NONE','push':'NOT PERFORMED'}
save('authorization-decision.json',auth)

inputs=['AGENTS.md','docs/project-state.md','docs/domain-model.md','docs/known-issues.md','docs/architecture.md','docs/development-artifact-hygiene.md',P,B,A,'docs/runbook.md','docs/t66f-b10-independent-phase-b-closure-adjudication.md','docs/benchmarks/t66f-b10/requirements-evidence-matrix.json','docs/benchmarks/t66f-b10/residual-risk-register.json','docs/benchmarks/t66f-b10/closure-decision.json','docs/benchmarks/t66f-b10/handoff-conditions.json','docs/benchmarks/t66f-b10/source-certification-boundaries.json','docs/benchmarks/t66f-b10/evidence-review.json','docs/t66f-b04-phase-b-measurement-feasibility.md','docs/benchmarks/t66f-b04/run-manifest.json','docs/benchmarks/t66f-b04/contract-matrix.json','docs/benchmarks/t66f-b04/source-identity.json','docs/benchmarks/t66f-b04/environment.json','docs/benchmarks/t66f-b04/logical-costs.json','docs/benchmarks/t66f-b04/historical-p03.json','docs/t66f-b03-ir07-independent-pep669-closure.md','docs/benchmarks/t66f-b03-ir07/evidence-manifest.json','docs/benchmarks/t66f-b03-ir07/monitoring-contract-decision.json','docs/t66f-b02-independent-targeted-audit.md','docs/benchmarks/t66f-b02-independent/summary.json','docs/benchmarks/t66f-b02-independent/execution-100000.json','docs/benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json','docs/benchmarks/t66f-b03-ic01-p03/evidence/ic01-p02-source-review.json','docs/t66f-phase-b-final-evidence-closure.md']
save('requirements-source-manifest.json',{'task':'T6.6F-B11','method_ko':'로컬 원문·보존 JSON 읽기 및 SHA 결합; 제품 import/실행/외부 웹 검증 없음','files':[{'path':p,'sha256':sha(p),'bytes':(ROOT/p).stat().st_size} for p in inputs],'exact_quote_checks':[{'id':x['id'],'path':x['target_path'],'reference':x['current_reference'],'quote_sha256':hashlib.sha256(x['current_normative_statement'].encode()).hexdigest()} for x in amendments]})

# 보고서는 모든 설명을 한국어로 작성한다. 원 ID·정확한 상태 토큰·원문 인용은 보존한다.
parts=[f'''# T6.6F-B11 — §35 비용·§36 I25 증거의 T6.9 이관 규범 개정 제안

**PASS — NARROW TRANSFER PROPOSAL READY FOR AUTHORIZATION. 권고는 Option 3, 보호 조건을 포함한 이관이다.** 이는 제안 심사의 완료이며 개정 승인·효력·실행 허가가 아니다. 현재 **B10 Option D — BLOCKED, Phase B INCONCLUSIVE, formal T6.6F closure NOT AUTHORIZED, R1 activation CLOSED, production NOT AUTHORIZED**를 유지한다.

변경 ID는 `{CHANGE}`다. 원 B03의 잔여 의무 8개만 T6.9의 증거 수집 전용 하위 단계 `T6.9-E`로 이관하는 미적용 추가문을 제안한다. T6.9-E는 이 제안이 신설하려는 이름이며 기존 규범 단계라고 주장하지 않는다. 전체 F 종결은 그 증거와 별도 R1/Android proof의 독립 수용 전까지 계속 차단한다. 새 source의 좋은 결과로 원 B03 결측을 없애지 않는 보수적 이관이다.

## 1. 독립성·시작 상태·작업 권한

이 세션의 제공 이력에는 B01–B09 구현·측정 또는 B10 종결 감사 관여가 없다. 독립성은 **SATISFIED**다. 다른 agent에게 위임하지 않았으며 외부 인적 정체나 UI reasoning 설정을 인증했다고 주장하지 않는다. 역할은 요구사항·규범 변경 검토와 초안 작성에 한정한다.

시작 HEAD는 `{HEAD}`로 예상값과 일치한다. 실제 index의 2,693개 path/mode/blob/stage와 index bytes SHA를 [starting-state.json](benchmarks/t66f-b11/starting-state.json)에 기록했다. staged 변경은 0개였지만 작업 트리는 기존 tracked 수정 10개 및 untracked 증거·소스를 포함하므로 clean이라고 하지 않는다. 시작 시 visible tracked/nonignored 파일 6,440개, 777,689,520B의 SHA/크기/mode를 기록했다. Git index나 기존 소스·프로토콜·release·증거는 수정하지 않았다.

AGENTS.md와 project-state/domain-model/known-issues/development-artifact-hygiene, architecture의 서버 authority 경계를 적용했다. 도메인 모델과 backend 계산을 authority로 유지하며 모바일 독립 금융 계산을 추가하지 않는다. 본 요청의 엄격한 no-execution 범위에 따라 build·backend/Flutter regression·benchmark·실기기·emulator·API 요청은 실행하지 않았다. 일반 AGENTS 검증 권고를 이 문서 초안에 대한 실행 허가로 해석하지 않았다.

## 2. 실제 구속 조항과 규범 의존성

원문 해시·정확한 발췌는 [requirements-source-manifest.json](benchmarks/t66f-b11/requirements-source-manifest.json), 의존성은 [normative-dependency-map.json](benchmarks/t66f-b11/normative-dependency-map.json)에 있다. C 문서 §1의 역사적 PROPOSED 표시는 유지하되, 본 심사는 B10과 요청이 지정한 현재 구현 수용 기준으로 그 필수 조항을 적용한다. 문서의 과거 설계 상태를 현재 waiver로 사용하지 않는다.

|정확한 출처|현재 요구와 종결 의존성|
|---|---|
|{link(P,'§4',68)}|engine은 immutable release artifact identity다. 다른 semantics를 old hash로 광고할 수 없으며 payload/engine/archive는 서로 다르다.|
|{link(P,'§16·16-S',321)}, {link(P,'§17–18',386)}|TTL 최대900초, Available 최대4와 client attempt 최대3을 구별한다. 초기·재시작 full O(N)은 허용하지만 정당한 complete provenance가 필요하다. 정상 refresh의 hidden scan은 금지다.|
|{link(P,'§23–25',486)}|표현·구조·완전성·raw 대응·변경 receipt/validator compatibility·same Target·최종 guard/동기 COMMIT·durable readback을 유지한다.|
|{link(P,'§26',533)}, {link(P,'§38.8',790)}|실제 Android driver/VFS·commit fence·I/O/power-loss proof 없이 rollout 차단. HOST 증거가 대체하지 않는다. isolated Phase B 이전 배치 시점은 명문 없음.|
|{link(P,'§31–33',612)}, {link(P,'I23/I24',732)}, {link(P,'§38.9–11',791)}|큰 restore/MW·legacy/migration/rollback·30 backup/artifact/GC는 별도 whole-F 의무다. R1 할당은 면제가 아니다.|
|{link(P,'§34',665)}|R1→interop/full-resync/crash→performance→독립 F→명시 rollout 순서. bounded D/E 성과로 이 전체를 통과시킬 수 없다.|
|{link(P,'§35',683)} 특히 {link(P,'702행',702)}|H/D 고정, N=1k/5k/10k/50k/100k의 no-change/card/cash 반복, rows read·hash/validation/write bytes·HTTP entity/RTT·memory·median/p95. 정상 full fetch/hash/serialize/write 0, flat P 목록 없음, bounded paths/facts.|
|{link(P,'§35 비교 문장',700)}, {link(P,'§15.3',315)}, {link(B,'§27',484)}|base64/JSON framing·compression CPU·headers/RTT와 full gzip, 대표/덜 반복되는 문자열, network/CPU/write 구분. backend query plan/rows·mobile bytes/rows·durable/readback·warmup/n/IQR도 해당 계약으로 보존한다.|
|{link(P,'§36 I25',734)}, {link(P,'§38.7·12',789)}|steady-state full-N MUST NOT; 실제 rows/bytes로 증명. lease/GC/refcount hidden O(N) 금지와 고정 H/D/full gzip/HTTP proof가 비용 종결과 연결된다.|
|{link(P,'§35 마지막 문장',702)}, {link(P,'§38.12',794)}|기존 승인된 단계 분리는 post-T6.6 기기 성능뿐이다. Android durability·HOST §35/I25의 수집 이관은 현재 허용되지 않는다.|

§35가 five-point grid를 직접 수립한다. B 설계 §27도 같은 다섯 규모를 제안한다. §36 I25 자체의 행에는 N100k 숫자가 없지만 §35/§38.7·12의 scaling proof와 결합되어 다섯 번째 정상 경로 증거가 필요하다. 반대로 **N100k instrumented full cold 성공을 독립 MUST로 만드는 문장은 없다.** §18/35는 cold의 O(N)을 허용하며 필수 정상 비용은 적법 baseline 위에서 얻을 수 있다.

숫자 H/D·warmup 수·표본 수·p95 estimator·절대 ms 합격선은 C §35에 없다. 기존 실험의 105행·n3를 보편 규범으로 만들지 않는다. VM/pager 전수 방문·NAND·순수 heap peak·exclusive observer CPU도 새 필수 gate로 발명하지 않는다. 원 metric의 관측 한계는 반드시 표시한다.

## 3. B10 판정과 증거 출처

{link('docs/t66f-b10-independent-phase-b-closure-adjudication.md','B10 §3–7',51)} 및 [closure-decision.json](benchmarks/t66f-b10/closure-decision.json)의 Option D를 그대로 유지한다. 다음은 과거 결과를 읽은 범위이며 B11 신규 실행이 아니다.

|구분|검증된 범위|현재 남는 한계|
|---|---|---|
|A. B02 N100k 기능|당시 source `1cabf319f0ac2c2069e804b47cb527b55e3374db`의 비계측 실제 D→E/E3/E4·delta/restart CLOSED. 400,532객체·261,543,083B|원 B03 ON 비용/계측 cold/I25 정량 전체로 승계할 수 없다.|
|B. 계측 cold|역사 IC01/P02→P03는 397,146/400,532·2,699.957907초·세 lease 만료·E3/E4 미완료 FAIL|최종 IR07 원 B03의 N100k 계측 full cold 성공은 UNVERIFIED. 기존 NO-GO 유지. 단독 재cold MUST로 추가하지 않는다.|
|C. B04 비용|원 B03의 1k/5k/10k/50k, 유효 통제80개/40쌍·정상 ON36개|N100k 정상 세 workload 및 rows/network/framing/full gzip 완결 비교의 결측 열.|
|D. E3 I25|네 N 정상 ON의 full_recoveries/full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds=0|N100k matched 직접 계측 미검증. 50k나 B02 one-row 보조 counter로 대체하지 않는다.|
|E. 실기기|기기 성능은 기존 post-T6.6 단계 분리|memory/VFS·전원·thermal·hardware 중단 미검증. 성능과 §26 durability는 서로 다른 의무다.|
|F. whole-F/R1|§26/31/32/33/34·I23/I24·§38.8–11 미완료 유지|비용 이관으로 formal F·R1 사용자 활성화·배포가 가능해지지 않는다.|

원 B03 IR07 correctness는 {link('docs/t66f-b03-ir07-independent-pep669-closure.md','IR07 보고서',1)}와 [계측 환경 결정](benchmarks/t66f-b03-ir07/monitoring-contract-decision.json)의 지원 source/runtime에 대해 CLOSED다. 새 material 반증은 발견하지 않았고 재감사하지 않았다. B01/B02 CLOSED, B04 bounded PASS, B09 exact admission/real-path PASS·performance MIXED도 그 범위에서 유지한다. B05/B08은 EXPERIMENTAL — NOT ADOPTED다.

B02 원 근거는 {link('docs/t66f-b02-independent-targeted-audit.md','§17–20',272)}, [summary](benchmarks/t66f-b02-independent/summary.json), [execution-100000](benchmarks/t66f-b02-independent/execution-100000.json)다. P03는 [원 full-analysis](benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json), [당시 source review](benchmarks/t66f-b03-ic01-p03/evidence/ic01-p02-source-review.json), [B04 재구성](benchmarks/t66f-b04/historical-p03.json)을 보존한다. 최종 IR07 payload를 역사 P03에 붙이지 않는다. B10은 원 B02 scratch 소실과 evidence 내 DB 부재를 확인했으며 B11도 사용 가능한 N100k accepted DB를 인증하지 않는다. 전체 filesystem의 부재를 단정하지 않는다.

## 4. 남은 의무의 정확한 목록

아래 ID는 B11 추적 별칭이며 새로운 원 규범 ID가 아니다. 수용 단위는 8개이고 여러 B10 parent/metric/scale 별칭은 중복 추적이다. 모든 B10 미완료 행 **37개**를 원 열 그대로 [transfer-obligation-register.json](benchmarks/t66f-b11/transfer-obligation-register.json)의 coverage에 보존했다. 각 canonical 의무에는 원 criterion·정확한 조항·scale·source/runtime/fixture·existing/missing evidence·blocker·기존 deferral·제안 owner·milestone·검증·미완료 결과·semantics 변경 여부가 있다.

|이관 추적 ID|원 요구|정확한 결측과 future owner|
|---|---|---|
''']
for x in transfers:
 parts.append(f"|{x['id']}|{', '.join(x['source_requirement_ids'])}|{x['missing_evidence_ko']} 제안 owner=T6.9-E, 개인 미배정.|\n")
parts.append('''
세 N100k 비용 cell은 hash/validation/write·memory·분포까지 포함한다. T35-ROWS/NET/GZIP는 하위 네 N에 남은 비교 결측도 포함하므로 N100k 한 점만 더하면 전체 비교가 자동 완료되는 것은 아니다. 기존 raw로 정확히 복구 가능한 열은 재집계할 수 있고, 없는 열은 실제 증거가 필요하다.

비이관 의무는 E-DEVICE-PERFORMANCE, F-ANDROID-DURABILITY, F-RECOVERY, F-MIGRATION, F-BACKUP, F-WHOLE-EXIT 및 SOURCE-REQUALIFICATION이다. B-COLD-100K는 역사 미검증 주장 보존 항목이며 독립 필수 gate가 아니다. A-B02-FUNCTIONAL은 closed provenance로 함께 남긴다. 어떠한 항목도 이관 때문에 사라지지 않는다.

## 5. T6.9의 실제 범위와 이관 실현성

''')
parts.append(f'''{link(A,'T6.6A §18',370)}은 full 50k/100k scalability 승인을 T6.9 범위로 기술한다. {link(B,'T6.6B §27',484)}은 fixed hot/seed/context/문자 다양성·다섯 N, no-change/card/cash·confirmed-heavy·한 달 hot 대량을 구분하는 PROPOSED F/T6.9 감사 방향이다. {link(B,'§29',513)}의 도식은 F 뒤에 post-T6.6 실기기/T6.9를 놓는다. C는 §33에서 T6.8 이후 dead API 별도 소비자 감사를 명시하지만 T6.9의 별도 상세 acceptance/owner/entry 계약은 확인되지 않았다. T6.7 UX를 시작할 독립 승인 규정도 이 검색으로 확보하지 못했다. 기존 범위의 방향을 없애거나 T6.9가 이미 잔여 8개를 소유한다고 주장할 수 없다.

따라서 **기술적·규범적 실현성은 CONDITIONAL**이다. 기존 D→TLS→Flutter/E3/E4 측정 수단과 원 B03 계측 인증이 있어 수집 역할을 맡길 구조는 있지만 N100k baseline·실행 성공은 미입증이다. 초안은 T6.9의 인수 acceptance와 prerequisites를 모두 새로 명시해야 한다. 상세 명세가 없다는 이유로 불완전 인계를 묵인하지 않고 C §35-T69를 인수 계약으로 제정하는 미적용 초안을 제공한다. 나중 별도 T6.9 문서가 생기면 이 의무와 원래 대규모 감사 범위를 함께 수록·대조해야 한다.

F 종결을 T6.9 수집의 전제로 그대로 두면 `F→T6.9 수집→F` 순환이 된다. 권고안은 F 전체 exit를 열지 않고 **T6.9-E collection-only entry**만 F 전에 허용하도록 C §34와 B §29의 관계를 함께 고친다. 기존 T6.9 전체 감사/최종 수용과 기기 gate에는 완료를 부여하지 않는다. 기존 문구는 현행 무승인 이관을 허용하지 않지만, §38 마지막 원칙은 실패 시 차단과 별도 명세 변경 감사를 요구하며 별도 명시 개정 제안 자체를 영구 금지하지는 않는다. 현재 예외를 발명하지 않고 이 문구를 정확히 제안하는 이유다.

T6.7/T6.8은 행정 종결을 근거로 unqualified source나 100k PASS를 사용하지 못한다. 이 초안은 해당 구현을 허가하지 않으며 legacy fallback/consumer 제거도 허가하지 않는다. T6.9-E 수집은 T6.7/8 완료를 전제로 삼지 않는다. 별도 R1 구현 작업의 선행 필요와 사용자 R1 활성화 CLOSED도 혼동하지 않는다.

## 6. source-version 한계와 재자격

원 기준은 payload `{PAYLOAD}`, engine `{ENGINE}`, archive `{ARCHIVE}`다. [B04 source-identity](benchmarks/t66f-b04/source-identity.json)와 [B10 source 경계](benchmarks/t66f-b10/source-certification-boundaries.json)가 근거이며 B11은 archive를 복원·실행하지 않았다. live B05-A나 별도 B08/B09 engine은 이 기준이 아니다.

이관을 안전하게 좁히기 위해 **나중 다른 source의 측정만으로 원 B03 이관 의무를 수용하는 경로는 제안하지 않는다.** 미래 최적화/최종 제품 source는 그 source의 미래 주장만 검증한다. 원 B03 정상 비용 증거가 나중에 완결되면 새 B03 cold 없이도 적법 baseline/provenance를 통해 이관 수용은 가능하지만, 원 P03 실패나 과거 full cold 미검증은 그대로다. 원 source에서 더는 측정할 수 없다면 이 개정 아래 의무를 완료시킬 수 없으며 별도 인간 결정·독립 개정 심사가 필요하다.

미래 source 채택/검증은 별도 승인 대상이다. backend engine 입력·artifact/allowlist·validator/schema·instrumentation·runtime/monitoring·Android binary/driver가 달라지면 변경 inventory와 exact identity를 먼저 기록하고 영향받는 계측 byte/SQL/ownership/cancellation oracle, 구조·index/root parity, same-view/authority/fence, accepted provenance·legacy/recovery/durability를 재자격한다. §23의 호환 proof 없는 validator/schema 변경은 full revalidation 대상이다. 성능 인증은 그 source의 전체 다섯 점 곡선으로 수행하며 옛 네 점+새100k를 합치지 않는다. 무조건 B01–B03 전체 closed 시험을 반복하는 의무는 만들지 않는다. 원 금융 데이터의 semantic equality는 두 engine의 동등성 증명이 아니다.

## 7. 세 가지 처분 비교

|선택|효과·비용|판정|
|---|---|---|
|1. 현행 유지|8개 결측을 기존 Phase B 안에서 완결할 때까지 현재 차단. 새 규범/entry 계약 비용 없음. baseline·계측 실현성 및 지연은 남음.|거절 시 기본 경로. 최소 증거는 위 8개이며 새 full cold 자체를 추가하지 않음.|
|2. 좁은 조건부 이관|의무를 T6.9에 보내고 행정 종결만 구분.|상세 entry/source/owner/gate 없이는 순환·무기한 미이행·source 대체 위험이 있어 단독 채택 비권고.|
|3. 보호 조건부 이관|원 source 고정·기명 owner/독립 수용자·수집 전용 entry·hard milestone·새 source 불대체·whole-F 차단을 함께 명문화.|권고. 모든 의무와 거부 가능성을 유지하지만 실제 실행 성공/일정은 보장하지 않음.|

[option-comparison.json](benchmarks/t66f-b11/option-comparison.json)에 같은 판단을 기록했다. Option3도 현재 미승인이며 사람이 승인하지 않으면 Option1이 계속 구속한다.

## 8. 정확한 미적용 개정문

아래는 **삭제 없는 추가문 방식의 redline**이다. 각 `현재 원문`은 해당 줄의 exact repository text이며 `추가안`은 그 뒤에 넣자는 제안이다. 원 파일은 수정하지 않는다. 기계 원본은 [proposed-amendment-record.json](benchmarks/t66f-b11/proposed-amendment-record.json)이다. 승인 시 AM01–05를 일관된 한 변경으로 심사·적용해야 하며 일부만 적용해 guard 문구를 누락할 수 없다. 원문이 달라졌다면 exact context를 다시 대조하고 재심사한다.

''')
for x in amendments:
 parts.append(f"### {x['id']}. {x['target_path']} {x['target_section']}\n\n대상: {link(x['target_path'],x['target_section'],x['current_reference']['line_start'])}. 사유: {x['reason_ko']}. 증거 효과: {x['effect_on_required_evidence_ko']}.\n\n현재 원문 — 아래 내용은 유지:\n\n````text\n{x['current_normative_statement']}\n````\n\n추가안 — DRAFT ONLY / NOT APPLIED:\n\n````text\n{x['proposed_addition_ko']}\n````\n\n")
parts.append('''§4·16–18·23–26·31–33의 수신/identity·복구·R1 기준 자체는 개정할 필요가 없다. §38.8–11도 변경 대상에서 제외한다. 독립 T6.9 상세 명세의 현행 문구는 발견되지 않았으므로 만들어 낸 current quotation이나 가상 파일 경로를 쓰지 않는다. 위 AM02/AM05가 새 인수 계약과 entry 변경의 exact 제안이며, 기존 상세 명세를 수정했다고 주장하지 않는다.

## 9. 보존할 기준과 미래 증거 수용 계약

위 AM02와 JSON future_acceptance_contract가 동일 계약이다. reviewer가 전체 audit chain을 다시 열지 않고 다음을 확인할 수 있다.

|수용 요소|필수 계약|
|---|---|
|규모·입력|다섯 N의 세 정상 workload, 실제 H/control/policy/문자 bytes와 D 고정. B04 재사용 digest 4개는 JSON에 있고 N100k digest는 미발급/null이며 실행 전 freeze해야 함.|
|계측·source|원 B03/IR07 지원 runtime ON. 실제 sink/primary spans/SQL NEW payload와 실패·rollback·stage 귀속. exact source/release/admission guards 불변.|
|rows·network·gzip|기존 raw의 실제 열만 재사용, 결측 명시·보완. 다섯 N 비교·framing/headers/RTT·full gzip과 다양성 비교 의무 유지. offline compression을 actual wire로 부르지 않음.|
|I25|E3 full counters0와 hot/changed/tree/index 작업·pin/COMMIT/readback 귀속, D/E lease/GC hidden scan 부재. wall slope만으로 O(1) 증명하지 않음.|
|실제 accepted completion|정당한 baseline/receipt→실제 D3/TLS/Flutter/E3→accepted readback/E4. no-change sequence 유지 가능. prepare/discard는 수용 표본 아님.|
|독립 correctness|실제 backend raw/presenters·native graph/value digest/FK·source identity. 모바일 금융 재계산 gate 추가 없음.|
|raw·보존|실패 포함 command/exit/time/표본·Target·accepted·metric·HTTP·manifest SHA/mode/size; 필요한 일관 DB는 보존/검증 뒤 disposable만 정리.|
|판정|모든 8개와 scale/metric의 원 source 증거가 완결되어야 T6.9-E EVIDENCE ACCEPTED. 정량 기준은 그대로이며 단말 절대 ms 기준을 새로 만들지 않음.|
|실패|결측은 PARTIAL/UNVERIFIED, 실제 full-N 위반은 귀속된 구현 거부/수정·재자격 사유. timeout/expired를 성공으로 바꾸지 않음. 차단 지속.|

B03 measurement guards·E3 guard 바로 뒤 동기 COMMIT·I25 counters를 완화하지 않는다. 일부 규모·외삽100k·비계측 기능으로 결측을 채우지 않는다. TTL/attempt 연장, B05/B08 채택, canonical data/source-SHA guard/release/admission 변경, 미실행 device PASS, R1 활성화·production 배포를 허가하지 않는다. 원 source 인증과 역사 실패는 소급 변경하지 않는다.

## 10. 승인·거절·실패 시 처분

**APPROVAL AUTHORITY NOT ESTABLISHED — EXPLICIT USER/PROJECT OWNER DECISION REQUIRED.** AGENTS는 명시 배포 요청을 요구하고 C §34는 구현·rollout 승인을 요구하지만, 이 규범을 바꿀 개인/직함·상설 절차를 특정하지 않는다. C §16-S의 과거 소유자 승인도 현재 reviewer에게 포괄 권한을 주지 않는다. 이 요청은 drafting authority만 부여했으므로 승인으로 간주하지 않는다.

유효 결정은 권한 근거·실제 승인자/일시·변경 ID와 exact 초안 SHA·8개 의무·기명 T6.9-E 책임자·독립 수용자·blocking milestone/보고 의무·잔여 위험 수락을 명시해야 한다. 지금 개인 이름·날짜·권한자는 null이며 B11이 지명하지 않는다. 승인에 필요한 이 필드들을 채워야 효력이 생기는 조건부 문구는 완성되어 있다. 새 benchmark 실행은 이 승인에 자동 포함되지 않으며 별도 사전 계획/GO가 필요하다.

위험은 N100k baseline 부재·계측 overhead/시간·증거 확보 실패·행정 상태 오독·책임자 미지정·미래 source와 원 source의 이중 검증 비용이다. 이 위험을 수락해도 actual full-N 위반이나 미측정을 PASS로 승인하는 권한은 이 제안에 없다. 원 source 측정이 불가능하면 T6.9-E를 수용할 수 없고 formal F 등 차단을 유지한다.

거절/미승인은 현행 원문·Option1·B10 차단을 유지한다. 승인 뒤 조건 위반/철회가 발생하면 행정 종결 효력을 중단/철회하고 원 gate를 복원한다. 이미 얻은 유일 증거·실패 원문은 보존한다. 자동 기한 연장·blanket waiver는 없다. 후속 별도 적용 작업은 AM01–05와 실제 T6.9 문서 존재 여부를 다시 대조한 뒤 문서에 반영하며 이 작업에서 수행하지 않았다.

## 11. 승인 전후에 가능한 상태 표현

|서로 다른 상태|승인 전 현재|Option3가 유효 승인·별도 적용된 뒤, 증거 완료 전|
|---|---|---|
|bounded measurement work package|B04 범위 완료·PASS|같은 scoped 결과 유지|
|Phase B 행정 종결|허가되지 않음|ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED만 허용|
|Phase B 정량 증거 수용|INCONCLUSIVE; grid PARTIAL; 100k/I25 UNVERIFIED|동일. 후속 T6.9-E 독립 수용 이후에만 새 날짜·source의 수용 판정 가능|
|formal T6.6F closure|NOT AUTHORIZED|여전히 NOT AUTHORIZED. 8개와 나머지 whole-F proof 완료 후 새 독립 재심사 필요|
|whole-F release proof|미완료|R1/Android/legacy/recovery/backup 등 독립 의무 유지|
|R1 activation|CLOSED|CLOSED. R1 구현 stage 진척과 사용자 활성화는 다름|
|production deployment|NOT AUTHORIZED|NOT AUTHORIZED. proof 완료도 별도 명시 승인/운영 요청을 대체하지 않음|

B01/B02 CLOSED, 원 B03 IR07 CLOSED, B04 bounded PASS, B05/B08 미채택은 승인 전후 그대로다. 과거 B10 Option D가 소급 변경되는 것도 아니다. 승인 후 행정 상태는 새 결정으로만 기록한다.

## 12. 분석 검증·보존·최종 권고

B11 검증은 새 JSON 파싱/필수 필드·상호 ID/8개 의무·37개 B10 미완료 행 coverage, exact 원문 발췌·인용 경로, manifest SHA, index path/mode/blob와 실제 index bytes 및 시작 파일 SHA/mode 비교뿐이다. 제품 import/실행·full cold·build·backend/Flutter regression·real-device는 0회다. 검증 결과는 [validation-and-preservation.json](benchmarks/t66f-b11/validation-and-preservation.json), 산출물 해시는 [evidence-manifest.json](benchmarks/t66f-b11/evidence-manifest.json)에 남긴다. B11 전용 문서/JSON/분석 작성·검증 도구만 생성했다. 대형 임시 실험 산출물 정리는 NOT APPLICABLE, 삭제/회수0B이며 기존 파일과 ignored runtime artifacts에는 쓰지 않았다. 초기 bwrap loopback 초기화 오류는 명령 실행 전 실패했고 승인 검토된 도구 경로로 문서 읽기/작성만 계속했다. 자동 승인 거절은 없었다.

**최종 권고: Option 3 보호 조건부 이관안 T66F-B11-TRANSFER-01을 명시적 인간 승인 대상으로 제출한다.** 원 B03 증거의 장소/수집 시점과 행정 상태만 변경하고 수용 조건을 약화하지 않는다. 이것은 실제100k 성공이나 실행 실현성을 인증하는 PASS가 아니다.

정확한 다음 행동: 사용자 또는 프로젝트 소유자는 T66F-B11-TRANSFER-01의 보호 조건부 이관안과 승인 권한 근거·기명 책임자·독립 수용자·차단 마일스톤을 하나의 명시적 결정으로 승인하거나 거절하십시오.
''')
parts.append('\n## 필수 판정 기록\n\n```text\n'+(D/'required-footer.txt').read_text()+'```\n')
(ROOT/REPORT).write_text(''.join(parts))
print(json.dumps({'report':REPORT,'transferred_obligations':len(ids),'B10_open_rows_covered':len(coverage),'amendments':len(amendments),'status':'DRAFT ONLY — NOT APPLIED'},ensure_ascii=False))

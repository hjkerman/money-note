"""완성된 B04 증거만 읽어 한국어 보고서를 작성한다."""
import json,pathlib,statistics
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b04'
def read(p):return json.loads(p.read_text())
def table(headers,rows):return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join('---' for _ in headers)+'|']+['|'+'|'.join(str(v) for v in row)+'|' for row in rows])
def num(v):return f'{v:,}' if isinstance(v,int) else str(v)
def seconds(v):return f'{v/1e6:.3f}'
m=read(E/'run-manifest.json');ts=read(E/'timing-summary.json');cost=read(E/'logical-costs.json');pairs=read(E/'pairs.json');dec=read(E/'fullscale-decision.json');checks=read(E/'checks.json');cleanup=read(E/'cleanup.json');identity=read(E/'source-identity.json');preserve=read(E/'preservation-after.json');env=read(E/'environment.json');hist=read(E/'historical-p03.json')
scales=sorted({x['N'] for x in m['runs'] if x['role']=='binding-lower-N' and x['valid_completed']});valid=m['valid_controlled_completed_runs'];pp=m['valid_controlled_pairs'];diag=m['diagnostic_completed_runs'];incomplete=m['incomplete_workload_runs'];stage=[read(R/p) for p in m['stage_diagnostic_files']];stagepairs=[]
for k in ('no_change','card','cash'):
 d={v['on']:v for v in stage if v['kind']==k and v['status']=='COMPLETED'}
 if len(d)==2:
  a,b=d[False],d[True];assert a['target']==b['target'] and a['accepted_before']['target']==b['accepted_before']['target']
  stagepairs.append({'kind':k,'OFF':a,'ON':b,'ratio':{f:b[f]/a[f] for f in ('E2_acquire_api_us','E3_verify_api_us','E3_prepare_api_us')}})
def op(k):return {'cold':'cold','no_change':'무변경','card':'카드 1행','cash':'현금 1행'}.get(k,k)
text=[]
def add(s):text.append(s)
add('# T6.6F-B04 — Phase B 측정 가능성·계측 시간 교란·제한 규모 실제 비용 검증')
add(f"**{dec['B04_verdict']} — {dec['B04_verdict_ko']}** B03 계측 정확성은 **CLOSED — IR07**로 유지한다. 이번 결과는 Phase B 전체 PASS가 아니다. 100k 판정은 **{dec['decision']}**이며 새 100k cold 실행은 **0회**다. {dec['summary_ko']}")
add(f"[실행 manifest](benchmarks/t66f-b04/run-manifest.json)는 유효한 정상 비용·완료된 cold·진단 전용·미완료를 분리한다. 유효한 통제 측정 {valid}개/{pp}쌍, 완료된 기타 publication 진단 {diag}개, 별도 stage 진단 {len(stage)}개다. [실행 전 계획](benchmarks/t66f-b04/plan.md), [계약 행렬](benchmarks/t66f-b04/contract-matrix.json), [쌍별 원자료](benchmarks/t66f-b04/pairs.json), [논리 비용](benchmarks/t66f-b04/logical-costs.json)에 연결한다.")
add('## 계약과 실제 설정')
add('§35의 바인딩 N은 **1000/5000/10000/50000/100000**이다. H는 hot/참조 working set와 필수 control/policy descriptor 크기, D는 base 이후 변경 행이다. 규범에는 **숫자 H/D, 반복 횟수, 절대 지연 합격선이 없다**. 숫자를 새 규범으로 만들지 않았다. 정상 목표는 O(H+changed bytes+L log P+256E), full history fetch/hash/serialize/write 0회이며 I25는 steady-state full-N 작업 금지다. cold/full sync의 O(N)는 허용된다. 해당 조건은 실제 논리 비용과 source 경계로 판단하며 wall-time 곡선을 복잡도 증명으로 바꾸지 않는다.')
add(table(['구분','요구·이번 적용','남은 의무'],[
 ['바인딩 §35','다섯 N에서 H/D 고정 no-change/card/cash 반복','100k 미실행'],
 ['기존 실험 설정','seed662602·평가일2026-10-05·current ledger105·다른10개 table35행','N label은 ledger N, 전체 authoritative N+35'],
 ['기존 실험 설정','초기 hot87364B/control3178B; archive N−105','105만으로 H 전체를 정의하지 않음'],
 ['실험 D','no-change0, 카드id1002·현금id101 UPDATE 각각1','세 trial은1001/1002/1003원, −51/−52/−53원'],
 ['바인딩 §16','실제900초 TTL, 기존 attempts3/observations3','연장·증가0'],
 ['바인딩 §25','같은 Target·정확한 base·원 AppState guard→COMMIT','inactive segmented 내부 경계; UI 활성화 없음'],
 ['바인딩 §35·I25','실제 hash/primary span/SQL payload와 operation 수','100k·완전한 rows-read/압축 비교 의무는 별도 미완료'],
 ['추가 실험 선호','정상3회 반복, 규모/회차별 순서 반전, fresh HTTP pool','OS cache flush 없음; n3 p95는 표본 최대값'],
 ['task 제한','하위 네 N만 실행, N100k cold 금지','별도 명시 승인 필요']]))
add('## 소스·환경·보존')
add(table(['항목','검증'],[['시작/종료 HEAD',preserve['head']],['B03 payload SHA-256',identity['payload_sha256']],['archive SHA-256',identity['archive_sha256']],['선택 source','899개 / 9,801,906B, 모든 바이트·mode 일치'],['나머지 baseline','고정 Git blob·실행 비트까지 대조'],['실행 workspace',identity['reconstruction']],['live payload 차이',str(identity['live_payload_differences'])],['runtime','CPython3.12.3 / backend SQLite'+env['python']['sqlite']+' / client SQLite3.53.4 / Flutter'+env['flutter']['frameworkVersion']+' / Dart'+env['flutter']['dartSdkVersion']],['Git index·기존 파일', '시작 실제 index bytes/entries와 동일, 기존 파일 변경0개' if preserve['index_preserved'] and not preserve['preexisting_changed'] else '보존 기록 확인 필요']]))
add('[무결성](benchmarks/t66f-b04/source-identity.json)과 [마지막 보존 검사](benchmarks/t66f-b04/preservation-after.json)를 보존했다. 동결 archive는 수정하지 않았고, 실행본은 기준 Git archive 위에 payload를 복원했다. 제품/B03 계측/규범/SHA 기대값·Snapshot v7/OfflineBaseline v4·원 authority guard는 불변이다. 새 코드는 B04 실험 driver/분석뿐이다. build 의존성만 기존 개발 runtime을 사용했다. 일반 sandbox는 bwrap loopback 초기화 오류로 시작하지 못해 승인 검토된 실행 경로를 사용했다. 자동 승인 거부는 없었다.')
add('실제 TLS는 새 loopback ephemeral port·같은 합성 credential·같은 서버/Target을 사용했다. 운영18080·DB·Snapshot·환경 파일·서비스에는 접근하지 않았다. 모든 규모에 기존 HOST large verification profile(object500000/metadata384MiB)을 동일하게 적용했다. 이는 운영 제한 변경이나 Android 메모리 합격 근거가 아니다. [환경 manifest](benchmarks/t66f-b04/environment.json)와 규모별 execution 파일에 실제 RSS·disk 표본을 남겼다.')
add('## ON/OFF 방법과 도구 오류')
add('각 mode는 독립된 빈 client DB에서 같은 Target을 실제 cold 취득하고, 같은 accepted Target/상대 sequence 위에서 정상 작업을 반복했다. namespace·immutable identity·authorization·H/D·runtime·리소스·관측 정책을 맞췄다. 로컬 generation UUID는 독립 발급되므로 UUID 일치 대신 Target·상대 sequence·DB count/body bytes·E4 값의 동등성을 검사하고 실제 UUID를 모두 기록했다. Cold의 backend는 bootstrap과 독립 oracle 뒤 warm 상태이며, client accepted/objects/staging은 비어 있다. OS page-cache cold를 주장하지 않는다. backend bootstrap과 mutation generation은 별도 **ON 단일 scope**이고 ON/OFF generation 쌍이 아니다.')
add('첫1k 진단은20 operation을 완료했으나 ON 정상9회 중8회에서 send 실패·retry1건과 약15초 대기가 있었다. 초기 예외 타입은 미기록이므로15초 timeout과 맞는다는 정황을 확정된 예외 분류로 바꾸지 않는다. 동일 boot의 후행 wall/단조시계 anchor에서는 backend 첫 요청 이전의 대기로 관찰됐지만, 초기 실행과 anchor 사이 wall-clock drift 상한은 기록하지 않았다. 완료된 body 시간에 실패한 send 대기를 숨겨 넣지 않았다. 양 mode에 매 operation 새 HTTP pool을 적용한 통제 cohort에서는 해당 오류가 사라졌다. 이 비교는 pool 수명에 민감한 교란을 보여주지만 stale socket/Zone 내부 경합의 세부 원인을 독립 분리하지 않았으며, 15초를 observer CPU라고 부르지 않는다. 첫 결과는 정상 grid와 분리했다. P02 prepared cache가 ON에 포함되므로 ON/OFF 차이는 cache 이득과 관측 비용을 포함한 순효과다. ON에는 TEMP row callback Stopwatch도 추가되어 있으며 이 타이머 자신의 비용을 독립 제거하지 않았다. 따라서 아래 비율은 B03+명시한 timing facade 구성의 실측 순효과이지 순수 B03 callback CPU가 아니다. 정상 pair는 두 client가 같은 process에 함께 살아 있어 RSS·JIT·OS cache 차이도 남는다.')
add('초기 driver의 TreeKey import 누락은 측정 전 compile 오류, 두 번째 준비의 기존 scratch/pending 재사용 거부는 측정 전 환경 오류였다. 새 cohort별 root 존재 금지로 바로잡았다. 첫1k 종료의 namespace BLOB JSON 오류는20개 완료 측정 뒤 artifact 단계 실패이며, 이미 생성된 SQLite backup을 독립 검증해 보존했다. fuser의 `--` 인자 형식 오류는 삭제0개에서 멈췄고 절대경로 호출로 수정했다. pubroot 밖 analyzer의 패키지 해석 오류는 import 경로만 바꾼 task-owned package 내부 분석본으로 분리했다. 원 로그와 [도구 사건 목록](benchmarks/t66f-b04/tooling-incidents.json)을 보존했다. B03 finding으로 재분류하지 않는다.')
add('## 시간 경계와 교란 실측')
add(table(['측정','실제 경계·한계'],[['내부 동기화 wall','원 AppState.publishSegmentedForIsolatedUse 호출→반환. segmented 내부 accepted publication이며 실제 UI/Offline-ready 완료는 미측정'],['backend handler','ASGI app 진입→응답 bytes 준비 완료. native wait 포함; CPU는 별도 process_time_ns'],['D3 내부','auth/prepared/admission/resolution/terminal serialization/terminal HTTP. 서로 포함되므로 더하지 않음'],['HTTP','send→body 완료, header 별도; 실패 send 시간 별도. 순수 network 지연이 아님'],['E1 SQL API','Database.execute/select 호출 inclusive; native DB·wrapper·UDF 포함'],['callback','Dart TEMP row UDF body 합의 하한. 전체 observer CPU가 아님'],['E3 commit/readback','제품이 반환한 transaction/readback stopwatch. 전체 E3Verify/Prepare와 다름'],['50k 별도 stage','공개 E2 acquire / E3 verify API·proof / prepare 각각 stopwatch; accepted 불변 후 discard'],['E4','실제 accepted read scope에서 ledger/cash 각1행과 hot 읽기'],['CPU·불확실성','client /proc10ms tick, backend process CPU; shared timer 비용·OS cache/JIT/순서·scheduling 잔존']]))
add('다음 OFF/ON은 각 cell의 wall median/p95(초), 비율은 **쌍별 ON/OFF 비율의 중앙값[min,max]**이다. 비율 중앙값은 두 mode 중앙값의 몫과 다를 수 있다. cold n=1, 정상 n=3이며 p95는 표본 최대값이다. 모집단 tail·통계적 신뢰구간을 주장하지 않는다.')
add(table(['N','작업','쌍','OFF median/p95 s','ON median/p95 s','쌍별 비율 중앙값[범위]','backend 비율 중앙값','SQL API 비율 중앙값'],[[x['N'],op(x['workload']),x['pairs'],f"{x['OFF_seconds']['median']:.3f}/{x['OFF_seconds']['nearest_rank_p95']:.3f}",f"{x['ON_seconds']['median']:.3f}/{x['ON_seconds']['nearest_rank_p95']:.3f}",f"{x['ratio']['median']:.3f}[{x['ratio']['min']:.3f},{x['ratio']['max']:.3f}]",f"{x['backend_ratio']['median']:.3f}",f"{x['E1_SQL_ratio']['median']:.3f}"] for x in ts]))
add('[시간 원자료](benchmarks/t66f-b04/timing-summary.json)와 pairs.json에 OFF/ON·절대 차이·비율·CPU·E3·E4를 모두 보존했다. 겹치는 handler/HTTP/SQL/callback을 합친 가짜 총시간은 없다. 순수 Python callback CPU·hash-only wall·network-only latency는 미측정이다.')
add('## Cold·정상 비용의 분리')
coldrows=[]
for n in scales:
 a=read(E/f'raw/n{n}-v3/cold-0-off.json');b=read(E/f'raw/n{n}-v3/cold-0-on.json');f=read(E/f'raw/n{n}-v3/fixture.json')
 def leases(d):return len({r['manifest']['observation_id'] for r in d['backend']['requests'] if r['manifest'] is not None})
 coldrows.append([n,num(f['graph']['objects']),num(f['graph']['canonical_bytes']),seconds(a['elapsed_us']),seconds(b['elapsed_us']),f"{leases(a)}/{leases(b)}",f"{a['observation_expired']}/{b['observation_expired']}"])
add(table(['N','reachable objects','고유 canonical B','cold OFF s','cold ON s','서로 다른 관측 OFF/ON','완료 전 만료 OFF/ON'],coldrows))
add('동일 nonce의 terminal replay200은 새 lease가 아니다. 각 Available의900초를 따로 적용했고 실제 갱신만 distinct observation ID로 센다. 완전 취득 뒤의 E3 local 후처리는 transfer TTL과 별도다. 모든 완료 cold는 accepted sequence0→1과 객체 수·고유 BLOB 합을 확인했다. 정상 no-change는 accepted UUID/sequence를 유지하고 신규 immutable0이며, 카드·현금은 정확히 한 행 변경 후 sequence를1씩 전진시켰다.')
add('backend cold bootstrap ON과 첫 카드/현금 generation ON은 다음과 같다. source seed 준비·독립 graph oracle는 timer 밖이며 실제 capture/finalize/commit은 generation scope 안이다. 이 값을 client/request 시간에 더해 ON/OFF 총량을 만들지 않는다.')
grows=[]
for n in scales:
 for name,fn in [('bootstrap','bootstrap.json'),('card','card-0-mutation.json'),('cash','cash-0-mutation.json')]:
  d=read(E/f'raw/n{n}-v3/server/{fn}');g=d if name=='bootstrap' else d['generation'];c=g['counters'];grows.append([n,name,f"{g['wall_ns']/1e9:.3f}",f"{g['process_cpu_ns']/1e9:.3f}",num(sum(int(v) for k,v in c.items() if k.endswith('/hash_input_bytes'))),num(sum(int(v) for k,v in c.items() if k.endswith('/submitted_bytes')))])
add(table(['N','generation ON','wall s','process CPU s','실제 hash 입력 B','primary submitted B'],grows))
add('## 실제 논리 비용')
add('각 byte 열은 독립 지표다. Hash는 실제 sink 입력(domain/NUL·반복 포함), primary validation은 UTF8/JSON/C1에 제출한 span이며 structured visits와 다르다. Backend JSON 완료와 Dart 전체 C1 완료도 구별한다. SQL은 NEW TEXT UTF8/BLOB payload이고 UPDATE는 NEW row 전체, DELETE 신규 payload0이다. scalar는 개수로 분리한다. API bind·HTTP entity·파일 성장·VFS/물리 I/O를 대용으로 쓰지 않았다. OFF counter는 **null/미계측**이며0 비용이 아니다.')
add('아래는 각 규모 첫 novel delta/trial0의 정확한 값이다(평균·추정 아님). client hash/validation은 publication과 정해진 E4 read를 포함하므로 E4는 stage 파일로 따로 확인할 수 있다. 나머지 두 정상 반복과 cold의 전체 counter는 logical-costs.json 및 원 JSON에 있다.')
selected=sorted([x for x in cost if x['trial']==0 and x['workload'] in ('no_change','card','cash')],key=lambda x:(x['N'],('no_change','card','cash').index(x['workload'])))
add(table(['N','작업','새 객체','client hash B','client submitted/completed B','SQL attempted/effective/committed B','objects committed B'],[[x['N'],op(x['workload']),x['new_immutable_objects'],num(x['client_hash_input_bytes']),f"{num(x['client_validation_submitted_bytes'])}/{num(x['client_validation_completed_bytes'])}",'/'.join(num(x['client_SQL_logical_payload'][o]) for o in ('attempted','effective','committed')),num(x['E1_objects_BLOB']['committed'])] for x in selected]))
add(table(['N','작업','backend request hash B','backend primary submitted/completed B','backend SQL attempted/effective/committed B'],[[x['N'],op(x['workload']),num(x['backend_hash_input_bytes']),f"{num(x['backend_validation_submitted_bytes'])}/{num(x['backend_validation_completed_bytes'])}",'/'.join(num(x['backend_SQL_logical_payload'][o]) for o in ('attempted','effective','committed'))] for x in selected]))
add('모든 유효 ON operation에서 E1 objects INSERT committed BLOB은 독립 DB의 sum(length(body)) 증가와 같았다. Attempted/effective/committed는 실제 scope에서 분리했고 rollback·실패 span도 별도 key로 보존했다. 신규 저장량과 repeated processing bytes를 혼동하지 않는다. 전체 최종 상태는 SQLite backup API로 보존해 quick_check/FK 및 독립 canonical SHA·reachable set·11개 table의 실제 값 digest를 backend와 양 client에서 대조했다. [보존 artifact 목록](benchmarks/t66f-b04/artifacts/)에 gzip SHA와 uncompressed SQLite SHA·실제 Target/UUID/sequence가 있다. 삭제된 원 P03 자료를 복구한 사본이 아니다.')
add('## E3 I25 관측')
add(table(['N','작업','E3 hash B','E3Verify primary B','hot raw 행','변경 행','tree examined','E3 SQL committed B'],[[x['N'],op(x['workload']),num(sum(x['stages'][s]['hash_input_bytes'] for s in ('e3Verify','e3Prepare','e3Commit'))),num(x['stages']['e3Verify']['validation_submitted_bytes']),x['work'].get('hot_raw_rows',0),x['work'].get('incremental_rows',0),x['work'].get('tree_nodes_examined',0),num(sum(x['stages'][s]['sql_payload']['committed'] for s in ('e3Verify','e3Prepare','e3Commit')))] for x in selected]))
add('정상 completed 범위에서 full_recoveries/full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds는0이다. source의 store_publication.verifyPublicationCandidate는 유효한 same-connection base proof에서 verifyIncrementalGeneration으로 가고, prepare는 incremental receipt의 네 root만 pin한다. commit은 작은 accepted metadata CAS/usage/guard→native COMMIT/readback이다. incremental_verification의 checked/hotRow는 실제 hot/참조110행과 changed tree/facts를 검사한다. H행 검증에서 같은 bounded leaf의 C1 span이 반복되어 약16MB validation이 생길 수 있으나 전체 역사 N행 재검증은 아니다. 실제 span을 줄여 기록하지 않았다. 몇 점의 wall trend를 O(1) 증명으로 부르지 않으며 100k I25는 미확인이다.')
if stagepairs:
 add('50k 별도 진단은 같은 accepted base와 Target에서 공개 E2/E3 API를 직접 호출했다. prepare 뒤 discard했으며 accepted ID/previous/sequence/Target 불변을 assertion했다. 이후 실제 게시는 원 AppState guard를 사용했고, 사전 취득으로 cache가 warm해진 해당 publication은 정상 비용 cell에서 제외했다.')
 add(table(['작업','E2 OFF/ON s','E2 비율','E3 verify OFF/ON s','E3 verify 비율','prepare OFF/ON ms'],[[op(x['kind']),f"{seconds(x['OFF']['E2_acquire_api_us'])}/{seconds(x['ON']['E2_acquire_api_us'])}",f"{x['ratio']['E2_acquire_api_us']:.3f}",f"{seconds(x['OFF']['E3_verify_api_us'])}/{seconds(x['ON']['E3_verify_api_us'])}",f"{x['ratio']['E3_verify_api_us']:.3f}",f"{x['OFF']['E3_prepare_api_us']/1000:.3f}/{x['ON']['E3_prepare_api_us']/1000:.3f}"] for x in stagepairs]))
 add('E2 API wall은 transport·E1·검증을 포함하며 기존 verification_us도 별도로 남겼다. 이를 순수 parser CPU로 바꾸지 않는다. E3 API stopwatch와 proof 자체 verificationMicroseconds를 함께 보존했다. stage별 E2_work/E3_verify_work가 acquisition과 publication 관측을 분리한다.')
add('## 교란 판정·100k 실행 판단')
add(f"**{dec['perturbation_classification']}**. {dec['perturbation_ko']}")
add(f"**100k: {dec['decision']}**. {dec['decision_ko']} {dec['projection_ko']}")
add('[별도 최소 성능 후보](benchmarks/t66f-b04/performance-candidate.json)는 ObservationRepository._lookup의 동일 hot body 두 decode를 함수 내부의 한 로컬 map으로 공유하는 것이다. 모든 context/projection/auth/TTL/canonical·terminal 검사는 유지하는 후보이며 이번에는 구현하지 않았다. 성공 object packet3174개에서 source상 최소554,586,672B의 중복 primary span 제거가 예상되지만, 실제 wall/CPU 절감이나100k 완료를 증명한 값이 아니다. admission과 terminal의 큰 시간 안에서 어느 성분이 줄어드는지는 같은50k 대응 측정으로 검증해야 한다.')
add('역사 P03는 **HISTORICAL FULL-SCALE FAILURE — NOT REPEATED**다. 397,146/400,532 객체, 세 관측 만료, 2,699.957907초, E3/E4 미완료, 원 matched backend/client SQLite 부재를 유지한다. 당시 backend handler 합은 '+f"{hist['backend_wall_total_s']:.6f}초, process CPU {hist['backend_cpu_total_s']:.6f}초, client SQL 경계 합 {hist['SQL_API_boundary_total_s']:.6f}초, row callback 하한 {hist['callback_lower_bound_total_s']:.6f}초다. SQL에 callback이 포함되고 handler는 HTTP wait와 겹치므로 더하지 않는다. 실패 원인을 instrumentation 하나로 단정하지 않는다. [원 raw 연결·수치](benchmarks/t66f-b04/historical-p03.json)를 보존했다.")
add('## 검증·정리·남은 의무')
add(checks['summary_ko'])
add('source-SHA guards와 전체 reconstruction 바이트/mode, 시작 index/기존 파일 보존을 마지막으로 확인했다. 전체 backend/Flutter·과거 cancellation lifecycle·IA01–IA07 재감사는 반복하지 않았다. B03 correctness 폐쇄를 작은 성능 fixture로 재판정하지 않았다.')
add(cleanup['summary_ko'])
add('남은 바인딩 의무는 100k의 fixed-H/D 정상 cost cell·large-N I25와 §35의 완전한 rows-read/HTTP·압축·framing 비교다. VM visit 세분화·추가 cold 표본·실제 UI 완료·generation의 대응 ON/OFF·exclusive observer CPU 분리는 추가 측정/진단 과제이며, 규범에 없는 숫자 표본 수나 합격선을 새 바인딩으로 만들지 않는다. Android memory/VFS·physical I/O·hardware power loss는 미검증이다. R1 large restore는 DEFERRED, R1 activation·B01/B02/B03는 CLOSED, production deployment는 NOT AUTHORIZED다. 전체 Phase B는 INCONCLUSIVE다.')
add('다음 행동: **'+dec['next_action_ko']+'**')
add((E/'footer.txt').read_text())
(R/'docs/t66f-b04-phase-b-measurement-feasibility.md').write_text('\n\n'.join(text)+'\n')
print('한국어 B04 보고서 작성 완료')

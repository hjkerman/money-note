# T6.6F Phase B 독립 전층 검증

## 01. 대상·판정 경계

시작 감사 commit은 `a7d045f3a73e8b1cd46faf0946251d712a5d6448`, 대상 제품은
`af9525e20e6df1dd7dfc152d3db79c1eb07925d2`다. 제품 구현을 수정하지 않는 감사다.
필수 backend 전체 회귀가 두 번 같은 assertion에서 실패하여 현재 Phase B 판정은
**INCONCLUSIVE**다. 새 독립 통합 증거와 이전 PASS는 이 미해결 gate를 대체하지 않는다.

## 02. Git·원격·source identity

변경 전에 AGENTS와 필수 도메인·신뢰 경계·Offline·security/runbook을 확인했다.
HEAD/main/origin/main/실제 `git ls-remote origin refs/heads/main`은 모두 시작 hash였다.
최초 작업 트리는 clean이었다. coverage 파일 추가 후 hash 기록 시의 untracked 상태와 구별한다.
제품 commit에서 시작 감사 commit까지 `backend`와 `mobile/lib` diff는 0이다.
[inventory.json](benchmarks/t66f-phase-b/inventory.json)에 실제 Git blob/SHA-256과 원격 조회를 기록한다.

## 03. Phase A 증거와 역사적 FAIL

**PRIOR AUDIT EVIDENCE:** 원 Phase A `7fc5420`의 E4-A01 MEDIUM FAIL,
후속 `5ad7bc8`의 E4-RA01 MEDIUM FAIL은 그대로 보존한다. 최종 RA01 독립 보고서는
두 finding CLOSED, Phase A blocker closure PASS와 이전 결과를 기록한다.
현재 소스가 그 최종 제품과 동일함을 확인했으며, 원 반례 assertion도 재실행한다.

**IMPLEMENTATION-SIDE CLAIM:** 이전 구현·교정 보고서의 1,503 Flutter/1,315 backend와
I25·Frozen 비용 주장을 현재 결과로 전용하지 않는다.

## 04. Binding F coverage matrix

대규모 회귀 전에 [B0 matrix](benchmarks/t66f-phase-b/coverage.md)를 작성했다.
전체 39개 절, I1–I25, §26 Android 증명, §31 R1, §33 legacy/rollback,
§34 stage dependency, §35 고정 H/D scaling·압축 비교를 포함한다.
별도 F 전용 규범 파일은 현재 문서 지도에서 발견하지 않았다.

§34는 R1 → isolated interoperability/full-resync/crash → 성능 gate → 독립 F 감사 → rollout을
구별한다. 이번 D/E 구현 범위의 검증 결과를 전체 T6.6F exit나 R1 완료로 확대하지 않는다.

## 05. 전체 D→E 구현 inventory

| 경계 | 실제 구현 | 입력·출력·소유권 |
|---|---|---|
| D1 | `backend/isolated_sync/capture.py` | 실제 row trigger·old/new cells·deferred fence; source와 같은 transaction |
| D2a | `canonical.py`, `raw.py`, `segments.py`, `facts.py`, `patricia.py`, `roots.py`, `rebuild.py` | C1/typed Ref/B+tree/complete F(raw)/Patricia |
| D2b | `store.py`, `maintenance.py`, `inputs.py`, `finalization.py` | captured diff→roots/index/input proof; COMMIT 전 certificate |
| D3a | `observation.py`, `observation_schema.py`, `artifacts.py` | original credential→coherent Target/manifest·lease |
| D3b | `http.py`, `transfer.py`, `workers.py` | 실제 authenticated typed path/offset/length POST; bounded native worker |
| D3c | `retention.py`, `retention_schema.py`, `owned_sqlite.py` | expiry/release/live roots/명시 synthetic maintenance GC·actual DB FD |
| E1 | `c1.dart`, `protocol.dart`, `object.dart`, `store.dart` | 받은 exact bytes→hash/shape/namespace 검증→immutable SQLite |
| E2 | `transport.dart`, `api_transport.dart`, `fetch.dart`, `graph.dart` | authenticated observation→typed graph closure→durable staging |
| E3 | `verification.dart`, `incremental_verification.dart`, `patricia_edit.dart`, `store_publication.dart` | complete F/raw/hot proof→receipt→current AppState fence→accepted COMMIT |
| E4 | `store_read.dart`, `store_frozen.dart`, `adapters.dart`, `workspace.dart`, `AppState` | pinned read/legacy export/current-ticket install/Frozen source·lineage |

D3b가 전송이고 D3c가 retention이다. 관측 응답 자체가 manifest이며 별도의 manifest GET은 없다.
각 외부 Ref는 parent의 검증된 bytes에서 도출한다. hash는 인증이나 금융 계산 증명으로 쓰지 않는다.
입출력·identity·persistence·실패/경쟁·다음 소유자의 상세 trace와 현재 binding coverage는
[boundary-trace.md](benchmarks/t66f-phase-b/boundary-trace.md)에 기록한다.

## 06. 실제 HTTP harness와 독립성

**NEW INDEPENDENT PHASE B EVIDENCE:** 새 [server.py](benchmarks/t66f-phase-b/server.py)는
NEW RetentionSandbox와 synthetic principal/token을 만들고 실제 `create_app()`을 Uvicorn TLS에
연결한다. [harness.dart](benchmarks/t66f-phase-b/harness.dart)는 실제 MoneyNoteApiClient/
IOClient/HttpClient로 통신한다. pipe는 fixture·clock·barrier·oracle 제어이며 객체 전송은 HTTP다.
자가 서명 인증서 허용은 해당 새 loopback host/port 하나에 한정된다.

backend source SQL→독립 typed child extraction/C1/SHA→실제 HTTP→client SQL body bytes를 비교한다.
별도 [state oracle](benchmarks/t66e4-audit/state_oracle.py)의 독립 F(raw)/Patricia/v7/lineage 검사도
실행한다. 이전 oracle 재사용과 새 통합 시나리오를 구별한다.

## 07. Wire contract

실제 경로는 POST observations, POST observations/{id}/objects, DELETE observations/{id}다.
Bearer selection·원 token hash/principal·request UUID·protocol 1·NS/versions·Target/sync_root·
typed Ref/offset/length·strict padded base64·원 canonical bytes를 소비한다.
201 신규/200 같은 nonce/204 release, no-store·JSON response를 실제 observer에서 기록한다.
capabilities는 명시 404이며 large_restore를 허위 광고하지 않는다.

## 08. 금융 내용·canonical bytes

실제 11개 table과 12개 projection을 backend-produced oracle과 비교한다. raw bytes는
client objects 테이블에서 별도 연결로 꺼내 backend bytes와 직접 비교한다. expected closure는
클라이언트의 completeness flag로 만들지 않는다. 전체 materialization은 backend SQL exporter의
정렬과 기존 v7 hash를 oracle로 삼는다. 비교용 legacy producer만 isolated version/trigger gate를
시험 profile에 맞추고 날짜·문구 선택을 고정한다. 금융 코드·raw admission·hash를 대체하지 않는다.

## 09. Monetary·Unicode

필수 `"\u001c+0001000.00\u001f"`는 backend raw 설정, canonical leaf, 실제 transfer,
E1 body, E3 accepted graph, E4 materialization에서 원문을 보존한다. local exactMoney의
거부 계약은 별도로 확인한다. 한글·emoji·combining sequence·BMP/supplementary key,
null과 historical integral REAL은 bytes/typed 결과/legacy Snapshot에서 구분한다.
숫자가 같다는 이유로 raw representation이나 lineage identity를 합치지 않는다.

## 10. Graph closure·F(raw)·hot/raw

table roots와 internal/leaf, Patricia node/leaf, hot/control의 전체 reachable set을 backend SQL
oracle과 비교한다. independent F(raw)와 canonical Patricia root도 대조한다.
source-independent 금융 재계산은 추가하지 않는다. hot의 전체 backend projection을 직접 비교하고
E3의 shared-field/raw-context 검증과 complete receipt를 실제 persisted state에서 검사한다.

## 11. 부정 integrity·context

실제 handler가 만든 응답에 한정된 test-only wire fault로 wrong principal/epoch/version/root,
malformed JSON, wrong immutable bytes/ref, wrong observation을 주입한다. accepted null/seq=0,
installed/frozen 부재와 source 부재를 직접 SQL로 확인한 후 같은 client의 정상 취득을 검증한다.
실제 다른 인증 principal의 유효한 서버 Target도 기존 principal cache로 들어가지 못한다.
실제 명시 epoch bootstrap 뒤 old lease **409/EPOCH_CHANGED/full_resync**, new-context 설치 거부와
기존 Frozen 보존을 검사한다. 이는 실제 backend process restart의 410 결과를 주장하는 사례가 아니다.

## 12. Cold·empty synchronization

비어 있는 client store에서 실제 generation의 모든 필수 객체를 받아 E3/E4에 도달한다.
별도의 empty financial dataset은 required settings를 유지하면서 비어 있는 각 금융 tree의
유일한 empty-root 표현과 complete table coverage를 검사한다. 부분 Snapshot을 empty authority로
승격하지 않는다.

## 13. Identical·localized·structural deltas

G1 cold → 동일 내용 → 한 행 변경 → 여러 localized 변경 → 260행 insert/split → delete →
후속 작은 변경을 실제 D1/D2b COMMIT으로 만든다. 각 전이의 실제 요청 hash 집합은 독립
backend target closure에서 이미 보유한 객체를 뺀 집합과 같아야 한다.
동일 Target의 객체 payload 요청 0과 observation/release HTTP는 구별한다.

## 14. E2 cache·resume·expiration/churn

E1 hash-on-read를 거쳐 reuse하며 오래된 stored flag만 신뢰하지 않는다.
실제 4개 객체를 durable 저장한 뒤 다음 response에서 취소하고 새 store handle/current ticket으로
오직 missing objects를 다시 받는다. 실제 전송 중 lease expiry와 generation churn에서는 fresh
observation으로 돌아가고 새 closure와 정확히 일치해야 한다. stale staging은 authority가 아니다.

## 15. HTTP response 수명

실제 backend 객체 response의 declared length를 거부하고 body를 stall시킨다.
같은 limit=1 IOClient에서 6회 거부 후 `/proc/self/fd` socket inode와 `/proc/net/tcp`의 remote port를
교차 관측한다. E2가 lease DELETE를 수행한 뒤 idle socket 1개가 남는 것과 누수를 구분한다.
후속 정상 C1/hash-verified transfer까지 같은 client를 사용한다. 잘린 실제 object HTTP response도
bounded retry 후 완전한 bytes만 저장해야 한다. 원 E2-A01 독립 OS socket 검사도 재실행했다. 실제 6회 FD는
**[1,1,1,1,1,1]**, 거부 시간은 **[769,809,781,696,688,684]ms**, 원 오류는 모두
`RESPONSE_SIZE_EXCEEDED/blocked`였다. 정상 follow-up도 같은 client에서 성공했고 idle FD는 1이었다.

## 16. E3 original authority·final COMMIT

`AppState:426/516/680`은 기존 coordinator에서 E2 전 original ticket을 얻고 끝까지 유지한다.
`store.dart:270`은 BEGIN IMMEDIATE→schema→body/quota/fault→final fence→동기 COMMIT이다.
`store_publication.dart:369`의 receipt/base/sequence/root 준비도 같은 writer transaction이다.
final guard 뒤 await·새 ticket·UI callback·deferred commit 경로는 없다. private sqlite3 handle에
application commit hook/UDF를 등록하는 코드도 없다. post-COMMIT readback 실패와 pre-COMMIT
rollback을 구분한다. 저장 seq를 현재 AppState authorization으로 대용하지 않는다.

## 17. E4 installation authority

acquisition 중 logout/credential/offline/newer legacy request/cancel, E3 acceptance 직후 credential
교체를 실제 barrier로 검사한다. returning error만 보지 않고 accepted/installed/source/B/pending/
frozen rows를 대조한다. old-session complete cache가 남는 것과 새 session의 설치 권한은 다르다.
E3 receipt는 E4 설치 authorization이 아니다.

## 18. E4-A01·RA01

원 이전 재감사 test와 RA16–18을 변경 없이 재실행한다. 새 real-HTTP A/B scenario는
canceled A의 finally recovery를 metadata await에서 멈춘 뒤 B의 성공 후 재개하고 source/B/pending/
pins가 그대로인지 확인한다. RA01의 null predecessor는 genuine initial/이미 COMMIT된 current
source의 obsolete hint와, 다른 미설치 target의 필수 predecessor를 구분한다.
이미 손실시킨 복구 증거를 fabrication으로 수선하지 않는다. 명시 Frozen read와 startup repair의
실패/성공 경계를 분리한다.

## 19. Source ownership·SQL fencing

`workspace.dart:221/269/379/482`는 actual installed UUID/seq, namespace, Frozen binding,
정확한 current source map과 복원 대상 소유권을 검사한다. `store_frozen.dart:44/130`은
source 준비/복원을 같은 SQLite writer transaction과 final fence에 묶는다.
같은 financial source 내용은 다른 operation UUID나 lineage를 대체하지 않는다.
이 보장은 owning AppState/isolate의 협력 파일 변경과 실제 다중 SQLite 연결 범위다.
임의 비협력 filesystem attacker의 rename CAS를 입증했다고 주장하지 않는다.

## 20. Frozen pins·lineage·retention

G1을 legacy/Frozen으로 설치하고 G2 native accepted/installed를 실제 전송·게시해도 G1의
receipt/root/pins/B identity가 남아야 한다. 별도 SQL closure와 fresh process read로 확인한다.
accepted, previous, durable Frozen과 temporary read snapshot의 수명을 혼동하지 않는다.
new accepted root를 옛 v7 lineage로 조용히 재결합하지 않는다.

## 21. Pending B/J

unknown online marker bytes를 실제 설치·실패·재시작 사이에 그대로 비교한다.
이미 backend에 같은 금융 내용이 있는 Frozen B 위에 두 input-only J operation을 저장하고
UUID·sequence 1/2·payload 원문을 유지한다. 명시 nonpublishing E2 취득이나 거부된 Offline 설치는
ACK/rebase/retirement를 만들지 않는다. 이 isolated 호출을 normal OFFLINE 동작으로 활성화하지 않는다.

## 22. Cross-store consistency

SQLite accepted/installed/frozen/pins와 source/B/J 파일은 하나의 transaction이라고 주장할 수 없다.
preparation→guarded source/B rename→Frozen finalization→native installed→permitted marker retire의
회복 프로토콜을 검증한다. 새 request의 source를 과거 recovery가 복원하지 못해야 하고,
COMMIT 전 실패와 COMMIT 후 readback 실패를 구분해야 한다.

## 23. 실제 process crash

새 backend child는 capture 전후/finalize 후/COMMIT 후의 정확한 barrier에서 실제 SIGKILL한다.
새 Flutter child는 실제 backend G1 설치 뒤 parent가 G2를 COMMIT하고, E3 acceptance 후,
source rename 전, native COMMIT 직전, 설치 후 API return 전에 종료한다.
actual PID/signal, 별도 SQLite의 receipt/F(raw)/root/pins와 fresh process Frozen read,
B/pending SHA를 기록한다. exception injection과 구분하며 hardware power loss를 주장하지 않는다.

## 24. Backend concurrency·DB identity

실제 5개 TLS 요청은 worker/lease budget 아래 bounded retry 또는 visible 503/429로 종료하며
committed Available 수와 실제 root pin 수가 일치해야 한다. release 후 새 유효 요청을 확인한다.
별도 SQLite writer lock 동안 503/retry_same, 해제 후 같은 nonce 201→200도 확인한다.
원 D3C-A01 actual-open DB replacement 반례와 기존 worker-lifetime 회귀를 재실행한다.
지원하지 않는 production hot-swap이나 공격자 filesystem 변경 보장으로 확대하지 않는다.

## 25. Independent cost 방법

[measure.py](benchmarks/t66f-phase-b/measure.py)는 임시 mobile source copy에서 실제 sqlite3
delegate/returned rows/BLOB bytes/pin I/D/U를 관찰한다. 제품 work counter는 oracle로 쓰지 않는다.
backend connection은 실제 SQLite statement trace를 정규화해 세며 trigger 반복 trace를 VM/row
수로 부르지 않는다. generation 작업량은 별도 SQL before/after immutable set과 finalizer trace로
측정한다. oracle의 full scans는 측정 구간 밖이며 서로 다른 timing을 더하지 않는다.

## 26. I25·전층 작업량

현재 완료된 두 fixture는 160→1,158 reachable objects다. identical real sync는 객체 요청 0,
HTTP 3, backend SQL trace 2,021, client SQL 796으로 동일했다. localized change는 실제 payload
객체 10→15, client SQL 1,350→1,568이며 full verifier는 0이었다.
D2 mutation은 신규 immutable 9→14, SQLite trace 881→1,037이다.
이는 고정 H/D와 bounded leaf/changed paths의 HOST 증거이며 전체 §35 1k/5k/10k/50k/100k grid의
완료나 production-scale latency proof가 아니다.

| 실제 경로 | graph 160 / graph 1,158 | HTTP requests | decoded object payload bytes | E1 INSERT | client SQL | pin I/D/U |
|---|---|---|---|---|---|---|
| cold native | 160 / 1,158 objects fetched | 163 / 1,161 | 99,898 / 741,950 | 160 / 1,158 | 6,603 / 43,535 | 4/0/0 / 4/0/0 |
| identical native | 0 / 0 objects fetched | 3 / 3 | 0 / 0 | 0 / 0 | 796 / 796 | 4/4/0 / 4/4/0 |
| localized native | 10 / 15 objects fetched | 13 / 18 | 17,299 / 162,191 | 10 / 15 | 1,350 / 1,568 | 4/0/0 / 4/0/0 |
| unchanged Frozen read | 0 / 0 objects fetched | 0 / 0 | 0 / 0 | 0 / 0 | 66 / 66 | 0/0/0 / 0/0/0 |

cold HTTP entity bytes는 180,194 / 1,310,856, identical은 2,934 / 2,936,
localized는 28,760 / 223,328이다. entity와 decoded payload, SQLite body read bytes는 서로 다른
측정이다. identical native의 body read는 29,496 / 171,655 bytes이며 raw node 4개·index node
2개, raw row 11 / 259다. bounded leaf packing(최대 256행)과 hot/raw verification 때문에
일부 leaf 내용은 읽는다. 이를 full-history scan이나 zero raw reads라고 부르지 않는다.

cold elapsed는 50.017 / 561.249초, identical 1.323 / 1.857초, localized 4.454 / 10.751초다.
반복 Frozen 한 표본은 39.450 / 39.606ms다. 병행 회귀 중 HOST single sample이며 median/p95·
실기기 latency 목표 통과가 아니다. 기록한 RSS는 Flutter/test process의 현재 RSS이며 순수 제품의
peak-memory로 주장하지 않는다. 실제 DB main/WAL/SHM 크기와 source fixture root는 별도 D2
`evidence/generation-cost-final__*.json`에 보존한다. 원 graph 전체 oracle는 측정 구간 밖이다.

## 27. Frozen-B repeated work

두 크기 모두 반복 read는 66 SQL·9,523 object bytes, raw/index node 재검증·full verifier·
legacy full read/lineage hash·pin I/D/U는 0이었다. unrelated native G2 후에도 같다.
fresh handle은 1,153→7,159 SQL과 full verifier 1회다. 이는 허용된 cold/reopen fallback이다.
historical 64/9,451은 과거 결과로 보존한다. **원 cost fixture의 현재 재실행**에서는
Frozen pending warm1/warm2/unrelated-accepted가 history 5와 512 모두 **85 SQL / 9,451 bytes**였다.
과거 대비 +21 SQL의 규모 독립적인 증가를 숨기지 않는다. full verification·raw/index 재검증·
pin 쓰기는 여전히 0이며 bounded metadata guard가 정상 반복마다 whole-graph 작업을 만드는
증거는 없다. 새 실제 HTTP fixture의 `readFrozenBaseline` 66/9,523과, 원 fixture의
`readFrozenPending` 85/9,451은 서로 다른 API·데이터다. 이 수치를 혼합하지 않는다.

## 28. Default application isolation

normal AppState/OfflineStore/refresh는 기존 authoritative-state 경로를 쓴다. segmented entry들은
명시 isolated API이며 startup/UI가 자동 호출하지 않는다. backend app.main과 production artifact에
isolated sync가 mount되지 않는다. 정상 SQLite CURRENT_SCHEMA_VERSION=4, Snapshot v7,
OfflineBaseline v4와 input-only B/J는 불변이다. segmented accepted generation은 Offline-ready가 아니다.

## 29. R1 gate

`requireSegmentedOfflineRecovery()`는 R1_RECOVERY_CONTRACT_REQUIRED로 차단하고,
실제 capabilities도 404다. R1 large restore/MW·resource proof·migration/rollback은 이번에 구현하거나
완료했다고 주장하지 않는다. debug build는 회귀일 뿐 설치/activation 승인이 아니다.

## 30. 새 독립 사례·원 회귀

새 독립 사례는 **49 PASS / 0 FAIL / 0 INCONCLUSIVE**다. 실제 TLS 통합 33,
실제 D→E SQL 계측 2, backend 6, Flutter SIGKILL 4, TLS concurrency 2, D2 계측 2다.
backend 6개 중 SIGKILL 3개와 Flutter 4개를 합친 실제 process-termination 부분집합은 7 PASS다.
동시성/authority 부분집합은 FB-A 5개 +FB05 +FB07 +FB12 +TLS concurrency 2 =10 PASS다.
이를 사용자가 열거한 모든 18개 authority scenario의 별도 신규 실제 HTTP 실행으로 부풀리지 않는다.

완료한 사례의 기대·실제·oracle는 [cases.json](benchmarks/t66f-phase-b/cases.json),
원 실행 수와 per-file 결과는 [summary.json](benchmarks/t66f-phase-b/summary.json)에 수집한다.
기존 구현 tests와 이전 독립 tests를 새 Phase B case로 세지 않는다. 한 test 안의 여러 generation
전이를 별개의 test PASS로 부풀리지 않는다. 새 실제 SIGKILL 7개도 전체 독립 사례의 부분집합이다.

감사 harness의 초기 오류도 보존한다. Flutter binding mock HTTP, nested workspace 경로,
import/field-name·immutable map·처음부터 존재하는 accepted singleton null row 처리 오류는
감사 전용 파일에서 수정했다. FB04의 첫 fixture는 이미 COMMIT된 current native source의
obsolete hint를 지웠으므로 null이 정당한 상태였다. 새 미설치 G3 target에 대해 필수 predecessor를
누락시키는 fixture로 교정하고 같은 source-preservation assertion을 적용했다. FB19의 명시 epoch
bootstrap 응답은 규범 §17의 409이며, 처음 410을 기대한 감사 fixture가 잘못됐다.
이 변경들은 기존 독립 반례나 제품을 고친 것이 아니다. 최종 단일 33-case campaign으로
교정한 harness 전체를 다시 실행하며, 앞선 실패 로그의 hash/오류를 집계에 남긴다.

원 Phase A 비용 2개와 RA01 비용 4개를 새 측정과 별도로 실행하여 모두 PASS를 확인했다.
원 Phase A 45개는 Dart 36 + actual crash 6 + compatible P0 replay 1 + 원 cost 2의 합이다.
이전 A01 correction 28개는 mobile 21 + concurrent 1 + actual crash 6이며,
RA01 correction 51개는 mobile 42 + native cost 2 + actual crash 7이다.
RA01 cost suite의 나머지 2개는 이전 A01 독립 재감사의 cost이며, 기존 Dart 18개와 합쳐
원 targeted re-audit 20개를 재실행했다. 각 분류는 부분집합이 겹치므로 새 사례나 full Flutter 수에
다시 더하지 않는다. mobile 부분은 최종 전체 Flutter 실행의 per-file 종료 결과로 확인한다. 기존 비용 fixture의
`ORDER BY hash LIMIT 1` corruption 선택이 실제 Frozen closure 밖의 객체를 잡을 수 있다는
역사적 한계도 삭제하지 않는다. 해당 한계는 현재 Frozen integrity 검사를 면제하지 않는다.
새 corruption/closure 검사는 명시한 필수 객체와 독립 complete oracle를 사용한다.

## 31. 전체 Flutter·backend 회귀

| 실행 | 실제 결과 | 처리 |
|---|---|---|
| 첫 full Flutter | 1,501 PASS / 2 FAIL / 2 SKIP | `after_frozen_prepare`, `after_source_prepare` actual child barrier timeout 보존 |
| full Flutter 재실행, concurrency=2 | **1,503 PASS / 0 FAIL / 2 SKIP**, done=true, exit=0 | 종료한 현재 회귀 결과 |
| 첫 full backend | **1,314 PASS / 1 FAIL**, 1,540 subtests PASS | concurrency status assertion 실패 보존 |
| 문제 backend test 단독 | 1 PASS | 전체 gate 대신 사용하지 않음 |
| full backend 재실행 | **1,314 PASS / 1 FAIL**, 1,540 subtests PASS | 같은 test 실패; 필수 gate 미충족 |
| 기존 원 Phase A | 45 PASS | 원 Dart/real crash/replay/cost 분리 집계 |
| 기존 A01 correction | 28 PASS | mobile21 + concurrent1 + crash6 |
| 기존 RA01 correction | 51 PASS | mobile42 + native cost2 + crash7 |
| 이전 targeted re-audit | 20 PASS | Dart18 + independent cost2 |
| E4 authority/race | 51 PASS | handoff35 + adapter authority16 |
| E4 process crash | 36 PASS | mobile17 + 원6 + A01 6 + RA01 7, 모두 실제 child 종료 |
| P0 | mobile183 + 독립 integration18 + compatible replay1 PASS | 본래 local-input 계약과 raw 보존 회귀 |
| E2 cleanup | 독립 OS socket9 + correction external5 PASS | mobile response cleanup13도 full suite에 포함 |
| D3c DB replacement 원 반례 | 1 PASS | 기존 test를 변경 없이 disposable DB로 실행 |
| scripts / frontend | 27 PASS / 21 PASS, npm build PASS | product source 불변 |

E1 original 96 및 correction211, E2 original124와 cleanup, E3 publication/authority/crash,
I25 correction47, E4 original163, Frozen B/J·Snapshot v7·OfflineBaseline v4·AppState suites는
최종 full Flutter의 per-file 결과에 포함한다. 47 I25는 publication30 + incremental6 + root-pin2
+baseline1 + root-pin-mode crash8의 부분집합이다. E3 crash 전체16도 통과했다.
위 숫자는 겹치는 부분집합이며 1,503 또는 새49에 다시 더하지 않는다.

Flutter 첫 두 timeout의 정확한 환경 원인은 확정하지 않았다. rerun PASS로 과거 실패를
지우지 않는다. backend의 JUnit 2,855 entries는 main tests1,315 + subtests1,540이므로
2,855개를 main tests로 부풀리지 않는다. analyze/build/format/Ruff/compileall의 종료 결과는
최종 summary와 footer에 별도로 기록한다.

## 32. 역사적 실패 분류

원 Phase A/A01/RA01 FAIL 문서는 불변이다. P0 진단의 historical 3 PASS/2 FAIL는 pre-P0
expectation을 보존한 자료이고, 과거 git path enumeration fixture error는 현행 monetary contract
위반 증거가 아니다. 보존 SHA와 compatible replay의 실제 실행을 별도로 확인한다.
backend concurrency 변동성도 과거 기록과 현재 첫 실패/선택 재현/전체 재확인을 모두 남긴다.

## 33. Findings

새로 확정한 제품 CRITICAL/HIGH/MEDIUM/LOW correctness finding은 0이다.
**F-BV01 / INFORMATIONAL — 필수 전체 회귀의 미해결 동시성 검증 실패**를 별도 기록한다.
이는 제품 데이터 손상이나 authorization 위반을 확정한 finding이 아니며, Phase B PASS를 막는
검증 gate다.

- 위치: `backend/tests/test_isolated_sync_transfer.py:497`; 관련 response mapping은
  `backend/isolated_sync/http.py:178–222`, lock limit은 `observation.py:121/266`이다.
- 요구: 사용자 §28/34의 필수 전체 backend 회귀 PASS와 binding §17의 정확한 error/retry semantics.
- 재현: disposable backend 전체 suite를 두 번 실행했다. 두 번 모두
  `test_bounded_concurrent_quota_and_same_request_status`가 5개 동시 요청 중
  `[201,201,201,201,429]` 대신 `[201,201,201,201,503]`을 관찰했다.
- 기대/실제: 원 assertion을 수정하지 않았으며 두 실행 모두 **1,314 PASS / 1 FAIL**,
  **1,540 subtests PASS**다. 그 사이 단독 실행은 1 PASS였다.
- 독립 증거: `summary.json`의 두 JUnit 실패, `evidence/backend-full.log`,
  `evidence/backend-rerun.log`를 보존한다. 새 로그의 행 끝 공백만 제거해 diff check를 만족시키고
  원문/저장본 SHA를 `summary.json`의 `text_log_preservation`에 따로 기록했다.
  assertion·status·오류 내용은 바꾸지 않았다. 새 실제 TLS writer-conflict test는
  503/retry_same과 이후 201→200을 관찰했지만, 원 실패의 response body/정확한 wait 원인은
  원 로그에 없다.
- 해석: 규범은 503/ROOT_NOT_READY/retry_same을 허용한다. 따라서 status 하나만으로 제품
  correctness defect를 선언하지 않는다. 반대로 단독 PASS나 이전 감사 PASS로 전체 실패를
  지울 수 없다. 병행 부하·SQLite lock/timeout 가능성은 **UNVERIFIED ASSUMPTION**이다.
- 영향: 필수 회귀 gate 미충족. 이 증거에서 committed data corruption, lease leak, 권한 우회는
  확인되지 않았다.
- 최소 후속 조치: 실패 응답 body와 worker/SQLite wait 근거를 보존하는 결정적 재현으로 원인을
  확인하고 필요한 교정 후 원 assertion을 유지한 전체 회귀를 재검증한다. 이번 감사는 product나
  원 tests를 수정하지 않는다.
- gate: Phase B **INCONCLUSIVE**, 전체 T6.6F 완료 선언 차단. R1 미구현은 별도 prerequisite이며
  이 finding의 제품 defect로 분류하지 않는다.

## 34. 한계

HOST synthetic 범위다. 실제 Android VFS/I/O/power loss, 모든 거대 graph 크기의 §35 grid,
gzip/Brotli 비교와 실기기 gate, R1의 >25MiB upload/atomic apply/backup/resource 증명은
이번 D/E 결과만으로 완료되지 않는다. 전체 scaling/compression grid는 미수행이며 물리적으로
실행 불가능함을 입증했다는 뜻도 아니다. 원 51개 authority/race 회귀와 새 결정적 실제 HTTP
barrier 사례를 실행했지만 사용자 18-row matrix 모두를 별도 새로운 실제 HTTP 시나리오로
전수 구성하지 않았다. 새 부정 wire 8개도 모든 protocol negative의 독립 주입을 뜻하지 않는다.
이 범위 밖 증거는 기존 suite 재실행·source inspection 또는 미검증으로 구별한다.
finite test corpus로 전체 입력 언어/모든 scheduling 동치를
주장하지 않는다. 현재 source는 bounded path 및 fail-closed 계약의 추가 근거다.

## 35. 실제 T6.6F exit

Phase B 구현 범위의 판정, 전체 T6.6F completion, R1 readiness, 일반 사용자 activation,
deployment는 별도 결정이다. §31/34/35의 잔여 prerequisite가 있으므로 전체 T6.6F exit를
SATISFIED로 표시하거나 완료를 선언하지 않는다.

## 36. Production 안전

자가 소유 임시 SQLite·test principal·loopback TLS만 사용했다. production API/DB/credential,
service/migration/deploy, APK 설치·배포, 일반 사용자 segmented activation을 수행하지 않았다.
실제 운영 상태를 접속 조사했다는 주장도 하지 않는다. 제품 source/configuration 변경은 0이다.

## 37. Audit-only diff·source 보존

새 `docs/benchmarks/t66f-phase-b/`와 이 보고서만 감사 소유 변경이다. 원 source/report hashes,
원 실패 반례와 P0 5개 diagnostic의 보존을 확인한다. 변경 파일 formatting/Ruff/compileall/diff와
Git staged inventory를 최종 확인한 뒤 audit-only commit/push한다.

## 38. Commit·push 및 최종 판정

이 문서를 최초 추가한 commit은 `git log -1 --format=%H -- docs/t66f-phase-b-independent-verification.md`로
확인할 수 있다. self-referential hash를 문서에 추측해 넣지 않는다. 실제 최종 HEAD/main/origin/main/
remote 및 clean 여부는 commit/push 뒤 재확인하고 최종 응답에 기록한다.
새 49개·full Flutter의 done/exit·build exit·raw evidence guard를 통과한 summary를 검토했다.
현재 결과는 **INCONCLUSIVE — T6.6F PHASE B VERIFICATION BLOCKED**다.
E4-A01/RA01의 기존 closure는 source 동일성과 원 반례/새 HTTP/회귀 증거 범위에서 유지한다.
원 Phase A FAIL 보고서는 역사적으로 그대로 FAIL이며 Phase B PASS를 발행하지 않는다.

이번 commit 대상은 이 보고서와 새 `docs/benchmarks/t66f-phase-b/`뿐이다. 제품·원 tests·역사적
보고서·진단 파일은 수정하지 않았다. commit/push 후 최종 4개 ref와 clean 상태는 최종 응답에서
실제 hash로 보고한다. 감사 commit을 제품 구현·배포·activation 승인으로 해석하지 않는다.

analyze·debug build·감사 파일 formatting·Ruff·compileall·npm build·diff check는 PASS다.
전체 formatting은 `--output=none`에서 기존 10개 차이를 확인했고 파일을 수정하지 않았다.
source/report hash 64개 및 P0 원 진단 5개 보존 검사가 PASS다.

아래 footer의 D3b/D3c 항목명은 요청 형식을 따른다. 실제 manifest는 D3a observation 응답,
object transfer는 D3b, retention/release/expiry는 D3c이며 본문·harness는 실제 책임을 따른다.


## 필수 최종 상태

```text
T6.6F PHASE B INDEPENDENT VERIFICATION:
INCONCLUSIVE

STARTING PHASE A AUDIT COMMIT:
a7d045f3a73e8b1cd46faf0946251d712a5d6448

AUDITED PRODUCT IMPLEMENTATION:
af9525e20e6df1dd7dfc152d3db79c1eb07925d2

FINAL AUDIT-ONLY COMMIT:
이 문서를 추가한 commit — git log -1 --format=%H -- docs/t66f-phase-b-independent-verification.md

REPOSITORY STATE:
VERIFIED

PHASE A BLOCKER CLOSURE:
PASS

BINDING T6.6F COVERAGE MATRIX:
COMPLETE

BACKEND D1-D3C CONTRACT:
INCONCLUSIVE

FLUTTER E1-E4 CONTRACT:
INCONCLUSIVE

REAL BACKEND-TO-FLUTTER HTTP INTEGRATION:
PASS

D3A OBSERVATION:
PASS

D3B MANIFEST:
PASS

D3C OBJECT TRANSFER:
PASS

WIRE PROTOCOL COMPATIBILITY:
PASS

C1 CANONICAL BYTES:
PRESERVED

IMMUTABLE OBJECT HASHES:
PASS

GRAPH CLOSURE:
PASS

F(RAW)/INDEX CONSISTENCY:
PASS

HOT/RAW CONSISTENCY:
PASS

MIXED-GENERATION REJECTION:
PASS

PRINCIPAL/DATASET/EPOCH ISOLATION:
PASS

RAW MONETARY VALUES:
PRESERVED

UNICODE VALUES:
PRESERVED

BACKEND FINANCIAL AUTHORITY:
PRESERVED

E1 DURABLE OBJECT STORAGE:
PASS

E2 VERIFIED ACQUISITION:
PASS

E2 RESUME/CHURN:
PASS

E2-A01 HTTP RESOURCE CLEANUP:
PASS

E3 APPSTATE AUTHORITY:
PASS

E3 ORIGINAL REQUEST TICKET:
PASS

E3 FINAL GUARD TO COMMIT:
PASS

E3 ATOMIC ACCEPTED PUBLICATION:
PASS

E3 EXPECTED BASE/SEQUENCE FENCING:
PASS

E3 DURABLE RECEIPT AND PINS:
PASS

E3 I25 INCREMENTAL COST:
INCONCLUSIVE

E4 GENERATION-CONSISTENT READ:
PASS

E4 LEGACY MATERIALIZATION:
PASS

E4 INSTALLATION AUTHORITY:
PASS

E4 PREVIOUS_SOURCE VALIDATION:
PASS

E4-A01 STALE RECOVERY:
PASS

E4-RA01 INSTALLATION PROVENANCE:
PASS

E4 FROZEN PIN RETENTION:
PASS

E4 SOURCE/LINEAGE CONSISTENCY:
PASS

E4 FROZEN-B REPEATED READ COST:
PASS

PENDING B/J DURABILITY:
PASS

PENDING B/J IDENTITY AND ORDER:
PRESERVED

IMPLICIT B/J ACKNOWLEDGMENT:
NONE

AUTOMATIC B/J REBASE:
NONE

SYNC_ROOT / V7 FINGERPRINT SEPARATION:
PRESERVED

SNAPSHOT V7:
PRESERVED

OFFLINE BASELINE V4:
PRESERVED

CROSS-LAYER AUTHORITY RACES:
INCONCLUSIVE

CONCURRENT G1/G2 READS:
PASS

CROSS-STORE CRASH CONSISTENCY:
PASS

FRESH-PROCESS RECOVERY:
PASS

BACKEND CONCURRENCY/DB IDENTITY:
INCONCLUSIVE

END-TO-END INCREMENTAL TRANSFER:
PASS

END-TO-END INCREMENTAL STORAGE COST:
INCONCLUSIVE

INDEPENDENT HTTP/SQL/OBJECT COUNTERS:
PASS

COLD SYNC:
PASS

IDENTICAL GENERATION SYNC:
PASS

SMALL DELTA SYNC:
PASS

LARGE DELTA SYNC:
PASS

RECOVERY/FALLBACK:
PASS

NEW INDEPENDENT END-TO-END TESTS:
49 PASS
0 FAIL
0 INCONCLUSIVE

INDEPENDENT PROCESS CRASH CASES:
7 PASS
0 FAIL
0 INCONCLUSIVE

INDEPENDENT AUTHORITY/RACE CASES:
10 PASS
0 FAIL
0 INCONCLUSIVE

FULL FLUTTER TESTS:
1503 PASS
0 FAIL
2 SKIP

FULL BACKEND TESTS:
1315 TESTS
1540 SUBTESTS
FAIL

FLUTTER ANALYZE:
PASS

FLUTTER BUILD:
PASS

CHANGED-FILE FORMATTING:
PASS

RUFF:
PASS

COMPILEALL:
PASS

GIT DIFF CHECK:
PASS

DEFAULT FLUTTER STARTUP:
UNCHANGED

NORMAL FINANCIAL READ/WRITE:
UNCHANGED

PRODUCTION SQLITE USER_VERSION:
UNCHANGED

R1 LARGE RESTORE:
DEFERRED

R1 ACTIVATION GATE:
CLOSED

GENERAL-USER SEGMENTED OFFLINE:
NOT ACTIVATED

PRODUCTION SEGMENTED ACTIVATION:
NOT PERFORMED

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
0

NEW LOW:
0

UNRESOLVED PHASE B BLOCKERS:
필수 backend 전체 회귀 실패 1건; 추가 미검증 범위는 본문 §34 참조

PHASE B VERDICT:
INCONCLUSIVE

BINDING T6.6F EXIT CRITERIA:
NOT SATISFIED

SAFE TO DECLARE T6.6F COMPLETE:
NO

SAFE TO START R1:
NO — 실제 단계 prerequisite 검증 미완료

SAFE FOR GENERAL-USER SEGMENTED ACTIVATION:
NO

SAFE TO DEPLOY:
NO

FINAL VERDICT:
INCONCLUSIVE — T6.6F PHASE B VERIFICATION BLOCKED

NEXT ACTION:
동시성 실패의 응답 body와 SQLite 대기 근거로 원인을 확정하고 원 assertion을 유지한 전체 backend 회귀를 재검증하세요.
```

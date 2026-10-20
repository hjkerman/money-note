# T6.6F-B02-A01 대형 cold acquisition 병목 조사

> 아래 정적 설명은 측정 경계와 원본 소스 검토 기록이다. 최종 수치·판정은 같은 디렉터리의 raw evidence를 정리한 최종 보고서에서 제시한다.

## 01–03. 시작 저장소와 보존

시작 HEAD/main/origin/main/actual remote main은 `6282c1c3577c42bba9382d786745d583a5d88236`이다.
시작 dirty 상태는 의도된 미커밋 B02 구현이며 제품 변경은 `mobile/lib/src/app_state.dart`,
`mobile/lib/src/segmented/fetch.dart`, `mobile/lib/src/segmented/store.dart` 3개, 합계326+/31−다.
원 index의 staged diff는 없었다. 기존 untracked B02 보고서·측정·4개 test 및 support도 입력으로 보호한다.
`initial-state.json`은 모든 기존 비무시 파일 SHA, product SHA, logical index entries와 원 binary diff를
보존한다. 조사에서는 이 제품 파일이나 기존 테스트·역사 보고서를 변경하지 않는다.

원 `AGENTS.md`, project/domain/known issues, architecture 신뢰 경계, Offline 문서와 실제 규범을
대조했다. 서버 DB/API가 금융 authority다. 클라이언트의 hash·구조·generation·durability 검사를
금융 공식 재계산으로 확대하지 않는다. Production DB/API/credential/service를 이용하지 않는다.

## 04–06. Observation 계약과 실제 구현

**SOURCE-LEVEL INVARIANT:** T6.6C §16은 Available 시점부터 최대900초, principal별 Available4개,
원 credential/NS/Target 결합을 요구한다. §17은 active flow의 observation 재시도를 최대3회로 제한한다.
`observation.py:114`의 Limits는 lease900, lock_wait1000ms, transaction10초다. lease는 고정이며
object 요청으로 연장되지 않는다. `create`의 terminal 검증 후 `validated_at`과 `expires_at`을 함께
기록한다. 최초 generation bootstrap/대부분의 observation 구성은 이 시각 이전이다.

`_guard`는 서버 UTC를 읽으며 `_check_lease`는 `expires_at <= timestamp(now)`와 retired 상태를
검사한다. Available은 새 요청 때문에 sliding 연장되지 않는다. Transaction/lock 대기 후와 응답
준비 후에도 재검사한다. Client wall-clock bookkeeping은 server transfer 권한의 oracle이 아니다.

HTTP15초 timeout, SQLite busy1000ms, 최대900초 observation lease와 client 전체 wall time은 다르다.
E1 decode/hash/write 및 cached closure 순회 시간도 실제 lease를 소비한다. E2는 graph를 마친 뒤
같은 nonce로 manifest를 다시 받고 exact bytes와 서버 terminal auth/TTL을 대조한다. §16상 완전히
취득·검증한 coherent 관측의 local publication은 lease 이후에도 가능하지만, 현재 E2의 마지막
재조회 gate를 임의 제거하지 않는다. Partial graph를 accepted로 바꾸거나 expired lease로 계속
전송받는 방식은 허용하지 않는다.

E2는 새 관측마다 새 staging UUID를 만들며 `new_observation`에만 fresh nonce를 사용한다.
동일 nonce/body retry는 원 manifest bytes를 그대로 받아야 한다. 새 관측은 다른 generation일 수
있다. 기존 cache가 재사용 가능하다는 사실과 옛 관측·ticket의 설치 권한은 분리된다.

## 07–09. Fixture와 단독 재현

원 seed662602, fixed H(current ledger105 및 참조/descriptor), N50000, cold base=null/D0을 쓴다.
11개 raw table 합계50035행, reachable V200331/E200327, canonical130710592B, depth22,
max fanout32, 최대 object151684B다. Index-node100056/index-leaf100057가 대다수를 차지한다.
다른 쉬운 graph로 바꾸지 않는다. 각 run의 NS/epoch/root는 새 합성 DB이므로 달라질 수 있으며
서로의 cache를 결합하지 않는다. 같은 run 내부의 관측 identity/root는 raw manifest로 비교한다.

실제 `isolated_sync.http.create_app`의 TLS loopback 서버 → 실제 MoneyNoteApiClient/E2 →
E1 SQLite staging → 원 AppState isolated E3 entry를 사용한다. E3/E4는 acquisition이 완성된
경우에만 실행된다. Backend BLOB 직접 E1 삽입, fabricated accepted pointer, lease clock 고정은 없다.

원 profile의 objects500k/edges1m/metadata384MiB를 그대로 사용한다. 기본 profile과 object64MiB,
payload512MiB, manifest8MiB, pages262144, staging128, chunk1MiB, path512, C1 depth128,
request3/observations3 및 retry-delay5000ms를 변경하지 않는다. N100k는 자동 실행하지 않는다.

최초 계측은 첫 lease의 실제410을 관측한 뒤 관측2에서 TRANSPORT_FAILED로 끝났다. 조사 logger의
비대기 IOSink.flush 중 write가 StateError를 내고 원 transport가 TRANSPORT_FAILED로 매핑하는
별도 최소 재현을 보존한다. 원 raw exception은 직접 포착하지 못했으므로 동일 원인이라고 소급
단정하지 않는다. 세 번 만료됐다고 기록하지도 않는다. 최초 자료·소스는 보존하고 조사 trace만
동기 append로 바꾼 확인 실행으로 최종 per-attempt 결론을 낸다. 제품 수정은 없다.

## 10–14. 관측별 진행과 검증 경계

최종 보고서는 각 observation ID/principal/NS/root, validated_at/expires_at, 실제 HTTP 상태와
durable commit을 분리한다. Wire의 decoded bytes, HTTP entity bytes, E1 logical payload,
hash input bytes, canonical validation bytes, physical DB/WAL 크기는 서로 다르다.

**INDEPENDENT MEASUREMENT:** server ASGI capture는 status/entity/chunks/hash 재전송 여부를
관측한다. Test-only wrapper는 원 함수에 위임하며 perf_counter_ns/thread_time_ns를 쓴다.
Client Stopwatch와 server perf_counter는 각각의 timebase 안에서만 elapsed를 계산한다.
동일 host의 UTC는 lease와 조잡한 연관관계에만 쓰며 서로 다른 Stopwatch 원점을 빼지 않는다.

`WorkerBudget.acquire`는 nonblocking semaphore이며 queue가 없다. 승인이 안 되면 즉시503이다.
기존 `admission_ms`는 permit 대기가 아니라 connect/schema/권한/metadata 검사를 포함한다.
원 credential 확인의 연결1개, transfer 연결1개, 마지막 terminal 연결1개를 개별 계측한다.
Native worker 시작 대기와 BEGIN IMMEDIATE 시간을 별도로 기록한다.

D3의 PathResolver는 매 path의 root부터 typed children을 따라가며 `Store(capacity=0)`을 사용한다.
같은 packet 안의 같은 prefix도 다시 SQL read/hash/C1/local-shape 검사한다. Object.body는 decoded
mutable view를 매번 새로 만들므로 root/prefix가 같다는 이유로 자동 reuse되지 않는다.

작은 read-only 부표본은 원50k graph의141개 객체와64개 index path다. 원 PathResolver가1206개
객체를 읽고1065개 동일 검증 context를 반복했다. 이 component는 실제 HTTP/전체 D→E의 대체가
아니다. Canonical decode/validation과 hash의 inclusive 시간도 중첩해서 합산하지 않는다.

## 15–17. E1 batch, backpressure, critical path

B02의 기존 bounded batch는 최대64 entries/1MiB이며 oversized singleton만 기존64MiB cap 안에서
허용한다. Hash/C1 검증 뒤 동일 transaction에서 object/typed edges/staging progress를 쓴다.
Cached ref bytes도 envelope에 charge한다. DELETE journal + synchronous EXTRA/FK를 유지한다.
각 batch는 commit 후 다음 wave로 넘어가며 메모리 buffer를 무제한 쌓지 않는다.

`_VerificationFrontier`는 최대64 parent-derived paths와64 cached progress refs를 보관한다.
`load` → `_wave` → 실제 HTTP → decode/hash → 동기 E1 batch/COMMIT → 다음 callback 순서다.
HTTP 요청은 한 번에 하나이고 다음 wave가 E1 write 완료를 기다린다. Network fetch와 local write의
동시 pipeline이라고 부르지 않는다. Socket/SQLite를 무제한 병렬화하지 않는다.

`after_commit` hook은 실제 COMMIT 이후다. 첫 insert→COMMIT span은 pre-BEGIN canonical 검사와
schema 검사 일부를 포함하지 않는 하한이다. Commit-only span은 그 안에 중첩되므로 더하지 않는다.
Client header→다음 send gap은 body 수신, C1/hash/graph/SQLite 및 계측을 포함한 합계이며 순수
network cost가 아니다. 최종 critical path는 중첩하지 않는 lookup/connect/resolve와 client gap,
operation별 inclusive work를 구분해 제시한다.

## 18–20. 관측 갱신과 restart

E1에 이미 commit된 완전 immutable 객체는 새 관측에서도 같은 trusted origin/NS/principal/Versions와
Ref가 일치하면 hash-on-read로 재사용한다. 새 observation의 root에서 complete closure를 다시
검사한다. Staged object는 CompleteTargetVerified도 accepted authority도 아니다.

미완료 cold에는 accepted-base provenance가 없으므로 cached objects를 다시 읽고 graph 순회와
새 staging progress를 반복한다. Network bytes 보존과 검증/SQL 작업 보존은 다르다. In-memory
마지막 progress buffer는 실패 때 버려질 수 있지만 이미 commit된 object BLOB는 남는다.
Partial chunk를 새 observation과 묵시 결합하지 않는다.

별도 process open/recover/health와 direct SQLite/FK/legacy checksum을 확인한다. 원 cold의
accepted가 null이므로 이를 기존 대형 accepted generation의 rollback 증거로 과장하지 않는다.
이 실행의 baseline.json/online-write marker 보존과 Frozen J/E4 pin이 존재하는 시나리오도 구분한다.

## 21. 대안과 최소 권고의 조건

**RECOMMENDED FUTURE CHANGE:** 우선 기존 large-profile cold scheduler가 validated parent path를
유한 cursor로 보존하여 packet64/1MiB를 잘 채우도록 한다. Dropped frontier를 전체 cache 재순회로
찾는 O(N²) 방식은 금지한다. Cursor 수·depth·bytes도 명시적으로 bounded해야 한다.
Valid accepted-base provenance가 있는 정상 delta에서는 cold 확장을 쓰지 않거나 unchanged subtree
경계에서 멈춰야 한다. Cold 최적화가 I25의 일상 delta를 full traversal로 되돌리면 안 된다.

두 번째 후보는 `backend/isolated_sync/transfer.py`의 **같은 요청·같은 native transaction 안에서만**
이미 검증한 typed path prefix를 bounded 재사용하는 것이다. Hash만 같은 임의 edge를 같다고 보지
않고 Ref.bytes, NS, kind, table/descriptor, Patricia prefix/count/parent count와 같은 incoming context를
키에 묶거나 원래의 동일 path prefix에 묶는다. Entry/byte cap을 두고 과대 object는 cache하지 않고
원 검사로 fallback한다. 최초 hash/C1/shape 검증, 모든 edge membership, cancellation check 및
마지막 credential/lease/DB-identity 검사는 그대로다. Authorization/SQLite schema의 cross-request
cache를 만들지 않는다.

실측을 근거로 한 좁은 수정 후보이지 50k/100k 성공 예측을 실행 결과로 바꾸는 것은 아니다.
후속 구현은 실제 두 cold grid를 통과하고 resource/정합성 회귀를 받아야 한다. 요청/observation
횟수 증가,900초 초과 lease, pragma 완화, partial publication은 최소 해법이 아니다.

## 22–24. 네 Flutter 실패와 현재 상태

원 후속 full run의4개는 pin0 기대값(실제4), fetch source SHA, AppState 복원 source SHA,
cached3×524288B batch 기대 거부(당시 실제 허용)다. 원 로그와 assertion을 보존한다.
마지막 batch-byte 제품 수정 전 compiled run이므로 현재 결과와 혼동하지 않는다.

원 source-SHA guard는 immutable wire artifact 자체보다 이전 감사의 fetch/default/authority 소스를
보호한다. 의도적인 코드 수정도 검증 gate를 자동 통과시키지 않는다. 기대 hash를 자동 갱신하거나
삭제/skip하지 않는다. Fetch/store/AppState 전체 변경을 재감사하고 승인된 source-lock 근거를
별도로 기록한 뒤에만 합법적 guard 갱신을 검토할 수 있다. 과거 protected-source artifact는 보존한다.

새 pin test의 현재 oracle는 기존 E3에서 허용했던 임시 root4개 작업과 영구 pin SQL 행 동일성을
구분한다. 원 역사 pin0 assertion이 통과했다고 하지 않는다. 최종 cached byte oracle는 실제 Ref
크기를 모두 charge한다. 이번 A01은 기존 어느 test/expected SHA도 수정하지 않는다.

## 25–27. 계측과 회귀 범위

재현 command, 시작·종료·exit·외부 guard 여부는 각 run의 command/execution JSON에 있다.
최초/확인 run을 합쳐 하나의 연속 acquisition으로 부르지 않는다. 원 source SHA와 각 fixture
identity는 별도로 남긴다. 초기 mock response의 Map 타입 오류도 조사 하네스 오류로 보존한다.

후속 검사는 cold 종료 뒤에만 실행한다. Fresh process reopen, targeted61 B02, 원 SHA guards,
E2 fetch/HTTP cleanup, backend lease/auth/permit/strict quota, npm build와 정적 검사를 수행한다.
Full Flutter/backend를 이번에 재실행했다고 하지 않는다. 과거1560 PASS/4 FAIL/2 SKIP 또는
backend1315/1540은 과거 구현측 evidence이며 최종 worktree full regression의 대체가 아니다.

## 28–31. 원인 순위와 개인용 제품 판단

실제 permit/lock wait, HTTP handler, client 검증·쓰기와 반복 작업을 측정한 뒤 순위를 낸다.
CPU-bound 검사를 대기열로 오해하지 않는다. 개인용 앱이므로 rare cold가 길어질 수 있지만
bounded attempts 안에서 완료해야 하며 normal one-row delta는 작게 유지해야 한다.

새 queue/service/DB engine/worker infrastructure는 필요 근거가 없다. Existing E1 batch와 durable
object cache를 유지하고 cold-only packet scheduling 및 request-local 검증 재사용으로 제한한다.
새 persistent state/migration, startup work, default budget 확장은 권고하지 않는다.
E1 pragma/transaction 안전성을 낮추거나 E3/E4/Frozen B/J를 바꿀 이유는 없다.

## 32–35. 후속 구현·검증과 남는 gate

후속 변경 범위는 우선 fetch.dart의 large cold frontier와 transfer.py의 bounded request-local
prefix reuse다. Backend source release hash가 바뀌면 기존 release-artifact 절차에 따라 정확한
artifact를 발급·대조한다. 금융 공식·wire schema·lease 의미를 바꾸는 변경은 아니다.
기존 B02 세 제품 파일은 승인된 후속 task 전까지 그대로 보존한다.

필수 검증은 실제50k/100k cold, identical/25·26-object one-row delta, fresh process resume,
corrupt/missing/wrong-type/NS/epoch/principal/expired/cancel/stale-ticket, batch fault/SIGKILL/ENOSPC,
concurrent accepted publication, prefix-cache context collision와 eviction/fallback, peak cursor/cache
bounds 및 SHA guard의 정식 처리다. Full Flutter/backend/analyze/build와 독립 targeted re-audit가
필요하다. 기존 strict quota assertion과 source/previous_source fencing은 보존한다.

후속 전층 logical hash/validate/write bytes는 각 함수에 실제 전달한 bytes로 계수해야 한다.
HTTP entity size, canonical payload sum, SQLite 파일/WAL 크기를 그 대신 쓰지 않는다. Backend
hash_bytes/decode_c1와 serialization, E1 verify/hash/INSERT BLOB, E2 response/chunk validation,
E3 F(raw)/receipt/pins, E4 read/materialization을 구분해 test-only hooks와 direct SQLite로 관측한다.
중첩 validator 호출과 domain prefix bytes의 중복을 숨기지 않는다.

Android driver/VFS/pragmas/I/O-success 및 hardware power-loss proof는 여전히 남는다. Host process
종료나 이번 HOST 측정은 이를 대체하지 못한다. Device performance는 별도 rollout gate다.
Large Restore/MW/backup/atomic restore/receipt/migration/rollback은 R1 소유로 남기며 구현하지 않는다.
B02나 Phase B를 COMPLETE/PASS로 선언하거나 일반 사용자 segmented Offline을 활성화하지 않는다.

## 36–37. 최종 판정과 제품 보존

최종 보고서는 실제 확인 실행과 후속 raw evidence가 완료된 후 판정을 확정한다. Gate가 남으면
그대로 남긴다. 원 dirty 변경 및 staged 상태를 최초 SHA/index entries와 다시 비교한다. 새 report와
조사 전용 artifacts만 추가하며 commit/push는 수행하지 않는다. Dirty 상태는 예상된 정상 종료 상태다.

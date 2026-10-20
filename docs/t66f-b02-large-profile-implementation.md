# T6.6F-B02 명시적 대형 graph 검증 profile — 구현 기록

## 01. 상태와 시작 저장소

**T6.6F-B02 IMPLEMENTATION INCOMPLETE — TARGETED CORRECTION REQUIRED**다.
명시 profile과 bounded batch는 구현했으나 필수50k/100k cold가 각각3회 lease 만료로 실패했다.
설정/작은 graph 시험을 전체 대형 D→E PASS로 바꾸지 않는다. 커밋·push하지 않았다.

시작 HEAD/main/origin/main/실제 remote main은 모두
`6282c1c3577c42bba9382d786745d583a5d88236`, 작업 트리는 clean이었다. 원
[B02 조사](t66f-b02-e2-object-budget-investigation.md),
[Phase B continuation](t66f-phase-b-continuation.md),
[Phase B 원 감사](t66f-phase-b-independent-verification.md),
[B01 독립 검증](t66f-b01-independent-validation.md)을 보존한다.
`AGENTS.md`, domain/architecture/known issues/project state, 개발 검증 절차와 T6.6C를 대조했다.
운영 DB/API/credential/service를 사용하지 않는다. 새 실험은 자가 소유 disposable HOST 자원이다.

## 02. 실제 조사 사실과 최소 구현 경계

원 100000은 protocol 한도가 아니라 E2 local policy의 기본값이자 설정 hard ceiling이다.
검사 대상은 다운로드 수가 아닌 재사용 subtree를 포함한 전체 target closure다.
원 E1 기본 metadata32 MiB는 한 cold stage에서 약47656개 객체에 먼저 도달할 수 있다.
같은 fixture의 50k/100k는 각각 V200331/400532, E200327/400528이며 canonical payload는
130710592/261543083 B다. 이를 더 쉬운 graph로 교체하지 않는다.

**구현측 변경:** `mobile/lib/src/segmented/fetch.dart`에
`FetchLimits.largeGraphVerification`라는 명시적 named constructor를 추가했다.
`mobile/lib/src/app_state.dart`의 기존 `publishSegmentedForIsolatedUse`에만
선택적 `verificationLimits`를 전달한다. 기존 기본 인자는 `const FetchLimits()`다.
최초 profile-only 구현의 E1 설정은 기존 API를 그대로 사용했으며 검증 harness의
`docs/benchmarks/t66f-b02-implementation/verification_profile.dart`에만 함께 선언한다.
실제 cold에서 추가 장벽을 재현한 뒤에만 §10이 허용한 최소 bounded HTTP/put/progress batch를
추가했다(§09). 따라서 최종 제품 변경은 위 두 파일 및 `mobile/lib/src/segmented/store.dart`다.
새 scheduler/cache/verifier/storage engine/schema/protocol은 없다.

## 03. profile 선택과 기본값 보존

|항목|원 기본값|명시적 HOST 검증 profile|
|---|---|---|
|E2 graph objects|100000|500000|
|E2 graph edges|200000|1000000|
|E1 namespace object count|100000|500000|
|E1 logical metadata|32 MiB|384 MiB|

원 constructor의 100001 거부는 유지한다. Named constructor만 큰 유한 ceiling을 사용한다.
서버 manifest/capability/원격 입력이 budget을 선택하거나 늘리지 못한다. 환경설정, persistent flag,
일반 startup/refresh/financial read-write에 자동 선택 경로를 추가하지 않았다. E4 installation
메서드에도 profile을 묵시 전달하지 않는다. 이 진입점은 기존부터 명시적 isolated API이며
제품 기본 data-source selection을 바꾸지 않는다.

개별 object64 MiB, payload512 MiB, manifest8 MiB, databasePages262144,
staging128, busy1000ms, chunk1 MiB, graph path512, C1 depth128,
HTTP/retry/observation attempt 한도는 모두 불변이다. Budget은 무결성/authorization 증거가 아니다.
같은 profile로 새 store를 열거나 재개해야 하며, E1/E2 각각의 실제 guard를 계속 적용한다.

## 04. 유한 ceiling 도출과 자원 구분

V400532 및 G1/G2 union400558보다 약25% 큰 둥근 count500000을 선택했다.
Edge ceiling1000000은 원 graphEdges/object ceiling 비율2를 유지하는 조사 권고값이다.
Metadata384 MiB=402653184 B는 100k cold core 약281975744 B와 추가 observation 두 번의
stage 링크2×400532×128 B 및 소규모 manifest/receipt 여유를 수용한다.
이 산술은 **ANALYTICAL ESTIMATE**이며 actual usage와 분리한다. 모든500k graph가 세 번의
stage와 payload/page 예산에도 들어간다고 보장하지 않는다. 어떤 한 guard라도 초과하면 실패한다.

Object count, edges, decoded payload, logical metadata, 실제 SQLite 파일/pages, process RSS 및
Dart heap은 서로 다르다. 새 RSS/heap hard quota를 만들지 않았다. 유한 V/bytes/depth/retry라는
기존 방어와 HOST 실측을 유지할 뿐 Android memory safety를 선언하지 않는다.

## 05. 유지한 integrity·authority·durability

C1 encoder/parser, domain SHA, `VerifiedObject.verify`, typed edges, complete graph verifier,
F(raw)/index 및 hot/raw verifier는 그대로다. 새 closure를 changed-frontier만으로 대체하지 않는다.
기존 single-object put의 body를 private `_putVerified`로 분리하고 같은 transaction에서 재사용한다.
새 batch는 object와 progress를 함께 커밋한다. schema/trigger/DELETE+EXTRA/FK/rollback,
기존 single-object API의 검증·fault·readback 순서는 보존했다.
E2 cancellation, original credential/session, bounded retry 및 response/release cleanup을 재사용한다.

AppState가 acquisition 전에 발급한 원 RefreshTicket, 기존 coordinator와 lineage lock,
user/auth/mutation/mode/session guard, synchronous final guard→COMMIT/readback은 불변이다.
새 config는 authorization token이 아니며 durable receipt를 설치 permit으로 취급하지 않는다.
E4-A01/RA01 source/previous_source fence, Frozen pins/lineage, Snapshot v7,
OfflineBaseline v4, frozen local `exactMoney()`/B/J 및 P0 코드는 변경하지 않는다.
`sync_root != state_fingerprint`와 R1 CLOSED gate를 유지한다.

## 06. 새 시험과 독립 oracle

`mobile/test/segmented_large_profile_test.dart`는 원/대형 constructor ceiling, 실제 작은 backend
graph의 V−1/V/V+1 및 edge/path boundary, 재사용 provenance, 실제 E1 transaction의
metadata319/320/321 B 경계, typed-kind/object/hash/context/version/cancel/missing/storage 실패를 검사한다.
작은 실제 fixture로 같은 enforcement를 실행하며 500001개 불필요한 객체를 만들지 않는다.
Metadata 경계의 expected charge는 별도 SQLite `usage`/실제 행/FK/새 writer 획득으로 확인한다.

`segmented_large_profile_authority_test.dart`는 명시 profile로 current authority와 prior accepted,
legacy B/pending byte 동일성을 확인한다. 동일 target은 원 E3의 idempotent sequence/ID를 유지한다.
`segmented_large_profile_crash_test.dart`는 실제 child를 SIGKILL한 뒤 공개 store 재개와 재수집,
독립 SQLite integrity/FK/progress와 B/pending bytes를 검사한다. Hardware power loss proof는 아니다.
`segmented_large_batch_test.dart`는 실제 64/65개, canonical bytes 1 MiB/초과,
oversized singleton, cached byte charge, list 소유권 및 whole-batch rollback을 검사한다.
기존 독립 profile/monetary 두 assertion과 기존 E1/E2/E3/E4 회귀를 수정하지 않는다.

## 07. 실제 50k/100k D→E 실행 경계

[재현 방법과 counters](benchmarks/t66f-b02-implementation/README.md)를 사용한다.
`server.py`는 원 seed662602와 current105/H, n+35 authoritative rows를 유지하는 실제 backend
bootstrap/finalizer를 생성한다. 별도 SQL/SHA walker가 graph identity/count를 확인한다.
실제 loopback TLS observation/manifest, typed object transfer 및 observation release를 사용한다.
Backend object catalog를 E1에 직접 복사하거나 accepted metadata를 수동 삽입하지 않는다.

새 빈 E1 → E2 실제 HTTP acquisition → 기존 original-ticket AppState E3 publication → E4
generation-bound bounded page read 순서다. 수집 실패 시 그 뒤 단계를 실행한 것으로 세지 않는다.
Real auth/observation clock 및 기존900초 lease를 사용하며 clock 고정·lease/timeout 연장은 없다.
합성 TLS의 exact loopback host/port만 인증서 예외를 허용한다. Credential/private key는 증거에 넣지 않는다.

## 08. 측정 분류와 한계

HTTP entity·decoded chunk bytes는 실제 wire observer 값이다. TLS/TCP framing bytes가 아니다.
기존 `store.work`는 제품 operation counter다. 독립 SQLite statement/row-scan/physical I/O
계수로 바꾸지 않는다. 별도 SQLite는 actual usage/accepted/generation/pin/FK 및 DB 크기를 본다.
`ProcessInfo.maxRss`/sampled RSS는 HOST client process 값이며 pure heap은 미측정이다.
Bootstrap 및 backend/Flutter full 회귀 일부가 같은 host에서 겹쳤다. 단회 wall time을
무부하 median/p95·Android latency/최대 안전 자원으로 확대하지 않는다.

HASH/VALIDATE/WRITE 전층 논리 byte campaign은 **DEFERRED**다. Canonical 총합/HTTP bytes,
`verified_bytes`, file growth를 실제 hash preimage·validation work·logical persistence bytes로
임의 치환하지 않는다. 원 Phase B의 남은 세 묶음과 Android/R1 상위 exit는 별개다.

## 09. 실제 cold가 드러낸 추가 장벽과 최소 후속 변경

**MEASURED RESULT:** profile-only 실제 TLS cold의 첫900초 lease에서 두 필수 N 모두
HTTP410 `OBSERVATION_EXPIRED`를 받았다. 50k의 첫 lease는1614개/decoded30328715 B,
100k는1446개/59806320 B까지만 진행했다. 이는 metadata/object budget 초과가 아니라
서버가 실제 유효 observation의 만료를 강제한 결과다. 실패 response 원문과 manifest,
wire counters를 `evidence/n50000`, `evidence/n100000`에 보존한다.

그 첫 실제 실패를 확인한 뒤 두 초기 client만 SIGKILL했다. test exit79는 **의도적 중단**이며
3 observation을 소진한 API 최종 실패로 세지 않는다. 별도 Dart process reopen은 두 경우 모두
healthy, accepted=null, 기존 legacy B/pending checksum 동일이었다(각각1648/1446개 객체와2 stages).
이를 대형 accepted generation의 성공적인 restart로 해석하지 않는다.

허용된 최소 후속 변경은 기존 D3 packet의 최대64 items/1 MiB decoded envelope를 사용하는
`_VerificationFrontier`와 E1 `putVerifiedStagedBatch`다. Parent가 검증한 hash path만 최대64개
잠시 보유한다. 버린 lookahead path는 원 complete DFS가 다시 발견한다. decoded secondary
cache나 두 번째 closure verifier는 없다. cached progress도64 refs/1 MiB로 제한하며 oversized
단일 객체만 원64 MiB 한도 안에서 원 chunk 방식으로 조립한다.

각 packet의 nonce/observation/cardinality/order/ref/offset/length, 각 typed object hash/C1 및
원 verifier가 계속 필수다. batch의 모든 객체가 검증된 뒤 기존 SQL transaction에서
object/edge/progress를 함께 쓰며, 중간 fault/SIGKILL은 전체 wave를 rollback한다. Cached 객체도
transaction 안에서 재검증한다. Session/cancel은 wave 전후와 flush 전후 검사한다. Accepted
publication은 여전히 전체 closure 및 E3의 현재 authority/COMMIT를 통과해야 한다.

**MEASURED RESULT:** 이 후속 bounded64 구현의 50k 첫 lease도3506 chunks/1060 object
requests에서 만료했다. 평균3.31 items/request였으며64개를 항상 가득 채웠다고 주장하지 않는다.
후속100k 첫 lease도 만료했다. 최종 유한 재시도 결과는 §12에 기록한다. TTL/clock/retry를
늘리거나 backend admission/terminal 보증을 건너뛰지 않았다. 새 streaming/scheduler/backend
cache나 임의 큰 frontier로 확장하지 않는다.

## 10. 작은 실제 전체 경로와 large 결과의 분리

**IMPLEMENTATION-SIDE TEST RESULT:** 별도 N=1000 full real HTTP plan은
`PASS_COLD_IDENTICAL_DELTAS_RESTART`다. V4132, cold768101313 µs다. 같은 original-ticket
경로를 사용했으나 필수 두 large N의 대체 증거가 아니다.

|단계|실제 전송 객체|독립 backend oracle|client verification|
|---|---:|---|---|
|identical|0|같은 generation/root|full recovery0/full verify0, idempotent sequence|
|one row|18|신규18/reused4114|incremental rows1/full verify0|
|multiple localized|32|신규32/reused4100|incremental rows2/full verify0|
|fresh-handle delta|18|신규18|정상 restart의 full recovery1/full verify2|

원 fixed-clock 조사와 달리 실제 clock의 control 객체가 갱신되어 one-row 신규 수가17+1이다.
이를 delta를 부풀린 실패나 고정 count 달성으로 해석하지 않는다. 별도 실제 Dart process의
open/recovery/scrub/accepted page read도 성공했다. Legacy B/pending bytes는 불변이다.
`result.phases[].store_work`는 각 작업 차이이며 최종 `store_work`는 재개 후 handle의 누적값이다.
그 값을 cold 전체 SQL 작업으로 제시하지 않는다.

기존 backend metrics hook의 이 작은 전체 plan 실측은1169 operations,
admission310779.504 ms, prepared447292.398 ms, path resolution61860.010 ms다. 요청별
admission/terminal 비용과 제한된 packet packing이 후속 병목 후보임을 보여 주지만, 이를 곧바로
새 backend 결함 또는 검증 생략 허가로 단정하지 않는다. Full large cold를 닫는 추가 교정은
이 자료에 근거해 좁게 결정해야 한다.

## 11. 기존 테스트 보존과 알려진 전체 회귀 실패의 구분

원 `segmented_adapter_isolation_test.dart`의 두 SHA assertion은 의도적으로 변경한
`fetch.dart` 및 기존 AppState isolated publisher 부분을 이전 E4의 전체 소스 hash와 비교한다.
실행에서 이 둘이 FAIL했다. 원 파일과 hash oracle를 **수정·삭제·skip하지 않았다**.
이 실패가 곧 financial/authority 동작 결함이라는 뜻은 아니지만, full-suite PASS라고 숨기지도
않는다. 후속 완료 단계에서는 승인된 최소 diff/기본 동작을 증명하는 source-lock 갱신도 필요하다.

새 B02 테스트 작성 과정의 seq+1/temporary pins0/싱글 요청 수 기대값 오류도 raw 로그에
보존한다. 기존 E3의 동일 generation은 sequence를 증가시키지 않으며, 임시 root4개 쓰기는
영구 pin rewrite가 아니다. 최종 새 oracle는 permanent pin SQL rows 동일성, bounded temporary
root 작업과 full verification0을 함께 본다. 기존 제품 보증을 완화하거나 old test를 고치지 않았다.

최종 targeted 재실행 중 한 번은 SIGKILL 대기점에 도달하기 **전** child의 native SQLite
`dlopen/sqlite3_initialize`에서 `Bus error`가 발생했다(60 PASS/1 ERROR). Debug build와 시간이
겹쳤으나 원인을 확정하지 않는다. 원 stack/exit를 `final-targeted` 로그에 보존했다. 빌드 종료 후
동일한 source/명령을 다시 실행한 `final-sequential-targeted`는61 PASS/0 FAIL이며 실제
4개 SIGKILL 대기점도 포함한다. 첫 오류를 제품 transaction 검증 성공으로 치환하지 않는다.

## 12. 최종 실측·회귀·판정

### 실제 필수 두 grid point

**MEASURED RESULT:** 두 bounded 실행 모두3 observations를 소진해
`AcquisitionFailure(OBSERVATION_EXPIRED,new_observation)`로 종료했다. 각 HTTP410의 원문,
각900초 lease, 최종 wire·usage·accepted SQL 및 recovery 결과를 보존했다.

|항목|N=50000|N=100000|
|---|---:|---:|
|backend authoritative rows|50035|100035|
|필수 reachable objects|200331|400532|
|graph edges / depth|200327 / 22|400528 / 23|
|전체 canonical object bytes|130710592|261543083|
|성공 전송된 objects/chunks|22392|23002|
|actual object HTTP requests|3489|3712|
|decoded 전송 bytes|40816368|70699641|
|HTTP request entity bytes 합계|27665236|29712806|
|HTTP response entity bytes 합계|58082536|98047934|
|cold 경과 µs(bootstrap 제외)|2699793901|2700442962|
|HOST client process peak RSS B|249905152|255053824|
|E1 최종 payload B|40816368|70699641|
|E1 최종 logical metadata B|18280381|18513600|
|E1 최종 DB file B|62914560|93106176|
|E1 transaction counter|3795|3991|
|실제 new object insert hook 횟수|22392|23002|
|실제 progress insert hook 횟수|41336|40218|
|현재 accepted / sequence|null / 0|null / 0|
|generation / permanent root pin rows|0 / 0|0 / 0|
|SQLite FK errors|0|0|

HTTP 합계는 failed/control/release 응답까지 포함한 entity 합계이며 TLS framing이 아니다.
`store_work`의 `verified_bytes` 및 transaction/hook 횟수는 독립 full SQL statement 계수가
아니다. 일부 cache/progress 재검증이 있어 hook/graph traversal 수와 unique objects도 다르다.
전체 backend SQL/SHA oracle는 client 입장 전에 독립적으로 원래의 큰 graph를 확인했다.
실패 시점 metadata는32 MiB 미만이었지만, 이것이 전체 graph를 원 기본 예산에 넣을 수 있다는
뜻은 아니다. 새 profile의 유한 ceiling만으로 현재 lease 안의 cold feasibility가 증명되지 않았다.

`resource-snapshots.json`의 중간 관측에서 DB journal/WAL/SHM은0 B였다. Peak journal/temp
usage나 전체 디스크 write amplification의 증거로 확대하지 않는다. Bounded 실행의 backend
bootstrap DB는 각각394903552/790274048 B, backend peak RSS는511428/958332 KiB였다.
Client pure heap, Android RSS/VFS 및 hardware power-loss safety는 미검증이다.

두 실행은 전체 회귀 및 서로와 같은 HOST에서 일부 겹쳤다. **새 장벽의 관측은 확정**이나,
무부하·단독 실행과 비교하지 않았으므로 host contention/요청 admission/packing/SQL 각각의
인과 비중은 아직 확정하지 않는다. 한계가 architecture 변경을 반드시 요구한다고도 단정하지
않는다. TTL·auth/terminal 보증을 우회하지 않는 단독 cold 병목 분리 측정이 다음 최소 작업이다.

### 실패 후 별도 실제 process recovery

50k는22392 objects/3 stages, 100k는23002 objects/3 stages를 별도 Dart 프로세스가
`recoverAcceptedGeneration`/`inspectStoreHealth`로 다시 읽었다. 둘 다 exit0, healthy,
accepted=null, legacy B/pending checksum 동일, R1 CLOSED였다. Incomplete cache를 성공한
accepted receipt/pin으로 만들지 않았다. 기존 accepted 유지 실패 시험은 새5 authority tests에서
별도로 검증한다. 큰 cold는 처음부터 accepted=null이므로 이를 기존 큰 accepted의 rollback
시험이라고 부르지 않는다.

큰 cold가 실패했으므로 50k/100k identical/delta/frozen/G1-G2 reader workflow는 **NOT RUN**이다.
One-row 신규25/26이라는 원 backend 조사값을 실제 client 전송·게시 성공으로 대체하지 않는다.

### 실제 회귀 결과

|검사|이번 실제 결과|범위·한계|
|---|---|---|
|최종 B02 targeted|61 PASS/0 FAIL|profile39/batch13/authority5/SIGKILL4|
|작은 full real plan|1 PASS|N1000 cold/identical/deltas/별도 process 재개|
|필수 대형 real cold|0 PASS/2 FAIL|각3회 실제 OBSERVATION_EXPIRED|
|원 독립 profile/monetary|2 PASS|기존 assertion 불변|
|full Flutter 첫 실행|1533 PASS/3 FAIL/2 SKIP|batch 전 및 초기 새 test oracle|
|full Flutter 후속 실행|1560 PASS/4 FAIL/2 SKIP|cached-byte 최종 수정 전 compiled source|
|full backend|1315 tests +1540 subtests PASS|실제2196.88초; JUnit2855=두 수량 합|
|Flutter analyze|PASS|최종 source, no issues|
|Flutter debug APK build|PASS|최종 source; 설치·배포 안 함|
|npm build|PASS|이번 최종 재실행|
|Ruff / compileall|PASS|backend 및 새 Python harness|
|변경 Dart/Python formatting|PASS|실제 package 문맥의 AppState 포함|
|git diff --check|PASS|원본 무관한 포맷 변경 없음|

후속 full Flutter의 네 번째 실패는 **초기 새 batch에서 cached ref의 bytes를 batch envelope에
합산하지 않았던 결함**을 새 boundary test가 드러낸 것이다. 최종 source는 new/cached 모두
`max(actual bytes,ref length)`를 합산하며,61 PASS 최종 targeted에 이 regression을 포함했다.
그 이후 full suite는 다시 실행하지 않았다. 앞서 설명한 두 source-SHA guard도 그대로 FAIL이므로
full Flutter PASS를 선언하지 않는다. 남은 하나는 초기에 작성한 pins0 기대값이며 새 최종
test에서 bounded temporary roots와 unchanged permanent rows라는 기존 계약으로 교정했다.
원 old test/fixture/assertion은 한 글자도 수정하지 않았다.

후속 full에서 E3 I25 baseline1/publication30, publisher36/crash16은 PASS였다. E4 adapter42,
authority16/crash4, handoff35/crash13, A01 21, RA01 42도 PASS였다. E4 isolation은21 PASS와
의도 변경 소스에 대한 위 SHA2 FAIL이다. 이 기능 회귀와 작은 N1000 counters는 기존 보증
보존의 증거지만, **large grid I25·Frozen-B 전체 비용의 독립 검증을 대신하지 않는다**.

### 보존·저장소·남은 단계

수집한1118개 보호 대상 tracked source/test/report/evidence는 HEAD 대비 SHA가 모두 동일하다.
세 제품 변경의 최종 SHA와 diff는 `evidence/summary.json`, `product.diff.gz`에 있다.
원 조사·Phase B FAIL/INCONCLUSIVE·P0·E4 감사·역사 diagnostic 이력은 그대로다.
초기 source snapshot은 **capture 시점**이며 각 장시간 process의 시작 SHA라고 주장하지 않는다.

최종 확인 HEAD/main/origin/main/actual remote main은 모두
`6282c1c3577c42bba9382d786745d583a5d88236`이다. Staged 파일/새 commit/push는 없다.
세 제품 변경과 새 tests/harness/report/evidence를 working tree에 보존했다. Worktree는 의도적으로
dirty이며 clean이라고 보고하지 않는다.

남은 B02 blocker는 (1) 실제50k/100k cold와 그 이후 delta/재개/reader/frozen 증명,
(2) 최종 source의 전체 Flutter 회귀 및 승인 diff에 대한 source-lock 처리가 끝나지 않은 점이다.
새 profile만으로 이 두 blocker가 닫혔다고 하지 않는다. 논리 hash/validate/write byte accounting,
나머지 Phase B 비용·cross-layer 증명, Android/device 및 R1은 각각 별도 미완료 항목이다.

**독립 B02 완료 감사 준비: NO. Phase B: STILL INCONCLUSIVE.**
추가 streaming/cache/scheduler/서버 authority 변경을 실행하지 않았다. General-user segmented
Offline·production activation·배포·설치·R1은 하지 않았으며 R1 gate는 CLOSED다.

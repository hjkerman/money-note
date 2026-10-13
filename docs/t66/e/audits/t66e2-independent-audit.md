# T6.6E2 독립 구현 감사

## 1. 감사 대상 commit

대상은 `69a8fd15b581357ef4be859fec03525bd6070fb4`, 기준은
`bd3a7e08c5b810c8c30d26e498d1994218b33b71`이다. 감사일은 2026-10-12다.
이 보고서는 구현자의 PASS를 독립 결과로 인용하지 않는다. 아래 실행 결과와
새로 작성한 oracle에 근거해 판정한다.

**FAIL — T6.6E2 CORRECTION REQUIRED.** 실제 IOClient의 header 거부 경로에서
응답 stream이 정리되지 않는 **E2-A01 / MEDIUM**을 확인했다. 반복 실패로 native 연결이
누적되므로 E3 시작을 차단한다. 기존 69개 독립 graph/storage 시나리오는 통과했지만,
추가 native HTTP 회귀 5개 중 대조군 1개만 통과하고 결함 재현 4개는 실패했다.
제품 구현은 수정하지 않았다.

## 2. Repository 및 remote 검증

시작과 감사 중 재확인에서 branch는 `main`, HEAD/main/origin/main/실제 remote main은
모두 대상 commit이었다. 시작 working tree는 clean이었다. 실제 remote는
`git ls-remote origin refs/heads/main`으로 확인했다. 기준 commit도 full hash로
확인했다. 사용자 변경을 reset하거나 삭제하지 않았다.

`AGENTS.md`, domain-model, known-issues, project-state, architecture의 서버 authority와
클라이언트 신뢰 경계, offline-mode, T6.6C, E1 구현/독립 감사/교정 재감사, E2 구현과
benchmark README/summary를 읽고 실제 source와 대조했다. 인증 및 개발 격리는
security/runbook의 해당 계약도 확인했다. 도메인과 확정 금융 projection의 authority는
계속 서버다.

## 3. 구현 diff inventory

`git diff --stat bd3a7e08..69a8fd15`는 **17 files, +3,476/-25**였다. 전체 diff와
추가된 source/test를 검토했다.

| 분류 | 변경 파일 |
|---|---|
| 기존 API seam | `mobile/lib/src/api_client.dart`의 6줄 generic callback |
| 새 E2 구현 | `mobile/lib/src/segmented/{api_transport,fetch,graph,transport}.dart` |
| E1 지원 변경 | `mobile/lib/src/segmented/store.dart`: opt-in schema v2, acquisition bookkeeping, 불필요한 staging count 생략 |
| 테스트 | `mobile/test/segmented_{acquisition_store,fetch,fetch_crash,http_integration,transport}_test.dart` |
| 합성 지원 | `mobile/test/support/segmented_e2_fixture.dart`, `segmented_fetch_crash_worker.dart`, `scripts/benchmarks/t66e2_server.py` |
| 문서/측정 | `docs/t66/e/implementation/t66e2-implementation.md`, `docs/benchmarks/t66e2/{README.md,summary.json}` |

dependency/lockfile, backend 구현, production schema, 금융 공식, Snapshot, OfflineBaseline,
AppState/UI/startup, 배포 설정 또는 Android version은 변경하지 않았다.

## 4. 감사 독립성 및 방법

새 도구는 `docs/benchmarks/t66e2-audit/`에만 추가했다. 제품 구현은 수정하지 않았다.
실제 서버가 새 disposable DB에서 만든 bytes를 사용하고, 직접 SQLite BLOB을 읽는
Python oracle로 C1/hash/typed reachability를 계산했다. 서버 GC/graph helper의 결과를
기대 집합으로 재사용하지 않았다. 다운로드 facts에서 canonical Patricia를 별도 재구성하고
11개 raw table을 같은 합성 서버의 직접 금융 row와 비교했다. 금융 projection을 모바일에서
다시 계산하는 검증 의무는 추가하지 않았다.

독립 HTTP client는 실제 전달한 method/path/request body, status, response bytes 및
credential 일치 여부를 기록한다. credential은 private pipe에만 있고 artifact에는 없다.
E1 DB는 fresh Python SQLite connection에서 검사한다. `graph_verified`와 cache-hit
counter를 단독 oracle로 사용하지 않는다.

감사 도구 개발 중 잘못된 시험용 hash domain, 동시 시험의 공유 fixture 파일, trace
field/시간 formatting 오류를 수정했다. 당시 실패는 제품 finding으로 계수하지 않았다.
최종 도구는 fixture를 실행별로 격리하고 negative 오류 code까지 확인한다. 원래 제품
테스트의 assertion은 수정하지 않았다. 실행 명령과 도구는 audit README에 보존했다.

## 5. D3a observation contract

규범은 T6.6C §15.2/§16이다. 실제 producer는
`backend/isolated_sync/http.py:134`, `observation.py:289` 및 observation repository다.
별도 manifest GET이나 별도 서명 필드를 가정하지 않았다. 인증된 POST response의
Target가 principal/NS/Versions/Context/네 transferable root 및 view hash를 결합한다.
내부 input-proof root는 서버에서 보호하지만 임의 다운로드 capability가 아니다.

`fetch.dart:191`은 `{protocol:1,request_id,base:null,inline_bytes:0}`를 보내고
201/200만 받는다. E1 manifest parser가 available/UUID/UTC time/최대 900초 lease와
Target identity를 검사한다. `CacheNamespace.verifyTarget`는 원 store의 trusted
origin/expected principal/NS/Versions와 대조한다. request nonce, initial/base-null,
inline-empty도 검증한다. 다른 principal/dataset/epoch 또는 잘못된 lease를 거부했다.

E2에는 accepted E3 provenance가 없으므로 base-null은 맞는 선택이다. 캐시 Ref의 재사용으로
incremental fetch를 수행한다. capabilities discovery/정상 runtime protocol selection은
이번 단계에서 구현하지 않았으며 현재 isolated endpoint를 production에 활성화하지 않는다.

## 6. D3b manifest contract

실제 POST observation response가 immutable manifest다. `fetch.dart:350`은 수집 후
같은 nonce를 다시 POST하여 서버 terminal credential/lease 검사를 통과한 뒤 원 manifest
bytes와 정확히 비교한다. root hash, nonce, observation ID, protocol/lease/required shape,
context 불일치를 독립 fixture 변형으로 시험했다. 유효한 시간으로 변경한 terminal manifest도
`IMMUTABLE_MANIFEST_CHANGED`로 거부한다. 문법이 맞는 것만으로 권한을 인정하지 않는다.

## 7. Typed object transfer

T6.6C §15.3 및 실제 `transfer.py:120`의 PathResolver와 `http.py:134`를 대조했다.
네 승인 root에서 부모의 검증된 typed child Ref만 따라가며 path는 최대 512 hashes다.
`fetch.dart:289`은 observation별 locator, request nonce, offset 문자열 및 최대 1MiB
length를 보낸다. 200만 받고 envelope nonce/observation/chunk 수/Ref/offset/decoded length를
대조한다. E1 strict base64/전체 길이/C1/kind/domain SHA-256 검증 후에만 저장한다.

틀린 type/ref/context, hash와 다른 유효 C1 bytes, 잘린 JSON/HTTP, 잘못된 base64,
과대 응답은 의도한 오류 단계에서 거부됐다. 부분 chunk는 verified object로 저장하지 않는다.
큰 singleton의 다중 chunk 시험도 기존 E2 suite에서 실행됐다.

## 8. Root 및 generation binding

실제 trust chain은 인증된 response → 원 store 문맥과 일치하는 manifest/Target → 네 certified
Ref → 검증된 부모의 typed edges → 전체 transferable closure다. `graph.dart:102`와
`object.dart:142`를 추적했다. hash만 맞는 다른 type/context/descriptor/Patricia/count/hot
context를 별도 재해시 corpus로 거부했다. 원본 bytes를 바꾸지 않고 저장하고 읽을 때 다시
검증한다. 이전 후보의 root set을 다음 후보에 합치지 않는다.

## 9. 독립 graph closure

`audit_backend.py`는 직접 `sync_objects`를 읽고 명시적 kind별 Ref만 추출한다.
C1 bytes 및 `SHA256("money-note.sync.v1/" + kind + NUL + bytes)`를 독립 계산하며
Ref의 bytes/type/NS/table/descriptor를 검증한다. raw-root의 11 table, B+tree node/leaf,
index-root/node/leaf, hot/control을 방문한다. 집합과 저장 BLOB을 Dart 결과 및 E1 DB의
staging_objects와 정확히 비교했다. all-table row oracle와 Patricia oracle도 통과했다.

`graph.dart:126`은 매 incoming edge의 type/Ref/descriptor를 다시 확인하며 seen/visiting,
object/edge/path 예산으로 누락·cycle·과도한 순회를 막는다. Patricia의 branch/prefix/count,
B+tree의 non-root fanout/empty-child도 검사한다. 금융 table은 비고 필수 settings만 있는 실제 서버 generation도
검증했다. 빈 raw라도 aggregate/context facts가 있어 index 전체가 반드시 index-empty라는
주장은 하지 않는다.

이는 **인증된 다운로드 graph closure**다. T6.6C §11의 F(raw) 재구축과 index 비교,
hot/raw 관계·Snapshot 복구 가능성 및 guarded publication은 E3에서 별도 확인해야 한다.
이번 단계가 이를 했다고 주장하지 않는다.

## 10. Cache reuse

`fetch.dart:275`는 매 cache hit에 `getVerifiedObject`를 호출하여 실제 BLOB/C1/hash/edge를
재검증한다. `recordStagedObject`도 같은 Ref를 재확인한다. 원 store context와 맞지 않는
manifest를 거부하고, 미참조 유효 cache object는 closure/staging에 포함하지 않았다.
immutable trigger를 원래 정의로 복원한 뒤 BLOB만 손상시킨 DB도 거부했다. 이 시험은
schema 손상을 cache 손상으로 오인하지 않는다. cache에서 leaf 하나를 제거한 경우 필요한
그 객체만 다시 다운로드했다.

## 11. 독립 HTTP 계수

계수 단위는 observation/manifest, object, release를 구분한다. 성공 단계의 실제 HTTP
object 요청 hash 집합이 직접 계산한 `reachable − prior cached objects`와 정확히 같았다.
응답 전 취소된 시도는 성공 응답/실제 payload와 구분한다. resume는 중단 직후 실제 SQLite
object 집합을 독립 snapshot하여 genuinely missing set을 계산했다. 구현의 cache-hit
counter만으로 효율을 판정하지 않았다.

## 12. Cold / identical / incremental 측정

새 fixture에는 11개 table과 ledger 13행이 있다. source 값에는 음수 금액, 한국어,
emoji와 normalization하지 않은 Unicode가 포함된다. 실제 ASGI endpoint/인증/SQLite를
private subprocess bridge로 호출했다. 동일 Target 실험을 위해 합성 환경에서 Judgment
문구의 무작위 선택만 고정했다. raw revision이 같더라도 hot wording이 바뀌면 새 hot
object가 필요하며, 이는 기존 integration 시험에서 별도 확인했다.

| 단계 | graph | 실제 object 요청 | decoded payload bytes | response body bytes | manifest/release | 시간(초) |
|---|---:|---:|---:|---:|---|---:|
| cold | 178 | 178 | 111,718 | 200,898 | 2/1 | 35.152 |
| identical | 178 | 0 | 0 | 2,934 | 2/1 | 1.579 |
| incremental | 178 | 10 | 20,378 | 32,868 | 2/1 | 3.689 |
| interrupted | 미완료 | 2개 응답 후 3번째 시도 취소 | 이미 저장된 2개 보존 | 별도 resume로 검증 | 종료 lease release | 미측정 |
| resumed | 178 | 8 | 9,837 | 18,428 | 3/1 | 3.138 |


관측과 manifest 요청까지 0이라는 뜻이 아니다. 각 정상 acquisition에 initial/terminal
manifest와 release가 필요하다. 중단 후 같은 lease를 재사용할 수 없으면 먼저 410을 받고
fresh observation을 얻는다. response bytes는 base64/outer JSON을 포함한 body이며 HTTP headers/TLS overhead는 포함하지 않는다.
단일 HOST 표본이며 median, 실제 TLS/Android latency 또는
RSS 상한 측정으로 해석하지 않는다. 구현 측 1,168-object 표본은 방법을 검토했지만 이번
독립 178-object 표본과 섞어 집계하지 않았다.

## 13. Observation expiration

mock 만료를 manifest/object/terminal 단계에 주입한 사례와 **실제 서버 clock을 정확히
900초 이동한** object/terminal 사례를 구분해 실행했다. 실제 410을 받은 경우 새 nonce와
observation을 얻고 explicit 동일 Ref만 재사용했다. expiry 자체로 검증된 object를 삭제하지
않는다. 단말 wall clock을 authorization oracle로 쓰지 않는다. 실제 session을 합성 DB에서
철회한 경우 401/reauthenticate로 중단하고 기존 객체 2개를 보존했다.

## 14. Generation churn

실제 writer가 G2 observation 뒤 첫 object 요청 중 G3를 COMMIT하도록 제어했다.
G2의 직접 row/graph oracle를 변경 직전에 확보했다. 결과는 정확히 G2였고 G3 root와
섞이지 않았다. 다음 acquisition/resume는 G3의 manifest/closure와 일치했다. 공통 immutable
객체는 재사용하고 stage/Target identity는 분리했다. 두 후보 모두 active data로 발행하지 않았다.

## 15. Durable staging

`store.dart:123`은 명시 `acquisition:true`일 때 건강한 E1 v1을 같은 transaction에서
v2로 확장한다. 기본 open은 v2를 임의 해석/강등하지 않는다. 새 acquisition 상태는
acquiring/interrupted/graph_verified이며 stage당 256 metadata bytes를 accounting한다.
9 table/1 index/13 mandatory trigger의 closed schema를 검증한다. E1-A02와 동일하게
`store.dart:209`의 BEGIN IMMEDIATE와 `_requireSchema` 후에 write/COMMIT한다.

실제 DB에서 manifest BLOB/checksum/roots, stage-object exact set, acquisition state,
usage, FK/integrity와 lock 해제를 확인했다. missing placeholders나 acquiring state를
verified object 또는 complete generation으로 해석하지 않는다. graph_verified도 E3의
활성화 authority가 아니다. resume는 persisted flag를 믿지 않고 서버와 graph를 재확인한다.

## 16. Process crash

독립적으로 **7개 실제 SIGKILL 경계**를 확인했다.

| 경계 | fresh-process persisted-state 및 재개 |
|---|---|
| manifest 응답 후 검증/기록 전 | object 0개, fresh acquisition |
| object response stream 중간 | 부분 object 0개 |
| 전체 검증 후 INSERT 전 | object 0개 |
| object COMMIT 후 progress 전 | object 1개 보존, 재다운로드 제외 |
| staging-object INSERT transaction 중 | object 1개 보존, 미COMMIT link rollback |
| graph_verified transaction 중 | 이전 acquiring 상태와 complete object 보존 |
| graph_verified COMMIT 후 API return 전 | durable 상태 보존, 새 process도 authorization/closure 재확인 |

모든 경계에서 별도 Dart process로 reopen/resume하고 fresh Python connection으로 actual
committed bytes와 missing set, checksum, accounting, FK/integrity, 활성 pointer 부재를
확인했다. SIGKILL 재개의 authority는 서버가 만든 fixture를 쓰는 mock이며, 실제 ASGI
close/reopen+retired lease 재취득은 별도 통합 사례다. 기존 E1 crash 7개와 E2 crash 3개도
전체 Flutter suite에서 통과했다. OS crash나 power-loss 보장을 주장하지 않는다.

## 17. Retry / timeout / cancellation

`fetch.dart:140`은 request 최대 3회, observation 최대 3회다. 동일 operation retry는
nonce/body를 보존한다. reset/timeout/503 후 성공, retry exhaustion, permanent401/422,
잘린 응답, missing descendant 반복을 독립 검증했다. excessive retry-after도 기존 suite로
확인했다. 실제 만료에는 fresh observation을 사용한다.

`transport.dart:144`는 auth/cancel을 응답 전후와 body chunk마다 확인하고 AbortableRequest와
timer를 사용한다. 취소 전에 저장된 유효 object는 보존하고 부분 object는 저장하지 않는다.
header 직후 auth 변경·거부 응답의 native cleanup은 E2-A01에서 별도로 실패했다.
progress transaction 도중 취소되어 이미 COMMIT한 object가 남더라도 incomplete stage를
complete로 반환하지 않았다. synchronous 검증/SQLite 구간은 다음 safe checkpoint에서
취소를 관찰한다. release는 별도 최대 2초 best effort이며 실패가 authorization을 연장하지 않는다.

## 18. Concurrency

`fetch.dart:242`의 static gate는 **Dart isolate당 acquisition 1개**다. 다른 store도 같은
isolate에서는 두 번째 session을 ACQUISITION_BUSY로 거부하고 admission queue를 만들지
않는다. 한 session의 정상 HTTP transfer는 순차적이다. barrier로 첫 session을 잡아 두고
두 번째를 시작해 staging 덮어쓰기 없이 첫 session만 완료함을 확인했다. 기존 suite에는
다른 store의 동일 gate 시험도 있다.

여러 isolate/process의 전역 HTTP 제한을 구현했다고 주장하지 않는다. 공유 E1 writes는
SQLite transaction/unique/schema 검증에 의존하고 기존 E1 concurrency 회귀도 실행했다.
서버 D3B-M01 workers/permit 구현은 diff에서 불변이며 실제 cancellation 회귀가 전체
backend suite에 포함된다. HTTP cancellation이 native worker 종료를 뜻한다고 가정하지 않는다. E2-A01은 클라이언트
HTTP socket/response 수명 문제이며 서버 D3B-M01 worker permit의 재발로 분류하지 않는다.

## 19. Resource bounds

source의 기본 제한은 chunk 1MiB, 요청 body 3MiB, manifest 8MiB, path512,
graph100,000 objects/200,000 edges, request3회/observation3회, timeout15초, cleanup2초다.
E1의 object64MiB, payload512MiB, logical metadata32MiB, staging128 및 DB page 한도도
계속 적용한다. 이들은 조합된 로컬 예산이며 모든 100,000-object graph가 다른 예산과
무관하게 들어간다는 보장은 아니다.

실제 과대 응답·object/edge/depth/metadata schema 한도와 64-page SQLITE_FULL을 시험했다.
그러나 header 단계의 과대/redirect/auth 오류 뒤 native 연결 정리는 E2-A01로 실패했다.
logical HTTP 1개 및 bounded retry가 실제 abandoned socket 상한을 보장하지 않는다.
실패 후 이전 valid BLOB/accounting이 유지됐다. object payload는 한 번에 하나씩 조립하고
부모의 raw rows는 descendant await 전에 버린다. graph 요약/Ref는 O(V+E), 한 object의
여러 bytes/JSON 복사와 hot singleton은 해당 크기까지 메모리를 사용한다. RSS는 측정하지
않았으므로 고정 수치의 peak memory를 주장하지 않는다. full financial dataset 배열을
정상 read path에 새로 만들지는 않는다.

## 20. E1 invariant 보존

원 독립 E1 suite 73개와 A01/A02 재감사 38개, 합계 **111 PASS**를 현재 commit에서
재실행했다. 후자에는 backend oracle의 4,755 monetary vectors, 원 object-limit 반례,
mandatory trigger 변형과 schema-change/COMMIT 경계 검증이 포함된다. Flutter E1 96개와
correction211개도 전체 suite에서 통과했다.

금액 trim/BOM 교정 source, C1/hash domain, object validator는 이번 diff에서 불변이다.
E2도 E1 put/get/recordStagedObject를 사용한다. opt-in v2의 trigger를 제거한 독립 사례와
기존 v2 trigger 시험도 write를 거부했다. 새 persistent write도 schema validation을
우회하지 않는다. 원 금액/Unicode bytes, immutable identity, conflict/idempotence,
read-time corruption, transaction/staging/crash 경계를 보존했다.

## 21. 기존 앱 격리

`rg`로 lib 전체의 E2/store 참조를 추적했다. `api_client.dart:38`의 callback과
`api_transport.dart:5`는 명시적 adapter이며 AppState/startup/normal repository/UI가
fetcher를 import하거나 생성하지 않는다. production DB user_version4, Snapshot v7,
OfflineBaseline v4, frozen B/J, 기존 online sync, 확정 금융 공식, backend runtime 및
Android v2.4.0(15)는 diff에서 불변이다. 전체 기존 회귀도 실행했다.

E2의 로컬 schema v2를 production SQLite schema version 변경으로 혼동하지 않는다.
active/accepted generation pointer 또는 E3 read-source publication은 구현하지 않았다.

## 22. 독립 scenario matrix

아래 40개는 요구사항별 증거 mapping이며 40개의 별도 새 test를 실행했다는 뜻이 아니다.
새 corpus의 실제 pytest case 수는 **74개: 70 PASS / 4 FAIL**이다. 69개 기본 사례와
실제 native HTTP 사례 5개를 나눠 실행했다. 실행 및 source 검증을 구분했다.

| # | 시나리오 | 실제 증거 및 관찰 | 판정 |
|---|---|---|---|
|01|인증된 관측|actual-asgi, Bearer 일치 trace와 201/200|PASS|
|02|invalid observation|manifest-id/lease/protocol, 정확한 오류|PASS|
|03|context mismatch|재해시 principal/dataset/epoch 변형|PASS|
|04|manifest binding|cold의 initial/terminal exact bytes|PASS|
|05|root mismatch|manifest-root, TARGET_HASH_INVALID|PASS|
|06|unsupported version|manifest protocol 및 object canon 변형|PASS|
|07|typed transfer|실제 ASGI의 정확한 reachable set|PASS|
|08|wrong type|재해시 wrong-type, OBJECT_KIND_INVALID|PASS|
|09|wrong identity|transfer-ref 및 유효 C1의 OBJECT_HASH_INVALID|PASS|
|10|malformed canonical|재해시 noncanonical, CANONICAL_INVALID|PASS|
|11|truncated|outer JSON/HTTP 길이 불일치 거부|PASS|
|12|oversized|실제 stream 예산 초과 거부|PASS|
|13|cache reuse|identical 0 payload, 직접 stored bytes 검증|PASS|
|14|cache corruption|trigger 복원 후 변형 BLOB의 거부|PASS|
|15|cross-context cache|원 store에 다른 NS/owner Target 거부|PASS|
|16|cold|실제 178-object graph와 request set 일치|PASS|
|17|identical|actual-asgi 및 완전 seed fixture, object 0개|PASS|
|18|small change|실제 writer, changed/reused set와 trace 일치|PASS|
|19|shared reuse|세대 간 공통 Ref 보존, 불필요 payload 없음|PASS|
|20|missing descendant|누락 410과 3 observations 상한|PASS|
|21|closure|독립 typed walk와 staging exact set|PASS|
|22|empty|실제 금융 tables가 비고 필수 settings만 있는 generation|PASS|
|23|Patricia|독립 canonical 재구성과 prefix 변형 거부|PASS|
|24|mixed generation|실제 G2 관측 중 G3 writer COMMIT|PASS|
|25|manifest 전 expiry|mock 410 후 fresh nonce|PASS|
|26|transfer 중 expiry|실제 정확한 900초 경계, 410 재관측|PASS|
|27|same generation 재관측|실제 terminal expiry, cache 재사용|PASS|
|28|different generation 재관측|actual churn 및 released stage resume|PASS|
|29|partial transfer|stream SIGKILL과 truncated response, 부분 BLOB 없음|PASS|
|30|fresh-process recovery|7 SIGKILL 후 별도 Dart process|PASS|
|31|committed object 보존|after_commit/progress kill 뒤 object 1개|PASS|
|32|retry bounds|reset/timeout/503/exhaustion, nonce/body 유지|PASS|
|33|permanent failure|401/422 단일 시도, 완료 없음|PASS|
|34|cancellation|전/응답 중/progress 취소, actual interrupted resume|PASS|
|35|request concurrency|정상 순차 gate는 PASS, header 거부 후 native 연결은 1→6 누적|FAIL, E2-A01|
|36|session policy|controlled barrier에서 ACQUISITION_BUSY|PASS|
|37|storage full|64-page 한도, actual committed BLOB/accounting|PASS|
|38|active publication 부재|직접 SQLite schema 및 모든 result source|PASS, source+실행|
|39|Offline/frozen 격리|전체 diff/참조 추적과 기존 Flutter 회귀|PASS, source+회귀|
|40|Snapshot/normal R/W 격리|전체 diff/참조 추적과 양쪽 full 회귀|PASS, source+회귀|

새 74개 전체의 expected/observed/oracle 요약은 audit `summary.json`에 보존한다.
Matrix #35의 native cleanup은 별도 추가 시험에서 실패했다. 형식 검증 성공과 resource
수명 보장을 구분하며 resource-bounds 전체 판정은 FAIL이다.

## 23. Full regression

| 검사 | 독립 실행 결과 |
|---|---|
| 기본 독립 E2 corpus | 69 PASS / 0 FAIL |
| 실제 native HTTP corpus | 1 PASS / 4 FAIL, E2-A01 |
| 새 독립 총계 | **70 PASS / 4 FAIL / 0 INCONCLUSIVE** |
| 기존 E2 | 124 PASS: fetch72/transport30/store14/crash3/ASGI5 |
| 원 E1 + A01/A02 독립 suite | 111 PASS / 0 FAIL |
| 전체 Flutter | **970 PASS / 0 FAIL / 기존 2 SKIP** |
| Flutter analyze | PASS |
| 변경 Dart formatting | PASS, 13 files |
| 전체 Dart formatting | FAIL, baseline과 동일한 기존 파일 10개 |
| debug APK build | PASS, 합성 API origin으로 compile만 수행, 미설치 |
| backend 첫 전체 실행 | 1,314 PASS / 1 FAIL + 1,540 subtests PASS |
| backend 실패 case 분리 실행 | 1 PASS / 0 FAIL |
| backend 전체 재실행 | **PASS: 1315 tests PASS, 1540 subtests PASS**, JUnit failures=0, 1566.937초 |
| safety / diagnostic | 27 + 33 = 60 PASS |
| frontend | 21 tests PASS, npm build PASS |
| Ruff / compileall / git diff check | PASS / PASS / PASS |
| 새 audit Dart analyze/format | PASS |

첫 backend 실패는 `tests/test_isolated_sync_transfer.py:497`의
`test_bounded_concurrent_quota_and_same_request_status`다. 동시 5개 관측에
기대 `[201,201,201,201,429]` 대신 `[201,201,201,201,503]`을 관찰했다.
분리 재실행은 통과했다. 동시 감사 부하가 있던 실행이라는 조건은 기록하지만 원인을
단정하지 않는다. backend source는 E2 diff에서 불변이다. 첫 실패를 숨기지 않고 전체
재실행 결과를 별도로 보존했다. 전체 재실행의 성공 여부와 관계없이 E2-A01은 재현된다.


machine output에서 hidden loader를 제외하여 정규 Flutter tests를 셌다. backend는 pytest
최종 summary의 tests/subtests와 JUnit을 대조한다. 중간 `exit`로 중단된 backend 실행은
실행 완료 결과로 세지 않고 전체를 재실행했다. 기존 dependency/Android toolchain 경고는
PASS와 구분하며 새 implementation 실패로 분류하지 않는다.

전체 Dart formatting은 기존 파일 10개에서 실패했다. 해당 파일 모두 baseline과 byte가
동일하고 E2 수정 파일 13개는 PASS다. 감사자가 제품 formatting을 바꾸지 않았다. 이
기존 차이를 숨기거나 전체 formatting PASS로 보고하지 않는다.

## 24. Findings 및 severity

### E2-A01 — Header 검증 실패 후 unconsumed native response 연결 누수

**MEDIUM / CONFIRMED FAILURE / E3 BLOCKER.** Critical/High/다른 Medium은 발견하지 않았다.

**위치:** `mobile/lib/src/segmented/transport.dart:143`의 `client.send` 후
`:144`의 인증 검사, `:147`의 Content-Length 검사, `:151`의 redirect 검사와
`:193`의 cleanup. 연결을 소유하는 body subscription은 `:156`에서만 시작한다.
위 검사가 먼저 throw하면 응답 stream을 구독/취소하지 않는다. auth 변경에는 abort조차
호출하지 않고, 나머지 두 경로의 `abortRequest()`도 실제 http 1.6.0에서는 충분하지 않다.
`package:http 1.6.0/lib/src/io_client.dart:156`의 response controller는 최초 listen 시에만
native response subscription을 만들며, 이미 abort됐다면 error를 발행하고 닫을 뿐
구독하지 않은 underlying HttpClientResponse를 취소하지 않는다. 최종 finally는 timer와
cancellation listener만 제거한다. `_activeStores`도 제거돼 다음 acquisition이 시작된다.

**위반 invariant:** 거부/취소된 요청이 자기 native 응답 자원을 끝까지 소유·해제해야 하며,
제한된 logical attempts가 끝난 뒤 abandoned response/socket이 무제한 누적되어서는 안 된다.
이는 E2의 bounded resource usage와 실패 후 후속 취득 가능성 계약을 위반한다.

**최소 조건:** 실제 pinned `IOClient`, 한 응답의 header를 받은 뒤 아직 끝나지 않은 body,
그리고 header 직후 auth 변경 또는 과대한 Content-Length/redirect다. trusted loopback HTTPS
서버와 disposable credential만 사용했다. 실제 서비스에 요청하지 않았다.

**독립 재현:**

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66e2-audit/test_audit.py -k native
```

`native_transport.dart`는 openssl로 새로 생성한 시험용 certificate만 신뢰하는 새 HttpClient와
loopback HttpServer를 만든다. 서버는 header와 1,024 body bytes를 보낸 후 나머지 body를
barrier처럼 보류한다. 별도 첫 대조군은 body를 정상 종료한다. 이후 정상 요청을 보내고
실제 `server.connectionsInfo().active`와 handler 요청 수를 확인한다. arbitrary sleep 대신
header 수신/API 반환을 interleaving 기준으로 사용하며 1초 timeout은 후속 작업의 상한이다.

| 조건 | 첫 결과 | 남은 active 연결 | 두 번째 정상 요청 | 실제 서버 요청 수 |
|---|---|---:|---|---:|
| 정상 body 대조군 | HTTP_200 | 0 | HTTP_200 | 2 |
| header 수신 중 credential 변경 | AUTHENTICATION_CHANGED | 1 | TRANSPORT_TIMEOUT | 1 |
| 302 redirect | REDIRECT_REJECTED | 1 | TRANSPORT_TIMEOUT | 1 |
| 과대한 Content-Length | RESPONSE_SIZE_EXCEEDED | 1 | TRANSPORT_TIMEOUT | 1 |

후속 timeout 시험의 `maxConnectionsPerHost=1`은 제한된 pool에서의 영향 증명이다.
production의 기본 pool 설정이 1이라고 주장하지 않는다. 별도 **기본 pool 설정**에서는
실제 public `IncrementalFetcher.acquire()`를 6회 순차 호출했다. manifest header가 8MiB
한도를 넘도록 하고 body는 매번 1,024 bytes만 보냈다. 6회 모두 RESPONSE_SIZE_EXCEEDED로
끝났지만 active connections는 **[1,2,3,4,5,6]**, server requests는 6이었다. logical gate가
해제돼 요청을 추가할 수 있고 source에는 누적 native 연결 수를 제한/해제하는 경계가 없다.
이 수치 자체가 무한회 실행 증명은 아니지만 누적 가능한 source 경로와 일치한다.

**직접 persisted-state:** 같은 실험의 fresh SQLite connection에서 objects=0,
staging=0, acquisition=0, integrity/FK/accounting 정상이며 활성 pointer도 없었다.
잘못된 content를 verified로 저장하거나 사용자에게 활성 금융 상태로 발행한 결함은 아니다.
관찰된 영향은 native resource 누적과 제한된 pool의 가용성 손실이다. 시험 종료 시
전용 client/server를 닫아 감사 자원을 정리했다.

**기대:** 거부된 응답은 native body/socket까지 확실히 정리되고 다음 정상 요청이 성공해야 한다.
실제 관찰은 위 표와 반복 수치다. 근거는 `summary.json`의 native 결과, 재현 source,
독립 pytest 4 FAIL 및 fresh SQLite 검사다. 정상 대조군과 기본 69개 성공도 함께 보존한다.

**최소 권고 교정:** transport가 response를 받는 즉시 body stream의 수명을 소유하고,
header/auth 검증 실패에서도 실제 native subscription을 확실히 취소하도록 정리 경계를
보강한다. 특히 http 1.6.0의 abort-before-listen 동작을 고려해야 한다. abort Future 신호만
보내거나 timer만 취소하는 것으로 끝내지 않는다. 전체 body를 무한히 drain하거나 빌린 앱
client 전체를 닫는 우회도 피한다. protocol/금융/graph/store를 재설계할 필요는 없다.
교정 후 이 4개 failing native tests와 정상 대조군, 기존 취소/timeout/redirect/과대 응답,
E1/E2 전체 회귀를 통과시켜야 한다. 감사자는 교정을 구현하지 않았다.

## 25. 남은 한계

- 실제 loopback 자체 서명 TLS socket은 새 finding 재현에 사용했다. 외부 TLS/실기기/
  Android 설치와 production latency는 시험하지 않았다.
- 7개 process-crash는 hardware/OS power-loss 보증이 아니다.
- 실제 ASGI와 mock/failure injection 및 source proof를 구분했다.
- 단일 표본 benchmark이며 peak RSS, 최대 default quota 전체 부하, multi-isolate 전역
  request admission을 검증한 결과가 아니다. 소규모 수치로 대규모 성능을 외삽하지 않는다.
- explicit E2 acquire는 현재 전체 reachable graph를 재검증하므로 local O(V+E+bytes)다.
  identical payload 0은 local O(1)을 뜻하지 않는다. 정상 앱 경로에는 연결하지 않았다.
  미래 E3/rollout의 incremental publication/scaling gate를 이 결과로 면제하지 않는다.
- F(raw)/index 대조, hot/raw/Snapshot 복구 가능성, fresh activation ticket·mutation/mode/
  owner fence, durable publication/installation은 E3의 필수 gate로 남는다.
- 보존한 mock fixture의 lease가 실제 server restart 뒤 유효하다고 가정하지 않는다.
  실제 server에서는 retired/expired lease에 fresh observation이 필요함을 별도 확인했다.

## 26. E3 readiness

**SAFE TO START T6.6E3: NO.** E2-A01을 교정하고 failing native 회귀를 독립 재감사하기
전에는 E3를 시작하지 않는다. graph_verified/VerifiedStagedGeneration은
CompleteTargetVerified, financial receipt 또는 활성화 권한이 아니다. E3는 별도 작업에서
필요한 검증과 guarded durable publication을 구현하고 독립 감사를 받아야 한다.

## 27. Production/deployment safety

production DB/API/서비스/credential/실제 사용자 데이터에 접근하지 않았다. 합성
RetentionSandbox, pytest 임시 DB와 임시 mobile store만 사용했다. APK는 debug compile만
수행하고 설치하지 않았다. segmented endpoints/sync/GC를 정상 runtime에 활성화하지
않았고 deploy/service restart/production migration/E3를 수행하지 않았다.

## 28. Audit-only commit / push

추가 파일은 이 보고서와 `docs/benchmarks/t66e2-audit/`의 독립 도구·README·summary뿐이다.
원래 E1/E2 구현/테스트/이전 보고서는 수정하지 않았다. 최종 commit 후에는 HEAD/main/
origin/main/actual remote main 일치와 clean working tree를 다시 검증한다. self-reference
hash를 report 내용에 넣기 위한 추가 commit은 만들지 않는다. 이 보고서를 추가한 commit은
다음 명령으로 조회한다.

```sh
git log -1 --format=%H -- docs/t66/e/audits/t66e2-independent-audit.md
```

## 필수 최종 footer

```text
T6.6E2 INDEPENDENT AUDIT:
FAIL

AUDITED IMPLEMENTATION COMMIT:
69a8fd15b581357ef4be859fec03525bd6070fb4

AUDIT COMMIT:
이 보고서를 추가한 commit; §28의 git log 명령으로 조회

REPOSITORY STATE:
VERIFIED

IMPLEMENTATION DIFF REVIEW:
COMPLETE

D3A OBSERVATION CONTRACT:
PASS

D3B MANIFEST CONTRACT:
PASS

AUTHENTICATED OBSERVATION:
PASS

MANIFEST/ROOT BINDING:
PASS

TYPED OBJECT TRANSFER:
PASS

C1 CANONICAL BYTE VERIFICATION:
PASS

IMMUTABLE OBJECT HASH VERIFICATION:
PASS

GENERATION MEMBERSHIP:
PASS

GRAPH CLOSURE:
PASS

CACHE INTEGRITY REVALIDATION:
PASS

COLD ACQUISITION:
PASS

IDENTICAL GENERATION OBJECT REDOWNLOADS:
0

SMALL INCREMENTAL REUSE:
PASS

INDEPENDENT HTTP REQUEST COUNTING:
PASS

OBSERVATION EXPIRATION:
PASS

GENERATION CHURN:
PASS

MIXED-GENERATION REJECTION:
PASS

DURABLE STAGING:
PASS

FRESH-PROCESS RESTART/RESUME:
PASS

PROCESS CRASH BOUNDARIES:
7 VERIFIED

NETWORK FAILURE RECOVERY:
FAIL

RETRY BOUNDS:
PASS

CONCURRENCY SAFETY:
FAIL

RESOURCE BOUNDS:
FAIL

ACTUAL SYNTHETIC D3A/D3B INTEGRATION:
PASS

NEW INDEPENDENT AUDIT CASES:
70 PASS
4 FAIL
0 INCONCLUSIVE

E2 EXISTING TESTS:
124 PASS
0 FAIL

E1 REGRESSION:
PASS

E1-A01:
PRESERVED

E1-A02:
PRESERVED

FULL FLUTTER TESTS:
970 PASS
0 FAIL
2 SKIP

FLUTTER ANALYZE:
PASS

FLUTTER BUILD:
PASS

BACKEND REGRESSION:
1315 TESTS
1540 SUBTESTS
PASS

RUFF:
PASS

COMPILEALL:
PASS

GIT DIFF CHECK:
PASS

OFFLINE BASELINE V4:
UNCHANGED

FROZEN OFFLINE B/J:
UNCHANGED

SNAPSHOT V7:
UNCHANGED

NORMAL FLUTTER READ/WRITE:
UNCHANGED

BACKEND RUNTIME:
UNCHANGED

ACTIVE GENERATION:
NOT IMPLEMENTED

SEGMENTED ENDPOINTS:
NOT ACTIVATED IN PRODUCTION

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
1

NEW LOW:
0

UNRESOLVED BLOCKERS:
1 — E2-A01

SAFE TO START T6.6E3:
NO

SAFE TO DEPLOY:
NO

FINAL VERDICT:
FAIL — T6.6E2 CORRECTION REQUIRED

NEXT ACTION:
E2-A01의 native 응답 정리를 교정하고 보존된 failing 회귀 및 독립 재감사를 통과시킨다.
```

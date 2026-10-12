# T6.6E2 — Incremental Fetch & Verification

## 1. 시작점과 범위

시작 commit은 `bd3a7e08c5b810c8c30d26e498d1994218b33b71`이다. 변경 전
branch `main`, HEAD, main, origin/main, 실제 원격 main이 일치했고 working tree는
clean이었다. E1-A01/A02 독립 재감사 PASS 기록 및 과거 감사 결과를 수정하지 않는다.

E2는 **인증된 관측의 immutable graph 수집과 검증된 staging**이다. E3의
`CompleteTargetVerified`, active/accepted pointer, UI read-source 교체, frozen B/J
통합을 구현하지 않는다. `graph_verified`는 활성화 증명이나 독립 금융 검증이 아니다.

주요 source:

- `mobile/lib/src/segmented/transport.dart`: 제한된 인증 transport, 오류 envelope.
- `api_transport.dart`: 기존 API client에 대한 명시 opt-in adapter.
- `fetch.dart`: acquisition, retry, resume, cancellation, lease cleanup.
- `graph.dart`: typed membership 및 다운로드 graph closure.
- `store.dart`: 기존 E1 저장소의 opt-in E2 bookkeeping 확장.
- `mobile/lib/src/api_client.dart`: 기존 client/session을 빌려 주는 generic callback
  `withIsolatedTransport`만 추가. 정상 호출 경로에서 E2를 import/실행하지 않는다.

새 persistence/HTTP framework나 dependency는 없다. backend source, C1/hash domain,
금융 공식, 배포 설정, 앱 버전은 변경하지 않는다.

## 2. 실제 D3a/D3b wire contract

규범은 `t66c-delta-sync-protocol.md` §7–17, §16-S, §23–27, §30이며 실제
`backend/isolated_sync/{canonical,segments,patricia,finalization,observation,http,transfer,retention,workers}.py`
및 기존 tests와 대조했다. 임의 observation GET이나 별도 manifest endpoint를 만들지 않는다.

| 연산 | 실제 요청/응답 |
| --- | --- |
| 관측 + manifest | `POST /api/sync/v1/observations`, `{protocol:1,request_id:UUID,base:null,inline_bytes:0}`. 새 관측 201, 같은 요청 retry 200 |
| typed object | `POST /api/sync/v1/observations/{id}/objects`, `{protocol:1,request_id,items:[{path:[hash...],offset:U64,length:int}]}` |
| chunk | 200, `{protocol,request_id,observation_id,chunks:[{ref,offset,length,data_base64}]}` |
| D3c release | `DELETE /api/sync/v1/observations/{id}`, 204 빈 body, idempotent |

Manifest의 Target에 인증 principal, NS, revision, Versions, Context 및 네 Ref가
결합된다. Target의 `sync_root`는 E1의 `view` domain hash로 검사한다. 내부 input-proof
root는 다운로드 root가 아니다. Outer HTTP JSON과 object의 원본 C1 bytes를 구별한다.

E2에는 accepted E3 provenance가 없으므로 `base=null`을 사용한다. 이는 raw revision을
accepted baseline으로 가장하지 않기 위한 선택이다. Incrementality는 검증된 Ref의
로컬 재사용으로 구현한다. Batch/inline은 사용하지 않으며 새 wire format이 아니다.

## 3. HTTP/auth 연결과 신뢰 문맥

`segmentedTransportForApi(api)`는 `MoneyNoteApiClient.withIsolatedTransport`를 통해
기존 `http.Client`, base origin, 현재 secure-storage session getter를 빌린다. 별도
로그인·credential store·cookie 저장소가 없다. 이 모바일 adapter는 기존 mobile Bearer
방식을 사용한다. Borrowed client를 닫지 않는다.

`AuthenticatedSegmentedTransport`는 canonical trusted HTTPS origin만 받는다.
고정된 sync locator 이외의 URL, redirect, 다른 origin으로 token forwarding을
거부한다. 선택한 원래 session과 현재 session을 요청 전후·body chunk마다 비교한다.
로그에는 credential이나 payload를 출력하지 않는다. 로컬 오류는 sanitized code만 가진다.

호출자는 이미 E1에 결합한 trusted origin/expected principal/NS/Versions의 store를
제공한다. `CacheNamespace.verifyTarget`로 다른 principal/dataset/epoch/Versions를
거부한다. namespace discovery나 정상 앱의 capability selector를 구현한 것이 아니다.
현재 isolated capabilities 404 및 R1 `large_restore` gate를 우회해 정상 runtime을
선택하지 않는다. 이 API는 합성 테스트/명시 격리 호출용이며 자동 fallback도 없다.

## 4. Observation과 manifest 검증

`IncrementalFetcher._observe`는 요청 nonce, protocol, available 상태, UUID,
최대 900초 UTC lease, Target hash와 cache context를 E1 model로 검사한다. 자신이
보낸 `base=null`, `change_kind=initial`, `inline_objects=[]`도 확인한다.

같은 nonce 재시도는 canonical manifest 내용이 정확히 같아야 한다. 처음 받은
manifest와 마지막 같은 nonce 조회를 비교하여, graph 수집 뒤 서버의 실제 terminal
credential/expiry 검사를 다시 통과한다. 단말 wall-clock에 skew 허용이나 lease 연장을
추가하지 않는다. 로컬 생성 시각은 bookkeeping에만 쓰인다.

성공/중단 뒤 release는 최대 2초 cleanup budget의 best effort다. D3b-only server의
미지원 응답이나 cleanup 실패는 bytes 무결성을 변경하지 않으며 최대 lease가 남는다.
Release는 authorization 연장이 아니고, 종료된 observation으로 E3 활성화를 허가하지 않는다.

## 5. Typed fetch와 정확한 bytes

Parent를 먼저 E1으로 검증한 후 `VerifiedObject.children`의 typed Ref만 따라간다.
Path는 manifest의 승인된 raw/index/hot/control root에서 시작한다. Hash를 URL이나
로컬 파일명으로 사용하지 않는다. 매 요청 nonce/observation/ref/offset/decoded length를
요청값과 비교하며 strict base64를 E1 `ObjectChunk`로 검사한다.

Object 전체 크기를 먼저 로컬 policy와 비교하고 최대 1 MiB chunk로 조립한다.
원본 전체 C1 bytes와 domain-separated SHA-256, type, version, NS/schema를 검증한
뒤 **E1 `putVerifiedObject`만** 사용한다. 부분 payload나 HTTP success를 verified로
기록하지 않는다. 끊긴 객체의 부분 chunk는 저장하지 않고 해당 객체만 다시 받는다.

## 6. Cache reuse와 graph closure

Cache hit도 `getVerifiedObject`의 실제 BLOB/C1/hash/typed-edge 재검증을 거친다.
기존 flag만 신뢰하거나 손상된 bytes를 조용히 수선하지 않는다. Cached object는 현재
manifest의 검증된 parent reference를 통해 도달했을 때만 후보 graph에 포함된다.

`verifyAcquisitionGraph`는 순차 DFS와 identity별 compact summary를 사용한다.
11개 table 순서/coverage, table/descriptor의 실제 child 대응, non-root B+tree fanout,
Patricia count/branch/maximal prefix, hot의 정확한 Target Context를 검사한다.
중복 descendant는 다시 다운로드하지 않으며 새 edge마다 type/context를 검사한다.
Cycle, missing child, unsupported type/version, budget 초과는 실패다.

**E2 closure의 정확한 한계:** 모든 요구된 transferable 객체의 무결성과 graph 연결을
검증한다. Raw로부터 독립 생성한 F(raw)와 index identity의 일치, hot/raw 공통 필드,
복구 가능성의 최종 검증 및 guarded durable publication은 E3에서 다시 수행해야 한다.
빈 구조·hash-valid negative fixture의 closure 통과를 금융 generation 수락이라고
부르지 않는다. `VerifiedStagedGeneration`은 `CompleteTargetVerified`가 아니다.

## 7. Durable staging와 schema

`SegmentedClientStore.open(..., acquisition:true)`만 E2 bookkeeping profile을 연다.
정상 E1 default profile은 version 1 그대로다. 정확하고 건강한 v1 schema만
`BEGIN IMMEDIATE` 안에서 v2로 승격한다. 손상된 trigger를 복원하거나 profile을
묵시적으로 수선하지 않는다. E1-A02의 transaction-local exact DDL 검사는 그대로다.

v2는 E1의 8개 table에 다음 한 table과 usage insert/delete trigger 2개를 추가한다:

`acquisition(staging_id, state, error_code)`.

Local 상태는 `acquiring`, `interrupted`, `graph_verified`다. 오류 code는 최대 64자
대문자 identifier이며 interrupted에만 허용한다. 각 record의 logical charge는 256B다.
정확한 schema는 9 table/1 index/13 trigger, SQL 정의 총 23개다. Production schema
user_version 4와 무관하다. v2를 E1 default로 다시 열면 downgrade하지 않고 거부한다.

Manifest/checksum/네 root, 실제 verified object links는 기존 E1 tables에 저장한다.
Progress 기록은 같은 transaction 안에서 schema·staging·객체를 검증한다. 내부 write
검사에서 쓰지 않는 전체 staged-object COUNT만 생략하여 O(N²) bookkeeping을 피했다.
공개 `loadStaging.objectCount`와 기존 검증은 유지한다.

## 8. Resume, lease, generation churn

`acquire(resumeId:...)`는 durable manifest의 원래 nonce로 서버를 다시 조회한다.
같은 observation이 유효하면 정확한 manifest를 확인하고 graph를 재탐색한다.
410/new_observation이면 새 nonce·새 staging을 만들고 검증된 객체만 재사용한다.
새 Target이 다른 revision/root를 가지면 새 graph만 탐색하며 기존 root를 섞지 않는다.
Epoch/account 불일치는 기존 store를 자동 재해석하지 않고 실패한다.

네트워크 실패 후 staged links가 없더라도 이미 COMMIT된 verified object는 재사용할
수 있다. 로컬 `graph_verified`만으로 복구/완료를 선언하지 않는다. 재시작도 현재
서버 관측과 전체 필요한 graph를 다시 확인한다. Credential이 교체된 경우 구 nonce의
immutable binding을 임의로 바꾸지 않는다. 새 수집을 명시 호출할 수 있다.

## 9. Retry/cancellation/concurrency

`_request`는 idempotent observation nonce/body 또는 같은 chunk nonce/body를 최대
3회 재시도한다. Transport timeout/reset/truncation 및 승인된 `retry_same`만 자동
재시도한다. 100/250/500ms 기본 delay와 서버 retry_after를 사용하며 5초를 넘는
delay는 budget 오류다. `new_observation`도 총 3회로 제한한다.

401/403 reauthenticate, epoch/base full_resync, malformed/unsupported/StorageFailed
blocked는 자동 재시도·fallback하지 않는다. Status/code/action/envelope를 실제
server 계약에 맞춰 검사한다. 오류를 빈 성공이나 no-change로 바꾸지 않는다.

Application Dart isolate 전체에서 동시 acquisition을 거부한다. 별도 store의
acquisition도 같은 gate를 통과해야 한다.
Worker queue를 만들지 않고 최대 HTTP 동시 수는 **1**이다. 별도 프로세스/isolates는
UUID별 staging과 E1 SQLite serialization을 공유하며, 전역 네트워크 scheduler를
제공하지 않는다. 정상 앱에서 다중 acquisition을 등록하지 않았다.

`SyncCancellation`은 checkpoints와 cancellable delay/AbortableRequest에 전달된다.
완료된 요청의 listener는 token에서 실제로 제거한다. 취소 Future에 제거 불가능한
callback을 요청마다 누적하지 않는다.
선택한 http 1.6.0 IOClient의 request/response abort 지원을 확인했다. 늦은 transport
exception도 관찰한다. 임의로 주입하는 transport 역시 bounded response/abort 계약을
지켜야 한다. 동기 E1 verification/SQLite transaction 도중 강제 interrupt하지 않고
안전한 다음 checkpoint에서 중단한다. 이전 verified 데이터는 삭제하지 않는다.

## 10. Resource bounds

기본 제한은 chunk/decoded response 1 MiB, body 3 MiB, path 512 hashes,
unique graph objects 100,000, edges 200,000이다. E1의 로컬 object 64 MiB,
payload 합계 512 MiB, metadata 32 MiB, staging 128개 제한을 유지한다.
이는 서버가 모든 object를 1 MiB로 제한한다는 뜻이 아니다.

큰 object 하나의 원본과 E1 검증 copy/parsed data는 필요하지만 전체 generation의
financial payload list는 유지하지 않는다. DFS summaries는 typed refs와 count/range/
prefix만 갖는다. 전체 RSS의 엄격한 상한이나 기기 성능을 증명했다고 주장하지 않는다.
Closed graph 검증은 캐시 hit에서도 O(visited bytes + V + E)다. 정상 금융 API·기존
refresh·관측 server hot path에 새 O(N) 작업을 넣지 않았다.

Staging은 128개에서 fail closed하며 unbounded로 누적하지 않는다. 사용자는 필요
없어진 local staging만 기존 `removeUnreferencedStagingData`로 명시 정리할 수 있다.
객체 GC나 accepted/frozen data retirement는 E2에서 구현하지 않았다.

## 11. 합성 통합 환경과 독립 oracle

`scripts/benchmarks/t66e2_server.py`는 **새 RetentionSandbox**만 생성한다. 실제
D1/D2b bootstrap/finalizer, D3a repository, D3b ASGI/auth/session hashing, D3c
release를 사용한다. Credential은 매 실행 무작위 생성하며 pipe 외 로그/fixture에
저장하지 않는다. Production path/.env/network listener를 사용하지 않는다.

Dart `BackendBridge`는 HTTP client seam을 통해 실제 TestClient ASGI 응답을 전달한다.
이는 실제 서버 endpoint/auth/SQLite 통합이며 실제 TLS socket/Android 기기 검증은
아니다. Backend mock payload를 Dart가 스스로 정답으로 생성하는 테스트와 구별한다.

Python oracle은 direct SQLite BLOB + 독립 schema parser + hashlib로 reachable set을
계산한다. Dart 통합 테스트는 저장된 bytes를 비교하고 직접 financial source rows와
11개 table을 대조하며, 다운로드 facts로 별도 Patricia builder의 root를 재구성한다.
Production graph walker로 expected set을 만들지 않는다. Payload request count도
bridge의 실제 요청 횟수와 비교한다.

동일 Target benchmark에서만 test-only `_MESSAGE_RANDOM.randrange`를 고정한다.
실제 서버에서는 같은 raw revision에서도 Judgment hot bytes가 달라질 수 있고,
그 경우 hot 다운로드는 올바른 동작이다. 금융 계산/서버 구현은 패치하지 않는다.

## 12. 테스트·측정·회귀 결과

2026-10-12 실행한 결과다. 과거 baseline 수치를 새 결과로 인용하지 않는다.
원래 독립 감사 보고서는 변경하지 않았다.

| 검사 | 이번 실행 결과 |
| --- | --- |
| 새 E2 tests | **124 PASS / 0 FAIL**: acquisition 72, transport 30, staging/schema 14, 실제 SIGKILL 3, 실제 ASGI integration 5 |
| Flutter 전체 | **970 PASS / 0 FAIL / 2 SKIP**. 기존 E1 307개(원래 96 + A01/A02 211), offline/B/J/Baseline/Snapshot 회귀 포함 |
| 원래 E1 독립 감사 + targeted re-audit 재실행 | **111 PASS / 0 FAIL**. 원본 audit 73개와 re-audit 38개; 후자의 서버 금액 oracle 4,755개 포함 |
| E1 원본 반례 replay | **PASS**: U+001C–U+001F bytes 보존, BOM 거부, missing-trigger write 거부와 fresh SQLite 상태 확인 |
| Backend 전체 | **1,315 tests + 1,540 subtests PASS**, 1 dependency deprecation warning, 1,848.33초 |
| Safety/diagnostic | **60 PASS**, 1 dependency deprecation warning |
| Flutter analyze / Dart format | **PASS / PASS** |
| Flutter debug APK build | **PASS**, 설치하지 않음. 기존 Gradle/AGP/Kotlin 향후 지원 경고만 있음 |
| Ruff / compileall / git diff --check | **PASS / PASS / PASS** |
| Frontend npm build | **PASS**, frontend source 변경 없음 |

새 test source는 `mobile/test/segmented_{fetch,transport,acquisition_store,fetch_crash,http_integration}_test.dart`다.
실제 SIGKILL 경계는 acquisition INSERT 전후 COMMIT 및 staged-object link INSERT다.
Fresh SQLite에서 이전 verified object 보존, 미완료 link rollback, FK/integrity,
lock 해제, resume와 active pointer 부재를 검사했다. 기존 E1의 실제 process-termination
7개도 전체 suite에서 다시 통과했다. OS/power-loss durability 검증은 아니다.

통합 oracle은 **11/11 table, 저장 bytes, global Patricia**를 확인했다. 관측 T의
다운로드 도중 writer U가 COMMIT해도 수집 결과는 T의 direct-source oracle과
일치했다. 별도 테스트는 같은 raw revision의 새 hot wording을 유효한 새 Target으로
수집하고 hot object 1개만 추가 다운로드함을 확인한다.

아래 값은 최종 전체 Flutter 실행에서 얻은 HOST 단일 표본이다. 정확한 원본 단위와
resource bounds는 `docs/benchmarks/t66e2/summary.json`, 재현 및 oracle 설명은 같은
디렉터리 `README.md`에 있다. 20회 표본·median·production 성능 개선은 주장하지 않는다.

| 수집 | Manifest / object / release 요청 | Cache 재사용 | Payload bytes | 총 소요 |
| --- | --- | --- | --- | --- |
| Cold | 2 / 1,168 / 1 | 0 | 751,847 | 234.027초 |
| 동일 Target | 2 / **0** / 1 | 1,168 | **0** | 11.003초 |
| Bounded mutation + concurrent writer | 2 / 16 / 1 | 1,152 | 165,510 | 10.201초 |
| 중단 후 reopen/resume | 3 / 14 / 1 | 1,154 | 162,171 | 17.962초 |

마지막 logical staging metadata는 1,310,124B다. 동일 Target에서도 현재 인증/manifest
검증과 cache byte 검증은 생략하지 않았다. Zero payload download는 zero network나
O(1) graph 검증이라는 뜻이 아니다. Cold elapsed는 순차 인증 HTTP seam 및 durable
per-object staging 비용을 포함한다. 이는 향후 bounded batch 최적화 여지가 있지만
E1 검증이나 terminal authorization을 우회할 근거가 아니다.

검증 명령:

```sh
cd mobile
flutter test --no-pub --machine
flutter analyze --no-pub
dart format --output=none --set-exit-if-changed lib/src/segmented lib/src/api_client.dart test/segmented* test/support/segmented*
flutter build apk --debug --no-pub --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18081
```

```sh
cd backend
../.venv/bin/python -m pytest -q --junitxml=/tmp/money-note-e2-backend.xml
```

Root에서 기존 independent audit/re-audit/replay, `scripts/tests scripts/benchmarks`,
Ruff, compileall, frontend `npm run build`, `git diff --check`도 실행했다.
실행 명령과 재현 방법은 benchmark README에 보존했다. 성공 로그 전체나 credential,
financial payload를 release artifact로 저장하지 않는다.

## 13. E3 handoff와 제한

Handoff는 local staging UUID, immutable manifest/Target, graph Ref set/edge count,
table counts, acquisition metrics다. 권한 증서·active pointer가 아니다. E3는 fresh
auth/owner/mode/mutation fence, durable object 재검증, F(raw)/index, hot/raw, 정확한
Snapshot 복구 가능성과 atomic activation/rollback을 구현·감사해야 한다.

부분 object chunk resume, batch 최적화, 자동 metadata/object GC, production capability
선택, 기기 TLS/실기기 성능, active-generation publication은 구현하지 않았다.
첫 manifest 응답을 받기 전에 process가 종료되면 observation ID/staging은 아직
알 수 없다. 다음 수집은 새 관측을 얻으며, 응답을 잃은 서버 lease는 기존 최대
900초 lifecycle/쿼터에 남을 수 있다. 임의 release ID나 stale authorization을 만들지
않는다. 큰 graph는 lease 안에 완료되지 않아 bounded 재관측/명시 resume가 필요할
수 있다. 모든 지원 크기의 단일 lease 완료나 자동 foreground/background rollout을
보장한다고 주장하지 않는다.
OS crash·hardware power-loss 보장은 주장하지 않는다. E1 원래 process-crash 경계와
E2 bookkeeping/progress의 실제 SIGKILL 경계를 검사한다.

## 14. 기존 시스템 격리와 production safety

E2를 normal startup/AppState/UI/navigation/online sync에 등록하지 않았다. 현재
금융 read/write·backend·schema v4·Snapshot v7·OfflineBaseline v4·frozen B/J·backup
정책·금융 projection은 불변이다. 실제 offline baseline/Snapshot 파일의 byte 비교도
새 acquisition 테스트에 포함한다. Segmented endpoints와 sync는 production 미활성이다.
Production data/API/credential/service 접근, deployment, migration, APK 설치는 없다.

## 15. Commit/push와 다음 gate

내부 completion gate 결과는 **T6.6E2 COMPLETE — READY FOR INDEPENDENT IMPLEMENTATION AUDIT**다.
알려진 미해결 Critical/High/Medium E2 blocker는 0개다. 이는 독립 감사 PASS 판정이 아니다.
E2 source/tests/harness/측정/report만
`feat(flutter): add T6.6E2 incremental fetch and verification`로 commit/push한다.
최종 hash는 자기 참조 없이 최종 응답에 기록한다. HEAD/main/origin/main/실제 원격
main과 clean 상태를 재확인한다. Commit은 배포 승인이 아니다.

다음 gate는 **독립 E2 구현 감사**다. 그 PASS 전 E3 시작·배포·segmented activation을
승인하지 않는다.

---

## 16. E2-A01 TARGETED CORRECTION

### 16.1 기준과 원본 감사 이력

시작은 clean `main`의 `814eab506aa8457d10a7302241a26120b9389ff6`이며
HEAD/main/origin/main/실제 remote main을 확인했다. 원래 E2 구현 commit은
`69a8fd15b581357ef4be859fec03525bd6070fb4`다. 독립 감사는 **FAIL — T6.6E2
CORRECTION REQUIRED**, 70 PASS / 4 FAIL, Medium E2-A01 한 건을 기록했다.
그 감사 보고서와 과거 `docs/benchmarks/t66e2-audit/summary.json`은 변경하지 않았다.
이 절은 구현자의 교정 검증이며 독립 targeted 재감사 PASS가 아니다.

수정 전에 원본 명령을 직접 실행했다.

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66e2-audit/test_audit.py -k native
```

실제 loopback HTTPS와 새 synthetic store에서 **1 PASS / 4 FAIL**을 재현했다.
Auth 변경/redirect/과대 Content-Length의 첫 오류는 각각
`AUTHENTICATION_CHANGED`/`REDIRECT_REJECTED`/`RESPONSE_SIZE_EXCEEDED`였지만
pool=1의 다음 정상 요청은 모두 `TRANSPORT_TIMEOUT`, 실제 서버 요청은 각 1건이었다.
Public acquire 6회 이후 서버 active는 `[1,2,3,4,5,6]`이었다. 별도 임시 디렉터리에
수정 전 library를 복원한 추가 계측에서도 **실제 client TCP FD가 같은 순서로 누적**됐다.
원본 반례를 단순 예외 확인으로 대체하지 않았다.

### 16.2 실제 원인 및 response 소유권

`mobile/lib/src/segmented/transport.dart`의 `AuthenticatedSegmentedTransport.exchange`
내부 `run()`이 `AbortableRequest`를 만들고 빌린 `http.Client`로 보낸다. Response는
이 operation이 소유하지만 client 자체는 application 소유이므로 닫으면 안 된다.
Header 후 auth/cancel/contentLength/redirect 검증이 body의 `await for`보다 먼저 실행된다.
기존에는 여기서 throw하면 response body를 구독·취소하지 않고 timer/listener만 정리했다.

현재 pinned `http 1.6.0`의 `IOClient.send`는 native `HttpClientResponse`를 감싼 controller의
`onListen`에서만 underlying subscription을 만든다. 이미 abort된 response를 처음 listen하면
abort 오류만 발행하고 native body를 구독하지 않는다. 따라서 `abortRequest()`만 호출하거나
그 뒤 wrapper stream만 취소하는 방법은 이 경로의 native 소유권 해제를 보장하지 않는다.

검토한 API는 설치된 public `package:http/io_client.dart`의 `IOStreamedResponse.detachSocket`,
실제 `http-1.6.0/lib/src/io_client.dart`와 `io_streamed_response.dart`, Dart 3.13.3의
`HttpClientResponse.detachSocket` 및 `_http/http_impl.dart`다. SDK의 client response
detach는 먼저 `_httpClient._connectionClosed`로 pool에서 분리하고 socket을 반환한다.
`Socket.destroy()`는 그 한 socket만 폐기한다. Body 완료를 기다리는 drain, subscription
cancel, 공유 client의 close를 서로 같은 조작으로 취급하지 않았다.

### 16.3 최소 source 교정과 오류 보존

제품 변경은 **transport.dart 한 파일**이다. `run()`의 header 검증 범위를 try/catch로
감싸고, 실패하면 timer와 cancellation listener를 제거한 뒤 `_discardResponse()`를 await하고
원래 exception/stack을 `rethrow`한다. 검증 규칙·오류 code·retry 정책은 바꾸지 않았다.

`_discardResponse()`는 실제 `IOStreamedResponse`라면 public API로 response의 socket을
detach하여 destroy한다. Socket이 없는 injected IO response 등은 일반 response stream을
listen/cancel하며 cancellation Future를 await한다. Cleanup 오류는 원래 오류를 덮지 않는다.
정리 대기는 **최대 2초**이고, timeout 후 늦게 반환된 detached socket도 등록해 둔 continuation이
폐기한다. 성공 응답의 기존 bounded `await for`, 길이 확인, 최종 auth/cancel 검사와 byte 반환은
그대로다. 공유 client를 close하거나 거부 body를 무한히 읽지 않는다.

같은 header 단계의 auth 변경, cancellation, 음수/과대 declared length, redirect, getter 예외를
공통 정리한다. 기존에 검사하지 않던 Content-Type 등의 새 acceptance rule은 만들지 않았다.
이미 timeout/cancel로 완료된 operation에 늦게 도착한 거부 응답의 정리도 시험했다.
Header 거부가 먼저 확정되면 정리 중 뒤늦은 deadline이 원래 오류를 바꾸지 않는다.

### 16.4 원본 oracle의 한계와 승인된 보강

첫 교정 뒤 pool=1의 다음 정상 요청은 성공했지만 **원본 server active assertion 네 개는
계속 FAIL**이었다. 이 중간 결과를 숨기지 않았다. 원본 fixture는 일부러 body를 끝내지 않는다.
Dart SDK `_HttpConnection`은 outgoing response가 완료될 때까지 parser를 pause하고,
`connectionsInfo()`는 그 `_ACTIVE` application 상태를 센다. Peer의 client FD가 이미 닫혀도
서버의 보류 response는 계속 active로 기록될 수 있다. Client가 원격 application response의
완료까지 강제한다는 보장은 없다.

프로젝트 소유자는 **원본 이력 보존과 oracle 보강을 명시 승인**했다. 이에 원본 native
시나리오의 요청·header·보류 body·pool 설정을 유지하며, worker PID와 새 synthetic destination
port로 한정한 `ss` 결과에서 실제 client TCP FD를 추가로 센다. 원래 server 계수도 계속 보존한다.
거부 응답 뒤 FD 0과 pool=1의 다음 HTTP_200을 모두 요구한다. 정상 응답의 재사용 가능한 idle
FD 1개를 누수로 세지 않는다. 기존 독립 감사 verdict나 과거 측정값을 소급 변경하지 않았다.

| 원래 실패 시나리오 | 수정 전 client FD / 다음 정상 요청 | 수정 후 client FD / 다음 정상 요청 | 현재 판정 |
|---|---|---|---|
| native-auth | 1 / TIMEOUT | 0 / HTTP_200, 실제 요청 2건 | PASS |
| native-redirect | 1 / TIMEOUT | 0 / HTTP_200, 실제 요청 2건 | PASS |
| native-oversized | 1 / TIMEOUT | 0 / HTTP_200, 실제 요청 2건 | PASS |
| native-repeated | 6회 FD 1,2,3,4,5,6 | 6회 FD 0,0,0,0,0,0 | PASS |

위 네 개는 별개 defect가 아니라 같은 response 소유권 누락의 결과다. 정상 native 대조군도
HTTP_200 두 번, 실제 connection 1개 재사용으로 PASS다. 수정 후 서버의 보류 active 수치는
각 1 및 `[1,2,3,4,5,6]`으로 여전히 기록된다. **이 서버 수치가 0이라고 주장하지 않는다.**

### 16.5 테스트와 독립 persisted-state 증거

`mobile/test/segmented_response_cleanup_test.dart`의 새 **13 tests**는 같은 header 단계
5조건, await 완료 barrier, 늦은 timeout의 오류 덮기 방지, cleanup exception 관측,
response-specific socket 폐기, socket 없는 IO fallback, 2초 bounded wait 및 late socket 폐기,
cancel/timeout 뒤 늦은 거부 응답, server golden C1/hash를 검사한다. 공유 client가 닫히지
않고 같은 client로 다음 정상 요청이 성공하는지도 확인한다. 취소 호출 횟수와 완료 시점을
별도로 측정하며, helper mock만으로 native 교정을 판정하지 않는다.

`docs/benchmarks/t66e2-audit/native_transport.dart`와 native pytest는 실제 연결과 pool 가용성을
검사한다. `docs/benchmarks/t66e2-a01/test_cleanup.py`의 추가 **5 tests**는 같은 반례에 대한
TCP FD 및 별도 Python SQLite 검증을 제공하고 수정 전 commit 비교도 지원한다. 거부 6회 후
fresh connection에서 objects/staging/acquisition 각 0, `integrity_check=ok`, FK 오류 0이었다.
미검증 bytes나 staging 완료/active pointer를 commit한 정황은 없다.

재현 명령·전후 측정·도구 한계는 `docs/benchmarks/t66e2-a01/README.md`와 `summary.json`에
보존한다. 상세 실행 로그와 DB는 `/tmp/money-note-e2-a01-*`, pytest 임시 디렉터리에 두며
credential이나 금융 payload를 release evidence로 복사하지 않는다.

### 16.6 실제 회귀 결과

| 검사 | 현재 실행 결과 |
|---|---|
| 원본 반례, 수정 전 | 1 PASS / 4 FAIL, 결함 재현 |
| 복원 baseline의 TCP FD oracle | 1 PASS / 4 FAIL, 실제 FD 누적 재현 |
| 원본 native 5조건, 승인된 oracle 보강 후 | 5 PASS / 0 FAIL; 원래 실패 4건 모두 PASS |
| 추가 native TCP/SQLite | 5 PASS / 0 FAIL |
| 새 Flutter cleanup | 13 PASS / 0 FAIL |
| 기존 E2 Flutter | 124 PASS: fetch72/transport30/store14/crash3/실제 ASGI5 |
| 기존 E1 Flutter | 307 PASS: protocol58/store31/crash7/money166/schema45 |
| 기존 E1 독립 감사/재감사 | 111 PASS / 0 FAIL |
| 기존 E2 non-native 독립 corpus | 69 PASS / 0 FAIL, 실제 ASGI 및 7 SIGKILL 경계 포함 |
| 전체 Flutter | **983 PASS / 0 FAIL / 기존 2 SKIP**, hidden loader 제외 |
| backend 전체 | **1,315 tests + 1,540 subtests PASS**, failures/errors=0, 1587.52초 |
| safety/diagnostic | 60 PASS |
| Flutter analyze / native audit Dart analyze | PASS / PASS |
| 변경 및 segmented Dart formatting | PASS |
| 전체 Dart formatting | 기존 불변 파일 10개에서 FAIL, 기존 감사와 동일; 자동 수정하지 않음 |
| debug APK compile | PASS, 새 합성 development origin; 설치하지 않음 |
| frontend | 21 tests PASS, npm build PASS |
| Ruff / compileall / git diff --check | PASS / PASS / PASS |

과거 독립 감사의 **첫 backend 전체 실패**도 별도로 보존한다.
`tests/test_isolated_sync_transfer.py:497`의
`test_bounded_concurrent_quota_and_same_request_status`가 기대
`[201,201,201,201,429]` 대신 `[201,201,201,201,503]`을 관찰했다. 당시 분리 재실행과
full rerun은 통과했다. 동시 부하 조건은 있지만 원인은 입증되지 않았으며 E2-A01에
기인한다고 주장하지 않는다. 이번 backend full run은 첫 완료 실행에서 전체 PASS였다.

초기 새 테스트의 constructor/unused-import 문제와 late mock timeout의 시험 설계 문제는
수정 후 재실행했다. 그 중간 실행을 PASS 건수에 합산하지 않는다. Android build의 기존
Gradle/AGP/Kotlin 지원 예정 종료 경고와 backend dependency warning도 새 결함과 구분한다.

### 16.7 격리, 비용, 한계와 다음 gate

정상 응답에는 추가 DB/graph scan, body buffering 또는 network round trip이 없다.
추가 비용은 try 범위와 header 실패 시 bounded response 정리다. Microsecond 성능 향상이나
모든 임의 client의 정리 latency 상한을 주장하지 않는다. 검증한 native IOClient의 detach는
이미 수신한 response에 대해 pool 분리와 socket 폐기를 제공한다. 악의적/비준수 injected
client가 cancel/detach를 완료하지 않으면 기존 client API 계약 밖이며, 2초 뒤에도 late 정리
continuation은 유지하지만 그 client의 실제 resource 해제를 보증한다고 주장하지 않는다.

실제 process-crash 회귀는 E1의 7경계와 E2 독립 corpus의 7 SIGKILL 경계를 다시 실행했다.
새 DB transaction/persistence boundary는 추가하지 않았다. OS crash/hardware power-loss는
보장하지 않는다. 실제 local TLS 검증은 Android 기기 설치나 production network 검증이 아니다.

E1 monetary/BOM/raw-string/C1와 mandatory SQLite trigger, object store, graph/manifest/lease/
retry/concurrency/staging은 수정하지 않았다. Backend, 금융 공식, schema v4, OfflineBaseline v4,
frozen B/J, Snapshot v7, startup/UI/normal financial read/write/online sync는 불변이다.
E3/active-generation publication은 미구현이며 segmented sync/endpoints는 미활성이다.
Production DB/API/credential/service 접근·배포·migration·restart·APK 설치는 수행하지 않았다.

내부 판정은 **E2-A01 FIXED — READY FOR INDEPENDENT TARGETED RE-AUDIT**다. 새로 확인한
미해결 Critical/High/Medium blocker는 0이다. Commit 대상은 이 교정과 직접 테스트·증거·이
addendum뿐이며 원본 독립 감사 보고서는 그대로다. Commit message는
`fix(flutter): release E2 response resources on header rejection`를 사용한다.
최종 hash와 push 후 HEAD/main/origin/main/실제 remote main 및 clean 검증 결과는 최종 응답에
기록한다. 자기 참조 없이 이 addendum의 commit은 다음 명령으로 찾을 수 있다.

```sh
git log -1 --format=%H -- docs/t66e2-implementation.md
```

다음 단계는 **독립 E2-A01 targeted 재감사**이며, PASS 전 E3 시작·배포·segmented sync 활성화는
허용하지 않는다.

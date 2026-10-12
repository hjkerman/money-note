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

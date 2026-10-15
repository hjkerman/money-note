# T6.6E4 — P0 독립 감사 후 구현 재개 기록

## 1. 현재 판정과 원본 보존

**T6.6E4 INCOMPLETE — TARGETED CORRECTION REQUIRED**

P0 checkpoint와 E4의 격리 읽기·완전한 legacy materialization·분리된 pending view를
구현했다. 이것을 E4 전체 완료, 독립 E4 감사 PASS 또는 일반 사용자 Offline 준비 완료로
확대하지 않는다. 아래 §9의 E4-owned 상태 변경 handoff는 아직 구현하지 않았다.
올바르게 닫힌 R1 gate 자체를 E4 결함으로 판정한 것이 아니다.

소유자는 원래 다섯 파일의 전체 hash를 유지하기 위해 재개 보고서를 분리하도록 승인했다.
따라서 `t66e4-implementation.md`의 BLOCKED 이력, P0 구현/감사 보고서와 원래 진단의
assertion·결과를 수정하지 않았다. 원본 문서를 최신 판정처럼 재작성하지 않는다.

## 2. P0 checkpoint

최초 `HEAD = main = origin/main = actual remote main`은
`ab59d6bbc39f27c36beb059f984ef527ac7b0bef`였다. staged 변경은 없고 기존 P0 변경과
감사 증거가 미커밋 상태였다. reset/restore/clean/stash를 수행하지 않았다.

독립 감사 `worktree-targets.json`의 **18개 파일 전부**, `protected-source.json`의
**29개 source 전부**, 원래 진단 **5개 전부**가 기록 SHA-256과 일치했다.
각 checkpoint의 명시적 index 경로와 bytes를 대조하고 다음과 같이 분리했다.

| checkpoint | commit | 내용 |
| --- | --- | --- |
| P0 구현 | `35d7c53f1652310de75e492a98491efc3fd5cbba` | 정확히 감사된 18개 파일; 원래 진단 포함 |
| 독립 감사 증거 | `671bb8668c16cba5f3729d9fb63fda4dbd1c67c5` | 독립 보고서·도구·측정 14개; 제품 source 변경 없음 |

`git show 35d7c53:<path>`의 18개 SHA도 감사 manifest와 전부 일치했다.
E4에서 P0 monetary source 7개를 수정하지 않았다. 새 isolation 시험은 현재 P0 source,
원래 5파일, 기존 startup/coordinator/OfflineProjection/C1/E2/verifier 등의 bytes를 대조한다.
AppState의 새 독립 read entry와 E3의 reader 중 write 거부 한 줄을 제거하면 각각 감사된
원본 source SHA와 같음도 검사한다. P0 독립 감사 판정을 새 E4 코드에 전용하지 않는다.

## 3. 실제 계약과 구현 범위

규범은 `t66/c/t66c-delta-sync-protocol.md` §22/24/25/26/29/31/34와 I25다.
도메인·architecture 신뢰 경계·Offline 계약 및 실제 E1/E2/E3 source와 대조했다.

| 분류 | 기능 | 이번 구현 |
| --- | --- | --- |
| A — 격리 사용 가능 | E3 accepted provenance를 통한 hot/PK-page 읽기 | 구현 |
| A | 원 complete raw/control의 정확한 v7 materialization | 구현; 별도 full verification 필수 |
| A | 기존 frozen B/J의 원래 provisional view·online pending status를 별도로 읽기 | 구현; ack/rebase 없음 |
| A | 기존 AppState ticket/session/mode/user/lineage 아래 결과 반환 | 명시 isolated API만 구현 |
| B — E4-owned 후속 | 새 segmented frozen epoch의 durable pin·원 legacy logical lineage 결합 | 미구현 |
| B — E4-owned 후속 | 같은 fresh acquisition 요청에서의 eligible pending retirement·설치 handoff | 미구현 |
| C — R1 필요 | 일반 사용자 segmented Offline/recovery 활성화·large restore/MW | 미구현, gate CLOSED |

B의 미구현을 R1 책임으로 떠넘기지 않는다. 반대로 C를 developer flag나 작은 fixture로
승인하지 않는다. T6.6C 변경·새 인증 token·새 금융 공식·새 acknowledgment 계약은 없다.

## 4. Accepted handoff와 논리 읽기

`mobile/lib/src/segmented/store_read.dart`는 기존 publication store의 extension이다.
새 object DB나 accepted pointer, schema migration을 만들지 않는다.

1. 명시적으로 `recoverAcceptedGeneration()`을 실행한다. healthy session은 기존 E3
   provenance를 재사용하며 reopen/외부 COMMIT/손상에는 기존 full recovery가 필요하다.
2. `withAcceptedRead`의 native `BEGIN DEFERRED`와 실제 pointer SELECT로 SQLite snapshot을
   확정한다. 같은 owning connection의 recovered proof, schema/profile, pointer/sequence,
   data_version을 검사한다. staging/`graph_verified`만으로 read authority를 만들지 않는다.
3. scope의 한 generation/root set만 사용한다. 모든 객체 읽기는 기존 E1 bytes/hash/C1/
   namespace/edge 검사를 통과한다. PK page는 검증된 raw tree의 해당 path/leaf만 읽는다.
4. scope 종료 시 native ROLLBACK으로 읽기 transaction을 해제한다. primary 오류를
   보존하며 해제가 불확실하면 connection을 재사용하지 않는다.

callback은 동기 scope다. async callback/Future 결과는 거부하며 escaped view의 객체 접근도
거부한다. 반환 records는 detached immutable copies이고 typed hot 결과도 같은 root set에서
만든다. Async cursor·stream-based financial source를 구현했다고 주장하지 않는다.

DELETE journal의 SHARED read snapshot은 다른 connection의 writer COMMIT/GC를 막는다.
writer는 SQLITE_BUSY로 실패·rollback하고 scope 종료 뒤 재시도할 수 있다. 같은 connection의
write/close는 transaction 진입 전에 거부해 reader transaction을 잘못 rollback하지 않는다.
G1 읽기 중 G2 publication을 직렬화하고 이후 새 읽기가 G2를 보는 정책이지 lock-free
동시 COMMIT 정책이 아니다. OS가 process 종료 시 잠금을 해제하므로 영구 reader pin이나
crash-orphan lease를 만들지 않는다. **이 reader 보호는 §29의 영구 frozen pins를 대신하지 않는다.**

## 5. Legacy와 금융 값

`segmented/adapters.dart`의 `SegmentedAuthority`는 Target/generation/sequence/typed hot/
defaults를 가진다. snapshot/fingerprint 필드는 없으며 legacy envelope와 별개다.
현재 반환값은 detached read snapshot이다. 장기 보유할 complete-store handle이나 설치 권한을
이전하는 전체 §22 handoff가 아니며 AppState의 일반 금융 UI나 OfflineBaseline을 설치하지 않는다.
명시적으로 선택한 cache의 as-of Target을 읽을 뿐 새 서버 관측으로 현재 epoch를 발견하지 않는다.
현재 상태로 설치하는 fresh-context handoff는 §9의 미구현 범위다.

명시적 `materializeLegacyRead`만 기존 complete verifier로 다시 확인한 store-owned proof를
요구한다. 11개 table을 모두 읽고 §22의 exporter 순서로 정렬한다. NULL 우선·UTF-8 BINARY
text order·integral REAL/int·원 Unicode를 보존한다. 원 control의 exported_at/range/policy/
columns/schema/ownership metadata로 기존 `bundleHash`의 table/data/policy/content/Snapshot ID와
state fingerprint를 계산하고 기존 strict `AuthoritativeBundle.decode`를 통과시킨다.

`sync_root`를 legacy fingerprint로 대입하거나 partial Snapshot을 envelope에 넣지 않는다.
새로 materialize한 Snapshot을 이미 frozen된 B로 가장하지 않는다. 기존 B의 user/synced_at/
typed/defaults/resolved reconciliation ID는 pending view에서 그대로 읽으며 재생성하지 않는다.

P0의 `"\u001c+0001000.00\u001f"`, plus·leading zero·decimal·원문 codepoint를 보존한다.
새 money grammar나 floating-point 금융 변환을 추가하지 않았다. Summary/할인/잔액은 backend
projection을 기존 typed factory로 읽을 뿐 재계산하지 않는다. B/J 입력은 원 exactMoney 그대로다.

독립 `test/support/e4_backend_oracle.py`는 보존된 producer의 **새 합성 seed만** 확장한다.
Unicode, NULL-date archive, integral REAL, PK와 다른 exporter 순서, BINARY Unicode key를
포함한다. 실제 backend exporter·`_build_manifest`·fingerprint·migrated restore dry-run이
기대 Snapshot을 만든다. E4 output과 complete object/record/manifest를 직접 비교한다.

## 6. Pending/Offline/Legacy 공존과 현재 권한

`readPendingLegacyView`는 기존 OfflineStore/lineage validator/OfflineProjection을 재사용한다.
원래 frozen B + ordered J에서만 provisional view를 만들며 새 segmented G에 J를 적용하지
않는다. ONLINE에서는 full B를 읽거나 그 B로 frozen lineage를 만들지 않으며, online marker는
별도 경로로 읽는다. FINALIZING의 old J/new B는 이 adapter에서 unavailable로 거부한다.
Frozen view의 lineage는 기존 metadata에 기록된 fingerprint이며 새로 추정하지 않는다. orphan/mismatched lineage는
unavailable이며 authoritative empty state로 숨기지 않는다.

`AppState.readSegmentedForIsolatedUse`는 기존 coordinator의 원래 read ticket과 현재 user/
auth-generation/lineage/mode/session을 검사한다. 필요한 await 뒤와 lineage lock 안팎에서
재검사하고 session getter 뒤에도 context를 다시 확인한다. persisted receipt는 설치 권한이
아니며 새 read ticket은 historical accepted candidate의 publication/설치를 승인하지 않는다.

ONLINE/OFFLINE/RECONCILIATION_REQUIRED에서 명시 read만 허용한다. FINALIZING 및 recovery
blocked에는 우회 경로가 없다. OFFLINE read는 기존 frozen B/J와 segmented view를 별도
provenance로 반환할 뿐 mode/B/source를 바꾸지 않는다. online unknown/confirmed marker도
원 status로 반환하며 둘 다 이 read만으로 retire하지 않는다. 기존 approved acknowledgment와
replay는 계속 기존 AppState가 소유한다.

새 read entry의 기본값은 hot only다. pending/full legacy는 명시 비용 선택이며 authorization
flag가 아니다. startup caller·자동 fetch·자동 mode/source 전환·UI notify·baseline 저장은 없다.
`requireSegmentedOfflineRecovery()`는 현재 항상 `R1_RECOVERY_CONTRACT_REQUIRED`로 거부한다.
설정으로 열 수 있는 gate나 임의 recovery proof는 없다. 기존 일반 legacy Offline는 그대로다.

## 7. 검증·중간 실패와 비용

실제 실행 집계는 `benchmarks/t66e4/` 및 최종 아래 절에 기록한다. raw 성공 로그·실제
credential·테스트 DB·금융 payload는 commit 대상이 아니다. 새 독립 audit PASS는 주장하지 않는다.

개발 중 수정한 문제를 숨기지 않는다.

- 테스트가 없는 모델 `toJson`을 호출했던 compile 오류는 실제 모델 API로 교정했다.
- `Never` 반환 동기 throw가 Future-returning subtype으로 오분류된 문제를 수정하고 원 오류 보존을 검사했다.
- 동일 값 UPDATE는 SQLite가 physical write를 생략할 수 있어 외부 invalidation oracle를 실제 staging INSERT로 바꿨다.
- 큰 table의 두 번째 page에 정수 i-key를 전달한 결함은 301행 실제 backend fixture로 **0 PASS/1 FAIL,
  KEY_INVALID** 재현 후 원 typed string key로 수정했다. E1 parser를 바꾸지 않았다.
- ONLINE pending status만 읽는 경로가 full legacy B를 읽지 못하도록 별도 negative oracle를 추가했고,
  FINALIZING의 old J/new B를 임의의 새 frozen lineage로 표현하는 경로도 닫았다.
- 초기 benchmark의 import/type 오류와 package cwd 명령 오류는 성공으로 계수하지 않는다.

일반 hot read는 두 객체만 읽고 PK page는 최대 256개 반환한다. payload bound는 기존 E1
object/store quota를 따른다. Full legacy는 명시 O(N) 예외이며 complete full proof·정렬·flat hash와
26,214,400B local export budget을 사용한다. 이 local budget은 R1 worst-case budget 승인이 아니다.
ONLINE pending view는 full B를 읽지 않는다. 현재 standalone legacy frozen view는 매 호출
기존 full B를 읽고 logical lineage hash를 계산한 뒤 O(J) projection을 수행한다.
이 **O(N+J) 반복 비용은 아직 최적화하지 않았다**. 기존 AppState 소유의 검증된 frozen B
provenance를 안전하게 재사용하는 연결과 비용 회귀가 남았다. 새 streaming projection이나
대규모 J 처리 보장을 추가하지 않았으며 일반 hot read는 pending을 읽지 않는다.

독립 SQL observer는 제품 counters만 읽지 않고 폐기용 source copy의 실제 select/execute,
returned BLOB/row·pin writes를 센다. native VM/page I/O 전체나 production RSS 측정은 아니다.
Cold/reopen의 O(N)과 healthy 읽기의 비용을 분리한다. 정상 source에는 observer를 연결하지 않는다.

실제 SIGKILL 4개는 before/during/after read 및 full-proof 완료 경계를 사용한다. 독립 SQLite
pointer/pins/FK/integrity, fresh owning store의 complete recovery, 실제 legacy v7/B/J bytes 및
별도 Python process의 restoreability/fingerprint/logical lineage를 검사한다.
읽기에는 새 durable state transition이 없으므로 존재하지 않는 write/COMMIT 경계를 발명하지 않는다.
OS crash/전원 손실·Android 실기기 내구성을 입증했다고 주장하지 않는다.

## 8. 회귀와 영속 증거

최종 source의 집계는 [`regression-summary.json`](benchmarks/t66e4/regression-summary.json)에
보존했다. Flutter machine의 최종 `done.success=true`와 각 testDone 결과를 대조했다.
이전 개발 중 실행 결과를 최종 source의 증거로 대체하지 않는다.

| 실제 실행 | 결과 |
| --- | --- |
| 새 E4 adapter/legacy 읽기 | 42 PASS / 0 FAIL |
| 새 E4 AppState authority/race | 16 PASS / 0 FAIL |
| 새 E4 실제 SIGKILL | 4 PASS / 0 FAIL |
| 새 E4 source·원본 보존 isolation | 23 PASS / 0 FAIL |
| **새 E4 합계** | **85 PASS / 0 FAIL** |
| **전체 Flutter** | **1,362 PASS / 0 FAIL / 2 SKIP** |
| P0 기존 targeted regression | 183 PASS / 0 FAIL, 위 전체 Flutter에 포함 |
| 독립 P0 corpus 재실행 | 24,836개, 모든 differential mismatch 0 |
| 독립 P0 audit 시험 재실행 | Python 5 + Flutter 18 = 23 PASS |
| 기존 E1/E2/E3 실제 SIGKILL | 7 + 3 + 16 = 26 PASS, 위 전체 Flutter에 포함 |
| Backend 전체 | 1,315 tests / 1,540 subtests PASS, 0 FAIL |
| Flutter analyze | PASS, issue 0 |
| Flutter debug APK build | PASS, 설치하지 않음 |
| 변경 Dart 11파일 formatting | PASS, 변경 0 |
| Ruff / compileall / frontend npm build | 모두 PASS |
| git diff --check | PASS |

Full Flutter는 `mobile/`에서 `flutter test --no-pub --machine test`로 실행했다.
Machine summary에는 frozen B/J·OfflineBaseline·Snapshot·AppState 및 E1/E2/E3의 개별 파일
집계가 포함된다. E1 monetary/schema correction은 각각 166/45 PASS, E2 response cleanup은
13 PASS다. E3 I25 publication 30, incremental verification 6, I25 baseline 1 PASS를 포함한다.
E4 crash 4개를 포함한 실제 process-termination 시험은 총 30 PASS다.

Backend 실행은 `.venv/bin/python -m pytest backend/tests -q`이며 1,512.07초였다.
경고 1개는 기존 FastAPI TestClient의 httpx/Starlette deprecation이다. Backend product source를
바꾸거나 해당 경고를 E4 결함으로 재분류하지 않았다. Flutter build의 Kotlin toolchain 안내도
별도 기존 dependency 경고이며 assembleDebug는 성공했다. 10개 기존 무관 formatting 차이는
유지했고 전체 무관 파일을 reformat하지 않았다.

원 진단은 assertion을 고치지 않은 채 다시 실행하여 **3 PASS / 2 FAIL**을 확인했다.
두 FAIL은 교정 전 server-valid string 거부 기대를 보존한 역사적 재현이다. 이를 현재 monetary
회귀의 실패로 계수하지도, 원 expected 결과를 바꿔 PASS로 만들지도 않았다.

원시 machine log·backend JUnit·P0 differential 결과는 폐기용 `/tmp/mn-e4-*` 실행 자료다.
Commit 대상의 요약·source hashes·재현 명령과 실제 test source를 함께 남기며 금융 payload나
credential을 로그 artifact에 포함하지 않는다. 새 E4에 대한 독립 감사 PASS는 주장하지 않는다.

### 8.1 독립 SQL 작업량

최종 비용은 [`read-cost-with-storage.json`](benchmarks/t66e4/read-cost-with-storage.json)에 있다.
history 4/400의 현재 reachable graph는 142/1,728 objects, 실제 persisted objects는 153/1,744,
독립 SQLite 검사에서 root pin rows는 각각 8, accepted sequence는 각각 2다.

| 읽기 단계 | SQL statements (작은/큰 graph) | object body B (작은/큰) | raw rows (작은/큰) | full recovery | pin INSERT/DELETE/UPDATE |
| --- | --- | --- | --- | --- | --- |
| healthy hot | 71 / 71 | 9,451 / 9,451 | 0 / 0 | 0 / 0 | 모두 0 |
| 동일 hot 반복 | 71 / 71 | 9,451 / 9,451 | 0 / 0 | 0 / 0 | 모두 0 |
| 1행 PK page | 71 / 74 | 5,899 / 153,130 | 5 / 256 | 0 / 0 | 모두 0 |
| 실제 작은 generation 변경 후 hot | 91 / 91 | 9,543 / 9,543 | 0 / 0 | 0 / 0 | 모두 0 |
| 새 connection의 recovery+hot | 1,900 / 20,944 | 413,867 / 4,981,023 | 228 / 2,604 | 1 / 1 | 모두 0 |

Warm hot는 control/hot 두 객체만 읽으며 index node 재검증은 0이다. PK page는 1개 반환을
위해서도 해당 leaf 전체 5/256 rows의 bytes를 검사한다. 이를 storage 1행 읽기라고 표현하지
않는다. Fresh recovery의 raw/index 재검증은 허용된 O(N) 초기 비용이고, 이후 read에서
full recovery를 반복하지 않는다. 정상 hot·small-change hot는 이번 두 규모에서 unchanged
history 증가와 무관한 작업량이었다. 이 결과를 standalone frozen legacy view까지 확대하지 않는다.

이 probe의 healthy hot는 20,245/11,867µs, 동일 hot 반복은 18,566/12,601µs,
small-change hot는 18,363/15,187µs였다. Fresh recovery+hot는 371,839/3,459,819µs였다.
계측 overhead·JIT·host 차이가 포함된 유한 synthetic 실행이며 production/Android 성능 약속이나
보편적 시간 복잡도 증명이 아니다. 별도 DB connection의 committed-row 계수는 timed phase 밖이다.
RSS는 probe process의 현재 값으로 fixture/JIT/observer를 포함하며 peak memory로 주장하지 않는다.

### 8.2 source와 미구현 gate의 구분

| 구현 근거 | 실제 위치 |
| --- | --- |
| 명시 AppState read entry와 현재 guard | `mobile/lib/src/app_state.dart:516` |
| 완전 materialization proof·scope transaction | `mobile/lib/src/segmented/store_read.dart:13`, `:39` |
| generation-bound PK reader | `mobile/lib/src/segmented/store_read.dart:120` |
| 별도 segmented authority mapping | `mobile/lib/src/segmented/adapters.dart:34` |
| 원 exporter order와 v7 materialization | `mobile/lib/src/segmented/adapters.dart:104` |
| 기존 frozen pending view·ONLINE B scan 금지 | `mobile/lib/src/segmented/adapters.dart:190` |
| 항상 닫힌 R1 boundary | `mobile/lib/src/segmented/adapters.dart:20` |

원 task의 crash/ack/source transition 목록 중 **새 durable frozen 전환 및 pending retirement**는
아직 구현하지 않아 해당 E4 전환 crash 검사를 실행했다고 주장하지 않는다. Read-scope crash
검사와 기존 legacy 회귀가 green인 것은 이 미구현 gate의 대체 증거가 아니다.

## 9. 남은 E4-owned 작업과 완료 gate

현재 isolated data read는 반환되지만 다음 E4-owned 세 항목을 완성하지 않았다.

1. **§25.6–7 handoff:** fresh E2 취득부터 E3 publication, readback, eligible confirmed
   token/owner/lineage retirement와 complete UI installation까지 같은 원 AppState 요청 권한을
   유지하는 E4 오케스트레이션. 지금의 historical read 결과에 새 ticket을 붙여 shortcut으로
   설치해서는 안 된다. 기존 E3 entry는 계속 segmented-internal publication만 반환한다.
2. **§29 frozen handoff:** 새 segmented frozen generation의 영구 pins와 원 control/hot/raw/index,
   complete legacy logical B, 기존 metadata lineage 및 finalizing resolved-ID의 crash-consistent
   결합. 현재 read snapshot은 수명이 짧고 이 영구 의무를 충족하지 않는다. Active legacy B/J의
   §33 migration 유예를 유지하며 자동 rebase나 새 legacy lineage bridge를 발명해서는 안 된다.
3. **반복 legacy frozen view 비용:** 현재 loader의 full B read/hash 반복을 기존 AppState가
   소유한 검증된 frozen B의 data provenance 재사용으로 줄이고 큰 B/작은 J의 실제 작업량을
   측정해야 한다. publication authority나 J admission을 cache하거나 변경해서는 안 된다.

이 세 사항은 R1 자체가 아니라 E4 구현의 남은 범위다. R1 Large Restore/MW와 일반 사용자
활성화는 별도이며 계속 CLOSED다. 따라서 지금은 **SAFE FOR INDEPENDENT E4 AUDIT: NO**다.
확인된 green 회귀만으로 전체 stage completion을 선언하거나 incomplete E4를 commit하지 않는다.

## 10. Git·배포 경계

P0의 두 checkpoint는 로컬 main에 보존했다. E4 구현·tests·측정·이 문서는 미커밋으로 보존한다.
전체 E4 completion gate가 충족되기 전 E4 commit/push를 수행하지 않는다. 원격 main은
원래 E3 audit baseline이며, 로컬이 두 checkpoint만큼 앞선 상태를 clean/원격 일치로 가장하지 않는다.

최종 확인: `HEAD = main = 671bb8668c16cba5f3729d9fb63fda4dbd1c67c5`,
`origin/main = actual remote main = ab59d6bbc39f27c36beb059f984ef527ac7b0bef`.
Staged 변경은 없고 E4 source/tests/증거만 미커밋이다. P0 18파일의 현재 bytes와 구현 checkpoint의
bytes가 독립 감사 SHA와 계속 일치하며 원본 5파일도 그대로다. 후속 작업용 hash inventory는
`benchmarks/t66e4/worktree-preservation.json`에 둔다. 자기 자신을 제외한 보존 snapshot이며
새 작업 시작 시 달라진 bytes를 임의 복원하는 도구가 아니다.

production DB/API/credential/service를 사용하지 않았다. production SQLite user_version 4,
Snapshot v7/OfflineBaseline v4/B/J, 기존 금융 authority·일반 startup/read/write는 보존한다.
배포·서비스 재시작·APK 설치·segmented 활성화·R1 구현을 하지 않는다.

---

## 11. T01/T02/T03 targeted completion — 구현과 검증 기록

이 절은 위 21,663B의 원래 INCOMPLETE 기록 **뒤에 추가한 후속 기록**이다.
원본 `t66e4-implementation.md` 전체 SHA 보존과 재개 보고서 분리라는 소유자 결정을 유지한다.
P0 두 checkpoint를 rebase/amend하지 않았고 기존 E4 source/tests/측정을 새로 대체하지 않았다.
최종 판정과 실제 회귀 집계는 아래 §11.9에 기록한다. 독립 E4 감사 PASS를 선언하지 않는다.

### 11.1 시작 상태와 binding scope

시작 시 `HEAD = main = 671bb8668c16cba5f3729d9fb63fda4dbd1c67c5`,
`origin/main = actual remote main = ab59d6bbc39f27c36beb059f984ef527ac7b0bef`였다.
로컬 P0 구현 `35d7c53f1652310de75e492a98491efc3fd5cbba`와 audit evidence commit을 확인했다.
기존 E4 dirty worktree가 의도한 출발점이며 reset/restore/clean/stash를 사용하지 않았다.
`worktree-preservation.json`의 20파일을 대조한 뒤 필요한 targeted 확장만 수행했다.
P0 18파일의 현재 bytes와 구현 checkpoint bytes는 감사 SHA와 일치하고 monetary source
7파일은 수정하지 않았다. [보존 검사](benchmarks/t66e4-targeted/verify_preservation.py)는
이 correspondence와 원 보고서 prefix, 이전 측정 및 기존 시험 12파일의 원 bytes를 검사한다.

규범은 T6.6C §22/24/25.1–7/26/28/29/31/32/33/34 및 I25다.
§25.6–7의 installation/confirmed retirement는 E4 책임으로 구현하며, receipt를 AppState
권한으로 전용하지 않는다. §29의 frozen Target/control/hot/raw/index는 기존 legacy
logical lineage와 **관계로 결합**하고 identity가 같다고 해석하지 않는다.
§31/R1 Large Restore/MW/일반 사용자 recovery는 여전히 별도 CLOSED다.

```text
기존 AppState 최초 ticket + session/user/auth/mutation/mode
  → E2 authenticated acquisition → E3 complete verify/atomic accepted
  → E4 durable readback
      ├ segmented-native installed data reference + complete-store handle
      └ 명시 legacy 경계: original-control full v7/B → frozen binding/pins
  → 같은 ticket의 최종 설치 fence → eligible confirmed marker만 retirement
  → 같은 complete candidate의 모든 typed fields 설치
```

### 11.2 T01 — 최초 ticket과 실제 설치 authority

`app_state.dart`의 `installSegmentedLegacyForIsolatedUse`와
`refreshSegmentedForIsolatedUse`는 기존 AppState coordinator에서 **acquisition 전 딱 한 번**
ticket을 발급한다. Resume candidate/ticket/authorization boolean을 caller가 주입할 API가 없다.
원 `_requireRefreshAuthority`, lineage lock, `_lineageGeneration`, authentication generation,
current user/mode와 기존 E2 transport session getter를 사용한다. Session getter 후 AppState를
다시 검사하고 `_onlineWriteInFlight`/cancellation/accepted id·sequence도 확인한다.

모든 pre-commit/fault hook 뒤 실제 마지막 fence가 실행된다. E3 native guard→COMMIT seam은
그대로이며 E4의 native transaction도 `finalFence(); COMMIT` 사이 await/callback/notify가 없다.
현재 pending의 exact token/owner/status/retryIdentity와 ONLINE/no-J/no-reconciliation framing을
최종 fence에 포함한다. 현재 권한은 cache하지 않으며 persisted ticket/receipt로 복구하지 않는다.

두 경로 모두 **explicit isolated workspace에서만** 호출 가능하고 normal startup caller는 없다.
`refreshSegmentedForIsolatedUse`는 `SegmentedAuthority{target,complete_store_handle,defaults}`를
반환하고 typed financial fields를 같은 candidate에서 설치한다. flat B/legacy fingerprint를
만들지 않으므로 정상 incremental 경로에 O(N) legacy hash를 강제하지 않는다.
`installSegmentedLegacyForIsolatedUse`는 명시적인 full legacy 경계이며 기존 strict Bundle
admission을 통과한 완전한 Snapshot과 original-control identity만 원 v4 writer로 저장한다.

Retirement는 기존 durable `serverCommittedRebuildPending` marker에만 가능하다.
`workspace.dart::retireConfirmedSync`는 hook 뒤 exact marker를 다시 읽고 실제 AppState fence
직후 동기 unlink한다. Unknown marker/J는 금액·날짜·내용·sync_root로 acknowledge하지 않는다.
삭제와 모든 candidate UI field assignment 사이 await/hook/session getter가 없다.
Post-install 오류는 `E4InstallationCommittedException`이며 clean rollback으로 표현하지 않는다.

### 11.3 T02 — isolated v5, durable frozen ownership

`store.dart`의 `adapters:true`만 isolated segmented schema v5를 연다. Default E3 store는 v4,
production SQLite user_version 4/OfflineBaseline v4는 그대로다. v4 전체 schema/trigger/usage를
검증한 뒤 동일 native transaction에서 opt-in 확장한다. 손상된 old profile을 repair하지 않는다.
`store_frozen.dart`는 두 data table을 추가한다.

| metadata | 의미와 bound |
| --- | --- |
| `installed` | segmented-native complete installed reference와 previous; max 1 row |
| `frozen` | installed legacy B 하나 + prepared replacement 하나; unique state indexes/max 2 |

Frozen row는 generation UUID/manifest/receipt/root pins, namespace/principal/dataset/epoch를
결합하며 binding에 원 user/synced_at/resolved-ID, Snapshot ID/v7 fingerprint, 기존
`recoveryLineageFingerprint(B)`, exact logical v4 serialization checksum을 별도 필드로 보존한다.
`baseline_sha256`은 로컬 결합 검사용 C1 checksum이지 새 Snapshot fingerprint가 아니다.
실제 원 v4 JSON serialization/legacy hash 공식 및 E1 C1/hash는 바꾸지 않았다.

기존 E3 네 root pin+immutable descendant edge 보호를 그대로 재사용한다. `frozen` FK와
retained-generation trigger, E3 generation pruning exclusion으로 accepted/previous에서 사라진
G1도 유지한다. 객체별 pin set을 다시 쓰지 않고 frozen INSERT/state UPDATE만 추가한다.
Reader scope 종료/logout/새 accepted generation만으로 permanent frozen ownership을 해제하지 않는다.
준비 실패는 proven non-installed preparation만 해제할 수 있다. 설치된 frozen row의 독립 unpin
API는 없으며, 명시 ONLINE/no-active-J legacy replacement의 동일 transaction만 obsolete
binding을 제거하고 새 installed binding으로 바꾼다. 실제 journal lineage를 rewrite하지 않는다.

Native `installed` reference 역시 current/previous generations를 retention exclusion으로 보호한다.
이 포인터는 E3 accepted pointer를 대신하지 않고 **authorized E4 installation의 data reference**다.
Account 권한이나 Offline permit을 저장하지 않는다. Complete-store handle은 generation-bound
native read snapshot에서만 객체를 읽고 historical handle을 새 AppState 설치 권한으로 쓰지 않는다.

### 11.4 cross-store 순서와 crash recovery

SQL accepted/receipt/pins/frozen/installed는 같은 isolated SQLite DB지만 legacy B/marker/source는
별도 파일이다. 전체 cross-store transaction이나 hardware power-loss durability를 주장하지 않는다.

Legacy 경계는 `prepared frozen pin COMMIT → 작은 prepared source atomic replace → 원 v4의
guarded B rename/readback → full lineage correspondence → frozen installed COMMIT → installed
data reference COMMIT → 최종 원 ticket fence → confirmed retirement → UI` 순서다.
Native 경계는 `작은 prepared source → fenced installed COMMIT/readback → hash-on-read hot/control
→ 최종 원 ticket fence → confirmed retirement → UI`이며 B/J를 materialize하거나 변경하지 않는다.

Source discriminator는 bounded JSON이며 namespace/generation/sequence/frozen binding을 SQL과
대조한다. 이전 source는 한 단계만 보존한다. 이것은 data recovery hint이지 authorization token이나
대체 accepted pointer가 아니다. `recoverLegacyHandoff`는 prepared/committed 상태를 SQL+exact B
readback으로 구별한다. 확실히 publish되지 않은 preparation만 버리고, committed full B는 검증
후 data association만 마무리한다. Native COMMIT 전 중단이면 이전 source, COMMIT 후면 complete
new reference를 유지한다. 불명확한 lineage/누락 sidecar는 pins를 보존하고 fail closed한다.

Recovery는 ticket/UI/성공 알림/pending 삭제를 재개하지 않는다. 남은 confirmed marker는 기존
read-only rebuild 사유이며 POST 재실행 허가가 아니다. Unknown은 항상 남는다.
File rename 후 권한이 변할 수 있으므로 complete new B가 durable data로 남을 수 있지만 stale
요청은 marker retirement/UI 설치를 못 한다. 이것을 이전 파일로의 clean rollback이라고 하지 않는다.
같은 owning AppState/SQLite isolate와 기존 협력 lineage serialization 범위만 지원한다.

### 11.5 T03 — 검증 증거 재사용과 invalidation

기존 full path는 매번 전체 B JSON+logical lineage hash를 읽은 뒤 원 O(J) projection을 만들었다.
Cold Frozen-B 경로는 full E1/E3 graph verification, 실제 durable receipt와 recursive pin closure,
original-control full materialization, 원 v4 loader와 lineage/identity/bytes correspondence를 확인한다.
그 뒤 private immutable B와 다음 data-proof key를 같은 owning store/workspace 안에 유지한다.

`namespace/principal/dataset/epoch/generation/roots + frozen binding/receipt + store identity +
SQLite data_version + legacy file invalidation stamp`

Warm 경로도 **매번** exact schema/mandatory triggers/profile/receipt/root pin/frozen binding 검사와
hot/control hash-on-read를 수행한다. Full raw/index/recovery/legacy parse/hash/pin rewrite는 반복하지
않는다. J와 metadata는 기존 owner/parser/lineage validator로 새로 읽고 원 B+ordered J에만 기존
OfflineProjection을 적용한다. Current AppState installation authority/session result는 재사용하지 않는다.

Reopen/process restart/외부 SQLite COMMIT/관련 SQL 오류/불명확한 COMMIT/readback/receipt·roots·pin
변경/손상/대상 identity 변경은 full fallback 또는 fail closed다. 같은 connection의 정상 E3 accepted
변경은 immutable frozen graph를 바꾸지 않으므로 그것만으로 전체 frozen proof를 무효화하지 않는다.
Mandatory schema 검사와 read hash는 생략하지 않는다. File stat은 추가 invalidation signal이지
integrity proof가 아니다. Arbitrary OS open-DB unlink/replacement나 unread disk bitrot의 즉시 탐지는
지원 보장이 아니며 restart/full materialization 및 실제 객체 read에서 검증한다.

### 11.6 legacy/B/J 및 R1 경계

P0 monetary source와 local input `exactMoney()`는 그대로다. `\u001c+0001000.00\u001f` 등 원
authoritative 문자열, Unicode/null/ordering/projection을 기존 audited reader로 보존한다.
Client 금융 재계산·float 변환·sync_root/fingerprint 대입·partial envelope는 없다.
기존 85개 E4 시험을 삭제하지 않았고 source-isolation normalizer는 정확한 E4 extension만 제외한다.

Active old B/J/FINALIZING/reconciliation이 있으면 새 legacy replacement를 거부한다. MW/restore와
resolved-ID를 동반하는 finalizing handoff는 기존 approved workflow와 R1의 artifact/recovery 증거가
없는데 새로 실행하지 않는다. 기존 baseline의 resolved ID를 재생성하거나 J에 덮어쓰지 않는다.
Isolated pending view는 실제 기존 lineage에 결합된 B/J만 노출한다. 일반 사용자 segmented
Offline/recovery는 `requireSegmentedOfflineRecovery` 및 opt-in workspace의 `loadBaseline`에서
항상 CLOSED다. Developer flag/E3 acceptance/adapter 성공으로 열 수 없다. Default OfflineStore,
startup, online refresh, 금융 read/write와 production feature configuration은 변경하지 않았다.

### 11.7 실제 oracle·측정·한계

[targeted 증거](benchmarks/t66e4-targeted/README.md)의 재현 명령을 사용한다. Backend-produced
financial records/v7 restore validator, 별도 SQL closure/receipt 검사는 adapter success flag와
독립이다. 실제 AppState ticket invalidation/lineage lock wait/session-before-auth-generation race와
exact before/after marker/B/J bytes를 검사한다. 13 child SIGKILL 경계는 설치 pointer write/COMMIT
readback/legacy rename/frozen prep/confirmed deletion 전후를 포함한다. Process death는 power loss
proof가 아니며 production/Android 실기기 성능이나 flush 보장을 새로 주장하지 않는다.

Before/after는 4/400 history의 실제 backend graph와 같은 3개 J를 사용한다. Full oracle는 원
OfflineStore full reader/hash이고, optimized 결과의 B/J/value를 exact 비교한다. 독립 E3 SQL observer를
임시 source copy에만 연결해 반환 rows/BLOB/actual pin writes를 센다. 계측 overhead·JIT가 포함된
유한 synthetic latency이며 물리 VM/page I/O나 peak RSS 전체는 아니다. Cold/reopen/full fallback
O(N)과 healthy 반복 metadata+O(J)를 구별한다. 실제 최종 수치는 아래 §11.9와 JSON에 둔다.

독립 SQL 실행의 실제 저장 oracle는
[`frozen-sql-cost.json`](benchmarks/t66e4-targeted/frozen-sql-cost.json)이다.
142/1,728 required objects, 동일 H/3개 J인 두 규모에서 다음을 측정했다.

| 단계 | SQL (작은/큰) | returned rows | 객체 body B | raw/index nodes | frozen full recovery | root pin I/D/U |
| --- | --- | --- | --- | --- | --- | --- |
| frozen pin handoff | 84/84 | 531/531 | 0/0 | 0/0, 0/0 | 0/0 | 모두 0 |
| cold frozen | 975/10,497 | 1,386/12,494 | 211,406/2,494,984 | 33/39, 256/3,424 | 1/1 | 모두 0 |
| healthy 반복 | 64/64 | 288/288 | 9,451/9,451 | 0/0, 0/0 | 0/0 | 모두 0 |
| unrelated E3 acceptance 뒤 | 64/64 | 288/288 | 9,451/9,451 | 0/0, 0/0 | 0/0 | 모두 0 |
| 외부 COMMIT fallback | 977/10,499 | 1,388/12,496 | 211,406/2,494,984 | 33/39, 256/3,424 | 1/1 | 모두 0 |
| 새 handle recovery | 975/10,497 | 1,386/12,494 | 211,406/2,494,984 | 33/39, 256/3,424 | 1/1 | 모두 0 |

각 first frozen handoff의 추가 durable 쓰기는 frozen INSERT 1/state UPDATE 1이며 full pin
rewrite는 없다. Healthy 첫 반복은 16,904/38,845µs, 같은 반복은 16,327/37,236µs였고,
cold는 247,815/3,115,769µs였다. 이는 observer overhead가 포함된 storage-only 측정이다.
Full fallback 이후와 fresh recovery 이후의 warm도 각각 64 SQL/288 rows/9,451B로 복귀했다.
[`verify_cost.py`](benchmarks/t66e4-targeted/verify_cost.py)의 같은 assertion을 raw observer 결과와
영속 count artifact에 각각 실행하여 PASS했다. SQL query text를 함께 보존하며 실제 VM의
모든 scanned row/page I/O까지 측정했다고 주장하지 않는다.

### 11.8 개발 중 실패 이력

새 child fixture 상대 import 오류의 6 PASS/2 FAIL을 경로 교정으로 해결했다. 첫 full regression은
v5 schema catalog에서 `CREATE UNIQUE INDEX` 정의 누락으로 E4 store initialization을 거부했다.
닫힌 schema 검사를 완화하지 않고 정확한 parser 정의를 추가했다. 최초 실행의 실패 요약을
최종 green 결과와 별도로 보존한다. 원 historical monetary probe 3 PASS/2 FAIL은 assertion을
바꾸지 않았으며 현재 monetary regression 실패나 새 E4 correctness 성공으로 재분류하지 않는다.

실제 400-history fixture 비용 suite를 전체 회귀와 중복 실행한 600초 harness timeout도 발생했다.
그 실행은 PASS로 계수하지 않았고 timeout 뒤 ACQUISITION_BUSY 후속 오류도 숨기지 않는다.
제품 timeout/재시도/작업량 assertion을 유지하고 해당 테스트의 유한 harness ceiling만
1,200초로 확장했다. 최종 whole-suite 실행에서 비용을 함께 생성해 중복 fixture를 제거했다.

새 namespace negative 2건은 E2가 실제 context 오류를 `AcquisitionFailure`로 감싸는데
`SegmentedException`을 기대한 oracle 오류와 이전 인증 race의 만료 전 lease 간섭을 드러냈다.
제품을 수정하지 않고 exact `AcquisitionFailure(CACHE_CONTEXT_MISMATCH)`를 요구하며 각 독립
사례 전 synthetic clock으로 bounded lease를 만료시켰다. 해당 두 건의 즉시 재실행은 2 PASS였다.
임의 예외로 assertion을 넓히지 않았다. 실패가 확정된 중복 회귀 프로세스와 orphan child만
종료했고, 파일·미커밋 구현·실패 측정 이력은 보존한 뒤 전체 회귀를 다시 시작했다.

### 11.9 최종 실행 결과와 commit/push

**T6.6E4 COMPLETE — READY FOR INDEPENDENT IMPLEMENTATION AUDIT**

위 원본 INCOMPLETE 기록을 지우지 않고 T01/T02/T03 완료 결과를 추가한다. R1 gate가
닫혀 있다는 이유로 E4-owned handoff를 생략한 판정이 아니다. Ordinary ONLINE의 최초
ticket부터 durable accepted/installed readback, eligible confirmed retirement와 같은 complete
candidate 설치, 명시 legacy full B/frozen lineage 관계, durable pins, 반복 frozen 검증 재사용을
구현했다. Active legacy B/J/finalizing의 migration을 금지하는 §33과 R1 의존 recovery/artifact
실행은 우회하지 않는다. 기존 approved legacy finalization/replay 구현도 수정하지 않았다.

최종 source의 actual machine `done.success=true`와 testDone을 대조한 결과는
[`targeted regression-summary.json`](benchmarks/t66e4-targeted/regression-summary.json)에 있다.

| 실제 실행 | 최종 결과 |
| --- | --- |
| T01 original-ticket/installation/authority handoff | 35 PASS / 0 FAIL |
| T02 durable frozen pins/legacy association | 19 PASS / 0 FAIL |
| T03 provenance/invalidation/cost/equivalence | 11 PASS / 0 FAIL |
| 새 실제 handoff/pin/native COMMIT SIGKILL | 13 PASS / 0 FAIL |
| **이번 targeted 추가 합계** | **78 PASS / 0 FAIL** |
| 기존 E4 read/race/crash/isolation | 85 PASS / 0 FAIL, 삭제·완화 없음 |
| **E4 전체 추가 시험** | **163 PASS / 0 FAIL** |
| E4 handoff/authority suite | 기존 16 + T01 35 = 51 PASS / 0 FAIL |
| E4 실제 process crash | 기존 4 + 새 13 = 17 PASS / 0 FAIL |
| 기존 E1/E2/E3 SIGKILL | 26 PASS; E4 포함 총 43 PASS |
| **전체 Flutter** | **1,440 PASS / 0 FAIL / 2 SKIP** |
| 기존 E3 I25 publication | 30 PASS / 0 FAIL, 정상 종료 |
| E1 monetary/schema correction | 166/45 PASS; C1·hash·trigger 보존 |
| E2 connection cleanup | 13 PASS; E2-A01 보존 |
| P0 기존 Flutter | 183 PASS, 위 전체에 포함 |
| P0 독립 재실행 | Python 5 + Flutter 18 = 23 PASS |
| P0 independent differential | 24,836개, 모든 mismatch 0 |
| 원 monetary diagnostic | 3 PASS / 2 FAIL, 원 bytes/과거 expected 그대로 |
| Backend 전체 | 1,315 tests + 1,540 subtests PASS, 0 FAIL |
| Flutter analyze / debug build | PASS / PASS; synthetic URL, 설치하지 않음 |
| 변경 Dart 19파일 formatting | PASS, 변경 0; 무관 10개 기존 차이는 유지 |
| Ruff / compileall / frontend npm build | 모두 PASS |
| 독립 SQL cost oracle / git diff --check | PASS / PASS |

Full Flutter 실행은 `mobile/`에서 `flutter test --no-pub --machine`으로 전체 `test`를 지정했다.
최종 T03 계수의 output 경로만 dart-define으로 추가했다. Backend JUnit은 failures/errors 0인
2,855 testcase(1,315 tests+1,540 subtests), 1,615.594초다. 경고 1개는 기존 Starlette/httpx
TestClient deprecation이며 backend product 변경이나 E4 결함에 기인한다고 하지 않는다.
Debug build의 기존 Kotlin/SDK toolchain 안내도 실제 assembleDebug 실패와 구별했다.

최종 full reader 비교는
[`frozen-legacy-work-final.json`](benchmarks/t66e4-targeted/frozen-legacy-work-final.json)에 있다.
14,637/234,509B의 B에서 교정 전 full oracle 2회는 B 29,274/469,018B를 읽고
lineage 29,408/469,152B를 hash했다. 교정 후 3회는 full B parse/hash/recovery/raw-index 탐색이
모두 0이고 control/hot 6객체, 28,353B만 검증했다. B/J/result는 full oracle와 exact 비교했다.
작은 B에서는 추가 metadata 검사 overhead로 elapsed가 더 클 수 있으며 latency 개선만으로
PASS하지 않는다. 주 oracle는 불필요한 전체 N 작업 제거와 independent SQL/storage work다.

첫 SQL 측정을 보존하고
[`frozen-sql-with-open.json`](benchmarks/t66e4-targeted/frozen-sql-with-open.json)에 cold open을
별도 계측했다. Open은 28 SQL/107 returned rows, 4,136/26,022µs이며 usage aggregate의 실제
scan은 N에 의존하는 정당한 초기 작업이다. 반환 aggregate row 1을 scanned row 1이라고 하지
않는다. 이후 warm은 두 규모 모두 동일한 64 SQL/288 rows/9,451B, raw/index/full recovery/pin
쓰기는 0이었다. 두 영속 artifact에 독립 `verify_cost.py`를 실행하여 PASS했다.

한계는 명시한다. Native VM/page I/O·각 monetary parser 호출·hardware power loss·Android
실기기 peak memory를 별도 계측/입증한 것은 아니다. Cold full 검증/명시 full legacy export는
O(N)이며 original provisional J projection은 O(H+J) 작업을 유지한다. Complete-store handle은
데이터 접근 reference이지 현재 session/설치 permit이 아니다. 일반 사용자 Offline/recovery,
Large Restore/MW/artifacts/activation은 R1과 후속 binding gate가 필요하며 계속 CLOSED다.
확인된 미해결 E4 Critical/High/Medium blocker는 0이며 독립 E4 감사는 아직 PENDING이다.

최종 source/시험/observer 25파일의 SHA는
[`source-hashes.json`](benchmarks/t66e4-targeted/source-hashes.json)에 기록했다. P0 18파일의
현재/기존 checkpoint SHA와 원본 5파일, 원 보고서 prefix를 다시 검증했다. 실제 DB/금융 payload/
credential/원시 성공 로그/APK는 commit 대상이 아니다. E4 source/tests/fixture code/측정/보고서만
검토·stage하고 P0 두 commit을 변경하지 않은 정상 main 이력으로 완료 commit 및 push한다.
이 문서를 포함하는 구현 commit은 `git log -1 --format=%H -- mobile/lib/src/segmented/store_frozen.dart`
로 식별하며 push 뒤 HEAD/main/origin/main/actual remote main과 clean worktree의 실측값은 최종
인계 응답에서 확인한다. Commit 자체를 본문에 자기 참조 hash로 꾸미지 않는다.

문서 작성은 제공된 한국어 기술 보고서 형식을 따랐으며, 새로운 사실은 실제 실행 자료로만
채웠다. Production SQLite user_version 4/Snapshot v7/OfflineBaseline v4/frozen B/J/금융 authority와
normal startup/read/write는 그대로다. 배포·서비스 변경·APK 설치·segmented 활성화·R1 구현은 없다.
다음 작업은 독립 E4 구현 감사이며 T6.6F/R1을 이 작업에서 시작하지 않는다.

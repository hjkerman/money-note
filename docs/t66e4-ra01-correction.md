# T6.6E4-RA01 — native previous-source 전제 교정

## 1. 대상·판정 경계

시작 HEAD/main/origin/main/실제 remote main은 모두
`5ad7bc8003e3799da63a912b700432bc48aa6471`이었고 working tree는 clean이었다.
이 commit은 **FAIL인 E4-A01 독립 재감사**다. 이전 교정은
`37293dc8b26ca08f94e240408354a6ab6f3d98ac`, 최초 E4 구현은
`e386586194edbef1fc35f0ea1cf4145a2ae32685`다. 기존 P0 두 checkpoint와 원 감사·진단은
수정하지 않는다. 초기 inventory 및 SHA는
[baseline-inventory.json](benchmarks/t66e4-ra01/baseline-inventory.json)에 보존한다.

이 문서는 **E4-RA01 구현 교정 보고서**다. 독립 targeted re-audit PASS 또는 Phase A/B/R1 완료를
선언하지 않는다. 아래 최종 완료 guard는 통과했으며, 구현 교정 판정은
**T6.6E4-RA01 CORRECTED — READY FOR INDEPENDENT TARGETED RE-AUDIT**다.

## 2. 수정 전 독립 재현

제품 변경 전에 원 `t66e4-a01-reaudit/independent_test.dart`를 수정 없이 `^RA(16|17|18) `로
선택 실행했다. **0 PASS / 3 FAIL**, `done.success=false`, exit 1이었다.
실제 SQL·source·B/pending bytes·fresh child 관찰은
[reproducer-before.json](benchmarks/t66e4-ra01/reproducer-before.json)에 있다.

| 원 사례 | 입력/실제 결과 |
|---|---|
| RA16, 원 시험 560행 | installed SQL owner가 있는 legacy preparation의 `previous_source`만 null로 손상. recovery가 정상 반환하면서 source unlink; 재개방은 `FROZEN_BINDING_INVALID` |
| RA17, 원 시험 560행의 native 분기 | installed native/legacy owner가 있는 native preparation의 predecessor만 null. 같은 source unlink와 재개방 실패 |
| RA18, 원 시험 649행 | RA16형 preparation 뒤 실제 AppState native 설치가 성공 반환. `legacy_frozen=null`; B/pending/objects/pins는 남지만 Frozen-B 읽기 및 fresh child 읽기가 실패 |

RA18의 기존 F0는 `8aa7da30-8125-4f0b-9eea-d9882da3846a`였다. 기존 baseline bytes·pending
token/order와 독립 graph oracle 결과를 확인했으며 읽기 예외만으로 source 손실을 추정하지 않았다.

## 3. 정확한 원인·계약

기존 `_restoreRecoverySource`는 현재 preparation의 A01 source/SQL ownership을 확인했지만,
**복원 대상 predecessor가 현재 installed native/Frozen owner를 표현하는지** 검사하지 않았다.
따라서 null을 무조건 “이전 source 없음”으로 해석해 unlink했다. 이후
`prepareSegmentedSource`는 실제 installed/Frozen owner가 있어도 source 부재를 첫 설치로 받아들여
legacy association이 없는 native source를 만들었다. AppState의 ticket/session guard는 유효했기
때문에 이 잘못된 DATA 전환도 성공 반환했다. authorization 실패가 아닌 provenance 실패다.

T6.6C §24의 immutable generation/receipt/root pin, §25의 readback/recoverability 및 installation
authority, §26–27의 fail-closed recovery와 pending 보존, §29의 exact B/J lineage가 근거다.
`previous_source`는 기존 E4 구현의 **한 단계 data recovery hint**이지 protocol authorization
token도 새 lineage fingerprint도 아니다. null의 의미는 실제 durable owner 상태로 결정한다.

### 설치 상태 행렬

| 상태 | 허용 결과·필수 조건 |
|---|---|
| A. installed native/Frozen owner와 source 모두 없음 | 정상 첫 native 설치 허용. 기존 일반 v4 B 파일이 있어도 이를 임의 segmented lineage로 변환하지 않음 |
| B. 정상 legacy Frozen source 존재 | source namespace/Frozen UUID/binding/receipt/root pins 및 exact B lineage 검증 후 원 association 그대로 native source에 보존 |
| C. 미커밋 preparation의 predecessor 누락, durable owner 존재 | `SOURCE_PROVENANCE_REQUIRED`; unlink/installed switch/retirement/성공 금지 |
| D. 잘못된 predecessor UUID/context/binding/lineage/type | 명시 provenance/identity 오류; 이전 owner·evidence 보존 |
| E. 현재 source가 다른 operation으로 supersede됨 | 기존 A01 exact source + SQL fence에 의해 stale recovery no-op 또는 설치 conflict; 승자 보존 |
| F. principal/dataset/epoch/namespace 불일치 | 기존 namespace/manifest/binding 검증 및 source-owner 검증으로 거부 |
| G. 최종 hook/session getter가 source를 변경 | guard 뒤 실제 source를 다시 비교. 설치 COMMIT·retirement 금지; hook이 만든 최신 source를 되돌리지 않음 |
| H. interrupted handoff | 현재 SQL owner에 따라 exact predecessor 복원 또는 committed source 유지. 증거 부족은 RecoveryBlocked |
| I. 반복 설치 | original ticket을 매번 새 요청 시작에만 발급. 같은 installed UUID/sequence의 SQL pointer는 idempotent, source/B/pins 관계를 다시 검사 |
| J. 현재 native source가 이미 COMMIT됨, 옛 rollback hint만 null | 현재 installed + Frozen association이 유효하면 허용. obsolete hint를 항상 필수로 만들지 않음 |
| K. legacy B는 commit됐으나 native installed pointer finalization 전 | 기존 승인된 순서대로 complete legacy Frozen owner를 인정. legacy Frozen generation과 native pointer를 무조건 같다고 요구하지 않음 |

## 4. 변경된 경계·모든 source mutation 검토

제품 변경은 세 파일뿐이다. schema, B/J, Snapshot/v4, E1/E2/E3 verifier/publisher, P0 money source는
변경하지 않는다.

| 실제 경로 | 소유권/변경·durability 규칙 |
|---|---|
| `workspace.dart::_sourceRecord` | legacy/native의 알려진 반대 종류 identity alias를 거부. unrelated audit metadata는 기존대로 보존 |
| `_writeSource` | 기존 16KiB read budget을 write 전에 적용. 원자 replace 직전 synchronous guard 유지 |
| `prepareLegacySource` | 기존 frozen preparation/B ordering 유지. encoding budget 외 새 legacy 설치 의미 변경 없음 |
| `prepareSegmentedSource` | 기존 source와 실제 native/Frozen owner가 일치하는지 먼저 검사. 원 source를 한 단계 hint로 보존; 실제 prepared map 반환 |
| `_requireSourceOwner` | namespace, current installed UUID/sequence, 최대 두 frozen rows 중 unique installed Frozen UUID/checksum를 검사. 기존 `_frozen/_generation`이 manifest/receipt/4 root pins도 검증 |
| `_restoreRecoverySource` | 기존 A01 exact source/SQL fence 안에서 **복원 대상**의 durable owner 관계까지 검사한 뒤 rename/unlink. null은 실제 owner가 없는 경우만 허용 |
| legacy recovery discard 및 rollback compensation | 기존 conditional source/SQL ownership, B/mode/J 검사와 보상 조건 그대로. 실패가 최신 source에 대한 무조건 restoration이 되지 않음 |
| native recovery | current committed source 또는 actual previous installed identity를 먼저 분류. missing-required predecessor는 expensive full recovery 전에 거부. await 뒤 기존 A01 fence 유지 |
| abandoned preparation cleanup | 기존 현재 source/installed/prepared fences 유지. live installed Frozen pin을 cleanup으로 해제하지 않음 |
| `store_frozen.dart::commitInstalledGeneration` | optional **동기** `prepareSource`만 기존 BEGIN IMMEDIATE 내부에서 실행. Future callback 거부, 실제 accepted/installed 조건과 최종 fence 유지 |
| `app_state.dart::refreshSegmentedForIsolatedUse` | 원 ticket·session·pending authority 유지. source/B 검증→E2/E3→lineage lock→동기 source preparation/installed commit→current source readback→기존 승인 pending retire/UI 순서 |

초기 native prerequisite 검사는 `verifySegmentedInstallationBase`다. Frozen owner가 있으면 기존
`readFrozenBaseline`으로 exact B/v7/v4 lineage 검증을 재사용한다. healthy cache만 provenance로
재사용하며 auth 결과는 캐시하지 않는다. await 뒤 source·owner를 다시 확인한다.

`requireNativeInstallationSource`는 **이 요청이 실제 준비한 source map**과 durable source,
target UUID/sequence, 실제 previous installed relationship, Frozen binding/receipt/root pins,
store/data_version/B file stamp 기반 verified provenance를 검사한다. 이는 설치 허가 token이 아니다.
AppState의 기존 `installationAuthority`가 먼저 실행되고 source DATA 검사가 그 뒤 실행되므로
session getter의 동기 reentry가 마지막 source 검사 뒤에 남지 않는다.

## 5. 성공·실패·pending 경계

COMMIT 전 성공 조건은 원 authority/session + pending token/status + actual source/installed/
Frozen provenance다. 실제 source preparation을 writer transaction 내부로 이동하여 별도 SQLite
writer가 precondition 검사와 installed mutation 사이에 끼어들지 못한다. 준비·fault/quota 검사는
최종 guard보다 앞이며 final guard→COMMIT은 기존 synchronous 경계이고 await/notify가 없다.

COMMIT/readback 뒤와 UI/pending retirement 직전에도 source postcondition을 확인한다.
Confirmed marker는 기존 approved token/owner/status 조건으로만 삭제한다. 삭제 이후에는
**현재 authority/session과 source 관계**를 재검사하며 이미 정상 retire된 marker의 존재를 다시
요구하지 않는다. OutcomeUnknown은 항상 남는다. UI 금융 계산·financial POST·ack heuristic은 없다.

읽기·COMMIT 이후 error는 기존 `PublicationCommittedException` 또는
`E4InstallationCommittedException` 분류를 유지한다. post-COMMIT 실패를 clean rollback 또는
성공으로 표현하지 않는다. pending 미retire/기존 B/pins 보존이 우선이다.

## 6. Cross-store recovery와 A01 보존

accepted/installed/frozen/receipt/root pins는 같은 isolated SQLite다. source/B/marker는 별도 파일이다.
동일 writer transaction에서 source를 준비하더라도 파일 rename 자체가 SQL rollback에 포함되지는
않는다. COMMIT 전 crash/실패는 기존 data-only hint+actual previous SQL owner로 복구하고,
COMMIT 후면 exact installed identity/legacy association을 유지한다. 불명확한 hint는 evidence를
보존하고 막는다. distributed transaction·directory-fsync·hardware power loss 보장은 주장하지 않는다.

A01의 전체 source map 비교, UUID/sequence/checksum 포함 operation identity, SQL
prepared/installed ownership, hook/await 이후 검사, conditional restoration/보상은 그대로다.
같은 sync_root/논리적 source라도 다른 operation의 cleanup은 승자에 대한 권한이 없다.
지원 범위는 기존 owning AppState/isolate의 synchronous file mutation 및 SQLite 다중 연결이다.
임의 외부 process의 비협력 file rename에 대한 전역 CAS를 주장하지 않는다.

## 7. 원 손상 fixture와 정상 source 보존의 차이

원 RA16/RA18은 시험 자체가 legacy preparation의 유일한 predecessor link를 먼저 지운다.
그 상태는 제품 호출 **전부터** 기존 F0를 source로 찾을 수 없다. 교정은 이를 성공으로
위장하거나 최신 accepted/Frozen UUID를 추측해 연결하지 않는다. `SOURCE_PROVENANCE_REQUIRED`로
거부하고 손상 source·SQL owner·B/pending·objects/pins를 그대로 보존한다. 이 fixture의 Frozen-B
읽기가 자동 복구됐다고 주장하지 않는다.

별도 회귀는 정상 source에서 rename/COMMIT/storage/authority 실패가 나도 기존 F0를 fresh handle 및
fresh child process로 읽을 수 있음을 확인한다. 또한 native preparation은 실제 `legacy_frozen`
association을 유지하면서 predecessor만 손상될 수 있다. 이 경우 native recovery/설치는 명시 거부하되
그대로 보존된 association을 이용한 **isolated verified Frozen-B 읽기**는 fresh process에서 가능하다.
이 읽기는 damaged native recovery 성공, historical ticket 복원 또는 일반 Offline 활성화가 아니다.

## 8. 시험·독립 oracle

신규 `mobile/test/segmented_e4_ra01_test.dart`는 원 backend bridge와 실제 AppState를 사용한다.
직접 별도 SQLite 연결의 installed/accepted/frozen/roots/objects 및 source/B/pending exact bytes를
대조한다. foreign_key_check, 원 독립 Python graph/typed closure/F(raw)/Patricia/v7/v4 lineage oracle,
fresh handle/child를 사용한다. 새 success boolean만으로 correctness를 판정하지 않는다.

첫 설치, 일반 unsourced v4 B 보존, valid legacy→native, repeated native, committed obsolete hint,
legacy commit/native finalization gap, missing sidecar, legacy/native 두 종류의 predecessor
missing/UUID/principal/dataset/epoch/binding/lineage/cross-kind alias 손상, await reentry, 최종 session
getter reentry, 다른 SQL writer, actual COMMIT BUSY, Future callback, write budget, rename 실패,
post-COMMIT readback, idempotent recovery, missing root pin, competing original ticket, credential/mode,
confirmed retirement 성공/거부를 검사한다. 기존 독립 반례는 편집하지 않는다.

신규 실제 SIGKILL 경계는 7개다: source 변경 전, pointer write/COMMIT 전, COMMIT 후, readback,
missing-required predecessor 거부 후, 합법적 recovery의 source 변경 전/COMMIT 후.
독립 process가 종료 직후 SQL을 보고 fresh Flutter process를 열어 source/lineage/F0 read와 R1 CLOSED,
그 뒤 Python oracle로 objects/pins/B/pending을 검사한다. 기존 A01의 stale conflict/concurrent source 및
Phase A 6개 crash도 재실행한다. child 호출을 새로운 독립 test로 중복 합산하지 않는다.

## 9. 비용 oracle·현재 회귀 상태

교정 전 원 `t66e4-a01-reaudit/measure.py`를 제품 변경 전에 실행해 history 5/512 두 규모를 측정했다.
원 SQL observer는 폐기용 source copy에서 실제 SELECT/execute/반환 rows/BLOB bytes, pin writes와
full verifier/recovery 함수 진입을 센다. working tree 제품은 계측하지 않는다.

원 Frozen-B pending 두 입력의 정상 warm은 두 규모 모두 **85 SQL / 9,451 object bytes**였다.
기존 64 SQL은 store-only warm 경계다. metadata/J 파일 bytes·VM scanned rows·physical I/O·peak
Android memory를 이 수치로 바꾸지 않는다. cold/reopen의 full verification은 합법적인 fallback이다.

새 native 비용 시험은 기존 Frozen-B-only 시험의 zero raw/index/full recovery/full pin-write assertion을
그대로 실행한다. native refresh는 기존 §25 hot/raw 검사를 수행하므로 raw/index 조회를 모두 0으로
요구하지 않는다. 대신 **독립 backend hot IDs가 포함된 exact snapshot leaf set과 exact index root/facts head**
밖의 모든 snapshot/index 조회를 금지하고, leaf 중복 조회 및 실제 row 합계를 검사한다. H/D가 고정된
history 5/512에서 불변 history를 순회하지 않는지 실제 SQL/object counter로 대조한다. full verification,
full Frozen recovery 및 legacy full read의 warm 재발을 허용하지 않는다. Frozen-B-only read의 pin writes는
0이어야 한다. Native refresh의 기존 E3는 idempotent 결과에도 임시 candidate의 required root 관계를
만들고 해제할 수 있다. 이는 accepted/Frozen permanent pin 재작성과 다르다. 별도 연결의 before/after
root set과 실제 SQL owner/hash/행 수를 대조해 unchanged retained owner의 INSERT/UPDATE를 금지한다.
임시 candidate마다 backend target의 정확한 4 root refs만 생성·해제할 수 있으며 전체 graph pin 재작성은
허용하지 않는다. 제품의 E3 알고리즘이나 pin 정책은 이 교정에서 변경하지 않는다.
기존 `_PatriciaEdit.finish`가 root의 facts head count를 읽는 것은 node 자손을 순회하는 것과 구분한다.

최종 완료 수·비용·commit 검증은 아래 후속 절과 `benchmarks/t66e4-ra01/summary.json`에 기록한다.
중간 harness 오류, 중단한 전체 회귀, 잘못된 zero-raw 비용 가정은 완료 증거와 분리한다.

### 개발 중 검출·정정한 문제

- 새 fixture의 Map `contains`는 deep equality가 아니었다. 실제 hash/owner key로 같은 row를 찾아
  모든 column을 deep equality로 대조하게 바로잡았다. foreign namespace fixture는 기존 C1 primitive로
  target hash를 다시 구성하여 의도한 source/context 검증 경계에 도달하게 했다.
- E2는 한 isolate의 simultaneous acquisition을 의도적으로 거부한다. 새 ticket 경쟁 시험은
  acquisition lock 내부가 아니라 원 recovery metadata await에서 A를 멈추고 B를 성공시킨다.
  변경 없는 idempotent 설치에는 pointer-write hook이 없으므로 mode 경합 시험은 실제 변경 target을 쓴다.
- 처음 추가한 비용 oracle의 raw/index=0은 native §25 hot/raw 검사에 맞지 않았다. assertion 제거 시도는
  자동 검토에서 거부됐다. 관련 source를 확인한 뒤 독립 backend hot leaf/root/facts-head exact-set과
  중복/row-count 검증으로 대체해 전체 history 조회를 허용하지 않는 oracle를 만들었다.
- 중간 전체 회귀는 정상 confirmed marker를 retire한 뒤 같은 marker가 아직 있어야 한다는 새 guard 때문에
  기존 T01 native confirmed 사례가 오류를 보고하는 regression을 발견했다. pre-retirement token guard는
  그대로 두고 post-retirement는 current authority/session/source만 검사하도록 고쳤다. 원 기존 반례를
  수정 없이 다시 실행해 PASS를 확인했고, 새 confirmed 성공/누락 predecessor 거부 사례를 추가했다.
  중간 전체 회귀는 보존·중단했고 최종 소스 전체 회귀를 별도로 다시 실행한다.
- 기존 원 비용 시험의 손상 주입 SQL은 `snapshot-leaf ORDER BY hash LIMIT 1`이며 Frozen closure로
  한정되지 않는다. 한 중간 실행에서 hash error 기대값과 실제 null이 달랐다. 당시 selected hash는
  기록되지 않아 그 실행의 개별 객체 귀속을 확정했다고 주장하지 않는다. 별도 변경 없는 assertion의
  관찰 재실행은 두 규모 PASS/selected hash 모두 Frozen member였다. 추가 진단은 **같은 선택 SQL**이
  4회 synthetic 변경 뒤 Frozen 밖 hash `010c96db8a3879f8f708a96c2a2468a95428a5e0520741b1b8da82079ab3b4e9`를
  고르는 경우를 독립 SQL closure로 확인했다. 이 foreign 객체만 canon/hash-invalid로 만들고 fresh store를
  열어도 exact Frozen B/lineage/source가 유지돼 읽힌다. §24는 읽지 않는 임의 다른 graph의 즉시 bitrot 탐지를
  약속하지 않는다. 따라서 원 선택 fixture의 한계를 기록하며, 이를 해결하려고 모든 graph를 매 읽기마다
  검증하거나 원 assertion을 약화하지 않는다. 이 귀속 진단을 새 RA01 correctness case 수에 더하지 않는다.

## 10. 보존·제한·다음 gate

검사한 기존 173개 비변경 파일의 SHA, P0 current/checkpoint 18파일, 원 diagnostic 5개 SHA를 재검사한다.
역사적 diagnostic의 3 PASS/2 obsolete assertion FAIL, 원 P0 baseline-enumeration fixture 결함과
approved compatible replay를 구분한다. 원 감사의 FAIL 보고서·assertions는 고치지 않는다.

Snapshot v7, OfflineBaseline v4, frozen input admission/ordered J/ack contracts, exact authoritative monetary
문자열 `"\u001c+0001000.00\u001f"`, C1/hash, E1 schema triggers, E2 HTTP cleanup, E3 I25와 final
guard→COMMIT는 변경하지 않는다. production SQLite user_version 4와 normal startup/read/write를 유지한다.
새 기능 activation/R1/Phase B/deploy/APK install은 하지 않는다. R1 gate는 CLOSED다.

독립 targeted re-audit 전에는 Phase B/R1/배포를 시작할 수 없다. 유일한 다음 승인 gate는 E4-RA01
교정에 대한 독립 targeted re-audit다.

## 11. 최종 실제 검증 결과

모든 수는 실제 machine event/JUnit/exit에서 집계했다. 최종 `--require-complete` guard가
완료 수·`done.success=true`·실제 exit·비용 비교·보존을 확인했다.
[summary.json](benchmarks/t66e4-ra01/summary.json),
[cases.json](benchmarks/t66e4-ra01/cases.json),
[session-exits.json](benchmarks/t66e4-ra01/session-exits.json)을 따른다.

| 검증 | 실제 결과 |
|---|---|
| 원 3개 RA01, 제품 변경 전 | 0 PASS / 3 FAIL, 재현 성공 |
| 최종 원 재감사 | Dart 18 + 원 비용 2 = 20 PASS / 0 FAIL |
| 원 Phase A regression replay | Dart 36 + 원 비용 2 + 실제 종료 6 + P0 compatible replay 1 = 45 PASS |
| 이전 A01 correction | 기존 unit 21 + concurrent 1 + 실제 종료 6 = 28 PASS |
| 신규 RA01 correction | unit 42 + native 비용 2 + 실제 종료 7 = **51 PASS / 0 FAIL** |
| E4 기존 authority/race | 51 PASS; 신규 교정 경합은 위 51개에 별도 포함 |
| E4 실제 process-crash regression | 기존 mobile 17 + 원 Phase A 6 + A01 6 + 신규 7 = **36 PASS / 0 FAIL** |
| 전체 Flutter | **1,503 PASS / 0 FAIL / 2 SKIP**, 실제 exit 0 |
| E4-P0 구현 / 독립 integration | 183 / 18 PASS |
| P0 독립 differential | **24,836 cases, 모든 mismatch 0** |
| 원 P0 Python / compatible replay | 4 PASS / 1 기존 fixture FAIL; 동일 monetary assertions의 기존 compatible replay 1 PASS |
| 역사적 원 diagnostic | 3 PASS / 2 obsolete assertion FAIL; 원문/SHA 그대로 |
| E2-A01 별도 TLS/socket cleanup | 9 PASS |
| Backend full | **1,315 tests / 1,540 subtests PASS**, failure/error 0 |
| Flutter analyze / debug build | PASS / PASS; APK 설치·배포 없음 |
| 변경 Dart 7파일 formatting | PASS; unrelated formatting 유지 |
| Ruff / compileall / diff check | PASS / PASS / PASS |
| frontend tests / build | 21 PASS / PASS |
| script safety | 27 PASS |
| 원 자료·P0 보존 | baseline inventory 173 비변경 파일, P0 current/checkpoint 18파일, 원 diagnostic 5파일 SHA 일치 |

원 Phase A 사례 재생은 구현 regression이지 독립 Phase A PASS 판정이 아니다. fixture 귀속 진단과
child 호출·같은 case의 반복 실행을 신규 51개에 더하지 않는다. 현재 계약 오류를 역사적 실패로
숨기지 않았으며 obsolete diagnostic·baseline-enumeration fixture의 사유는 원 감사 및 §9에 명시했다.

### 실제 작업량·latency

추가 archive rows는 5/512, 해당 required graph는 **146/2,177 objects**다. 전후 원 Frozen-B warm
12개 조합의 SQL/object bytes/raw-index/full verifier/recovery/lineage/pin 계수는 모두 같았다.
[cost-comparison.json](benchmarks/t66e4-ra01/cost-comparison.json)에 before/after를 별도 보존한다.

| 작업 | 작은 graph | 큰 graph | 검증·pin 작업 |
|---|---:|---:|---|
| Frozen-B store-only warm | 64 SQL / 9,451 bytes | 동일 | full/raw/index/recovery/pin writes 0 |
| Frozen-B pending 2입력 warm | 85 SQL / 9,451 bytes | 동일 | full/raw/index/recovery/pin writes 0 |
| unrelated acceptance 뒤 Frozen-B warm | 85 SQL / 9,451 bytes | 동일 | full verification 및 pin writes 0 |
| native 유효 previous-source handoff | 1,010 SQL / 47,133 bytes | 1,010 SQL / 193,092 bytes | raw leaf 4 / index root+head 2, full verifier 0 |
| native repeated handoff | 1,013 SQL / 37,682 bytes | 1,013 SQL / 183,641 bytes | raw leaf 4 / index 2, full verifier/recovery/legacy full read 0 |
| required predecessor 누락 native 거부 | 44 SQL / object bytes 0 | 동일 | raw/index/full/recovery/pin writes 0 |
| 정상 first native cold | 6,085 SQL / 399,987 bytes | 81,241 SQL / 5,952,662 bytes | 필요한 full verification 1; initial root pins 4 |
| fresh-store recovery | 4,040 SQL / 882,402 bytes | 52,841 SQL / 12,888,567 bytes | cold installed/Frozen 증명 full 4; pin writes 0 |

Native repeated의 SQL 반환 rows도 두 규모 모두 **5,948**이었다. 실제 raw leaf body의 rows는
**9→259**로 늘었다. 큰 graph의 touched leaf packing은 한 leaf의 최대 256행과 다른 leaf의 3행이다.
T6.6C D2a의 일반 leaf 상한 **256행 / 262,144 canonical bytes**에 따른 필수 H leaf byte 비용이며,
전체 N이나 Patricia 자손을 순회한 결과가 아니다. exact server-derived H leaf set과 root/facts-head 밖
조회 금지 assertion이 통과했다. native bytes가 완전히 상수라고 주장하지 않는다. oversized singleton과
무상한 row/string byte 입력은 프로토콜처럼 별도 비용이며 이 합성 결과에 숨기지 않는다.

Native 반복의 실제 root INSERT/DELETE는 두 규모 모두 **4/4**였으며 모두 **한 임시 candidate owner**의
정확한 backend root refs였다. 영구 accepted/Frozen owner에 대한 rewrite는 0이다. 단순 최종 set 동등성이
아니라 실제 SQL owner/hash/계수와 before/after rows를 함께 확인했다.
[native-handoff-cost.json](benchmarks/t66e4-ra01/native-handoff-cost.json)에 보존한다.

전체 native repeated latency는 작은/큰 graph **1.073s / 1.060s**, 누락 거부 **16.6ms / 10.3ms**였다.
Cold first native는 **43.9s / 624.8s**, fresh-store recovery는 **1.15s / 14.96s**였다. SQL observer·JIT·동시
회귀 부하를 포함한 synthetic 측정이며 production throughput/Android latency 보장이 아니다.
`transaction_us` 원자료는 observer의 COMMIT/ROLLBACK 이벤트 값이며 read rollback timer도 포함한다.
이를 native final critical-section의 독립 duration으로 해석하지 않는다. RSS는 current RSS이지 peak가 아니다.
Guard→COMMIT no-await 및 짧은 metadata-only 경계는 실제 source ordering·reentry/BUSY/권한 경합 시험으로 검증했다.

### 최종 제한·독립 재감사

Critical/High/Medium의 미해결 **교정 범위 blocker는 0**이다. source가 이미 손상된 입력의 자동 복원,
arbitrary 외부 file writer의 OS-wide CAS, unread unrelated object의 즉시 bitrot 탐지, hardware power loss,
Android 실기기 및 R1 Large Restore/MW를 입증하거나 구현했다고 주장하지 않는다. 원 3개 반례의 사전 손상과
정상 source에서 실패한 installation의 보존을 §7처럼 구분한다. 일반 segmented Offline/R1 gate는 CLOSED다.

## 12. Commit/push 검증 방식

완료 guard와 전체 diff/원 SHA를 검토한 뒤, 제품 3파일과 이 교정의 tests/fixtures/측정/문서만 stage한다.
Commit message는 `fix(flutter): reject E4 native install with invalid previous source`다.
자기 자신의 hash를 문서에 넣기 위해 history를 다시 쓰지 않는다. 이 보고서를 처음 추가한 교정 commit은
다음 Git 명령으로 정확히 식별할 수 있다.

```bash
git log --diff-filter=A --format=%H -- docs/t66e4-ra01-correction.md
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --short
```

정상 main history의 push 이후 위 네 refs의 일치와 clean tree를 별도 확인한다. 실제 최종 commit hash와
push 결과는 최종 응답 및 Git 원격 ref가 증거다. 원 P0/A01/audit commits를 amend/rebase/force-push하지 않는다.
운영 배포·APK 설치·segmented activation은 수행하지 않는다. 다음 단계는 이 commit의 독립 RA01 targeted
re-audit이며, 그 전 Phase B/R1/배포는 금지다.

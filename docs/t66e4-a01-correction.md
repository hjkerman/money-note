# T6.6E4-A01 — 오래된 복구의 Frozen-B source 덮어쓰기 교정

## 1. 범위와 기준점

이 작업은 E4-A01 **MEDIUM** 하나의 구현 교정이다. 독립 재감사나 Phase A PASS 선언이 아니다.
원 구현은 `e386586194edbef1fc35f0ea1cf4145a2ae32685`, 시작한 독립 감사 commit은
`7fc5420353477e16224c6ccce6fadd50e7ff55e0`다. 시작 당시 HEAD/main/origin/main/실제 remote main이
모두 같았고 worktree는 깨끗했다. P0 두 checkpoint와 원 감사·진단은 수정하지 않는다.

제품 변경은 다음 두 파일뿐이다.

- `mobile/lib/src/segmented/workspace.dart`: source 소유권 대조, 조건부 복원/삭제, preparation 복구.
- `mobile/lib/src/segmented/store_frozen.dart`: 기존 writer transaction으로 installed/prepared 소유권을
  재검사하며 동기 source 복원 callback을 실행하는 좁은 API.

AppState/coordinator/ticket/session guard, E1/E2/E3 publisher, schema, 금액 parser, legacy B/J,
Snapshot v7 및 OfflineBaseline v4 형식은 바꾸지 않는다. R1과 Phase B는 시작하지 않는다.
실제 수정 위치는 `workspace.dart:250`(source 대조), `:289`/`:317`(중단된 preparation),
`:359`(superseded 복구), `:477`(rollback 순서), `store_frozen.dart:122`(installed SQL fence)다.

## 2. 원 실패의 수정 전 재현

원 [`stale_recovery_test.dart`](benchmarks/t66e4-audit/stale_recovery_test.dart)를 한 글자도 바꾸지 않고
제품 변경 전에 실행했다. **0 PASS / 1 FAIL**, `done.success=false`였다.
`loadMetadata()`의 실제 await를 Completer로 지연하며 sleep으로 race를 추정하지 않는다.

같은 AppState/coordinator에서 최초 설치, 이전 취소 요청 A, 최신 요청 B가 순서대로 시작된다.
각 요청의 ticket은 해당 entry의 기존 `begin()`에서 발급되며 새 ticket으로 A를 승인하지 않는다.
원 재현에서 A는 `before_legacy_rename`의 실제 `SyncCancellation.cancel()`로
`ACQUISITION_CANCELLED`를 받는다. A의 lineage section이 해제된 뒤 `finally`의 data-only recovery가
대기하는 동안 B가 정상 설치된다. Durable source의 소유자는 ticket이 아니라 frozen UUID와 binding,
generation/sequence 및 이전 source 관계다. persisted receipt를 현재 권한으로 읽지 않는다.

| 수정 전 실제 관찰 | 값 |
| --- | --- |
| 최초 F0 | `be39bf81-1918-4897-b159-7827c477e65e` |
| B가 정상 설치한 F2 | `c1f2ec1d-b3ac-44ff-83fc-096a373ee957` |
| B 성공 직후 source | F2 |
| A 복구 재개 후 source | 이미 삭제된 F0 |
| 별도 SQL installed | `d11f18b8-3466-4de2-9a03-61f6b3f9b163`, sequence 2 |
| 별도 SQL frozen | F2, installed |
| B/pending bytes | B 성공 직후와 동일 |
| 객체·pin·C1/hash/typed closure/F(raw)/Patricia | 원 독립 Python oracle 통과 |
| Frozen-B 읽기 / 새 store handle 복구 | 둘 다 `FROZEN_BINDING_INVALID` |

원 감사의 다른 재현 UUID와 이번 실행 UUID를 섞지 않는다.
[`reproducer.json`](benchmarks/t66e4-a01/reproducer.json)에 이번 수정 전후 source와 실제 SQL,
독립 graph·receipt·root 결과를 축약 보존한다. 원 감사의 FAIL 기록은 그대로 남아 있다.

## 3. 원인과 전체 mutation 검토

원 `app_state.dart:666`의 실패 `finally` 복구는 lineage lock 밖에서 실행된다. 이것만으로 설치 권한을
만드는 것은 아니지만, 원 `workspace.dart:331`은 await 전에 `unchanged`를 계산한 뒤 metadata/J await
후 파일을 먼저 무조건 복원했다. 그 뒤 SQL preparation 검사가 실패해도 파일 변경은 취소되지 않았다.
SQL은 F2, 파일은 F0인 불일치가 남았다.

| 경로 | 기존 문제/소유자 | 교정 후 durable mutation 조건 |
| --- | --- | --- |
| `prepareLegacySource` | 현재 AppState 원 ticket이 승인한 새 frozen preparation | 기존 final installation guard를 hook 뒤 rename 직전에 유지; 변경 없음 |
| `prepareSegmentedSource` | 현재 원 ticket이 승인한 accepted/installed handoff | 기존 final guard 유지; 변경 없음 |
| legacy 미게시 preparation 복구 | await 전에 읽은 source/B로 무조건 restore/unlink | 같은 source 전체 identity + 같은 prepared UUID/checksum + 현재 이전 B + ONLINE/J 없음; writer transaction의 final fence에서만 파일 변경 |
| native 미COMMIT source 복구 | await 전 source와 설치 pointer를 재사용 | 현재 installed ID/sequence/namespace를 BEGIN IMMEDIATE 안에서 비교하고 hook 뒤 source를 재검사 |
| B rename 후 prepared→installed 마무리 | SQL 소유권은 검사하지만 source의 async 변경을 별도 배제하지 않음 | 같은 source와 exact B correspondence를 마지막 SQL fence에서 재검사; 최신 source면 no-op/rollback |
| source가 없는 초기 orphan 정리 | await 뒤 생긴 source/설치를 배제하지 않음 | source 부재, B 파일 동일성, current installed 부재와 prepared SQL owner를 final fence에서 재검사 |
| source 복원 뒤 COMMIT 실패 | 파일과 SQL은 별도 durable 경계 | SQL에 원 preparation이 여전히 있을 때만, 복원된 source와 installed pointer가 그대로인 transaction에서 원 preparation source 재연결 |
| 복원 뒤 process death | old source + rollback된 orphan preparation이 남을 수 있음 | 검증된 현재 installed B/source 아래의 최대 한 prepared orphan만 조건부 정리; 새/모호한 B는 unpin 금지 |
| 이전 source가 native인 복원 | native 설치 pointer는 유효하지만 legacy preparation이 남을 수 있음 | 기존 Frozen B가 있으면 그 lineage를 검증하고 정리; 아직 B가 없으면 원 preparation이 B를 게시하지 않았음을 증명한 뒤 native pointer/source/B 부재를 final fence에서 재검사 |
| `discardUnacceptedGeneration` 등 E3 정리 | frozen/installed 제외 조건 | 그대로 유지; source를 쓰지 않음 |
| logout/read-scope dispose/읽기 fallback | source 설치/교체 권한이 아님 | 새 source mutation이나 pin release를 추가하지 않음 |

source 생성·교체·복원·삭제는 `workspace.dart`의 `_writeSource`, `_restoreRecoverySource` 및 명시 prepare
경로에 한정된다. 원 legacy 파일 writer는 B/J 형식을 유지하고 sidecar를 설치 권한으로 사용하지 않는다.

## 4. 수정된 소유권 불변식

복구가 읽어 둔 source 전체를 현재 source와 다시 대조한다. namespace/discriminator, frozen UUID와
binding 또는 native generation/sequence, 이전 설치 및 이전 source 관계까지 포함한다.
같은 sync_root·같은 binding·같은 generation만으로 다른 작업을 같은 owner로 취급하지 않는다.
새 UUID를 가진 같은 논리 source 사례도 별도로 검사한다.

`_requireRecoverySource`와 파일 rename/unlink 사이에는 await·isolate message·UI notification이 없다.
`before_source_rename` hook **뒤**에 마지막 source/B 검사를 수행한다. 동기 재진입이 새 source를 쓰면
이 마지막 대조가 실패하여 예전 파일을 덮어쓰지 않는다. source 불일치는 private
`_SupersededSourceRecovery`로 해당 data-only 복구만 no-op 처리한다. 손상 metadata, storage failure,
잘못된 namespace나 lineage를 일반 성공으로 바꾸지는 않는다.

legacy discard는 기존 `discardFrozenPreparation`의 BEGIN IMMEDIATE 안에서 원 prepared SQL owner를
확인한 뒤, 기존 final fence에서 source 복원을 수행하고 COMMIT한다. row가 사라졌거나 installed가
됐으면 source를 먼저 바꿀 수 없다. Native 복원 및 실패 보상은 `restoreUncommittedSource`에서 현재
installed ID/sequence/namespace와 필요한 prepared owner를 확인한다. SQL writer lock은 다른 connection의
설치 COMMIT과 직렬화된다. async callback은 거부한다.

모든 file writer는 기존 **같은 owning AppState/isolate** 범위다. 동기 source 대조→rename은 그 범위의
async interleaving을 배제하고, SQL writer lock은 해당 SQL ownership의 competing COMMIT을 배제한다.
임의의 다른 process/isolate가 협력 protocol 없이 source 파일을 직접 교체하는 OS 차원의 CAS를 새로
제공한다고 주장하지 않는다. read-then-await-then-unconditional-write는 더 이상 없다.

## 5. 실패·cross-store recovery

파일과 SQLite 전체를 하나의 transaction이라고 주장하지 않는다. source 이전 값은 이미 보호된
설치 generation을 가리키고, old installed pin은 SQL preparation 삭제와 별개로 계속 유지된다.

- 마지막 검사 전 실패: SQL rollback, source/B/pending 그대로.
- 파일 복원 후 COMMIT 실패: primary 오류를 유지한다. 원 prepared row가 살아 있고 source가 방금 복원한
  값일 때만 SQL ownership fence 아래 원 preparation source를 다시 연결한다. 최신 source에는 보상 write 금지다.
- COMMIT 후 hook/readback 오류: row가 없으므로 완료된 정리를 rollback으로 가장하지 않는다.
- source 복원 후 COMMIT 전 process death: SQL은 prepared row를 rollback할 수 있다. 재시작은 검증된
  old installed B/source 아래의 abandoned preparation만 정리한다. 객체 GC나 금융 삭제는 추가하지 않는다.
- source/B/SQL 관계가 모호하거나 저장 오류가 계속되는 경우: pins와 pending을 보존하고 fail closed한다.

abandoned 정리는 최대 installed 1 + prepared 1이라는 기존 v5 한도 안에서만 수행한다. source와
현재 B/installed owner가 그대로이고 ONLINE/J 없음이 확인되어야 한다. Active J나 다른 lineage에
대한 자동 rebase/release가 아니다. 정상 E3 accepted 변경은 frozen pin을 해제하지 않는다.
Native 이전 source에 대해서도 동일하게 적용한다. `_recoverNativePreparations`는 prepared row가 없는
정상 native 경로에서는 bounded metadata만 읽고 legacy hash/materialization을 하지 않는다.
처음 legacy B를 준비한 native-only 상태에서 실제 B가 후보와 같으면 release하지 않고 명시 복구를
요구한다. B가 없다는 사실을 legacy authority나 빈 금융 baseline으로 승격하지 않는다.

## 6. AppState·legacy·금융 경계

AppState 제품 파일은 수정하지 않았다. 원 RefreshTicket, coordinator, user/auth/mutation/mode/session
검사와 lineage section, pending retirement 및 UI 설치 순서는 그대로다. 이전 복구의 storage 정리 권한은
새 설치 권한이 아니며 새로운 ticket·boolean permit·authentication system·durable authority token을 만들지 않는다.

`retireConfirmedSync`와 unknown marker 보존은 변경하지 않는다. A의 실패/취소 복구는 pending을
acknowledge/retire/replay하지 않는다. 동시 B 성공 이후에도 unknown bytes와 순서가 그대로다.
새 SQL schema나 lineage format, v7 fingerprint 공식, OfflineBaseline v4 의미, P0 authoritative money
grammar와 frozen input `exactMoney()`를 바꾸지 않는다. `sync_root != state_fingerprint`는 그대로다.
일반 startup/read/write, production configuration 및 CLOSED R1 gate도 변경하지 않는다.

## 7. 테스트와 독립 oracle

원 FA17은 변경하지 않고 수정 전 FAIL과 수정 후 PASS를 비교한다. 추가
`mobile/test/segmented_e4_a01_test.dart`의 21개는 metadata/J 지연과 legacy/native 최신 설치,
같은 binding의 다른 UUID, concurrent/idempotent recovery, logout 뒤 합법적 data-only finalize,
rename hook 재진입, commit 전후 오류, 실제 SQLite COMMIT BUSY, 잘못된 source context,
rename 오류, legacy/native/native-only abandoned preparation 복구, stale installed sequence 및
async callback 거부를 검사한다.
별도 `concurrent_recovery_test.dart` 1개는 원 FA17의 원 ticket 설치와 모든 durable oracle를 유지하고,
B 설치 후 A의 복구를 재개하면서 B 자신의 복구도 동시에 시작한다. A의 취소 오류는 유지되고 B의
source/B/installed/frozen/pins/pending은 그대로이며 reopen 읽기도 성공했다.
새 교정 시험의 중복 없는 총수는 unit 21 + 별도 동시 복구 1 + SIGKILL 6 = **28**이다.

실제 파일 bytes와 별도 sqlite3 connection의 accepted/installed/frozen/root pins/object bytes checksum을
비교한다. 오류 반환만으로 PASS하지 않는다. 새 store handle/별도 Python process는 원 독립 C1/hash/
complete closure/F(raw)/Patricia/v7 restore/legacy lineage oracle를 실행한다.

최종 새 실제 SIGKILL 6개는 다음 경계다. 테스트 timeout이나 기존 assertion을 완화하지 않는다.

1. B 정상 COMMIT 후, 대기 중인 A 복구를 재개하기 전.
2. B 정상 COMMIT 후, A의 superseded recovery no-op 완료 뒤.
3. 실제 source 복원 후 SQL COMMIT 전: 별도 SQLite SHARED reader로 native COMMIT가 대기하는 동안
   supervisor가 바뀐 실제 source를 관찰하고 tester PID를 SIGKILL한다.
4. source 복원과 prepared 삭제 COMMIT 뒤, API return 전.
5. 이전 source가 native이고 기존 Frozen B가 있는 source 복원 후 SQL COMMIT 전.
6. 이전 source가 native-only이고 아직 legacy B가 없는 source 복원 후 SQL COMMIT 전.

각각 fresh process로 reopen/recover/read하고 direct SQLite/graph/legacy oracle 및 pending exact bytes를
검사한다. 3번은 복구 전 실제 source가 복원된 상태이고 immediate SQL에는 prepared row가 남아 있음을
함께 확인하여 완료된 오류 보상 뒤의 kill과 구별한다. 첫 네 경계의 성공 자료와 강화 자료는 보존하고,
native 두 경계를 포함한 최종 증거는 [`crashes-final.json`](benchmarks/t66e4-a01/crashes-final.json)에 둔다.
이것은 process-death 검증이지 hardware/Android power-loss 증명이 아니다.

## 8. 반복 비용

원 독립 [`measure.py`](benchmarks/t66e4-audit/measure.py)를 수정하지 않고 최종 제품의 폐기용 copy에
SQL observer를 연결했다. 제품 counter만을 oracle로 쓰지 않는다. 5/512 history의
146/2,177 required objects에서 15 phases씩 검사했다.

| 반복 경로 | 이전 독립 감사 | 이번 교정 후 | 양쪽 불필요 full 검증/recovery/pin I/D/U |
| --- | --- | --- | --- |
| storage-only warm | 64 SQL / 288 returned rows / 9,451B | 동일 | 모두 0 |
| B+2 J pending view | 85 SQL / 423 returned rows / 9,451B | 동일 | 모두 0 |
| 무관한 E3 acceptance 뒤 | 85 SQL / 423 returned rows / 9,451B | 동일 | 모두 0 |
| fallback/reopen 뒤 warm | 85 SQL / 423 returned rows / 9,451B | 동일 | 모두 0 |

원 감사와 위 12개 size/phase 조합의 SQL·객체·full 함수·pin 작업량을 정확히 대조했다.
첫 교정 측정의 storage-only elapsed는 20,716/18,136µs, pending 첫 warm은 26,992/23,595µs였다.
Native 이전 source 보완 전 측정을 지우지 않고 최종 source의 재측정을 별도
[`cost-final.json`](benchmarks/t66e4-a01/cost-final.json)에 둔다.
최종 storage-only elapsed는 작은/큰 graph에서 23,809/38,565µs,
pending 첫 warm은 43,105/67,747µs였다. 앞선 시간과 다른 동시 synthetic workload에서 측정했으므로
latency 개선을 주장하지 않는다. 같은 SQL·반환 행·객체 bytes·검증/pin 작업량이 비용 oracle다.
각 phase 종료의 RSS snapshot은 작은 graph 202,567,680–238,854,144B, 큰 graph
258,199,552–270,422,016B였다. 시간 연속 peak 측정이나 객체 cache 단독 메모리로 해석하지 않는다.
JIT/observer/동시 synthetic workload의 유한 측정이며 production latency 보장이 아니다.
returned rows를 VM scanned rows라고 부르지 않는다. body bytes는 metadata/J 파일·physical page I/O를
포함하지 않는다. cold/reopen/corrupt/lineage fallback의 필요한 O(N)은 정상 warm에 섞지 않는다.
복구 시 16KiB 한도의 source metadata 대조와 최대 두 frozen rows 검사, 실제 rollback의 한 writer
transaction을 추가했으며 정상 read path의 full graph/금액 재파싱/pin rewrite는 추가하지 않았다.

## 9. 검증 결과

최종 source를 고정한 실행의 결과다. 전체 Flutter의 마지막 `done.success=true`와 process exit 0을
확인했다. 개별 재실행을 더해 전체 suite 수를 부풀리지 않는다.

| 검사 | 관찰 결과 |
| --- | --- |
| 원 FA17 수정 전 | 0 PASS / 1 FAIL; source가 F2에서 삭제된 F0로 되돌아감 |
| 원 Phase A 사례 수정 후 재실행 | 45 PASS / 0 FAIL: Dart 36 + SQL cost 2 + SIGKILL 6 + P0 replay 1 |
| 새 교정 사례 | 28 PASS / 0 FAIL: unit 21 + 동시 복구 1 + 새 SIGKILL 6 |
| 최종 전체 Flutter | **1,461 PASS / 0 FAIL / 2 SKIP**, exit 0 |
| P0 monetary | 기존 Flutter 183; 독립 Flutter 18 PASS; 24,836 differential cases mismatch 0; 호환 replay 1 PASS |
| E2-A01 독립 TCP FD/pool | 5 PASS / 0 FAIL |
| Backend full | 1,315 tests + 1,540 subtests PASS / 0 FAIL |
| Flutter analyze / debug build | PASS / PASS; 합성 `https://a01.invalid`, 설치·배포 없음 |
| 변경 Dart 5파일 formatting | PASS; 무관한 파일 reformat 없음 |
| Ruff / compileall / diff check | PASS / PASS / PASS |
| Frontend test / build | 21 PASS / PASS |
| 배포 script 안전성 시험 | 27 PASS / 0 FAIL; 배포 실행 아님 |
| P0 checkpoint/current 18파일·원 진단 5파일 | SHA 일치 |
| 원 E4 inventory | 허용한 제품 2파일 외 69/71파일 그대로 |

원 monetary 역사적 진단은 **3 PASS / 2 FAIL** 그대로다. 두 FAIL은 교정 전 서버 유효 금액을
거절해야 한다는 당시 기대다. 원 P0 Python suite는 **4 PASS / 1 fixture FAIL** 그대로이며,
후속 신규 `adapters.dart`를 존재하지 않는 `ab59...` 경로에서 `git show`하는 실행기 오류다.
원 Phase A에서도 동일하게 기록된 문제다. 원 fixture/assertion은 수정하지 않았다. 감사의 기존
호환 replay는 금액/bytes/hash assertion을 유지한 채 **1 PASS**다. 이를 모두 PASS로 표기하지 않는다.

E1/E2/E3 SIGKILL 26과 기존 E4 SIGKILL 17은 전체 Flutter 내부 사례다. 원 Phase A 6과 새 교정 6을
포함한 E4 process-crash grouping은 29개다. 기존 E4 authority grouping은 handoff 35 + adapter 16 =
51개이며 별도 교정 28개와 전체 Flutter 수는 서로 중복을 포함하는 분류다.
[`summary.json`](benchmarks/t66e4-a01/summary.json)은 원 machine/JUnit counts, 각 실행의 snapshot,
개발 중 harness 실패, 정적 검사 exit, P0 corpus와 최종 source SHA를 보존한다. source 보완 전에 시작한
첫 전체 실행은 별도 `flutter_pre_native_full`로 남기고 최종 source 전체 회귀의 대체 증거로 쓰지 않는다.

## 10. 증거 보존·한계·인계

원 audit report/finding/test/FAIL artifact는 변경하지 않는다. P0 현재/원 checkpoint 18파일,
원 diagnostic 5파일 SHA 및 resumption 보고서 21,663B 원 prefix가 일치했다.
새 artifact는 [`benchmarks/t66e4-a01/`](benchmarks/t66e4-a01/README.md)에만 추가한다.

첫 신규 unit compile의 import/반환 타입 누락, 새 crash child의 누락 import, 첫 독립 suite 호출의
존재하지 않는 P0 파일 경로는 harness 오류로 보존한다. assertion/timeout을 완화하지 않고 정확한 기존
타입/import/경로를 수정·재실행했다. 원 monetary 진단의 obsolete rejection 2 FAIL과 원 P0 baseline
fixture의 후속 파일 enumeration 실패는 원문 그대로 별도 실행하며 제품 회귀로 바꿔 부르지 않는다.

임의 OS 파일 조작, unread bitrot 즉시 탐지, hardware power loss는 새 보장이 아니다. Schema/receipt/
hash-on-read/full fallback과 기존 pin 보호를 유지한다. 미해결 저장 불확실성을 일반 성공으로 감추지 않는다.
R1 gate는 CLOSED, general-user segmented Offline/recovery는 활성화하지 않는다. 배포·production 접근·
APK 설치·Phase B·R1 실행은 없다. 구현 교정 완료 뒤 독립 targeted re-audit가 필요하다.

구현 교정 completion gate를 통과했으며 새 Critical/High/Medium 구현 blocker는 0이다.
원 독립 MEDIUM finding의 독립 closure를 선언하지 않는다. **독립 E4-A01 targeted re-audit 준비 완료**이며
Phase B는 그 재감사가 PASS할 때까지 차단한다.

completion assertion은 PASS이며 commit 직전 P0·진단 SHA와 원 감사 불변을 다시 확인했다.
commit 직전 실제 remote main도 `7fc5420353477e16224c6ccce6fadd50e7ff55e0`였다.
교정 commit message는 `fix(flutter): fence stale E4 frozen-source recovery`다. 이 문서를 처음 포함한
commit은 `git log -1 --format=%H -- docs/t66e4-a01-correction.md`로 식별한다. 자기 참조 hash를 만들거나
원 감사 commit을 amend하지 않는다. 정상 `origin main` push 후 HEAD/main/origin/main/실제 remote main과
clean worktree의 실제 검증 hash는 최종 응답에 기록한다. commit·push는 배포나 Phase B 허가가 아니다.

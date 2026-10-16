# T6.6E4-RA01 독립 targeted 재감사

## 01. 대상과 판정 경계

대상 교정은 `af9525e20e6df1dd7dfc152d3db79c1eb07925d2`다. 비교 기준은 원 실패 재감사
`5ad7bc8003e3799da63a912b700432bc48aa6471`이다. 감사일은 2026-10-16이며 제품 구현은 수정하지 않았다.

**최종 판정: PASS — E4-RA01 INDEPENDENT TARGETED RE-AUDIT COMPLETE.** 이 문서는 E4-RA01과 직접 영향 경로의
재감사다. 새로운 전체 E4 설계 감사나 T6.6F Phase B를 수행했다고 주장하지 않는다.

**IMPLEMENTATION-SIDE CLAIM:** 교정 51개, 이전 재감사 20개, Flutter 1,503개 및 backend 1,315개
통과, previous-source 결함 해소와 A01 보존이다. 이를 독립 결과로 전용하지 않는다.

**INDEPENDENTLY VERIFIED FACT:** 원 RA16–18 assertion은 변경 없이 3 PASS다. 현재 제품 3파일의
실제 call graph, 별도 SQLite 연결, 새 synthetic 상태 전환, 실제 SIGKILL, 임시 source copy의 SQL observer를
사용했다. 전체 실행 수와 완료 exit는 [summary.json](benchmarks/t66e4-ra01-reaudit/summary.json),
case별 결과는 [cases.json](benchmarks/t66e4-ra01-reaudit/cases.json)에 둔다.

**UNVERIFIED ASSUMPTION:** 실제 Android 전원 손실, 임의 외부 프로세스의 비협력 source rename,
읽지 않은 모든 다른 generation의 즉각적인 bitrot 탐지는 입증하지 않는다. 지원 범위는 기존 owning
AppState/isolate의 협력 파일 변경과 실제 SQLite 다중 연결이다.

## 02. Repository·remote와 정확한 source

변경 전 AGENTS 및 project/domain/known-issues, architecture 신뢰 경계, offline/security/runbook과 지정된
규범·원 감사·교정 보고서·benchmark 방법을 읽었다. 최초 작업 트리는 clean이며 실제 remote를 별도 조회했다.

```text
HEAD = main = origin/main = 실제 remote refs/heads/main
af9525e20e6df1dd7dfc152d3db79c1eb07925d2
Git tree: 13ca80b840e584a7c61dc3a37feec7c3d31d92e0
```

`git rev-parse`, `git ls-remote`, `git status`, `git diff --stat/--name-status` 및 각 파일의 SHA-256/Git blob을
대조했다. [inventory.json](benchmarks/t66e4-ra01-reaudit/inventory.json)에 교정 29파일과 원 역사적 자료
44파일의 SHA를 기록했다. 초기 clean 상태를 감사 파일 추가 후의 dirty 상태와 혼동하지 않는다.
원 감사·반례·제품 hash의 최종 일치는 별도 완료 guard로 확인한다.

## 03. 전체 교정 diff inventory

`5ad7bc8..af9525e`는 **29 files, +18,015/-17**이다. dependency/config/backend/schema 변경은 없다.

| 분류 | 파일·검토 내용 |
|---|---|
| 제품 3 | `app_state.dart`: 설치 전 provenance 및 최종 source guard; `store_frozen.dart`: 같은 writer transaction의 동기 source 준비; `workspace.dart`: predecessor/current owner·typed alias·16KiB write budget 검증 |
| unit 1 | `mobile/test/segmented_e4_ra01_test.dart`: 42개 실제 AppState/SQL/byte·오류·경합 assertion |
| Dart fixture 3 | RA01 `cost_test.dart`, `crash_child_test.dart`, `corruption_selector_test.dart` |
| Python 5 | RA01 `collect.py`, `measure.py`, `observe_original_cost.py`, `test_crash.py`, `validate.py`: 임시 copy·actual PID·oracle·집계 규칙 |
| JSON 15 | before/after reproduction, 원/신규 비용, 실제 crash, corpus, source hash, inventory, 완료 summary/cases/exits |
| 문서 2 | RA01 correction 보고서와 benchmark README |

세 제품 파일의 전체 diff와 새 executable fixture·assertion을 읽고 JSON 전체를 파싱했다. encoding budget과
cross-kind alias 거부는 같은 source provenance/readback 경계를 보호한다. unrelated runtime refactor는 없다.
원 RA16–18 시험과 과거 FAIL 보고서는 이 교정에서도 byte-identical이다.

## 04. 원 E4-A01과 E4-RA01

[원 Phase A FAIL](t66e4-independent-audit.md)은 canceled A의 늦은 recovery가 정상 B의 source를 덮는
E4-A01 MEDIUM을 기록했다. [이전 재감사 FAIL](t66e4-a01-independent-reaudit.md)은 원 stale-race closure를
확인했지만 별도의 E4-RA01 MEDIUM을 발견했다. 원 두 보고서의 FAIL 판정은 그대로 보존한다.

RA01은 이전 source가 없는 진짜 첫 설치와, installed/Frozen owner가 있는데 predecessor만 손실된 상태를
구별하지 못했다. 기존 `_restoreRecoverySource`는 현재 preparation 소유권만 검사한 뒤 null이면 unlink했다.
그 다음 native 준비가 source 부재를 첫 설치로 받아들여 F0 association이 없는 성공을 반환할 수 있었다.
graph/B/pending/pins 자체 손실과 source-to-lineage 단절을 구분한다. 이 반례는 controlled metadata corruption이며
remote exploit이나 서버 금융 계산 오류가 아니다.

## 05. 원 세 RA01 반례의 변경 없는 결과

원 [independent_test.dart](benchmarks/t66e4-a01-reaudit/independent_test.dart)의 RA16/17은 560행의 두 분기,
RA18은 649행이다. `--name 'RA1[678] '`로 원 파일을 그대로 선택 실행했다.
[original-three.json](benchmarks/t66e4-ra01-reaudit/original-three.json)은 별도 SQL/source/B/pending/fresh-child 관찰이다.

| 사례 | 원 실패 | 현재 관찰·독립 oracle | 결과 |
|---|---|---|---|
| RA16 | legacy preparation의 predecessor null → source unlink·prepared DELETE COMMIT | `SOURCE_PROVENANCE_REQUIRED`; source와 실제 installed/frozen/root rows, B/pending 보존; reopen도 명시 차단 | PASS |
| RA17 | native preparation의 predecessor null → 같은 source 유실 | 동일한 명시 거부와 durable evidence 보존 | PASS |
| RA18 | 실제 AppState native 설치 성공, `legacy_frozen=null`, F0 읽기 실패 | 설치 성공 없음; `SOURCE_PROVENANCE_REQUIRED`; source/SQL/B/pending 보존; 독립 C1/graph/receipt/pin oracle 통과 | PASS |

원 RA16/18의 입력은 시험이 **호출 전에** 유일한 F0 predecessor link를 지운 legacy preparation이다.
따라서 현재도 그 손상 source에서 Frozen-B 읽기는 `FROZEN_BINDING_INVALID`이고 RA18의 fresh child는 exit 1이다.
이는 자동 수리 성공이 아니다. 원 assertion의 안전한 명시 거부/evidence 보존 분기가 통과했다.
누락된 source를 추측해 만들거나 expected result를 변경하지 않았다. 정상 source에서 설치 실패 후 fresh-process
읽기가 유지되는 사실은 별도의 NR07/NR10/NR11, correction 사례 및 SIGKILL 시험으로 확인한다.
native preparation에 F0 association이 남은 경우의 isolated verified read는 NR13/NP context 사례로 구분한다.

## 06. 실제 root cause와 교정 위치

[workspace.dart:379](../mobile/lib/src/segmented/workspace.dart#L379)의 `_restoreRecoverySource`는 현재 source 일치와 함께 **복원 대상**을
`_requireSourceOwner`로 검사한다. `:221`은 실제 installed UUID/sequence, namespace, unique installed Frozen
UUID/binding과 `_frozen/_generation`의 receipt/root 관계를 대조한다. null은 실제 installed/Frozen owner가
없는 경우만 허용한다. 현재 source가 이미 COMMIT된 native source이면 `:532`는 obsolete rollback hint의 부재를
무조건 오류로 만들지 않는다.

`workspace.dart:255`의 `verifySegmentedInstallationBase`는 유효한 Frozen owner에 대해 기존 exact B/v7/v4
lineage 검증을 재사용하고 await 후 source/owner를 다시 검사한다. `:187`의 실제 source 준비도 같은 검사를
writer lock 안에서 반복한다. `:269`는 이 요청이 실제로 준비한 source map과 target/previous relationship,
Frozen provenance, store/data_version/B stamp를 최종 검사한다. 단순 caller null check에 의존하지 않는다.

## 07. 독립적으로 도출한 previous_source 전환 행렬

근거는 §22/24/25/26/29다. `previous_source`는 한 단계 **DATA 복원 정보**이며 protocol auth token이 아니다.
내용이 같은 Snapshot 또는 sync_root를 operation/legacy lineage 대용으로 쓰지 않는다.

| 초기 durable 상태 | 필수 증거·허용 결과 | 실패·복구 후 의무 |
|---|---|---|
| source와 native/Frozen owner 없음 | null 허용; 현재 original ticket으로 정상 최초 native 설치 | valid target/receipt/installed/source; Frozen B를 임의 생성하지 않음 |
| 일반 unsourced v4 B만 있음 | segmented owner 부재가 입증되면 최초 native 허용 | 기존 B bytes 보존; 임의 segmented lineage 결합 금지 |
| installed Frozen F0/정상 legacy source | exact namespace/F0/binding/B lineage를 predecessor로 보존 | 실패하면 F0/pins/B/pending 유지 |
| current native G1 및 F0 association | UUID/sequence와 F0가 현재 SQL owner와 일치해야 함 | 다른 operation 또는 stale owner의 복원 금지 |
| 실제 owner가 있는데 required predecessor 없음 | 명시 거부, evidence 보존 | null을 첫 설치 증거로 해석하거나 unlink 금지 |
| 잘못된 kind/UUID/sequence/context/binding/lineage | 명시 거부 또는 superseded recovery no-op | 최신 valid owner 변경 금지 |
| current native source 이미 COMMIT, obsolete hint 없음 | current owner/F0 관계가 유효하면 허용 | historical hint만을 이유로 정상 source 폐기 금지 |
| legacy B/Frozen commit 후 native finalization 전 | legacy F와 native installed G가 일시적으로 다를 수 있음 | 검증된 legacy lineage 유지; 두 ID의 무조건 동일성 요구 금지 |
| interrupted preparation, 실제 previous owner 있음 | same writer fence에서 exact predecessor 복원 | B/owner 조건이 불충분하면 blocked |
| 첫 미게시 preparation, 실제 previous owner 없음 | 기존 B 미변경/ONLINE/J없음의 증거 아래 해제 가능 | dangling source나 fabricated source 금지 |
| 반복·동시 설치 | 매 요청 시작의 original ticket, current durable source/accepted/installed 조건 | idempotent data와 현재 authorization을 구분 |

## 08. Genuine initial 설치

NR01은 owner 없는 최초 native 설치의 source rename 뒤 SQL rollback, 정상 recovery/unlink, 새 원 ticket의
retry와 reopen을 검사한다. NR12는 첫 legacy preparation을 정리한 뒤 최초 native 설치를 실제로 수행한다.
새 SIGKILL의 first-before/first-after는 **별도 process**에서 prior-null 또는 complete-new native 결과와 hot/control
읽기를 확인한다. Frozen owner가 없는데 가짜 Frozen-B source를 만들지는 않는다. 기존 correction의 initial
unsourced v4 B 보존도 full 회귀에 포함한다.

## 09. Missing/invalid/stale provenance

원 세 반례, 기존 correction의 16개 typed/context predecessor 변형, 독립 NR03–04/NR08–09/NR13–14,
NP principal/dataset/epoch/lineage/receipt/pin 사례를 대조한다. type 오류를 null과 합치지 않으며, 같은 Frozen
binding을 갖더라도 native operation UUID/sequence가 다르면 거부한다. source를 검증한 뒤 API session getter나
fault hook에서 바꾸는 경우도 final source 비교에서 차단한다. 오류 반환만으로 안전하다고 판단하지 않고 실제
installed/frozen/roots/source/B/pending을 비교한다.

## 10. 설치 성공의 durable postconditions

[app_state.dart:760](../mobile/lib/src/app_state.dart#L760)의 native 경로는 실제 준비 map을 request-local로 보관한다.
COMMIT 전에 current authority/session/pending와 source→installed/F0/receipt/pins/cached exact B를 검사한다.
COMMIT/readback 뒤, retirement/UI 직전과 반환 직전에도 관계를 확인한다. success boolean 또는 process-local
verified flag만으로 source association을 만들지 않는다. NR02의 여러 legacy/native 왕복 후에도 최신 F의
별도 v7 fingerprint/legacy lineage와 root owner가 유지되며 fresh child가 읽는다.

## 11. 실패 보존과 rollback 분류

pre-COMMIT 오류는 SQL을 rollback하고 valid B/pending/Frozen 의무를 보존한다. source file rename은 SQL
rollback에 포함되지 않으므로 준비된 한 단계 predecessor와 actual previous SQL owner로 data recovery한다.
post-COMMIT readback 오류는 `PublicationCommittedException`으로 분류하며 성공 rollback으로 표현하지 않는다.
기존 correction의 actual COMMIT BUSY, rename 실패, post-COMMIT readback과 NR01/NR11, actual crash 결과를
함께 확인했다. 손상 fixture의 test-owned exact repair는 제품이 수행한 자동 복구로 계수하지 않는다.

## 12. E4-A01 원 stale-race 보존

원 [stale_recovery_test.dart](benchmarks/t66e4-audit/stale_recovery_test.dart)는 assertion 변경 없이 PASS다.
같은 실제 AppState에서 canceled A의 metadata await 동안 B가 정상 설치하고, A가 뒤늦게 재개돼도 B의 source와
SQL/Frozen lineage를 바꾸지 않는다. 이전 독립 RA01–15와 A01 concurrent/SIGKILL도 재실행했다. 새 NR05는
base 검증 후 대기하는 original request를 최신 request가 무효화하며, NR07은 같은 Frozen ID의 다른 source
metadata owner를 rename 전에 대조한다. 현재 source equality를 current AppState authorization으로 쓰지 않는다.

## 13. Source/SQL 검사→변경 원자성

native 호출 순서는 `AppState:786` → `commitInstalledGeneration` → `_transaction`이다.

```text
BEGIN IMMEDIATE → mandatory schema → current accepted/installed
→ synchronous prepareSource → actual source/owner 검증·atomic file rename
→ installed UPSERT/readback → quota·fault hooks
→ original authority/session/pending → exact prepared source + provenance
→ synchronous COMMIT → synchronous installed readback
```

[store_frozen.dart:44](../mobile/lib/src/segmented/store_frozen.dart#L44)의 UPSERT에 별도 conditional WHERE를 넣은 형태는 아니지만, current 상태 비교와 mutation이
같은 connection의 write transaction 안에 있다. callback은 Future를 거부한다. 다른 SQLite writer/DDL이 중간에
COMMIT할 수 없으며 실제 두 번째 store connection의 callback 진입 전 STORE_BUSY 거부를 원 시험이 확인한다.
recovery는 [restoreUncommittedSource:130](../mobile/lib/src/segmented/store_frozen.dart#L130)의 current installed namespace/UUID/sequence와 optional prepared
owner 검사 아래 source를 바꾼다. legacy prepared DELETE와 final source 복원도 같은 writer transaction이다.
이는 SQLite의 [단일 writer와 BEGIN IMMEDIATE 계약](https://www.sqlite.org/lang_transaction.html)에 부합한다.

파일은 별도 자원이다. SQL lock을 파일 전역 CAS로 표현하지 않는다. 파일 소유권은 complete source map을 await와
hook 뒤 다시 비교하고 owning isolate에서 guard→rename/unlink를 동기 실행한다. 임의 비협력 OS writer는 보장
범위 밖이다. 원 실제 COMMIT BUSY/조건부 보상·새 crash 결과는 source와 SQL이 서로 다른 durable 자원임을
전제로 검사한다. [rollback-journal locking](https://www.sqlite.org/lockingv3.html)의 reader/COMMIT BUSY도 구분했다.

## 14. Final guard와 reentrancy

[store.dart:272](../mobile/lib/src/segmented/store.dart#L272)은 fault hook을 finalFence보다 먼저 실행하며 guard 뒤 곧바로 `_db.execute('COMMIT')`다.
사용 중인 sqlite3 3.7.0의 `database.dart:287`은 native `sqlite3_exec`를 동기 호출한다. 제품 connection은 private이며
commitFilter/UDF/collation/동기 application callback 등록이 없다. row triggers는 schema가 검증된 SQL이고 DML은
final guard 이전이다. credential getter 뒤에는 AppState generation을 재검사하고 그 뒤 DATA source guard를 수행한다.
최종 source guard 이후 await/isolate roundtrip/notify/hook은 없다. 원 ticket을 E2 전에 받아 E3/E4에 그대로 유지한다.

## 15. Same-source/different-operation·concurrent 경합

논리적 sync_root나 Frozen binding이 같아도 exact source operation UUID/sequence/전체 map과 actual SQL owner를
대조한다. 원 독립 RA02/RA10/RA11/RA13/RA14, correction same-source/different-operation, NR07/NR08/NR09를
사용했다. Completer barrier 또는 실제 SQLite lock으로 interleaving을 통제한다. sleep만으로 stale ownership을
추측하지 않는다. 서로 다른 requests와 overlapping recoveries의 최종 승자, legitimate rollback/idempotence를
별도 검사한다. 동시 session 전체를 재설계하거나 독립 auth system을 추가하지 않았다.

## 16. Cross-store 일관성

accepted/installed/Frozen receipt/root pins는 같은 isolated SQLite에 있고 source/B/J/pending은 별도 파일이다.
source 준비를 SQL writer lock 안으로 옮겨도 파일과 DB가 하나의 transaction이 되지는 않는다. native 실패/종료는
actual installed owner와 exact predecessor로 복구하고, legacy B commit 뒤에는 정확한 B checksum/lineage 아래
Frozen finalization만 허용한다. ambiguous evidence는 보존/blocked다. stale A가 B의 source/pin을 해제하지 못하며
data recovery는 과거 ticket 복원·UI 설치·pending retirement를 수행하지 않는다.

## 17. Fresh-process 읽기

NR02/NR07/NR10/NR11은 기존 verified child를 별도 process로 실행했다. 세 새 SIGKILL과 원/교정 process suites는
supervisor가 실제 child를 종료한 뒤 새 Flutter process를 시작한다. Python oracle는 새 read-only SQLite connection에서
C1/SHA/typed edge/complete closure/F(raw)/Patricia/11 table/v7 fingerprint/v4 lineage를 검사한다. helper child
호출을 별도 신규 사례로 중복 합산하지 않는다. 최초 native-only에는 Frozen-B 없음이 정상이며 installed hot/control을
검사한다. invalid native predecessor의 retained F0 read와 damaged native recovery 성공은 구분한다.

## 18. Frozen pins·immutable objects

영구 Frozen pin, accepted/current/previous pin, 임시 read scope를 구분한다. retained root rows와 immutable objects를
실제 owner/hash로 대조하고 정상 source 실패·stale recovery·restart에서 보존을 확인한다. NR02 최초 새 harness는
여러 정상 게시 뒤 모든 옛 owner까지 영구 보존하도록 과도하게 요구해 17 PASS/1 FAIL이었다. source의 pruning 규칙을
읽고 새로운 before/after accepted/installed/Frozen/roots 기록을 추가하여 실제 latest Frozen owner의 **모든 root rows**
보존을 검사하도록 바로잡았다. 제품·원 시험은 변경하지 않았다. 최초 로그 digest/실패는 summary에 남긴다.

## 19. Pending B/J·legacy identity

unknown pending은 GET/materialization/native install로 retire하지 않는다. confirmed는 기존 token/owner/status와 current
원 ticket·session 및 durable source postconditions 아래서만 retire한다. post-retirement guard는 정상 삭제된 marker의
존재를 다시 요구하지 않고 current authority/source를 확인한다. 원 RA07의 actual ordered J, 새 unknown marker bytes,
P0/B/J/offline/full 회귀를 사용했다. 자동 rebase·implicit acknowledgment·pending 순서/identity 변경은 관찰되지 않았다.
sync_root와 Snapshot v7 fingerprint는 서로 다른 identity다. 같은 Snapshot의 synced_at만 바꾼 NP-lineage도 기존 frozen
lineage로 받아들이지 않는다.

## 20. 실제 process-crash

기존 E4 grouping은 full Flutter의 17개, 원 Phase A 6개, A01 6개, RA01 7개로 구성한다. 모두 실제 tester PID 종료 여부와
fresh process oracle를 읽고 재실행한다. 신규 3개는 [test_crash.py](benchmarks/t66e4-ra01-reaudit/test_crash.py)에서
별도로 SIGKILL한다. 최초 pointer write/COMMIT 전에는 null prior, COMMIT 뒤에는 complete new native가 남는다.
legacy→native→새 legacy의 Frozen pointer/COMMIT 전 종료는 old SQL + 새 committed B/source를 새 process가 올바른
Frozen owner로 finalize한다. partial source를 valid authority로 인정하지 않는다. `crashes.json`에 즉시 SQL과 fresh-read
결과를 함께 둔다. 예외-only fault 시험을 SIGKILL로 세지 않으며 hardware power-loss 보장을 주장하지 않는다.

## 21. T01/T02/T03 회귀

T01은 기존 AppState coordinator/원 ticket, user/auth/request/mutation/mode/session, lineage queue, pending status를
유지한다. T02는 durable Frozen owner와 exact legacy binding/receipt/root retention을 유지한다. T03은 store identity,
Frozen ID/checksum/receipt, data_version 및 B stamp로 data provenance만 재사용한다. current authorization은 매번 검사한다.
외부 COMMIT·schema/receipt/pin/body/lineage 손상과 reopen에서 full fallback 또는 명시 거부를 확인하며, 정상 cache가
uncertain recovery를 무조건 승인하는 boolean으로 바뀌지 않는다.

## 22. E4-P0·금융 의미

P0 source/checkpoint 및 원 진단 5파일 SHA 보존을 확인했다. monetary source는 교정 diff 밖이다.
원 24,836 differential에서 authoritative 4,903 accepted / 19,933 rejected, frozen-input 3,866 accepted이며
authoritative/E1/frozen/raw/C1-hash/non-setting mismatch는 모두 0이다. `"\u001c+0001000.00\u001f"`는 backend/E1/
authoritative legacy read에서 exact codepoints로 보존되고 원 local exactMoney/B/J input contract는 그대로다.
new floating-point conversion이나 backend 금융 projection 복제는 없다.

## 23. E1/E2/E3와 I25

E1 C1/hash/raw/trigger 검증, E2 auth/typed transfer/cache/response cleanup, E3 index/tree/F(raw)/hot/raw/receipt/base-sequence/
final native publication 알고리즘은 이 diff에서 변경하지 않았다. 공유 frozen store의 native source callback과 AppState
opt-in guard는 이번 재감사로 다시 검토했다. full 회귀 및 별도 E2 cleanup suite, old E3 I25/authority/crash tests를 실행한다.
accepted DATA provenance, Frozen DATA/lineage provenance와 current AppState authorization을 섞지 않는다.

## 24. 독립 비용 측정

실제 SQL driver를 폐기용 copy에만 연결하고 full verifier/frozen recovery/legacy reader의 실제 함수 진입을 계측했다.
제품 work counters는 oracle가 아니다. 새 fixture는 history 7/256, 총 objects 154/1,152다.
[independent-cost.json](benchmarks/t66e4-ra01-reaudit/independent-cost.json)에 반환 rows·bytes·raw/index·pin·timing/RSS를 둔다.

| 새 측정 경로 | 작은 graph | 큰 graph | full/raw/index·pin 결과 |
|---|---:|---:|---|
| legacy/native healthy repeated F0 read | 66 SQL / 9,451 object bytes | 동일 | full/raw/index/lineage 재검증·pin I/D/U 0 |
| required predecessor 거부 | 44 SQL / object bytes 0 | 동일 | full/raw/index·pin I/D/U 0 |
| 거부 후 retained F0 반복 읽기 | 66 SQL / 9,451 bytes | 동일 | 불필요한 전체 작업 0 |
| 정상 data recovery 후 반복 읽기 | 66 SQL / 9,451 bytes | 동일 | 불필요한 전체 작업 0 |
| fresh handle | 1,117 SQL / 271,560 bytes | 7,123 SQL / 1,857,666 bytes | 필요한 full 검증; pin 쓰기 0 |

원 independent observer의 history 5/512(146/2,177 required objects)도 그대로 재실행했다. store-only warm은 64 SQL,
B+J 2입력 warm은 85 SQL이며 둘 다 9,451 bytes다. 동일 API 경계를 구분하며 새 66을 기존 64의 정확한 재현으로
표현하지 않는다. stale conflict는 SQL/body/full/pin 0, legitimate legacy rollback은 두 규모 모두 83 SQL/객체 body 0,
legacy full read 1과 prepared owner DELETE 1이다. explicit recovery의 full fallback과 ordinary repeated read를 구분한다.

native repeat는 두 규모 모두 1,013 SQL/5,948 반환 rows, raw leaf 4/index root+facts-head 2, full verifier/frozen full recovery/
legacy full read 0이다. object bytes는 37,682→183,641, touched leaf rows는 9→259다. 이는 H가 포함된 leaf의 protocol
packing 비용이며 전체 history 순회로 해석하지 않는다. exact server-derived H leaf/index set assertion을 검토하고 재실행했다.
actual pin INSERT/DELETE 4/4는 한 임시 candidate의 4 roots이며 영구 accepted/Frozen owner rewrite는 0이다.

new native repeat latency는 1.350s/1.223s, required predecessor 거부는 17.2ms/11.9ms다. CPU/JIT/observer와 동시 회귀 부하를
포함한 synthetic 측정이며 Android latency/throughput 보장이 아니다. object body bytes는 metadata/J 파일 bytes·physical I/O·
모든 처리 bytes가 아니며 returned rows는 VM scanned rows가 아니다. original before/after evidence는 overwrite하지 않았다.

## 25. 새 독립 사례 행렬

기존 구현 시험은 이 수에 넣지 않는다. 아래 case별 actual result는 machine/JUnit에서 집계하며 direct state/byte evidence와
매칭한다. 첫 import 컴파일 오류와 NR02 harness 교정은 최종 actual case 수와 분리한다.

| ID | 시나리오·기대/관찰 oracle | 결과 |
|---|---|---|
| NR01 | first source precommit rollback→정상 retry; actual installed/source/pending·reopen | PASS |
| NR02 | legacy/native 왕복과 다른 lineage; latest Frozen owner root 전수·fresh child | PASS |
| NR03 ×4 | list/string/int/bool predecessor; source/SQL/B/pending exact 보존 | PASS |
| NR04 | native-only durable owner의 missing predecessor; 두 handle의 명시 거부 | PASS |
| NR05 | 검증 뒤 대기한 old ticket vs newer native request; 승자 committed state 불변 | PASS |
| NR06 | E3 acceptance 뒤 mandatory trigger 제거; source rename/installed COMMIT 없음 | PASS |
| NR07 | native rename 직전 같은 Frozen ID의 다른 metadata owner; exact 승자 source 유지 | PASS |
| NR08 ×2 | previous installed UUID/sequence 오류; SQL owner가 exact라도 stale transition 거부 | PASS |
| NR09 | 같은 generation의 다른 predecessor operation sequence; 명시 거부 | PASS |
| NR10 | 정상 rollback 후 두 fresh handle/process 반복 recovery; idempotent data | PASS |
| NR11 | native precommit 실패→fresh recovery→정상 retry; unknown marker/B/pins 불변 | PASS |
| NR12 | 첫 미게시 legacy preparation 정리→genuine initial native; invented Frozen 없음 | PASS |
| NR13 | damaged native predecessor 거부 후 retained F0 isolated fresh read | PASS |
| NR14 | installed DML 뒤 source binding 변경; SQL rollback·성공 반환 없음 | PASS |
| NP ×3 | foreign principal/dataset/epoch predecessor; unchanged state·retained F0 read | PASS |
| NP-lineage | 같은 Snapshot에 다른 synced_at; frozen lineage 대체 거부 | PASS |
| NP-receipt | truncated durable receipt; native 성공 없음·현재 source/B/pending 보존 | PASS |
| NP-pin | E3 verification 뒤 required root pin 제거; source 준비/설치 차단 | PASS |
| NC7/NC256 | 실제 SQL/object/function-entry·pin observer의 새 두 규모·거부/복구/warm | PASS |
| crash ×3 | actual SIGKILL·fresh process·독립 Python persisted graph/lineage/byte oracle | PASS |


## 26. 역사적 실패 분류

원 Phase A FAIL, 이전 A01 re-audit FAIL, RA16–18의 이전 FAIL은 역사적으로 그대로다. 원 monetary probe는 3 PASS/2 FAIL로
재실행됐으며 두 FAIL은 pre-P0 authoritative reader의 rejection을 기대하는 obsolete assertion이다. 원 P0 Python도 수정 없이
4 PASS/1 FAIL이다. 그 한 FAIL은 `git show ab59d6b:mobile/lib/src/segmented/adapters.dart`가 E4 이전 commit에 없는 fixture
enumeration 오류이며, monetary validator assertion 실패가 아니다. 기존 compatible replay는 동일 monetary assertions를 유지한다.

원 비용 fixture의 lexicographically first raw leaf 선택은 Frozen closure 밖을 고를 수 있다는 한계도 소스·귀속 진단으로
확인했다. 이번 원 비용 assertion은 변경 없이 통과했고 다른 graph의 unread bitrot 즉시 탐지 의무로 확대하지 않는다.
중간 새 harness compile 오류·과도한 pin 요구와 구현 측 과거 개발 중 오류도 현재 제품 finding으로 합산하지 않는다.
역사적이라고 이름 붙였다는 이유만으로 dismiss하지 않고 실제 assertion/contract/실패 위치를 대조했다.

## 27. 전체 회귀 결과

| 검증 | 독립 실행 결과 |
|---|---|
| 원 RA16–18 선택 실행 | 3 PASS / 0 FAIL; 원 assertion 변경 없음 |
| 새 독립 감사 | **29 PASS / 0 FAIL / 0 INCONCLUSIVE** = Dart 18+6, 비용 2, 실제 SIGKILL 3 |
| 원 Phase A 45 | Dart 36 + 원 비용 2 + 실제 종료 6 + P0 compatible replay 1, 모두 PASS |
| 이전 targeted re-audit 20 | 원 Dart 18 + 원 비용 2, 모두 PASS |
| 이전 A01 교정 28 | unit 21 + concurrent 1 + 실제 종료 6, 모두 PASS |
| RA01 교정 51 | unit 42 + native 비용 2 + 실제 종료 7, 모두 PASS |
| E4 authority/race | 기존 grouping 51 PASS; 새 독립 경합은 위 29개와 구분 |
| E4 process-crash | 기존 grouping 36 PASS; 새 독립 SIGKILL 3개는 별도 |
| 전체 Flutter | **1,503 PASS / 0 FAIL / 2 SKIP**, done.success=true, exit 0 |
| E1/E2/E3·I25·Frozen B/J/v4/v7 | full Flutter 포함 suite별 counts/cases와 원 source 보존 확인 |
| E4-P0 구현 / 독립 integration | 183 / 18 PASS |
| P0 independent differential | 24,836 cases / mismatch 0 |
| 별도 E2-A01 socket | 원 5 + 독립 targeted 9 PASS; shared client/FD/C1/hash oracle |
| backend full | **1,315 tests / 1,540 subtests PASS**, failure/error 0, exit 0 |
| analyze / debug APK build | PASS / PASS; 설치 없음 |
| 변경 Dart 7파일·새 감사 4파일 format | PASS; 전체 format의 기존 10파일 차이 보존 |
| Ruff / compileall / diff check | PASS / PASS / PASS; 새 감사 Python도 검사 |
| frontend test/build / script safety | 21 PASS / PASS / 27 PASS |
| 원 monetary diagnostic | 3 PASS / 2 superseded assertion FAIL; 역사적 결과로 구분 |
| 원 P0 Python | 4 PASS / 1 Git baseline fixture FAIL; compatible replay 별도 PASS |
| target/historical SHA | 교정 29파일과 보호한 역사적 44파일 모두 최초와 동일; 제품 diff 없음 |

backend는 이번 첫 full run에서 1,315 tests/1,540 subtests PASS, 2,496.17s다. 원 감사 및 이전 재감사에는 quota 경합 시험의
expected 429/actual 503 실패 후 full rerun PASS 이력이 있다. 이전 targeted audit에서는 focused run도 실패했다.
원인은 확정되지 않았으며 환경 문제로 단정하거나 과거 결과를 지우지 않는다. backend는 이번 diff 밖이고 현재 full run은
실패 없이 완료했다. 이를 해결한 새 backend 교정이라고 주장하지 않는다.

## 28. 포맷·원 자료 보존

교정 Dart 7파일의 format 검사는 PASS다. 전체 `lib test` format 검사는 기존 10개 비변경 파일 때문에 exit 1이다.
[format-baseline.json](benchmarks/t66e4-ra01-reaudit/format-baseline.json)의 10개는 교정 diff 밖이며 `git show 5ad7bc8:<path>`와
byte-identical이다. unrelated reformat은 하지 않았다. P0 current/checkpoint 18파일, 원 diagnostic 5파일과 교정 inventory의
173개 비변경 파일 보존 검사를 재실행했다. 제품과 역사적 감사·fixture는 감사 도중 수정하지 않았다.

## 29. 새 findings

확인된 새 CRITICAL/HIGH/MEDIUM/LOW correctness finding은 **0**이다. 미해결 correction blocker는 **0**이다. 원 RA01은 missing-required provenance를 성공으로 전달하지 않으며 정상 source 실패와 성공의 durable postconditions를 실제 DB/fresh process로 검증했다.

손상된 predecessor를 guessing하지 않는 fail-closed는 새로운 결함이 아니다. 실제 owner 없는 첫 설치의 null을 blanket reject하는
교정도 아니다. 확인되지 않은 arbitrary filesystem attacker·미실행 R1 functionality를 새로운 blocker로 만들지 않았다.

## 30. 남은 한계

finite synthetic interleaving/두 graph 규모의 실측과 source reasoning을 모든 미래 실행의 실측 증명으로 표현하지 않는다.
지원 모델 밖의 비협력 file writer, 악성 rehash metadata, 전원 손실/실기기 fsync, 미읽은 unrelated bitrot, R1/large restore,
production configuration의 실시간 상태는 검증하지 않았다. protocol의 필수 구조·source/lineage/receipt/pin 검사는 이 한계를
이유로 완화하지 않았다. 정상 source 실패 보존과 호출 전에 이미 손상된 source의 evidence 보존을 끝까지 구분한다.

## 31. E4-A01과 E4-RA01 formal closure

**E4-A01: CLOSED. E4-RA01: CLOSED.** 원 stale-race 및 세 predecessor 반례를 변경 없이 재실행했고, 직접 영향받는 source/SQL writer fence, current AppState/session, 정상 첫 설치, failed/committed recovery, Frozen/pending/lineage 및 incremental-cost 경계를 독립 검증했다.

**PASS — E4-RA01 INDEPENDENT TARGETED RE-AUDIT COMPLETE**다. 원 Phase A FAIL과 이전 targeted FAIL은 역사적으로 그대로 남는다. 이 문서는 두 blocker에 대한 새로운 closure 결정이다.

## 32. Phase A gate

**PHASE A BLOCKER CLOSURE: PASS. SAFE TO START T6.6F PHASE B: YES.**

최초 Phase A의 다른 PASS는 audited code/가정이 그대로 유지된 범위에서만 이어받는다. 교정된 세 제품 파일과 직접 영향 경로는 이번에 새로 검토했고 필수 회귀가 완료됐다. 다른 미해결 Phase A blocker는 발견되지 않았다. 따라서 binding stage gate에 따라 Phase A를 progression 가능한 상태로 해제한다.

**Phase B는 NOT STARTED**다. Phase A closure를 integrated Phase B PASS, R1 완료, 일반 사용자 segmented Offline 준비 또는 배포 승인으로 확대하지 않는다. Phase B는 별도 명시 호출이 필요하다.

## 33. R1·production isolation

일반 startup은 기존 OfflineStore와 정상 API/금융 경로를 사용하며 새 E4 entry를 자동 호출하지 않는다.
변경된 AppState method는 명시 isolated opt-in 경로다. normal 금융 read/write, Snapshot v7, OfflineBaseline v4,
frozen B/J, backend authority/config/schema는 diff 밖이다. production SQLite user_version 4를 수정하지 않았다.
R1 `requireSegmentedOfflineRecovery` 및 E4Workspace ordinary loadBaseline gate는 CLOSED다.
Phase B·R1·production API/DB/credentials/service·migration/restart/deployment·APK 설치·segmented activation은 수행하지 않았다.
허용된 debug APK build만 non-production origin define으로 실행했다.

## 34. Audit-only commit/push

새 보고서와 `docs/benchmarks/t66e4-ra01-reaudit/`만 감사 소유 파일이다. product diff empty와 target/historical SHA guard,
explicit stage allowlist 및 cached diff를 확인한 뒤 audit-only commit/push한다. 원 FAIL 보고서를 amend하지 않는다.
자기 참조 hash를 만들지 않으며 실제 audit commit은 다음 명령 및 최종 응답으로 식별한다.

```bash
git log -1 --format=%H -- docs/t66e4-ra01-independent-reaudit.md
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --short
```

```text
T6.6E4-RA01 INDEPENDENT TARGETED RE-AUDIT:
PASS

FAILED PREVIOUS RE-AUDIT COMMIT:
5ad7bc8003e3799da63a912b700432bc48aa6471

AUDITED CORRECTION COMMIT:
af9525e20e6df1dd7dfc152d3db79c1eb07925d2

AUDIT-ONLY COMMIT:
이 보고서를 처음 추가한 commit; §34 Git 명령과 최종 응답으로 식별

REPOSITORY STATE:
VERIFIED

CORRECTION DIFF REVIEW:
COMPLETE

ORIGINAL THREE RA01 FAILURES:
3 PASS
0 FAIL

RA01 ROOT CAUSE:
CONFIRMED

PREVIOUS_SOURCE CONTRACT:
PASS

LEGITIMATE INITIAL INSTALLATION:
PASS

MISSING REQUIRED PREVIOUS_SOURCE:
REJECTED

INVALID PREVIOUS_SOURCE:
REJECTED

STALE PREVIOUS_SOURCE:
REJECTED

SAME-SOURCE DIFFERENT-OPERATION:
PASS

NATIVE INSTALL SUCCESS POSTCONDITIONS:
PASS

FAILED INSTALL SOURCE PRESERVATION:
PASS

FRESH-PROCESS FROZEN-B READ:
PASS — 정상 source의 실패/성공·retained association; 사전 손상된 legacy 반례는 §05

SOURCE/LINEAGE CONSISTENCY:
PASS

SOURCE OWNERSHIP FENCE:
PASS

SQL OWNERSHIP FENCE:
PASS

CHECK-TO-MUTATION ATOMICITY:
PASS

E4-A01 STALE RECOVERY REGRESSION:
PASS

CONCURRENT INSTALL/RECOVERY:
PASS

LEGITIMATE RECOVERY:
PASS

RECOVERY IDEMPOTENCE:
PASS

CROSS-STORE CRASH CONSISTENCY:
PASS

FROZEN PIN RETENTION:
PASS

IMMUTABLE OBJECT RETENTION:
PASS

PENDING B/J DURABILITY:
PASS

UNAUTHORIZED PENDING RETIREMENT:
NONE

ORIGINAL APPSTATE TICKET:
PRESERVED

AUTHORITY/SESSION GUARDS:
PASS

T01 REGRESSION:
PASS

T02 REGRESSION:
PASS

T03 REGRESSION:
PASS

E4-P0 MONETARY REGRESSION:
PASS

E3 I25 COST:
PRESERVED

FROZEN-B REPEATED READ COST:
PASS

INDEPENDENT SQL/OBJECT COUNTERS:
PASS

HISTORICAL DIAGNOSTIC CLASSIFICATION:
COMPLETE

NEW INDEPENDENT AUDIT CASES:
29 PASS
0 FAIL
0 INCONCLUSIVE

EXISTING RA01 CORRECTION TESTS:
51 PASS
0 FAIL

ORIGINAL PHASE A AUDIT CASES:
45 PASS
0 FAIL

PREVIOUS E4-A01 CORRECTION TESTS:
28 PASS
0 FAIL

PREVIOUS TARGETED RE-AUDIT CASES:
20 PASS
0 FAIL

E4 AUTHORITY/RACE:
51 PASS
0 FAIL

E4 PROCESS CRASH:
36 PASS
0 FAIL

FULL FLUTTER TESTS:
1503 PASS
0 FAIL
2 SKIP

FLUTTER ANALYZE:
PASS

FLUTTER BUILD:
PASS

CHANGED-FILE FORMATTING:
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

SNAPSHOT V7:
PRESERVED

OFFLINE BASELINE V4:
PRESERVED

FROZEN B/J:
PRESERVED

SYNC_ROOT / V7 FINGERPRINT:
SEPARATED

R1 GENERAL-USER ACTIVATION GATE:
CLOSED

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
0

NEW LOW:
0

UNRESOLVED CORRECTION BLOCKERS:
0

E4-A01 FINDING:
CLOSED

E4-RA01 FINDING:
CLOSED

PHASE A BLOCKER CLOSURE:
PASS

SAFE TO START T6.6F PHASE B:
YES

T6.6F PHASE B:
NOT STARTED

SAFE TO START R1:
NO — SEPARATE PREREQUISITES PENDING

SAFE TO DEPLOY:
NO

FINAL VERDICT:
PASS — E4-RA01 INDEPENDENT TARGETED RE-AUDIT COMPLETE

NEXT ACTION:
별도 명시 호출로 T6.6F Phase B 통합 검증을 시작한다.
```

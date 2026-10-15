# T6.6E4-A01 독립 targeted re-audit

## 01. 대상과 판정

대상은 `37293dc8b26ca08f94e240408354a6ab6f3d98ac`, 비교 기준은 원 FAIL 감사 commit
`7fc5420353477e16224c6ccce6fadd50e7ff55e0`이다. 원 E4 구현은
`e386586194edbef1fc35f0ea1cf4145a2ae32685`다. E4-A01과 직접 변경된 recovery 경계만 감사한다.

**최종 판정: FAIL — E4-A01 CORRECTION STILL REQUIRED**

원 stale-race 반례는 닫혔다. 그러나 직접 영향 경로에서 **E4-RA01 MEDIUM**을 새로 확인했다.
현재 installed SQL owner가 있는데도 `previous_source=null`을 허용해 source를 삭제하며,
실제 AppState native 설치가 성공한 뒤 기존 Frozen-B lineage가 연결되지 않아 읽기가 실패한다.
새 독립 결과는 **17 PASS / 3 FAIL / 0 INCONCLUSIVE**다. Phase B는 계속 차단한다.

원 FAIL 보고서는 수정하지 않는다. 이번 판정은 그 finding의 closure이며 Phase B, R1 또는 배포
완료 선언이 아니다. 새 독립 결과·전체 회귀와 제한은 아래 실제 실행 증거로 구분한다.

## 02. Repository 확인

변경 전에 AGENTS.md 및 필수 project/domain/known-issues, architecture의 서버 authority 신뢰
경계와 security/runbook 관련 규칙을 읽었다. 시작 working tree는 clean, branch는 main이었다.
HEAD/main/origin/main과 별도 `git ls-remote origin refs/heads/main`이 모두 대상 commit과 일치했다.
원 FAIL/원 구현/P0 checkpoint Git objects도 보존돼 있다.

`git diff --stat 7fc5420..37293dc`, `git diff --name-status`, 두 제품 파일의 전체 diff를 검사했다.
초기 refs와 22파일 SHA-256은 [inventory.json](benchmarks/t66e4-a01-reaudit/inventory.json)에 둔다.
감사 종료 시 같은 hash를 다시 검사하며 제품·과거 증거를 수정하지 않는다.

## 03. 교정 diff inventory

**22 files, +9,417/-19**: 제품 2, 신규 test 1, 문서/benchmark 19다.

| 경로 | 실제 변경 |
|---|---|
| `mobile/lib/src/segmented/workspace.dart` | 전체 source identity 재검사, 조건부 restore/unlink, rollback 보상, legacy/native abandoned preparation 정리 |
| `mobile/lib/src/segmented/store_frozen.dart` | `restoreUncommittedSource`: 같은 writer transaction 안의 installed/prepared SQL fence와 동기 file callback |
| `mobile/test/segmented_e4_a01_test.dart` | unit 21개 |
| `docs/benchmarks/t66e4-a01/` | 별도 concurrent 1개, 실제 SIGKILL 6개, pre/post 및 비용 증거·집계 |
| `docs/t66e4-a01-correction.md` | 교정 보고서; 독립 감사의 대체 증거로 쓰지 않음 |

AppState/coordinator/API/session, E1/E2/E3 verifier/publisher, schema, P0 money parser,
Snapshot/v4 format, production configuration, UI/backend에는 제품 diff가 없다.

## 04. 증거의 독립성

- **IMPLEMENTATION-SIDE CLAIM:** 교정 보고서의 28/45/51/29/1,461/1,315와 비용 보존 주장.
- **INDEPENDENTLY VERIFIED FACT:** 이 감사가 실행한 원 assertion, 새 synthetic interleaving,
  actual SQLite rows/file bytes, fresh process, 독립 C1/SHA/typed closure/F(raw)/Patricia 및 SQL observer.
- **UNVERIFIED ASSUMPTION:** Android 실기기·OS/hardware power loss, arbitrary external file CAS,
  읽지 않은 bitrot의 즉시 탐지, 모든 미래 크기의 latency 보장.

새 DB는 매번 임시 synthetic backend/store에서 만들었다. 기존 구현 시험은 새 독립 case로 세지
않는다. 원 SQL observer와 graph oracle는 과거 독립 감사 도구를 재사용하며 production helper의
reachability/completeness flag를 기대값으로 쓰지 않는다. 비용·ticket 관찰만 폐기용 source copy에
계측했다. 원 제품 파일을 계측하거나 교정하지 않았다.

## 05. 원 E4-A01 실패와 재실행

원 실패는 A의 lineage critical section 밖 `finally`가 예전 source와 `unchanged`를 읽고 metadata/J
await 뒤 source를 먼저 복원한 것이다. 최신 B가 정상 설치돼도 A의 파일 변경은 SQL의 뒤늦은
소유권 거부로 rollback되지 않았다. 원 `workspace.dart:331–353`, `app_state.dart:666–670`과
과거 finding-e4-a01.json을 현재 source와 대조했다.

원 [stale_recovery_test.dart](benchmarks/t66e4-audit/stale_recovery_test.dart)는 변경 없이 실행했다.
실제 SyncCancellation, 같은 AppState/coordinator, 원 pending marker, source byte equality,
새 store handle, 독립 SQL/graph assertions를 모두 유지했다. **1 PASS / 0 FAIL**, `done.success=true`,
exit 0이었다. 최신 source byte equality, B/unknown marker 불변, Frozen read와 fresh-handle recovery
모두 통과했고 별도 SQL foreign_key_check는 0이었다.

수정 전 FAIL은 과거 감사의 사실로 보존하며 이번 corrected source에서 수정 전 실패를 새로
실행했다고 주장하지 않는다. 현재 재현의 전후 source/installed/frozen/sequence 및 raw byte
보존 여부는 [original-reproducer.json](benchmarks/t66e4-a01-reaudit/original-reproducer.json)에 있다.

## 06. Root cause와 실제 mutation 교정

`workspace.dart:472`는 await 뒤 `_requireRecoverySource(source)`를 다시 실행한다.
`485–489`는 **prepared SQL owner 검증/삭제를 시작한 transaction의 finalFence에서** source를
복원한다. 없는/이미 installed인 preparation은 파일을 바꾸기 전에 거부된다.
`250–275`는 hook 뒤 현재 전체 source와 이전 B/ONLINE/no-J를 다시 비교한 뒤 동기 rename/unlink한다.

이것은 앞단 검사만 추가한 변경이 아니다. 과거 file-first 순서를 SQL-owner-first로 바꾸고,
실제 mutation 자체에 현재 source 조건을 붙였다. superseded recovery는 null data-only no-op이며
설치 성공, 과거 ticket 복원, pending acknowledgment로 해석하지 않는다.

## 07. Source 소유권

legacy source는 namespace, frozen UUID, binding checksum, previous_file, 이전 source를 가진다.
native source는 local generation UUID/sequence, previous installation/sequence와 legacy frozen
association을 가진다. sync_root만 같다는 이유로 같은 operation으로 판단하지 않는다.

`_requireRecoverySource`는 제한된 JSON 전체를 비교한다. raw JSON whitespace는 다시 encode되며,
key 순서나 추가 metadata가 달라지면 보수적 superseded no-op일 수 있다. 보안 서명이나
AppState 권한 token을 추가한 것이 아니다. 같은 UUID가 prepared에서 installed로 바뀌는 경우는
별도 SQL state 검사로 보호한다.

다만 이 검사는 **현재 source의 변하지 않음**을 보장할 뿐 이전 source의 유효한 ownership까지
입증하지 않는다. 누락된 predecessor와 실제 installed owner의 모순은 §27 E4-RA01로 남아 있다.

| 직접 mutation 경로 | 소유자·최종 조건 | 재시작/반복 결과 |
|---|---|---|
| `prepareLegacySource` / `prepareSegmentedSource` | 기존 현재 AppState ticket guard 뒤 rename; SQL frozen 또는 accepted data는 먼저 준비 | 기존 pending/installed handoff 규칙 유지 |
| legacy 미게시 source restore/unlink | 같은 prepared UUID/checksum/state + 현재 source 전체 + 원 B/ONLINE/no-J; 같은 write transaction | superseded no-op, current owner만 정리 |
| native 미COMMIT source restore | 현재 installed UUID/sequence/namespace + 같은 source; writer transaction 안 callback | 이전 설치 source만 복원, 새 sequence는 거부 |
| B 게시 뒤 prepared finalization | source 동일 + exact B correspondence + prepared SQL owner | data association만 마무리, ticket/ack 복원 없음 |
| source 없는 초기 orphan cleanup | source 부재 + 이전 B 동일 + installed 부재 + 같은 prepared owner | bounded row 정리, 새 source/설치는 거부 |
| restored legacy/native source의 abandoned cleanup | 검증된 installed Frozen B, 같은 source/B/owner + 다른 미게시 preparation | 최대 1개 orphan만 해제, ambiguous B면 보존/blocked |
| 파일 restore 뒤 COMMIT 실패 보상 | 원 preparation이 남고 방금 복원한 source/B와 installed owner가 여전히 동일 | 새 source를 덮지 않음; 완료된 COMMIT는 보상하지 않음 |

이 경로들은 기존 source record의 조건부 교체 또는 기존 SQL state 전환이다. 새 ownership schema,
영구 ticket, 임의 unpin API 또는 별도 authentication coordinator를 만들지 않았다.

## 08. SQL 소유권

`store_frozen.dart:122–143`는 기존 `_transaction` 안에서 installed ID/sequence/namespace,
필요한 preparation UUID/checksum/state를 재검사한다. legacy cleanup은 기존
`discardFrozenPreparation`의 같은 transaction 안 `_frozen(expected.id)`와 state/checksum을 사용한다.

DELETE의 WHERE는 UUID PK다. checksum 조건과 affected-row count만으로 동시성을 주장하지 않는다.
실제 row 존재·state·checksum 검사가 같은 `BEGIN IMMEDIATE` 안에 있고, exact schema 아래 같은
connection의 PK DELETE 전후에 다른 writer가 개입할 수 없다는 것이 근거다. 현재 SQL owner가
사라졌거나 installed가 됐으면 restore callback이 실행되지 않는다.

## 09. 검사→변경의 원자성 범위

실제 경계는 다음과 같다.

```text
BEGIN IMMEDIATE → mandatory schema 검사 → prepared row 검증/DELETE 또는 installed fence
→ quota·before_commit hook → source 준비·before_source_rename hook
→ 현재 source + B/ONLINE/J 마지막 동기 검사 → rename/unlink → 동기 SQLite COMMIT
```

다른 SQLite connection의 writer는 이 구간에서 제외된다. RA04는 먼저 잡힌 writer가 recovery를
BEGIN에서 거부함을, RA13은 SQL 소유권 검사 뒤 rename hook에서 경쟁하는 두 번째 writer가
STORE_BUSY로 거부되고 그 callback이 실행되지 않음을 실제로 검사한다.
[SQLite transaction 문서](https://www.sqlite.org/lang_transaction.html)와
[rollback locking 문서](https://www.sqlite.org/lockingv3.html)의 writer/reader 규칙과 대조했다.

파일 경계는 기존 **같은 owning AppState/isolate**에서 동기 final check→rename으로 보호된다.
검사 뒤 await/isolate round trip/제품 hook은 없다. private SQLite에 application UDF/commit hook을
등록하는 경로도 없다. SQL lock이 다른 process의 임의 파일 rename까지 막는다고 주장하지 않는다.
여러 independent process/isolate가 같은 workspace 파일을 협력 protocol 없이 쓰는 전역 CAS는
이번 교정과 기존 지원 모델의 보장이 아니다. 이 한계를 SQLite connection 간 writer 보호와 구분한다.

## 10. 같은 source·다른 operation

RA10은 같은 generation과 **같은 binding checksum**을 갖는 다른 frozen UUID를 설치한다.
A가 읽은 source와 B의 operation UUID가 다르므로 A의 rollback은 no-op이어야 한다.
RA01은 같은 UUID의 SQL owner가 실제 prepared→installed로 전환되는 경우도 별도로 검사한다.
RA02는 이미 삭제된 SQL owner의 exact source replay를 corruption fixture로 만들어 file-first
변경/부활이 불가능한지 검사한다. RA11의 임의 추가 metadata는 비교 sensitivity 시험이며 새
protocol operation ID나 authorization field로 도입한 것이 아니다.

## 11. Concurrent install/recovery

원 FA17, 기존 correction의 metadata/J × native/legacy 4변형 및 별도 concurrent-winner 시험을
실행했다. source가 바뀐 stale recovery는 최신 SQL owner/pins를 정리하지 않고 종료해야 한다.
RA03은 두 store handle에서 네 recovery를 겹쳐 bounded preparation만 해제하는지 검사한다.
기존 AppState lineage lock이 모든 connection을 잠근다는 가정은 사용하지 않았다.

## 12. Delayed recovery와 원 ticket

AppState 제품 diff는 없다. 원 coordinator의 begin은 E2 전에 발급되고 같은 closure가 E3/E4
설치까지 유지된다. A의 취소는 취소로 남고 B는 자기 원 ticket으로 설치한다.
추가 폐기용 관찰은 실제 begin의 세 정수와 A의 SQL/source를 기록하되 원 assertion은 유지한다.
실제 관찰된 `(lineage, authentication, request)`는 initial `(0,0,1)`, A `(0,0,2)`,
B `(0,0,3)`이었다. 같은 관찰 실행의 A source는
`3379eb5e-bfd9-48cd-b230-afc3b781a0a4`(prepared, sequence 1), B source는
`443ee5a0-cbba-43a1-a2d7-17b932078e9f`(installed, sequence 2)였다.
A가 재개된 뒤에도 B source와 lineage/pins는 그대로였다. A의 기존 source checksum,
legacy lineage, Snapshot identity, receipt 및 root rows와 B의 최종 독립 graph를
[operation-observation.json](benchmarks/t66e4-a01-reaudit/operation-observation.json)에 보존했다.
이는 source copy의 추가 logger 관찰이다. 원 uninstrumented 재현 PASS를 이 logger로 대신하지 않았다.

이 durable operation evidence를 현재 AppState authorization으로 해석하지 않는다.
fresh recovery는 ticket을 재구성하지 않으며 UI 설치·POST·pending retirement를 하지 않는다.

## 13. 합법적 recovery

owner가 여전히 현재이면 미게시 preparation의 이전 source 복원이 가능해야 한다.
B가 이미 새 값으로 rename됐으면 exact B/lineage를 검증하고 data association만 마무리한다.
native/native-only predecessor, source 없는 최초 preparation, rollback 뒤 orphan도 별도 시험한다.
복구 전체를 비활성화한 수정으로 PASS시키지 않는다.

## 14. Idempotence

RA12는 복구 후 같은 상태에서 세 번 다시 실행하고, 새 store와 별도 process에서 읽는다.
existing concurrent/current-owner recovery도 반복한다. source/B/pending exact bytes와 committed
references가 바뀌지 않아야 하며 prepared owner는 하나만 정리돼야 한다. 복구 실행 횟수를
시험 수에 중복 합산하지 않는다.

## 15. Source/lineage

검사는 source UUID뿐 아니라 frozen binding, local generation/sequence, original v7 fingerprint,
Snapshot ID, 전체 OfflineBaseline v4 logical lineage를 대조한다. 같은 금융 rows를 다른
lineage로 재연결하지 않는다. 원 oracle는 leaf bytes와 원 control에서 11 tables/F(raw)/Patricia,
Snapshot restore/fingerprint 및 v4 lineage를 독립적으로 검사한다. 정상 metadata에서의 이 검증과
복원 대상 predecessor 검증은 다르다. E4-RA01에서는 graph/SQL binding은 완전하지만 source
연결만 없어져 Frozen-B가 읽히지 않았다.

## 16. Frozen pins

accepted/installed/frozen 소유권은 구분된다. recovery는 실제 prepared owner만 삭제하며
installed frozen 해제 API를 만들지 않는다. 다른 E3 acceptance만으로 Frozen B를 해제하지 않는다.
별도 SQLite `foreign_key_check`, generation_roots와 typed closure 및 실제 object hashes로
required graph 보존을 확인한다. PK row count만으로 retention PASS를 판단하지 않는다.

## 17. Pending B/J

outcomeUnknown marker는 원 재현과 새 시험에서 byte-identical이어야 한다. read-only recovery가
acknowledge/retire/replay할 경로는 없다. RA07은 검사가 진행되는 동안 유효 ordered J를 추가하여
source 복원·pin release가 차단되고 J bytes가 그대로 남는지 검사한다. 정상 confirmed retirement는
기존 AppState 원 ticket/token/owner/status/retry identity 경계에 남아 있다.

## 18. Cross-store와 실패 보상

파일과 SQLite는 하나의 transaction이 아니다. legacy rollback에서 파일 복원 후 COMMIT가
실패하면 SQL rollback 뒤 **원 preparation이 아직 있고 방금 복원한 source/B가 그대로일 때만**
SQL ownership fence 아래 원 preparation source를 다시 연결한다(`workspace.dart:490–514`).
post-COMMIT 오류로 row가 사라졌다면 완료된 작업을 rollback으로 가장하지 않는다.

기존 real COMMIT BUSY 및 RA14는 보상 도중 새 valid source가 생겨도 이를 덮어쓰지 않는지
확인한다. ambiguous association에서는 pins/pending을 유지하고 실패한다. 파일 restore 뒤
process death로 SQL prepared row만 남으면 현재 installed source/B 아래 bounded orphan만 정리한다.

## 19. 실제 process-crash

기존 E4 child termination 17개는 full Flutter 안에서 **17 PASS**였다. 원 독립 G1→G2 SIGKILL 6개는
**6 PASS, 689.476초**, 교정 측 실제 SIGKILL 6개는 **6 PASS, 511.059초**였다.
따라서 E4 process-crash grouping은 **29 PASS / 0 FAIL**다. 원 6개는 원 Phase A 45에,
교정 6개는 구현 correction 28에 포함되므로 새 독립 17개에 더하지 않는다.

SIGKILL supervisor는 tester PID와 barrier를 확인한다. source restore 전 COMMIT case는 실제
별도 SHARED reader로 COMMIT를 막고, 파일이 복원됐으며 prepared row가 아직 남아 있는지
kill 직후 확인한다. exception-only 시험을 process termination으로 세지 않는다. 모든 재개방은
fresh process/SQLite에서 graph/pin/source/B/unknown marker를 검사한다. power loss 보장은 아니다.

## 20. Fresh-process readability

원 reproducer의 fresh handle과 실제 child recovery를 구분한다. RA01/RA10/RA12 및 실제
SIGKILL 재개방은 다른 Flutter process에서 Frozen B를 읽는다. 비용 시험의 cold child도 별도
process에서 current source/lineage와 ordered J를 검사한다. 프로세스 내 cached boolean으로
재시작 성공을 추정하지 않는다. 반면 RA16/17은 source 삭제 뒤 fresh handle의 복구가 실패했고,
RA18은 fresh recovery가 정상 반환한 뒤에도 Frozen-B 읽기가 실패했다. RA18은 별도 Flutter
process에서도 실제 FROZEN_BINDING_INVALID / exit 1을 확인했다. 이 child의 오류 종료를
SIGKILL 29개에 더하지 않는다. negative 결과도 보존한다.

## 21. T01/T02/T03 regression

T01 원 ticket/session/pending authority, T02 durable frozen ownership/공유 graph retention,
T03 provenance key/invalidation/full fallback을 관련 기존 suite로 실행한다. AppState 및 E3
final guard→COMMIT body는 변경 없음을 확인했다. 원 45개 Phase A 사례도 현재 source로 재실행한다.
원 Phase A **45 PASS / 0 FAIL**: 원 Dart 35 + 변경 없는 FA17 1 + 원 독립 비용 2 +
원 SIGKILL 6 + 원 assertions를 유지한 P0 compatible replay 1이다. 교정 측 28개도 unit 21 +
별도 concurrent winner 1 + SIGKILL 6을 모두 실행해 **28 PASS / 0 FAIL**로 확인했다.

## 22. P0 보존

교정 diff는 monetary 경로를 건드리지 않는다. 원 inventory의 변경 허용 두 제품 파일 외 69개,
P0 checkpoint의 source/fixture 및 원 진단을 hash로 대조한다.
`"\u001c+0001000.00\u001f"`의 authoritative 원문 수락/보존과 frozen exactMoney 입력 거부는
기존 183개 및 원 독립 integration으로 재검사한다. C1/hash/v7 fingerprint/v4 lineage를
숫자 표시값의 동등성만으로 판단하지 않는다.

## 23. 비용

I25는 정상 steady-state full N 작업 반복을 금지한다. cold/restart/명시 full export와
손상/불확실성의 full fallback은 구분한다. 원 64 SQL은 storage-only, 전체 B+J reader는 85 SQL이었다.
새 `measure.py`는 임시 source copy에서 실제 SQL, driver BLOB/rows, 실제 complete verifier 및
legacy reader 함수 진입을 관찰한다. 제품 supplied work counter를 판정 oracle로 읽지 않는다.

실제 required objects는 history 5/512에서 **146 / 2,177**이었다.

| 경계 | 작은/큰 SQL | returned rows | object-body bytes | full verification | pin I/D/U |
|---|---|---|---|---|---|
| unchanged store-only | **64 / 64** | 288 / 288 | **9,451 / 9,451** | 0 / 0 | 0/0/0 |
| unchanged 전체 B+J | **85 / 85** | 423 / 423 | **9,451 / 9,451** | 0 / 0 | 0/0/0 |
| cold 및 handle reopen | 1,088 / 13,304 | 1,716 / 15,987 | 258,936 / 3,489,198 | 1 / 1 | 0/0/0 |
| 실제 fresh-process cold | 1,088 / 13,304 | 1,716 / 15,987 | 258,936 / 3,489,198 | 1 / 1 | 0/0/0 |
| delayed stale conflict 재개 | 0 / 0 | 별도 object 조회 없음 | 0 / 0 | 0 / 0 | 0/0/0 |
| 합법적 owned rollback | **52 / 52** | metadata/파일 recovery | 0 / 0 | 0 / 0 | root pins 0/0/0; 준비 frozen owner DELETE 1 |

합법적 rollback에는 기존 full legacy B read 1회와 파일 해시 검사가 있다. 24,707/120,893µs로
크기 영향을 받는 **명시 interruption recovery**이며 ordinary warm read에 반복되지 않았다.
stale conflict의 0 bytes는 source metadata I/O까지 0이라는 뜻이 아니다.

stale conflict·legitimate recovery 뒤 warm 전체 B+J는 25,208/26,747µs,
store-only는 22,390/20,909µs였다. 실제 fresh-process cold는 1,233,666/5,250,555µs였고
반드시 full verifier 1회와 legacy reader 1회를 수행했다. 후속 정상 warm의 raw/index/full/legacy
재검증은 0이다. 원 감사의 12개 warm size/phase 조합과 현재 독립 재실행의 해당 작업량을 대조한다.
SQL/body/함수 진입이 같다는 근거를 latency 개선 주장과 구분한다.
[cost-comparison.json](benchmarks/t66e4-a01-reaudit/cost-comparison.json)의 12개 대조는 mismatch 0이다.

source는 16KiB, frozen rows는 최대 2개다. bounded ownership 재검사가 history-dependent full
scan으로 바뀌는지 source와 두 규모 관찰을 함께 평가한다. returned rows는 VM scanned rows가
아니며 body bytes에 metadata/J 파일·physical I/O는 포함하지 않는다. JIT·병행 synthetic workload
latency를 Android production latency로 표현하지 않는다.

## 24. 역사적 diagnostic 분류

원 probe_test.dart의 두 FAIL은 서버 유효 값을 legacy authoritative reader가 거부해야 한다는
교정 전 assertion이다. P0 계약에서는 이를 수락해야 하므로 의도적으로 보존된 과거 기대다.
원 Python P0의 별도 FAIL은 E4 신규 adapters.dart를 존재하지 않는 E3 commit에서 `git show`하려는
baseline enumeration fixture 오류다. 원 assertions나 파일을 고치지 않았다. 기존 독립 compatible
replay는 `--diff-filter=M`만 보완해 같은 monetary/byte/hash assertions를 실행한다.
이번에도 원 진단은 **3 PASS / 2 과거 assertion FAIL**, 원 P0 suite는 **4 PASS / 1 fixture FAIL**,
compatible replay는 **1 PASS**였다. 해당 baseline fixture 오류는 monetary assertion에 도달하기 전
발생한다. 나머지 원 P0 corpus의 수락/거부·raw/C1/hash 검사는 별도로 통과했다. 새 current-contract
defect로 분류하지 않으며 역사적 기대를 삭제해 모두 PASS라고 쓰지도 않는다.

## 25. 새 독립 matrix

새 독립 case는 **17 PASS / 3 FAIL / 0 INCONCLUSIVE**: RA01–RA15와 두 graph 비용 시험은 PASS,
RA16/17의 누락 predecessor 및 RA18의 실제 AppState 후속 설치는 FAIL이다.
RA01/RA10/RA12의 child 읽기, RA07의 J 기록 보강 재실행, ticket logger 재실행과 비용 phases를
별도 case로 추가 계수하지 않는다.

| 요구 interleaving | 실제 실행·관찰 |
|---|---|
| A 원 stale recovery | 변경 없는 FA17; 최신 source/B/pins/pending 및 reopen 보존 |
| B recovery/install overlap | FA17, 기존 metadata/J × native/legacy 4변형; stale no-op |
| C competing recoveries | RA03 두 handle/네 recovery와 기존 concurrent-winner; 소유권 혼동 없음 |
| D same source/different operation | RA10 동일 binding checksum·다른 UUID, RA01 같은 UUID state 변경 |
| E legitimate recovery | RA12, existing native/native-only/first preparation; 유효 이전 source 복원 |
| F repeated recovery | RA12 세 번+handle/process reopen; committed identity/pending 동일 |
| G fresh process after stale A/B | 실제 stale_before_release/stale_after_conflict SIGKILL+reopen |
| H failed SQL update | RA04/RA13 actual writer BUSY, RA14 actual COMMIT BUSY 보상; 최신 source 보호 |
| I newer installation fails | RA15 actual AppState B의 pre-install failure; A 재개 후 이전 유효 B 보존 |
| J different valid lineage | 원 FA17 backend mutation G2 및 새 lineage/source, RA06 B 변경 |
| K source replacement near mutation | RA09 및 existing 마지막 rename hook; 후속 source 재검사 |
| L retention | direct SQL roots/receipts 및 independent C1/typed closure; 최신/이전 required graph 보존 |
| 누락 predecessor ownership — **FAIL** | RA16/17 source unlink 정상 반환; RA18 native 설치 성공 뒤 기존 Frozen-B 읽기 불가 |

RA02와 RA05의 source replay/schema 손상은 controlled corruption이며 production execution을
가장하지 않는다. RA07은 실제 생성한 J의 operation ID/sequence/payload와 exact bytes를 기록한다.
각 실제 case 이름과 결과는 [cases.json](benchmarks/t66e4-a01-reaudit/cases.json), 지속 상태는
[persisted.json](benchmarks/t66e4-a01-reaudit/persisted.json)에 있다.

각 case의 이름·PASS/FAIL은 실제 machine 결과로 계수한다. fixture compile/선택 옵션/observer
경로 오류와 중단된 harness는 제품 FAIL 또는 새 PASS로 세지 않는다. 기존 implementation의
28개를 새 independent case로 합산하지 않는다.

RA16/17의 첫 예외 요구와 RA18 첫 실행의 “성공 거부” assertion을 보존한 뒤, 최종 실행은
**정상 반환한다면 실제 기존 Frozen-B source/읽기를 보존해야 한다**는 durable invariant와
재개방/별도 process 읽기로 보강했다. verified previous
복구 후 정상 성공하는 합법적 구현까지 금지하지 않는다. 현재 제품은 그 보강된 assertion에도
FAIL했다. 원 FA17 및 기존 제품 tests의 correctness assertions는 변경하지 않았다.

## 26. 전체 회귀

| 실제 실행 | 결과 |
|---|---|
| 원 E4-A01 그대로 | 1 PASS; assertion/timeout/원 파일 hash 불변 |
| 원 Phase A cases | 45 PASS / 0 FAIL |
| 구현 correction cases | 28 PASS / 0 FAIL: unit 21 + concurrent 1 + 실제 SIGKILL 6 |
| 새 독립 cases | **17 PASS / 3 FAIL / 0 INCONCLUSIVE**, E4-RA01 |
| 기존 E4 authority/race grouping | 51 PASS: handoff 35 + adapter authority 16; full suite에 포함 |
| E4 T01/T02/T03 기존 suite | handoff 35 / frozen 19 / provenance 11 PASS; 새 negative lineage 반례는 별도 FAIL |
| E4 process-crash grouping | 29 PASS: 기존 17 + 원 독립 6 + correction 6 |
| 기존 E1/E2/E3 실제 crash | 7 / 3 / 16 PASS, full suite에 포함 |
| P0 monetary / 독립 integration | 183 / 18 PASS |
| E1 money/schema corrections | 166 / 45 PASS |
| E2-A01 | Flutter 13 + 독립 TCP Python 5 PASS |
| E3 incremental/I25/authority/publication | 관련 기존 suite 모두 PASS; normal producer/source hash 보존 |
| full Flutter | **1,461 PASS / 0 FAIL / 2 SKIP**, done.success=true, exit 0, 3,756.498초 |
| analyze / debug APK build | PASS / PASS, exit 0; 설치 없음 |
| correction changed-file format | Dart 5파일 PASS; 신규 audit Dart 3파일도 별도 PASS |
| full formatting | 기존 변경 없는 10파일 차이로 exit 1; correction diff 밖임을 확인, 수정 안 함 |
| 최종 backend full | **1,315 tests / 1,540 subtests PASS**, exit 0, 1,706.148초 |
| Ruff / compileall / diff check | PASS / PASS / PASS |
| frontend npm test / build | 21 PASS / build PASS |
| scripts safety | 27 PASS; 배포 실행 아님 |
| 역사적 진단 / 원 P0 fixture | 3 PASS/2 과거 assertion FAIL, 4 PASS/1 fixture FAIL; §24 참조 |

Backend JUnit 2,855는 tests와 subtests 합계다. visible Flutter testDone과 done.success 및 실제
process exit를 모두 확인했다. 각 재실행이나 child invocation을 full suite 개수에 더하지 않았다.
정확한 per-file 결과·최초 실패·exit는 [summary.json](benchmarks/t66e4-a01-reaudit/summary.json)에 있다.

실제 명령은 아래와 같다. Flutter cwd는 `mobile`, backend pytest는 `backend`, npm은 `frontend`다.
독립 시험 및 copy instrumentation 명령은 [README](benchmarks/t66e4-a01-reaudit/README.md)에 둔다.

```bash
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine --concurrency=2 test
/home/hjkerman/.flutter/bin/flutter analyze --no-pub
/home/hjkerman/.flutter/bin/flutter build apk --debug --no-pub --dart-define=MONEY_NOTE_API_BASE_URL=https://reaudit.invalid
../.venv/bin/python -m pytest -q --junitxml=/tmp/mn-e4-a01-reaudit/backend-final.xml
.venv/bin/python -m ruff check backend/app backend/tests scripts/local_deploy.py scripts/tests
.venv/bin/python -m compileall -q backend/app backend/tests scripts
E4_A01_OUTPUT=/tmp/mn-e4-a01-reaudit/correction-crash .venv/bin/python -m pytest -q docs/benchmarks/t66e4-a01/test_crash.py
E4_AUDIT_OUTPUT=/tmp/mn-e4-a01-reaudit/phase-a-crash .venv/bin/python -m pytest -q docs/benchmarks/t66e4-audit/test_crash.py
git diff --check
```

첫 backend 전체 실행은 **1,314 PASS / 1 FAIL / 1,540 subtests PASS**, exit 1,
2,282.225초였다. `tests/test_isolated_sync_transfer.py:497`의
`test_bounded_concurrent_quota_and_same_request_status`에서 expected `[201,201,201,201,429]`
대신 `[201,201,201,201,503]`이었다. 단독 재실행도 **0 PASS / 1 FAIL**, 5.201초로 같은 차이가
재현됐다. 이를 단독 PASS로 해소됐다고 보고하지 않는다.

과거 E2 및 원 Phase A 감사에 동일 현상이 기록돼 있고 backend product/test는 이번 diff에서
바뀌지 않았다. 직접 root cause를 입증하지 않았으므로 환경/CPU 경합 원인이라고 단정하거나
E4-A01의 source ownership 결함이라고 귀속하지 않는다. 최종 전체 재실행은 위 표와 summary에
별도로 보존한다. 잔여 backend quota 시험 불안정성은 Phase B에 전달하며 역사적 FAIL을 지우지 않는다.

새 감사 harness의 초기 잘못된 `object_refs` table, 오류형·fixture 참조 사전 점검,
observer copy의 support 경로 누락, plain-name/regex 선택 오류는 제품 결과와 구분한다.
제품과 원 반례 assertions/timeout은 바꾸지 않았다. 원 새로운 assertion을 무조건 성공하는
기대로 약화하지 않았으며 올바른 실제 schema/API를 확인해 harness를 수정했다.

## 27. Findings

**Critical 0 / High 0 / Medium 1 / Low 0.**

### E4-RA01 — 누락된 predecessor와 현재 installed owner의 모순을 허용함

**Severity: MEDIUM. Phase B blocker: YES.** 원 E4-A01의 정상 metadata stale race와는 구분되는
직접 영향 recovery/ownership 결함이다. 이 동작을 이번 교정이 처음 도입했다고 주장하지 않는다.

**Source:** `mobile/lib/src/segmented/workspace.dart:57–60`은 previous_source를 optional Map으로만
검사한다. `:266–272`는 null이면 source를 삭제하고, `:276–283`의 fence는 이전 B hash/ONLINE/J만
검사한다. legacy `:485–489`의 prepared DELETE와 native `:417–426`의 restore 경로 모두 이전
source가 현재 installed SQL owner를 가리켜야 하는 관계를 확인하지 않는다.
`mobile/lib/src/segmented/store_frozen.dart:122–143`은 current installed fence를 통과해도 callback의
null predecessor와 그 owner의 모순을 배제하지 못한다. `workspace.dart:171–190`의 다음 native
source는 이전 파일이 없으면 legacy_frozen/binding을 null로 기록한다.

**위반 계약:** §26의 안전한 handoff/recovery, §29의 Frozen B와 durable legacy lineage association,
이번 재감사 §12의 missing/invalid expected ownership evidence에 대한 fail-closed 요구다.
`previous_source` 부재는 첫 handoff에서는 가능하지만 실제 SQL installed/Frozen B가 있는 상태에서
이전 소유권 부재의 증거가 될 수 없다.

**최소 조건:** 정상 F0/B0/installed SQL owner, 그 위에 미완료 legacy 또는 native preparation,
그리고 source JSON의 **previous_source 한 필드만 null이 된 불일치**다. C1 object, checksum,
receipt, financial rows, credentials를 변경하거나 재해시하지 않는다. 서로 다른 process의
비협력 파일 writer나 잘못된 현재 AppState ticket도 필요 없다. controlled local-metadata corruption
시험이며 원격 exploit/일반 정상 handoff의 실패로 표현하지 않는다.

**재현:** [independent_test.dart](benchmarks/t66e4-a01-reaudit/independent_test.dart)의 RA16–RA18.

1. 같은 실제 AppState로 valid F0/B0를 설치하고 unknown pending marker를 만든다.
2. 기존 E4 API로 미완료 source preparation을 만들며 previous_source가 실제로 존재함을 확인한다.
3. 새 폐기용 source 파일에서 그 필드만 null로 바꾼다. 현재 SQL owner와 B0는 정상으로 남긴다.
4. RA16/17은 recovery를 직접 실행한다. 오류 없이 반환하고 source 파일이 삭제된다. legacy의
   prepared row 정리도 COMMIT된다. 새 store handle에서 recovery는 FROZEN_BINDING_INVALID다.
5. RA18은 직접 cleanup 대신 실제 `AppState.refreshSegmentedForIsolatedUse`를 호출한다.
   initial recovery가 위 불일치를 통과한 뒤 native installation이 **성공 반환**한다.
6. 새로운 native source의 legacy_frozen/binding은 null이지만 SQL에는 기존 F0 installed owner와
   pins가 남는다. 즉시 및 store 재개방 뒤의 F0 읽기는 모두 FROZEN_BINDING_INVALID다.
   fresh native recovery 자체는 정상 반환한다. 별도 Flutter process의 재개방/읽기도 실제
   FROZEN_BINDING_INVALID로 실패한다.

**기대:** predecessor의 namespace/kind/ID/sequence/Frozen binding을 실제 installed SQL owner와
대조한 뒤에만 restore/unlink해야 한다. 불일치하면 source/prepared evidence를 보존하고 blocked로
반환하거나, 계약상 허용되는 verified previous association을 명시적으로 복구해야 한다. 현재
설치가 기존 Frozen B 연결을 잊은 상태로 성공을 반환해서는 안 된다.

**실제·독립 증거:** [finding-e4-ra01.json](benchmarks/t66e4-a01-reaudit/finding-e4-ra01.json)에 세
실행의 actual source/accepted/installed/frozen/root rows와 byte hashes 및 fresh-handle 결과를 둔다.
RA18은 `installed_successfully=true`, install_error=null, fresh_recovery_error=null이면서
read_error와 fresh_read_error가 모두 FROZEN_BINDING_INVALID다. 독립 Python read-only SQLite
C1/SHA/typed closure/F(raw)/11-table/Patricia 검사는 통과했다. B/pending bytes도 그대로다.
따라서 object/pin 유실과 source-to-lineage 연결 손상을 혼동하지 않는다.

**영향:** 현재 ticket으로 정상 반환한 native installation 이후에도 반드시 보존해야 할 기존
Frozen B가 읽히지 않는 재현 가능한 lineage/recovery 가용성 결함이다. authoritative financial rows,
raw money, unknown pending, required graph/pins의 삭제는 관찰되지 않아 Medium으로 제한한다.

**최소 교정:** 기존 writer transaction/final fence 안에서 **복원 대상** previous_source의 존재와
typed identity를 현재 installed/Frozen SQL owner 및 이전 B association에 대조한다. 실제 이전 owner가
있는데 predecessor가 없거나 불일치하면 파일 unlink/rename과 준비 row release 전에 거부한다.
확인되지 않은 부재를 다음 native source의 legacy association 부재로 전달하지 않는다.
진짜 첫 handoff의 정상 null predecessor는 허용한다. 새 schema/auth system/금융 계산/R1 설계는
필요하지 않으며 이 감사에서는 제품을 수정하지 않는다.

**필수 회귀:** RA16/17이 durable 변경 전에 명시 거부하거나 검증된 기존 source를 복구하고,
RA18이 source 연결을 잃은 성공을
반환하지 않아야 한다. 기존 valid first/native/native-only recovery, 원 FA17 및 warm cost도 유지해야 한다.

## 28. 한계

지원 경계는 하나의 owning AppState/isolate의 협력 source writer와 실제 SQLite의 복수 connection이다.
임의 OS source replacement, 악성 재해시 metadata, 실기기 hardware power loss까지 보장하지 않는다.
최신 source 비교는 authentication 체계가 아니며 durable receipt도 설치 ticket이 아니다.
유한한 graph 두 규모의 비용 및 bounded synthetic interleaving을 모든 미래 실행의 실측 증명으로
표현하지 않는다. required source/SQL/lineage/pin 검사는 이 제한을 이유로 완화하지 않았다.

## 29. Phase A blocker closure

**원 E4-A01 stale-race finding 자체는 CLOSED**다. 원 반례·same-checksum/different-UUID·동시
recovery·writer fencing을 실제로 재검증했다. 원 감사 보고서는 역사적으로 FAIL 그대로다.
변경 없는 code/가정의 원 PASS 증거는 그대로 유지할 수 있고 직접 변경된 경로도 새로 검사했다.

그러나 **E4-RA01 MEDIUM이 OPEN**이므로 Phase A 전체 blocker closure는 **FAIL**이다.
원 sole finding의 교정을 새 ownership 불일치까지 안전하다는 승인으로 확대하지 않는다.

## 30. Phase B

**SAFE TO START T6.6F PHASE B: NO.** E4-RA01의 최소 predecessor/SQL 관계 교정과 독립 재감사가 필요하다.

Phase B는 실행하지 않았다. 이 감사와 기존 full regression은 D1–D3c/E1–E4 integrated Phase B의
별도 검증을 대신하지 않는다.

## 31. R1·production

R1 recovery/activation gate는 CLOSED다. E4 adapters의 isolated synthetic 시험만 수행했다.
production DB/API/credentials/service에 접근하지 않았고 migration/restart/deployment/segmented
activation/APK install을 수행하지 않았다. debug APK는 `https://reaudit.invalid` define으로 build만 한다.
기존 startup·일반 금융 read/write·Snapshot v7·OfflineBaseline v4·backend 금융 authority는 보존한다.

## 32. Audit-only commit/push

새 파일은 이 보고서와 `docs/benchmarks/t66e4-a01-reaudit/`뿐이다. 원 보고서·진단·correction
artifacts와 제품은 stage하지 않는다. 마지막 hash/allowlist/cached diff 확인 뒤 audit-only commit을
push하고 HEAD/main/origin/main/실제 remote/clean 상태를 확인한다.

자기 참조 hash를 만들지 않는다. 이 보고서를 처음 포함한 commit과 실제 최종 상태는 다음 명령 및
최종 응답으로 식별한다.

```bash
git log -1 --format=%H -- docs/t66e4-a01-independent-reaudit.md
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --short
```

```text
T6.6E4-A01 INDEPENDENT TARGETED RE-AUDIT:
FAIL

ORIGINAL FAILED AUDIT COMMIT:
7fc5420353477e16224c6ccce6fadd50e7ff55e0

AUDITED CORRECTION COMMIT:
37293dc8b26ca08f94e240408354a6ab6f3d98ac

AUDIT-ONLY COMMIT:
이 보고서를 최초 포함한 commit — §32 명령으로 식별

REPOSITORY STATE:
VERIFIED

CORRECTION DIFF REVIEW:
COMPLETE

ORIGINAL E4-A01 REPRODUCER:
PASS

ROOT CAUSE VALIDATION:
PASS

STALE SOURCE OWNERSHIP FENCE:
PASS — 원 정상 metadata stale race

SQL OWNERSHIP FENCE:
FAIL — 복원 대상 predecessor/installed 관계 미검증

CHECK-TO-MUTATION ATOMICITY:
PASS — 기존 owning isolate 및 SQLite writer serialization 범위

SAME-SOURCE DIFFERENT-OPERATION:
PASS

NEWER SOURCE PRESERVATION:
PASS — 원 race와 정상 metadata

CONCURRENT INSTALL/RECOVERY:
PASS

CONCURRENT RECOVERY:
PASS

LEGITIMATE RECOVERY:
PASS — 유효한 predecessor

RECOVERY IDEMPOTENCE:
PASS

FRESH-PROCESS RECOVERY:
FAIL — E4-RA01; 정상/실제 SIGKILL cases는 PASS

FROZEN-B READ AFTER STALE RECOVERY:
PASS — 원 E4-A01

SOURCE/LINEAGE ASSOCIATION:
FAIL

FROZEN PIN RETENTION:
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
FAIL — invalid predecessor 뒤 설치 성공; 기존 authority tests는 PASS

T02 REGRESSION:
FAIL — lineage association; pins는 보존

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
17 PASS
3 FAIL
0 INCONCLUSIVE

ORIGINAL PHASE A AUDIT CASES:
45 PASS
0 FAIL

EXISTING E4-A01 CORRECTION TESTS:
28 PASS
0 FAIL

E4 AUTHORITY/RACE:
51 PASS
0 FAIL

E4 PROCESS CRASH:
29 PASS
0 FAIL

FULL FLUTTER TESTS:
1,461 PASS
0 FAIL
2 SKIP

FLUTTER ANALYZE:
PASS

FLUTTER BUILD:
PASS

CHANGED-FILE FORMATTING:
PASS

BACKEND REGRESSION:
1,315 TESTS
1,540 SUBTESTS
PASS — 최종 전체 실행; 최초 전체/단독 실패는 §26에 보존

RUFF:
PASS

COMPILEALL:
PASS

GIT DIFF CHECK:
PASS

SNAPSHOT V7:
PRESERVED

OFFLINE BASELINE V4:
REGRESSED — B bytes/hash는 보존, Frozen-B source 연결은 E4-RA01

FROZEN B/J:
REGRESSED — lineage association; B/J bytes와 pins는 보존

SYNC_ROOT / V7 FINGERPRINT:
SEPARATED

R1 GENERAL-USER ACTIVATION GATE:
CLOSED

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
1

NEW LOW:
0

UNRESOLVED E4-A01 BLOCKERS:
1 — 직접 영향 경로의 E4-RA01

E4-A01 FINDING:
CLOSED — 원 stale-race에 한함; E4-RA01은 OPEN

PHASE A BLOCKER CLOSURE:
FAIL

SAFE TO START T6.6F PHASE B:
NO

T6.6F PHASE B:
NOT STARTED

SAFE TO START R1:
NO — SEPARATE PREREQUISITES PENDING

SAFE TO DEPLOY:
NO

FINAL VERDICT:
FAIL — E4-A01 CORRECTION STILL REQUIRED

NEXT ACTION:
E4-RA01의 predecessor와 실제 installed/Frozen SQL owner 관계 검사를 최소 교정한 뒤 독립 재감사를 수행한다.
```

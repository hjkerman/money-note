# T6.6E3 구현 기록 — authority-fenced segmented publisher

**최신 판정: T6.6E3 COMPLETE — READY FOR INDEPENDENT IMPLEMENTATION AUDIT.**
I25 통합 교정 및 최종 회귀 결과는 27절이다. 독립 감사 PASS나 배포 승인은 아니다.

> 1–25절은 최초 미완료 구현 기록이며, 26절은 I25 교정 중간 기록이다.
> 이후 소유자가 additive pin 확장을 승인한 뒤의 구현·최종 결과는 27절에서 구분한다.

## 1. 현재 판정과 시작점

**T6.6E3 INCOMPLETE — TARGETED CORRECTION REQUIRED.**

권한 경계, 완전한 구조 검증, 동기 SQLite publication 및 process-crash 복구를
구현했다. 그러나 세션 중 accepted provenance를 증분 재사용하지 않고 전체 raw/index를
재검증하는 경로가 남는다. T6.6C §18/§23/§24/§35 및 I25의 steady-state 요구를
충족했다고 주장하지 않는다. 이는 계약 모순이나 소유자 결정 부재가 아니라 **E3 구현의
잔여 보완 1건**이다. E4/R1로 이 책임을 넘기거나 계약을 수정하지 않는다.

시작 commit은 `9a53b139cbb99d40020ba0635cf6b44730f3ca51`이다. 시작 시 branch는
`main`이고 HEAD/main/origin/main/실제 remote main이 모두 일치했으며 working tree는
clean이었다. `f66e4fb299524d84f7da2a64dea5d7b39651f3d5` 이후 diff는 문서 정리와
backend migration test의 문서 경로 docstring 변경이며 Flutter/backend runtime 변경은
없었다. 과거 독립 감사 보고서와 교정 이력을 수정하지 않았다.

## 2. authority 조사 결정과 단계 소유권

규범은 [T6.6C](t66/c/t66c-delta-sync-protocol.md)의 §10/11/18/19/22–26/34–36이다.
기존 AppState, coordinator, E1/E2 source와 독립 재감사 기록을 대조했다.

- AppState가 기존 `_lineageGeneration`, `_authenticationGeneration`, 선택 user/mode,
  `_refreshCoordinator`, `_lineageTail`과 최종 publication 권한을 계속 소유한다.
- E3는 구조 index/tree diff, 검증 association, segmented-internal publication만 맡는다.
- Pending/Offline/Legacy adapter와 B/J lineage handoff는 E4에 남긴다.
- large restore/MW, 실기기 복구 전제는 R1 및 후속 통합 gate에 남긴다.
- `sync_root`를 Snapshot v7 `state_fingerprint`로 사용하지 않는다. 부분 segmented
  state로 `AuthoritativeBaselineEnvelope`나 `OfflineBaseline`을 만들지 않는다.

새 coordinator, 독립 authorization token, persisted ticket의 권한 복원은 없다.
`publication:true`는 isolated schema 선택일 뿐 권한 boolean이 아니다.

## 3. 변경 source와 격리 profile

| source | 역할 |
| --- | --- |
| `mobile/lib/src/app_state.dart` | 명시 E3 오케스트레이션, 기존 guard 추출·공유 |
| `mobile/lib/src/segmented/verification.dart` | complete tree diff, F(raw), canonical Patricia 및 receipt |
| `mobile/lib/src/segmented/store.dart` | opt-in isolated v3 admission, exact schema/usage 검증 |
| `mobile/lib/src/segmented/store_publication.dart` | durable generation/pins/accepted, 동기 publisher와 복구 |
| `mobile/lib/src/authoritative_snapshot_validation.dart` | 기존 구조/identity 검사만 소비하는 segmented 입력 경계 |
| `scripts/benchmarks/t66e2_server.py` | 자기 소유 합성 DB의 bounded insertion/deletion oracle |

새 dependency, canonical encoder, hash domain, backend runtime 변경은 없다.
E1/E2 default schema와 기존 production SQLite user_version 4를 혼동하지 않는다.

## 4. AppState 오케스트레이션과 원래 ticket

`AppState.publishSegmentedForIsolatedUse`만 명시 호출점이다. 기본 startup에서 호출하지
않으며, ordinary ONLINE/선택 user/진행 중 financial write 없음이 초기 조건이다.
임의 mode bypass 인자를 제공하지 않는다.

선택 principal과 기존 coordinator의 ticket을 **acquisition 전에 한 번** 캡처한다.
기존 E2 `segmentedTransportForApi`와 `IncrementalFetcher.acquire`를 사용한 뒤 E3
검증·준비를 수행하고, 동일 ticket을 유지한 채 기존 `_withLineageLock`에 진입한다.
최종 storage fence는 AppState 소유의 동기 `requireAuthority` closure다.

기존 legacy refresh의 `requireInstallAuthority`와 E3가 `_requireRefreshAuthority`를
공유한다. 기존 user/auth/lineage/request/mode 비교 조건과 finalizing 허용 범위를
변경하지 않는다. E3에서는 finalizing 허용 인자를 사용하지 않는다.

## 5. session 전이와 최종 guard

`MoneyNoteApiClient.saveSession`은 AppState auth generation보다 먼저 `_sessionToken`을
바꿀 수 있다. 기존 E2 transport의 실제 credential getter와 `checkSession`을 재사용해
이 구간도 거부한다. 별도 credential store나 로그인 흐름은 만들지 않는다.

최종 fence 순서는 cancellation/disposed → 기존 AppState guard → 기존 session guard
→ AppState guard 재확인이다. session getter는 실제 구현에서 순수 조회다. 마지막
재확인은 test-controlled 동기 callback의 상태 변경도 놓치지 않기 위한 방어다.
remote credential revocation의 관측점은 E2의 terminal observation이며, offline cache
receipt가 미래 서버 authorization이라고 주장하지 않는다.

## 6. 실제 E1/E2 handoff와 identity

E2는 동일 authenticated manifest를 terminal 조회한 후 `graph_verified`를 기록하고
관측 release를 best effort 수행한다. E3는 이 명시 acquisition을 원래 ticket 아래에서
실행한다. release 뒤에도 bytes의 integrity evidence는 남지만 lease를 연장하거나
과거 observation을 새 권한으로 사용하지 않는다.

local UUIDv4 generation ID, server `sync_root`, observation ID/request ID, NS,
principal, Versions, revision, Context, accepted commit sequence를 구분한다. receipt에는
비밀이 아닌 owner와 원래 ticket의 lineage/authentication/request 숫자만 역사 증거로
저장한다. token/password는 저장하지 않는다. store만으로 AppState 권한을 제조하지 않는다.

## 7. complete index/tree diff

`diffRawTrees`는 11개 table의 old/new ordered descriptor frontier와 row cursor를
사용한다. 완전히 같은 descriptor/Ref는 내려가지 않는다. unequal internal node를
확장하고 PK 순서로 leaf rows를 merge한다. 한쪽 leaf가 끝나도 반대쪽 cursor를 보존해
split/merge/경계 이동을 삭제로 오인하지 않는다. 양쪽 frontier 소진과 bounded change
목록을 요구한다. exact C1 raw 값이 같은 이동 행은 mutation으로 세지 않는다.

`segmented_diff_integration_test.dart`는 실제 D2b가 만든 update, 260행 insertion 및
deletion, 무변경 generation을 사용한다. 기대 change 집합은 backend의 별도 직접 SQL
source에서 PK별로 비교한다. production diff가 만든 목록을 기대값으로 재사용하지 않는다.

## 8. F(raw)/index와 hot/raw

`rowFacts`/`buildRawFacts`는 `backend/isolated_sync/facts.py`의 PK/unique/ref/reverse/
allocation/context_reverse와 event count/sum, active batch, last_closed_month catalog를
구현한다. 구조 합계는 exact integer/BigInt이며 금융 projection을 재계산하지 않는다.

`canonicalFactsRoot`는 F(raw)로부터 fact-key digest, collision bucket의 exact C1 순서,
MSB prefix, maximal binary branching/count를 독립 구성한다. 다운로드 index의 root가
자기 자신을 증명하게 하지 않는다. 기대 root는 실제 backend의 Patricia root다.

base가 있으면 base도 검증하고 모든 old row facts를 먼저 제거한 다음 new facts를
넣는다. duplicate UNIQUE owner overwrite, old membership 불일치, target root 불일치를
거부한다. aggregate/context 전이는 검증한 target 구조 facts와 일치해야 한다.

`validateSegmentedRawProjection`은 full raw rows와 실제 hot/control만 받는다.
기존 `_relationships`, `_projectionIdentities`, `validateBundleProjectionStructure`,
정책 compatibility 및 settings/date/context 대응을 공유한다. 새로운 금융 계산 엔진이나
부분 Snapshot wrapper는 없다. E1의 원문 Unicode/monetary string 및 C1 검증은 그대로다.

## 9. durable manifest와 receipt

`CompleteGenerationProof`는 private constructor를 가진 data verification 결과다.
검증된 Target/manifest, complete graph, diff와 `segmented-e3/1` receipt를 묶는다.
receipt는 Target, base sync_root, sorted Ref 집합 digest, object/edge/fact 수,
changed-row/reused-subtree 수를 결합한다. receipt byte getter는 copy를 반환한다.
E2 `graph_verified` flag만으로 이를 구성할 수 없다.

`prepareGeneration`은 실제 durable staging manifest, graph_verified association,
expected base, context, proof와 모든 object Ref의 존재를 검사한다. immutable manifest,
receipt/checksum 및 모든 object pin을 transaction에 저장하고 readback한다.

checksum은 로컬 손상 탐지이지 서명이나 현재 authorization이 아니다.

## 10. opt-in SQLite v3

`SegmentedClientStore.open(..., publication:true)`만 isolated v3를 사용한다.
기존 v1/v2 exact schema/usage 검증 후 같은 `BEGIN IMMEDIATE` 안에서 승격한다.
default E1은 v1, acquisition-only E2는 v2이며 v3를 묵시 downgrade/repair하지 않는다.

추가 tables는 `generations`, `generation_objects`, singleton `accepted`다.
accepted에는 current/previous local UUID, sequence, namespace-bound checksum이 있다.
generation/Ref/pin의 immutable trigger, accepted/current previous 삭제 방지,
retained object 삭제 방지, usage charge를 exact DDL 검증에 포함한다.

E1-A02의 transaction-local schema 검증은 모든 E3 write에도 적용한다. `user_version`나
trigger 이름만 믿지 않는다. profile·metadata·object quotas도 유지한다.

## 11. 동기 publication과 no-await 경계

`commitPreparedGeneration`은 concrete 동기 API다. async transaction callback이나
다른 isolate에 COMMIT을 위임하지 않는다. PreparedGeneration은 생성한 store connection에
결합되어 reopen한 connection에서 재사용할 수 없다.

순서는 다음과 같다.

```text
BEGIN IMMEDIATE
exact schema / durable manifest / receipt / pins 검사
expected accepted ID + commit sequence 비교
검증 때의 connection-local PRAGMA data_version 비교
accepted current/previous/sequence/checksum 갱신 또는 idempotent 판정
quota 검사와 모든 pre-COMMIT fault hook
AppState final authority + session fence
동기 COMMIT
동기 accepted readback
```

최종 fence와 `COMMIT` 사이에는 await, hook, notification, isolate message가 없다.
실제 lock closure도 await 없이 이 API를 실행한다. sqlite3 3.7.0의
`lib/src/implementation/database.dart:287`에서 parameterless `execute`가 동기
`sqlite3_exec`를 사용함을 설치된 source로 확인했다. private connection에 Dart UDF,
custom busy/commit callback을 등록하지 않는다.

Dart는 `void Function()`에 async closure를 전달할 수 있으므로 `Future Function()`
runtime 형태도 거부한다. 이 검사는 임의 사용자 callback을 새로운 권한 체계로 만드는
장치가 아니다. 실제 publication fence의 권한은 기존 AppState에만 있다. tests의
noop fence는 storage primitive의 atomicity만 시험하며 AppState 권한 증거로 세지 않는다.

## 12. concurrency와 verification freshness

expected accepted ID/sequence는 expensive acquisition 전에 캡처한다. SQLite write
transaction 안에서 다시 비교하므로 다른 publisher가 먼저 결정한 pointer를 오래된
요청이 덮지 못한다. 이 CAS는 권한을 대신하지 않는다.

외부 connection의 COMMIT은 `PRAGMA data_version`으로 감지한다. 검증 전 counter를
prepare와 publication에서 비교하고, 다른 connection/reopen으로 proof를 이동하지
못하게 한다. counter는 해당 connection에서만 의미가 있으며 auth token이 아니다.
자기 connection의 공개 API는 immutable bytes를 바꾸거나 삭제하지 않는다.

DDL도 SQLite write이므로 BEGIN IMMEDIATE 이후 다른 connection의 schema 변경은
publication과 경합해 성공할 수 없다. final AppState/session guard는 cooperative
lineage lock과 별도로 반드시 실행한다. 모든 isolate/process의 AppState 권한을 하나의
lock으로 보호한다고 주장하지 않는다. 앱의 기존 단일 authority-owner isolate가 범위다.

E2의 isolate-local bounded acquisition admission을 유지한다. 더 새 E3 요청도 같은
coordinator에서 begin하므로 오래된 ticket이 무효화된다. 새 요청이 ACQUISITION_BUSY로
실패하더라도 오래된 요청에 권한을 되돌려 주지 않는다.

## 13. 오류·readback·rollback

SQLITE_BUSY/LOCKED, constraints, schema, quota, SQLITE_FULL 및 final guard 실패는
pre-COMMIT이면 rollback한다. rollback 자체의 실패가 원래 원인을 가리지 않는다.
COMMIT은 기존 busy timeout 동안 owning isolate를 동기 차단할 수 있다.

COMMIT 뒤 hook/readback 실패는 cause를 보존한 `PublicationCommittedException`이다.
AppState가 lineage-lock 결과를 await하는 사이 권한이 바뀐 경우에도 이미 커밋된 격리
namespace와 반환 권한 상실을 구분한다. 이 경우 성공 결과·UI 설치·pending 정리는 없다.
커밋 뒤 오류를 clean rollback이나 자동 이전 generation 복원으로 표현하지 않는다.

## 14. accepted recovery

`recoverAcceptedGeneration`은 current/previous pointer checksum·manifest·receipt를
검사하고 두 graph의 실제 bytes/F(raw)/index/hot 대응을 다시 검증한다. 실제 sorted
Ref set과 pins, object-set digest 및 object/edge/fact 수를 별도로 비교한다. current
receipt의 base sync_root는 previous Target과 일치해야 한다. 외부 COMMIT이나 pointer
변경이 관찰되면 검증을 성공으로 반환하지 않는다.

invalid current를 빈 데이터나 정상 legacy 성공으로 숨기지 않는다. explicit recovery가
실패하며 기본 legacy 경로는 원래대로 남는다. 이전 accepted authority를 묵시 재활성화하지
않는다. durable ticket 숫자로 새 publication을 허가하지 않는다.

## 15. pins와 최소 cleanup

prepared generation은 complete graph object들을 pin한다. accepted/previous 역할은
하나의 accepted row transaction으로 switch된다. immutable manifest/pins는 그 전에
durable/readback되므로 새 accepted pointer가 미완성 data를 가리키지 않는다.

staging cleanup은 accepted object bytes를 삭제하지 않는다. current/previous generation과
그 pins의 직접 삭제도 trigger가 막는다. 실패한 AppState 작업은 자신의 unaccepted
prepared record를 해제하고, accepted/previous는 해제하지 않는다.

explicit recovery는 검증된 current/previous 외의 prepared metadata를 제거한다.
이는 cooperative 단일 AppState owner의 conservative 정리이며 다른 live preparation은
실패/재시도할 수 있다. 여러 독립 authority owner의 무중단 publication을 보장하는
범용 GC가 아니다. immutable object sweep, E4 reader/frozen/J/artifact pin 설계,
whole-tree compaction은 구현하지 않는다. 손상으로 recovery가 실패하면 추측 삭제하지 않는다.

## 16. 실제 process-crash 증거

`segmented_publication_crash_test.dart`와 별도 Dart worker는 ready barrier 후 실제
SIGKILL을 사용한다. 예외 injection만으로 crash를 대체하지 않는다.

| 경계 | fresh reopen의 허용 결과 |
| --- | --- |
| before_transaction | complete G1, sequence 1 |
| after_generation_manifest | complete G1, sequence 1 |
| after_generation_pins | complete G1, sequence 1 |
| after_publication_begin | complete G1, sequence 1 |
| after_accepted_pointer | complete G1, sequence 1 |
| before_publication_commit | complete G1, sequence 1 |
| after_publication_commit | complete G2, sequence 2 |
| during_publication_readback | complete G2, sequence 2 |

새 connection으로 pointer/sequence, integrity_check, foreign_key_check, missing pinned
objects 0과 후속 write-lock 획득을 검사한다. fresh store에서도 graph/F(raw)를 검증한다.
이 증거는 process termination이며 Android 실기기 sudden power loss, OS crash,
손상 hardware의 fsync 보증으로 표현하지 않는다. DELETE/EXTRA/FK profile은 E1 그대로다.

## 17. 합성 테스트와 독립 oracle

- `segmented_publication_test.dart`: 실제 backend canonical fixture, 직접 SQLite
  committed pointer/pins/checksum/receipt, BUSY/FULL, async guard 거부, failure rollback.
- `segmented_authority_test.dart`: 실제 AppState/coordinator/API credential getter와
  actual synthetic D3a/D3b ASGI acquisition. logout/reauth/mutation/mode/newer refresh,
  credential-update gap 및 pre/post-COMMIT authority race를 검사한다.
- `segmented_diff_integration_test.dart`: backend 직접 SQL 기대 rows, 실제 canonical
  tree/Patricia roots, update/insert/delete/no-change 및 payload request 수를 비교한다.
- process-crash 8건은 별도 process 종료 및 fresh reopening을 사용한다.

Hash-valid negative index/hot fixture는 ancestor와 Target hash까지 갱신한다.
따라서 E2 closure를 통과한 representation도 E3 association 검사에서 거부되는지 검증한다.
receipt 손상 fixture는 checksum/usage/원래 trigger를 맞춰 schema 거부만으로 semantic
검증을 대체하지 않는다. 예상 object/edge/fact 수는 실제 graph에서 재계산한다.

## 18. legacy/B/J 격리

실제 AppState publication 전후 legacy baseline, pending marker, frozen journal 파일의
bytes를 비교한다. 기존 summary 객체 identity와 lastSuccessfulSyncAt도 유지한다.
E3는 pending을 synthesize/rebase/acknowledge/retire하지 않고 financial UI를 설치하지 않는다.

기존 E1의 모든 segmented import 금지 assertion은 승인된 AppState 단일 경계를
허용하도록 단계에 맞게 변경했다. 다른 lib 파일의 import 금지는 유지하고 AppState에서
store.open이 없으며 명시 E3 entry가 lib 안에서 호출되지 않는지 검사한다. 별도의 실제
default AppState 테스트도 segmented DB와 observation/object 요청 0을 확인한다.
이는 정상 startup/읽기/쓰기의 격리 요구를 제거한 변경이 아니다.

## 19. 제한된 HOST 측정

원본 단위와 재현 방법은 `docs/benchmarks/t66e3/`에 보존한다. 전체 회귀와 겹친
단일 HOST 표본이며 production throughput, device latency, median/p95가 아니다.

초기 260 archive 행을 포함한 294 raw rows/1,168 objects에서 시작해 260행을 추가·삭제한다.
무변경과 deletion에서 immutable payload 요청은 0이었다. tree diff 자체는 무변경에
raw root 2개만 읽고 table subtree 11개를 재사용했다. **그러나 이것은 전체 E3 local
검증이 O(1)이라는 증거가 아니다.**

publication transaction은 full graph 검증 후 schema/metadata/CAS/guard/COMMIT만
수행한다. 그래도 pin-count 등 metadata 작업은 generation 크기에 의존한다.
strict peak RSS나 최댓값 quota에서의 latency를 검증하지 않았다. current/previous graph
pins는 bounded quota로 계수하지만 메모리·저장 효율 gate가 완료된 것은 아니다.

## 20. 잔여 보완 — I25

원인은 다음 세 경로에서 명확하다.

1. `AppState.publishSegmentedForIsolatedUse`가 매번 full accepted recovery를 호출한다.
2. `verifyCompleteGeneration`이 target rows/F(raw)/Patricia를 모두 구성하며, base도
   재귀적으로 full 검증한다. session의 unchanged validated facts를 재사용하지 않는다.
3. `prepareGeneration`이 매번 complete per-object pins를 다시 저장한다.

full initial/restart 검증의 정확성은 입증했지만 이를 정상 incremental 전이에 반복하는
방식은 T6.6C §18/§24/§35 및 I25(MEDIUM)의 요구와 다르다. payload 0이나 빠른 frontier
diff를 근거로 이 차이를 숨기지 않는다. 자체 구현 점검의 **Medium 보완 1건**이며
독립 감사 finding이라고 부르지 않는다. 완료·push·독립 E3 감사 준비 판정을 보류한다.

최소 후속 순서는 다음과 같다.

1. connection/validator/NS/root 및 corruption freshness에 결합된 accepted verification
   provenance 재사용을 구현한다. persisted evidence를 AppState 권한으로 바꾸지 않는다.
2. 완전한 frontier diff의 old facts 제거/new facts 삽입과 affected reverse closure를
   persistent canonical Patricia에 증분 적용한다. changed hot의 raw 조회도 영향집합으로
   한정한다. initial/restart full oracle는 유지한다.
3. publication의 pin association과 metadata freshness를 whole-graph rewrite 없이
   유지한다. active/previous 보호와 rollback을 약화하지 않는다.
4. H/D 고정·N 증가에서 읽은 rows/검증 bytes/쓴 metadata를 계측해 I25를 검증하고
   authority/crash/full 회귀를 다시 실행한다.

이 보완은 E3 소유이며 E4/R1 구현이나 protocol amendment를 요구하는 것으로 돌리지 않는다.

## 21. 실제 회귀 실행

최종 source에 대한 전체 Flutter 실행은 **1,047 PASS / 0 FAIL / 기존 2 SKIP**,
8분 23초였다. 과거 baseline 결과를 새 실행 결과로 전용하지 않는다. 중간 실패도 보존한다.

| 검사 | 이번 실행 결과 |
| --- | --- |
| 새 E3 사례 | **64 PASS / 0 FAIL**: publication 36, AppState authority 19, process crash 8, diff/integration 1 |
| authority race subset | **13 PASS / 0 FAIL**: pre-COMMIT 6, acquisition 이후 5, newer segmented 1, post-COMMIT 1 |
| E3 실제 process termination | **8 PASS / 0 FAIL** |
| E1/E2 및 기존 AppState/Offline/Snapshot | 최종 full suite에서 PASS; 기존 E1 process-crash 7건 포함 |
| Flutter 전체 | **1,047 PASS / 0 FAIL / 2 SKIP** |
| Flutter analyze | **PASS**, No issues found |
| changed-file formatting | **PASS**, 11 files / 0 changed |
| Flutter debug APK build | **PASS**, build만 수행; 설치·배포 없음 |
| backend 전체 | **1,315 tests + 1,540 subtests PASS**, 1 warning, 1,599.46초 |
| Ruff / compileall / git diff --check | **PASS** |
| frontend npm build | **PASS** |

최종 Flutter log는 `/tmp/money-note-e3-flutter-verified.log`, backend log는
`/tmp/money-note-e3-backend.log`다. 이는 개발 checkout의 합성 실행이며 영구 보존 로그나
독립 감사 결과가 아니다. bounded 결과/측정은 `docs/benchmarks/t66e3/`에 남긴다.

- 첫 전체 Flutter 실행: 1,040 PASS / 1 FAIL / 2 SKIP. 기존 E1 static import assertion과
  승인된 AppState 경계의 충돌이었다. 18절의 경계 검사로 변경했다.
- 다음 실행: 1,045 PASS / 1 FAIL / 2 SKIP. 새 base receipt 손상 fixture가 usage를
  갱신하지 않아 semantic recovery 전에 STORE_METADATA_CORRUPT로 거부됐다. production
  validation을 완화하지 않고 합성 fixture만 독립 bookkeeping에 맞췄다.
- 구체적 오류 assertion 보강 중 logout 경합은 E2 release 뒤 AUTHENTICATION_CHANGED를 전달하는
  AcquisitionFailure였다. 임의 Exception 허용 대신 이 실제 auth code와 기존 AppState
  stale-authority 오류만 기대하도록 수정했다.
- backend 전체는 이번 세션에서 **1,315 tests + 1,540 subtests PASS**, warning 1,
  1,599.46초였다. backend runtime source는 변경하지 않았다.
- frontend npm build, debug APK build, Ruff, compileall은 실행하여 통과했다.
  APK를 설치·배포하지 않았다.

## 22. 지원 범위와 남은 제한

E1의 Monetary A01/BOM/raw preservation/C1, E1-A02 schema integrity와 E2-A01 cleanup
구현을 변경하지 않았다. 해당 기존 회귀는 full suite에 포함한다. 기존 AppState race,
OfflineBaseline v4, frozen B/J, Snapshot v7 회귀도 그대로 실행한다.

세션별 provenance/증분 비용 보완 외에도 integrated scaling, 실제 Android power-loss,
E4 Pending/Offline/Legacy/B/J handoff, R1 large restore/MW와 일반 사용자 activation은
미구현/미검증이다. 이 보고서는 independent E3 audit PASS나 production readiness가 아니다.
기존 불변 파일의 formatting 차이는 일괄 수정하지 않는다.

## 23. 운영 안전

backend/Flutter 테스트는 새 temporary synthetic DB/store와 mock/ASGI pipe만 사용했다.
production DB/API/credential/service/backup에는 접근하지 않았다. production migration,
배포, service restart, APK 설치, segmented endpoint/일반 사용자 activation은 하지 않았다.
기본 Flutter 재무 read/write·startup·UI와 backend runtime 설정은 불변이다.

## 24. commit/push

완료 gate 미충족으로 **commit/push하지 않았다**. 작업 파일은 이 시작 commit 위에
보존한다. 사용자 변경을 reset/삭제하지 않았다. 시작 HEAD/main/origin/main/실제 remote
main의 일치는 확인했지만 구현 미완료 working tree를 clean이라고 주장하지 않는다.

## 25. 다음 행동

I25의 accepted provenance 재사용과 증분 index/pin publication 비용을 보완한 뒤,
full 회귀와 독립 E3 구현 감사 준비 판정을 다시 수행한다. E4/R1은 시작하지 않는다.

## 26. I25 TARGETED CORRECTION — 별도 교정 이력

### 26.1 시작 상태와 현재 판정

이 절은 앞선 INCOMPLETE 이력을 지우지 않는 2026-10-13 추가 기록이다. 시작 committed
HEAD/main/origin/main/실제 remote main은 모두
`9a53b139cbb99d40020ba0635cf6b44730f3ca51`이었다. working tree는 원래 E3 source,
tests, fixtures, 보고서와 측정을 포함한 **의도된 dirty 상태**였다. staged 변경은 없었다.
이를 clean baseline으로 되돌리지 않았으며 기존 구현을 새로 작성하지 않았다.

**T6.6E3 INCOMPLETE — I25 CORRECTION STILL REQUIRED.** 원래 비용 문제는 재현했고,
증분 검증기의 독립 full-oracle 일치를 확인했다. 그러나 실제 AppState publisher의
session-bound recovery/provenance 재사용과 root 기반 pin 확장은 아직 연결하지 않았다.
검증기 단독 비용 개선이나 기존 안전 회귀 PASS를 전체 I25 완료로 바꾸지 않는다.

원래 작업은 별도 `/tmp/money-note-e3-i25-before.Pa37tN/worktree.tgz`와 tracked patch로
보존했다. 영구 측정용 작은 source snapshot은 `docs/benchmarks/t66e3/i25-before-worktree.tgz`
다. 원래 E3 authority/publication/crash/diff tests, crash worker, E1 store test 및 backend
fixture script 7개는 시작 snapshot과 byte 비교해 이번 교정에서 변경하지 않았음을 확인했다.
원래 publisher에는 측정 counter만 추가했으며 final guard/COMMIT·retention 정책은 불변이다.

### 26.2 binding 요구와 비용 귀속

규범은 T6.6C §18/§23/§24/§35와 **I25(MEDIUM): steady-state full N 작업 MUST NOT**다.
조건을 충족하는 정상 세션은 `O(H + changed bytes + L log P + 256E)`의 hot·변경 byte·
touched path·변경 fact 작업을 사용한다. initial/restart/schema-invalid/full recovery의
O(N) 예외를 모든 정상 publication에 적용할 수 없다. §25 최종 권한 검사는 매번 필요하다.

| 현재 연산 | 반복 불필요 작업 | 실제 원인 | 최소 교정 방향 | 보존할 불변식 |
| --- | --- | --- | --- | --- |
| AppState recovery | current/previous 전체 재검증 | 매 호출 `recoverAcceptedGeneration` | 검증된 connection/session frame 재사용, 외부 변경·불확실성 때 무효화 | startup/full recovery·fail-closed |
| complete verifier | raw rows/F(raw)/Patricia 및 base 재귀 재구성 | full routine만 연결됨 | accepted data proof + complete tree diff + canonical path edit | 정확한 old/new membership·F(raw)/index·hot/raw |
| generation prepare | 새 UUID마다 전체 pin association 복사 | `generation_objects` per-object INSERT loop | 기존 pin을 보존하는 opt-in root relation와 자손 보호 | current/previous closure·atomic pointer/pins |

교정 전 별도 test는 cold, identical, 세 번의 한 행 변경, reopen, 그 후 반복, 실패,
retry를 크기별로 실행했다. 190/1,168 objects의 identical에서 각각 객체 1,742/10,548회,
full raw rows 150/882행, pin INSERT 190/1,168회를 관측했다. 세 번째 한 행 변경도
recovery가 current/previous 380/2,336 objects를 검사했다. 원본 JSON과 세부 표는
`docs/benchmarks/t66e3/i25-before.json` 및 README에 보존한다.

pin의 원래 accepted association을 같은 generation에서 DELETE/INSERT한 것은 아니다.
새 local generation 준비 때 전체 association을 복사하는 비용이다. 이 차이를 유지한다.
pin DELETE/UPDATE, 모든 SQL statement, recovery metadata row의 완전 계수와 peak RSS는
아직 없다. 누락된 counter를 0으로 보고하지 않는다.

### 26.3 이번 source 변경과 독립 검증

| source | 이번 변경 |
| --- | --- |
| `segmented/work.dart` | callback·권한 기능이 없는 실제 작업 counter |
| `segmented/store.dart`, `store_publication.dart` | 성공한 verified object read/bytes, transaction attempt, recovery/pin INSERT/metadata API counter |
| `segmented/graph.dart` | typed subtree의 compact summary와 선택적 integrity provenance, lazy complete Ref enumeration |
| `segmented/verification.dart` | target row의 leaf 위치, private raw/fact catalogue, 기존 complete oracle 유지 |
| `segmented/patricia_edit.dart` | 기존 C1/hash를 사용한 canonical Patricia path-copy insert/delete/collapse |
| `segmented/incremental_verification.dart` | complete frontier diff와 변경 fact/aggregate/context 전이, affected relation closure·hot/raw 검사 |
| `authoritative_snapshot_validation.dart` | 기존 segmented helper의 relation/hot 검사를 분리해 공유; legacy validator 불변 |
| `app_state.dart` | 기존 full verifier에 측정기 전달만 추가; authority·ticket·orchestration 불변 |

data integrity provenance, durable accepted provenance, 현재 AppState authority는 별개다.
이번 standalone private catalogue는 검증한 graph/rows/facts/leaf 위치와 동일 Target을
결합한다. 새 proof의 data delta는 accepted 후에만 채택할 목적으로 분리했다. 후속 proof
채택 뒤 예전 base proof를 재사용하면 identity mismatch로 거부한다. 이 private data model을
아직 store의 accepted 상태에 연결하지 않았다. 현재 세션 권한을 cache하지 않는다.

증분 검증은 old facts를 모두 제거한 뒤 new facts를 추가하고, canonical index를 touched
path만 편집해 실제 server index root와 비교한다. unique owner 충돌, exact old membership,
event count/sum, active batch, context facts를 유지한다. projection 금융 계산을 새로
구현하지 않았다. 기존 `_relationships`/projection identity 검사를 필요한 영향집합에
적용하며 hot이 참조하는 raw leaf는 실제 bytes를 hash-on-read한다.

typed subtree summary는 shape/range/count와 context를 결합하며 금융 payload를 저장하지
않는다. 같거나 재사용 가능한 tree region을 identity로 건너뛰더라도 target parent의
descriptor/typed relationship을 검사한다. complete graph Ref 목록은 lazy enumeration이며
full oracle와 retention 유지 작업에서 필요할 때만 전체 순회한다.

receipt `/2`는 root와 object/edge count association이고 기존 `/1`의 sorted full Ref
digest와 의미가 다르다. 기존 `/1` 의미를 바꾸지 않았고 v3 publisher는 `/2`를 허용하지
않는다. 이로 인해 standalone verifier 성공을 accepted publication으로 가장할 수 없다.

### 26.4 provenance 유효성 경계 — 아직 필요한 연결

최종 integration은 owning store/connection, namespace(origin/principal/dataset/epoch),
Versions/validator, accepted local UUID/previous/sequence/checksum, manifest/receipt, complete
pins와 full recovery 완료 증거를 결합해야 한다. 이 연결은 현재 미구현이다.

재사용을 금지할 조건은 다음과 같다.

- reopen/restart 또는 incomplete recovery, store/profile identity 불일치;
- 외부 COMMIT의 connection-local `PRAGMA data_version` 변화, unexpected pointer/sequence;
- schema/mandatory trigger·receipt·pins 불일치, missing/corrupt object 관측;
- dataset/epoch/principal/origin/namespace/Versions 불일치, malformed typed graph;
- uncertain COMMIT/readback 또는 accepted 상태의 완전성을 확정할 수 없는 오류.

이 경우 complete recovery/verification 또는 fail-closed가 필요하다. target download의
단순 timeout이 accepted bytes corruption을 의미하지는 않는다. 성공한 자기 connection의
immutable insert와 schema/accepted 변경을 구분해야 한다. `recovered=true` 같은 영구
boolean, persisted ticket 또는 이전 session guard로 권한을 복원하지 않는다.

§24처럼 읽지 않은 임의 bitrot를 즉시 발견한다고 약속하지 않는다. 실제 hash-on-read와
scrub에서 오류가 관측되면 data proof 재사용을 중단해야 한다. 현재 standalone corruption
test는 읽는 reused raw bytes가 손상되면 거부됨을 확인하며 전체 store cache invalidation
증거는 아니다.

### 26.5 pin extension과 도구 안전 경계

기존 v3의 per-object pin/receipt/보호 trigger는 그대로 남아 있다. 실제 root pin table,
schema version 변경, cleanup 알고리즘 교정은 적용하지 않았다. 도구 안전 검토에서 해당
retention schema/cleanup 범위의 별도 승인을 요구했으며, 삭제 대상을 넓히거나 기존
trigger를 DROP하는 방법으로 우회하지 않았다. 적용 도중의 불완전한 자체 migration
편집만 원래 시작 상태로 되돌렸고 사용자 E3 파일을 삭제하지 않았다.

제안하는 최소 범위는 기존 v3 table/trigger/pin을 보존하는 additive opt-in root 관계,
reachable object 및 edge 삭제 방지, current/previous 보존 정책 유지다. object GC·금융행
삭제는 포함하지 않는다. 기존 cleanup의 current/previous 제외 조건도 유지한다. 이 정확한
범위에 대한 확인을 요청했다. 이는 T6.6C 계약 모순이라고 보고하지 않는다.

독립 in-memory SQLite 모델 2건은 shared descendants, current/previous, 정확한 obsolete
generation, pointer 전이 COMMIT/ROLLBACK 및 retained edge/object 삭제 거부를 검증한다.
이는 새로 만든 합성 모델만 변경하며 실제 schema migration이나 publisher pin cost가
통과했다는 증거는 아니다. 원래 E3 file-backed pin/crash 회귀도 계속 유지한다.

### 26.6 측정 결과와 독립 complete oracle

`segmented_incremental_verification_test.dart`는 backend가 생성한 190/1,168/4,130-object
graph에서 동일·한 행 변경·8행 추가·삭제·반복 변경을 시험한다. 기존 full verifier에는
재사용 cache를 주지 않고 target roots, counts, diff, 전체 required Ref 집합을 비교한다.
oracle의 전체 enumeration은 측정 구간 밖에서 수행한다.

| graph objects | identical reads / index nodes | 한 행 변경 reads / index nodes | hot/raw rows |
| --- | --- | --- | --- |
| 190 | 9 / 2 | 45 / 28 | 4 |
| 1,168 | 9 / 2 | 65 / 42 | 4 |
| 4,130 | 9 / 2 | 67 / 44 | 4 |

큰 두 graph에서 changed graph node는 16개, tree frontier는 6개, changed facts는
4개였다. identical의 verified bytes는 25,171/164,737/164,742로 leaf 크기 차이가 있다.
단순 read 수만으로 byte 비용이 모든 크기에서 상수라고 주장하지 않는다.

hash-valid F(raw)/index 불일치와 hot/raw 불일치는 full/증분 verifier 양쪽이 거부한다.
reused hot-referenced raw corruption도 거부한다. 그러나 **실제 publisher의 반복 recovery,
pin writes와 전체 before/after matrix는 아직 개선되지 않았다.** I25의 통합 비용 gate는
미완료이며 이 표는 독립 알고리즘 검증 및 제한된 scaling 증거다.

### 26.7 이번 회귀 실행과 아직 실행 중인 검사

아래 수치는 이전 1,047 PASS 결과를 재사용한 것이 아니라 이번 교정 source 실행이다.

| 검사 | 이번 결과 |
| --- | --- |
| 교정 전 baseline 재현 | 1 PASS, 크기별 9개 표본; 실제 full recovery/full pin INSERT 재현 |
| 새 증분 verifier | 6 PASS, 크기별 full oracle 및 hash-valid negative/corruption |
| 독립 root pin SQLite 모델 | 2 PASS; 실제 publisher integration은 미검증 |
| 기존 E3 전체 | 64 PASS, authority race subset 13 및 실제 child-process crash 8 포함 |
| 전체 Flutter | 1,056 PASS / 0 FAIL / 기존 2 SKIP, 9분 56초 |
| E1/E2·A01/A02·HTTP cleanup·AppState·OfflineBaseline/B/J/Snapshot | 전체 suite에서 기존 회귀 PASS |
| Flutter analyze | PASS, No issues found |
| Flutter debug APK build | PASS, 설치·배포 없음 |
| frontend npm build | PASS |
| Ruff / compileall | PASS |
| backend 전체 | 첫 실행은 완료 결과 없이 중단; 별도 전체 rerun 결과 대기 |
| 최종 changed-file formatting / diff check | 문서 갱신 뒤 최종 재확인 대기 |

원본 실행 log는 `/tmp/money-note-i25-{core-verified,e3-regression,flutter-full,analyze-verified,build}.log`
다. backend 첫 log는 약 51% 진행 후 완료/실패 summary 없이 중단되어 PASS로 세지 않는다.
재실행은 `/tmp/money-note-i25-backend-full-rerun.log`이며 최종 결과만 아래 보완 기록으로
추가한다. 이전 도구 승인 심사의 사용량 제한으로 실행되지 않은 명령도 PASS로 세지 않았다.

원래 actual process-crash 8건은 전부 다시 실행했다. 새 persistence 경계를 연결하지
않았으므로 새 root-pin publication crash 보증은 없다. hardware/OS power-loss durability,
최대 quota에서의 동기 latency나 peak memory도 새로 입증하지 않았다.

### 26.8 권한·격리·잔여 gate

최종 AppState authority/session fence와 native `COMMIT` 사이에는 추가 hook/await/notification이
없다. 원래 ticket·lineage lock·accepted base/sequence/data_version fence·post-COMMIT 오류
구분은 불변이며 원래 authority/crash 회귀로 다시 확인했다. 새 proof·counter는 권한이 아니다.

Snapshot v7, OfflineBaseline v4, frozen B/J, pending ack/retirement/rebase, production schema,
financial UI 및 정상 read/write·startup 경로는 변경하지 않았다. E4/R1은 구현하지 않았고
production DB/API/credentials/services에 접근하지 않았다. build만 수행했고 APK 설치,
배포, segmented sync activation은 하지 않았다.

잔여 I25 보완은 **하나의 통합 미완료 문제**다: 검증된 accepted session provenance를 실제
E2/E3 경로에 안전하게 연결하고, 호환 schema의 증분 pins·recovery invalidation·동시성·crash·
전체 작업 counter로 완료 gate를 입증해야 한다. 단독 verifier 테스트나 도구 제한을 이유로
검증·권한 불변식을 완화하지 않았다.

완료 전용 정책에 따라 **commit/push하지 않았다**. 모든 기존 및 새 작업은 보존한다.
독립 E3 구현 감사 준비 판정은 NO이며 E4/R1·배포를 시작할 수 없다.

## 27. I25 승인 후 통합 교정

### 27.1 범위 승인과 구현 연결

소유자는 기존 v3 pin·receipt·보호 trigger를 보존하고, 새 generation에 root 관계와
자손 보호 제약을 추가하는 최소 opt-in 확장을 명시 승인했다. current/previous 보존 정책,
기존 cleanup 제외 조건을 유지하며 객체 GC·금융 데이터 삭제는 추가하지 않는 범위다.
앞선 도구 제한은 이 승인 뒤 해소됐으며 26절의 미연결 상태는 아래 source로 보완했다.
원래 incomplete 이력과 before artifact는 삭제하거나 최신 수치로 덮어쓰지 않았다.

`AppState.publishSegmentedForIsolatedUse`는 원래 ticket을 acquisition 전에 한 번만
발급한다. 같은 authority 아래 store recovery, E2 acquisition, store-owned candidate
검증과 준비를 실행한다. `IncrementalFetcher.acquire(verifiedBase: expected)`는 private
recovered store가 제공하는 data provenance만 재사용한다. 기본 E2 호출은 계속 전체
graph closure를 검증한다. server terminal manifest/auth/session/release 의미는 불변이다.

### 27.2 실제 provenance 및 무효화

`store_publication.dart`의 private `_AcceptedSession`은 owning connection의 실제 accepted
reference, complete proof와 `PRAGMA data_version`을 결합한다. `_reusableSession`은 매번
정확한 schema/mandatory trigger, profile discriminator/namespace/validator, connection
counter와 catalogue Target identity를 검사한다. 새 store handle이나 process에는 cache가
없으며 complete recovery부터 시작한다. Store path를 열어 본다는 사실이나 boolean만으로
data proof를 만들지 않는다.

owning connection의 공개 API는 immutable object bytes/refs/edges를 변경하지 않는다.
다른 connection의 실제 COMMIT, 새 accepted sequence, schema/profile 손상, read/scrub에서
관측한 missing/corrupt bytes, transaction 오류와 불확실한 post-COMMIT/readback은 frame을
폐기한다. unrelated network 실패만으로 accepted bytes를 손상으로 단정하지 않는다.
읽지 않은 bitrot의 즉시 탐지는 §24와 같이 약속하지 않는다. SQLite 파일은 E1의 app-private
소유 경로이며 임의 OS-level 교체에 대한 새 보안 보증이나 production GC admission은 아니다.

`verifyPublicationCandidate`는 manifest의 cache namespace/origin-bound principal/epoch/
Versions와 expected base를 검사한다. frame이 유효하면 증분 검증, 아니면 기존 complete
검증을 사용한다. 결과의 connection/expected base/sequence/data_version association은
private weak-key `Expando`에 둔다. 외부 memory loader로 만든 `/2` proof를 store에 전달해
root 4개만 pin하는 우회는 `VERIFICATION_CONNECTION_REQUIRED`로 거부한다. 이 association은
**data verification의 연결**이지 authorization token이나 guard 대체가 아니다.

현재 AppState ticket/user/auth/mutation/mode 및 transport session 검사는 절대 cache하지
않는다. persisted authority_history 숫자는 역사 metadata일 뿐 새 publication 권한이 아니다.

### 27.3 incremental index와 완전 fallback

accepted catalogue의 canonical facts/PK/reverse/context index를 기반으로 complete ordered
tree diff를 구한다. 동일 typed descriptor는 재사용하고 변경 leaf 및 ancestor 관계를 검증한다.
old facts 전체 제거 → new facts 추가 → 영향 aggregate/context 전이 → canonical Patricia
path-copy edit 순서를 사용한다. 실제 server target root와 같아야 한다. 필요한 relation
reverse closure와 hot/raw row는 기존 구조 검사·실제 hash-on-read를 계속 수행한다.
변경되지 않은 graph integrity summary는 payload나 금융 계산 결과를 새로 해석하지 않는다.

proof를 채택할 때 private delta와 새 leaf 위치만 반영한다. 오래된 empty-delta proof가
catalogue identity를 되돌리는 경로도 거부한다. 초기·restart·invalid provenance의 full oracle는
보존했다. recovery는 current와 previous의 실제 complete graph/F(raw)/hot 대응, durable
receipt·pin closure를 재계산한다. 최적화에 필요한 증거를 다시 확정하지 못하면 fail-closed다.

### 27.4 additive isolated schema v4와 pins

이 v4는 **`segmented-store/1`의 명시 publication profile**이며 production SQLite
user_version 4와 무관하다. 기본 E1 v1/E2 v2는 변경하지 않는다. 기존 v3를 exact DDL·usage로
검증한 같은 write transaction에서 additive `generation_roots`와 추가 보호 trigger를 만든다.
기존 `generation_objects`, `/1` receipt, 모든 기존 protective DDL과 pin rows를 보존한다.
손상된 v3를 repair하지 않는다.

새 `/2` receipt는 검증된 전체 Target roots/object count/edge count association이다.
기존 `/1` sorted full Ref digest를 다른 의미로 해석하지 않는다. full cold verifier도 store-owned
검증을 마친 뒤 이 별도 association으로 root pin 준비를 할 수 있다. 기존 direct full-proof
API의 `/1` 경로는 호환 유지하며 정상 AppState publication은 `/2`를 사용한다.

`generation_roots`는 각 generation의 4개 transferable roots를 objects에 FK로 결합한다.
object와 edge DELETE에는 validated edges를 따라 모든 자손을 보호하는 추가 trigger가 있다.
root relation의 UPDATE/직접 DELETE와 edge UPDATE도 금지한다. 재귀 reachability 작업은
명시 DELETE maintenance에서만 발생하며 보통 INSERT/COMMIT에는 없다. object sweep은 없다.

새 준비는 root pin 4개만 INSERT한다. 공유 descendant는 bytes를 복사하거나 pin set을
전개하지 않아도 current/previous의 root closure로 보호된다. pointer 전이와 요구 pin은
동일 DB의 durable 준비·최종 transaction/readback으로 결합한다. 실패한 준비의 root pins는
transaction rollback 또는 기존 unaccepted-only 정리로 해제한다.

cleanup의 SQL 범위는 원래와 동일한 `id IS NOT current AND id IS NOT previous`다.
각 삭제 API도 실제 accepted row를 재검사하고 보호 trigger가 이중 방어한다. 새 object GC나
별도 generation 보관 기간/개수를 발명하지 않았다. 정상 publisher에는 current/previous와
다음 정리 전 superseded 1개까지 최대 12 root rows가 남는다. 준비 중에는 일시적으로 4개가
더 생길 수 있다. 다른 live 준비는 원래 cooperative cleanup처럼 실패/재시도할 수 있다.

기존 v3 full pin을 보존한 store의 최초 승격·검증·마지막 old association retirement는
one-time migration/maintenance 비용일 수 있다. 정상 새 `/2` 반복 갱신의 O(N) rewrite로
숨기지 않는다. 수동 API의 누적 staging/preparation은 기존 metadata quota로 제한되며
E4의 범용 cache GC/reader lifecycle은 구현하지 않았다.

### 27.5 authority/COMMIT·CAS·오류 보존

final critical section은 기존 AppState lineage owner와 동일 isolate에서 실행한다.
BEGIN IMMEDIATE → exact schema/profile/receipt/pins → expected accepted ID/sequence와
data_version → metadata/quota/pre-COMMIT hooks → 실제 AppState/session fence → 즉시
동기 COMMIT 순서다. 마지막 guard와 COMMIT 사이 await/callback/notification은 추가하지
않았다. private SQLite connection에는 reentrant user-defined SQL callback을 등록하지 않는다.

readback은 cache pointer를 반환하지 않고 실제 accepted/manifest/receipt row를 다시 읽는다.
unchanged session에서 이미 검증한 이전 pins에 불필요한 COUNT scan을 하지 않는다.
새 `/2` 준비의 pin 검사는 indexed root 관계 4개다. COMMIT/readback 성공 후에만 proof delta와
session frame을 채택한다. guard/COMMIT 실패는 rollback하며 frame을 폐기한다. COMMIT 후
오류는 원래 cause를 가진 `PublicationCommittedException`이고 clean rollback으로 보고하지
않는다. 이후에는 full recovery가 필요하다.

readback의 마지막 data_version도 검증 때의 값과 같아야 한다. owning COMMIT 자체는 이
connection counter를 바꾸지 않는다. frame에는 새로 관측한 counter가 아니라 원래 검증
counter를 저장한다. 외부 post-COMMIT write/corruption 뒤 이전 proof에 새 stamp를 부여하는
경합은 두 개의 결정적 추가 시험으로 차단한다. 이후 외부 변경이 발생해도 다음 재사용
검사에서 원래 counter와 다르므로 frame이 폐기된다.

### 27.6 추가 oracle와 process-crash

`segmented_i25_publication_test.dart`는 실제 backend-generated graph 3개 크기로 11개
scenario를 실행한다. 시간만 보지 않고 실제 store/verification/pin SQL counter를 기록한다.
각 target을 별도 complete verifier로 재구성하고, 독립 SQLite recursive query로 current와
previous의 실제 pin closure를 server fixture object set과 비교한다. pin lookup의 실제
EXPLAIN QUERY PLAN도 기록한다. 전체 graph oracle는 측정 구간 밖이다.

추가 사례는 healthy 반복 recovery, fresh handle, 실제 외부 staging COMMIT, additive v3
승격/DDL·receipt·pin 보존, 외부 proof 우회 거부, dataset/epoch/principal/version, 경쟁
publication, newly reachable missing descendant, pre/post-COMMIT 오류·재복구, mandatory
trigger 누락과 receipt/index-object/profile/pin 손상, staging cleanup 및 retained object/edge
삭제 거부를 검사한다. AppState 원래 authority race는 같은 실제 owner/API를 사용한다.

원래 child-process crash 8개 경계는 유지하고 동일 8개를 `/2` root-pin publication으로
추가했다. fresh process와 독립 SQLite에서 complete G1/G2, sequence, object set closure,
4개 root pins, FK/integrity 및 재획득 가능한 write lock을 검사한다. 기존 `/1` process
경로도 그대로 남는다. power-loss/실기기 fsync 보증을 새로 주장하지 않는다.

### 27.7 중간 실패와 수정한 시험 전제

첫 통합 회귀의 두 실패는 숨기지 않는다.

1. 외부 변경 oracle의 `UPDATE accepted SET sequence=sequence`는 이번 SQLite에서 실제
   data_version 변화가 없었다. 실제 valid staging row를 다른 connection에서 COMMIT하도록
   수정해 외부 저장 변경을 확실히 만들었다. production version 검사를 완화하지 않았다.
2. post-COMMIT authority loss 시험이 legacy `generation_objects` non-empty만 요구해 새
   root representation을 거부했다. actual accepted root 4개와 전체 retained closure가
   독립 backend object set과 정확히 같은지로 보강했다. 보존되어야 할 pin 증거 검사를
   삭제하거나 단순 exception 성공으로 바꾸지 않았다.

backend 첫 재실행은 1,315 tests PASS·1,536 subtests PASS·4 subtests FAIL이었다.
실패는 기존 cash-fixed process-kill child의 `ModuleNotFoundError: No module named 'app'`다.
root cwd의 pytest 수집 경로만으로 child import가 설정되지 않았다. backend 구현·테스트를
바꾸지 않고 절대 `PYTHONPATH`를 명시했다. 별도 해당 file 재실행은 12 tests + 17 subtests
PASS였다. 전체 backend는 같은 올바른 환경에서 재실행하며 결과를 아래에 기록한다.

### 27.8 최종 결과 및 commit/push

최종 source의 전체 Flutter 실행은 **1,094 PASS / 0 FAIL / 기존 2 SKIP**, 15분 47초다.
이전 26절의 1,056 PASS를 재사용하지 않는다. 최종 post-COMMIT fence까지 포함한다.

| 검사 | 이번 최종 실행 |
| --- | --- |
| 기존 E3 사례 | 64 PASS, 원래 case를 제거하지 않음 |
| 새 I25 사례 | 47 PASS: baseline 1, verifier 6, 독립 pin 모델 2, 실제 publication 30, 추가 process crash 8 |
| E3 authority race subset | 13 PASS; 전체 AppState E3 authority 19 PASS |
| 실제 E3 process-crash | 16 PASS: 기존 `/1` 8 + 새 `/2` 8 |
| 최종 post-COMMIT seam 별도 재현 | 2 PASS, full suite에도 포함 |
| 전체 Flutter | 1,094 PASS / 0 FAIL / 2 SKIP |
| E1/E2·E1-A01/A02·E2-A01·기존 AppState·B/J·Baseline·Snapshot | full suite PASS |
| Flutter analyze | PASS, No issues found |
| Flutter debug APK build | PASS, 설치/배포 없음 |
| frontend npm build | PASS |
| changed-file format / Ruff / compileall / diff check | PASS; 마지막 문서 갱신 뒤 diff 재확인 |
| backend 전체 | **1,315 tests + 1,540 subtests PASS**, warning 1, 1,590.01초 |

log는 `/tmp/money-note-i25-flutter-final-verified.log`,
`/tmp/money-note-i25-{analyze,build}-final-verified.log`다. 최종 measurements의 33개 표본은
`docs/benchmarks/t66e3/i25-publication-after.json`에 보존했다. checksum은
`4760a0c5c63487c15f50c0fcfab84efc84d39c1de91cb4cd334851210cec31b4`다.

| graph objects | identical reads 전→후 | identical full raw rows 전→후 | pin INSERT 전→후 | 한 행 변경 reads / index nodes 후 |
| --- | --- | --- | --- | --- |
| 190 | 1,742 → 9 | 150 → 0 | 190 → 4 | 59 / 28 |
| 1,168 | 10,548 → 9 | 882 → 0 | 1,168 → 4 | 85 / 42 |
| 4,130 | 교정 전 미측정 → 9 | 교정 전 미측정 → 0 | 교정 전 미측정 → 4 | 87 / 44 |

정상 identical/작은 변경의 full recovery와 full verification은 모두 0회다. 성공 publication의
actual accepted metadata read는 크기와 무관하게 7회, rollback은 6회였다. 이는 실제 pointer/
receipt read를 생략한 성능 개선이 아니다. root pin query plan은
`SEARCH generation_roots USING PRIMARY KEY (generation_id=?)`였다.

4,130-object 단일 HOST 표본의 cold acquisition/publication은 237.359초, complete verification
3.159초였다. 많은 최초 object transaction과 합성 fixture 전송이 포함된 비용을 숨기지 않는다.
동일 target은 전체 236.514ms / verification 73.287ms / critical 4.437ms / readback 1.464ms,
한 행 변경은 전체 1,544.394ms / verification 164.813ms / critical 28.430ms였다.
restart의 recovery는 6,487.663ms 및 8,260 retained objects 검사였다. 그 직후 정상 반복은
full recovery 없이 객체 9개만 읽었다. 33개 표본에서 관측한 critical 구간은 4.437–48.514ms다.
median/p95, 최대 busy timeout, Android device latency나 production throughput 보증이 아니다.

hot/raw는 4행, tree frontier는 큰 두 graph의 한 행 변경에서 6개, changed facts는 4개였다.
1,168→4,130 objects 증가에도 reads 85→87 / index nodes 42→44이며, unchanged graph 전체를
순회하지 않았다. byte 비용은 bounded leaf 크기에 의존하며 작은 graph와 큰 graph가 완전히
같은 byte 수를 읽는다고 주장하지 않는다. §35의 H에는 required settings/control 작업도
포함하고 E에는 영향을 받는 reverse/constraint closure를 포함한다.

cold/restart 표본의 timer/counter는 store open 뒤부터 시작한다. open의 quick/FK/usage scan은
기존 E1 startup O(N)이며 위 recovery counter에 포함되지 않는다. 전체 SQL statement 수나
모든 startup metadata row를 완전 계측했다고 주장하지 않는다. 실제 root query plan, issued
pin SQL 및 independent persisted closure를 함께 사용한다. 원래 `summary.json`/before
snapshot은 그대로 보존했다.

backend 실행 이력도 구분한다. root cwd의 잘못된 child import 환경 실행은 4 subtests FAIL,
수정된 환경의 다음 전체 실행은 **1,314 tests PASS / 1 FAIL / 1,540 subtests PASS**,
2,383.96초였다. 후자의 실패는 `test_bounded_concurrent_quota_and_same_request_status`에서
기대 `[201,201,201,201,429]` 대신 `[201,201,201,201,503]`을 받은 것이다. 기존 E2 독립 감사
23절에도 동일 case가 기록돼 있으나 이번 실패의 원인을 E3나 부하로 단정하지 않는다.
동일 source/환경의 분리 실행은 1 PASS, 4.12초였다. assertion이나 backend를 수정하지 않았고
최종 전체 재실행은 `/tmp/money-note-i25-backend-final-verified.log`에 기록했으며
**1,315 PASS + 1,540 subtests PASS**, warning 1, 1,590.01초였다. 경고는 기존
Starlette TestClient/httpx deprecation이고 별도 correctness 실패로 세지 않았다.

### 27.9 남은 범위와 감사 handoff

이번 비용 gate는 현실적인 3개 합성 크기의 operation counters와 complete oracle로 검증한다.
§35의 전체 1k/5k/10k/50k/100k integrated/device 스트레스·compression 비교, peak RSS 및
hardware/OS power-loss 검증까지 수행했다고 주장하지 않는다. E4의 Pending/Offline/Legacy/
B/J adapter, reader/frozen pin lifecycle와 R1 Large Restore/MW는 미구현이다.

future 같은-connection GC/repair가 immutable bytes/edges를 변경하려면 이 provenance의 명시
무효화와 in-flight verification 보호를 함께 설계해야 한다. 현재 E3에는 그런 object DELETE/
repair API가 없다. E1 staging cleanup은 bytes를 지우지 않으며 현재/이전/준비된 graph는
root/legacy pin 제약으로 보호된다. 과거 session ticket·receipt를 미래 권한으로 쓰지 않는다.

정상 startup/read/write와 Snapshot v7, OfflineBaseline v4, frozen B/J, backend runtime,
binding protocol 및 E1 canonical/monetary/HTTP cleanup source는 diff로 불변을 재확인했다.
AppState E3 entry는 lib 안에 정의만 있고 자동 호출점이 없다. financial UI 설치, pending
retirement/ack/rebase, APK 설치, 배포, production migration/activation은 수행하지 않았다.

전체 backend gate까지 완료했다. 자체 source/test 점검에서 미해결 Critical/High/Medium
E3 blocker는 없다. 이는 독립 감사 결과가 아니다. **E3 구현 및 I25 교정은 COMPLETE**이며
독립 구현 감사 준비 상태다. E4/R1·일반 사용자 segmented 활성화·배포는 허용되지 않는다.

### 27.10 commit/push 인계

완료 gate를 확인한 source, 기존 E3 작업, 새 I25 회귀, 합성 측정 및 이 보고서를 같은
feature commit에 포함한다. commit 제목은
`feat(flutter): complete T6.6E3 incremental authority-fenced publisher`다.
원래 committed baseline은 `9a53b139cbb99d40020ba0635cf6b44730f3ca51`이며 기존
uncommitted 작업을 reset/discard하지 않았다. 시작 main/origin/main/실제 remote main과의
일치도 최종 commit 직전에 다시 확인했다.

이 보고서를 포함한 정확한 구현 commit은 `git log -1 --format=%H -- docs/t66e3-implementation.md`
로 식별한다. commit 자체를 자기 SHA로 인용할 수 없으므로, push 뒤의
HEAD/main/origin/main/actual remote main·clean tree 대조 결과와 SHA는 최종 인계 응답에
기록한다. commit/push는 배포 허가가 아니며 APK 설치·production activation은 하지 않는다.

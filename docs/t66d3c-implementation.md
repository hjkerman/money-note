# T6.6D3c — 최초 중단 기록과 승인 후 구현 재개

이 문서의 첫 부분은 최초 **BLOCKED** 결과의 보존 기록이다. 소유자 승인 후
추가된 계약·구현·검증은 아래 `승인 후 구현 재개` 절에서 구분한다. 최초 중단을
구현 결함 수정이나 완료 결과로 바꾸어 표현하지 않는다.

## A. 시작 Git 상태

시작 시 branch는 `main`이며 HEAD/main/origin/main/실제 remote main은 모두
`e1b6e6493c6e2644275f37173f25a46be84b8173`이었다. Working tree는 clean이었다.
실제 parent는 `e97b1d7f54231e6cc21d7d2ec897f6fd150cbd32`, 그 parent는
`9f9a94c03ff43c6d87e77e1dc2c30a30080cf71b`다.

## B. 변경 파일과 격리 범위

이 문서만 추가했다. Backend/app/isolated_sync/tests/mobile/frontend, schema,
release artifact, 배포 스크립트를 수정하지 않았다. 진단 스크립트와 결과는
`/tmp/mn-d3c-retention-probe.py`, `/tmp/mn-d3c-retention-probe.json`에 있다.
진단은 `ObservationSandbox`가 직접 생성한 폐기용 합성 SQLite만 사용했다.

**구현 판정: BLOCKED — RETENTION OR GC CONTRACT CORRECTION REQUIRED.**

D3c 요청의 §11/§43에 따라, 서버 previous/recovery retention과 과거 complete
certificate의 객체 참조 보관 의미를 확정하기 전 삭제 구현을 중단했다.
아래 내용은 완료된 D3c 구현 보고가 아니라, source inspection·합성 반례·실행한
제한 회귀의 기록이다. 규범 문서는 변경하지 않았다.

## C. Observation lifecycle

**VERIFIED — 기존 동작만:** `ObservationRepository._check_lease()`와
`_retire_expired()`는 available→retired 전환을 제공한다. D3c 일반 lifecycle
processor, explicit termination, revoked credential 정리 기능은 구현하지 않았다.

## D. Sticky retirement

기존 `_connection()`은 실패 시 savepoint를 되돌린 뒤 확정된 retirement만 같은
writer lock 아래 commit한다. M01 terminal boundary와 M02 quota replacement·clock
rollback 제한 회귀를 실행했다. 이 경계를 수정하지 않았다.

## E. Pin release

**NOT IMPLEMENTED:** 일반 idempotent release. 기존
`ObservationConnection._epoch_bootstrapped()`만 이전 namespace 관측을 retired,
그 pins를 inactive로 바꾼다. 이는 규범 §5의 cold bootstrap 동작이다.
만료만으로는 기존 pin을 해제하지 않았다.

## F. Exact-once/idempotent release

D3c release accounting과 동시 release 검증은 미구현·미실행이다.
D3B-M01의 worker permit release와 observation root-pin release를 혼동하지 않는다.

## G. Transactional lifecycle boundaries

현재 observation 생성 및 lookup/object 준비는 `BEGIN IMMEDIATE` metadata scope를
사용한다. 새 retirement/release/reclaim transaction은 추가하지 않았다.
Available 관측의 pins를 제거하는 작업은 수행하지 않았다.

## H. Retention-root inventory — INCOMPLETE

| 범주 | 확인한 실제 참조 | D3c 판단 상태 |
| --- | --- | --- |
| 현재 complete authority | `sync_current`→`sync_commits`의 raw/index/input | 반드시 보관 |
| 기존 active observation pins | raw/index/hot/control/input 다섯 role | release 전 반드시 보관; 공개 다운로드는 네 root만 |
| native transfer 준비 | 같은 SQLite `BEGIN IMMEDIATE` 안에서 bytes materialization | GC와 동일 DB writer serialization을 사용할 수 있으나 새 GC 연동은 미검증 |
| 과거 complete certificate | 모든 `sync_commits`가 raw/index/input 객체 FK 보유 | 보관 종료·축약 조건 미지정 |
| 서버 previous/recovery generation | 명시적 selector/pointer/retirement 규칙 없음 | 필수 범위 미확정 |
| 기존 server pre_restore | standalone Snapshot v7 파일 | 객체 store의 root pin으로 발명하지 않음; 기존 파일 보존 |
| frozen B/J/pending/local previous | 규범의 모바일 local store/pins | 자동으로 서버 pin이라고 해석하지 않음 |
| 미래 shared backup/large restore | 현재 segmented backup dependency 없음 | DEFERRED TO R1 |

근거는 [규범 §6](t66c-delta-sync-protocol.md#6-revisioncontext관측-identity)의
서버가 client base root를 보관하지 않을 수 있다는 설명,
[§16](t66c-delta-sync-protocol.md#16-coherent-observation-수명인가)의 lease/root count,
[§24](t66c-delta-sync-protocol.md#24-mobile-physical-store와-publication-전제)의 local
generation/pin 정의와 §32의 **local SQLite** GC 문맥이다. §32의 previous/frozen
목록만으로 서버 previous 세대의 정확한 선택·해제 규칙을 도출할 수 없다.

또한 [D3b 보고서 AD](t66d3b-implementation.md)에는 후속 서버 retention을
`current/previous/active observations`로 기술하지만 previous의 선택·보관 종료를
정의하지 않는다. 이 보고서의 언급을 새 규범 정책으로 승격하지 않았다.

## I. Current/previous generation retention — 계약 blocker 1

실제 [finalization.py](../backend/isolated_sync/finalization.py)의 `SQL`은
`sync_commits.raw_hash/index_hash/input_hash`에 `sync_objects` FK를 둔다.
`sync_authority_fence.finalized_tx_id`도 complete certificate를 참조한다.
`FinalizationConnection.finalize()`는 매번 complete row를 추가하고 current를
갱신하며, bootstrap도 기존 certificate를 보존한다.

따라서 과거 complete certificate를 영구 retention root로 해석하면 그 모든
generation graph를 보관해야 한다. 반대로 current/observation만 root로 해석해
과거 graph를 회수하려면 해당 certificate의 FK 및 fence/audit metadata 처리
계약이 필요하다. 현재 이를 임의로 삭제·해제하는 근거는 없다.

서버 previous/recovery 대상과 certificate의 물리적 객체 보관 의미를 함께
명시해야 한다. 이는 기존 D2b/D3a/D3b의 오류를 발견했다는 주장이나 광범위한
아키텍처 재설계 요청이 아니다. D3c의 파괴적 삭제 판정을 위한 좁은 계약 공백이다.

### 삭제 없는 합성 재현

1. 기존 `ROWS` fixture와 합성 auth session을 새 `ObservationSandbox`에 넣는다.
2. Install/bootstrap 후 observation 하나를 만든다.
3. `app_labels` 한 row를 세 번 각각 실제 D1/D2b transaction으로 갱신한다.
4. 제어 clock을 901초 진행해 lookup으로 sticky retirement를 확정한다.
5. Fresh connection에서 객체 bytes·FK·certificate·pin을 읽는다.
6. 독립 JSON graph walker와 `hashlib.sha256`으로 두 root 해석을 비교한다.
7. No-op transaction 두 번과 explicit epoch bootstrap 뒤 같은 검사를 반복한다.

| 상태 | certificate 수 | 저장 객체 수 | current+active pin 도달 객체 | 모든 certificate+pin 도달 객체 | 정책에 따라 보관 판정이 달라지는 객체 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 변경 3회, observation 만료 | 4 | 178 | 162 | 178 | 16 |
| no-op 2회 추가 | 6 | 178 | 162 | 178 | 16 |
| cold epoch bootstrap 추가 | 7 | 330 | 152 | 328 | 176 |

만료 후 observation은 fresh connection에서 `retired`, 다섯 pins는 여전히 active다.
Epoch bootstrap 후 active pin은 0이고, 과거 certificate 6개는 남는다.
두 no-op 뒤 같은 revision의 complete certificate는 3개다. 따라서 revision 값만으로
직전 transaction의 identity를 정의해서도 안 된다. SQL rowid를 규범 recovery
selector로 새로 채택하지 않았다.

전 상태에서 `PRAGMA foreign_key_check`는 이상 없었고, 읽은 객체의 독립
domain-separated SHA-256 및 typed Ref 길이 검사는 통과했다. 이 walker는 검사
대상의 실제 명시 Ref만 따른다. Production reachability 구현이나 전체 C1 admission
검증을 대신하지 않는다. **DELETE와 pin release는 한 번도 실행하지 않았다.**

### 필요한 최소 계약 명확화

다음 두 항목을 한 좁은 retention addendum으로 확정해야 한다.

1. 서버가 별도로 보관할 previous/recovery generation의 유무, 있다면 정확한
   identity 선택 및 해제 조건. No-op/same-revision과 epoch 전환도 명시한다.
   모바일 previous/frozen 및 standalone 30-backup 정책과 분리한다.
2. 위 retention과 live observation/transfer dependency가 모두 사라진 과거
   complete certificate의 root FK 보관을 종료할 수 있는지, 종료 시 certificate·
   D1/D2b fence/coverage evidence를 어떤 상태로 보존하거나 축약할지.

승인 전 안전한 처리는 모든 과거 certificate 참조를 보관하고 destructive GC를
막는 것이다. 이를 정상 역사 세대 회수·steady-state storage gate의 완료라고
주장하지 않는다. 임의의 이전 1개/2개/30개 정책을 구현하지 않았다.

## J. Active observation protection

기존 다섯 pins와 lookup의 exact role/hash 검사를 유지했다. 생성·restart·금융
불변 회귀는 실행했다. 새 GC와의 경쟁 보호는 미구현이다.

## K. In-flight transfer protection

`TransferRepository.acquire()`는 `_connection()` 안에서 path 검증, 객체 읽기,
chunk/response bytes 준비와 terminal guard를 수행하고 connection을 닫는다.
Network await 동안 해당 transaction을 유지하지 않는다. 이것을 향후 동일 DB GC와
직렬화할 수 있다는 source 근거는 있으나, D3c 구현·race 증명을 완료하지 않았다.
Retention이 authorization TTL을 연장한다는 규칙도 추가하지 않았다.

## L. D3B-M01 worker-lifetime integration

기존 `WorkerBudget`/`WorkerLease`/`NativeJob`을 수정하지 않았다.
기존 cancellation regression 25개를 실제 실행했으며 모두 통과했다.
ASGI cancellation을 native 종료나 GC retention release로 해석하는 코드를 추가하지 않았다.

## M. Immutable graph reachability

진단용 독립 walker만 `/tmp`에서 실행했다. raw-root→table root,
snapshot-node→children, index-root→facts, index-node→left/right를 따르고
inline row/fact/hash-looking 값을 별도 객체 edge로 만들지 않았다.
새 production용 D3c graph walker, count 검증·복구, missing/corrupt graph gate는 미구현이다.

## N. Shared object retention

진단 walker는 visited set으로 공유 객체를 한 번만 센다. Shared subtree 삭제 안전성은
실제 GC가 없어 검증하지 않았다. Physical deduplication을 transfer 권한으로 바꾸지 않았다.

## O. GC candidate selection

**NOT IMPLEMENTED:** 위 16/176개를 삭제 후보라고 확정하지 않는다. 이들은 서로 다른
retention 해석의 차집합이며, 현재 실제 certificate/FK가 보호한다.

## P. Mark/sweep 또는 동등 설계

**NOT IMPLEMENTED:** mark round, incoming-edge/root-pin count, sweep progress,
generation fence를 추가하지 않았다. 규범 §16의 count 계약을 mark 결과만으로
대체하지 않았다.

## Q. Concurrent writer/GC

**NOT VERIFIED:** GC가 없으므로 새 writer/GC fence·stale mark 경쟁 시험도 없다.
기존 금융 writer/finalizer 동작을 변경하지 않았다.

## R. Concurrent observation/GC

기존 동시 quota replacement 회귀는 통과했다. 새 pin publication/sweep race는
미검증이다. 이를 기존 동시성 테스트만으로 입증했다고 주장하지 않는다.

## S. Transactional deletion

객체·pin·certificate·observation metadata의 DELETE는 실행하지 않았다.
실제 합성 GC, deletion rollback 및 batch 후 retained graph 검증은 미구현이다.

## T. Crash/restart

독립 진단은 각 검사마다 fresh connection을 사용했다. 기존 worker correction suite의
event-loop 종료/native cleanup 회귀는 포함했다. D3c SIGKILL·mark/sweep/reclaim
crash 시험은 실행하지 않았으며 hardware power-loss 보장을 주장하지 않는다.

## U. Metadata reclamation

**NOT IMPLEMENTED:** retired observation/pin/view/obsolete certificate metadata 회수와
budget 감소. 이전 ID 재사용/tombstone 설계를 임의로 정하지 않았다.

## V. Quota/budget recovery

기존 principal quota·sticky retirement 동작만 재검증했다. D3c의 record 4,096개 및
logical 64MiB budget 회수·반복 steady-state 시험은 실행하지 않았다.

## W. Clock rollback과 epoch

기존 terminal expiry, quota 교체 후 clock rollback 및 bootstrap 회귀가 통과했다.
진단에서도 만료 관측이 durable retired임을 확인했다. Old-epoch certificate/root의
보관 종료 의미는 I의 계약 명확화가 필요하다. Epoch 정책을 바꾸지 않았다.

## X. Backup/restore dependencies

`snapshot._write_snapshot_backup()`은 standalone Snapshot v7을 생성·readback·검증한다.
Server `pre_restore`/`pre_reconcile_server` 파일과 기존 retention은 건드리지 않았다.
현재 파일 백업을 segmented 객체 pin으로 간주하거나 기존 30-backup을 두 세대로
줄이지 않았다. Physical DB backup은 별도의 quiescent cold-start 경계다.

## Y. Corruption/fail-closed

삭제 안전성 증명을 완성할 수 없어 삭제 자체를 막았다. 새 graph corruption·missing
child·count damage 주입에 대한 D3c 동작은 미구현·미검증이다.

## Z. Synthetic dry-run/actual GC 구분

진단은 read-only graph 비교이며 정식 GC dry-run API가 아니다.
Actual GC API와 정상 runtime destructive entry point는 추가하지 않았다.

## AA. Storage growth/reclaimed bytes

위 표는 합성 진단의 논리 객체 수이며 performance benchmark가 아니다.
회수 객체 0개, 논리 회수 bytes 0이다. DELETE/VACUUM/file shrink는 수행하지 않았다.
공유 객체 보존 수·장기 steady-state storage는 측정하지 않았다.

## AB. GC performance와 lock hold

**NOT MEASURED:** GC가 미구현이므로 mark/sweep·batch/lock/memory 측정은 없다.
의미가 확정되지 않은 retention 정책으로 성능 수치를 만들지 않았다.

## AC. Normal-request overhead

Runtime source가 바뀌지 않아 새 O(N) dependency를 추가하지 않았다.
기존 observation의 full-history/graph rebuild 금지 및 transfer SQL point-access 회귀는
실행했다. D3c 전후 latency 비교 benchmark는 실행하지 않았다.

## AD. Complete post-GC reconstruction

기존 HTTP full-generation reconstruction oracle은 통과했다. 실제 GC를 실행하지
않았으므로 **post-GC 11-table/Patricia reconstruction gate는 미충족**이다.

## AE. Independent reference oracle

진단의 expected reachability는 Store.edges/PathResolver를 호출하지 않고 direct
SQLite bytes를 독립 `json.loads`/`hashlib`로 읽어 계산했다. Fresh-connection FK 및
status/pin 검사는 persisted-state evidence다. Complete retained root set이 미확정이므로
차집합 자체를 deletion proof로 사용하지 않았다.

## AF. 새 테스트와 실행 내역

새 tracked D3c test는 0개다. 새 독립 합성 진단 스크립트 실행은 성공했다.
실제로 실행한 기존 제한 backend 회귀는 **72 tests PASS, 51.40초**다.

- `test_isolated_sync_transfer_cancellation.py`: 25개 전체.
- `test_isolated_sync_finalization.py`: `test_no_change_and_neutral_sequence`,
  `test_bootstrap_rotation_and_install_idempotence`,
  `test_second_fence_cannot_accept_capture_only`, `test_legacy_snapshot_logical_parity`.
- `test_isolated_sync_observation.py`: `test_complete_pins_restart_and_financial_immutability`,
  `test_expiration_and_epoch_rotation`, `test_terminal_lease_expiry_is_sticky`,
  `test_quota_replacement_clock_rollback`, `test_concurrent_quota_replacement_is_atomic`,
  `test_forbids_full_history_and_graph_rebuild`, `test_no_runtime_import_or_new_routes`,
  `test_all_twelve_legacy_projection_parity`.
- `test_isolated_sync_transfer.py`: `test_full_generation_http_reconstruction_oracle`,
  `test_sql_point_access_no_financial_or_graph_scan`,
  `test_release_artifact_hashes_exact_bytes_and_target`,
  `test_no_hash_release_artifact_or_normal_route_activation`.

추가 실행: safety/diagnostic `pytest -q scripts/tests scripts/benchmarks`
**59 PASS, 4.02초**, backend/app/isolated_sync/tests/scripts Ruff PASS,
동일 경로 compileall PASS, `npm --prefix frontend run build` PASS.
성공 전체 로그는 출력하지 않았고 `/tmp/mn-d3c-stop-*.log`에 보관했다.

## AG. D1/D2a/D2b/D3a/D3b 회귀

위 제한 회귀 이외의 전체 backend는 **NOT RUN**이다. D1/D2a 전체 suite,
D3c migration/concurrency/crash/GC suite를 실행했다고 주장하지 않는다.
사용자가 제공한 1,227 tests + 1,540 subtests는 이전 독립 감사 baseline이며 이번
실행 수에 합산하지 않았다. 기존 code의 불변과 실행한 일부 회귀의 성공을
전체 보존 증명과 구분한다.

## AH. Snapshot v7

Exporter/restore/hash/schema source는 unchanged다. 기존 logical parity test는
통과했으나 Snapshot 전체 suite를 별도로 실행했다고 주장하지 않는다.

## AI. Normal runtime isolation

Source/schema/route/startup/scheduler 변경 0이다. 기존 no-runtime-import/no-route
회귀가 통과했다. Segmented sync와 GC를 정상 runtime에 활성화하지 않았다.

## AJ. T6.6E dependencies

**DEFERRED TO T6.6E:** local store, durable accepted/previous/frozen B/J/pending pins,
atomic publication, Android durability 검증. 이를 서버 retention 규칙으로 발명하지 않았다.

## AK. R1 dependencies

**DEFERRED TO R1:** large restore/shared recovery integration. 기존 standalone backup과
reconciliation evidence는 보존하며 이번 작업에서 형식·보관 의미를 바꾸지 않았다.

## AL. Known limitations

새 D3c 구현 기능은 없다. 계약 blocker 1개가 있어 completion gate는 충족되지 않았다.
새 Critical/High/Medium 구현 결함을 확인한 것은 아니며, 전체 독립 감사도 수행하지 않았다.
필수 문서 전체에 대한 구현 검토를 완료했다고 주장하지 않는다. 중단 판단의 직접 근거는
위에서 특정한 규범 절·실제 schema/finalizer·진단 결과다.

## AM. Production safety

Production DB/API/credential/service 접근 NONE, 배포 NOT PERFORMED.
자가 소유 합성 DB 이외를 테스트하지 않았다. Actual object deletion/pin release는
합성 DB에서도 0회다. Production-reading dry-run, 서비스 restart, migration, APK 설치 없음.

## AN. Commit/push

Completion gate 미충족으로 commit/push하지 않았다. HEAD는 시작 commit 그대로다.
이 문서를 uncommitted 상태로 보존한다. 기존 tracked source 변경은 없다.
최종 HEAD/main/origin/main/실제 remote main도 모두 시작 commit과 같았다.
Working tree에는 `?? docs/t66d3c-implementation.md`만 남았다.
`git diff --check`와 신규 문서의 no-index whitespace 검사도 통과했다.

## AO. 판정과 다음 단계

**BLOCKED — RETENTION OR GC CONTRACT CORRECTION REQUIRED**

서버 previous/recovery generation의 정확한 보관·해제 규칙과 참조가 없어진 과거
complete certificate의 root FK 축약 허용 계약만 명확히 승인한 뒤 D3c를 재개한다.
전면 재설계나 기존 D1/D2a/D2b/D3a/D3b 재구현은 요청하지 않는다.

---

# 승인 후 구현 재개 — T6.6D3c

## A. 이전 BLOCKED 상태와 재개 Git

위 최초 중단 기록을 보존했다. 재개 시 branch `main`, HEAD/main/origin/main/실제
remote main은 모두 `e1b6e6493c6e2644275f37173f25a46be84b8173`이었다. 기존 dirty
상태는 이 미커밋 보고서 하나뿐이었다. Source reset/checkout/clean/restore를 수행하지
않았고 관련 없는 변경도 없었다. 최초 중단은 올바른 안전 정지였으며 이번 명시 승인으로
계약의 모호함이 해소되었다.

## B. 승인된 서버 retention 정책

**IMPLEMENTED:** 현재 financial SQLite 행은 날짜와 무관하게 보존한다. Obsolete
representation만 회수하며 current tree를 repack/compact하지 않는다. 서버 previous의
자동 장기 보관은 **NONE**이다. 모바일 previous/frozen B/J와 혼동하지 않는다.

Live 의무는 current complete의 raw/index/input, 미해제 observation의 다섯 roots,
실제 객체 의존 중인 native preparation, 미해결 atomic publication, 승인된 explicit
durable root다. Historical complete certificate는 digest/provenance/fence 증거이지
영구 reconstructability 보장이 아니다.

## C. 계약 및 변경 범위

T6.6C `§16-S`만 추가했고 C1/hash domains/wire/모바일 저장 정의는 바꾸지 않았다.
`docs/architecture.md`, `docs/project-state.md`에 최소 일관성 설명을 추가했다.

Source는 `retention_schema.py`, `retention.py`를 추가했다. 기존 `finalization.py`에는
정확한 metadata contract에 이미 포함된 trigger만 허용하는 isolated extension을,
`observation.py`에는 기존 동작을 보존하는 schema/charge/replay hook을 추가했다.
`http.py`에는 D3c repository를 명시 구성한 경우에만 §15.4 DELETE를 등록했다.
Normal `backend/app`, frontend/mobile, 배포 파일과 의존성은 수정하지 않았다.

`test_isolated_sync_retention.py`, `scripts/benchmarks/t66d3c.py` 및 compact 측정
artifact를 추가한다. 기존 artifact 정의상 financial_engine identity는 모든 backend
소스에 결합되므로 `t66d3b-release-artifacts.json`의 정확한 source digest artifact도
갱신했다. 금융 공식이나 C1 버전 변경이 아니다.

## D. Historical certificate 증거 모델

**IMPLEMENTED / VERIFIED:** `sync_commits`의 모든 필드, epoch/revision/roots/status,
capture certificate, change coverage 및 두 deferred fence를 그대로 보존한다. GC는
certificate/fence 행을 삭제하거나 hash를 NULL로 만들지 않는다. 과거 certificate의
status가 complete라는 사실만으로 객체가 현재 물리적으로 남았다고 해석하지 않는다.

`accepted_generation()`과 미래 writer의 `generation()`은 current만 승인한다.
Old observation은 자신의 live pins와 실제 objects를 추가 검증한다. Archived digest를
클라이언트가 지정하여 historical reconstruction authority를 발급하는 API는 없다.
Test: `test_historical_certificate_only_objects_reclaimed_and_writer_restarts`,
`test_post_gc_all_eleven_tables_patricia_and_immutable_old_target`.

## E. FK/reference 분리와 migration

**IMPLEMENTED:** checkpoint `1000005`, `isolated_synthetic_gc` profile이다. Production
checkpoint 4는 불변이다. `rebuild_evidence()`는 정확히 세 table의 object-availability
FK만 분리한다: `sync_commits`, `sync_observations.input_hash`, historical pin hash.
Non-null digest와 CHECK, observation/certificate identity FK, 두 deferred fence는 보존한다.

Current의 기존 raw/index FK에 더해 `sync_retention_roots`가 current raw/index/input 및
active observation 5 roots를 FK-backed로 보호한다. 객체 삭제 직전 zero-count guard도
있다. Migration은 자체 소유 임시 DB의 독립 connection에서 FK OFF/table rebuild를
수행하며 EXCLUSIVE boundary, FK check, atomic rollback, FK ON, exact schema admission을
검증한다. 다른 financial constraint/trigger는 변경하지 않는다. WAL 설정은 이 격리
file에만 적용한다. Failed migration의 financial/schema/version 상태는 rollback되지만
이미 설정한 WAL journal mode는 남을 수 있다.

Test: `test_versioned_migration_preserves_evidence_and_raw_rows` — rollback/repeat,
certificate/fence/financial state 불변, FK 분리와 checkpoint 확인.

## F. Current generation 보관

**IMPLEMENTED:** `sync_gc_current_insert/update/delete` triggers가 current의 세 live
root를 publication과 같은 transaction에서 교체한다. `Collector._roots()`가 current
certificate/input proof 및 실제 live references를 대조한다. `mark()`는 그 descendants
전체를 검증한다. Historical certificate의 동일 hash도 current reachability에 있으면
회수하지 않는다. Root의 나이나 거래 날짜로 삭제하지 않는다.

## G. Publication/recovery 임시 보호

D2b의 raw/capture/object/edge/certificate/current/fence는 한 SQLite transaction이다.
Uncommitted object/publication은 mark snapshot에 보이지 않으며 writer COMMIT은 object/
root/count fence를 바꾼다. Sweep이 먼저 lock을 얻으면 writer가 대기하고, writer가 먼저
commit하면 stale mark를 거부한다. Persisted half-publication을 정상 상태로 승인하지 않는다.
새 generation이 안전하게 commit된 후 previous라는 이유의 추가 pin은 만들지 않는다.

## H. Observation 보관과 sticky retirement

**IMPLEMENTED / VERIFIED:** `available → retired`는 기존 D3a expiry/guard를 유지한다.
Pin lifetime은 별도의 `released` bit와 live-root rows로 표현한다. Retired여도 release
전에는 다섯 roots를 보수적으로 보호한다. `maintain()`은 TTL/retired/credential 무효/
epoch 불일치를 명시 maintenance에서 처리한다. 새로운 일반 요청에 sweep을 넣지 않았다.
Retired→available, released pin→active 전환은 SQL trigger로도 거부한다.

Test: expiry/nonce/clock rollback, replay invalidation, sustained quota, epoch bootstrap.
M01/M02의 error-path sticky retirement savepoint 계약은 보존했다.

## I. In-flight transfer와 D3B-M01

**IMPLEMENTED / VERIFIED:** 별도의 무기한 transfer row를 만들지 않는다. 기존
`TransferRepository.acquire()`의 BEGIN IMMEDIATE가 lookup, typed-path resolution,
전체 immutable bytes 검증·chunk/base64/response materialization, terminal TTL guard를
포함한다. Sweep/retirement writer와 직렬화하므로 객체 의존 중에는 삭제할 수 없다.

Native worker가 실제 connection을 닫은 뒤 materialized bytes만 남으면 DB retention
의존성은 끝난다. HTTP coroutine 취소는 이 transaction이나 worker permit을 대신
해제하지 않는다. 취소된 worker도 정상 finally/rollback/close까지 보호를 유지한다.
Materialized response는 기존 별도 terminal credential/expiry guard 후에만 공개한다.
이는 인가 연장이 아니며 network 전송 동안 DB lock을 유지하지도 않는다.

Test: 실제 ASGI Task.cancel을 사용하는
`test_actual_asgi_transfer_gc_serialization_and_native_cancel` 두 경우. 기존 25개
D3B-M01 tests도 회귀 범위에 포함한다.

## J. Idempotent pin release와 원자성

**IMPLEMENTED / VERIFIED:** `RetentionRepository.release()`는 동일 원 credential/principal을
lock 안에서 재검증하고 retired 상태·5 pins inactive·lifecycle released를 한 transaction으로
설정한다. 각 pin/root는 PK와 active 조건으로 exact-once 해제하며 shared-object incoming
count와 root-pin count를 혼동하지 않는다. 삭제는 별도 GC eligibility 검증 뒤에만 한다.

Fault로 실패하면 모든 부분 release/reclaim을 savepoint rollback한다. 확정된 terminal
retirement만 기존 D3a 방식으로 따로 commit하여 retired+아직 보호되는 5pins 상태를 남긴다.
Available+missing pins를 만들지 않는다. 동일 원 credential DELETE는 204 idempotent이며
권한 없는 credential은 거부한다. Default D3b repository에는 DELETE를 등록하지 않는다.

Test: 7개 release fault boundaries, concurrent duplicate release, HTTP DELETE, reclaim rollback.

## K. Immutable reachability

**IMPLEMENTED:** `Collector.mark()`는 일관된 WAL read snapshot에서 live roots를 독립
열거하고 C1/domain hash/canon/raw-schema/namespace/type/ref bytes를 검증한다. 기존
`PathResolver.validate()`의 실제 typed edges만 따라가며 hash처럼 보이는 임의 fact/row
field를 edge로 취급하지 않는다. Raw descriptors/B+tree, Patricia, internal proof,
hot/control의 실제 graph를 검사하고 `sync_object_edges`와 정확히 대조한다.

Visited set으로 중복/무한 순회를 막고 incoming/pin counts를 실제 graph와 재계산 비교한다.
Shared descendants는 어느 하나의 root라도 도달하면 보존한다. Inline leaf rows의
`sync_rows`는 별도 canonical preimage cache로 검증/회수하며 financial source rows가 아니다.

## L. GC eligibility와 bounded sweep

**IMPLEMENTED / VERIFIED:** validated `O - reachable`만 후보다. `Mark`는 해당 Collector
instance에 결합된 비지속 plan이다. Sweep은 새 BEGIN IMMEDIATE에서 transactional fence가
정확히 같은지 확인한다. Index-backed `incoming=0 AND pins=0` 객체만 mark 후보와 대조하고
parent edge를 지운 뒤 객체를 삭제한다. FK/count guard와 검증된 DAG가 live descendants의
삭제를 막는다. Reference count만으로 mark를 생략하지 않는다.

한 batch는 기본 128, 최대 1024 records 및 기본 1초/최대 5초 soft processing bound다.
SQL 한 문장의 실시간 hard deadline 보장은 아니다. 모든 committed batch 후 writer lock
밖에서 새 전체 mark로 retained descendants를 다시 검증한다. 중간 실패는 남은 garbage를
보수적으로 보관하며 무리한 진행을 하지 않는다. 반복 round는 idempotent다.

## M. Writer/observation/transfer 동시성

**VERIFIED:** metadata/object/edge/root/count mutations가 같은 persisted serial fence를
증가시킨다. WAL mark 중 실제 writer/observation COMMIT이 가능하고 stale sweep은 삭제
전 실패한다. Two collectors의 stale plan도 사용할 수 없다. Transfer가 객체 준비 transaction을
보유하면 GC는 busy/lock timeout으로 실패한다. Worker가 종료한 뒤 새 mark로 재시도한다.
Test: `test_publication_commits_during_mark_snapshot_then_sweep_aborts`, stale mark 5cases,
실제 ASGI expiry/cancellation, concurrent release.

## N. Historical certificate 회수 반례

**VERIFIED — 새 측정:** 독립 `/tmp/mn-d3c-approved-probe.py`는 production walker 없이
SQLite JSON/typed references와 독립 SHA-256을 검사했다.

| 합성 상태 | stored | current/live 도달 | 모든 cert와 live의 합집합 | certificate-only |
| --- | ---: | ---: | ---: | ---: |
| 세 번 mutation + active observation | 178 | 162 | 178 | 16 |
| 새 epoch bootstrap | 330 | 152 | 328 | 176 |

첫 fixture에서 16 objects+2 cache preimages, 논리 17,772 bytes를 회수했다. Epoch fixture는
certificate-only 176 및 orphan hot/control 2, cache preimages 37을 회수했고 논리
132,824 bytes를 회수했다. 두 경우 모두 금융/revision/current/certificate/fence state의
GC 전후 fresh-connection 비교는 동일했다. Current 전체검증과 이후 writer도 통과했다.
모든 과거 certificate가 계속 reconstructable하다는 주장은 하지 않는다.

## O. Metadata 회수와 quota 회복

**IMPLEMENTED / VERIFIED:** retired+released record만 pin/observation/lifecycle metadata를
회수하고 charge를 반환한다. Cached hot/control view는 live-root 필요가 없을 때만 제거한다.
새 ID는 CSPRNG UUIDv4이며 absent ID는 재인가하지 않는다. 동일 original credential/request
nonce가 새 Target으로 바뀌지 않게 compact replay digest를 같은 유한 budget에 유지한다.
Replay charge는 namespace/digests/nonce/framing을 포함해 512 bytes다. Original token row가
실제로 삭제되거나 epoch가 바뀌어야 그 replay evidence도 회수한다. Session timestamp 만료나
사용자 비활성은 clock rollback/재활성화로 되돌아갈 수 있으므로 영구 폐기의 증거가 아니다.
Maintenance가 auth row를 변경하지는 않는다. Financial certificate는 회수 대상이 아니다.

4 available/4096 records/64MiB 기본 한도는 유지한다. Test는 작은 configured record/byte
한도로 5회 × 4 observation lifecycle을 반복해 동일 경계를 증명한다. 전체 4096개·64MiB의
물리적 채움 stress를 수행했다고 주장하지 않는다. 무한 nonce를 영구 유효 credential로
사용해도 무한 저장이 가능하다는 보장은 없다. Compact replay도 budget을 소모하며 finite
budget 소진 시 fail closed한다. 기존 token row의 실제 삭제 또는 epoch 전환 후 maintenance로
회복 가능하다. 기존 token을 남긴 채 새로 로그인하는 것만으로 replay charge를 반환하지 않는다.

## P. Crash/restart

**VERIFIED:** file-backed SQLite 실제 child SIGKILL을 release 중/후, mark 중, partial delete,
delete COMMIT 전/후, reclaim 중/후 8곳에 주입한다. Fresh connection은 금융 state와
certificate/fence 보존, current/live graph completeness, lock cleanup을 확인한다.
Plan은 process-local이며 재시작 뒤 무효다. 부분 round를 authoritative 상태로 재개하지
않고 새 mark를 수행한다. SQLite committed batch 또는 전체 rollback만 남는다. SIGKILL은
hardware power-loss 증명이 아니다.

## Q. Epoch

`RetentionConnection._epoch_bootstrapped()`는 기존 cold-bootstrap epoch 정책을 보존하고
old observation retirement+pin release를 bootstrap과 같은 transaction에서 수행한다.
새 accepted generation을 보호하며 old certificate 증거는 남긴다. 추가 old-epoch pin은
만들지 않지만 explicit obligation이 있다면 그 root는 계속 보존한다.
Test: active observation epoch bootstrap, stale mark epoch, replay epoch invalidation.

## R. Clock rollback

Timestamp는 기존 UTC wall-clock persisted contract다. Monotonic timing은 성능/soft bound에만
사용한다. 이미 retired/released/reclaimed된 관측은 wall-clock rollback으로 재활성화되지
않는다. Missing observation ID도 `OBSERVATION_INCOMPLETE/new_observation`이며 성공하지
않는다. 기존 terminal expiry는 `OBSERVATION_EXPIRED/new_observation`으로 보존한다.

추가 반례 두 개를 수정 전에 재현했다: session expiry까지 시계를 전진했다가 되돌리기,
사용자 비활성 후 재활성화하기. 일시적 credential 무효를 영구 폐기로 간주하면 회수된
manifest nonce가 새로운 Target을 만들 수 있었다. Original token row 존재 여부로 replay
회수 조건을 좁힌 뒤 두 반례와 migration/budget 관련 5개 focused tests가 통과했다.
이는 auth/lease 유효 기간을 연장하지 않고 retry evidence만 보수적으로 보관하는 수정이다.

## S. Corruption fail-closed

Required root/child, certificate, pin/lifecycle, counts/edges, C1/hash/domain/version/schema/
namespace가 불일치하면 mark 또는 admission이 실패하고 sweep하지 않는다. Corrupt orphan도
보수적으로 전체 round를 막는다. GC는 financial authority를 수선하지 않는다. Unsupported
또는 malformed metadata를 조용히 건너뛰지 않는다.
Test: corruption 6categories, missing descendant/schema, altered canon/kind/raw-schema 3cases.

## T. Synthetic dry-run/actual 구분

**NOT ACTIVATED — 정상 runtime:** `Collector.collect()` 기본은 dry-run으로 retirement,
release, object deletion도 하지 않는다. `apply=True`는 `RetentionSandbox`가 직접 만든
temporary directory/file의 inode/device/parent/symlink 검사와 exact experimental schema/
profile admission을 요구한다. Existing DB path나 env/CLI flag로 production DB를 선택하는
생성자는 없다. 신뢰된 Python private metadata API의 악의적 변조를 막는 OS sandbox라는
주장은 하지 않는다. HTTP GC endpoint/normal startup scheduler는 없다.

## U. 원래 blocker 해소

소유자의 narrow 계약 승인으로 certificate의 증거 lifetime과 reconstruction lifetime을
분리할 수 있었다. 원래 16/176 certificate-only 차이가 재현되었고 실제 합성 GC가
이를 회수했다. 과거 금융 행을 지운 것이 아니다. D1/D2b deferred fences와 current
validation을 완화하지 않았다. Future real financial card/cash command와 12 projections도
과거 representation 회수 후 기존 backend oracle와 비교한다.

## V. 독립 oracle

Test `oracle()`은 current certificate/pins/explicit metadata를 직접 읽고 JSON typed edges 및
독립 hashlib로 expected reachable/candidate set을 만든다. Production `Collector`,
`Store.edges`, `PathResolver`를 expected-set 계산에 사용하지 않는다. GC candidates/남은
storage와 대조하며, 별도의 D2b full-rebuild/financial oracle도 사용한다. Codec/Fact 모델을
공유하는 canonical Patricia rebuild는 그 공유 범위를 명시한다. `Index.build()` full-build는
incremental update와의 differential check이며 완전히 별개인 Patricia encoder라는 주장은
하지 않는다. Graph reachability/returned-byte SHA-256 oracle는 production walker와 분리했다.

## W. Post-GC 11-table HTTP 재구성

**VERIFIED:** `test_post_gc_all_eleven_tables_patricia_and_immutable_old_target`는 old/current
두 유효 observation을 유지한 채 GC 후 실제 authenticated ASGI HTTP로 네 roots부터
returned typed parent를 따라 내려간다. Base64/C1/domain SHA-256/ref length를 독립 검사하고
11개 tables 전체 logical rows를 각각의 pre-GC SQLite state와 비교한다. Fact 전체와 canonical
Patricia root를 D2a `Index.build()` full-build로 비교하고 12개 hot projection 및 Target retry 불변도
확인한다. 내부 proof root는 retention 대상이지 transferable root가 아니다.

## X. 논리 storage 회복

새 benchmark는 bounded card/cash generations와 overlapping retained manifest를 유지한 뒤
dry-run/actual/second-no-garbage round를 수행한다. Object deletion과 `sync_rows` cache deletion을
별도로 집계한다. Logical reclaimed bytes는 두 body의 합이며 SQLite file shrinkage가 아니다.
VACUUM을 실행하지 않는다. Financial raw tables는 GC DELETE 대상에 없다.

**VERIFIED — 이번 4개 독립 benchmark DB 합계:** obsolete objects **3,300개**, cache
preimages **180개**, 논리 **23,313,490 bytes**를 회수했다. 모든 round의 remaining candidates는
0이며 두 번째 round의 object/cache 추가 삭제도 모두 0이었다. 이는 서로 다른 네 DB의 합계로,
하나의 ledger에서 반복 회수한 수치나 물리 파일 감소량이 아니다. Current+retained manifest의
8개 root references를 유지했고 source 금융 행을 GC로 삭제하지 않았다.

## Y. 성능

최종 측정 결과는 `docs/benchmarks/t66d3c/summary.json`에 별도 기록한다. Matched D3b-profile과
D3c-profile은 같은 synthetic seed/financial code로 376/1k/5k/10k, 고정 hot composition,
3 warmups/20 samples를 사용한다. Bootstrap/path oracle/cleanup은 hot timing 밖이다.
No-change observation/manifest retry/root/leaf/card/cash와 explicit GC를 분리한다.
Instrumentation은 real SQL rows/VM steps/EXPLAIN 및 HTTP stage metrics를 수집한다.
측정 중 같은 개발 호스트에서 backend 회귀도 실행되었으므로 latency는 환경 의존 참고값이며
독점 CPU 성능이나 deployed application latency로 해석하지 않는다.
Bounded observation quota COUNT를 historical ledger scan으로 오분류하지 않는다.
SQL statement 수는 Python connection execute 호출이며 trigger 내부 substatement를 별도
statement로 세지는 않는다. VM lower bound에는 hook 설치 후 실행한 trigger 작업도 포함한다.
`object_reads/object_bytes_read`는 transfer path resolver의 측정으로 lookup/terminal의 추가
root reads나 물리 디스크 I/O 총량이 아니다. 그 추가 조회는 전체 SQL/materialized-row 수에
포함한다. Nested stage timing을 합쳐 end-to-end latency로 만들지 않는다.

Mark는 O(all stored immutable representations+cache), 메모리도 O(stored graph)이며 normal
request에서 실행하지 않는다. Default admission cap은 1,000,000 records/1GiB encoded bodies다.
Decoded Python peak memory가 encoded cap과 같다는 보장은 없다. Post-batch full validation은
안전 우선으로 반복되므로 많은 garbage/batches에서는 maintenance 총 시간이 늘어난다.
WAL mark는 writer COMMIT을 막지 않지만 오래된 read snapshot 동안 WAL checkpoint 회수를
지연시킬 수 있다. Lock-hold와 elapsed mark/sweep을 구분한다.

**VERIFIED — 최종 48 cells / 960 measured samples / 4 maintenance rounds:** Python 3.12.3,
SQLite 3.45.1, Linux x86_64, i7-8750H/12 logical CPUs에서 측정했다. 10k HOST 결과는 다음과
같다. 단위는 ms, 각 값은 median / p95다.

| 경로 | 기존 D3b profile | D3c profile |
| --- | ---: | ---: |
| No-change observation | 425.63 / 437.91 | 403.77 / 409.26 |
| Manifest retry | 384.44 / 389.45 | 386.80 / 400.31 |
| Raw root | 291.70 / 293.70 | 324.99 / 342.46 |
| Ledger leaf | 528.84 / 529.86 | 539.27 / 574.49 |
| Card mutation | 574.18 / 579.32 | 645.82 / 714.12 |
| Cash mutation | 166.92 / 197.77 | 210.44 / 225.69 |

Fixed profile admission/count/fence 비용이 추가된다. 일부 더 빠른 수치를 성능 개선이라고
단정하지 않는다. 376→10k에서 no-change SQL materialized rows는 **4,521**,
manifest retry **3,861**, root **2,908**로 동일했다. 이 값에는 반복 exact schema admission이
포함되며 금융 행 4,521개를 읽었다는 뜻이 아니다. Root resolver는 1 object, leaf는 path 높이에
따라 3→4 objects를 읽었다. Card changed objects는 14→22, cash는 14→19였다.
전 48 cells의 SQL/EXPLAIN에서 unexpected historical scans는 **0**이었다. 이는 source
inspection/실제 access plans와 함께 해석하며 returned rows나 elapsed time만으로 입증하지 않는다.

| Ledger rows | 실제 GC 총 시간(s) | 최대 deletion write-lock(ms) | 삭제 objects | 논리 회수 bytes |
| --- | ---: | ---: | ---: | ---: |
| 376 | 24.52 | 261.32 | 672 | 5,648,903 |
| 1,000 | 48.30 | 295.12 | 757 | 5,786,801 |
| 5,000 | 179.11 | 390.24 | 903 | 5,920,043 |
| 10,000 | 261.10 | 562.56 | 968 | 5,957,743 |

모든 fixture는 한 bounded batch로 후보를 회수했다. `sweep_ms`는 삭제 transaction 뒤의
전체 graph 재검증도 포함하며 pure lock time이 아니다. 10k dry-run은 195.33초, 실제 round의
첫 mark는 179.66초였다. 큰 maintenance 비용을 정상 refresh 비용으로 숨기지 않는다.
10k process 누적 peak RSS는 414,156 KiB이며 순수 GC 추가 메모리의 측정값이 아니다.
실제 batch counts/SQL/VM/object/stage metrics와 전 규모 median/p95는 compact JSON에 있다.

## Z. 최종 회귀 결과

**VERIFIED — 이번 실행:** 전체 backend **1,284 tests + 1,540 subtests PASS**,
1,511.57초(25:11), 기존 TestClient deprecation warning 1개다. 신규 D3c **57 cases**는
이 전체 수에 포함되며 중복 합산하지 않는다. D1 capture/fence, D2a codec/tree/Patricia,
D2b finalizer/BoundedInputs, D3a M01/M02/12 projections, D3b transfer/25 cancellation cases,
migration/financial/Snapshot v7/authoritative-state suite가 모두 포함된다.

별도 safety/diagnostic **59 PASS**(5.08초), frontend **21 tests / 6 files PASS**, frontend
build **PASS**(1.42초), 전체 관련 Ruff **PASS**, compileall **PASS**다. Flutter/Android는
변경이 없어 실행하지 않았다. 이전 중단 기록이나 독립 감사의 수치를 이번 결과로 재사용하지
않았다. 초기 fixture 오류와 reversible credential 반례는 수정 후 최종 전체 실행에 포함했다.
초기 전체 실행은 **1 failed / 1,281 passed / 1,540 subtests passed**였다. 유효 card update
fixture의 필수 `usage_place` 누락 때문에 기존 writer가 올바르게 거부한 것이며, fixture를
보완했다. Reversible credential 두 반례는 별도로 수정 전 **2 failed**를 재현했고,
수정 후 focused 5개 및 최종 전체 회귀에서 통과했다. 이 이전 수치는 최종 PASS에 합산하지 않는다.

실제 실행 명령:

```sh
cd backend
../.venv/bin/python -m pytest -q --durations=10
# repository root
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
.venv/bin/python -m ruff check backend/app backend/isolated_sync backend/tests scripts/tests scripts/benchmarks
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts/benchmarks
npm --prefix frontend run test
npm --prefix frontend run build
git diff --check
```

임시 실행 근거는 `/tmp/mn-d3c-complete-regression.log`,
`/tmp/mn-d3c-complete-safety.log`, `/tmp/mn-d3c-frontend-tests.log`,
`/tmp/mn-d3c-frontend.log`다. 임시 로그의 영구 보존은 보장하지 않는다.

주요 구현/검증 위치는 다음과 같다. Test names는
`backend/tests/test_isolated_sync_retention.py` 안의 실제 함수다.

| 보장 | 구현 위치 | Test |
| --- | --- | --- |
| 정확한 versioned migration/FK 분리 | `retention_schema.py: RetentionSandbox.install/rebuild_evidence` | `test_versioned_migration_preserves_evidence_and_raw_rows` |
| Historical 증거 보존/미래 writer | `retention.py: Collector._roots/mark/sweep` | `test_historical_certificate_only_objects_reclaimed_and_writer_restarts` |
| Current/shared/live observation 보호 | `retention.py: Collector._roots/mark` | `test_active_old_generation_and_shared_subtrees_survive` |
| Exact-once/atomic release | `retention.py: RetentionRepository._release/release` | `test_release_fault_rolls_back_all_pins_sticky_retirement`, `test_concurrent_release_exact_once_and_wrong_original_credential` |
| Worker/transfer 보호 | 기존 `transfer.py: TransferRepository.acquire`, `workers.py: NativeJob.invoke` | `test_actual_asgi_transfer_gc_serialization_and_native_cancel` |
| Writer/observation/GC fence | `retention.py: Collector.sweep` | `test_stale_mark_aborts_before_any_delete`, `test_publication_commits_during_mark_snapshot_then_sweep_aborts` |
| Rollback/SIGKILL/restart | `retention.py: release/maintain/sweep` | `test_deletion_transaction_rollback_preserves_every_object`, `test_real_process_interruption_recovery` |
| Quota/budget 회복 | `retention.py: RetentionRepository.maintain` | `test_sustained_quota_and_metadata_budget_recovery`, `test_budget_rejection_does_not_release_active_observation` |
| Sticky expiry/replay | `retention.py: _admit_request/maintain` | `test_expiry_reclaim_nonce_replay_and_clock_rollback`, `test_reclaimed_manifest_nonce_survives_reversible_credential_invalidation` |
| Epoch/bootstrap | `retention_schema.py: RetentionConnection._epoch_bootstrapped` | `test_epoch_bootstrap_releases_old_pins_but_preserves_certificate_evidence` |
| Corruption fail-closed | `retention.py: Collector.mark` | `test_corrupt_retention_metadata_blocks_gc_without_deletion`, `test_missing_required_descendant_and_unknown_schema_fail_closed`, `test_unsupported_or_changed_canonical_object_fails_closed` |
| HTTP 11-table/Patricia/Target | 기존 D3b transfer + D3c retained roots | `test_post_gc_all_eleven_tables_patricia_and_immutable_old_target` |
| 실제 금융 command/12 projections | 기존 `BoundedInputs`/backend presenters | `test_real_financial_writer_and_twelve_projections_after_historical_gc` |
| 명시 보호/cross-principal dedup | `retention.py: Collector.protect/unprotect` | `test_explicit_retention_release_and_cross_principal_shared_content` |
| Synthetic admission/default 격리 | `retention_schema.py: assert_owned/connect`, `http.py: create_app` | `test_positive_synthetic_ownership_and_default_runtime_isolation`, `test_http_release_same_original_credential_idempotent_and_no_gc_route` |
| 정상 경로의 graph/history scan 금지 | 기존 D3a/D3b 경로와 fixed-size profile hooks | `test_normal_http_requests_do_not_scan_history_or_gc_graph`, 48-cell SQL/EXPLAIN benchmark |

## AA. Normal runtime 격리

`backend/app`/normal routes/auth/session 구현, financial formulas, Snapshot v7,
OfflineBaseline/pending/journal/mobile/deployment 코드는 변경하지 않았다. Source 검사와
기존 default app regression으로 inactive 경계를 확인한다. 새 checkpoint 및 WAL은
자가 소유 실험 sandbox에서만 명시 설치한다.

## AB. 제한

Current 또는 승인된 live obligation만 재구성 보장 대상이며 arbitrary historical server rollback은
제공하지 않는다. Original token row/epoch가 남아 있는 replay evidence는 유한 budget에 남는다. Corrupt
orphan도 GC를 막으며 자동 수선하지 않는다. Mark는 maintenance O(N), batch 후 전체 재검증은
추가 비용이다. Maintenance는 명시 호출이며 production scheduler/관리 command는 없다.
Busy/stale mark는 caller가 새 snapshot으로 재시도한다. 자동 무제한 retry를 하지 않는다.
기존 D1 capture/change/fence와 historical certificate 증거는 보존하므로 계속 증가할 수
있다. 이 GC가 전체 SQLite의 무한 사용에 대해 고정 용량을 보장한다는 주장은 하지 않는다.
회수하는 immutable representation 및 D3 observation budget과 구분한다.

## AC. T6.6E/R1 의존성

**DEFERRED TO T6.6E:** mobile segmented store/C1 validation/durable publication/frozen B/J/
pending/reconciliation. 서버 pin을 기기의 모든 cache로 확대하지 않는다.
**DEFERRED TO R1:** large restore/protected segmented restore transitions 및 그 실제 durable
obligations adapter. Existing standalone Snapshot v7/pre_restore/pre_reconcile 파일은 이 GC의
object graph가 아니며 읽거나 삭제하지 않는다. Future obligation은 trusted explicit API로
durably pin한 뒤 작업해야 한다. 현재 없는 backup roots를 발명하지 않았다.

## AD. Production 안전

Production DB/API/credentials/services/.env/backup에 접근하지 않았다. 배포·restart·APK 설치,
production migration/reading dry-run은 수행하지 않았다. 모든 실제 삭제는 직접 생성한
폐기용 synthetic SQLite의 immutable/cache/완료 lifecycle metadata에 한정한다.

## AE. Commit/push

최종 acceptance gates 통과 후 관련 13개 파일만
`feat(backend): finalize isolated retention and safe object GC`로 commit/push한다.
이 문서를 포함하는 commit이 최종 구현 revision이며 self-hash 순환을 피하기 위해 그 hash는
최종 응답/Git에서 확인한다. HEAD/main/origin/main/실제 remote main과 clean tree를 재검증한다.
Commit/push는 deployment 허가가 아니다.

## AF. 다음 단계

내부 구현/회귀/합성 GC/측정 gate를 통과했다. 알려진 unresolved Critical/High/Medium
구현 결함은 0/0/0, D3c blocker는 0이다. 이는 독립 감사 통과를 뜻하지 않는다.
**T6.6D3c COMPLETE — READY FOR INDEPENDENT IMPLEMENTATION AUDIT.**
독립 D3c 구현 감사를 요청한다. 감사 전 T6.6E 시작 및 production 배포는 승인하지 않는다.

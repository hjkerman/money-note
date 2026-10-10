# T6.6D3a — 격리 coherent observation 저장소와 원자적 target pin

## A. 판정·시작 Git 상태

내부 최종 판정은 **T6.6D3a COMPLETE — READY FOR INDEPENDENT IMPLEMENTATION AUDIT**다.
독립 D3a 구현 감사와 운영 활성화 승인을 대신하지 않는다. 알려진 미해결 D3a
Critical/High/Medium은 0/0/0, D3a blocker는 0이다. 미구현 후속 범위는 아래에 별도로 기록한다.

시작 시 branch는 `main`, HEAD = local main = origin/main = 실제 remote main =
`07e5826cb179908d120df01004b83297757cb83e`, working tree는 clean이었다.
실제 parent는 `158fbaab6867e0edda6b37647e129b743dd077b8`이다.
사용자가 제공한 독립 D2b 감사 PASS는 선행 증거이며 이번에 다시 수행한 독립 감사가 아니다.

**IMPLEMENTED:** committed complete D2b generation 검증, read-only 금융 scope,
coherent Target, original credential/terminal guard, atomic root pin, persisted
observation, 재조회·만료 거부·cold-bootstrap epoch 무효화다.

**NOT ACTIVATED:** 정상 startup/profile/writer/API/mobile은 새 저장소를 사용하지 않는다.
**DEFERRED TO D3b:** HTTP negotiation/transfer/typed path 권한 검증이다.
**DEFERRED TO D3c:** 일반 lease release/renewal/retention/GC다.
**DEFERRED TO T6.6E:** mobile segmented durable store/publication/migration이다.

## B. 변경 파일·격리 범위

| 파일 | 책임 |
| --- | --- |
| [observation.py](../backend/isolated_sync/observation.py) | `ObservationRepository`, `accepted_generation`, `ObservationInputs`, `financial_scope`, `hot_projections`, 오류·limit·context |
| [observation_schema.py](../backend/isolated_sync/observation_schema.py) | 자체 생성 synthetic DB의 checkpoint `1000004`, exact schema admission, `ObservationSandbox/Connection` |
| [inputs.py](../backend/isolated_sync/inputs.py) | 기존 pure input query를 `MaintainedInputs`에 분리; writer `BoundedInputs`의 별도 lifetime/overlay 유지 |
| [finalization.py](../backend/isolated_sync/finalization.py) | exact 확장 profile을 받는 admission, cold bootstrap의 격리 epoch hook; 기본 D2b 계약 유지 |
| [test_isolated_sync_observation.py](../backend/tests/test_isolated_sync_observation.py) | 금융·인증·pin·중단·동시성·오류·격리 테스트 |
| [t66d3a.py](../scripts/benchmarks/t66d3a.py) | 자체 생성 DB 전용 HOST 측정; SQL plan/row/object/byte 계측 |
| [test_t66d3a.py](../scripts/benchmarks/test_t66d3a.py) | 출력 경로·덮어쓰기 거부 및 반환 BLOB byte 계측 검증 |
| [summary.json](benchmarks/t66d3a/summary.json) | compact 실측 요약; 전체 표본·plan은 `/tmp` 원본 |

이번 변경에는 `backend/app/`, mobile, frontend 제품 source 수정이 없다.
다만 시작 commit의 D2b에는 기존 app 파일의 명시적 opt-in branch가 이미 있다.
“기존 app 파일에는 격리 관련 코드가 전혀 없다”는 주장은 하지 않는다.
이 작업은 그 branch를 정상 runtime에서 활성화하지 않는다.

## C. Complete D2b generation 검증

**IMPLEMENTED / VERIFIED:** `accepted_generation()`은 자기 저장소의 새 connection에서
`BEGIN IMMEDIATE`를 얻은 뒤 D2b `generation()`을 호출한다. 검사 범위는 다음과 같다.

- `sync_current`의 namespace/raw schema/revision/raw/index/tx와 `sync_commits`의
  `complete` certificate 일치, 실제 revision singleton과 정수·비음수 일치.
- `target_revision - base_revision = change_count`, 변경이 있는 같은 epoch의
  capture certificate 존재와 revision/count 일치. O(N) bootstrap은 R→R을 허용한다.
- 정확한 11개 table descriptor와 각 root object의 hash/C1/context/table/height/count/range.
- global facts root의 structural version/count, maintained-input proof의 정상 root.
- strict schema와 모든 기존 capture/revision trigger의 exact 정의.

D1 `capture_only`만으로는 complete authority를 만들 수 없다. Current certificate 삭제,
stale R, missing/corrupt root, 잘못된 input proof, stale cash aggregate,
unapproved schema를 거부한다. `test_invalid_accepted_generation`,
`test_changed_complete_generation_requires_capture_certificate`가 해당 증거다.

이 검증은 D2b bootstrap 및 보호된 atomic finalizer의 완전성 보증을 계승한다.
매 관측마다 모든 descendant를 재검증하는 임의 bitrot 전체 scrub은 아니다.
조회한 객체는 hash/C1/type 검사를 받고, 전송 descendant 검증은 D3b의 별도 의무다.

## D. Observation identity

T6.6C §9·§15의 필드 의미를 바꾸지 않는다. Response는
`protocol/request_id/status/observation_id/validated_at/expires_at/base_sync_root/change_kind/target/inline_objects`다.
`inline_objects=[]`이며 아직 transfer를 구현한 것이 아니다.

Target은 정확히 `ns/principal_id/versions/revision/context/raw_ref/index_ref/hot_ref/control_ref/sync_root`다.
`sync_root`는 기존 D2a `roots.sync_root()`의 `view` domain/C1로 계산한다.
raw root, global facts root, maintained-input proof, legacy Snapshot fingerprint는 별개다.

`request_id`와 observation ID는 canonical UUIDv4다. Retry identity는 원래
credential hash + request UUID + exact C1 request bytes다. 같은 요청은 같은 유효
observation을 반환하고, 같은 UUID의 다른 body는 `REQUEST_CONFLICT`다.
`test_idempotent_retry_request_conflict_and_quota`가 검증한다.

## E. Dataset epoch·revision

NS는 D2b가 이미 저장하는 server/dataset/epoch UUID와 정확히 일치해야 한다.
Revision은 row-trigger counter이며 연속 client revision을 요구하지 않는다.
같은 epoch·같은 R의 다른 raw/index root는 `BASE_INVALID`로 거부한다.
Sensitive-only mutation은 raw/index가 같아도 R을 전진시키며 `raw` 전이다.

Connection 재열기는 cold startup이 아니다. 명시적 `sandbox.bootstrap()`은 기존 v1대로
EXCLUSIVE O(N) 새 epoch를 만든다. 같은 transaction의 `_epoch_bootstrapped()`가
이전 NS observation을 `retired`, 그 pin을 inactive로 전환한다.
Object/certificate 삭제나 일반 GC를 수행하지 않는다.
이전 epoch lookup은 `EPOCH_CHANGED`; 새 epoch observation은 새 NS를 사용한다.

## F. Principal·인증 guard

원래 선택된 `BundleCredential(token_hash,user_id)`와 live caller `guard`를 필수로 받는다.
Guard는 취소·auth-generation 전이 시 원 credential과 다른 값 또는 실패를 반환해야 한다.
단순 cached user ID는 충분하지 않다. D3b는 이 caller ticket을 실제 요청 lifecycle과
연결하고 기존 인증 middleware의 credential 선택 규칙을 재사용해야 한다.

`_guard()`는 writer lock 이후 SQL로 원 session hash의 user, expiry, active 상태를
확인하고, pin 전과 모든 쓰기 뒤 COMMIT 직전에 다시 확인한다.
`last_seen_at`이나 금융 row는 갱신하지 않는다. 다른 token으로 자동 재선정하지 않는다.
Wrong principal·same-user 새 token·guard 누락·취소·inactive/expired session은 거부한다.

기존 제품은 복수 active principal이 동일 단일 장부를 보는 모델이다.
신규 owner별 금융 행 격리를 발명하지 않았다. Observation과 lookup은 원 principal 및
원 credential에 묶이며 서로 다른 인증 문맥에서 재사용할 수 없다.

## G. 금융 evaluation context

`Evaluation.wire()`는 `evaluation_date/timezone_offset_minutes/financial_engine`을 만든다.
Date는 실제 `date`, offset은 정수 −1439..1439, engine은 reviewed artifact의 SHA-256이다.
현재 서버 날짜/offset provider를 사용할 수 있으나 테스트는 명시적 synthetic context다.
같은 R에서도 날짜·offset·engine이 바뀌면 오래된 hot을 새 context로 재사용하지 않는다.

`versions()`는 sync/canon/structural/Snapshot/recurring interpretation과 raw schema,
projection schema, policy registry digest를 고정한다. Engine artifact는 고정된 app 및
isolated source·Judgment YAML의 path/content hashes다. 프로세스 내 immutable이며
production release compatibility 승인이 아니다. D3b rollout은 이 artifact와 지원
allowlist를 실제 release packaging에 포함·검증해야 한다.

Terminal 시 evaluation/provider 및 versions를 재평가하여 construction 중 날짜·offset·
engine·registry 변경을 거부한다. 유효한 기존 observation lookup은 그 observation의
고정 context를 유지한다. 새 날짜로 projection을 바꾸어 응답하지 않는다.

## H. 별도 read-only 금융 input scope

`ObservationInputs`는 `MaintainedInputs`를 공유하지만 writer `BoundedInputs`가 아니다.
`financial_scope()`는 accepted generation/input proof에 묶고 SAVEPOINT + `query_only=ON`,
transaction·total_changes·active lifetime을 검사한다. 종료 후 사용과 직접 SQL 쓰기도 거부한다.
현재 accepted committed state이므로 writer net overlay는 빈 집합이고 D1 events를 읽지 않는다.

기존 maintained cash prefix, closed-month top-k count, policy horizon,
event totals 및 indexed ownership/source/reverse lookup을 소비한다.
조회한 aggregate는 accepted input Patricia proof와 대조한다. 숨은 history fallback은 없다.
`test_read_scope_lifetime_and_no_writes`, stale-cash negative case가 검증한다.

## I. 12개 hot 금융 projection 동등성

`hot_projections()`는 기존 authoritative presenter/formula를 호출한다.
Summary·payment allocation·할인·month-close eligibility·Judgment를 복제하지 않는다.
Money validation과 `AuthoritativeProjections` schema admission을 전후로 유지한다.

| 실제 projection | 기존 backend 계산 |
| --- | --- |
| `month_close_status` | `month_close_status` |
| `entries` | `list_entries`, `_present_entries` |
| `panels` | `list_panels`, `_present_panels` |
| `summary` | `_summary_values_from_read_view` |
| `card_payment_status` | `current_payment_status` |
| `judgment` | `app_judgment` |
| `confirmed_planned_entries` | `list_confirmed_planned_entries`, `_present_entries` |
| `cash_flows` | `list_cash_flows`, `_complete_rows(CashFlow)` |
| `settings` | 비민감 `list_settings` 결과 |
| `owner_discount_month` | `discount_month_status(...,owner)` |
| `family_discount_month` | `discount_month_status(...,family)` |
| `transit_discount_profile` | `transit_discount_profile_status` |

`test_all_twelve_legacy_projection_parity`는 기존 B-1 `_construct/_prepare`의 full bundle을
독립 oracle로 사용한다. 격리 schema version/trigger validator gate만 테스트에서 대체하며
금융 계산은 원본이다. 9/30·10/5·10/31·11/1 × base/recurring/fixed/policy/archive/cash
24개 조합에서 12개 전체 값을 비교한다. Oracle의 O(N) Snapshot은 테스트에만 있다.
Judgment random 문구는 양쪽 동일 seed로 비교하고 금액/null/배열 순서도 exact 비교한다.
운영 문구의 요청별 변동은 기존 의미이며 같은 R의 비금융 hot 변경은 명세 §9의 `context` 전이다.

`share_pin_hash/share_pin_is_default`는 hot settings와 raw transfer에서 제외한다.
실제 금융 계산 내부 settings를 바꾸지 않으며 민감 값을 다른 transfer 표현으로 만들지 않는다.
`test_sensitive_setting_revision_only`는 R 전진·raw root 재사용·object 내 sentinel 부재를 확인한다.

## J. Coherent target metadata

하나의 짧은 `BEGIN IMMEDIATE` 안에서 accepted certificate, aggregate proof,
financial input, fixed context, hot/control, target 및 pin을 만든다.
Source writer는 이 경계에 진입할 수 없으므로 R/raw/index/aggregate가 섞이지 않는다.
Terminal current `tx_id/NS/R/raw/index`도 처음 선택값과 대조한다.

`hot/control`은 명세의 정확한 필드로 만든다. Control은 v7 해석·11개 column 목록·
정책 horizon·default policy·최초 exported_at을 보존한다.
동일 NS/R/versions/context/hot bytes이면 immutable control을 재사용한다.
Hot/control에 D2b Store 전용 `raw_schema` 필드를 몰래 추가하지 않는다.
`_put_view()`는 exact object/domain/C1 identity와 충돌 여부를 확인한 별도 저장 경로다.

## K. Atomic root pin

`create()`의 순서는 다음과 같다.

1. 새 자체 connection에서 metadata writer lock 획득 및 exact schema admission.
2. 원 credential·accepted D2b generation·fixed context 확인.
3. read-only hot/control/Target 준비와 base contract 검사.
4. terminal guard/current identity/quota/byte/deadline 검사.
5. immutable hot/control, view metadata, observation 및 5개 root pin 저장.
6. guard/context/expiry/deadline 재확인 후 하나의 SQLite COMMIT.

실패하면 context manager가 transaction 전체를 rollback한다. Response를 return하기 전에
COMMIT이 성공해야 한다. COMMIT 뒤 응답 유실은 complete orphan observation일 뿐이며
동일 request ID로 조회할 수 있다. 금융 command receipt나 pending retirement가 아니다.

## L. Root coverage·reachability

| pin role | 대상 | 외부 transfer root 후보 |
| --- | --- | --- |
| `raw` | 11-table descriptor를 포함하는 raw-root | 예 |
| `index` | complete global facts index-root | 예 |
| `hot` | 이번 context의 12 projections | 예 |
| `control` | Snapshot 해석·정책 metadata | 예 |
| `input` | certificate의 server-local maintained-input proof | 아니오 |

5개 role은 observation ID와 함께 같은 transaction에서 저장하고 FK로 object 존재를 요구한다.
`sync_observation_pin_hash(hash,active)`가 active 외부 pin 수의 indexed source다.
Descendant를 펼치거나 모든 object에 per-observation pin을 복제하지 않는다.
기존 D2b typed child edges와 root pin이 후속 reachability GC의 입력이다.
`roots()`는 4개 typed Ref만 반환하며 hash 자체를 권한으로 취급하지 않는다.

## M. Lease·expiry metadata

UTC wall-clock `validated_at/expires_at`을 persisted metadata로 저장한다.
Lease는 최대 900초, active principal당 최대 4개다. Process monotonic clock은
transaction elapsed 측정에만 쓰며 재시작 timestamp로 저장하지 않는다.
관측 생성 뒤 DB lock은 해제하고 미래 download 동안 read transaction을 유지하지 않는다.

Lookup은 원 credential/current epoch/contract/complete certificate/5개 active pin과
root 객체를 재검증한다. Current R이 바뀌어도 같은 epoch의 pinned old target은 유효하다.
만료를 확인한 observation은 `retired`를 저장하여 이후 wall-clock 역행에도 부활하지 않는다.
이때 pin은 보호한 채 남기고 해제는 D3c에 맡긴다. 일반 clock 신뢰·교정 정책은 운영 의존성이다.

## N. 동시성·terminal TOCTOU

`test_writer_before_lock_acquisition`은 Event로 observer의 BEGIN 진입을 고정하고 writer의
credential 삭제/금융 commit/rollback을 수행한다. Guard는 대기 이전 값이 아니라 lock
획득 뒤 실제 committed session/generation을 본다. Bootstrap 후 epoch mismatch도 거부한다.
`test_terminal_identity_changes_before_lock_acquisition`은 BEGIN 직전 gate를 두고
epoch bootstrap·caller 취소·principal 교체를 각각 완료한 뒤 observer를 풀어 거부를 확인한다.
`test_uncommitted_authority_not_observable`은 finalize됐지만 미commit인 target을 노출하지 않는다.

`test_observation_lock_prevents_mixed_writer_target`은 pin 전 writer를 시도하여 lock 충돌을 확인한다.
`test_concurrent_observers_same_target`은 두 observation의 raw/index 및 10개 pin을 독립 SQL로 확인한다.
다른 generation 관측, old pin의 유지, writer rollback은 별도 비교한다.
Repository의 lock wait 기본값은 1초이고 D2b writer timeout은 바꾸지 않았다.

## O. Crash·restart

`test_process_kill_atomic_observation`은 fork subprocess를 validation/roots/pin_raw/pin_input/
before_commit/after_commit 6개 boundary에서 SIGKILL한다. Fresh connection으로 raw state,
독립 D2b graph/facts oracle, auth rows, observation/pins를 확인한다.
COMMIT 전에는 observation이 없고 COMMIT 후에는 완전한 observation만 존재한다.
Caller가 ID를 받지 못한 after-COMMIT도 원 request ID로 복구한다.

이는 선택한 process interruption의 SQLite recovery 증거다. 임의 instruction-level crash나
hardware power-loss/Android durability 증명이 아니다. Mobile durability는 T6.6E 이후 gate다.

## P. Failure injection

Validation/roots/각 5개 pin/before-COMMIT 8개 failure에서 observation/pin 전체 rollback과
금융·revision·auth 상태 불변을 확인한다. Persisted response/Target shape 손상도 value-free
`REQUIRED_METADATA_INVALID`로 분류한다. Pin 누락, capture 누락, stale aggregate,
wrong base/epoch/schema/credential/context, deadline/resource 초과를 fail closed한다.

Schema `1000004` 설치는 D2b profile 위 metadata-only atomic transaction이다.
재설치는 strict 검증만 수행한다. 새 exact table/index contract를 전달하며 unknown schema를
허용하는 예외를 추가하지 않았다. 기존 D1/D2b fence와 finalizer를 우회하지 않는다.
별도 safety test `test_d3a_isolated_migration_failure_is_atomic`은 DDL 중간 실패 뒤
fresh connection의 user_version/전체 dump가 D2b와 동일하고 재시도가 성공함을 확인한다.
`test_d3a_restored_synthetic_database_requires_new_epoch`는 자체 생성 DB의 SQLite backup을
다른 자체 생성 DB에 복원한 뒤 mandatory cold bootstrap의 새 epoch와 old-observation 거부를 확인한다.

## Q. Error·retry 계약

| repository code | action | caller 의미 |
| --- | --- | --- |
| `AUTH_REQUIRED`, `PRINCIPAL_OR_SESSION_CHANGED` | `reauthenticate` | 기존 original credential 폐기·새 인증/ticket 필요 |
| `EPOCH_CHANGED`, `BASE_INVALID` | `full_resync` | frozen B/J/pending 보존 후 명시적 full 경로 |
| `ROOT_NOT_READY` | `retry_same` | busy/미완료 target/deadline; bounded 전체 retry |
| `OBSERVATION_CONFLICT` | `new_observation` | context/guard coherence 재평가 |
| `OBSERVATION_EXPIRED`, `OBSERVATION_INCOMPLETE` | `new_observation` | 새 request ID·coherent target 필요 |
| `LEASE_LIMIT`, `TRANSFER_BUDGET` | `retry_same` | 실제 limit/expiry/용량에 맞춰 대기·요청 조정 |
| `UNSUPPORTED_CONTRACT`, `INVALID_EVALUATION_CONTEXT` | `blocked` | compatibility/입력 수정; implicit legacy fallback 금지 |
| `REQUIRED_METADATA_INVALID`, `PIN_TRANSACTION_FAILED`, `REQUEST_CONFLICT` | `blocked` | 손상/내부 실패/서로 다른 요청; 자동 성공 처리 금지 |

Repository는 한 번만 시도하며 hidden retry/reselection이 없다. 최대 3회의 HTTP caller
retry 및 code→status mapping은 D3b가 구현할 의무다. 오류에 SQL 값/token/row를 출력하지 않는다.

## R. No hidden O(N) 근거

정상 관측 경로에는 Snapshot export, legacy flat hash, `Tree.rows/objects`,
`Index.build/facts`, `read_state/rebuild`, aggregate 재생성이 없다.
`test_forbids_full_history_and_graph_rebuild`는 주요 전체 순회 helper를 실패하도록 대체한다.
SQL EXPLAIN/VM/result rows와 object reads를 규모별로 계측하여 source 검사와 교차 확인한다.

허용된 비용은 H(current/planned/panels/active payment와 실제 reference closure),
고정 11개 root header, bounded Patricia proof 경로, 정책 horizon과 indexed top-k/prefix다.
H에는 현재 계약이 반환하는 비민감 settings/정책도 포함한다. H와 reference fan-in 자체가
무상한이므로 모든 계정의 O(1)을 주장하지 않는다.
Schema/config singleton과 cap이 있는 observation metadata 조회를 historical scan과 구분한다.
Pin 생성은 정확히 5개의 root metadata이며 descendant 순회 0이다.

## S. HOST scaling 실측

최종 실측은 **24 cells / 480 trials / 560 observations**, historical full scan **0**이다.
각 값은 complete repository 호출의 **median / p95, ms**다.

| N | 금융 무변경 | card 후 | cash 후 | 날짜 전이 | observer 2개 | writer 경합 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 376 | 225.53 / 227.91 | 222.78 / 237.75 | 223.85 / 236.35 | 211.52 / 220.95 | 431.49 / 494.55 | 210.80 / 244.62 |
| 1000 | 245.67 / 267.23 | 233.53 / 261.54 | 233.94 / 235.68 | 232.25 / 236.35 | 513.42 / 519.19 | 259.15 / 277.10 |
| 5000 | 240.78 / 243.28 | 231.97 / 242.40 | 231.70 / 238.56 | 238.17 / 239.61 | 498.77 / 519.42 | 249.61 / 271.05 |
| 10000 | 245.94 / 255.63 | 233.36 / 235.46 | 232.47 / 236.77 | 227.08 / 230.11 | 511.06 / 524.76 | 256.19 / 265.33 |

10k 금융 무변경의 단계별 median은 accepted validation **100.74ms**, read-only 금융 계산
**53.78ms**, Target metadata 잔여 구간 **61.63ms**, pin transaction 후반 **24.22ms**,
COMMIT **2.42ms**다. 단계 median의 합을 total median이라고 주장하지 않는다.
Target 잔여 구간은 각 동일 표본에서 total_ms − validation/financial/pin/commit을 계산한 값이며,
C1 hot/control/Target 준비·hash·budget/terminal 검사 등을 포함한다. 별도 CPU sampler 결과가 아니다.

10k 단일 관측은 object reads **34**, root refs **5**, 실제 relationship rows **6**이다.
금융 무변경 반환 행 **2,127**은 모든 N에서 같고 SQL은 SELECT **424**, PRAGMA **384**,
INSERT **9**, UPDATE **1**, BEGIN **1**, SAVEPOINT/RELEASE 각각 **7**이다.
반환 행에는 schema/config metadata 및 반복 hot 조회가 포함되며 고유 금융 행 수가 아니다.
수행한 모든 SELECT의 EXPLAIN을 확인했고 원장 전체 SCAN/전체 object enumeration은 없었다.

10k 금융 무변경의 returned BLOB은 **23,276B**, bound write BLOB median은 **95,262B**,
새 immutable hot/control object는 **2개 / 90,357B**다. Existing Judgment random presentation
때문에 이 cell의 20개 응답은 모두 허용된 `context` 전이였다. “금융 무변경”을
“hot bytes까지 동일해서 쓰기가 0”이라고 표현하지 않는다. 재현 가능한 동일 hot bytes의
`unchanged` 전이와 control 재사용은 별도 고정-seed 테스트가 확인한다.

Python **3.12.3**, SQLite **3.45.1**, Linux **6.8.0-146**, Intel **i7-8750H**, logical CPU **12**,
SQLite **DELETE / synchronous=2(FULL) / page=4096**이다. Bootstrap은 N별 1회 실측으로
376 **2,755.28ms**, 1k **7,001.62ms**, 5k **35,218.71ms**, 10k **74,345.00ms**였다.
Process peak RSS 최대 **325,348KiB**는 bootstrap/oracle/전 cell 누적이며 관측 전용 peak가 아니다.

원본: `/tmp/money-note-d3a-final-measurements.json` (**803,192B**), SHA-256
`586f791c8f3efd8608b3248e39076e058f084b928479130d4aacbdfc3f838e13`.
[compact summary](benchmarks/t66d3a/summary.json)에 source hashes와 전체 cell 통계를 남겼다.

이는 HOST/SYNTHETIC backend metadata 측정이며 phone/network/deployed latency가 아니다.

측정은 N=376/1k/5k/10k, hot ledger 105행 고정, cell당 warmup 3회+측정 20회다.
No-change/card 후/cash 후/date 전이/observer 2개/10ms writer contention의 24개 cell이다.
Card/cash mutation은 각 cell 준비 때 한 번 수행하고 관측 표본마다 bootstrap하지 않는다.
독립 full row/facts/graph oracle과 EXPLAIN은 관측 timing 밖에서 실행한다.
Full oracle은 최초 및 card/cash로 raw state가 바뀐 뒤 각 1회이고, date/concurrency cell은
같은 이미 검증된 raw generation을 사용한다. 각 N의 initial bootstrap은 별도 1회이며 O(N) 예외다.
준비 관측의 accepted Target을 base로 전달하며 그 lease를 폐기하지 않고 synthetic clock을
901초씩 전진시킨다. Request별 Judgment 문구 변동은 허용된 `context` 전이로 기록한다.

전체 표본과 SQL plan은 신규 `/tmp` JSON에만 기록하고 compact 통계만 commit한다.
Returned BLOB bytes와 bound write BLOB bytes는 논리적인 materialization/쓰기 payload다.
SQLite page/file I/O·HTTP bytes를 직접 측정한 값이 아니다. VM counter는 100-step 단위 하한이다.
Pair workload의 total latency/SQL/rows는 두 관측 합계, phase metrics는 첫 관측 값이다.
Peak RSS는 같은 process의 누적 maximum이며 cell 전용 peak로 해석하지 않는다.
전체 회귀와 일부 병렬 실행된 shared HOST이므로 절대 latency 비교에는 간섭이 있다.

T6.6A의 full gzip/Brotli 절감과 이번 CPU/input/metadata 경로는 별개다.
압축 full bundle보다 wire가 얼마나 작은지 측정하지 않았고 독립 median을 더하지 않는다.
기존 D2b audit latency도 이번에 측정한 observation latency가 아니다.

## T. Resource bounds

| 자원 | 기본값·제약 |
| --- | --- |
| lease / active principal observations | 900초 이하 / 4개 이하 |
| total persisted records | 4,096개; 초과 fail closed |
| per-observation logical metadata | 8MiB; 요청/response/hot/control 검사 |
| global logical metadata budget | 64MiB; O(1) monotonic counter, 같은 pin transaction에서 증가 |
| transaction elapsed | 10초, configurable ≤60초; terminal soft deadline |
| SQLite lock wait | 1초, configurable 1..5,000ms |
| inline request budget | 0..1MiB; 실제 inline transfer 없음 |
| benchmark process | address space 2GiB / CPU 1,800초 / 지정 N만 허용 |

Global byte charge는 response/request/Target/view identity, 새 hot/control bytes와
보수적 framing 여유를 포함한다. 실제 SQLite page size/물리 disk quota의 대체가 아니다.
Counter 감소·record 회수는 D3c 전에는 없으므로 장시간 반복 시 명시적 자원 한도로 멈춘다.
현재는 폐기용 DB 전용이다. Soft deadline은 작업 중 OS-level preemption이 아니며
admission에 실패한 transaction이 authority를 남기지 않는 경계다.

## U. D3b repository interface

`ObservationRepository.create(credential,request_id,guard,base,protocol,inline_bytes)`는
committed metadata response를 만든다. `lookup(id,credential,guard)`는 fresh auth/epoch/TTL/
certificate/pins/root를 검증한 동일 response를 반환한다. `roots(...)`는 4개 typed roots만 반환한다.

**DEFERRED TO D3b:** 기존 인증 credential 선택, original request generation ticket,
capability/HTTP 상태/no-store, object chunk/base64/size budget, typed parent-child path 검증,
fresh terminal auth 및 immutable engine artifact distribution이다.
현재 API는 arbitrary object bytes/enumeration/download authorization을 제공하지 않는다.
Known hash만으로 fetch를 허용할 수 없다. 독립 D3a 감사 전 D3b 착수 준비 완료로 표현하지 않는다.

## V. D3c retention·GC 의존성

**DEFERRED TO D3c:** serialized release/expiry/renewal, active pin accounting의 증명,
root→typed edges reachability, budget 회수, orphan/staging 정리와 race-proof GC다.
D3a는 expired pin을 임의 해제하거나 current가 바뀌었다는 이유로 object를 삭제하지 않는다.
Mandatory epoch bootstrap 무효화 hook은 일반 GC와 구별한다.

완전한 시스템의 accepted/previous/frozen B/J/pending/reconciliation/30 backup·restore artifact
pins는 observation만으로 대체할 수 없다. 이 작업은 그 retention correctness를 입증하지 않는다.
Large restore/Mobile Wins 지원은 별도 R1, mobile generation publication은 T6.6E다.

## W. 실행 검증·재현

최종 전체 backend는 **1,050 tests + 1,540 subtests PASS**, **933.41초**다.
이 안에 새 D3a backend tests **97개**가 포함된다. 기존 D1/D2a/D2b·Snapshot·
authoritative endpoint·금융·migration 회귀도 이번 최종 source에서 실제 실행했다.
최종 D3a 단독 suite도 **97 PASS / 66.68초**로 별도 재실행했다.
Safety/diagnostic corpus는 신규 D3a 4개를 포함한 **50 tests PASS**, **4.42초**다.
Ruff, compileall, shell syntax, 문서 링크 9개·source hashes 5개·test reference 대조,
JSON 통계 검증, `git diff --check`, frontend `npm run build`도 PASS다.
Full backend 및 safety에는 기존 `Starlette TestClient/httpx` deprecation warning 각 1건이 있으며 실패가 아니다.

다음 명령은 repository root 기준이다. 성공 로그 전체는 출력하지 않는다.

```bash
cd backend
../.venv/bin/python -m pytest -q tests/test_isolated_sync_observation.py
../.venv/bin/python -m pytest -q --durations=8
cd ..
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
.venv/bin/ruff check backend scripts/benchmarks/t66d3a.py scripts/benchmarks/test_t66d3a.py
.venv/bin/python -m compileall -q backend/isolated_sync backend/tests/test_isolated_sync_observation.py scripts/benchmarks/t66d3a.py scripts/benchmarks/test_t66d3a.py
bash -n scripts/dev-server.sh scripts/deploy-server.sh scripts/release-mobile.sh
.venv/bin/python scripts/benchmarks/t66d3a.py --output /tmp/money-note-d3a-reproduction-new.json
cd frontend
npm run build
cd ..
git diff --check
```

전체 backend는 D1 capture/fence, D2a codec/tree/index, D2b finalizer/bounded writer,
migration/schema, payment/recurring/Summary, Snapshot v7, 기존 authoritative endpoint를 포함한다.
Mobile/Flutter/Android runtime은 바꾸지 않아 해당 suite/APK 설치는 수행하지 않는다.

검증 중 발견한 sensitive hot settings 누출 가능성, repository lock wait 기본값,
손상 envelope의 오류 분류와 capture certificate 누락 검사는 내부 테스트 단계에서 수정했다.
SQLite transaction context의 종료와 handle close가 다른 점도 반영하여 성공·실패 호출의
connection을 명시적으로 닫는다. `test_repository_connections_close_on_success_and_failure`로 확인한다.
하위 `CaptureConnection.__exit__`도 이미 close하므로 이는 명시적 방어와 regression 증거이며
기존 D1/D2b connection 누수를 발견·수정했다는 주장이 아니다.
초기 benchmark의 1행 budget-table scan 오분류도 수정했다. 실패/중단/옛 code-state 실행은
최종 PASS 수치에 포함하지 않는다. 독립 감사 0건이라는 사실과 구분한다.

## X. 한계·남은 proof

정상 원장과 고정 H에서 정상 경로의 역사 전체 작업 부재를 검증한다. 임의 거대 H,
거대한 active closure, storage-full/hardware corruption의 모든 위치를 완전 증명하지 않는다.
Per-root provenance는 보호된 D2b 경로를 신뢰하며 arbitrary 외부 SQL 공격을 sandboxing하지 않는다.
읽지 않은 descendant의 임의 손상은 transfer/read 검증 및 후속 full recovery의 대상이다.

Financial presentation random 문구는 기존 동작을 유지하므로 동일 R/context의 hot Ref가
매번 같을 것을 강제하지 않는다. 명세에 허용된 context 전이이며 raw/index 재사용을 깨지 않는다.
Source-derived engine artifact의 production allowlist, D3b transfer auth, D3c retention,
mobile atomic publication, legacy v7 complete materialization adapter, R1은 아직 미구현이다.

## Y. Production 안전성

모든 DB는 `ObservationSandbox`가 생성·소유한 temporary synthetic SQLite다.
기존 DB 경로를 받는 installer나 정상 startup activation은 없다.
Production DB/API/credential/service 접근·배포·restart·migration·APK 설치는 없다.
Financial formula, Snapshot v7, OfflineBaseline v4, B/J, pending/outcomeUnknown,
reconciliation와 정상 authoritative-state acquisition은 유지한다.
GET/observation 성공은 ambiguous POST의 receipt나 pending retirement 근거가 아니다.

## Z. Commit·push 경계

모든 D3a completion gate가 통과한 경우에만 이 격리 구현·테스트·측정 요약·문서를
`feat(backend): add isolated coherent observation repository`로 commit/push한다.
최종 HEAD/main/origin/main/실제 remote main 일치와 clean 상태는 최종 인계 보고에 기록한다.
Commit은 deployment 또는 D3b/D3c 착수 승인이 아니다.

## AA. 다음 작업

별도 독립 D3a 구현 감사에서 accepted certificate/terminal auth/financial scope/
atomic pin/root coverage/SQL scaling과 process recovery를 검토한다.
감사 통과 전 D3b를 시작하지 않으며 production 활성화는 별도 승인 대상이다.

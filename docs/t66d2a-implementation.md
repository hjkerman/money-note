# T6.6D2a — 격리 canonical segments와 global facts index

## 1. 범위·기준선·판정

시작 상태는 `main`, HEAD = local main = origin/main = 실제 remote main =
`5277f7931bc3a4386832a3136d04bf373cd66709`, clean working tree였다.
사용자가 제공한 D1 독립 감사 PASS와 이번 내부 검증은 서로 다른 증거다.
이번 작업의 독립 D2a 감사는 아직 수행하지 않았다.

**IMPLEMENTED:** C1, domain hashing, immutable PK B+tree와 mutation, raw-root,
전체 structural facts와 canonical Patricia, full rebuild·검증 도구다.
**NOT ACTIVATED:** 정상 runtime import, DB migration, writer 연결, endpoint,
권위 있는 certificate 발급은 없다. D1 `capture_only`의 의미도 바꾸지 않았다.
**DEFERRED TO D2b:** epoch/descriptor 발급, capture old/new 연결, reverse closure,
root/index의 동일 transaction 저장과 pre-commit authoritative finalizer다.
**DEFERRED TO D3:** coherent observation, object transfer, lease/서버 GC다.

최종 내부 판정: **T6.6D2a COMPLETE — READY FOR INDEPENDENT IMPLEMENTATION AUDIT**.
새 D2a 131 tests를 포함한 전체 backend 850 tests + 1,540 subtests가 통과했다.
이는 독립 감사 승인이나 D2b 착수/운영 활성화 허가가 아니다.

## 2. 계약과 source 대조

[AGENTS](../AGENTS.md), [architecture](architecture.md), [domain](domain-model.md),
[Offline](offline-mode.md), [project-state](project-state.md), [known-issues](known-issues.md),
[T6.6A](t66a-payload-attribution.md), [T6.6B](t66b-hot-cold-design.md),
[T6.6C](t66c-delta-sync-protocol.md), [D1](t66d1-implementation.md)를 기준으로 했다.
[기존 schema](../backend/app/db.py), [migration](../backend/app/db_migrations.py),
[Snapshot](../backend/app/services/snapshot.py),
[raw ownership](../backend/app/services/financial_relationships.py),
[recurring ownership](../backend/app/services/legacy_recurring.py),
[모바일 raw 구조](../mobile/lib/src/authoritative_snapshot_validation.dart)와 대조했다.

새 facts는 Category B의 raw 저장·복구 관계다. 할인, payment partition/remaining,
Summary, month-close eligibility, archived effective amount를 계산하지 않는다.
Backend financial authority, OfflineProjection, B/J, pending/outcomeUnknown,
Snapshot v7와 OfflineBaseline v4는 변경하지 않았다.

## 3. 구현 모듈과 API

| 파일 | 구현·호출 계약 |
| --- | --- |
| [canonical.py](../backend/isolated_sync/canonical.py) | `decode_json`, `decode_c1`, `encode`, `hash_bytes`, `Namespace/Context/Key/Object`, `row_hash` |
| [raw.py](../backend/isolated_sync/raw.py) | exact 11-table column/type/domain, `Row.make`; direct `Row` 생성도 admission·PK 일치를 검사 |
| [segments.py](../backend/isolated_sync/segments.py) | `Tree.build/lookup/put/delete/move/validate`, immutable `Node`, `raw_root` |
| [facts.py](../backend/isolated_sync/facts.py) | `row_facts`, `build_facts`, `validate_state`, `validate_index`, borrowed-connection `read_state` |
| [patricia.py](../backend/isolated_sync/patricia.py) | `Fact`, persistent `Index.build/lookup/put/delete/facts/validate/object` |
| [roots.py](../backend/isolated_sync/roots.py) | exact Target envelope shape·U64·version/context 확인 후 `sync_root` hash만 계산 |
| [rebuild.py](../backend/isolated_sync/rebuild.py) | explicit 전체 raw state → complete trees/raw-root/index; read-only mapping으로 반환 |

모든 입력은 명시적 값/borrowed connection이다. 정상 설정 경로의 DB를 자동으로 열지 않는다.
`Object`와 `Row`는 immutable bytes를 보유하고 decoded view는 사본이다.
Tree/Index의 기존 version도 mutation 뒤 보존된다. `Node/Tree/Index`의 low-level
dataclass는 trusted algorithm representation이지 외부 bytes admission API가 아니다.
Untrusted representation에는 explicit 전체 invariant 검증·complete F 비교가 필요하다.
`raw_root`/`sync_root` hash 계산 자체는 완전한 authority 승인이나 금융 정확성 증명이 아니다.

## 4. C1과 SQLite storage class

C1은 UTF-8, BOM/공백/final newline 없음, scalar key 정렬, array 순서 유지,
정확한 control escape와 non-ASCII 원문을 사용한다. Unicode normalization/repair는 없다.
JSON duplicate key는 escape decode 후에도 거부한다. Original numeric token을
Decimal로 먼저 검사하여 underflow·fractional rounding·범위 초과를 숨기지 않는다.
`decode_c1`은 재직렬화로 입력을 고치지 않고 exact received bytes와 C1을 비교해 거부한다.
오류는 입력 값을 포함하지 않는 `CanonicalError(REJECT_...)`로 분류한다.

| raw spec | 허용 SQLite/Python 표현 | C1 | 거부 |
| --- | --- | --- | --- |
| `i` | INTEGER / bool 아닌 signed-int64 int | 최소 decimal number | REAL/TEXT/BLOB/범위 초과; 기존 B-2 native integer domain을 확대하지 않음 |
| `n` | INTEGER 또는 지원 historical integral REAL, ±(2^53−1) | int는 정수, REAL은 `1000.0`, `-0.0` 보존 | fractional/NaN/infinity/문자열/bool/unsafe money |
| `s` | valid Unicode TEXT | 원 scalar·NUL·공백·조합형 그대로 | BLOB, isolated surrogate, 타입 불일치 |
| `d`, `m` | 실제 달력 날짜/월인 TEXT | 원 문자열 | 불가능한 날짜, 잘못된 형식 |
| `?…` | 위 표현 또는 NULL | 원 값 또는 `null` | absent column; NULL을 empty/zero로 바꾸지 않음 |

현재 authoritative column에는 허용 BLOB가 없다. Empty BLOB도 empty TEXT가 아니다.
SQLite affinity가 받아 주는 잘못된 storage class를 금융 domain으로 확대하지 않는다.
SQLite 자체가 저장 시 잃어버린 REAL −0 부호를 복원한다고 주장하지 않는다.
받은 Python REAL −0.0 및 JSON REAL token은 C1에서 보존한다.

전체 column 계약은 아래와 같다. `?`는 nullable이며 모든 column은 required다.
물리 schema의 NOT NULL/FK/UNIQUE와 추가 승인된 Snapshot raw predicates는 구별한다.

| table / PK | INTEGER `i` | money `n` | TEXT/date/month |
| --- | --- | --- | --- |
| ledger_entries / id | id, sort_order, ?due_day, ?source_planned_entry_id, discount_override | ?amount_value, ?aux_amount_value | book_section, entry_kind, ?entry_date:d, ?date_label, ?group_label, title, ?usage_place, ?usage_item, ?amount_expr, ?aux_amount_expr, ?extra_value, ?confirmed_at, ?confirmed_month:m, ?spending_category, ?payment_key, created_at, updated_at |
| monthly_panels / id | id, discount_override, sort_order, ?due_day, ?confirmed_cash_flow_id | ?amount_value, discount_amount | month:m, panel_type, title, ?spent_on:d, ?amount_expr, ?confirmed_at, ?confirmed_month:m, created_at, updated_at |
| cash_flows / id | id, sort_order, is_primary_income | amount_value | occurred_on:d, title, created_at, updated_at |
| card_payment_batches / id | id | — | usage_month:m, source, status, created_at |
| card_payment_batch_items / id | id, batch_id, entry_id | — | entry_payment_key, created_at |
| card_payment_events / id | id, ?batch_id, ?cash_flow_id | total_amount | event_date:d, event_type, note, ?idempotency_key, ?request_fingerprint, created_at |
| card_payment_allocations / id | id, payment_event_id | amount_value | entry_payment_key, created_at |
| card_payment_deferrals / entry_payment_key | ?original_sort_order | — | entry_payment_key, from_payment_month:m, target_payment_month:m, ?original_book_section, ?original_entry_date:d, ?original_date_label, ?original_group_label, ?original_title, created_at |
| notification_candidate_registrations / registration_key | target_id | — | registration_key, target, request_fingerprint, created_at |
| app_settings / key | — | — | key, value, updated_at |
| app_labels / key | — | — | key, value, updated_at |

기존 계약에 없는 새 finite domain은 만들지 않았다. `book_section`, `event_type`, registration
target은 기존 domain을 확인하며 amount allocation은 nonnegative다.
`entry_kind`, `panel_type`, status, flags에 임의 enum/0-or-1 제약을 추가하지 않는다.
단 fixed-linked cash의 flag=0은 기존 관계 제약이다.
필수 money settings는 scheduled_income/cash_flow_balance/card_limit 3개다.
선택적 base_next_month_liquidity/liquidity_status도 존재하면 기존 B-2 exact-money
문자열 문법을 검사한다. 검사 시 해석한 값으로 원 TEXT를 바꾸지 않는다.

`share_pin_hash`, `share_pin_is_default`는 SQL 조회에서 제외하고 `Row` admission에서도
값을 encoding하기 전에 거부한다. Generic codec 자체는 비밀 판별기가 아니므로
D2b는 D1 excluded marker를 transfer row로 취급하면 안 된다.

## 5. Canonical vectors·언어 간 검증·hash framing

[committed vectors](specimens/t66c-canonical-vectors.json)의 유효 8개는 exact bytes,
길이, 독립 `hashlib.sha256`과 일치했다. 잘못된 surrogate 3개는 거부했다.
기존 expected vector를 수정하지 않았다. Raw duplicate keys, fractional·underflow,
초대형 exponent/integer, noncanonical token도 fail-closed한다.

[격리 Dart formatter](../scripts/benchmarks/t66d2a_c1.dart)는 제품 모바일 코드와 무관하다.
유효 vectors 8개 + 추가 controls 11개 및 invalid surrogate 3개를 실행했다.
Python/Dart가 INTEGER extrema, integral REAL/−0, scalar key order, Unicode/NUL,
null/bool/array 및 대표 row representation에서 같은 UTF-8 bytes를 냈다.
이는 formatter parity이며 Dart의 production raw-token/duplicate-key parser 구현 증명이 아니다.

12개 기존 domain label의 framing은 정확히
`SHA256(b"money-note.sync.v1/" + ASCII(kind) + b"\0" + received_C1_bytes)`다.
Row의 preimage는 §11의 `{ns,raw_schema,table,key,value}`로 별도 처리한다.
Table root는 해당 leaf/node descriptor이며 새 `table-root` domain을 발명하지 않았다.
Raw/index/view root는 서로 다른 객체이며 기존 flat Snapshot hash와 합성하지 않는다.

## 6. B+tree·representation identity

Profile은 leaf 256행/262,144 bytes, internal fanout 32, non-root 최소 16이다.
Empty table은 유일한 empty leaf, 큰 단일 row는 oversized singleton이다.
Byte boundary는 `oversized=false`인 ordinary 후보의 길이로 검사한다.
`true` token이 한 byte 짧아지는 경계에서도 oversized 판정이 흔들리지 않는다.

Bootstrap은 PK sorted greedy packing 및 마지막 group의 균등 재분배(홀수 오른쪽)다.
Insert/update는 해당 leaf/path만 복사하며 midpoint split을 반복한다.
33-child overflow는 16/17이다. Delete는 empty leaf 제거, internal left-first borrow,
right borrow, left-first merge 및 unary-root collapse를 수행한다.
일반 삭제의 nonempty leaf merge, 선택적 maintenance compaction API는 없다.

0/1/255/256/257/511/512/513/8192/8193/10k, exact byte boundary/one byte over,
큰 Unicode singleton, internal overflow/underflow/root collapse를 검사했다.
Full invariant validator는 PK/범위/child order/height/count/bytes/hash/coverage를 검사한다.
Independent test oracle은 serialized reachable graph를 별도로 읽어 확인한다.

같은 row set의 incremental tree와 bootstrap tree가 다른 유효 shape/root를 가질 수 있다.
실제 256→257→256 witness를 테스트했다. 이것은 logical equality와 representation
identity의 차이다. 동일 epoch/revision root mismatch를 완화하지 않았고, D2b가 같은
R의 representation-only 재구축을 광고하는 것도 허용하지 않는다.

## 7. Complete facts catalog·global 제약

모든 fact key/value는 §11의 C1 배열/값이며 locator를 넣지 않는다.

| family | source/identity·NULL 규칙 | 변경 시 D2b 영향 |
| --- | --- | --- |
| pk | 11개 table 모든 PK → 전체 row_hash | 해당 old/new PK·incoming ref |
| unique ledger_payment_key | non-null ledger key, 빈 문자열 포함 → Owner | key ref/reverse/allocation/batch |
| unique recurring_child | expense source Key/month/stamp → child Owner | old/new epoch와 source·closed context |
| unique batch_pair/key/entry | item의 batch+key, key, entry 각각 → Owner | batch owner·referenced allocations |
| unique allocation_pair | event+payment key → allocation Owner | event aggregate와 batch closure |
| unique cash_owner | non-null event cash 또는 fixed-linked cash → Owner | event/fixed owner 양쪽·flow |
| unique event_idempotency | non-null key → event Owner; 전 table, BINARY | old/new N4 identity |
| ref/reverse | 실제 FK 7개와 allocation logical payment-key ref; NULL은 없음 | 양방향 edge와 삭제 target의 closure |
| allocation | event/payment key/allocation Key → exact amount decimal string | event sum/count |
| aggregate event | 모든 event, 0건도 count/sum `"0"` | incoming allocations |
| aggregate active_batch | 빈 table도 `"0"` | status 전이 |
| context last_closed_month | raw setting 또는 absence면 null | context_reverse 전체 |
| context_reverse | planned source, source/epoch 표시 ledger, 모든 fixed panel → row_hash | 해당 raw 관계 전체 재검증 |

실제 DB UNIQUE는 모든 PK, batch_items(batch_id,entry_payment_key), N4 partial index다.
추가 ledger-key/epoch/batch-owner/allocation/cash ownership은 승인된 raw predicates이지
새 DB FK/UNIQUE가 생겼다는 뜻이 아니다. Deferral/registration target FK는 만들지 않았다.

실제 FK는 ledger source→ledger, panel cash→cash, event batch/cash, item batch/entry,
allocation event다. Allocation payment-key는 `@ledger_payment_key` logical namespace다.
Ref마다 정확한 inverse와 source row hash를 생성한다.
Full validator는 source-kind/epoch/active ownership, nonnegative allocation, event sum,
immediate negative cash, fixed date/period/flag/sign/disjointness, active batch≤1,
필수 settings를 검사한다. 금융 파생값 계산은 없다.

`Index.validate`만으로 F(raw)의 완전성이 성립하지 않는다. `validate_index`는 전체
raw state로 F를 다시 생성해 canonical root와 비교하며 missing reverse/rogue fact도
거부한다. 이것은 명시적 O(full state) reference 검사이며 normal incremental API가 아니다.

## 8. N4·Patricia

실제 migrated SQLite의 `UNIQUE(idempotency_key) WHERE idempotency_key IS NOT NULL`
oracle와 12개 paired control을 비교했다. NULL 중복 허용, empty/동일/NUL 포함 동일 key
중복 거부, 대소문자·공백·NUL suffix·조합형/완성형·supplementary 차이를 보존했다.
이벤트 종류나 ID로 uniqueness scope를 나누지 않는다.

Patricia는 fact-key SHA-256 MSB-first, maximal common literal bit prefix,
left0/right1, unary 금지, exact C1-key sorted collision bucket이다.
Empty/leaf/node/root는 명세 field를 그대로 사용한다.
Build, lookup, persistent insert/replace/delete, canonical traversal, 전체 invariant 검사가 있다.
별도의 bit-at-a-time radix reference가 root bytes/hash를 재구축한다.
Input 순서 3개씩, random mutation, 255-bit 공통 prefix/one-bit divergence,
강제 fact-key digest collision, 마지막 fact 삭제를 검사했다.
강제 collision은 테스트 monkeypatch뿐이며 실제 hash algorithm을 바꾸지 않는다.

## 9. 독립 oracle·SQLite·randomized 증거

[독립 reference](../backend/tests/isolated_sync_reference.py)는 json.dumps 기반 유효
C1 serializer, 직접 hashlib framing, serialized graph traversal, bit-at-a-time Patricia,
별도 complete facts extractor를 쓴다. Fact key/value 전체를 대조하므로 extractor와
같은 함수가 만든 root끼리만 비교하는 순환 oracle이 아니다.
기존 SQLite FK/UNIQUE와 backend Snapshot ownership 검사도 독립 oracle로 사용한다.
`rebuild`는 complete bootstrap을 제공하지만 같은 함수의 hash 일치만으로 증명하지 않았다.

고정 seeds: tree 66201..66203(각 600 operations), Patricia 66211..66213(각 500),
SQLite labels 66221..66222(각 80), multi-table histories 66231..66232(각 70)다.
매 step에서 SQL/독립 dict의 logical row set, encoded tree, invariant, complete facts,
Patricia reference root를 대조한다. Multi-table case는 ledger/cash/event/allocation
insert/update/delete와 cascade를 함께 다룬다. 테스트의 full-state diff는 D2b 구현이 아니다.

실제 migrated SQLite current-like 376/1k/5k/10k/confirmed-heavy 1200 fixture는
기존 T6.6A generator의 고정 seed/date/offset을 재사용했다. 모든 table을 읽고
Snapshot exporter 결과와 PK-sorted logical rows를 비교했으며 DB dump/revision이
전후 동일함도 확인했다. Historical REAL-affinity schema의 실제 migration도 별도 검사했다.
Cross-leaf source/child, 삭제 cascade, SET NULL의 valid/invalid final state,
global duplicate/참조 누락/합계·출금·fixed ownership·필수 설정 등의 공격을 검사했다.

## 10. Snapshot v7와 D1 경계

v7 exporter/hash/restore 및 D1 capture/fence 코드는 변경하지 않았다.
Segment PK order는 v7 export order와 다르다. 이후 adapter는 다음 기존 순서를 재현해야 한다.
Ledger: book_section/kind/date/sort/id; panels: month/type/sort/id; cash: date/sort/id;
items: batch/id; events: event_date/id; allocations: event/id; deferrals: target month/key;
registrations/settings/labels: key. Batch는 id다. Sensitive settings 제외도 유지해야 한다.

이번 증거는 complete logical raw rows 보존·기존 exporter 무변경 회귀다.
Segment hashes로 기존 flat table/data/content/fingerprint SHA를 합성할 수 있다는 주장이 아니다.
Exact v7 materialization bytes/metadata/hash/restore adapter는 후속 통합 proof다.

## 11. D2b interface·복잡도·남은 의존성

D2b는 admitted Row → old `row_facts` 제거 → 새 row/tree path와 facts 추가 →
affected reverse/epoch/cash/event/context closure 확인 → index paths/raw-root/view metadata
구축에 이 API를 사용할 수 있다. `Tree.move`는 explicit PK 이동을 지원한다.
Lookup/put/delete는 complete tree/index를 재구축하지 않는다. Immutable 객체의
기존/새 hash 차이로 changed object를 골라 저장할 수 있다.

단 D2a는 DB-backed object resolver/store를 구현하지 않았으며 이미 구성된 immutable
node graph를 입력으로 받는다. D2b는 이 graph의 lazy object loading/receipt와 transactional
object persistence를 설계·검증해야 한다. `validate_state`, `build_facts`, `rebuild`,
`validate_index`를 매 transaction 호출하는 통합은 scaling 계약 위반이다.

| operation | 알고리즘 비용·가정 |
| --- | --- |
| C1 | 총 scalar/byte 길이 + object key sort; raw row schema width는 고정 |
| tree bootstrap | PK sort O(N log N) + O(encoded bytes), object construction |
| tree mutation | O(log P) bounded-fanout path + affected leaf bytes/row; oversized row 길이는 별도 |
| row facts | 해당 row 폭과 일정 catalog 수; aggregate/reverse closure는 별도 D2b 의무 |
| Patricia build | F digest sort O(F log F) + 최대 256-bit radix construction/bytes |
| Patricia update | 최대 256 path + collision bucket/changed value bytes; O(N) rebuild 없음 |
| complete validation/rebuild | 전체 row/facts/objects를 처리; bootstrap/test/recovery 전용 |

따라서 D2a가 backend O(N)을 제거했다고 주장하지 않는다.
D1의 begin/finalize schema check overhead도 그대로다. D2b는 audited schema identity를
connection/transaction의 DDL·schema generation과 결합해 재사용할 수 있는지 별도로
입증해야 하며 단순히 check를 삭제해서는 안 된다.

## 12. HOST 알고리즘 성능

측정 원문·CPU/wall min/max/stdev·모든 samples는 [performance.json](benchmarks/t66d2a/performance.json)에 보존했다.
HOST: Intel Core i7-8750H(6 cores/12 threads), RAM 약 23,885 MiB,
Linux 6.8.0-146, Python 3.12.3, SQLite 3.45.1이다.
별도 correctness 테스트와 일부 병행한 측정이며 완전히 idle인 host 결과는 아니다.
동일 process의 CPU time도 보존했다. 10k facts에서 wall/CPU median은
9006.30/9004.58ms였다.
Thermal/frequency 및 다른 process 영향을 제거한 절대 latency 보장은 하지 않는다.

각 cell은 wall **median / p95 ms**다.

| 단계 | 376 | 1k | 5k | 10k | confirmed-heavy 1200 |
| --- | --- | --- | --- | --- | --- |
| c1_encode | 20.90 / 21.18 | 58.56 / 58.97 | 285.96 / 286.64 | 643.93 / 653.75 | 84.21 / 85.03 |
| row_admission | 102.11 / 102.63 | 286.63 / 288.03 | 1422.11 / 1440.51 | 3127.70 / 3204.62 | 414.00 / 417.31 |
| row_hash | 39.10 / 40.67 | 104.73 / 105.10 | 502.82 / 503.78 | 1258.27 / 1312.43 | 146.83 / 148.29 |
| tree_build | 81.22 / 82.01 | 210.06 / 212.41 | 986.92 / 988.84 | 2243.26 / 2332.35 | 287.28 / 290.72 |
| facts_catalog | 289.33 / 291.16 | 776.25 / 798.67 | 3712.02 / 3729.87 | 9006.30 / 9098.44 | 1346.20 / 1399.54 |
| patricia_build | 204.12 / 226.84 | 466.38 / 488.58 | 2125.98 / 2141.56 | 4974.39 / 5062.38 | 2342.05 / 2356.73 |
| structural_validate | 107.55 / 114.21 | 288.11 / 290.50 | 1423.41 / 1437.32 | 3146.12 / 3289.94 | 419.49 / 422.51 |

| fixture | archive / source-linked child | facts | objects | object bytes | 추가 Python peak bytes | process RSS high-water KiB |
| --- | --- | --- | --- | --- | --- | --- |
| 376 | 271 / 1 | 464 | 942 | 702083 | 3762392 | 69012 |
| 1000 | 895 / 1 | 1088 | 2192 | 1699094 | 4683737 | 79560 |
| 5000 | 4895 / 1 | 5088 | 10208 | 8119800 | 21110936 | 145020 |
| 10000 | 9895 / 1 | 10088 | 20230 | 16153738 | 40877994 | 238616 |
| confirmed-heavy | 0 / 600 | 4825 | 9667 | 5716001 | 15081270 | 238616 |

메모리 peak는 raw fixture·기존 graph를 이미 가진 상태에서 새 full rebuild에 추가로
추적된 allocation이며 전체 장부 resident size가 아니다. RSS는 process 누적 high-water라
confirmed-heavy의 단독 peak를 뜻하지 않는다. Memory probe의 tracing overhead가 큰 시간은
일반 rebuild latency로 사용하지 않았다.
10k object bytes 16,153,738은 raw leaf/node·global facts tree·raw/index roots의 합이고
HTTP full bundle 5,684,312 bytes와 다른 물리 표현이다. 특히 fact마다 별도 leaf 및 내부
객체가 생겨 object/index overhead가 크다. 이것은 protocol correctness를 바꾸거나
D2a에서 format 최적화를 할 이유가 아니라 D2b/D3 object-store batching·bounded update
비용의 후속 실측 의무다. 새 full rebuild를 normal transaction에 붙여서는 안 된다.

모든 결과는 synthetic HOST이며 금융 transaction·HTTP·단말 latency가 아니다.
Warmup 3회, 작은 fixture 20 samples, 비용이 큰 5k/10k는 5 samples를 사용한다.
5개 sample p95는 상위 관측값 부근의 기술 통계일 뿐 안정적인 tail 추정이 아니다.
각 단계는 독립 inclusive 측정이며 합산해 end-to-end라고 부르지 않는다.
메모리는 별도 full rebuild 1회의 tracemalloc peak와 process RSS high-watermark다.

추가 [updates.json](benchmarks/t66d2a/updates.json)은 동일 admitted base에서 title 한 필드만
변경한 tree path 및 old/new row facts 경로를 각각 warmup 3 + sample 20회 측정했다.
Full target F(raw) 재구축 root와도 일치했다. D1 capture/fence/commit 비용은 포함하지 않는다.

| fixture | tree update median / p95 ms | facts paths median / p95 ms | 변경 objects / bytes |
| --- | --- | --- | --- |
| 376 | 47.31 / 47.97 | 3.80 / 4.18 | 12 / 155056 |
| 1000 | 47.64 / 47.92 | 3.73 / 4.12 | 12 / 155389 |
| 5000 | 47.23 / 47.61 | 4.94 / 5.29 | 15 / 159551 |
| 10000 | 48.01 / 48.25 | 6.43 / 6.65 | 19 / 161795 |
| confirmed-heavy | 50.23 / 50.76 | 11.04 / 11.21 | 28 / 172927 |

Changed-object 수/bytes를 구한 전체 enumeration은 측정 구간 밖의 **진단 oracle**다.
D2b는 capture가 가리키는 affected paths와 immutable 공유 subtree를 이용해 변경 객체를
수집해야 하며 이 진단 enumeration을 정상 writer에 복사하면 안 된다. Indexed subtree
의 hash/height/range와 Patricia prefix를 비교하여 unchanged subtree에서 즉시 멈출 수 있다.
위 bytes는 tree/index 객체만이며 hot/control/raw-root/view, HTTP, 저장 transaction,
reverse closure가 큰 mutation 또는 256KiB oversized row의 비용을 대표하지 않는다.
따라서 이 결과는 bounded path API의 증거이지 D2b steady-state 최종 인증이 아니다.

## 13. 실제 검증 명령·결과

아래는 이번 실제 실행 결과다. 과거 D1 감사 수치를 새 실행으로 재사용하지 않았다.

| 검사 | 이번 결과 |
| --- | --- |
| 전체 backend `pytest -q --durations=8` | **850 passed + 1540 subtests passed**, 641.75s |
| 새 D2a corpus(전체 실행에 포함) | canonical 34, trees 21, facts 50, Patricia 11, roots 10, 실제 SQLite scale differential 5 = **131 passed** |
| 별도 강화된 independent catalog + differential | **55 passed**, 120.07s |
| 실제 D1 capture/fence, Snapshot v7, migrations, financial projections | 전체 backend에 포함, 모두 PASS; 원본 source 불변 |
| 격리 safety + 기존 payload/fixture consistency | **42 passed**, 2.56s |
| Backend/scripts Ruff 0.15.22 | PASS |
| Dart 3.13.3 formatter parity / analyze | 유효 19 + invalid 3 controls PASS / no issues |
| Frontend `npm run build` | PASS, 1.53s |
| `bash -n` 3개 scripts | PASS |
| 문서 links·aggregate sample/warmup consistency·`git diff --check` | PASS |
| ShellCheck | 미설치, NOT RUN |
| Full Flutter/Android/frontend tests·lint | 해당 source 불변으로 이번 범위에서는 NOT RUN; frontend build와 격리 Dart 검증은 실행 |

Backend와 safety에서 기존 Starlette/httpx deprecation warning 각 1건이 있었다.
의존성을 바꾸어 없애지 않았다. 초기 test-first module absence, test helper key 처리,
Dart 진단 도구 문법 실패는 수정 후 재실행했다. 최종 unresolved 실패는 없다.
Full run 도중 추가한 independent reference assertion은 별도 55-test 실행으로도
확인했다. Timed 알고리즘 함수와 제품 runtime은 그 oracle 보강으로 바뀌지 않았다.

```bash
(cd backend && PATH=/home/hjkerman/.flutter/bin:$PATH ../.venv/bin/python -m pytest -q tests/test_isolated_sync_canonical.py)
(cd backend && PATH=/home/hjkerman/.flutter/bin:$PATH ../.venv/bin/python -m pytest -q --durations=8)
(cd backend && ../.venv/bin/python -m pytest -q tests/test_isolated_sync_facts.py tests/test_isolated_sync_differential.py)
.venv/bin/python scripts/benchmarks/t66d2a.py --output /tmp/money-note-d2a-performance.json
.venv/bin/python scripts/benchmarks/t66d2a.py --output /tmp/money-note-d2a-updates.json --updates-only
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks/test_payload_bytes.py scripts/benchmarks/test_t66a_fixture.py
.venv/bin/python -m ruff check backend scripts
dart analyze scripts/benchmarks/t66d2a_c1.dart
(cd frontend && npm run build)
bash -n scripts/dev-server.sh scripts/deploy-server.sh scripts/release-mobile.sh
git diff --check
```

실행 재현은 checkout root와 개발 venv를 사용한다. Backend pytest는 backend cwd에서 실행한다.
도구는 기존 DB 입력을 받지 않고 own TemporaryDirectory의 실제 migrated synthetic DB만 사용한다.
기본 targets는 376/1000/5000/10000/confirmed-heavy이며 2GiB address-space/1800 CPU-second
ceiling이 있다. `--verify-only`는 차등 검사, `--updates-only`는 단일 row 경로 실측,
`--samples`는 bounded 1..100이다.
Tracked aggregate는 raw row/credential을 포함하지 않으며 큰 raw samples/DB는 Git에 없다.

## 14. 한계·감사·안전성

집중 source/runtime 자체 점검에서 잔여 in-scope Critical/High/Medium은 0건이다.
독립 구현 감사는 별도다. Release descriptor artifact/compatibility allow-list 발급,
full v7 adapter, D2b transaction atomicity/capture closure, D3 observation/leases,
mobile segmented store와 Android power-loss durability는 이번에 입증하지 않았다.
50k/100k 및 실기기 측정은 수행하지 않는다. D2a는 bounded 알고리즘 기반을 검증하는 단계다.

정상 `backend/app`, migration, Dockerfile, D1 capture, mobile/frontend source는 수정하지 않았다.
생산 DB/API/credential/service에 접근하지 않았으며 deployment/dry-run/APK 설치도 없다.
Commit/push는 후속 D2b 구현·runtime 활성화·배포 승인이 아니다.
다음 단계는 실제 D2a 구현에 대한 별도 독립 감사다.

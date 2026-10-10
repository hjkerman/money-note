# T6.6D2b — 격리 transactional incremental finalization

## 최신 상태와 증거 구분

이 문서는 **이전 미완료 시도와 targeted continuation을 함께 보존**한다.
아래 A~AG는 이전 시도의 원 기록이며, 923개 회귀·28개 raw-row benchmark cell과
Medium D2B-G01을 소급해서 새 결과로 바꾸지 않는다. 최신 변경·검증은 AH를 따른다.
Continuation 시작에서도 HEAD/main/origin/main/실제 remote main은
`158fbaab6867e0edda6b37647e129b743dd077b8`였으며, 기존 미커밋 D2b 파일을 그대로 보존했다.
최신 구현 판정은 **T6.6D2b COMPLETE — READY FOR INDEPENDENT IMPLEMENTATION AUDIT**다.
D2B-G01과 추가 fence FK scan을 해결했다. 최종 953 tests + 1,540 subtests,
40-cell/800표본 재측정이 통과했다. 상세 수치·조건은 AH~AK를 따른다.
이는 자체 구현 검증이며 독립 D2b 감사·D3 착수·배포 승인이 아니다.

## A. 판정·시작 Git 상태

**T6.6D2b INCOMPLETE — TARGETED FIX REQUIRED**

격리 raw/index finalizer는 구현했지만, 실제 borrowed payment·원장 삭제 writer에
전체 historical ledger ownership 조회가 남는다. 따라서 D2b의 전체 정상 mutation
scaling gate를 통과했다고 판정하지 않는다. 이 의존성을 D3로 조용히 이관하거나
기존 validator를 생략하지 않았다. 프로토콜 모순이나 금융 계산 변경이 필요한
architectural blocker를 발견했다는 뜻도 아니다.

시작 시 `main`, HEAD = local main = origin/main = 실제 remote main =
`158fbaab6867e0edda6b37647e129b743dd077b8`, clean working tree였다.
부모는 `5277f7931bc3a4386832a3136d04bf373cd66709`다. 사용자 제공 D2a 독립 감사
PASS와 이번 구현·내부 검증은 별도 증거다. 독립 D2b 감사는 수행하지 않았다.
완료 조건 미충족으로 이번 변경은 commit/push하지 않는다.

## B. 변경 파일·격리 범위

| 파일 | 상태·책임 |
| --- | --- |
| [capture.py](../backend/isolated_sync/capture.py) | 기존 admission 호출 두 곳을 기본 동작이 동일한 `_validate_capture_schema()` hook으로 분리 |
| [store.py](../backend/isolated_sync/store.py) | IMPLEMENTED: SQLite immutable objects, bounded LRU, lazy D2a adapters |
| [maintenance.py](../backend/isolated_sync/maintenance.py) | IMPLEMENTED: capture coalescing, reverse closure, exact maintained inputs |
| [finalization.py](../backend/isolated_sync/finalization.py) | IMPLEMENTED: isolated schema, bootstrap, pre-commit finalizer, 두 번째 fence |
| [test_isolated_sync_finalization.py](../backend/tests/test_isolated_sync_finalization.py) | 실제 file-backed SQLite·독립 full-state oracle·실패/재시작/금융 동등성 |
| [t66d2b.py](../scripts/benchmarks/t66d2b.py) | 자체 synthetic DB만 생성하는 opt-in benchmark |
| [test_t66d2b.py](../scripts/benchmarks/test_t66d2b.py) | compact summary 값 보존·임시 출력 범위·덮어쓰기 방지 |
| 이 문서와 compact benchmark 요약 | 구현 증거·한계·재현 |

`backend/app`, 정상 migration 목록, D2a 알고리즘, API, mobile, frontend 제품 코드는
변경하지 않았다. D1의 기본 schema 검증·capture-only 의미는 유지한다.
**NOT ACTIVATED:** normal startup import, 정상 writer 연결, 새 protocol/endpoint,
운영 schema 변경, 압축 활성화. Profile을 외부 DB 경로에 설치하는 API도 없다.

## C. Persistent immutable object store

`Store.put/get`은 승인된 C1 `Object`와 domain hash를 저장·조회한다.
`sync_objects(hash,kind,body)`에서 동일 content를 재사용하고 동일 hash의 다른
kind/bytes는 거부한다. 새 typed child Ref의 존재·byte length를 확인한 뒤 parent와
`sync_object_edges`를 저장한다. Hash처럼 보이는 임의 문자열을 edge로 해석하지 않는다.

`row`는 명세 §11의 별도 preimage이므로 `kind`를 발명하지 않고 `sync_rows`에
exact C1 bytes를 보관한다. Leaf에는 명세대로 row 값이 포함되어 있다.
Patricia의 PK fact에 있는 row hash는 임의의 object-transfer 권한이 아니다.
Table descriptor는 기존 raw-root의 inline descriptor이며 별도 hash domain을 만들지 않았다.

Store는 이미 열린 SQLite transaction을 요구한다. D1 metadata authorizer 아래에서만
쓰기 가능하고, 저장·collision 검사는 원 금융 transaction과 동일하다.
이는 악성 privileged Python 코드나 직접 DB 파일 변조를 방어하는 sandbox가 아니다.

## D. Lazy resolver

`LazyObject`, `LazyTree`, `LazyIndex`는 Ref/descriptor만으로 sibling을 재사용한다.
읽은 object는 exact hash/bytes/kind/namespace/canon/schema를 확인한다.
Tree의 로드된 path는 D2a leaf/node 재구성과 descriptor를 비교한다.
Index root는 structural version·count를 확인한다. Bounded LRU 기본값은 256 objects다.

`persist_tree/persist_index`는 새 native nodes만 방문하고 lazy unchanged subtree를
enumerate하지 않는다. 정상 finalizer는 `.objects()`, `Tree.rows()`, `Index.facts()`,
`Index.build()`를 호출하지 않는다. 이를 mock으로 금지한 테스트가 있다.
전체 accepted graph의 validation을 매번 수행하는 대신, complete bootstrap과
지원 writer의 atomic update라는 귀납을 사용한다. Full graph 검사는 테스트 oracle다.
외부 손상 DB를 무검증으로 최초 accepted base로 채택하는 인터페이스는 제공하지 않는다.

## E. D1 capture 연결

`FinalizationConnection.begin_capture()`는 D1의 `BEGIN IMMEDIATE`, UUID context,
strict admission, revision fence를 그대로 사용한다. `sync_current.revision`과 실제
legacy revision이 다르면 거부한다. 이 writer lock 아래에서는 base epoch/root가
다른 transaction에 의해 교체될 수 없다. 선택적인 expected epoch/revision도 검증한다.

`finalize()`는 실제 `capture.read_changes`를 소비하고, audited D1 finalization으로
정확한 revision interval/column coverage를 확인한 뒤 source-write context를 닫는다.
이후 tree/index 작업 중 실패하면 D1 certificate를 포함한 전체 transaction을 rollback한다.
별도 독립 capture trigger를 만들지 않았다.

## F. First-old/final-new coalescing

`coalesce()`는 revision 순으로 사건을 재생한다. 처음 만난 PK의 accepted row를 lazy
tree에서 읽고 OLD가 현재 membership과 정확히 같은지 비교한 뒤 제거한다. NEW는
그 시점에 비어 있는 membership에만 삽입한다. 최종 row는 실제 SQL의 PK 조회와
storage-class-preserving C1 bytes로 비교한다.

출력은 최초 OLD와 최종 NEW의 membership 차이다. DELETE/재INSERT를 동일 entity라고
추측하지 않는다. INSERT→UPDATE, 반복 UPDATE, INSERT→DELETE, DELETE→INSERT,
PK A→B, key 재사용, savepoint rollback을 처리한다. 논리적으로 동일한 최종 값은
tree를 다시 만들지 않지만 D1 사건과 revision 증가를 버리지 않는다.

## G. OLD/NEW membership

모든 OLD membership을 먼저 제거하고 모든 NEW membership을 넣는다.
Patricia에서도 OLD facts를 전부 제거한 뒤 NEW facts를 넣어 최종적으로 유효한
UNIQUE 교환을 중간 상태 때문에 거부하지 않는다. OLD fact가 accepted index와
다르면 fail closed다. PK 이동은 old key 제거와 new key 삽입으로 표현한다.

## H. 민감 marker

`share_pin_hash`, `share_pin_is_default`의 D1 excluded side에는 row 값을 만들지 않는다.
Visibility/key/op를 검증하고 revision coverage는 유지한다. 이런 값만 바뀌면 raw/index
root는 같고 revision/certificate는 전진할 수 있다. Capture cells·object·row bytes에
synthetic sentinel이 들어가지 않는지 검사한다. 기존 포함↔제외 key 이동 계약도
허용된 side만 coalescing한다. 민감 값을 hash로 전달하는 새 규칙은 만들지 않았다.

## I. B+tree incremental updates

기존 D2a `Tree.delete/put`을 변경 PK 순으로 적용한다. Lazy root에서 영향 leaf와
parent path만 읽고 변경한다. Immutable unchanged subtrees는 Ref 그대로 남는다.
256행/256KiB leaf·fanout 32 규칙은 D2a 그대로다. 실제 persisted split 이후 새 연결에서
삭제·merge/root collapse를 검사한다. 선택적 v1 representation-only compaction은 없다.
Mutation history가 다른 fresh rebuild와 B+tree hash equality를 요구하지 않는다.

## J. Patricia incremental updates

`row_facts`의 OLD/NEW와 event count/sum·active batch count·last_closed_month facts를
변경한다. `_derived`는 allocation delta를 넓은 Python 정수로 계산한다. 새 path만
persist하고 기존 immutable branch를 재사용한다. Complete final facts의 root는 독립
radix reference 및 실제 SQLite 전체 재추출/full-build Patricia와 정확히 비교한다.

## K. Reverse-reference closure

`sync_reverse(dst_table,dst_key,src_table,src_key,field)`의 destination PK와 source index로
incoming/outgoing closure를 찾는다. Canonical ref/reverse facts와 별도로 batch item의
payment-key lookup edge를 유지하여 key 변경 시 영향을 놓치지 않는다.
OLD와 NEW의 outgoing 대상 모두를 seed로 넣고 삭제 후 끊어진 관계도 검사한다.

마지막 마감 월 변경은 `sync_context_reverse` 전체를 영향 집합으로 처리한다.
이는 실제 영향을 받는 R이며 최악 O(N)일 수 있다. 모든 fan-in이 상수라는 주장은 없다.
추출한 closure에 기존 D2a Category B raw predicates를 적용한다.
전체 역사 facts를 순회하여 incoming reference를 찾지 않는다.

## L. Global UNIQUE/FK/N4

PK·composite UNIQUE·logical payment key·cash owner·recurring epoch는 기존 D2a facts다.
Native FK와 isolated schema 제약도 유지한다. N4는 non-null 전체 key의 BINARY UNIQUE,
여러 NULL 허용, 빈 문자열 충돌 거부이며 trim/case-fold/Unicode normalization을 하지 않는다.
관련 기존 D1/D2a SQLite parity tests와 새 final-state swap/삭제/aggregate 실패 검사를 실행한다.
Native FK의 child lookup에도 index가 필요하다. 실제 원본 ledger DELETE plan은
`card_payment_batch_items`를 scan했고 새 `sync_fk_item_entry`로 bounded lookup한다.
원본 `idx_ledger_source_planned` partial index는 이미 source FK 조회에 사용된다.
현재 격리 draft의 추가 source index와 allocation-event index에는 기존 index와 중복되는
부분이 있어 write amplification을 줄일 후속 정리 후보로 기록한다. 이 중복을 새로운
필수 integrity 보장으로 주장하지 않는다. 정상 product schema/index는 변경하지 않았다.

## M. Maintained aggregates와 미완료 연결

| 구현 | 비용·정확성 | 사용 범위 |
| --- | --- | --- |
| `sync_cash_prefix`, `cash_prefix` | 날짜 ordinal의 고정 domain Fenwick; 최대 약 22 PK 단계; Python exact intermediate·TEXT 저장 | Backend raw 누계 입력; 실제 기존 `cash_flow_total` 및 독립 sum과 비교 |
| `sync_totals/closed_count`, `closed_counts` | archive expense 월별 count; indexed 최근 월 조회 | 기존 폐쇄 월 통계의 입력 후보 |
| `sync_totals/policy_horizon`, `policy_horizon` | ledger date/panel month/batch usage_month의 월별 count·최대값 | policy covered-through 입력 후보 |
| event sum/count·active batch | 기존 canonical aggregate facts; OLD/NEW delta | 구조·복구 관계 검사, financial remaining 계산 아님 |
| reverse/FK lookup indexes | 실제 영향 관계·source 조회 | closure와 SQLite FK action |

모두 raw mutation과 rollback/commit을 같이 한다. Randomized oracle에서 count/horizon,
cash prefix, context reverse를 전체 SQL state와 비교한다. Summary/할인/payment remaining
공식은 복제하지 않았다. 이 입력들을 **기존 모든 presenter/writer에 연결하지는 않았다.**
Cash prefix 등을 구현했다는 사실을 기존 financial engine의 모든 O(N) 제거로 표현하지 않는다.

## N. Raw/index roots

기존 D2a `raw_root`와 `Index.object()`를 사용한다. 고정 11개 table descriptor 중
변경된 tree의 Ref만 바뀐다. Namespace·RAW_SCHEMA·canon/structural과 exact roots를
`sync_current` 및 `sync_commits`의 base/target epoch/revision에 결합한다.
RAW_SCHEMA는 exact raw contract와 capture schema digest의 isolated release descriptor다.
운영 release compatibility ID로 광고하지 않는다.

이는 RAW ROOT와 GLOBAL FACTS ROOT다. Hot/control/evaluation을 포함하는 최종 Target
view producer나 legacy Snapshot v7 fingerprint가 아니다. D3의 coherent producer가
financial evaluation context와 별도로 결합해야 한다. 정상 commit에 flat v7 SHA 계산은 없다.

## O. Pre-commit finalizer

구현 순서는 다음과 같다.

```text
지원 context/base 검증 → D1 complete capture 검증·source context 닫기
→ coalescing·실제 최종 SQL row 확인 → tree/facts 변경
→ reverse closure 검증 → maintained inputs 변경
→ immutable row/tree/index/root 저장 → complete certificate/current 준비
→ SQLite COMMIT
```

`finalize()` 성공은 아직 COMMIT receipt가 아니다. 호출자가 commit해야 한다.
실패 시 전체 rollback한다. 성공한 GET/observation을 mutation receipt로 바꾸는 API는 없다.
Pending/outcomeUnknown·모바일 B/J의 코드나 형식도 변경하지 않았다.

## P. D1 fence 통합

D1 `sync_capture_commits.status=capture_only`를 그대로 둔다. 추가
`sync_authority_fence`는 같은 tx_id의 D1 capture certificate와 D2b complete
`sync_commits`를 모두 deferred FK로 요구한다. 명시적으로 D1 base-class finalizer만
호출해도 D2b commit은 실패한다. D2b의 public `finalize_capture()`는 거부한다.
Root/object가 없는 capture-only completion을 authority로 승격하지 않았다.
Finalize 후 raw write는 기존 context 부재 trigger가 거부한다.

## Q. Bootstrap

`FinalizationSandbox`는 자신이 생성한 temporary synthetic DB만 받는다.
기존 initializer로 checkpoint 4까지 생성 → D1 설치 → 격리 checkpoint `1000002`
설치 → explicit bootstrap 순서다. D1 migration과 D2b migration은 구별하며 D2b 설치
실패는 완전한 D1 profile로 rollback한다. Bootstrap 전 source-write authority는 없다.

Bootstrap은 EXCLUSIVE coherent state에서 전체 raw admission/F/catalog/trees/index를
구성하고 검증·저장하므로 O(N)이다. 매 explicit cold bootstrap/restart에 epoch를
회전한다. 단순 connection reopen은 서버 cold restart가 아니다. 기존 immutable
objects는 삭제하지 않는다. Finance rows/revision/Snapshot은 bootstrap이 바꾸지 않는다.

## R. Financial parity

실제 기존 borrowed functions를 legacy/isolated의 동일 synthetic seed에서 실행했다:
card create, cash create, recurring confirm, fixed confirm, payment event, transit policy,
archive edit, historical delete의 8종이다. Timestamp·recurring payment key·Snapshot clock을
명시 고정하고 실제 저장된 Snapshot 전체와 기존 Summary/payment status를 비교한다.
새 financial formula를 oracle로 쓰지 않는다.

**중요:** payment/delete parity 성공은 scaling 성공이 아니다. 같은 tests가 이 두 writer의
`SELECT * FROM ledger_entries`를 확인하여 남은 의존성을 기록한다. 일반 HTTP router의
필수 response 준비·인증까지 새 profile로 연결한 end-to-end protocol 시험도 아니다.

## S. Snapshot v7

Exporter/restore/hash/manifest 코드는 불변이다. No-op 및 동일 금융 작업의 v7
동등성을 실제 exporter로 확인한다. Segmented representation을 flat SHA로 오해하지 않는다.
Restore/Mobile Wins의 fence-aware validator·epoch adapter와 large upload는 미구현이다.
Full B/J/legacy baseline materialization이나 backup 30개 정책을 대체하지 않는다.

## T. Rollback·restart

Capture/coalescing/tree/facts/closure/aggregate/object/root 각 단계에서 실패를 주입하여
fresh connection의 전체 dump와 원 generation을 비교한다. Schema/epoch/base 오류,
capture marker/cell/OLD/NEW 손상, missing/corrupt object, logical reference/UNIQUE 실패도
reject한다. 실제 `max_page_count`의 SQLITE_FULL과 COMMIT busy 후 rollback/retry를 검사한다.

`fork`와 `os._exit`를 사용하는 bounded process 중단 5개는 raw write 뒤, object 뒤,
root 뒤, finalize 뒤 commit 전, commit 후다. 재개 시 old 전체 또는 new 전체만 허용한다.
이는 process-crash 증거이지 arbitrary instruction-level crash나 하드웨어 전원 손실
증명이 아니다. During-COMMIT의 모든 instruction을 exhaustively 시험하지 않았다.

## U. Concurrency

두 writer의 IMMEDIATE contention·retry, writer와 read transaction/Snapshot export,
stale expected base와 epoch mismatch를 검사한다. Reader는 commit 전 old complete
state를 보고 commit 뒤 새 state를 본다. Reader lock 때문에 commit이 실패하면 완료로
간주하지 않고 reader 종료 후 같은 준비된 transaction의 재commit 또는 rollback을 한다.
D3 lease/download 중 network concurrency를 시험했다는 주장은 없다.

## V. Migration·schema admission

기존 `_validate_current_schema`와 33개 D1 replacement trigger SQL exact admission을
유지하고 D2b metadata/index SQL 전체·version/profile·raw columns를 추가 검증한다.
Unknown trigger/altered column/version을 거부한다. 새 normal migration이나 startup
import를 등록하지 않았다. 기존 backend가 이 experimental checkpoint를 일반 DB로
사용하게 만드는 compatibility 우회는 없다.

## W. Writer coverage

| 경로 | 이번 범위·후속 의무 |
| --- | --- |
| entries create/update/delete/reorder/planned | D1 raw capture 대상; 실제 create/confirm/delete parity. Payment/recurring 전체 validator의 bounded adapter 미완료 |
| cash_flows create/delete, panels create/update/delete/confirm | capture/FK 대상; 실제 cash/fixed parity 및 SET NULL. Own-session/HTTP 연결 미활성 |
| card_payments event/allocations/batches/items/deferrals | 11-table capture와 closure 대상; 실제 event parity. 기존 whole-history ownership/presenter 비용 미해결 |
| settings/labels/card_charge profiles | capture·marker·randomized/실제 policy parity. Normal operations router 연결 미활성 |
| notification registrations | D2a row/facts와 D1 capture 대상. 전체 notification service adapter 별도 검증 필요 |
| month close | archive copy/delete·source/fixed/income/batch raw 사건은 foundation 범위. 실제 top-level month-close adapter·mandatory backup 연결은 미활성 |
| reconciliation `apply_mobile_wins` | 기존 B/J/receipt transaction 불변. Fence-aware 전체 validator 및 epoch/bootstrap adapter 필요; R1/rollout 의존성 |
| Snapshot restore/reset/bulk completion | 일반 capture-only로 우회 금지. Mandatory backup·full replacement/epoch adapter·large restore는 R1/후속 prerequisite |
| migration/startup/CLI/direct maintenance | 자체 sandbox bootstrap만 지원. 실제 운영 writer 전환·audit은 별도; context 없는 profile SQL write는 거부 |
| users/auth/audit/reconciliation receipts | authoritative 11 tables 밖; 정상 코드 불변. Future control/authorization 검토 필요 |

이 목록은 정상 `app.db.session()`을 새 경로로 전환했다는 뜻이 아니다.

## X. No-change

Raw 사건 없음은 roots/objects를 재생성 저장하지 않는다. Neutral INSERT→DELETE도
net membership이 비면 raw/index root를 유지하되 D1 revision/capture는 전진한다.
Sensitive-only update 역시 root와 R의 의미를 구별한다. Calendar/evaluation-only
변경은 raw finalizer가 hot view를 재사용하도록 승인하는 근거가 아니다. D3 producer가
fresh evaluation을 해야 한다. Optional v1 compaction은 금지 상태다.

## Y. Scaling·write amplification

최종 알고리즘/schema 기준 실측은 [summary.json](benchmarks/t66d2b/summary.json)에 있다.
Benchmark fixture 식별값은 `seed=662600`, evaluation date는 2026-10-05이며 current ledger 105행을 고정한다.
이 generator는 RNG를 사용하지 않고 행 번호로 값을 결정하므로 seed field는 profile label이다.
376/1k/5k/10k의 archive만 늘린다. Payment relationship seed와 설정은 동일하다.
T6.6A의 rich fixture와 다른 fixture이므로 bundle bytes/압축 수치를 재사용하지 않는다.

각 raw-row workload는 3 warmups+20 measured COMMIT이며 full differential oracle는
측정 밖이다. Bootstrap은 expensive O(N) initialization 1회로 표본 한계를 명시한다.
Card/cash title, historical update/delete, event note, no-change, 세 행 변경의 7종이다.
이는 실제 HTTP submit/금융 전체 response latency가 아닌 isolated transaction 측정이다.
행 수는 각 작업 시작 시점 기준이며 historical delete의 결과는 한 행 적다.
Delete 다음 재삽입은 같은 finalizer를 거쳐 측정 밖에서 준비한다.

다음은 **HOST raw-row transaction wall median / p95 ms**다.

| 작업 | 376 | 1k | 5k | 10k |
| --- | --- | --- | --- | --- |
| current card title | 545.73 / 556.85 | 570.89 / 598.15 | 534.02 / 545.85 | 568.91 / 572.48 |
| cash title | 366.40 / 386.01 | 326.96 / 386.59 | 388.68 / 396.85 | 338.45 / 341.03 |
| historical title | 341.82 / 351.04 | 476.52 / 492.70 | 573.21 / 583.26 | 507.08 / 523.80 |
| historical delete | 260.56 / 279.67 | 388.97 / 401.86 | 444.47 / 464.31 | 413.65 / 420.10 |
| payment event note | 455.19 / 468.82 | 477.81 / 492.71 | 511.32 / 514.38 | 460.16 / 462.23 |
| no-change | 54.46 / 61.27 | 68.86 / 70.21 | 64.57 / 65.34 | 60.18 / 61.98 |
| 세 ledger rows | 780.78 / 850.75 | 1080.01 / 1119.19 | 1135.67 / 1192.28 | 998.54 / 1008.90 |
| bootstrap 1회, median/p95 아님 | 2253.75 | 6284.62 | 31745.48 | 69234.97 |

Bootstrap을 제외한 28 cells·560 measured commits와 84 warmups를 완료했고 모든
workload 후 full differential oracle가 통과했다. 50k/100k는 expensive full oracle와
자원/시간 상한 때문에 실행하지 않았다. Bootstrap은 예상대로 N 증가 비용이 크다.

| current card 작업의 median 접근량 | 376 | 1k | 5k | 10k |
| --- | --- | --- | --- | --- |
| net changed rows / changed leaves / closure identities | 1 / 1 / 6 | 1 / 1 / 6 | 1 / 1 / 6 | 1 / 1 / 6 |
| object SQL reads | 51 | 58 | 65 | 73 |
| 신규 immutable objects | 17 | 17 | 18 | 21 |
| 신규 object C1 bytes | 156557 | 156896 | 160040 | 161781 |
| 별도 신규 row bytes | 825 | 825 | 825 | 825 |
| SQLite VM lower-bound indication | 21800 | 21800 | 21800 | 21800 |

네 규모에서 raw-row 경로의 ledger full-scan plans는 0이었다. Object reads/paths는
역사 전체 행 수가 아니라 tree/index 경로에 따라 증가했다. 시간만으로 O(1)을 선언하지 않는다.
10k card의 wrapper 호출은 SELECT 262, INSERT 93, UPDATE 2, DELETE 3, PRAGMA 182,
BEGIN/SAVEPOINT/RELEASE 각 1회다. INSERT에는 edge/metadata가 들어가며 native trigger
내부의 개별 statements 전체를 세었다는 뜻이 아니다.

10k card stage medians는 begin 22.63, raw 2.73, capture 28.78, coalescing 260.42,
tree 93.07, facts 51.10, closure 3.76, aggregates 0.20, objects 102.54,
root 0.15, COMMIT 3.23ms다. Capture에는 base-generation load와 D1 검사가 포함된다.
Resolver 시간은 coalescing/closure 등 해당 단계 안에 포함되며 별도 독립 timing이 아니다.
각 단계 median의 합을 total median과 같다고 주장하지 않는다. CPU total median은
566.91ms다. 특히 C1 decode/hash·bounded leaf 재구성의 상수 비용이 크며 이를
이미 최적화했다고 표현하지 않는다.

10k no-change는 신규 objects/rows/leaves 0, object reads 19, wrapper SELECT 102와
PRAGMA 182였다. D1 admission의 고정 setup 비용도 남는다. 역사 delete의 신규 objects
median 0은 warmup 뒤 동일 representation을 재사용한 dedup 효과이지 삭제 비용 0이 아니다.
처음 삭제·반복 복원 없는 실제 workload의 object write 수를 대표한다고 주장하지 않는다.
신규 object bytes는 C1 payload일 뿐 SQLite page/journal의 물리 write bytes나 wire bytes가 아니다.

측정은 begin/raw/capture/coalescing/tree/facts/closure/aggregates/objects/root/commit을
분리한다. Wrapper SQL 호출 수는 trigger 내부 native statements의 총수가 아니다.
SQLite progress handler의 VM steps는 100-op 단위 lower-bound indication이다.
SELECT뿐 아니라 raw DML의 EXPLAIN QUERY PLAN을 검사하여 native FK scan도 확인한다.
새 leaf/tree/index node 수는 최종 changed representation의 nodes이며 physical object
INSERT 수와 다르다. 기존 exact bytes가 저장되어 있으면 object INSERT는 0일 수 있다.

Raw samples/log는 `/tmp/money-note-d2b-*`이며 Git에 큰 DB/response를 넣지 않는다.
CPU affinity/frequency/thermal을 고정하지 않았고 full regression과 실행이 겹쳤다.
Wall latency를 D1의 별도 host 결과와 직접적인 인과 비교로 해석하지 않는다.
RSS는 process high-water이며 bootstrap/reference 검증도 포함한다.
376/1k/5k/10k 누적 process RSS high-water는 각각 73264/88364/184928/312352KiB였다.
환경은 Intel Core i7-8750H, RAM 24,458,564KiB, Python 3.12.3, SQLite 3.45.1이다.
동일 synthetic initialization의 journal mode는 DELETE, synchronous=2(FULL), page size=4096이다.
새 진단 CLI는 출력 경로를 새 `/tmp` 파일로 제한하고 기존 파일 덮어쓰기를 거부한다.

## Z. 남은 O(N) — 완료 차단 항목

**D2B-G01 / Medium / 구현 completeness·성능 의존성:**
[financial_relationships.py](../backend/app/services/financial_relationships.py)의
`_validate_card_payment_rows()`는 여섯 관계 table 전체를 읽는다.
`validate_runtime_recurring_ownership()`도 전체 ledger를 읽는다.
[card_payments.py](../backend/app/services/card_payments.py)의 event writer와
[entries.py](../backend/app/repositories/entries.py)의 `_delete_card_payment_references()`
등이 이 경로에 의존한다. 실제 두 parity scenario에서 전체 ledger SELECT를 확인했다.

추가로 현재 Summary의 `cash_flow_total`, policy horizon/closed-month 계산과 전체
response preparation을 새 maintained inputs에 연결하지 않았다. 이들은 finalizer가
path-local이라는 사실만으로 사라지지 않는다. Existing financial formulas/validation을
생략하거나 read-only validation receipt를 writable transaction에 위장 재사용하지 않았다.

필요한 targeted correction은 complete accepted base + 실제 captured closure를 근거로
기존 writer의 필수 구조 검사를 동등하게 수행하는 **격리 bounded writer/read adapter**와
maintained input 연결이다. 실제 금융 response parity 및 SQL/VM 접근량을 함께 검증해야 한다.
이 correction이 끝나기 전 D2b 완료나 history-independent financial submit을 주장할 수 없다.
이는 새로운 production defect를 도입했다는 뜻이 아니라 미완료 D2b gate다.

새 finalizer의 steady-state는 사건 D, leaf L, 실제 closure R, affected paths와 row bytes에
의존하도록 구현했다. Bootstrap/full oracle/restore/backup/대량 cascade/context closure의
O(N)은 명시 예외다. 모든 작업 O(1)이나 모든 backend O(N) 제거를 주장하지 않는다.

## AA. 후속 단계

- **DEFERRED TO D3:** authenticated coherent observations, hot/control/Target producer,
  transfer authorization, lease, pin/refcount/GC. 현재 accepted raw/index objects를
  정상 client에 노출하지 않는다.
- **DEFERRED TO E:** mobile immutable store, Android power-loss ordering, validated reuse,
  atomic pointer, frozen B/J/pending/reconciliation/legacy adapter.
- **DEFERRED TO R1:** large restore/Mobile Wins staging·backup·idempotent apply·epoch adapter.
- **D2b 내부 미완료:** 위 D2B-G01을 D3 의존성으로 바꾸지 않고 먼저 해결한다.
- 정상 rollout 전 모든 writer/old-client/restore consumer compatibility와 독립 감사 필요.

## AB. 새 테스트

새 targeted corpus는 최종 73 parameterized cases다. 고정 random seed 662501–662503은
각 40 transactions, 662511–662512는 각 30 transactions로 합계 180 random commits다.
이는 사용자 제공 D2a 감사의 1,200 mutation steps를 이번에 다시 측정했다는 뜻이 아니다.

Oracle는 actual SQL rows, 별도 `isolated_sync_reference.audit_tree/facts_from_raw/patricia_root`,
native FK, independently derived reverse/context/counts/cash state다. O(N) oracle는
bootstrap/test assertion 밖 normal finalization에 들어가지 않는다. Hash/root count만
맞는지 확인하는 circular test로 대체하지 않았다.

## AC. 실행 검증·재현

```bash
# backend/ 기준
../.venv/bin/python -m pytest -q tests/test_isolated_sync_finalization.py
../.venv/bin/python -m pytest -q --durations=8

# repository root 기준
.venv/bin/ruff check backend scripts/benchmarks/t66d2b.py scripts/benchmarks/test_t66d2b.py
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks/test_payload_bytes.py scripts/benchmarks/test_t66a_fixture.py scripts/benchmarks/test_t66d2b.py
.venv/bin/python scripts/benchmarks/t66d2b.py --output /tmp/money-note-d2b-performance-final.json
.venv/bin/python scripts/benchmarks/t66d2b.py --summarize /tmp/money-note-d2b-performance-final.json --output /tmp/money-note-d2b-summary.json
npm --prefix frontend run build
bash -n scripts/dev-server.sh scripts/deploy-server.sh scripts/release-mobile.sh
git diff --check
```

최종 backend 회귀는 **923 tests + 1,540 subtests PASS**, 808.77초다.
여기에 기존 D1 113개/D2a 131개, migration/Snapshot/금융/authoritative endpoint 검사와
새 D2b 73개가 포함된다. Safety/진단 보조 suite는 **44 PASS**, 3.24초다.
Ruff·shell 3개 syntax·문서 link·`git diff --check`는 PASS다.
Frontend production build도 PASS(1.38초)다. Python compileall도 실행했다.
Benchmark의 최종 28 cells와 compact summary 재생성·보조 테스트도 PASS다.
Raw report는 829206B로 `/tmp/money-note-d2b-performance-final.json`에 보존하며,
compact 요약만 저장소에 둔다. 원 표본이 사라지면 위 opt-in 명령으로 재생성한다.
ShellCheck는 미설치로 미실행이다. 수정 전 중간 full regression은
920 tests + 1,540 subtests PASS였으며 최종 코드 결과와 구별한다. 중간 targeted는
72 PASS, 마지막 resolver/split/FK index 3 controls도 PASS였다. Schema/index와 계측을
보강하기 전 시작한 benchmark는 중단했고 최종 코드로 재실행했다. 중단 run의 값을
최종 실측으로 쓰지 않는다. Starlette/httpx의 기존 deprecation warning 1개가 있었다.
Flutter/Android/frontend tests·linter는 제품 코드 무변경으로 미실행이다.

## AD. 한계

새 Critical/High correctness 결함을 확인하지 않았지만 독립 감사의 무결함 판정은 아니다.
알려진 Medium completeness/scaling gap 1건 때문에 최종 판정은 INCOMPLETE다.
실제 전원 손실, arbitrary disk corruption, 모든 crash instruction, 긴 multi-device/lease,
50k/100k, 실제 단말, 정상 deployment 통합은 검증하지 않았다. Metadata/object/change
retention은 늘어나며 GC가 없다. Disk exhaustion은 실패/old state 보존으로 처리한다.
Auth-session SQLite lock risk, 기존 full backup·복구 비용도 해결했다고 주장하지 않는다.

## AE. Production 안전성

Production DB/API/credential/service 접근, deployment dry-run/apply, restart/reload,
APK 설치가 없다. Temporary self-owned synthetic SQLite 외 migration은 적용하지 않았다.
금융 공식·bundle·Snapshot v7·OfflineBaseline v4·pending/J·normal acquisition은 불변이다.
Experimental roots를 기존 API에서 반환하지 않는다. 제품 서버가 새 package를 자동
import하지 않는지도 source 검색으로 확인한다.

## AF. Commit/push·최종 Git

완료 gate 미충족으로 commit/push하지 않았다. HEAD는 시작 commit이고 새 파일과
bounded capture hook 변경은 working tree에 남긴다. Clean 완료를 주장하지 않는다.
실제 최종 Git refs와 diff 검증은 최종 실행 보고서에 별도로 기록한다.

## AG. 다음 작업

D2B-G01의 격리 bounded writer/read adapter와 maintained input 연결을 완료하고,
실제 금융 mutation의 whole-history scan 부재를 다시 입증한 다음 독립 D2b 감사를 요청한다.
D3 착수나 배포는 허용하지 않는다.

## AH. Targeted continuation — 최신 구현·검증

### A~D. 범위·기존 작업·원인

기존 object store/lazy resolver/capture/coalescing/tree/Patricia/fence/bootstrap/failure
구현을 폐기하거나 D1/D2a를 재작성하지 않았다. 원 blocker는 finalizer의 전체 rebuild가
아니라, borrowed 금융 command와 presenter가 기존 full-state validator/누계 입력을
호출한 것이다. 같은 template의 모든 과거 발생을 읽는 국소 query도 history-dependent다.
이를 단순히 `WHERE source_id=?`라는 이유로 bounded라고 분류하지 않는다.

새 [inputs.py](../backend/isolated_sync/inputs.py)의 `BoundedInputs`를 `begin_capture()`
뒤 명시적으로 생성해 기존 command에 `conn=`으로 전달한다. 새로운 금융 엔진이나
HTTP route가 아니다. Raw SQL은 그대로 전달하며 query를 가로채서 결과를 위장하지 않는다.

### E. 전체 조회 inventory와 해결

| 진입점·call chain | 이전 접근·실제 의존성 | 분류·현재 격리 입력 | 인덱스·비용 |
| --- | --- | --- | --- |
| payment create/delete/discount → `_validate_card_payment_rows` | 여섯 테이블 `SELECT *`; 무관한 모든 ledger/event/cash 포함 | A: complete accepted base + 모든 capture OLD/NEW가 seed인 관계 closure에 **기존** `validate_card_payment_ownership` 적용 | PK/payment-key, reverse destination+field; 실제 active workbench H 및 영향 R |
| `list_entries` → `validate_runtime_recurring_ownership` | 전체 ledger; 원본/발생 epoch 필요 | A/B: 변경 행·현재/미마감 epoch의 closure에 기존 validator 적용 | source+month+timestamp, confirmed_month range |
| confirm/update/delete → `_require_recurring_ownership` | `id=? OR source_planned_entry_id=?`로 같은 template의 모든 과거 발생 | B: 요청 source + 미마감 발생 + 현재 원본 epoch + 실제 변경 target | `sync_input_recurring_epoch`; 마감된 불변 발생 재검사 없음 |
| recurring cancellation → `_ensure_recurring_confirmation_epoch` | source/target + 전체 source children | B: 위 입력에 요청 삭제 target을 명시적으로 포함 | 동일; archive·NULL 날짜를 identity selector에서 배제 |
| `list_confirmed_planned_entries` | 모든 planned/expense 후보 | A/B: current confirmed sources의 필요한 완전한 epoch closure | current section + source epoch index |
| current deletion → `_legacy_recurring_source` | 모든 non-NULL source ID를 Python set에 materialize | B: hot confirmed template별 `SELECT 1 ... source_id=? LIMIT 1` | 기존 source index; 실제 existence만 필요 |
| Summary → `cash_flow_total` | cutoff 이전 모든 cash amount | C: 검증된 Fenwick prefix + 현재 transaction 전체 cash delta | 최대 약 22 calendar PK lookups + D + proof paths |
| Judgment → 최근 마감 월 건수 | 모든 archive expense GROUP BY | C: indexed top-k count + OLD/NEW overlay | `(domain,key)`; k+D 후보 |
| policy descriptor 입력 horizon | 전체 ledger/panel/batch에서 최대 월 추출 | C: `BoundedInputs.policy_horizon` | maintained month count의 indexed maximum + D; full Snapshot exporter는 불변 |
| Summary/month-discount → `allocation_totals(..., 'discount')` | 모든 과거 discount allocations | B: 실제 projection payment keys별 기존 exact sum 입력 | allocation payment-key index + event PK; 관련 allocation R |
| payment batch projections → batch allocations/events | 해당 batch와 event 관계 | D: 기존 금융/grouping 코드 유지 | event(type,batch)·event FK·allocation(event,key) index |
| `discount_month_status` | LIKE는 date index가 있어도 scan 가능 | B: canonical month expression index; legacy 비패딩 월의 prefix 의미도 별도 indexed range로 유지 | `sync_input_ledger_month` / 기존 date index |
| payment `_primary_income_total` | cash LIKE month | B: 실제 payment context의 month+primary-income indexed 입력 | `sync_input_cash_month`; 해당 월의 실제 income rows |
| fixed/payment/cash ordering | cash 전체 MAX(sort_order) | B: 기존 MAX SQL 그대로, 별도 sort index | `sync_input_cash_sort` extremum lookup |
| month status → legacy recurring EXISTS | NULL-source history를 LIKE로 읽을 위험 | B: 서버가 정한 target month expression index | ledger month + source epoch index |
| Summary fixed/claim/frozen/panels | panel_type 필터에 month-first index만 존재 | B/H: type index 추가; 미삭제 config/queue 전체는 진짜 hot input | `sync_input_panel_type`; H가 큰 경우 H 비용 유지 |
| native ledger DELETE → FK batch-items | child entry_id scan | B: 이전 D2b의 `sync_fk_item_entry` 유지 | child key SEARCH; source FK 기존 partial index도 유지 |
| D1/D2b certificate INSERT → deferred FK child lookup | `sync_tx_fence`·`sync_authority_fence`의 finalized ID 검색이 누적 fence 전수 scan | B: 격리 profile에 두 `finalized_tx_id` 인덱스 추가; D1 trigger/fence 의미 불변 | `sync_input_capture_fence_finalized`·`sync_input_authority_fence_finalized`; ledger N뿐 아니라 transaction history M scan도 제거 |
| template DELETE/큰 CASCADE/기간 역행 | 실제 역사적 source/reference/eligibility가 대량 변경 | D: 영향을 받는 모든 D/R을 capture·검증 | O(D+R) 가능; bounded single-row라고 위장하지 않음 |
| full Snapshot/mandatory backup/bootstrap/restore | 완전한 history 자체가 필요 | E: O(N) 유지, 정상 bounded path 밖 | 기존 안전 경계 보존, R1 별도 |

### F~J. 입력 scope·payment·recurring·삭제

[financial_inputs.py](../backend/app/services/financial_inputs.py)는 구현을 자동 생성하지
않는 opt-in scope 경계다. `backend/app`은 `isolated_sync`를 import하지 않는다.
일반 SQLite connection에는 원 query와 validator가 그대로 실행된다. 기존
`CardOwnershipReadView`는 자기 query_only·schema·savepoint/lifetime 검사를 유지한 채
명시적인 provider만 전달한다. 쓰기 transaction에 read-only PASS를 위장 재사용하지 않는다.

Provider는 accepted generation/tx_id/base revision에 결합한다. transaction 종료·재시작·
finalize 뒤 재사용을 거부한다. net은 매번 실제 D1 사건과 revision interval을 확인하며
같은 revision의 SAVEPOINT ABA나 여러 command의 앞선 쓰기를 stale cache로 취급하지 않는다.
OLD base reverse와 NEW capture adjacency의 합집합으로 끊어진 관계도 포함한다.

`maintenance.incoming/context_seeds`는 전역 facts의 UNIQUE 보증을 유지하면서, 변하지 않은
마감 epoch를 source의 새 확인과 독립적으로 재사용한다. 현재 source epoch와 미마감 child는
인덱스 range로 모두 읽는다. source 삭제/kind 변경·마감 월 역행은 이 축약을 허용하지 않는다.
실제 변경된 과거 child는 날짜와 무관하게 항상 seed다. 새 UNIQUE/FK/source/epoch 위반을
과거 검증 재사용이라는 이유로 허용하지 않는다. 원본 한 건에 300개의 마감 발생이 있는
반례 fixture에서도 새 확인의 SQL/closure가 이 전체 이력을 enumerate하지 않는지 검사한다.

일반 historical delete는 지급 여부의 기존 indexed allocation/event 검사를 그대로 사용한다.
지급된 행의 거부 문구, reference cleanup, event total 재계산 및 source 확인 취소는 기존
함수가 담당한다. 관계 없는 과거 행까지 읽던 ownership 입력만 교체했다.

### G. Maintained input의 transaction 일관성

Base Fenwick/count/horizon 값은 **commit 전까지 base 값**이다. Provider는 first-OLD/final-NEW
전체 delta를 덧씌운다. cutoff 변경·과거 cash 날짜 이동·삭제·여러 command·rollback/savepoint를
처리한다. 넓은 Python 정수 중간값을 보존하고 named Summary/allocated total의 기존
`exact_money` 경계를 그대로 사용한다. 할인·배분·Summary·Judgment 공식은 복사하지 않았다.

추가된 `sync_commits.input_hash`는 local maintained-input proof다. 기존 C1/Patricia 객체를
재사용하지만 **protocol global facts root나 raw root가 아니다.** `local-maintained-input`
keys에 저장한 cache cell 값으로, 읽거나 변경할 cell을 exact 비교한다. 오래된 cash/count/
horizon을 새 authority로 다시 인증하는 것을 거부한다. 기존 33 capture triggers는 불변이다.
격리 draft storage checkpoint만 `1000003`, profile 3으로 명시했다. 정상 DB checkpoint 4와
Snapshot 7, RAW_SCHEMA/프로토콜 의미는 바꾸지 않는다. 미커밋 draft profile 2는 임시
sandbox만 존재했으며 product migration 대상이 아니다. D1→3 설치는 여전히 atomic하다.

Finalizer는 OLD cache 값을 proof와 비교 → delta maintenance → 변경 local facts/path 저장 →
certificate/input_hash 준비를 같은 raw/object/index/root transaction 안에서 수행한다.
Bootstrap만 전체 local facts를 만든다. 정상 commit에서 모든 aggregate를 다시 만들지 않는다.
Hash는 server 인증이 아니며 privileged DB/authorizer 우회 공격까지 보장하지 않는다.
완전한 valid base와 보호된 metadata write 경로라는 기존 귀납 전제는 유지한다. 사용하지 않는
모든 object/cache의 임의 disk corruption을 매 commit 전수 탐지했다는 주장도 하지 않는다.

### K~L. 동등성·SQL 증거

[d2b_financial_reference.py](../backend/tests/d2b_financial_reference.py)는 기존 함수를 호출해
12개 projection을 비교하는 **test-only 입력 조립**이다. Full bundle/Snapshot을 숨겨 호출하지
않는다. Summary, payment allocation/status, current/confirmed entries, panels, cash, settings,
month status, owner/family policy, transit profile, Judgment를 legacy full-state 계산과 비교한다.
Judgment의 기존 요청별 random 문구는 test seed로 통제하며 level/입력/공식은 바꾸지 않는다.

새 테스트는 성공과 거부를 모두 비교한다. Payload schema에서 먼저 실패한 것을 command
거부 동등성으로 오인하지 않도록 오류 type/message와 실제 지원 payload를 확인한다.
archive actual NULL date, 수정된 실제 금액, 월 경계, 정책 변경, 반복 확인, payment create/cancel,
cash wide cancellation, source 삭제/SET NULL, 중복 발생, missing key, 과다 배분, 변경 retry,
지급된 행 삭제, stale cache/context 등을 포함한다. Full-state oracle는 **테스트 밖 정상 경로에
없다.** 기존 73개 corpus의 의미를 보존했고 storage version 음성 검사는 새 VERSION+1을 거부한다.

### M. 새 benchmark 방법과 증거

[t66d2b_writers.py](../scripts/benchmarks/t66d2b_writers.py)는 376/1k/5k/10k, 고정 hot 105행,
seed 662602/evaluation 2026-10-05, 10개 금융 workload마다 warmup 3 + measured 20을 수행한다.
실제 command → 12개 projection → finalizer → SQLite COMMIT을 측정한다. Cash/payment/recurring/
fixed/delete의 다음 표본 준비도 같은 finalizer로 하되 측정 밖에서 수행하여 hot 규모를 유지한다.
매 표본 legacy 금융 oracle, 규모별 시작/끝 full structural/Patricia/raw oracle는 측정 밖이다.
기존 28-cell raw-row 결과와 이 40-cell whole-financial 결과는 workload가 다르므로 직접적인
속도 개선율로 나누지 않는다. Bootstrap은 규모별 O(N) 1회, tail 성능 증거가 아니다.

계측은 Python SQL 호출 수, 반환 행 수, SQLite progress VM 100-step 하한, 실제 실행된 SQL의
EXPLAIN QUERY PLAN, 영향 closure/leaf/path/object 수와 C1 bytes다. Native FK의 lookup도 DML
plan에 포함한다. 반환 행만으로 bounded라고 판정하지 않는다. LIMIT 0 schema probe의 SCAN은
행 접근 0으로 별도 분류하며, 큰 sync_objects/facts/history alias scan을 예외로 감추지 않는다.
현재 scalar revision/profile/context, config/queue H와 schema metadata는 history N과 구분한다.
EXPLAIN은 진단 privilege에서 compile만 하며 source mutation을 실행하지 않는다.
객체 bytes는 SQLite page/WAL/journal의 물리 write bytes가 아니다. RSS도 bootstrap/oracle를
포함한 process high-water mark이지 bounded transaction만의 allocation이 아니다.
`writer_ms`는 provider 준비·기존 command·SQLite capture trigger 실행을 포함한다.
`capture_ms`는 base generation 취득과 D1 schema/coverage finalization을 포함하며,
순수 trigger CPU만 독립 분리한 값은 아니다. `aggregates_ms`에는 local proof 검증·경로 갱신도
포함된다. Projection 전체 시간과 그 안의 validator 시간을 중복 합산하지 않는다.
단계별 median의 합을 total median이라고 간주하지도 않는다.

최종 실측 표는 AI, 회귀와 재현은 Q~R 및 AJ에 기록한다.

첫 40-cell run은 800개 금융 동등성 비교를 통과했지만, 강화된 scan gate가 두 fence의
FK child scan을 발견했다. 이 중간 run의 raw 값은
`/tmp/money-note-d2b-bounded-writers-final.json`에 보존하며 **최종 scan-gate 증거로 쓰지 않는다.**
대상은 ledger 전체 조회가 아니라 누적 transaction fence 수 M에 비례하는 SQLite FK 입력이다.
두 격리 인덱스를 추가하고 certificate INSERT의 실제 EXPLAIN이 SEARCH인 음성/양성 검사를
추가했다. 최종 재측정은 별도 raw 파일을 사용한다. 재측정의 전체 graph oracle를 규모별
시작/끝으로 두는 것은 측정 밖 중복 비용만 줄이며, 모든 표본의 12-projection 비교·측정 경계·
3 warmups/20 samples·실제 금융 workload는 그대로다.

### N~P. Transaction·실패·기존 foundation

기존 D1 capture/fence와 D2a C1/tree/Patricia는 유지한다. Local input proof까지 원 raw mutation,
reverse, aggregate, objects, certificate와 함께 SQLite에서 commit/rollback한다. D1-only
certificate로 authority를 완료할 수 없고 finalize 뒤 raw write도 막는다. 새 stale-cache
finalizer 실패 뒤 fresh connection으로 이전 generation을 확인한다. 이전 SAVEPOINT/COMMIT
busy/storage-full/프로세스 종료/동시 writer/reader/Snapshot 검사는 그대로 다시 실행한다.
프로세스 crash 검사를 Android/하드웨어 power-loss 보증으로 표현하지 않는다.

### Q~R. 회귀·남은 O(N)

최종 소스의 전체 backend는 **953 tests + 1,540 subtests PASS**, 750.06초다.
기존 D1/D2a, Snapshot/financial/authoritative API/schema 및 D2b **103개**(기존 73 + 신규 30)를
포함한다. 별도 targeted 102개 PASS(167.18초)는 마지막 fence-index 검사 추가 전 결과이며,
그 뒤 집중 5개 PASS(13.77초)와 위 최종 전체 회귀로 구별한다. Safety/diagnostic은
**46 PASS**(2.59초), frontend build PASS(1.26초), Ruff·compileall·shell 3개 syntax·현재
문서 local links·`git diff --check`도 PASS다. Backend와 safety 실행에는 기존 Starlette/httpx
deprecation warning 각 1개가 있었다. Flutter/Android 및 frontend test/lint는 제품 코드
무변경으로 미실행이다(frontend build는 실제 실행). 이전 923/1540을 재사용한 수치가 아니다.
Artifact 완성 뒤 동일 safety corpus를 재확인한 결과도 **46 PASS**(2.28초)다.

일반 제품 runtime의 full bundle/Snapshot/backup 및 특별 restore/reconciliation
adapter는 그대로다. Initial/bootstrap/full recovery O(N), 실제 대량 D/R, H 또는 정책/config S가
큰 경우의 비용은 예외로 명시한다. 모든 backend O(N) 제거나 production submit 성능을
주장하지 않는다. D3 activation·R1 large restore·E mobile store·GC/lease는 구현하지 않았다.

현재 bounded 계약은 **명시적 `BoundedInputs`를 전달한 지원 command와 presenter**다.
Raw `FinalizationConnection`을 그대로 기존 financial function에 전달하는 것은 legacy
full-state 입력 선택이며, bounded performance 경로라고 부르지 않는다. 후속 writer/observation
adapter가 이 opt-in 경계를 지켜야 한다. D2b raw SQL capture 자체는 여전히 전체 11 tables를
지원하지만 모든 top-level HTTP/restore/reconciliation workflow를 연결했다는 뜻은 아니다.

정상 경로의 비용 모델은 D개의 변경 payload + L개의 ordinary leaf(최대 256행/256KiB,
oversized singleton은 해당 row의 실제 bytes) + 영향 R +
변경 B+tree/Patricia/index path + 실제 hot H/config S 입력이다. SQL B-tree/해시 tree의
lookup depth와 bytes 상수도 포함되므로 strict O(1) 또는 latency가 완전히 평평하다고
주장하지 않는다. `result_rows`는 schema PRAGMA와 metadata까지 포함한 반환 행 수이고,
`relationship_rows`는 반복 호출의 누적 금융 행 수, `closure_rows`는 virtual target/settings를
포함한 finalizer의 고유 방문 identity 수다. 물리적인 rows examined를 전부 직접 관찰한
계측이 아니므로 query plan·VM-step 하한·source call graph를 함께 사용한다.
Capture의 E개 ordered events도 처리해야 한다. Provider는 SAVEPOINT/rollback ABA를 피하려고
매번 전체 transaction-local E를 다시 확인한다. 고정 개수의 bounded command에서는 history N
scan이 아니지만, 아주 긴 command batch의 반복 coalescing이 D에 대해 항상 선형이라는
보장은 없다. 안전한 transaction-local memoization과 반복 schema admission 절감은 별도
증명이 필요한 최적화 후보이며, 이 작업에서 D1을 재작성하거나 검사를 완화하지 않았다.

### S~V. 격리·운영·commit·다음 gate

| Continuation 변경 파일 | 책임·검증 |
| --- | --- |
| `backend/app/services/financial_inputs.py` | 명시적 inactive 입력 interface; 기본 SQLite는 `None` |
| `backend/app/services/financial_relationships.py` | provider 분기·기존 read-view lifetime 유지 |
| `backend/app/repositories/entries.py` | recurring source/confirmed/삭제 후보와 최근 마감 count 입력 |
| `backend/app/services/summary.py` | 기존 Summary 공식의 cash prefix·현재 할인 입력만 교체 |
| `backend/app/services/card_payment_reads.py` | 현재 payment month의 primary income 입력 |
| `backend/app/services/card_payments.py` | 월 범위·현재 payment keys의 할인 allocation 입력 |
| `backend/app/services/month.py` | 현재 target month의 legacy-generated EXISTS 입력 |
| `backend/isolated_sync/inputs.py` | tx/base-bound input provider·OLD/NEW overlay·local input proof |
| `backend/isolated_sync/maintenance.py` | 영향 epoch/context closure·touched aggregate cell |
| `backend/isolated_sync/finalization.py` | isolated profile 3·strict indexes·atomic local proof maintenance |
| `backend/tests/d2b_financial_reference.py` | 기존 12개 projection을 호출하는 test-only oracle 조립 |
| `backend/tests/test_isolated_sync_inputs.py` | parity·거부·stale cache/context·마감 이력·재개방·전수 열거 금지 |
| `backend/tests/test_isolated_sync_finalization.py` | 기존 corpus 유지·complete local proof와 새 version 음성 검사 |
| `scripts/benchmarks/t66d2b_writers.py` | 40-cell 실제 command+projection+commit·SQL/VM/객체 계측 |
| `scripts/benchmarks/test_t66d2b.py` | 기존 두 검사 보존·alias scan 분류·cursor 값/반환행 계측 |

App 파일에는 좁은 inactive input-scope 분기만 추가했다. 일반 connection이 provider를 생성,
설치하거나 experimental migration/endpoint를 활성화하는 경로는 없다. 원 금융 공식·raw
Snapshot 7·정상 acquisition·OfflineBaseline 4·B/J·pending/outcomeUnknown는 불변이다.
운영 DB/API/credential/service, deploy dry-run/apply, restart, APK 접근은 없다.
모든 completion gate 통과 전 commit/push하지 않는다. 다음 gate는 구현의 **별도 독립 D2b 감사**이며
D3 착수나 production 활성화 허가가 아니다.

## AI. 최종 HOST/synthetic 실측

새 [bounded-writers-summary.json](benchmarks/t66d2b/bounded-writers-summary.json)은
**최종 소스/격리 profile 3**의 별도 artifact다. 이전
[summary.json](benchmarks/t66d2b/summary.json)은 원 미완료 시도의 28-cell raw-row 결과로
그대로 보존했다. 이번 raw report는 1,501,120 bytes이며 SHA-256은
`2493f8fc4608d5f0ac34459a86ea12f89712513bcad8af48c9cbde8f4c9721ae`다.
`/tmp/money-note-d2b-bounded-writers-verified.json`에 모든 원 표본을 보존한다.
원 표본 JSON/DB/금융 row data는 Git에 추가하지 않는다.

환경은 Linux 6.8.0-146 x86_64, Python 3.12.3/GCC 13.3, SQLite 3.45.1,
i7-8750H 2.20GHz/12 logical CPUs, RAM 23,885MiB다. SQLite DELETE journal,
synchronous=FULL(2), 4096-byte pages, FK/recursive triggers=ON,
cached_statements=0, Store LRU=256이다. 별도 factory control에서도 PRAGMA를 확인했다.
AS 2GiB/CPU 3600초 제한, 고정 seed/date/hot composition을 사용했다.
CPU affinity/frequency를 고정한 전용 장비나 실제 Android 측정이 아니다.

### 전체 command + 12 projections + finalization + COMMIT

단위 ms, 각 cell **median / nearest-rank p95**, warmup 3 + measured 20이다.

| 실제 workload | 376 | 1k | 5k | 10k |
| --- | ---: | ---: | ---: | ---: |
| current card amount update | 663.53 / 725.76 | 692.83 / 708.23 | 710.42 / 724.55 | 722.11 / 732.16 |
| cash expense create | 145.74 / 147.98 | 150.64 / 164.23 | 158.36 / 161.46 | 162.67 / 166.34 |
| historical title update | 401.46 / 433.83 | 690.12 / 703.89 | 707.43 / 720.77 | 721.97 / 736.36 |
| historical delete | 332.95 / 352.96 | 609.37 / 621.39 | 621.77 / 634.44 | 634.84 / 652.15 |
| payment event create | 486.14 / 509.86 | 564.62 / 581.07 | 627.98 / 648.66 | 666.61 / 687.76 |
| recurring confirm | 923.26 / 940.91 | 1239.42 / 1252.00 | 1059.43 / 1111.97 | 910.76 / 931.22 |
| fixed confirm | 209.55 / 224.29 | 245.68 / 252.63 | 267.33 / 281.21 | 258.19 / 279.10 |
| transit policy toggle | 107.96 / 112.88 | 121.03 / 128.39 | 132.18 / 134.30 | 125.19 / 125.94 |
| no raw mutation | 84.68 / 86.62 | 91.78 / 92.78 | 99.36 / 100.51 | 94.87 / 103.95 |
| two entry updates + cash create | 776.31 / 849.53 | 854.95 / 867.90 | 895.27 / 912.11 | 868.94 / 949.70 |

**40개 모든 cell**에서 800회 측정/120회 warmup, 금융 동등성 PASS,
unbounded-table scan 0, EXPLAIN 오류 0이다. Raw field `ordinary_ledger_scans`는 이름과 달리
ledger뿐 아니라 모든 비상수 metadata/alias scan도 분류한다. Artifact의 97개 원 query-plan
union에는 `SELECT rowid ... LIMIT 0` schema probe의 SCAN도 남겨 두었다.
이는 `_validate_critical_structure`의 실제 행 접근 0이며 예외 분류를 숨겨 제거한 원본이 아니다.
Config H/S, singleton revision/context/profile, schema catalog 접근은 별도다.
두 fence는 실제 `SEARCH ... finalized_tx_id=?` covering index plan으로 바뀌었다.

초기 bootstrap은 단일 기술 표본(반복 median/p95 아님)으로 각각
2,029.39 / 5,552.88 / 26,872.87 / 54,383.08ms였다. Process RSS high-water는
75,820 / 89,284 / 188,708 / 319,392KiB로, bootstrap와 oracle를 포함한 누적 값이다.
50k/100k는 이번 continuation의 필수 40 cells·전체 회귀에 자원을 한정해 미실행했다.

### 10k 단계 median

단위 ms. 나머지 workload의 모든 단계와 min/max/stddev는 artifact에 보존한다.

| 단계 | Card | Cash | Historical delete | Recurring | No-change |
| --- | ---: | ---: | ---: | ---: | ---: |
| context/schema setup | 18.29 | 16.78 | 17.05 | 17.05 | 16.79 |
| writer/provider 준비·실행 | 9.56 | 5.79 | 11.70 | 239.78 | 4.81 |
| 12 projections | 248.93 | 38.75 | 243.77 | 56.86 | 31.68 |
| D1 coverage completion 포함 capture | 23.03 | 22.36 | 22.45 | 23.14 | 20.99 |
| finalizer coalescing | 205.85 | 1.42 | 205.49 | 225.95 | 0.00 |
| tree update | 73.13 | 0.43 | 35.90 | 77.78 | 0.00 |
| global facts/Patricia | 41.60 | 20.74 | 34.81 | 112.85 | 6.20 |
| reverse/structural closure | 3.27 | 2.91 | 2.98 | 4.31 | 2.48 |
| aggregates/local proof | 5.58 | 27.74 | 8.61 | 5.83 | 0.78 |
| immutable objects 저장 | 83.40 | 15.85 | 41.80 | 133.19 | 2.56 |
| root/certificate 준비 | 0.27 | 0.27 | 0.30 | 0.29 | 0.25 |
| COMMIT | 10.01 | 9.26 | 8.85 | 5.36 | 8.40 |

### 10k SQL/object amplification

각 값은 median이다. L=처리한 leaf, I=처리한 structural+local Patricia nodes,
CAS/row는 실제 새 `sync_objects`/`sync_rows` records다. Bytes도 두 저장소를 구분한다.
SQL은 Python에서 발행한 SELECT/INSERT/UPDATE/DELETE 횟수이며 native index/trigger의
모든 내부 물리 쓰기를 센 수치가 아니다(PRAGMA 등은 artifact에 별도 보존).

| workload | L / I | CAS / row | CAS bytes / row bytes | SQL S/I/U/D |
| --- | ---: | ---: | ---: | ---: |
| card | 1 / 33 | 22 / 1 | 165308 / 838 | 970 / 96 / 2 / 3 |
| cash | 1 / 42 | 19 / 1 | 11974 / 464 | 930.5 / 80 / 1 / 1 |
| historical update | 1 / 35 | 19 / 1 | 164138 / 841 | 968 / 89 / 2 / 3 |
| historical delete | 1 / 33 | 0 / 0 | 0 / 0 | 926 / 7 / 1 / 7 |
| payment | 3 / 214.5 | 193.5 / 3 | 101869.5 / 1477 | 1950 / 577.5 / 1 / 1 |
| recurring | 2 / 107 | 109 / 2 | 222952 / 1711 | 1465 / 364 / 3 / 3 |
| fixed | 2 / 106.5 | 83.5 / 2 | 45580 / 1122 | 1272 / 266.5 / 2 / 3 |
| policy | 1 / 14 | 17 / 1 | 11591 / 415 | 831 / 62 / 1 / 3 |
| no-change | 0 / 0 | 0 / 0 | 0 / 0 | 719 / 5 / 1 / 1 |
| several rows | 2 / 98 | 50.5 / 3 | 180159 / 2134 | 1337 / 192.5 / 3 / 5 |

Historical delete의 0 CAS writes는 warmup/재삽입 cycle에서 **동일한 삭제 target objects를
이미 보유하여 deduplicate**한 결과다. 임의의 새로운 삭제가 언제나 bytes 0이라는 뜻이 아니다.
No-change에도 certificate/context metadata 쓰기는 남지만 historical immutable object는 안 쓴다.
Finalizer closure는 10k에서 4~14 identities였으며 반복 input relationship reads는 6~57행이다.
이는 원본 한 개에 300개 마감 발생이 있는 별도 negative fixture의 bounded closure 검사와
서로 다른 증거이며, 모든 사용자 데이터에서 fan-in이 작다는 주장이 아니다.

### 해석

history가 376→10k로 늘어도 card 객체 read는 56→84, no-change는 16→21이었다.
하나의 historical update는 한 leaf만 처리했고 CAS bytes는 376에서 80,145B,
1k 이후 159,773~164,138B였다. Leaf 충전율·tree 높이 때문에 376→1k latency가 뛸 수 있다.
Recurring도 changed leaf 2개지만 CAS bytes가 1k 328599→10k 222952로 달랐다.
따라서 latency를 N만의 선형식으로 맞추거나 단조 감소/증가를 강제하지 않는다.
Query plans·고정 leaf 수·path 수·전수 열거 금지 검사가 N-scan 부재의 주 근거다.

10k card의 coalescing/projection은 여전히 큰 ordinary leaf decode/admission 비용을 보인다.
Schema admission과 수백~수천 SQL calls도 고정 비용이다. 제거된 full-history scan과 별개로
검증된 immutable node reuse/직렬화/SQL 호출 최적화 여지가 크며, 검사를 생략해 줄이지 않았다.
기존 568.91/338.45/413.65/60.18ms는 다른 raw-row workload의 **이전** 값이다.
이번 whole-financial 수치와 개선율을 계산하지 않는다. 실제 production submit/phone/network
성능이나 D3 end-to-end synchronization 성능을 측정한 결과도 아니다.

## AJ. 최종 검증·재현

실행한 명령은 다음과 같다(전체 성공 로그는 출력하지 않고 /tmp에 보관).

```bash
# backend/ 기준
../.venv/bin/python -m pytest -q tests/test_isolated_sync_finalization.py tests/test_isolated_sync_inputs.py
../.venv/bin/python -m pytest -q tests/test_isolated_sync_inputs.py -k 'commit_certificate or reopening or forbids_full or unrelated_cash or nonpadded'
../.venv/bin/python -m pytest -q --durations=8

# repository root 기준; output은 존재하지 않는 /tmp 경로로 바꾼다
.venv/bin/python scripts/benchmarks/t66d2b_writers.py --output /tmp/money-note-d2b-bounded-writers-verified.json
.venv/bin/python scripts/benchmarks/t66d2b_writers.py --summarize /tmp/money-note-d2b-bounded-writers-verified.json --output /tmp/money-note-d2b-bounded-writers-summary.json
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks/test_payload_bytes.py scripts/benchmarks/test_t66a_fixture.py scripts/benchmarks/test_t66d2b.py
.venv/bin/ruff check backend scripts/benchmarks/t66d2b*.py
.venv/bin/python -m compileall -q backend/isolated_sync backend/tests/test_isolated_sync_finalization.py backend/tests/test_isolated_sync_inputs.py backend/tests/d2b_financial_reference.py backend/app/services/financial_inputs.py scripts/benchmarks/t66d2b.py scripts/benchmarks/t66d2b_writers.py scripts/benchmarks/test_t66d2b.py
bash -n scripts/dev-server.sh scripts/deploy-server.sh scripts/release-mobile.sh
npm --prefix frontend run build
git diff --check
git diff --cached --check
```

ShellCheck는 미설치로 미실행이다. 이 목록의 `bash -n`은 구문 검사일 뿐 deployment
dry-run/apply 실행이 아니다. 새 30개 테스트는 단일 fixture뿐 아니라 transaction overlay,
wide money·날짜 이동·기간 역행·실제 payment create/cancel·정기/고정 성공과 거부·정책·
stale cache/base/context·과거 cash/discount history·full enumeration 금지를 검증한다.
기존 crash/concurrency/Snapshot/migration corpus를 유지한 전체 953개 결과와 함께 판정했다.

## AK. 완료 gate·commit 경계·다음 작업

**D2B-G01: RESOLVED.** 지원 bounded 금융 경로에서 payment/recurring/historical delete의
의무적인 전체 history 조회를 제거하고 maintained inputs를 연결했다. 추가로 발견한 fence
FK scan도 해결했다. 자체 검토 범위에서 미해결 Critical/High/Medium correctness/scaling
finding은 0이다. 별도 독립 감사에서 무결함을 확인했다는 뜻은 아니다.

기존 dirty D2b 작업과 이번 continuation을 함께 commit하는 대상이며, 정확한 완료 commit과
HEAD/main/origin/main/실제 remote·clean 검증은 최종 Git 로그·응답을 따른다.
운영 데이터/서비스/배포/프로토콜 활성화는 전혀 수행하지 않았다. D3/E/R1의 미구현 adapter,
관측/전송 권한·lease/GC·큰 restore·Android durable storage는 그대로 후속 의무다.
다음 작업은 **독립 D2b 구현 감사 요청**이며 D3 착수나 배포가 아니다.

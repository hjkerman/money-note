# T6.6F Phase A — T6.6E4 독립 구현 감사

## 01. 대상과 판정

감사 대상은 `e386586194edbef1fc35f0ea1cf4145a2ae32685`이며 E3 독립 감사 기준점
`ab59d6bbc39f27c36beb059f984ef527ac7b0bef` 이후 **전체 E4 변경**을 검토했다.
P0, 초기 read adapter, T01/T02/T03 최종 completion을 모두 포함한다.

**최종 판정: FAIL — T6.6F PHASE A / E4 CORRECTION REQUIRED**

새 독립 사례는 **44 PASS / 1 FAIL / 0 INCONCLUSIVE**다. 수정하지 않은 제품에서
35개와 새 복구 경쟁 반례 1개, instrumented disposable copy의 비용 시험 2개,
실제 SIGKILL supervisor 6개, 원 P0 assertions의 baseline 재현 호환 시험 1개다.
**E4-A01 MEDIUM**: 이전 취소 요청의 data-only recovery가 같은 AppState의 최신 정상
설치 뒤 source를 이미 폐기된 frozen ID로 되돌린다. B/pending/graph/pins는 보존되지만
Frozen-B 읽기와 재시작 복구가 막힌다. §31의 독립 재현은 Phase B를 차단한다.
기존 구현 시험과 positive assertion 보강 재실행을 새 사례로 중복 계수하지 않았다.
최종 전체 회귀 수치는 §30에 기록한다. 구현 측 PASS를 독립 결과로 전용하지 않았다.

이 감사는 Phase A다. Phase B, R1, 운영 활성화, 배포를 수행하거나 승인하지 않는다.
감사일은 2026-10-15다. 제품 구현을 수정하지 않았다.

## 02. Repository·remote 검증

변경 전 `AGENTS.md`와 필수 project/domain/known-issues 문서, architecture의 서버 authority
신뢰 경계 및 offline/security/runbook 관련 계약을 읽었다. 시작 branch는 `main`, working tree는 clean이었다.

```text
HEAD = main = origin/main = 실제 remote refs/heads/main
e386586194edbef1fc35f0ea1cf4145a2ae32685
E3 기준점: ab59d6bbc39f27c36beb059f984ef527ac7b0bef
P0 구현: 35d7c53f1652310de75e492a98491efc3fd5cbba
P0 독립 증거: 671bb8668c16cba5f3729d9fb63fda4dbd1c67c5
```

모든 commit object가 존재한다. `git rev-parse HEAD main origin/main`, `git ls-remote origin
refs/heads/main`, `git status --short`, `git cat-file -t`, `git log`로 각각 확인했다.
실제 remote 확인을 tracking ref 확인으로 대신하지 않았다. 초기 상태와 71파일 SHA-256은
[`source-inventory.json`](benchmarks/t66e4-audit/source-inventory.json)에 있다.
최종 audit-only commit과 push 후 상태 확인은 §36 및 최종 응답으로 식별한다.

## 03. 전체 E4 diff inventory

`git diff --stat ab59d6b..e386586`은 **71 files, +13,824/-64**다.
제품 14파일, test/fixture 13파일, 문서·감사·benchmark 44파일이다.
P0 checkpoint에 속한 18파일과 이후 E4 53파일을 구분했다.

| 제품 경로 (`mobile/lib/src/` 아래) | 변경·감사 범위 |
|---|---|
| `money.dart` | P0 별도 authoritative setting admission; 원 input parser prefix 보존 |
| `api_client.dart` | P0 응답/기존 MW wrapper의 B 문법 구분 |
| `authoritative_bundle.dart`, `models.dart` | P0 complete bundle/AppSettings 읽기 |
| `offline/offline_data.dart`, `offline/offline_store.dart` | P0 B 읽기·저장; J/input admission 보존 |
| `segmented/object.dart` | P0 E1의 공통 authoritative helper 재사용 |
| `app_state.dart` | 명시 E4 read/native/legacy entry, 원 ticket·lineage·pending guard |
| `segmented/adapters.dart` | 별도 authority, typed mapping, full v7 materialization, pending view |
| `segmented/store.dart` | opt-in v5, read scope, schema/transaction·cache invalidation |
| `segmented/store_read.dart` | bounded SQLite snapshot, PK pagination, complete-store handle |
| `segmented/store_frozen.dart` | installed reference, durable frozen ownership, recovery/provenance |
| `segmented/store_publication.dart` | read-scope rejection과 frozen/installed prune exclusion |
| `segmented/workspace.dart` | cross-store source, guarded B, lineage binding, frozen B cache |

시험은 P0 monetary 183개, 초기 read/authority/crash/isolation, 최종 handoff/frozen/provenance/crash와
backend fixture를 포함한다. 모든 71개 경로·분류·hash는 inventory에 열거했다.
Dependency/lockfile, Android configuration/version, backend/frontend 제품, production schema,
금융 공식, navigation의 변경은 없다. T6.6C 규범 자체를 수정한 diff도 없다.

## 04. 독립 방법과 증거 구분

- **IMPLEMENTATION CLAIM**: 구현 보고서의 163/51/17/1,440/1,315 수치와 64 SQL 주장은 검증 대상이다.
- **INDEPENDENTLY VERIFIED FACT**: 직접 읽은 source, 실제 machine/JUnit, 별도 SQLite 연결,
  backend raw fixture, 독립 C1/hash/typed closure/F(raw)/Patricia, 실제 SIGKILL과 SQL observer 결과다.
- **UNVERIFIED ASSUMPTION**: Android 실기기 power loss, 임의 OS 파일 대체, unread bitrot의 즉시 탐지,
  모든 미래 graph 크기의 시간/메모리 보장은 이번 결과에 포함하지 않는다.

[`independent_test.dart`](benchmarks/t66e4-audit/independent_test.dart)는 실제 제품을 수정 없이 호출한다.
실제 server bytes를 E1 검증 cache에 미리 넣어 E4 경계 시험의 반복 network 비용을 줄였으나,
E2는 새 authenticated observation과 graph membership을 검증해야 한다. cache가 권한을 대신하지 않는다.
비용 시험만 source copy에 observer를 연결했다. 모든 DB/root/credential은 새 synthetic fixture다.

## 05. T6.6C 규범 mapping

| 규범 | 실제 구현과 독립 근거 |
|---|---|
| §22 | 별도 SegmentedAuthority; 명시 full export에서만 원 control·11 tables·기존 flat hash 사용 |
| §24 | isolated namespace SQLite의 manifest/receipt/pins/accepted·installed·frozen, 재시작 full proof |
| §25 | 원 AppState ticket, 기존 queue, 동기 final guard→COMMIT, readback 뒤 eligible pending·동일 candidate 설치 |
| §26 | SQLite·SIGKILL 결과는 통과; 동시 data-only recovery의 최신 handoff 보호는 **E4-A01 FAIL** |
| §29 | B/J bytes·ordered input·SQL frozen pins 보존; 최신 legacy/frozen source association은 **E4-A01 FAIL** |
| §31 | 일반 segmented Offline/recovery 진입을 실제로 거부; R1 proof/activation을 발명하지 않음 |
| §34 | E4 read/legacy/pending/frozen adapter만 구현; R1 Large Restore/MW와 Phase B 미실행 |

§33의 active legacy B/J/finalizing migration 유예도 유지한다. 이번 E4 entry는 eligible ONLINE의
isolated installation이다. 새 segmented MW/finalizing 실행이나 artifact/upload 권한을 제공하지 않는다.
기존 legacy finalizing·resolved-ID cleanup은 기존 owner에 남으며 회귀로 보존한다. 이 구분을
R1 구현 완료나 모든 복구 경로의 활성화 보장으로 확대하지 않는다.

## 06. E4-P0 보존

현재 P0 18파일을 독립 감사 hash 및 `35d7c53`의 실제 Git bytes와 대조해 모두 일치했다.
원 진단 5파일, 초기 E4 보고서 prefix **21,663 bytes**, 보존 목록의 기존 E4 12파일도 일치했다.
`verify_preservation.py`를 실행했고 product 변경 없이 MATCHED를 관찰했다.

기존 독립 corpus **24,836개**를 다시 평가했다. backend 수락 4,903/거부 19,933이며
authoritative/E1/frozen/raw/C1-hash/non-setting mismatch는 모두 0이다. 원 helper의
Python whitespace 29개·ASCII decimal grammar·safe-integer 조건을 source와 대조했다.
finite corpus를 전체 언어 동등성 증명으로 주장하지 않는다.

## 07. T01 원 ticket lifecycle

`app_state.dart:516`과 `:680`은 현재 user/cache/mode를 검사한 뒤 기존 `_refreshCoordinator.begin`
으로 **E2 전에** ticket을 발급한다. 이 local ticket을 E2 취득, E3 검증/prepare/COMMIT,
E4 materialization, lineage lock 대기, pending retirement·UI assignment까지 같은 closure로 유지한다.
publication 시 새 ticket을 발급하는 shortcut은 없다.

Receipt의 request/auth/lineage 정수는 역사적 data evidence다. 재시작의 workspace recovery는
AppState를 만들거나 ticket을 복원하지 않는다. 이전 candidate나 persisted receipt를 현재 설치
권한으로 승격하는 실제 caller를 찾지 못했다. 신규 coordinator나 credential store도 없다.

## 08. 최종 설치 권한과 session

`app_state.dart:560`, `:725`의 final guard는 ONLINE/no-J/no-reconciliation framing과 원 pending
token/owner/status/retry identity를 먼저 읽고, 원 ticket의 user/auth/request/mutation/mode 및
현재 session을 다시 검사한다. `api_client.dart:59`는 token을 secure-storage await **전에** 바꾸지만,
E2 transport가 캡처한 credential과 현재 getter 비교가 이 구간을 차단한다.

새 FA03/04/05/06은 E3 acceptance 뒤, source rename 전, 설치 전, retirement 직전의 mode,
credential, cancellation, principal 변화를 주입했다. legacy B/pending/installed/frozen을 별도로 읽었다.
FA07은 lineage lock을 기다리는 원 요청을 더 최신 legacy request로 무효화했다.
단순 exception assertion만으로 PASS하지 않았다. 이전에 적법하게 commit된 complete E3 cache는
남을 수 있으나 stale 요청의 pending retirement·UI 설치는 허용하지 않았다.

## 09. Pending retirement·acknowledgment

`workspace.dart:197`은 실제 파일의 owner/token/status/retry identity를 다시 읽는다.
`serverCommittedRebuildPending`만 허용하고 모든 hook/read 뒤 final AppState fence를 실행해
동기 unlink한다. 그 뒤 `app_state.dart:634`, `:777`의 전체 candidate assignment까지 await,
session getter, fault hook이 없다. post-install hook 실패는 committed outcome으로 분류한다.

Unknown은 실제 새 서버 관측과 데이터가 일치해도 byte-identical로 남았다. 재시작 recovery도
삭제하지 않았다. J의 operation ID/sequence/order/payload와 manual retry 규칙은 P0 hash 및
기존 frozen 회귀로 보존했다. GET/root equality를 mutation acknowledgment로 쓰지 않는다.

## 10. 완전한 legacy materialization

`adapters.dart:116`은 `hasFullMaterializationProof`를 요구한다. 이 proof는
`store_read.dart:13`의 owning-store full graph 검증과 private binding에서만 유효하다.
E2 `graph_verified`만으로 얻을 수 없다. 실제 모든 11 table을 keyset page로 읽고 원 exporter
ORDER BY, NULL-first, UTF8 BINARY, numeric ordering으로 정렬한다.

독립 checker는 실제 leaf bytes에서 rows를 추출하고 별도로 exporter 순서를 계산했다.
원 control의 schema/recurring version/exported_at/range/policy/columns와 설치된 Snapshot을
대조했다. backend restore validator와 별도 SHA/lineage 검사를 통과했다. 실제 backend fixture의
complete object set과 원 raw source도 비교했다. missing/corrupt bytes가 빈 데이터로 바뀌는 경로는 없다.

## 11. Snapshot v7 identity

full export는 기존 `bundleHash`의 table/data/policy/content hashes와 Snapshot ID,
state_fingerprint를 계산한다. `sync_root`를 대입하지 않는다. 실제 persisted B의 fingerprint는
backend `snapshot_state_fingerprint`와 일치하고 target.sync_root와 달랐다.
원 raw monetary/Unicode 표현과 control metadata를 보존했다.

FA15는 **같은 v7 Snapshot**을 유지하면서 resolved reconciliation ID만 바꾼 legacy B를 만들었다.
financial content hash가 같아도 v4 logical lineage가 달라 `LEGACY_LINEAGE_UNAVAILABLE`로 거부했다.
pending과 SQLite pin rows는 그대로였다. content equivalence를 lineage equivalence로 사용하지 않는다.

## 12. Segmented/legacy authority 분리

native entry는 `SegmentedAuthority{target,complete_store_handle,defaults}`와 같은 candidate를
설치한다. legacy envelope의 Snapshot/fingerprint 필드는 만들지 않는다. native 설치 전후 원
baseline.json bytes가 동일했다. explicit legacy entry만 full B를 materialize한다.

Accepted, installed data reference, frozen B가 항상 같은 generation일 필요는 없다.
예를 들어 accepted G3/native installed G3 뒤에도 legacy Frozen G1은 원 lineage로 보존된다.
각 reference는 complete graph를 가리키며 현재 AppState 권한을 저장하는 permit이 아니다.

## 13. Cross-store handoff 순서

SQL과 legacy 파일 전체를 하나의 원자 transaction이라고 주장하지 않는다.

```text
legacy: E3 accepted → full materialization → prepared frozen COMMIT
  → prepared source rename → guarded B rename/readback
  → full B/lineage correspondence → frozen installed COMMIT
  → installed reference COMMIT/readback → 원 ticket fence
  → eligible confirmed unlink → 같은 candidate UI

native: prepared source → fenced installed COMMIT/readback
  → generation snapshot의 hot/control hash read → 원 ticket fence
  → eligible confirmed unlink → 같은 candidate UI
```

`workspace.dart:248`은 source discriminator, namespace, generation/sequence 또는 frozen binding을
실제 SQL·B bytes와 대조한다. 확실히 publish되지 않은 preparation만 정리한다. rename 뒤
complete new B가 남은 경우 검증 후 data association만 마무리하며 과거 ticket/UI/POST/pending
cleanup을 재개하지 않는다. 불명확한 correspondence는 pins를 유지하고 fail closed한다.

위 순서는 단일 handoff 및 crash 재개에서 관찰한 정상 경로다. **동시 이전 recovery가 최신
handoff를 덮어쓰는 반례**는 별개다. `app_state.dart:666`의 실패 cleanup은 lineage lock 밖에서
실행되며, `workspace.dart:336`의 await 뒤 source를 재확인하지 않고 덮어쓴다. 이후 SQL 거부가
이미 수행된 파일 변경을 취소하지 못한다. 따라서 전체 cross-store consistency를 PASS로 승인하지 않는다.

## 14. T02 durable frozen pin model

opt-in `adapters:true`만 isolated segmented schema v5를 사용한다. default E3 v4 및 production
SQLite v4와 다른 파일이다. 기존 v4 schema/usage가 손상됐으면 upgrade로 수선하지 않는다.

`store_frozen.dart:444`의 `frozen`은 installed 최대 1 + prepared 최대 1, generation FK와
receipt checksum, C1 binding/checksum을 보존한다. `installed`는 current/previous data reference다.
generation root 4개와 immutable typed descendant edges가 실제 closure를 보호한다. frozen/installed
FK·retained triggers·`store_publication.dart:491,581` prune exclusion을 함께 검토했다.

## 15. Legacy lineage association

`workspace.dart:102`는 namespace/generation/sequence, user/synced_at/resolved ID,
기존 v7 fingerprint/Snapshot ID, **전체 v4 B의 원 recovery-lineage hash**, C1 B association
checksum을 별도로 기록한다. association checksum을 v7 identity로 바꾸지 않는다.

cold reader는 실제 legacy B와 원 control로 다시 materialize한 B의 전체 logical lineage 및
Snapshot identity를 비교한다. FA13/15 및 비용 lineage 변경은 같은 financial rows라도 다른
owner/lineage를 허용하지 않았다. metadata/J는 매번 원 parser로 읽으며 old J를 new G에 옮기지 않는다.

이 fail-closed 검사는 E4-A01로 잘못 덮인 source도 거부한다. 그러나 오류를 탐지한다는 사실이
최신 정상 설치의 association을 보존했다는 뜻은 아니다. §31은 새 연결에서도 이 연결 손상이
지속되는 실제 반례를 보존한다.

## 16. Pin lifetime·rollback·재시작

FA08에서 G1이 accepted current/previous 및 native installed current/previous에서 벗어나도록
후속 generation을 만들고 reopen했다. 실제 G1 closure와 frozen owner가 남고 읽기가 성공했다.
`discardUnacceptedGeneration(G1)`은 false, installed frozen preparation release는 거부됐다.
read scope close·logout은 durable frozen 소유권의 release가 아니다.

FA12는 frozen installed transition 안에서 정확한 `StateError('audit rollback')`를 주입했다.
원 installed owner와 새 prepared pin이 남았다. 새 B가 이미 rename된 경우 이를 clean rollback이라
표현하지 않는다. unresolved 전환의 양쪽 graph가 보호되고 후속 data recovery가 필요하다.
legitimate ONLINE/no-active-J legacy replacement만 같은 SQL transaction에서 이전 frozen association을
교체한다. current acceptance 변화만으로 old Frozen B를 해제하지 않는다.

## 17. T03 provenance reuse

`store_frozen.dart:328,345`와 `workspace.dart:359`를 추적했다. proof는 owning store identity,
SQLite data_version, namespace/principal/dataset/epoch/generation/roots, receipt, frozen binding,
schema/root pins, private immutable B 및 legacy file invalidation stamp에 결합된다.

warm에서도 exact schema/mandatory triggers/profile, durable receipt/root pins/frozen association,
hot/control hash-on-read를 수행한다. file stat은 integrity proof가 아닌 추가 invalidation signal이다.
AppState guard 결과·lease·pending acknowledgment를 재사용하지 않는다.

## 18. Provenance invalidation

새 FA11은 trigger, receipt, root pin, raw bytes, missing raw, legacy file/lineage, source discriminator,
schema version을 바꿨다. 매 경우 read를 거부하고 기존 B/pending을 추가 변경하지 않았다.
object corruption 주입 뒤 trigger 정의를 복원해 payload 오류와 schema 오류를 구분했다.

외부 SQLite COMMIT과 reopen은 실제 full proof 1회로 돌아갔다. 같은 owning connection의
정상 E3 acceptance만 바뀐 경우에는 Frozen G1에 대한 full 작업을 반복하지 않았다.
receipt/schema/pin 불확실성, transaction/readback failure의 cache invalidation 경로도 검토했다.
임의의 재해시된 local metadata나 OS open-DB 교체를 attacker authority로 신뢰하는 모델을 가정하지 않는다.

## 19. Full-verification equivalence

실제 같은 B와 ordered J를 변경하지 않은 full legacy reader와 optimized reader에 전달해
baseline.toJson, operation.toJson 전체 및 대표 projection 값을 exact 비교했다. 별도 graph oracle는
원 persisted C1/domain SHA, typed refs/edges, 11-table raw facts와 global Patricia root를 검증했다.

외부 손상 후 optimized path가 호출한 실제 complete verifier는 hash 오류로 거부했다.
missing pin과 wrong lineage도 직접 영속 상태에 근거해 거부했다. 서로 다른 두 제품 flag가
같다는 이유로 equivalence를 주장하지 않는다. unread bitrot의 즉시 탐지는 §24의 보장이 아니다.

## 20. 독립 Frozen-B work counters

`measure.py`는 임시 lib copy의 SQLite open만 `AuditDatabase`로 감싼다. 실제 select/execute,
driver returned rows/BLOB, actual pin writes를 관찰한다. complete verifier/Frozen recovery/
legacy load/hash는 실제 함수 진입에 별도 observer를 넣었다. 제품 work counter를 판정에 읽지 않았다.

실제 결과는 [`cost.json`](benchmarks/t66e4-audit/cost.json)에 있다. 5/512 history,
**146/2,177 required objects**, 같은 H와 2개 J를 사용했다.

| 측정 경계 | 작은/큰 SQL | returned rows | object-body bytes | raw/index | full verify/legacy full read | pin I/D/U |
|---|---|---|---|---|---|---|
| cold Frozen-B pending | 1,088 / 13,304 | 1,716 / 15,987 | 258,936 / 3,489,198 | 44/264 · 58/4,320 | 1/1 · 1/1 | 0/0/0 |
| unchanged pending 반복 | **85 / 85** | **423 / 423** | **9,451 / 9,451** | 0/0 | 0/0 | 0/0/0 |
| storage-only 반복 | **64 / 64** | **288 / 288** | **9,451 / 9,451** | 0/0 | 0/0 | 0/0/0 |
| unrelated E3 acceptance 뒤 | 85 / 85 | 423 / 423 | 9,451 / 9,451 | 0/0 | 0/0 | 0/0/0 |
| 외부 COMMIT fallback | 1,090 / 13,306 | 1,718 / 15,989 | 258,936 / 3,489,198 | 44/264 · 58/4,320 | 1/1 · 1/1 | 0/0/0 |
| reopen full proof | 1,088 / 13,304 | 1,716 / 15,987 | 258,936 / 3,489,198 | 44/264 · 58/4,320 | 1/1 · 1/1 | 0/0/0 |

구현 측 64 SQL 주장은 **storage-only 경계**에서 독립 재현됐다. 전체 B+J adapter 비용은
21 SQL이 더 있다. 이를 64라고 보고하지 않는다. 일반 반복의 불필요 full verification·pin writes는 0이다.

## 21. Graph scaling·fallback 비용

작은/큰 warm pending은 각각 32,583/24,394µs, storage-only는 21,533/17,808µs였다.
cold pending은 386,675/3,783,289µs였다. host/JIT/observer를 포함한 유한 측정이며 latency
차이만으로 cost PASS를 내리지 않는다. graph 크기가 늘어도 ordinary warm raw/index/full 작업이 0인
actual operation counts 및 source 논증이 주 근거다.

규범 §35/I25는 정상 steady-state의 full N fetch/hash/serialize/write 반복을 금지하며
조건부 비용을 `O(H + changed bytes + L log P + 256E)`로 제시한다. 모든 operation O(1)을
요구하지 않는다. §18/24의 cold initialization·complete-store restart O(N)과 명시 full legacy
export는 허용 경계다. 이 감사는 두 규모에서 unchanged Frozen-B 재검증·pin 재작성 0을 확인했다.
§35의 D/E 전체 1k/5k/10k/50k/100k integrated scaling은 Phase B 완료로 주장하지 않는다.

corrupt object는 59/38 SQL 뒤 `OBJECT_HASH_INVALID`, missing pin은 양쪽 8 SQL 뒤
`GENERATION_RECEIPT_INVALID`로 거부했다. 바뀐 legacy lineage는 132/153 SQL과 명시 full
materialization 뒤 `LEGACY_LINEAGE_UNAVAILABLE`였다. 정확한 bytes/pin 복원 후 full fallback을
거쳐 다시 warm으로 돌아갈 수 있었다. 이 예외 작업을 steady-state 비용과 혼합하지 않는다.

별도 EXPLAIN은 객체·root 조회의 PK lookup 및 bounded metadata scans를 확인했다.
[`warm-query-plans.json`](benchmarks/t66e4-audit/warm-query-plans.json)에 실제 SQL을 남겼다.
returned rows는 scanned VM rows가 아니며 9,451B는 object BLOB만 센다. metadata/J 파일,
물리 page I/O, cold-open usage aggregate, Android peak memory를 이 수치로 주장하지 않는다.

## 22. Generation-pinned logical reads

`store_read.dart:39`는 BEGIN DEFERRED 후 실제 pointer SELECT로 native snapshot을 확보하고
owning provenance를 대조한다. callback은 synchronous/bounded이며 Future와 escaped view를 거부한다.
동일 connection의 write/close는 BEGIN 전에 거부해 reader transaction을 훼손하지 않는다.

FA14는 실제 G2 prepare/COMMIT를 다른 store connection에서 시도했다. G1 Frozen read 동안
COMMIT는 STORE_BUSY로 rollback됐고 G1 rows는 동일했다. scope 종료 뒤 같은 준비를 commit해
G2를 읽었다. G1/G2 root·records를 섞지 않았다. read scope에는 crash-orphan durable reader row가 없다.
이것은 DELETE-journal reader와 writer의 직렬화이지 lock-free 병행 COMMIT 보장이 아니다.
[SQLite rollback locking](https://www.sqlite.org/lockingv3.html)의 SHARED/EXCLUSIVE 규칙과
실제 실행이 일치한다. `data_version`의 same/other-connection 차이는
[SQLite PRAGMA 문서](https://www.sqlite.org/pragma.html#pragma_data_version) 및 새 외부 COMMIT 시험으로 대조했다.

## 23. Monetary·Unicode regressions

원 `"\u001c+0001000.00\u001f"`는 backend/E1/authoritative bundle/B에서 수락되고 원문을 보존했다.
frozen input `exactMoney()`는 이전 거부를 유지했다. backend/E1 helper, C1/domain SHA,
Snapshot hash 및 original input parser prefix의 현재 hash는 P0 checkpoint와 같았다.

원 진단은 수정 없이 **3 PASS/2 FAIL**이었다. 두 FAIL은 이제 수락해야 하는 값을 계속 거부하라는
과거 assertion이다. 원 파일을 고치거나 현 구현의 correctness 실패/성공으로 재분류하지 않았다.
P0 독립 suite는 4 PASS/1 baseline fixture 실패였다. 후속 신규 파일에 `git show ab59d6b:path`가
불가능했던 오류이며, 새 호환 재현에서 원 monetary/codepoint/hash assertions가 모두 통과했다.
기존 Flutter P0 독립 integration 18개도 통과했다. 원본과 보완 실행을 모두 summary에 남겼다.

## 24. Backend 금융 authority

E4는 backend-produced typed projections를 기존 model로 소비한다. balance/discount/summary/
month close/payment formulas를 새로 계산하지 않는다. `OfflineProjection(B,J)`는 기존 ordered
input-only J의 provisional view다. raw 필드·monetary 문자열·Unicode·null·stable PK를 구조와 identity로
검사한 결과를 독립 금융 계산 엔진의 증명으로 표현하지 않는다.

## 25. 역사적 E4 blocker closure

| 역사적 문제 | 현재 확인한 교정·증거 |
|---|---|
| Monetary admission incompatibility | P0 원문 hash/24,836 corpus/원 반례/18 integration 보존 |
| 원 ticket pending/install handoff 부재 | E2 전 ticket부터 synchronous installation까지 같은 guard; 새 stale/pending 시험 |
| durable Frozen pin/legacy lineage 부재 | v5 durable owner/receipt/lineage, G1→G3/reopen/actual SQL closure |
| 반복 Frozen-B full verification | 독립 SQL·실제 함수 진입, 두 규모 warm 0 raw/index/full/legacy parse/hash/pin writes |

원 `t66e4-implementation.md`의 BLOCKED, resumption prefix의 INCOMPLETE, 초기 비용/개발 실패를
덮어쓰지 않았다. 최종 append만 읽고 최초 미완료 기록이 없었던 것으로 취급하지 않았다.

## 26. 새 independent cross-boundary cases

실제 45개 각각의 이름·결과는 [`independent-cases.json`](benchmarks/t66e4-audit/independent-cases.json)에 있다.

| 범주 | 새 실행 | 독립 oracle·관찰 |
|---|---|---|
| FA01–FA07, 양쪽 entry·시점 변형 | 원 ticket/session/mode/cancel/principal/new request | 실제 B/marker bytes, installed/frozen/accepted SQL, 원 backend closure/source |
| FA08–FA10 | G1 retention/reopen/unpin/reader close | direct SQL root closure, independent F(raw)/Patricia/receipt, escaped view 거부 |
| FA11 8종 | schema/trigger/receipt/root/raw/missing/lineage/source | 외부 controlled corruption 후 rejection, B/marker 추가 write 0 |
| FA12–FA14 | rollback, 다른 owner/lineage, 실제 G2 COMMIT race | committed rows와 file bytes, 실제 SQLite busy/rollback/retry |
| FA15–FA16 | equal content/different resolved lineage, 실제 R1 entry | old pending/pins 보존, AppState Offline 진입 false |
| FA17 — **FAIL** | 이전 취소 recovery 대기 중 같은 AppState의 최신 요청 정상 설치 | source가 폐기된 F0로 회귀; 새 DB handle에서도 FROZEN_BINDING_INVALID |
| 새 crash supervisor 6개 | 이미 installed G1 뒤 G2 handoff | SIGKILL PID barrier, fresh process/SQLite/graph/lineage, unknown marker 동일 |
| cost 2개 | cold/warm/unrelated/reopen/corrupt/pin/lineage | actual SQL/BLOB/function entries, unchanged full legacy reader |
| P0 호환 replay 1개 | 과거 baseline 재구성 | 원 assertions 그대로, 현재/과거 readers와 backend wire |

각 case는 실제 assertion 결과로 계수했다. 이 범주 표의 행 수나 비용 phase/child 호출 수를
독립 시험 수로 세지 않는다. 새 35개 제품 실행에 기존 구현의 51개 authority/race를 더해
새 86개라고 표시하지 않는다.

## 27. Process-crash 증거

새 supervisor 6개는 이미 G1을 설치한 뒤 legacy의 after_frozen_prepare, after_legacy_commit,
after_frozen_install, after_e4_installation 및 native의 after_segmented_install_pointer,
during_installation_readback에서 실제 Flutter tester를 SIGKILL했다.

fresh connection에서 accepted/installed/frozen/receipt/root closure와 모든 C1/hash/F(raw)/Patricia를
검증했다. legacy rename 전에는 old B, rename 뒤에는 검증된 new B와 unresolved 또는 finalized
frozen ownership이 남았다. native COMMIT 전에는 old installed/source, COMMIT 후에는 complete new
installed와 old Frozen B가 남았다. unknown marker는 **6/6 byte-identical**이었다.

data-only recovery 뒤에도 pending 삭제·POST replay·UI authority 복원은 없었다.
[`crash.json`](benchmarks/t66e4-audit/crash.json)에 전후 reference/sequence/lineage/hash를 보존했다.
개별 SQLite 원자성과 전체 파일 handoff의 차이를 유지한다.
[SQLite atomic commit](https://www.sqlite.org/atomiccommit.html)은 driver/filesystem 가정에 의존하며,
이 SIGKILL 결과를 OS crash/Android/hardware power-loss 보장으로 확대하지 않는다.
6개 SIGKILL 통과는 FA17의 동시 cleanup 결함을 배제하지 않는다. 해당 실패는 process kill 없이도 재현된다.

## 28. Authority race 결과

새 사례는 post-acceptance, source/pre-install/pre-retirement fence, session-before-auth-generation,
cancel, wrong principal, newer request/lineage queue를 별도로 검증했다. 기존 51개는 logout,
same-user reauth, 실제 mutation, newer legacy/segmented request, offline/unsupported mode,
wrong namespace, pending replacement, failed preparation, post-COMMIT classification도 포함한다.
최종 실제 기존 suite 개수는 §30의 machine 결과로 확인한다.

Native final guard→COMMIT는 `store.dart:296–299`, 기존 E3는 `store_publication.dart:439–440`이다.
guard 뒤 await/isolate/deferred transaction/UI notification/hook이 없다. private DB connection에
application commit/update/authorizer/UDF callback을 등록하거나 넘기는 경로도 없다.
fault hooks는 final guard 전 또는 COMMIT/readback 뒤에 있어 마지막 authority 검사를 우회하지 않는다.
반면 FA17은 취소된 요청의 lock 밖 `finally`가 후속 성공 요청의 source를 변경하는 경로다.
이는 final publication guard의 async gap이 아니라 data-only recovery serialization 및 재검사 결함이다.

## 29. E1/E2/E3·legacy isolation

기존 c1/graph/fetch/transport/verification/coordinator/Snapshot repository/OfflineProjection/
lineage validator 및 backend source의 protected hashes를 대조했다. E3 변경은 read-scope rejection,
frozen/installed retention exclusion이며 마지막 fence/COMMIT 본문은 동일했다.
공유 `_transaction`의 새 finalFence는 같은 BEGIN IMMEDIATE/schema/usage transaction 안에서 실행된다.

일반 startup/DI/UI에서 E4Workspace 생성, adapters:true open, 새 install/refresh entry의 자동
호출을 찾지 못했다. 정상 AppState 기존 부분은 E4 extension/import를 제외하면 E3 기준 bytes와 같다.
일반 routing/financial write/frozen input semantics는 보존했다. P0의 의도된 authoritative admission
호환 교정은 §06/23에 명시했다. R1 gate는 실제 FA16에서도 닫혀 있었다.

## 30. 전체 회귀 결과

| 실행 | 실제 결과 |
|---|---|
| 새 독립 전체 | **44 PASS / 1 FAIL / 0 INCONCLUSIVE**, FA17은 E4-A01 |
| 계측 없는 독립 read/authority/retention | 35 PASS; 그중 strengthened FA01 2개 재실행도 PASS, 중복 계수 안 함 |
| 독립 SQL 비용 | 2 PASS, 30 phases; full/corrupt/lineage fallback 포함 |
| 새 G1→G2 실제 SIGKILL | 6 PASS, 857.156초 |
| 원 E4 implementation tests | **163 PASS / 0 FAIL**: adapters 42, isolation 23, authority 16, 초기 crash 4, handoff 35, frozen 19, provenance 11, handoff crash 13 |
| 기존 T01/T02/T03 | handoff 35 / frozen 19 / provenance 11 PASS, 위 163에 포함 |
| 기존 E4 authority/race grouping | 51 PASS: handoff 35 + authority 16, 별도 새 51개로 세지 않음 |
| 기존 E4 process crash | 17 PASS: handoff 13 + adapter 4, 실제 child termination 확인 |
| 기존 26 SIGKILL regression | E1 7 + E2 3 + E3 16 PASS |
| E4-P0 monetary | 183 PASS, 원 독립 Flutter integration 18 PASS |
| P0 기존 독립 corpus | 24,836개, authoritative/E1/frozen/raw/C1-hash mismatch 0 |
| P0 원 Python suite | 4 PASS / 1 fixture FAIL; 신규 E4 파일의 과거 Git baseline 조회 실패 |
| P0 호환 baseline replay | 1 PASS; 원 monetary/hash assertions 보존 |
| 역사적 원 E4 진단 | 3 PASS / 2 과거 reject assertion FAIL; 변경·재분류 안 함 |
| E1 monetary/schema correction | 166 / 45 PASS |
| E2-A01 | Flutter response cleanup 13 PASS + 기존 독립 TCP Python 5 PASS; six rejection FD 모두 0 |
| E3 I25 / authority / process crash | 해당 incremental 6, baseline 1, I25 publication 30, diff 1, root-pin 2 / authority 19 / crash 16 PASS |
| 최종 full Flutter | **1,440 PASS / 0 FAIL / 2 SKIP**, `done.success=true`, exit 0, 3,017.864초 |
| Flutter analyze | PASS, exit 0 |
| Flutter debug APK build | PASS, exit 0; 설치 안 함 |
| 변경 Dart formatting | E4 diff 25파일 PASS; 새 audit Dart 4파일도 별도 PASS |
| 전체 Dart formatting | 기존 변경 없는 10파일 차이로 exit 1, E4 diff 밖임을 확인; 수정 안 함 |
| 최종 backend full | **1,315 tests / 1,540 subtests PASS**, exit 0, 1,970.848초 |
| Ruff / compileall | backend·관련 scripts PASS; 새 audit 파일도 별도 PASS |
| safety / diagnostic | 27 / 33 PASS, 총 60; production 실행 없음 |
| frontend npm test / build | 21 PASS / build PASS |
| git diff --check | PASS; audit-only stage 후 cached diff도 검사 |

실제 명령은 repository root 기준 아래와 같다. `flutter` 명령의 cwd는 `mobile`,
backend pytest의 cwd는 `backend`, npm의 cwd는 `frontend`다. 전체 suite에 포함된 기존 회귀를
개별 실행한 것처럼 추가 계수하지 않았다.

```bash
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine --concurrency=2 test
/home/hjkerman/.flutter/bin/flutter analyze --no-pub
/home/hjkerman/.flutter/bin/flutter build apk --debug --no-pub --dart-define=MONEY_NOTE_API_BASE_URL=https://audit.invalid
../.venv/bin/python -m pytest -q --junitxml=/tmp/mn-e4-phase-a-audit/backend-final.xml
.venv/bin/python -m ruff check backend/app backend/tests scripts/local_deploy.py scripts/tests
.venv/bin/python -m compileall -q backend/app backend/tests scripts
.venv/bin/python -m pytest -q scripts/tests
.venv/bin/python -m pytest -q scripts/benchmarks
E2_A01_OUTPUT=/tmp/mn-e4-phase-a-audit/e2-cleanup .venv/bin/python -m pytest -q docs/benchmarks/t66e2-a01/test_cleanup.py
npm test -- --reporter=json --outputFile=/tmp/mn-e4-phase-a-audit/frontend.json
npm run build
git diff --check
```

독립 시험 명령·instrumented copy 방법은 [audit README](benchmarks/t66e4-audit/README.md)에 있다.
최종 runtime은 Flutter 3.47.4 / Dart 3.13.3, backend venv Python 3.12.3이다.
fresh-state oracle/backend venv의 SQLite는 3.45.1, EXPLAIN·집계용 시스템 Python 3.13.9의
SQLite는 3.51.0, Dart native SQLite는 3.53.4다.
다른 driver의 EXPLAIN을 Dart VM의 실측 scan count로 바꾸지 않는다.
[`summary.json`](benchmarks/t66e4-audit/summary.json)은 실제 machine/JUnit/exit 상태와 최초 실패를 보존한다.

전체 Flutter는 hidden loader를 제외한 visible testDone과 `done.success`를 함께 확인한다.
Backend의 JUnit 2,855는 1,315 tests + 1,540 subtests 합계다. 다른 감사의 결과를 이번 결과로 쓰지 않는다.

첫 전체 Flutter는 **1,437 PASS/3 FAIL/2 SKIP**, 1,826.693초였다. 세 FAIL은 기존 E4 child의
120초 barrier timeout이다. 같은 제품·assertion·timeout으로 `--concurrency=2` 전체 재실행을
수행했다. 첫 실패를 삭제하거나 완료된 PASS라고 재분류하지 않는다. 직접 root cause를
입증하지 않았으므로 CPU/build 경합 탓이라고 단정하지 않는다.

첫 backend는 **1,314 PASS/1 FAIL/1,540 subtests PASS**, 2,478.716초였다.
`tests/test_isolated_sync_transfer.py:497`의 동일 quota case에서 expected 429 대신 503이었다.
이는 과거 E2 감사 §34에 보존된 동일 현상의 재발이다. 단독 재실행은 **1 PASS, 5.930초**였다.
최종 전체 재실행 결과는 위 표와 summary에 별도로 기록한다. 원인은 미확정이며 E4 diff에는
backend product/test 변경이 없다. E4 결함이나 환경 원인으로 임의 귀속하지 않았다.

감사 harness의 누락 import, 표준 inspect 이름 충돌, 무의미한 DB SELECT row-order 비교,
StateError/Exception 기대형 및 새 취소 재현의 nullable 타입 표기 오류를 수정한 실행과 중단된 실행도 보존했다. 예외형 교정은
아무 오류 허용이 아니라 정확한 `StateError('audit rollback')`를 요구했다. 제품은 수정하지 않았다.

## 31. Findings

**새 Critical 0 / High 0 / Medium 1 / Low 0.** E4-A01은 Phase A와 Phase B 진행을 차단한다.
역사적 monetary FAIL, P0 fixture drift, 최초 full 회귀 실패와 구분되는 실제 제품 결함이다.

### E4-A01 — 이전 취소 요청의 복구가 최신 설치 source를 덮어씀

**Severity: MEDIUM. Phase B blocker: YES.**

**Source:** `mobile/lib/src/app_state.dart:666–670`의 lock 밖 실패 복구,
`mobile/lib/src/segmented/workspace.dart:331–353`의 await 전 `unchanged` 계산과 await 뒤
무조건 source 복원/삭제가 원인이다. 특히 `:341–345`의 파일 변경이 `:347–353`의 B 검증보다
먼저 일어난다. `mobile/lib/src/segmented/store_frozen.dart:316–324`는 preparation 소유권을
SQL에서 재검사하지만 이미 바뀐 파일을 되돌리지 못한다.

**위반 계약:** §26의 일관된 handoff/recovery 및 §29의 durable Frozen B/legacy lineage
association. data-only recovery는 새 authority를 만들지 않더라도 이미 성공한 최신 handoff를
훼손해서는 안 된다. 과거 source를 읽은 것만으로 현재 파일 복원 권한이 성립하지 않는다.

**최소 조건:** 정상 G0 legacy installation, 같은 AppState/workspace/store의 두 overlapping
명시 E4 요청, 이전 요청의 legacy rename 전 취소, recovery의 async metadata read 지연이다.
새 coordinator, 악성 DB 조작, 다른 principal, production 활성화 또는 R1은 필요 없다.

**재현:** [`stale_recovery_test.dart`](benchmarks/t66e4-audit/stale_recovery_test.dart).
제품은 변경하지 않았다. 기존 virtual async `loadMetadata()`만 test subclass의 Completer로
한 번 지연한다. 기존 fault 경계에서 ordinary `SyncCancellation.cancel()`을 전달하며 실제
권한 검사에서 `ACQUISITION_CANCELLED`를 받는다. sleep으로 race 성공을 추정하지 않는다.

1. G0/F0/B0를 정상 설치하고 outcomeUnknown marker bytes를 저장한다.
2. 이전 요청 A가 F1/source preparation을 만든 뒤 B rename 직전 취소된다.
3. A의 lineage lock은 해제되지만 `finally` recovery는 F1과 `unchanged=true`를 읽은 뒤
   `loadMetadata()`에서 대기한다.
4. 같은 AppState의 최신 요청 B가 원 coordinator ticket을 새로 얻는다. B의 initial recovery는
   F1을 정리한다. synthetic backend를 변경한 G2/F2/B2 installation은 정상 반환한다.
   SQL은 F2 installed만 남고 source도 F2다. 이전 F0 association은 정당하게 교체됐다.
5. A recovery를 재개하면 stale `previous_source` F0를 source에 먼저 rename한다.
   이미 없어진 F1의 SQL cleanup은 실패한다. A의 `finally`는 cleanup 오류를 삼키며 원 취소를 유지한다.
6. B2/marker bytes, source 및 별도 SQLite rows를 다시 읽는다. store를 닫고 새 handle로
   열어도 SQL은 F2지만 workspace recovery와 Frozen-B 읽기는 실패한다.

**기대:** A의 늦은 복구가 B의 F2 source/B2/pins를 보존해야 한다. 현재 source가 바뀌었거나
예상 preparation이 없어졌으면 stale cleanup을 중단해야 한다. B의 성공은 재개방 후에도 유효해야 한다.

**실제:** 최종 취소 재현에서 source는 새 F2 `85842340-94db-426c-85c0-5dbc520f0065`에서
이미 삭제된 F0 `b1cd69dc-809e-4855-882b-c8506ada8c72`로 바뀌었다. SQL에는 F2 installed가
남고 foreign_key_check는 0이다. B2와 unknown marker bytes는 그대로다. read와 새 handle의
recovery는 모두 **FROZEN_BINDING_INVALID**다. 올바른 source 보존 assertion이 FAIL했다.
최초 StateError failure 주입 재현도 같은 결과였으며 실제 취소/fresh handle 재현으로 보강했다.

**독립 증거:** [`finding-e4-a01.json`](benchmarks/t66e4-audit/finding-e4-a01.json)에 두 실행의
source 전후, accepted/installed/frozen 실제 rows, errors, byte 보존 여부와 독립 graph 결과를
보존했다. 새 Python read-only 연결의 C1/SHA/typed closure/F(raw)/11 tables/Patricia 검사는
통과했다. 따라서 graph/pin 유실과 source association 훼손을 혼동하지 않는다. 에러 반환만을
근거로 판정하지 않고 최신 성공 이후의 실제 지속 상태로 FAIL을 판단했다.

**영향:** 최신 성공한 Frozen B의 읽기·복구가 차단되는 재현 가능한 가용성/lineage 연결 결함이다.
금융 rows, pending bytes, required object pins의 삭제나 stale 요청의 금융 UI 설치는 관찰되지 않았다.
이 범위를 넘어 severity를 높이지 않는다.

**최소 교정:** 기존 lineage owner로 initial/finally recovery와 handoff를 일관되게 직렬화하고
중첩 lock을 피한다. 모든 await 뒤, source rename/unlink 직전에 현재 source identity,
현재 B correspondence, 예상 prepared SQL ownership을 다시 확인한다. 최신 transition이나
사라진 preparation이면 **어떤 source 변경도 먼저 하지 말고** stale cleanup을 중단한다.
SQL final fence 이후 오류가 파일 변경을 자동 rollback한다고 가정해서는 안 된다.
새 auth system, financial formula, R1 또는 unrelated schema redesign은 필요 없다.

**필수 회귀:** 같은 deterministic A-cancel/B-success interleaving에서 source는 F2를 유지하고,
B2/unknown marker는 동일하며 fresh store + workspace recovery/read가 성공해야 한다.
이 보고서는 제품을 교정하지 않는다.

## 32. 제한·미검증 가정

같은 owning AppState/isolate와 private store/workspace의 publication serialization을 검토했고,
recovery가 그 경계 밖에 있는 실제 결함을 발견했다. 정상·crash 통과를 전체 concurrency 증명으로 확대하지 않는다.
arbitrary OS open-DB unlink/replacement, 의도적으로 모든 hash를 재계산한 local attacker,
unread bitrot 즉시 탐지, 실제 Android power loss를 보장하지 않는다. 외부 SQLite COMMIT은
지원 invalidation 경계로 직접 시험했다. 무관한 새 acceptance는 frozen proof를 불필요하게 깨지 않았다.

actual SQLITE_FULL/busy/ENOSPC 관련 기존 E1/E2/E3 시험과 quota 회귀를 실행한다. 새 E4 rollback은
fault injection이며 실제 파일시스템을 가득 채운 시험이라고 부르지 않는다. 새 SIGKILL은 실제 process death다.
현재 local 기본 한도는 object 64MiB, 합계 512MiB/100,000개, manifest 8MiB,
metadata 32MiB, staging 128개다. E4 full legacy export는 26,214,400B, page는 최대 256 rows,
source metadata는 16,384B, frozen은 최대 2 rows, installed는 current/previous 한 record다.
이 local 자원 정책을 server financial input limit으로 재해석하지 않는다. cold/full export의
O(N) 공간·시간과 기존 J projection의 O(H+J)는 허용된 명시 경계이며 일반 warm read는 전자를 반복하지 않는다.
resource limits·두 graph의 work counts는 확인했지만 모든 input/J 크기·Android peak RSS를 측정하지 않았다.
기존 10개 full-format 차이를 손대지 않았고 이번 diff의 새 formatting regression으로 분류하지 않았다.

## 33. Phase B readiness

**SAFE TO START T6.6F PHASE B: NO.** E4-A01의 최소 교정과 독립 targeted re-audit가 먼저 필요하다.

Phase B는 이번에 시작하지 않았다. 이번 기존 full regression 및 E4 요구 cross-boundary fixture는
독립 D1–D3c/E1–E4 integrated Phase B 완료 선언이 아니다. R1 proof와 일반-user activation은
별도 선행 조건이며 Phase A 판정만으로 열리지 않는다.

## 34. R1 gate

`adapters.dart:24`와 `workspace.dart:77`은 segmented Offline/recovery 진입을 거부한다.
FA16에서 성공한 E4 installation 뒤 실제 AppState.enterOfflineMode도 false였다.
R1 Large Restore/MW upload, 새 server protocol, recovery permit/flag 또는 일반-user source switch를
구현하지 않았다. 기존 active legacy B/J/finalizing은 기존 workflow로 보존하며 자동 conversion하지 않는다.

## 35. Production safety

새 RetentionSandbox/ObservationSandbox, 새 임시 SQLite/Flutter root, local/mock transport 및 synthetic
session만 사용했다. 실제 production DB/API/credential/service에 접근하지 않았다.
backend restart/migration/deployment, APK installation, segmented activation을 수행하지 않았다.
debug APK는 synthetic `https://audit.invalid` define으로 build만 했고 설치·배포·commit하지 않았다.
production SQLite user_version 4, Snapshot v7, OfflineBaseline v4, frozen B/J와 backend 금융 authority는 보존했다.

## 36. Audit-only commit·push

추가 파일은 이 보고서와 `docs/benchmarks/t66e4-audit/`뿐이다. 초기 source inventory의 제품 hash를
마지막에 다시 비교해 **71/71 동일**을 확인했다. stage된 경로가 이 allowlist에만 속하는지 검사한다. 사용자 파일·구현·원
보고서·벤치마크·DB·APK·원시 성공 로그를 stage하지 않는다. commit message는
`test(flutter): independently audit T6.6E4 pending and frozen lineage`다.

자기 참조 hash를 본문에 조작하지 않는다. 이 보고서를 최초 포함한 audit-only commit은 다음으로
식별하며 실제 commit hash와 push 후 HEAD/main/origin/main/actual remote/clean 상태는 최종 응답에 기록한다.

```bash
git log -1 --format=%H -- docs/t66e4-independent-audit.md
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --short
```

```text
T6.6F PHASE A / E4 INDEPENDENT AUDIT:
FAIL

AUDITED E4 IMPLEMENTATION COMMIT:
e386586194edbef1fc35f0ea1cf4145a2ae32685

AUDIT-ONLY COMMIT:
이 보고서를 최초 포함한 commit — §36 명령으로 식별

REPOSITORY STATE:
VERIFIED

COMPLETE E4 DIFF REVIEW:
COMPLETE

T6.6C §22:
PASS

T6.6C §29:
FAIL — E4-A01의 legacy/frozen association 훼손

T6.6C §31 ACTIVATION GATE:
PRESERVED

T6.6C §34 E4 SCOPE:
PRESERVED

E4-P0 SOURCE PRESERVATION:
PASS

E4-P0 MONETARY REGRESSION:
PASS

ORIGINAL HISTORICAL DIAGNOSTICS:
PRESERVED

T01 ORIGINAL APPSTATE TICKET:
PASS

T01 INSTALLATION AUTHORITY:
PASS

T01 SESSION GUARD:
PASS

T01 STALE INSTALLATION REJECTION:
FAIL — 설치 guard는 작동하지만 이전 cleanup의 최신 source 변경을 차단하지 못함

T01 PENDING RETIREMENT AUTHORITY:
PASS

T01 UNACKNOWLEDGED PENDING PRESERVATION:
PASS

CROSS-STORE CRASH CONSISTENCY:
FAIL — SIGKILL 시험은 PASS, 동시 recovery는 E4-A01

LEGACY MATERIALIZATION:
PASS

SEGMENTED / LEGACY AUTHORITY:
SEPARATED

SYNC_ROOT / V7 FINGERPRINT:
SEPARATED

SNAPSHOT V7 IDENTITY:
PRESERVED

OFFLINE BASELINE V4 LINEAGE:
VIOLATED — B 자체는 동일하며 frozen source 연결이 훼손됨

T02 DURABLE FROZEN PINS:
PASS

T02 FROZEN PIN RESTART RECOVERY:
PASS — SQL pins 보존; workspace 연결 복구는 E4-A01로 FAIL

T02 FROZEN RETENTION:
PASS

T02 LEGACY LINEAGE ASSOCIATION:
FAIL

T02 PREMATURE UNPIN REJECTION:
PASS

T02 SHARED OBJECT RETENTION:
PASS

T03 PROVENANCE REUSE:
PASS

T03 PROVENANCE INVALIDATION:
PASS

T03 FULL VERIFICATION EQUIVALENCE:
PASS

T03 REPEATED FROZEN-B COST:
PASS

T03 INDEPENDENT SQL/OBJECT COUNTERS:
PASS

REPEATED READ SQL OPERATIONS:
storage-only 64 / 전체 B+J adapter 85 — 두 graph 규모 동일

REPEATED READ BYTES:
9,451 object-body bytes — metadata/J 및 물리 I/O 제외

UNNECESSARY FULL VERIFICATION:
0 — unchanged warm read

UNNECESSARY PIN WRITES:
0 — 측정된 read phases

GRAPH-SIZE SCALING:
PASS — 146 / 2,177 required objects의 bounded 비교

GENERATION-PINNED READS:
PASS

MIXED-GENERATION READ REJECTION:
PASS

RAW MONETARY STRINGS:
PRESERVED

UNICODE VALUES:
PRESERVED

BACKEND FINANCIAL AUTHORITY:
PRESERVED

FROZEN B/J:
REGRESSED — source association; B/J bytes는 보존

IMPLICIT B/J ACKNOWLEDGMENT:
NONE

AUTOMATIC B/J REBASE:
NONE

NEW INDEPENDENT AUDIT CASES:
44 PASS
1 FAIL
0 INCONCLUSIVE

EXISTING E4 TESTS:
163 PASS
0 FAIL

E4 AUTHORITY/RACE:
51 PASS
0 FAIL

E4 PROCESS CRASH:
17 PASS
0 FAIL

E1 REGRESSION:
PASS

E2 REGRESSION:
PASS

E2-A01:
PRESERVED

E3 REGRESSION:
PASS

E3 I25 COST:
PRESERVED

FULL FLUTTER TESTS:
1,440 PASS
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
PASS

RUFF:
PASS

COMPILEALL:
PASS

GIT DIFF CHECK:
PASS

R1 LARGE RESTORE:
DEFERRED

R1 GENERAL-USER ACTIVATION GATE:
CLOSED

GENERAL-USER SEGMENTED OFFLINE:
NOT ACTIVATED

DEFAULT FLUTTER STARTUP:
UNCHANGED

NORMAL FINANCIAL READ/WRITE:
UNCHANGED

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
1

NEW LOW:
0

UNRESOLVED E4 BLOCKERS:
1 — E4-A01

PHASE A VERDICT:
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
FAIL — T6.6F PHASE A / E4 CORRECTION REQUIRED

NEXT ACTION:
E4-A01의 recovery 직렬화와 변경 직전 현재 source 재검사를 최소 교정한 뒤 독립 targeted re-audit를 수행한다.
```

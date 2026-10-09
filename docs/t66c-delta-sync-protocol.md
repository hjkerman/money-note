# T6.6C — Segmented authoritative delta/revision sync 규범 명세

## 1. 상태·범위·규범 용어

**T6.6C PROTOCOL DESIGN COMPLETE — READY FOR INDEPENDENT DESIGN AUDIT**

이 문서는 승인된 [T6.6B D+C 설계](t66b-hot-cold-design.md)를 구체화한 **PROPOSED CONTRACT**다. 새 endpoint·migration·storage·validator·압축은 구현하거나 활성화하지 않았다. 독립 T6.6C 설계 감사와 이후 구현 승인이 필요하다. 사용자 제공 T6.6B 독립 판정은 APPROVE, 설계 차단 모순 0, 제품 결정 0이다. 해당 감사 원문을 새로 수행했다고 주장하지 않는다.

`MUST`는 필수, `MUST NOT`은 금지, `SHOULD`는 예외 사유를 기록해야 하는 권고다. 각 절의 새 동작은 별도 표시가 없어도 PROPOSED다. `CURRENT IMPLEMENTATION`은 현재 소스, `IMPLEMENTATION PROOF REQUIRED`는 아직 검증하지 않은 구현 gate, `OPTIONAL FUTURE OPTIMIZATION`은 v1에 필요하지 않은 개선이다.

시작 branch `main`, HEAD/main/origin/main/실제 remote main은 `29af67ca7704ebca2e353275b599779966be0f2c`, working tree clean을 확인했다. 금융 공식·현재 API·Snapshot v7·OfflineBaseline v4·B-2 admission·OfflineProjection·journal/pending format은 변경하지 않는다. 신규 설계는 기존 `state_fingerprint` 의미를 재정의하지 않는다.

## 2. CURRENT 계약·소스와 binding 제약

규범 원본은 [architecture.md](architecture.md)의 신뢰 경계, [domain-model.md](domain-model.md), [offline-mode.md](offline-mode.md), [security.md](security.md), [runbook.md](runbook.md)다. 문서의 역사적 단계 기록과 사용자 제공 최신 감사 판정을 구분한다.

| 실제 소스 | 확인한 계약 |
| --- | --- |
| [authoritative_state.py](../backend/app/services/authoritative_state.py): `_construct`, `_prepare`, `_terminal_guard` | 같은 read view·평가 문맥, 원 credential, 완전 응답 준비와 terminal freshness, bounded retry |
| [snapshot.py](../backend/app/services/snapshot.py): `_export_snapshot`, `_build_manifest`, `snapshot_state_fingerprint`, `restore_snapshot` | 11개 전체 table, flat canonical SHA, 정책 호환, mandatory backup·rollback |
| [db.py](../backend/app/db.py): `SCHEMA`, `session`, `borrowed_or_new_session` | 33개 row revision triggers, 같은 connection transaction, FK ON |
| [db_migrations.py](../backend/app/db_migrations.py): `_validate_revision_triggers`, `_validate_current_schema` | 현재 DB checkpoint 4, 예상 trigger 본문·추가 authoritative trigger 엄격 검사, migrated N4 index |
| [responses.py](../backend/app/routers/responses.py): `financial_response` | 필수 금융 response bytes 준비가 commit 이전, socket 유실은 ambiguous |
| [authoritative_schemas.py](../backend/app/authoritative_schemas.py): `AuthoritativeProjections` | 12개 필수 typed projections |
| [authoritative_bundle.dart](../mobile/lib/src/authoritative_bundle.dart), [authoritative_snapshot_validation.dart](../mobile/lib/src/authoritative_snapshot_validation.dart) | strict raw token·Unicode·schema·hash·raw 구조·N4; Category C 재계산 없음 |
| [coherent_refresh_coordinator.dart](../mobile/lib/src/coherent_refresh_coordinator.dart), [app_state.dart](../mobile/lib/src/app_state.dart) | ticket/auth/lineage/mode, 같은 candidate/envelope, durable publish 뒤 pending 정리·전체 설치 |
| [offline_store.dart](../mobile/lib/src/offline/offline_store.dart), [offline_data.dart](../mobile/lib/src/offline/offline_data.dart) | full v4 baseline, 전체 lineage hash, 원자 temp/readback/guarded rename, frozen B/J·artifact |
| [offline_reconciliation.py](../backend/app/services/offline_reconciliation.py): `apply_mobile_wins` | 검증한 B 복원 + ordered J를 단일 transaction에 적용, receipt/status·artifacts 유지 |

Backend는 Summary·judgment·discount·grouping/allocation·month-close·archived actual·recurring/fixed 계산의 유일한 authority다. 모바일은 A: transport/표현/authority/generation/publication, B: raw 구조/identity/복구를 검증하고 C의 금융 엔진을 복제해서는 안 된다(MUST NOT). Hash는 인증·금융 계산 증명이 아니다.

T6.6B 감사의 12개 binding 제약을 채택한다: D+C, 압축의 CPU 한계, flat SHA 비합성, revision의 row locator 부재, 역사 수정, cascade capture, 전역 제약, frozen B/J, GET≠POST receipt, durability/index/tracking proof, 큰 복구 상한, 30-backup 의미 보존이다.

## 3. 참여자와 책임

| 참여자 | CURRENT / 신규 | MUST 책임 |
| --- | --- | --- |
| authoritative SQLite | 존재 | 금융 사실·transaction·기존 제약 |
| capture/finalizer | 신규 | 모든 raw write를 같은 transaction에 기록하고 root/index/aggregate를 commit 전에 확정 |
| immutable object catalog | 신규 | exact bytes와 content identity, reference graph·lease pin |
| coherent observation producer | B-1 원칙 재사용, 새 producer 필요 | 같은 R/context의 target·hot·control, 원 credential terminal guard |
| object transfer API | 신규 | authenticated observation에 reachable한 객체만 byte-exact 전송 |
| mobile sync coordinator | 기존 guards 재사용, 새 consumer 필요 | base identity·tree diff·cancel·mode·generation, acquisition 자체는 nonpublishing |
| validated object store | 신규 | immutable bytes·validator provenance·완전성·hash-on-read |
| global structural index | 신규 | 전역 facts와 reverse closure를 raw state에 결합 |
| generation publisher | 새 physical adapter 필요 | complete target의 durable atomic switch와 recoverability |
| Offline/pending/reconciliation | 존재, 명시 adapter 필요 | frozen B/J·receipt 독립성·finalization·retention |

## 4. Version과 공통 타입

새 namespace는 `/api/sync/v1/`다. 현재 `/api/authoritative-state` bundle_version=1과 독립인 **sync protocol 1**이다. 기존 API에 새 envelope를 반환해서는 안 된다(MUST NOT).

이 명세의 JSON record는 명시된 필드를 모두 요구하고 unknown field를 거부한다. Optional은 별도 명시한 경우만 허용한다. Nullable field는 생략과 다르다. JSON key 중복·잘못된 UTF-8/Unicode·nonfinite 숫자·원화 손실을 거부한다.

| 타입 | 정확한 의미 |
| --- | --- |
| `UUID` | 소문자 canonical UUIDv4 문자열. 서버/dataset/epoch/observation/request/upload IDs |
| `U64` | `0` 또는 `[1-9][0-9]*`인 decimal **문자열**, 0..2^63−1. R/count/bytes/offset. JSON Number로 변환하지 않음 |
| `Hash` | 소문자 SHA-256 hex 64자. 예제의 `<h:...>`는 명시적인 상징 placeholder이며 실제 wire 값이 아님 |
| `Time` | UTC `YYYY-MM-DDTHH:mm:ssZ`, 유효 달력 날짜·시각 |
| `NS` | `{server_id:UUID,dataset_id:UUID,epoch:UUID}` |
| `Ref` | `{hash:Hash,bytes:U64}`. bytes는 decoded canonical object 길이, HTTP 압축/base64 길이 아님 |
| `Key` | integer PK이면 `["i","signed decimal int64"]`, TEXT PK이면 `["t",String]`. `-0` 금지; TEXT는 valid Unicode, normalization 없음 |
| `Versions` | `{sync:1,canon:1,structural:1,raw_schema:Hash,snapshot:7,recurring_ownership:1,projection_schema:Hash,policy_registry:Hash}` |
| `Context` | `{evaluation_date:"YYYY-MM-DD",timezone_offset_minutes:integer,financial_engine:Hash}`. offset −1439..1439; 서버가 평가에 실제 사용한 값 |
| `ReconciliationId` | 기존 16..128자 `[A-Za-z0-9._:-]+`. 신규 upload UUID와 별개이며 기존 retry identity를 UUID로 강제 변환하지 않음 |

`raw_schema`는 11개 raw table/columns/types/domains/order/필수 저장 제약의 versioned descriptor hash다. `projection_schema`는 현재 12 typed contracts의 descriptor hash다. `structural=1`은 §10의 검사 catalog를 식별한다. `policy_registry`는 해석 호환 identity이지 금융 할인 재검증 허가가 아니다. `financial_engine`은 코드·설정 해석 release identity이며 raw DB revision과 별도다. 지원 descriptor는 client build에 포함된 explicit allow-list/검증된 호환 규칙으로 확인한다. 모르는 version을 best-effort parse해서는 안 된다(MUST NOT).

Descriptor/engine hashes는 배포 build에 포함된 **immutable release artifact의 SHA-256**이며 runtime DB 전체를 hash하여 만드는 값이 아니다. Raw descriptor는 실제 columns/PK/type-domain/제외 settings/구조 catalog version, projection descriptor는 12개 root의 재귀 required shapes/domain/공유 raw-field transforms를 포함해야 한다. Artifact exact bytes·hash와 호환 allow-list를 함께 review/배포한다. 새 semantics를 old hash로 광고하는 것은 contract 위반이다. 이 단계는 실제 descriptor hash를 발급하거나 registry compatibility가 완전히 해결됐다고 주장하지 않는다.

## 5. Dataset epoch·principal과 rollback fence

`sync_identity`라는 **향후 metadata table**에 server_id/dataset_id/epoch를 저장한다. Snapshot 11개 table에는 넣지 않는다. CSPRNG UUIDv4를 사용하고 ID를 시간·사용자 번호에서 유도해서는 안 된다(MUST NOT).

본 v1은 복잡한 외부 monotonic anchor 대신 보수적인 fence를 선택한다.

1. Server_id/dataset_id는 신규 DB 생성 시 발급하여 지속한다. Dataset을 새로 reseed/provision하면 dataset_id도 새로 발급한다. HTTPS endpoint identity도 client namespace의 일부다.
2. **서버 cold startup마다**, 검증된 단일 publisher가 EXCLUSIVE bootstrap transaction에서 새 epoch를 발급하고 raw roots/index를 재구축한 뒤에만 sync capability를 활성화한다. 이전 epoch cache/observation은 새 관측으로 설치 불가다.
3. Snapshot restore, 전체 reset/reseed, MW의 전체 B 교체는 같은 write transaction에서 epoch를 변경하고 전체 target roots를 재구축한다. 일반 card/cash/policy/month-close는 epoch를 변경하지 않는다.
4. Physical SQLite backup 복원/교체는 quiescent maintenance와 cold startup을 MUST 요구한다. 기존 epoch가 든 DB를 복원해도 startup의 새 epoch 때문에 R/ID 재사용을 신뢰하지 않는다. 실행 중 DB hot-swap은 지원하지 않는다.
5. Publisher는 동시에 하나여야 한다. 현재 Docker CMD는 단일 Uvicorn launch다. 향후 여러 worker가 있다면 bootstrap을 프로세스마다 실행하지 않도록 단일 publisher ownership을 먼저 입증해야 한다. 분산 consensus를 도입하지 않는다.

Epoch rotation은 같은 metadata transaction에 이전 epoch의 Available observation을 무효화하고 root pins를 release한다. Old object 회수는 bounded GC로 지연할 수 있다. Expiry 전이라는 이유로 새 dataset의 변화 이후 옛 lease download를 계속 허용하지 않는다. 이미 client에 완전 수신된 observation의 한계는 아래와 같다.

**비용 인정:** restart 후 O(N) bootstrap/full resync가 발생한다. 안정된 server epoch 안의 정상 refresh가 목표이며 restart까지 O(H+D)라고 주장하지 않는다. Cold epoch 재사용을 유지하려면 별도 rollback-resistant durable anchor가 필요하지만 이는 OPTIONAL FUTURE OPTIMIZATION이다.

Client durable namespace는 `(trusted HTTPS origin,server_id,dataset_id,epoch,principal_id,Versions)`다. 같은 숫자 user ID라도 다른 endpoint/dataset/epoch를 혼합하지 않는다. Object bytes의 NS는 dataset에 결합하고 observation/accepted generation은 principal에도 결합한다. 같은 장부를 읽는 다른 principal 사이의 자동 local cache 결합은 금지한다. 재인증 뒤 bytes는 fresh identity/호환성 확인 후 재사용할 수 있지만 이전 auth-generation ticket은 절대 재사용하지 않는다.

서버 reset/restart를 client가 아직 관측하지 못한 동안, 이미 완전 수신한 과거 coherent observation을 즉시 무효화하는 push 보장은 없다. 이는 terminal guard 후 일반 mutation도 마찬가지다. Client가 fresh capability/observation에서 새 epoch를 알면 이전 epoch를 새 authority로 설치하지 않는다. Old frozen B의 복구 증거·내용 보존은 별개이며 epoch mismatch로 삭제하지 않는다.

## 6. Revision·context·관측 identity

R은 같은 epoch에서 committed raw changes를 세는 현재 revision 값이다. 한 transaction에서 여러 row trigger가 증가시킬 수 있으며 R→T는 **T≥R**, 연속 +1을 요구하지 않는다. No-op UPDATE와 A→B→A도 R 증가로 구분한다. 새 epoch에서는 과거 R과 비교하지 않는다. 모든 공개 R은 SQLite committed 관측이며 uncommitted intermediate R은 광고하지 않는다.

Persistent raw state의 identity는 `(NS,R,raw_ref,index_ref,raw_schema,structural)`다. 금융 평가 context는 별도의 date/offset/engine/registry/projection schema다. Complete sync generation은 §9의 Target와 sync_root다. 같은 R의 날짜/offset/engine 변화는 hot/control을 재생성할 수 있지만 unchanged raw tree를 무효화하지 않는다.

Client는 같은 epoch에서 base보다 낮은 target R을 stale로 거부한다. 같은 R인데 raw/index root가 다르면 서버 identity 오류로 fail-closed한다. 같은 R의 hot/context 변경은 허용한다. 서로 다른 RefreshTicket과 mutation lineage는 R 비교보다 먼저 설치 권한을 제한한다.

Missed revisions는 intermediate event 재생 대신 accepted base tree와 complete target tree를 비교하여 전이한다. 서버 log retention이 끝나도 두 tree와 client accepted indexes가 완전하면 tree diff로 진행 가능하다. Server가 client base root를 보관하지 않는다고 그 base를 새 authority로 승인하는 것은 아니다. Base는 client의 durable validated provenance로 검증하며 서버는 read-only 취득을 최적화하는 힌트로만 쓴다.

## 7. Canonical object bytes와 hash

Object는 `C1` canonical JSON의 UTF-8 bytes다. Hash는 `SHA256(ASCII("money-note.sync.v1/") || ASCII(kind) || 0x00 || object_bytes)`다. kind도 body의 필수 필드이며 endpoint Ref와 일치해야 한다. HTTP Content-Encoding을 적용하더라도 해제 후 원 bytes를 그대로 유지해야 한다.

C1 규칙:

- UTF-8 BOM·공백·final newline 없음. Map keys는 Unicode scalar 순서(동등한 valid UTF-8 byte 순서)로 정렬하고 `,`/`:`만 delimiter로 사용한다. Array 순서는 의미를 가진다.
- String은 valid Unicode scalar sequence다. U+0022는 backslash+quote, U+005C는 두 backslash로 쓴다. Control U+0008/000C/000A/000D/0009는 각각 short escape `\b`/`\f`/`\n`/`\r`/`\t`, 나머지 U+0000..001F는 소문자 `\u00xx`를 사용하고 그 밖은 원 UTF-8로 쓴다. Slash/한글/emoji를 불필요하게 escape하지 않는다. Normalize/trim/case-fold/replace는 MUST NOT이다.
- Integer는 부호 있는 최소 decimal 표기다. Metadata 큰 정수는 U64 string, raw row는 기존 type/domain과 safe-integer admission 범위를 보존하며 signed-int64는 표현의 외곽 상한일 뿐이다. Money는 ±(2^53−1)의 정확한 정수 의미를 MUST 유지한다. 새 표현이 기존 B-2 raw ID/정수 허용 범위를 넓히지 않는다.
- 지원 historical REAL의 integral money는 기존 Python Snapshot canonical encoder처럼 `1000.0`/`-0.0`을 유지한다. Float를 int로 합치지 않는다. v1의 supported numeric raw/projection fields는 정수 또는 이러한 integral REAL이다. Policy rate/parameters의 문자열은 그대로 보존한다. 새 fractional non-money numeric schema는 명시적 canonical/version 검토 없이 추가하지 않는다.
- Bool/null은 `true`/`false`/`null`. 숫자 lexical preflight를 JSON decode 이전에 수행한다. `-1e-400` 같은 금액을 decode한 0으로 승인하지 않는다.

Hash 검증은 **받은 canonical bytes**에 한다. JSON 재직렬화로 invalid token을 숨기지 않는다. C1 formatter의 cross-language byte parity는 구현 gate이며 supported legacy scalar와 [C1 vectors](specimens/t66c-canonical-vectors.json)로 입증해야 한다. 특히 Dart String의 기본 UTF-16 key 정렬이 scalar/UTF-8 순서와 같다고 가정하지 않는다(V05). 현행 B-2 helper를 변경하지 않으며 새 consumer가 올바른 comparator를 사용해야 한다. 기존 money/Unicode 계약을 바꾸는 새 normalization은 없다.

## 8. Partitioning·Snapshot B+tree

권고는 **PK-ordered persistent B+tree**, leaf 최대 256행과 262,144 canonical bytes, internal fanout 최대 32다. 이 값은 v1의 구체적 profile이며 성능 최적값이라는 실측 주장은 아니다. Month partition은 history query index로만 사용한다.

Integer Key는 수학적 signed-int64 순서, TEXT Key는 exact UTF-8 BINARY 순서다. 한 table 안에 Key tag를 섞지 않는다. Leaf rows는 strict ascending PK이며 `{key:Key,value:SnapshotRow}` 쌍이다. PK와 row의 실제 PK 필드는 MUST 일치한다. 모든 현재 raw fields를 보존한다.

| Object kind | 정확한 body 필드 |
| --- | --- |
| `snapshot-leaf` | `kind,ns,canon:1,raw_schema,table,height:0,count:U64,min:Key\|null,max:Key\|null,oversized:boolean,rows:[{key,value}]` |
| `snapshot-node` | `kind,ns,canon:1,raw_schema,table,height:integer,count:U64,min:Key,max:Key,children:[Child]` |
| `Child` | `ref:Ref,height:integer,count:U64,min:Key,max:Key` |

Empty table은 `snapshot-leaf` count="0", min/max=null, rows=[], oversized=false인 유일한 empty-root 표현이다. 그 밖의 leaf는 1행 이상이다. Empty child를 internal node에 넣지 않는다. Internal root는 2..32 children, non-root internal은 16..32 children이다. 모두 동일 child height, parent height=child+1, count=sum children, min=첫 child.min, max=마지막 child.max다. Height는 0..63이다. Child ranges는 strict disjoint ascending이다. Hash가 child 순서·range·count를 결합하며 실제 child body와 descriptor도 일치해야 한다.

Leaf가 한 row만으로 byte 상한을 넘으면 `oversized=true` singleton을 허용하고 §15의 bounded transfer chunks로 취득한다. 기존에 허용된 긴 string을 새로운 길이 제한으로 거부하지 않는다. 일반 leaf는 oversized=false이고 두 상한 모두 만족해야 한다. 극단적 key/row 길이는 별도 입력 비용이며 bounded H 가정에 숨기지 않는다.

Bootstrap은 sorted rows를 상한까지 순서대로 채우고 최대 fanout groups를 만든다. 마지막 non-root group이 16 미만이면 직전 group과 균등 재분배한다(홀수 잉여 child는 오른쪽). Update는 변경 PK 순으로 적용한다. Overflow leaf는 row 중간에서 나누고 양쪽이 byte 상한을 만족할 때까지 반복 분할한다. Internal overflow 33 children은 왼쪽 16/오른쪽 17로 분할한다. Empty leaf는 제거한다. Non-root internal underflow는 왼쪽 sibling에 16 초과 child가 있으면 마지막 child를 빌리고, 없으면 오른쪽에서 첫 child를 빌린다. 둘 다 불가하면 왼쪽 우선 merge하고 parent까지 반복한다. Unary root는 collapse하고 전체 삭제는 empty leaf로 바꾼다. 일반 삭제에서 **nonempty leaf**를 즉시 merge하지 않는 것을 v1 규칙으로 선택한다. Internal 최소 fanout은 유지하므로 depth는 O(log P)다. 정기 compaction은 새 representation root를 게시하는 별도 maintenance이며 정상 refresh에 섞지 않는다. 그러므로 tree shape는 mutation history에 의존할 수 있다. **같은 raw rows면 항상 같은 B+tree root라는 주장은 하지 않는다.**

PK는 바뀔 수 있다면 old Key DELETE + new Key INSERT다. 날짜/월 변경은 PK가 같아도 raw row와 history indexes를 바꾼다. Leaf 경계가 달라져도 row identity는 같다. Late archive insertion과 month-close copy/delete도 같은 규칙이다.

## 9. Raw root·control·hot·sync root

`raw-root` body는 `{kind,ns,canon:1,raw_schema,tables:[{name,root:ChildOrEmpty,count:U64}]}`다. Root descriptor의 min/max는 empty일 때만 null이다. Tables는 다음 **정확한 11개·순서**이며 omission/중복/extra를 거부한다:

`ledger_entries`, `monthly_panels`, `cash_flows`, `card_payment_batches`, `card_payment_batch_items`, `card_payment_events`, `card_payment_allocations`, `card_payment_deferrals`, `notification_candidate_registrations`, `app_settings`, `app_labels`.

각 table의 count는 root descriptor count와 같아야 하고 descriptor Ref/height/count/min/max는 실제 root body와 정확히 일치해야 한다. `ChildOrEmpty`는 §8 Child와 같은 필드이며 empty root에서만 height=0/count="0"/min=max=null이다. Table 이름/PK type/schema와 맞지 않는 root를 다른 table에 재사용하지 않는다.

`hot` body는 `{kind:"hot",ns,canon:1,projection_schema,context,state}`다. `state`는 현재 `AuthoritativeProjections`의 정확한 12개 required shape를 재사용한다: month_close_status, entries, panels, summary, card_payment_status, judgment, confirmed_planned_entries, cash_flows, settings, owner_discount_month, family_discount_month, transit_discount_profile. 서버가 계산한다. Raw duplicate fields·identity/type·context는 client가 검사하지만 grouping/할인/Summary를 재계산하지 않는다.

`control` body는 `{kind:"control",ns,canon:1,snapshot_schema:7,recurring_ownership_version:1,exported_at:Time,range:{scope:"all"},card_charge_policy:ExistingManifest,columns:{table:[sorted exact columns]},discount_policy_defaults:{owner,family}}`다. Owner/family는 enabled/disabled enum이다. columns에는 빈 table도 포함한다. Original B를 materialize할 때 이 metadata를 그대로 사용한다.

`Target` 필드는 모두 required다:

| 필드 | 타입·의미 |
| --- | --- |
| `ns`, `principal_id` | NS, 양수 signed-int64 principal |
| `versions`, `revision`, `context` | Versions, U64, Context |
| `raw_ref`, `index_ref`, `hot_ref`, `control_ref` | 각 typed object의 Ref |
| `sync_root` | 아래 view hash |

`sync_root = SHA256(ASCII("money-note.sync.v1/view") || 0x00 || C1(Target에서 sync_root만 제외))`다. NS/principal/R/versions/context와 모든 refs가 결합된다. Ordinary hash이지 signature가 아니다. 별도의 서버 auth/HTTPS가 origin을 보장한다.

동일 R/context/hot bytes이면 producer는 기존 immutable hot/control과 Target을 재사용 SHOULD 한다. 최초 해당 view 생성 시의 exported_at도 유지한다. **Freshness는 새 observation의 validated_at/terminal guard로 확인**하며 export timestamp를 매번 바꿀 필요는 없다. 같은 R에서 비금융 presentation이 바뀌면 hot_ref/sync_root가 달라질 수 있고 raw-unchanged 전이로 처리한다.

새 `(NS,R,Context,Versions,hot bytes)` view의 control.exported_at는 최초 해당 view 준비 시각이다. 다른 raw revision의 과거 export 시각을 무조건 물려주지 않는다. Same view를 다시 관측할 때만 이 metadata를 그대로 재사용한다. 초 단위 시각이 같아 같은 control bytes가 되는 것은 허용한다.

## 10. 전역 구조 facts catalog

`structural=1`의 원본은 현재 `validateAuthoritativeSnapshot`의 `_relationships`와 `_projectionIdentities`, `validateBundleProjectionStructure`, 실제 migrated DB constraint다. 구현은 검사 하나라도 누락한 채 version 1이라 부르지 MUST NOT 한다. 다음 raw catalog는 required다.

| Fact/검사 | namespace·키·값/조건 |
| --- | --- |
| PK | `pk/table/Key → row_hash`, 11개 table 전부. 같은 숫자 ID의 다른 table은 구별 |
| payment key | ledger의 non-null payment_key → owner PK, 전역 unique; 값/domain은 기존 계약 |
| source/epoch | source planned PK + confirmed_month + confirmed_at → expense child PK; 부분 epoch 금지, 활성 source는 정확히 한 actual; 종료 epoch와 현재 source를 혼동 금지 |
| actual FK | ledger source→ledger planned, panel fixed→cash, event→batch/cash, item→batch/entry, allocation→event; optional null은 기존 계약대로 |
| batch membership | `(batch_id,entry_payment_key)` unique, 원장 ID/key 일치, payment key의 batch owner와 item entry owner unique |
| allocation | `(event_id,payment_key)` unique, 실제 non-planned 원장 key 존재, batch owner 대응, nonnegative exact amount |
| raw event totals | event별 allocation sum/count, total_amount 대응, immediate 출금의 음수 amount 대응; financial remaining 계산 아님 |
| cash ownership | event→cash unique, fixed→cash unique, 두 owner set disjoint; fixed spent_on/confirmed epoch/flag/금액 부호 관계 |
| active batch | active 상태 count≤1 |
| N4 | non-null idempotency_key → event PK, **전 table UNIQUE, UTF-8 BINARY**. 빈 문자열 포함; null은 fact 없음 |
| deferral | entry_payment_key PK·기존 nullable original metadata/domain. 존재 FK를 새로 만들거나 금융 이월 eligibility를 재계산하지 않음 |
| registrations | registration_key PK·target domain. 삭제된 target가 남는 것을 허용하므로 임의 FK를 새로 만들지 않음 |
| settings/labels | key PK·필수 money settings·exact string, sensitive settings 제외·동일 raw setting view |
| row-local | 필수/nullable/type/finite domain/date/epoch/Unicode/정확한 원화; 현행 Snapshot compatibility |

Projected PK/source/key uniqueness, present raw source references, shared raw field 대응, policy descriptor/manifest compatibility, cheap same-entity alias equality는 hot 검증에 그대로 남는다. N1/N2/N3의 독립 canonical 금융 재계산은 포함하지 않는다.

## 11. Global index의 canonical identity·갱신

`index_ref`는 **완전한 raw facts F(data)**의 canonical index-root다. Server index를 다운로드하여 신뢰하는 것만으로 completeness가 성립하지 않는다. Client는 initial에 모든 raw rows에서 F를 생성하고, 전이 때 accepted F에 정확한 raw row diff를 적용하여 target index root와 반드시 비교해야 한다(MUST).

Fact Key/Value는 아래 고정 JSON arrays의 C1 bytes다. `Owner=[table,Key]`, `row_hash=H("row",C1({ns,raw_schema,table,key,value}))`다. Hash preimage의 value는 전체 SnapshotRow다. Derived integer sums/counts는 부호 있는 최소 decimal **문자열**로 기록하고 SQLite/Dart 고정 폭으로 중간합을 잘라내지 않는다. Leaf locator는 shape 변화로 전체 index를 흔들지 않도록 canonical facts에 넣지 않고 local lookup cache로 분리한다.

| Fact key | Fact value·정확한 생성 조건 |
| --- | --- |
| `["pk",table,Key]` | row_hash; 모든 row |
| `["unique",domain,components]` | Owner; 아래 unique domains에 해당하는 row만. 같은 key의 다른 Owner는 F 생성 자체가 실패 |
| `["ref",src_table,src_key,field]` | `[dst_table,dst_key]`; 아래 non-null raw 참조 각각 |
| `["reverse",dst_table,dst_key,src_table,src_key,field]` | source row_hash; 모든 ref의 정확한 역방향 하나 |
| `["allocation",event_key,payment_key,allocation_key]` | amount의 exact decimal 문자열; 모든 allocation |
| `["aggregate","event",event_key]` | `[allocation_count_string,allocation_sum_string]`; allocation 없는 event도 `["0","0"]` |
| `["aggregate","active_batch"]` | active batch count 문자열; 빈 table도 `"0"` |
| `["context","last_closed_month"]` | raw setting value 또는 null; setting absence를 임의 날짜로 보충하지 않음 |
| `["context_reverse","last_closed_month",table,Key]` | row_hash; source/epoch 관계가 있는 ledger row와 fixed panel 모두 |

Unique domain/`components`는 `ledger_payment_key/[payment_key]`, `recurring_child/[source_Key,confirmed_month,confirmed_at]`, `batch_pair/[batch_Key,payment_key]`, `batch_key/[payment_key]`, `batch_entry/[entry_Key]`, `allocation_pair/[event_Key,payment_key]`, `cash_owner/[cash_Key]`, `event_idempotency/[idempotency_key]`다. Ledger payment_key와 event idempotency는 non-null일 때만 생성하며 빈 문자열을 생략하지 않는다. Recurring child는 §10의 expense child, cash_owner는 모든 non-null event cash 및 fixed-linked cash다. 다른 table의 같은 숫자 ID는 Owner에서 구별한다. UNIQUE 값은 BINARY exact scalar 비교이며 C1 배열이 delimiter 충돌을 방지한다.

Ref catalog는 ledger.source_planned_entry_id→ledger.id, panel.confirmed_cash_flow_id→cash.id, event.batch_id→batch.id, event.cash_flow_id→cash.id, item.batch_id→batch.id, item.entry_id→ledger.id, allocation.payment_event_id→event.id다. Allocation.entry_payment_key→`["unique","ledger_payment_key",[key]]`도 logical ref/reverse를 만든다(목적 domain은 `@ledger_payment_key`, 목적 Key는 `["t",key]`). Deferral의 entry_payment_key는 현재 mobile 계약이 존재 FK를 요구하지 않으므로 새 mandatory ref를 만들지 않는다. Registration도 target FK를 만들지 않는다. Settings/labels PK만의 facts와 row-local domains는 §10대로다.

Catalog 밖의 자의적 fact를 추가하지 않는다. 각 row의 PK/unique/ref/reverse/allocation facts와 위 세 aggregate/context fact families의 **합집합만** F다. Actor/입력 순서에 의존한 owner 선택은 금지다. Ref 목적 PK·kind/raw 조건, recurring epoch·last_closed_month 조건, fixed period·flow 조건, allocation batch owner·sum/event/cash 관계, 필수 settings presence를 §10/현행 structural predicates로 검사한다. 이 predicates는 금융 projection 계산이 아니다. Context fact가 바뀌면 context_reverse 전체를 영향집합 E로 처리하며 이 변경은 O(E), 최악 O(N)일 수 있다.

Fact key digest는 `SHA256(ASCII("money-note.sync.v1/fact-key") || 0x00 || key_bytes)`다. Index는 **canonical compressed binary Patricia trie**를 선택한다.

- `index-empty`: `{kind,ns,canon:1,structural:1,raw_schema,count:"0"}`.
- `index-leaf`: `{kind,ns,canon:1,structural:1,raw_schema,digest:Hash,count:U64,facts:[{key,value}]}`. 같은 digest의 모든 exact key를 C1 byte 순서로 정렬한다. Hash collision이라도 서로 다른 key를 합치지 않는다.
- `index-node`: `{kind,ns,canon:1,structural:1,raw_schema,prefix:String,left:Ref,right:Ref,count:U64}`. prefix는 자식 digest들의 maximal common binary prefix(0..255 bits)이고 다음 bit 0/1이 left/right다. 두 child는 nonempty, count는 합계다. Prefix가 증가하지 않는 path와 unary node를 금지한다.
- `index-root`: `{kind,ns,canon:1,structural:1,raw_schema,facts:Ref,count:U64}`.

같은 facts 집합은 insertion history와 무관하게 같은 Patricia representation/root를 만든다. 이 선택은 B+tree shape가 server와 client의 skipped-revision 적용 순서에 따라 달라질 문제를 피한다. Full crypto digest의 collision bucket도 exact keys로 처리한다. Depth는 최대 256이고 정상 collision-free lookup/update는 그 상한 안에서 수행한다. Crypto collision resistance 가정을 넘어선 adversarial giant bucket에 일정 성능을 약속하지 않는다.

Digest bit order는 SHA-256 bytes의 MSB-first다. Prefix는 `[01]*` literal string이다. 모든 index-leaf facts의 key digest가 leaf.digest와 같아야 하며 count는 facts 개수다. 모든 node/root count는 child들의 facts count와 일치한다. Client가 F로 canonical trie를 독립 생성한 bytes/hash/count를 비교하므로 받은 node의 주장만으로 canonical prefix/전체 fact coverage를 승인하지 않는다.

전이 알고리즘: changed/deleted raw rows의 **old facts를 전부 제거한 뒤** new facts를 exact key 순으로 넣고, 변경 key의 incoming/outgoing reverse edges, old/new source epochs, shared cash owners, affected event sums/counts/active batch count를 검사한다. 전체 결과에는 각 raw row가 정확히 한 PK fact를 가져야 한다. Unchanged rows의 accepted facts는 재사용한다. 같은 UNIQUE key의 다른 owner를 overwrite하지 말고 reject한다. Incremental raw sums는 넓은 exact intermediate를 사용하고 계약상 저장/노출 범위에서 검사한다.

이 귀납은 complete accepted base + 완전한 old/new diff + complete reverse closure가 전제다. Index receipt는 `(NS,raw_ref,index_ref,structural,validator_build)`에 결합한다. Index 손상/불일치/지원 검사 변경이면 전체 재검증이지 silent regeneration으로 정상 성공 처리하는 것이 아니다.

## 12. Transactional capture·기존 trigger 통합

권고는 **audited DB capture + explicit transaction finalizer의 hybrid**다. Writer instrumentation만 사용하면 direct SQL/cascade 누락을 탐지하기 어렵고, trigger만으로 금융 projection·canonical tree를 구현하는 것은 부적절하다.

향후 migration은 기존 33개 `revision_<table>_<event>` trigger를 같은 이름의 audited body로 교체한다. 기존 revision 증가 의미는 보존하고 capture를 추가한다. 현재 admission에 그냥 새 trigger를 설치해서는 안 된다(MUST NOT). `SCHEMA`, expected trigger token contract, migration rollback/startup, B-1 schema identity 검사를 **같은 릴리스에서** 갱신해야 한다. 현재 checkpoint 4를 몰래 재해석하지 않고 새 checkpoint를 배정한다. Snapshot v7 raw 11개는 변하지 않는다. 구 server binary는 새 DB checkpoint에 code-only rollback할 수 있다고 가정하지 않는다.

Legacy Snapshot dry-run도 미래 migrated schema의 capture context/finalizer를 갖춘 isolated transaction으로 실행해야 한다. Runtime restore/bootstrap는 audited bulk wrapper와 epoch rotation을 사용한다. 새 triggers 때문에 v7 inserts가 실패한다고 capture/FK를 비활성화하거나 구 schema-only dry-run으로 회피하지 않는다. Snapshot v7의 wire schema와 금융 내용은 그대로이며 내부 schema admission/restore transaction adapter만 미래 구현 대상이다.

향후 metadata는 `sync_identity`, `sync_tx_context`, `sync_changes`, `sync_tx_fence`, `sync_commits`, `sync_current`, `sync_objects`, `sync_observations`다. 제품 금융 table·auth/reconciliation receipts와 구분하며 Snapshot export 대상이 아니다.

| record | 필수 의미 |
| --- | --- |
| tx context | BEGIN IMMEDIATE/EXCLUSIVE 안에서 발급한 UUID tx_id, 단일 active writer, base epoch/R |
| change | tx_id, event sequence, 해당 row trigger 후 R, table, INSERT/UPDATE/DELETE, old/new Key, old/new raw values 또는 excluded-setting marker |
| fence | 해당 tx_id가 finalized commit record를 갖지 않으면 COMMIT 불가 |
| commit | tx_id, base/target epoch/R, raw/index roots, 완료 상태·change 범위 |
| current | 마지막 complete raw/index root와 정확히 대응하는 epoch/R |

Capture trigger는 context 없으면 ABORT, revision 증가, old/new values와 key 기록, fence 생성을 수행한다. `sync_tx_fence(tx_id,finalized_tx_id)`는 두 ID NOT NULL·일치 CHECK와 `sync_commits(tx_id)`에 대한 **DEFERRABLE INITIALLY DEFERRED FK**를 사용한다. Source write가 발생한 transaction은 finalize record 없이는 commit할 수 없게 한다. Finalizer는 context를 같은 transaction에서 삭제하고, 후속 raw write는 context 부재로 ABORT한다. 새 transaction은 새 UUID context를 만들며 과거 commit/context를 재사용해서는 안 된다(MUST NOT). Read-only transaction은 context가 필요 없다. 단순 “코드가 잊지 않을 것”에 의존하지 않는다. FK ON은 connect/startup의 필수 조건이며 commit record를 임의 작성하거나 FK를 끄는 침해 backend는 threat model 밖이다. Direct maintenance는 audited transaction wrapper를 사용하거나 quiescent epoch bootstrap을 수행한다.

Foreign-key CASCADE/SET NULL로 바뀐 row도 각각 같은 audited trigger에서 capture한다. SQLite FK actions·trigger 실행 실제 parity는 migrated DB proof다. Rolled-back rows/capture/R/fence/root 모두 함께 rollback한다. Sensitive setting 값은 capture payload에도 복사해서는 안 된다(MUST NOT). 포함↔제외 key 이동은 허용된 쪽 raw values만 보존하고 revision coverage marker는 남긴다.

## 13. 실제 writer coverage와 root finalizer

| 현재 write 경로 | capture/finalizer 의무 |
| --- | --- |
| repositories entries/panels/cash_flows/settings/labels | 모든 create/update/delete, old/new PK, discounts의 raw 입력/설정 포함 |
| services card_payments | events/cash/allocations/items/deferrals와 취소·이월·late archive, FK actions |
| services month | archive 새 ID INSERT + current DELETE + registration rewrite + source/fixed reset + income + batch 교체 |
| recurring/fixed confirm/cancel | source+epoch+child, panel+cash ownership의 전체 변경 |
| offline_reconciliation.apply_mobile_wins | 전체 B replacement + J replay + receipt를 같은 transaction; epoch 변경·full roots |
| snapshot.restore/reset/bulk completion | mandatory pre_restore 뒤 원자 변경, 전체 교체는 epoch rotation; bulk delete captures |
| migration/bootstrap | quiescent EXCLUSIVE, 기존 admission 먼저, 새 index/root·epoch 완성 전 sync 미노출 |
| direct SQL/CLI/maintenance | context/fence/finalizer 필수, 누락 시 ABORT; 비인가 DB hot-swap 미지원 |

본 v1은 **synchronous pre-commit root/index maintenance**를 선택한다. Financial transaction 안에서 모든 mutation과 기존 필수 financial_response 준비를 마친 뒤 capture를 coalesce하고 changed leaves/index paths/maintained aggregates를 갱신하고 전체 required structural closure를 검증한다. 이어 `sync_current`와 finalized commit을 기록하고 context를 삭제한 뒤 commit한다. Finalize 또는 response 준비 실패는 원 command와 metadata를 모두 rollback한다. Finalizer 뒤 presenter의 숨은 write도 허용하지 않는다. 이후 socket 유실은 여전히 ambiguous POST다.

Capture first-old/final-new 비교로 중간 변경을 coalesce할 수 있으나 삭제·insert·identity 이동·FK 영향과 R coverage를 잃어서는 안 된다(MUST NOT). New objects bytes는 동일 SQLite metadata transaction에 저장하여 root가 없는 파일이나 아직 durable하지 않은 파일을 참조하지 않게 한다. Objects는 immutable이고 충돌한 동일 hash의 다른 bytes는 fatal integrity 오류다.

Coalesce **이전** capture의 revision marker는 transaction base R+1부터 target R까지 중복·누락 없는 정확한 범위여야 한다. Excluded sensitive setting도 값 없는 marker를 남긴다. Finalizer는 marker coverage와 audited trigger identity를 검사하고 하나라도 누락되면 finalized record를 만들지 않는다. 이는 한 금융 transaction 내부의 기존 row-trigger 증가 검증이지 client에 R→R+1을 강요하는 규칙이 아니다. Old/new payload·cascade closure 자체의 정확성은 migrated capture와 full-rebuild property oracle로 입증해야 한다.

Post-commit은 lease expiry/GC/metric 같은 비권위 작업만 한다. Async root builder와 “뒤처진 root를 최신 R이라고 광고”하는 설계는 v1에서 기각한다. Cold startup/full reset의 bootstrap O(N)은 예외다. Dirty row 발견을 위해 매 refresh table scan을 하면 성능 gate 실패다.

## 14. Hot 평가·maintained aggregates

Producer는 현재 B-1처럼 한 read view에서 R/raw/index와 fixed Context를 고정하고 backend financial presenters를 사용한다. Same R/context/engine/registry/projection-schema에 대해 검증된 immutable hot cache를 재사용할 수 있다. Date-only change는 hot/control을 갱신하며 cold trees는 재사용한다.

| hot section | backend 입력·무효화 |
| --- | --- |
| entries/confirmed | current/planned 및 source+epoch로 찾는 실제 child, policy/allocations; create/edit/delete/confirm/close |
| panels | fixed와 미삭제 frozen/claim/family, fixed-linked cash·family policy; panel/confirm/settlement |
| Summary | current/planned/panels·active payment·cash prefix aggregate/settings; 관련 write·cutoff/date |
| payment | active batch/items + referenced ledger/event/allocation/deferral·policy; 결제/취소/이월/마감 |
| judgment | Summary·월 cash·최근 closed-month counts/settings·코드 CATEGORY_LABELS; app_labels와 다름 |
| cash | 직전월 시작~평가월 말 source rows; date/flow write |
| month_close_status | source/fixed/settings·서버 date/offset; financial eligibility는 backend |
| settings/owner/family/transit | 비민감 settings·월 registry와 해당 source; 정책/context 변경 |

T6.6D MUST 제공할 bounded-history 입력은 cash exact prefix/date index, per-month closed counts, source+epoch lookup, payment ownership/reverse indexes, incremental policy horizon metadata다. History cash를 REAL SUM/int64 overflow로 대체하지 않는다. 현행 full ownership validators/전체 Snapshot construction이 남은 경로는 새 protocol 노출만으로 history-independent라고 인증할 수 없다. H 자체는 무상한이다.

## 15. 새 API와 메시지 schema

이 절의 endpoint는 모두 **NEW DESIGN**이다. 모든 호출은 기존 trusted transport와 본체 auth를 사용하고 Cache-Control no-store다. Shared/PIN session은 권한이 없다. Sync POST는 금융 command가 아니라 read-only observation/transfer metadata 작업이며 online-write pending을 생성하지 않는다. 금융 POST retry 허가로 확장하지 않는다.

### 15.1 Capability

`GET /api/sync/v1/capabilities` → 200 `{protocol:1,ns:NS,principal_id,versions:Versions,features:{tree_diff:true,chunked_objects:true,large_restore:1},limits:{inline_bytes:1048576,batch_items:64,batch_decoded_bytes:1048576,chunk_bytes:1048576,lease_seconds:900,observations_per_principal:4,restore_bytes:U64,upload_seconds:86400}}`.

Limits는 해당 서버의 실제 허용 budget이다. 여기서 fixed 수치는 v1 상한이며 더 작은 실제 limit은 명시 반환한다. Restore budget은 별도 배포 resource proof로 설정한다. Client는 capability를 auth-generation 바뀔 때 재확인한다. Namespace/Versions 변경을 설치 권한으로 간주하지 않고 full/upgrade 정책을 따른다. 404/명시 미지원이면 protocol 선택 **전에** 기존 full consumer를 유지할 수 있다. Invalid segmented response 후 implicit legacy fallback은 금지다.

### 15.2 Observation 생성

`POST /api/sync/v1/observations` body `{protocol:1,request_id:UUID,base:Base|null,inline_bytes:integer}`. Inline_bytes는 0..capability limit. `Base={ns,principal_id,versions,revision,raw_ref,index_ref,hot_ref,control_ref,context,sync_root}`로 Target와 같은 shape다. Client의 accepted Target exact bytes를 사용한다.

201(신규)/200(동일 request retry) body:

`{protocol:1,request_id:UUID,status:"available",observation_id:UUID,validated_at:Time,expires_at:Time,base_sync_root:Hash|null,change_kind:"initial"|"unchanged"|"context"|"raw",target:Target,inline_objects:[ObjectChunk]}`.

Base null이면 initial. Raw/index refs·R이 달라지면 raw, 그렇지 않고 Target가 달라지면 context, Target가 같으면 unchanged다. 서버가 검증하지 못한 client base를 “accepted”라고 서명하지 않는다. Client는 echo한 base_sync_root와 자기 base의 exact equality를 검증한다. Same request_id는 original credential identity와 request C1 digest에 결합한다. 같으면 유효 lease 동안 같은 immutable observation, 다르면 409 REQUEST_CONFLICT다. 만료 뒤에는 새 request_id로 새 observation을 요청한다.

Producer는 credential 선정→같은 금융 read view/Context→target/hot/control/JSON 준비→B-1 수준 terminal guard→available lease의 원자 pin 순서를 MUST 따른다. 객체/lease 준비는 금융 R을 증가시키지 않는다. V1은 **observation 생성에만 짧은 BEGIN IMMEDIATE metadata transaction**을 선택한다. 그 안에서 current NS/R/roots와 원 credential을 고정하고 backend의 read-only 금융 presenter를 사용하며 immutable hot/control·응답 bytes·lease root pin을 준비한다. 마지막에 원 credential/NS/R/versions와 root association을 재검사하고 available lease와 함께 commit한다. Read view를 닫고 나중에 pin하는 race를 허용하지 않는다. 새 publisher는 이 transaction 안에서 금융 row를 ensure/수정해서는 안 된다(MUST NOT). Busy/guard conflict는 최대 3회 관측 전체 retry 후 409 OBSERVATION_CONFLICT 또는 503 ROOT_NOT_READY다. Commit 후 새 금융 변경은 후속 사건이다. 객체 download 동안 이 transaction을 유지하지 않는다.

이는 기존 B-1 endpoint를 수정하는 지시가 아니라 새 metadata-writing producer의 선택이다. Writer serialization/lock duration을 측정해야 하며 H가 큰 동안 생기는 contention은 숨기지 않는다. SQLite read transaction을 무기한 열거나 GC가 candidate root를 지운 뒤 stale Ref를 광고하는 대안보다 단순한 안전 경계다. Client network await/parse/build/lineage-lock/publication/installation guards는 별도로 유지한다.

### 15.3 Object acquisition

`POST /api/sync/v1/observations/{observation_id}/objects` body `{protocol:1,request_id:UUID,items:[{path:[Hash],offset:U64,length:integer}]}`. Items 1..64, length 1..1MiB, decoded 합≤1MiB, path 1..512개다. Path는 target의 raw/index/hot/control root에서 시작하여 실제 parent-child refs를 따라 마지막 object에 도달한다. 서버는 own object bytes로 path를 검증한다. Hash를 안다는 이유만으로 조회를 허용하지 않는다. 이 방식은 전체 reachability scan을 요청마다 하지 않게 한다.

200 `{protocol:1,request_id:UUID,observation_id:UUID,chunks:[ObjectChunk]}`이며 요청 순서와 같고 partial success는 없다. `ObjectChunk={ref:Ref,offset:U64,length:integer,data_base64:String}`. Strict RFC4648 padded base64를 사용하고 decoded length·offset·Ref 전체 bytes와 부합해야 한다. Inline_objects도 같은 chunk shape이며 target root object 또는 검증 가능한 descendant만 허용한다. Inline descendant는 parent object를 함께 제공하거나 이미 accepted path로 검증할 수 있어야 한다.

전체 object를 조립하고 길이/hash/C1/shape를 확인하기 전 bytes는 staging일 뿐이다. 서로 다른 observation의 chunk를 자동 결합하지 않는다. 동일 immutable Ref/NS를 explicit 확인한 재사용은 허용된다. Base64의 추가 bytes `4×ceil(decoded/3)`와 JSON framing/CPU를 성능 보고에 포함한다. 원 money lexeme는 **base64 내부 decoded bytes**에서 preflight해야 한다. Outer JSON parser만으로 admission을 끝내지 않는다.

### 15.4 종료·ack

`DELETE /api/sync/v1/observations/{id}`는 동일 owner/credential의 lease release, 204 idempotent다. 네트워크 실패해도 expiry로 정리한다. Local publication ack는 필수 endpoint가 아니다. Client complete installation 결정이 authority 경계이며 server ack/lease release는 financial receipt가 아니다.

## 16. Coherent observation 수명·인가

`Created → Available → Expired/Retired`다. Created는 client에 공개하지 않는다. TTL은 available 시점부터 최대 900초, 원 credential hash와 principal, namespace, immutable Target를 기록한다. 동시에 principal별 최대 4개의 Available을 허용하고 초과 시 429다. 이미 발급한 lease를 새 요청 때문에 조용히 evict하지 않는다.

Available 동안 참조한 object graph를 GC에서 pin한다. V1은 **object별 incoming-edge count + external root pin count**를 선택한다. Object 최초 insert 시 typed child Ref edges를 기록하고 child count를 같은 transaction에 증가시킨다. Lease는 네 개 target root의 pin만 증가시키므로 N개 descendants를 enumerate하지 않는다. Edge/pin count가 모두 0인 object만 bounded GC에서 제거하고 그때 child counts를 감소시킨다. Schema가 지정한 Ref만 edge이며 임의의 hash 문자열을 object link로 해석하지 않는다. 로컬 store도 같은 규칙을 사용하되 미수신 object는 missing placeholder로 구분한다. Complete manifest는 missing placeholder를 참조할 수 없다. Counter 손상은 full reachability 검증/blocked이지 추측 삭제가 아니다.

Download마다 original credential이 여전히 유효한지 검사한다. 다른 token으로 같은 principal 재인증해도 옛 lease는 사용하지 않고 fresh observation을 얻는다. 이후 DB mutation은 pinned Target를 바꾸지 않는다. Read transaction을 download 전체 동안 유지하지 않는다. Process restart는 §5의 새 epoch와 old lease 410으로 처리한다.

Lease 만료 전 완전 취득·검증한 객체를 local publication하는 것은 가능하다. 만료는 transfer 권한 수명이지 이미 수신한 coherent 관측의 무결성 소멸이 아니다. Ticket/mutation/mode/owner guards는 여전히 통과해야 한다. Mid-download expiry면 staged bytes를 accepted로 만들지 않고 fresh observation과 explicit refs로 재사용 여부를 판단한다.

## 17. 오류·retry와 full-resync 분류

Error body는 `{protocol:1,request_id:UUID|null,error:{code:String,action:"retry_same"|"new_observation"|"full_resync"|"blocked"|"reauthenticate",retry_after_ms:integer|null,current_ns:NS|null}}`다. 설명 문자열은 wire 필수가 아니다. Unknown code를 성공으로 취급하지 않는다.

| HTTP/code | 행동 |
| --- | --- |
| 401 AUTH_REQUIRED / 403 PRINCIPAL_OR_SESSION_CHANGED | reauthenticate, install 금지. Pending/J 유지 |
| 409 EPOCH_CHANGED | full_resync, old frozen authority 보존, 새 NS 확인 |
| 409 BASE_INVALID | full_resync 또는 local lineage 손상이면 blocked |
| 409 REQUEST_CONFLICT | blocked; 동일 nonce의 다른 body 자동 retry 금지 |
| 409 OBSERVATION_CONFLICT | new_observation, 최대 3회 client attempt 후 visible failure |
| 410 OBSERVATION_EXPIRED / OBSERVATION_INCOMPLETE | new_observation; target 일부를 live state로 보충 금지 |
| 422 UNSUPPORTED_CONTRACT / INVALID_REQUEST | blocked/명시 client upgrade; full로도 모르는 schema를 승인하지 않음 |
| 413 TRANSFER_BUDGET | 작은 object batch/inline budget으로 retry_same, 금융 POST 재전송 아님 |
| 429 LEASE_LIMIT / 503 ROOT_NOT_READY | retry_same, 명시 backoff; root/R 불일치 광고 금지 |
| network timeout/reset/500 | accepted B 보존, 동일 read-only request bounded retry 가능; financial POST receipt 판정과 분리 |

Local errors는 server codes와 구분한다: REPRESENTATION_INVALID, OBJECT_HASH_INVALID, GLOBAL_INDEX_INVALID, GENERATION_CHANGED, MODE_INELIGIBLE, PERSISTENCE_FAILED. 기존 baseline을 새 authority로 덮거나 자동 sanitize하지 않는다. Network timeout 자체는 cache corruption 증거가 아니다. Active flow의 client observation 재시도는 최대 3회, 기본 backoff 100/250/500ms와 서버 retry-after를 사용하고 foreground 무한 loop는 금지한다.

`retry_same`은 동일 read-only 작업/target 재시도다. Body를 바꾸면 새 request_id를 사용하며 같은 nonce의 다른 body를 413 retry로 정당화하지 않는다. Server BASE_INVALID의 action은 full_resync로 고정하고, client가 frozen/local lineage를 증명하지 못하면 별도 local RecoveryBlocked로 격상한다. Unsupported contract는 full resync로 해결되는 척하지 않는다.

## 18. Initial·full synchronization

1. No accepted base면 capability/auth/versions를 확인하고 base=null로 observation을 얻는다. Existing pins/J/pending은 삭제하지 않는다.
2. Raw-root와 11개 table tree를 모두 취득한다. 각 child descriptor/row-local 표현/PK/order/count/hash/namespace를 검증한다.
3. 전체 raw rows에서 global facts/index를 **독립 구조 계산**하여 target index_ref와 비교한다. Downloaded index를 그대로 trust하지 않는다.
4. Hot/control을 취득·검증하고 raw references/shared fields/정책 호환/context를 검사한다. 금융 결과는 backend 계산을 소비한다.
5. §25 complete target eligibility를 만족한 뒤 durable generation으로 게시한다. 초기 cache 일부만으로 Offline-ready를 선언하지 않는다.

O(N) full initialization·전체 구조 검증은 허용된다. Complete-store restart 검증도 O(N)을 허용한다. 정상 online steady state는 같은 검사를 매번 반복하지 않는다.

## 19. Base→target tree diff와 삭제 완전성

Base B의 accepted provenance·complete raw tree·global index를 먼저 확인한다. Target T의 full root를 받되 **서버가 보내 준 changed-row 목록만 믿지 않는다**. V1의 정확성은 complete target tree와 accepted base의 비교에 있다.

권고 알고리즘은 PK-range frontier diff다.

1. 각 table의 old/new root descriptor를 ordered frontier에 놓는다. Equal Ref+descriptor subtree는 그대로 재사용하고 내려가지 않는다.
2. 비동일 internal node는 검증한 children으로 대체한다. Min/max가 disjoint인 old/new interval은 각각 deletion/insertion 후보로 분류한다.
3. 겹치는 unequal ranges는 양쪽 node를 leaf까지 확장하고, 서로 겹치는 leaf interval의 연결 성분을 모아 old/new rows를 PK로 merge-diff한다. 새 boundary로 leaf를 split했다고 같은 index 위치의 child만 비교하면 안 된다.
4. Old leaf에만 있는 PK는 delete, new에만 있으면 insert, 양쪽이면 exact raw value/row_hash로 update 또는 unchanged를 구분한다. Range 이동의 old/new 양쪽을 모두 포함한다.
5. 양쪽 frontier가 소진되어 coverage가 완전함을 확인한다. Old tree의 삭제된 subtree를 아예 방문하지 않아 삭제를 놓치는 구현은 불합격이다.
6. §11 old facts 제거/new facts 삽입·reverse closure 검증 후 derived index root=target index_ref를 확인한다. Unchanged PK/row가 leaf shape 때문에 이동한 것은 금융 mutation으로 추정하지 않는다.

Server capture log는 changed paths inline/hints의 가속에 쓸 수 있지만 correctness 증명은 아니다. Log가 없어도 tree diff가 완전하면 skipped revisions를 지원한다. Tree/index가 없거나 coverage를 증명할 수 없으면 full resync다. Unbalanced frontier를 최악 O(N)으로 만드는 구현은 고정 D scaling gate를 통과하지 못한다.

## 20. No-change·historical edit/delete·month close

No-change는 fresh auth/terminal guard와 동일 Target 확인 후 old verified objects/index를 재사용한다. 새 synced-at/validated-at가 필요하면 local generation metadata만 작게 갱신한다. Same R 날짜 전이는 raw/index 유지 + fresh hot/control이다. 새 view를 old date의 hot으로 대체하지 않는다.

Historical update는 같은 PK의 raw bytes·관련 table leaf/paths와 facts를 바꾼다. 날짜 변경은 source/epoch identity를 만들지 않으며 old/new month query index를 invalidate한다. Delete는 target에서 사라진 row와 cascade/SET NULL 결과를 함께 diff하고 reverse references를 확인한다. Tombstone event는 server discovery용이며 target tree membership이 최종 삭제 의미다.

현재 `close_current_month`는 archive INSERT 새 ID, current DELETE, registration target rewrite, planned/fixed epoch reset, 급여 cash INSERT, batch/items/events/allocations/deferrals 변경을 같은 transaction에 한다. Protocol은 stable payment key를 PK와 혼동하지 않는다. 한 마감의 많은 changes/R 증가를 한 target로 관측하며 R+1을 요구하지 않는다. Recurring/fixed 확인은 source+epoch/child 또는 panel/cash 전체 closure를 검증한다. Payment grouping/order·close eligibility·effective money는 backend 결과다.

## 21. 구체 JSON 예제와 해석 규칙

완전한 request/response 예제는 [t66c-protocol-examples.json](specimens/t66c-protocol-examples.json)에 있다. 실제 credential/사용자 데이터는 없다. **모든 `<h:...>`는 상징 hash placeholder**이며 real computed hash라고 주장하지 않는다. `Ref.bytes`도 설명용 declared size이지 실측이 아니다. Placeholder를 동일 label로 일관되게 사용하며 canonical object/hash test vectors와 혼동하지 않는다. 실제 구현 wire에서는 64-hex와 실제 bytes가 필수다.

| 예제 ID | required 상황·정확한 결과 |
| --- | --- |
| E01 | base 없음 → initial observation, complete download/index validation 후에만 게시 |
| E02 | same Target no-change → fresh lease, raw/index/hot/control 재사용 |
| E03 | confirmed card POST 뒤 R100→103 → raw/index/hot 변경, committed marker는 게시 전 보존 |
| E04 | historical PK41 수정 → leaf/raw/index/hot refs 변경 가능, 같은 PK |
| E05 | historical PK42 삭제 → target membership 제거·global closure 확인 |
| E06 | month-close PK5→PK43 copy/delete, stable payment key 유지, 여러 table/큰 R jump |
| E07 | R100→300 skipped revisions → target tree diff, intermediate replay 불필요 |
| E08 | object download 중 lease expiry → 410, 새 observation, partial 설치 금지 |
| E09 | local cold corruption → fresh observation 아래 exact Ref repair; frozen B는 rebase하지 않음 |
| E10 | epoch 불일치 → 409 full_resync, old B/J/pending pin |
| E11 | unsupported schema → 422 blocked/upgrade, best-effort full parse 금지 |
| E12 | same R 다음 날짜 → raw/index 동일, Context/hot/control/sync root 변경 |

예제 파일은 protocol shape/echo/base-target identity/failure-action을 점검하는 **명세 fixture**다. Canonical financial bundle, migrated DB oracle 또는 implemented endpoint 실행 증거가 아니다.

## 22. Legacy Snapshot v7의 정확한 materialization

Current table/data/policy/content SHA, Snapshot ID, state_fingerprint는 **기존 full v7 파일에서 그대로 권위 있는 무결성 identity**다. New sync_root/raw/index roots는 다른 객체다. 정상 incremental path는 legacy flat hash를 계산하지 않는다. New Target에는 `state_fingerprint` 필드를 넣지 않는다.

Future client는 `SegmentedAuthority={target,complete_store_handle,discount_policy_defaults}`라는 별도 내부 envelope를 사용해야 한다. 기존 `AuthoritativeBaselineEnvelope.snapshot/fingerprint`에 partial Snapshot이나 sync_root를 주입해서는 안 된다(MUST NOT). Typed candidate의 user는 현재 선택된 AuthUser이며 Target.principal_id와 auth-generation guard로 결합한다. 기존 AppState의 guard/게시/retirement 순서를 보존하는 별도 adapter가 필요하고, legacy envelope가 실제 필요한 Offline/recovery/backup 경계에서만 전체 v7를 materialize한다. 이 adapter가 normal refresh에서 flat fingerprint를 요구하면 scaling gate 실패다.

Full export/restore/MW/recovery artifact가 필요할 때 complete raw state를 materialize하고 **B의 원 control metadata**로 v7 파일과 기존 flat hashes를 계산한다. Newly generated current Snapshot과 frozen B를 구분하고 export 시점의 registry/date로 frozen B를 다시 만들지 않는다. Synced-at/user/typed/defaults/resolved reconciliation ID도 frozen logical baseline에 보존한다.

Canonical array ordering은 CURRENT exporter와 같다:

| table | ORDER BY |
| --- | --- |
| ledger_entries | book_section, entry_kind, entry_date, sort_order, id |
| monthly_panels | month, panel_type, sort_order, id |
| cash_flows | occurred_on, sort_order, id |
| card_payment_batches | id |
| card_payment_batch_items | batch_id, id |
| card_payment_events | event_date, id |
| card_payment_allocations | payment_event_id, id |
| card_payment_deferrals | target_payment_month, entry_payment_key |
| notification_candidate_registrations | registration_key |
| app_settings / app_labels | key |

NULL sort·BINARY text order와 integral REAL/int 표현을 보존한다. PK leaf를 그대로 이어 붙이지 않는다. Full materialization에는 O(N) 검사·정렬 비용을 허용한다. Empty columns, table row counts/hash, data/policy/content hashes, snapshot_id 및 state_fingerprint를 existing algorithms로 재계산하고 restore는 기존 manifest/정책/actual migrated constraints admission을 유지한다. Segment SHA를 합쳐 flat SHA를 얻었다고 주장하지 않는다.

## 23. Client validation의 정확한 수명

| 상황 | MUST 검증 |
| --- | --- |
| 새 object/changed bytes | strict base64→exact bytes length/hash→UTF-8/raw-money+duplicate keys→JSON→모든 string/key Unicode→C1/required/types/domains→object NS/schema/count/ranges |
| raw leaf 최초 수신 | 기존 Snapshot raw row contracts와 PK/domain/money/epoch; whole index가 완성되기 전 authoritative 아님 |
| hot/control 매 변경 | 12 shapes/metadata/context·policy compatibility·present raw reference·같은 raw field/alias equality |
| raw relation 변경 | accepted facts에서 old/new reverse closure + target global index root equality |
| unchanged object | same NS/version/content identity와 complete accepted validation receipt. Read 시 hash 확인, filename/mtime trust 금지 |
| schema/structural validator 변경 | 지원된 compatibility proof 없으면 full revalidation/index rebuild. Old receipt 자동 승격 금지 |
| full recovery/materialization | complete-store/root/global constraints + 정확한 legacy v7 hash/restoreability |

Exact-money/Unicode/duplicate-key는 inner canonical bytes에도 적용한다. Compressed transport/outer JSON 정상이라는 이유로 생략하지 않는다. Off-device partial object는 provisional staging이다. 기존 B-2 parser는 full legacy bundle에 그대로 유지하며 새 protocol consumer가 기존 함수를 부적절한 partial Bundle에 호출하거나 checks를 약화하지 않는다. Refactor 필요 시 별도 구현/test 승인 범위로 둔다.

## 24. Mobile physical store와 publication 전제

신규 store discriminator는 **`segmented-store/1`**이다. 현재 `baseline.json` schema v4를 재해석하지 않는다. 권고 구현은 loose object files와 directory ordering을 최소화하기 위해 **단일 local SQLite object store**에 immutable object bytes/chunks, receipts, index nodes, generation manifests, pins, accepted pointer를 저장한다. Backend DB 교체나 OfflineProjection redesign이 아니다.

| record | 필수 의미 |
| --- | --- |
| objects/chunks | NS+Hash+exact bytes, 전체 hash 완료 전 `staged`; chunk size≤1MiB |
| validation receipts | object/NS/schema/canon/validator, raw-index complete association |
| object_edges | parsed parent-child refs; GC와 completeness의 검증된 graph |
| generations | Target, owner/local auth provenance, synced_at, complete object/index roots, optional resolved reconciliation ID, manifest checksum |
| pins | accepted/previous/frozen/J/pending/reconciliation/artifact/in-flight/migration 이유와 identity |
| accepted | principal namespace별 한 generation ID와 commit sequence; manifest와 같은 SQLite transaction에 갱신 |

Local generation ID는 UUIDv4이며 Target.sync_root와 구분한다. 무변경 sync의 synced_at만 갱신해도 새 immutable local manifest/ID를 만들 수 있다. Auth provenance는 owner와 비밀이 아닌 lineage 식별 정보일 뿐이며 token/password를 저장하지 않는다. 재시작/재인증 뒤 durable receipt는 bytes 검증 증거이지 과거 ticket의 설치 권한이 아니다.

Accepted generation에 reachable한 모든 bytes/index가 로컬에 있어야 한다. Local pointer checksum은 손상 탐지이지 서명이 아니다. Startup에는 complete-store/readback/index 검증 O(N)을 허용한다. Session 중 unchanged immutable store의 검증 provenance를 재사용하되 hash-on-read·scrub에서 손상을 발견하면 fail-closed한다. 읽지 않은 임의 bitrot를 즉시 탐지한다고 약속하지 않는다.

## 25. Atomic publication·installation eligibility

`CompleteTargetVerified`가 되려면: base provenance 유효, authenticated same Target, 11 table coverage, object hashes/shape/ranges, exact old/new membership, complete global index, hot/control raw 대응·호환성, owner/auth/request/mutation/mode guards, 로컬 저장 가능성이 모두 만족되어야 한다.

게시 순서 MUST:

1. Staged object chunks를 완성·검증하고 immutable objects와 index nodes를 durable transaction에 저장한다. Old object를 overwrite하지 않는다.
2. Complete manifest와 모든 required edges/receipt를 저장·readback하고 기존 authority/frozen/artifacts를 pin한다.
3. 기존 AppState lineage critical section에서 ticket/user/auth/mutation/mode를 재검사한다. Ordinary ONLINE 또는 기존 finalizing 허용 범위만 가능하다.
4. 같은 local SQLite transaction에서 complete manifest/pins/accepted pointer를 switch한다. Guard 검사와 commit 사이 await로 generation이 바뀌지 않도록 native synchronous commit 또는 coordinator fencing을 사용한다. **비동기 commit을 발행한 뒤 guard 없이 설치하지 않는다.**
5. Durable accepted generation을 load/readback하여 recoverability와 installation authority를 확인한다. 실패하면 pending 유지·성공 알림 금지다.
6. Eligible confirmed pending을 기존 token/owner/lineage 조건으로 retire한다. OutcomeUnknown은 retire하지 않는다.
7. 같은 complete candidate의 모든 user/summary/payment/judgment/entries/confirmed/panels/cash/settings/status/policy fields를 설치하고 notify/success를 수행한다.

세션이 local commit과 경합하면 stale namespace의 complete cache는 남을 수 있지만 새 session의 accepted authority로 사용하거나 pending을 정리하지 않는다. Accepted pointer의 auth/request fence를 포함한 native compare-and-commit 또는 동일-thread synchronous commit을 구현에서 입증해야 한다. 이것은 단순 transaction API 호출만으로 해결됐다고 주장할 수 없는 proof다.

## 26. Android durability와 safe fallback

논리 원자성, process crash, sudden power loss를 구분한다. 권고 SQLite store는 모든 object/index/manifest/pointer를 같은 DB 안에 두고 rollback-journal **DELETE + synchronous=EXTRA + foreign_keys=ON** profile을 사용한다. Object data를 먼저 commit한 다음 pointer를 commit하므로 새 pointer가 이전 미완료 object를 참조하지 않는다. SQLite VFS/디스크 flush 가정에 의존한다. [SQLite atomic commit](https://sqlite.org/atomiccommit.html), [synchronous pragma](https://sqlite.org/pragma.html#pragma_synchronous), [deferred FK](https://sqlite.org/foreignkeys.html#fk_deferred)의 의미와 실제 Android driver를 대조해야 한다.

SQLite가 abstract atomicity를 제공한다는 사실을 현재 Flutter/Android/실기기 power-loss 검증으로 표현하지 않는다. REQUIRED abstraction은 `putImmutableAndSync`, `verifyComplete`, `commitAcceptedWithFence`, `recoverAcceptedOrPrevious`, `pinAndGCTransaction`이다. File-backed alternative라면 file data flush, same-filesystem atomic replace, directory entry flush, journaled pointer recovery를 모두 입증해야 한다. Rename 하나로 충분하다고 가정하지 않는다.

**IMPLEMENTATION PROOF REQUIRED:** 선택 driver가 pragmas/VFS를 실제 적용하고 I/O error를 성공으로 반환하지 않는지, native commit fence, process death·disk-full·corrupt pointer·GC 중단 테스트, 실기기 전원 손실 범위. 지원 primitive/검증이 없으면 segmented rollout을 MUST 차단한다. 안전한 fallback은 기능 활성화 전 기존 full consumer/store를 유지하는 것이며, invalid segmented acquisition 뒤 성공으로 legacy를 호출하는 hidden fallback이 아니다.

기존 pending/J/state 파일은 format을 바꾸지 않는다. Pointer와 별도 파일 삭제의 cross-store crash는 resolved reconciliation ID·남은 marker의 conservative recovery로 처리한다. Pending 삭제가 유실되어 marker가 다시 보이는 것은 read-only rebuild 사유이지 POST 재전송 허가가 아니다.

## 27. Client/server state machines·crash matrix

```text
서버: Created ──terminal guard + pin──> Available ──TTL/release/restart──> Expired/Retired

클라이언트:
AcceptedBase → ObservationAcquired → ComponentsStaged → ComponentsValidated
  → CompleteTargetVerified → DurableGenerationPublished → EligiblePendingRetired
  → StateInstalled
```

No pending이면 retirement 단계는 no-op이다. 각 단계의 실패는 old accepted authority와 J/pending을 보존한다. Auth/mode/lineage change는 Cancelled, representation/global failure는 Rejected, network/lease는 Retryable, persistence는 RecoveryBlocked로 분류한다. Cancellation 뒤 이전 ticket으로 다시 publish하지 않는다. Finalizing 진입은 기존 reconciliation coordinator만 허가한다.

| 중단 위치 | durable authority·restart |
| --- | --- |
| 다운로드 전/중/일부 완료 | old accepted, staging은 권위 없음; old load 후 fresh/valid lease retry |
| 검증 후 object commit 전 | old, 메모리 PASS 재사용 불가; 다시 verify/store |
| objects/index commit 후 manifest 전 | old + orphan immutable objects; fresh target에서 explicit reuse 가능 |
| manifest 저장 중/완료, pointer 전 | old, staged complete target은 자동 install하지 않음 |
| pointer transaction 중 | old 또는 complete new; corrupted DB/pointer면 verified previous 또는 blocked |
| pointer 후 pending 전 | new complete B + marker, confirmed면 read-only finalization; unknown 유지 |
| pending retirement 중/후 UI 전 | new B, marker 존재/삭제; POST 재실행 없음, new state reload |
| UI 후 notify 전 | new durable B, 재시작 install; notify를 receipt로 취급하지 않음 |
| GC 중 | pins/accepted transaction 보호; incomplete cleanup 재개, active content 손실이면 blocked |

이전 authority 복구는 local recovery이지 fresh network 성공이 아니다. Power-loss로 new commit이 입증되지 않으면 submit 성공을 재구성하지 않는다. Any candidate가 complete라 해도 stale ticket이면 publication/installation 불가다.

## 28. Pending receipt matrix

| 상태 | sync/download | publish | marker retire·UI success |
| --- | --- | --- | --- |
| pending 없음 | ONLINE/mode eligible에서 허용 | complete target·guards 후 허용 | refresh 성공만 표시 |
| POST in flight | 자동 병행 rebuild 금지, 기존 single-flight | mutation lineage 앞선 target 금지 | 금지 |
| definite pre-mutation rejection | 기존 endpoint contract로 marker 해제 후 일반 refresh | 일반 규칙 | mutation 성공 표시 금지 |
| confirmed receipt, committed marker persist 전 | 먼저 marker를 durable committed로 기록 | 그 전 completion 금지 | receipt만으로 UI 완료 금지 |
| serverCommittedRebuildPending | read-only sync/repair 허용 | complete current target만 | durable new B+guards 후 해당 marker retire·성공 |
| outcomeUnknown | 기존 복구가 허용하는 read-only observation은 가능 | 기존 정책이 허용하면 complete observation 저장 가능, unknown 보존 | GET만으로 retire/새 금융 POST/Offline 진입/submit 성공 금지 |
| idempotent explicit retry receipt | 원래 payload/key/owner로 확인 후 committed 전이 | 이후 일반 rebuild | 다른 retry identity로 unknown 해제 금지 |
| publication/retirement 실패 | marker 그대로·read-only recovery | old 또는 durable complete new | 완성 성공 금지, duplicate POST 유도 금지 |

새 sync POST가 read-only인 것은 기존 financial POST의 retry 조건을 바꾸지 않는다. Receipt/marker status와 accepted generation은 별도 독립 증거다.

## 29. Frozen B/J와 reconciliation

Offline 진입은 현재 규칙대로 pending 없는 verified authoritative generation에서만 가능하다. 해당 Target/control/hot/raw/index와 필요한 모든 objects를 frozen pin하고 기존 metadata lineage에 결합한다. J는 기존 input-only operation ID/sequence/payload 형식이다. Server unavailable이면 frozen B와 J를 로컬에서 reload하며 OfflineProjection은 provisional이다.

OFFLINE에서는 현재 health-only 동작을 유지하고 새 observation이 B를 교체하지 않는다. Reconnection은 RECONCILIATION_REQUIRED이며 자동 rebase/merge가 아니다. Mode/metadata/J framing mismatch는 RecoveryBlocked다.

MW는 frozen B를 exact v7+legacy baseline으로 materialize하고 원 ordered J와 기존 reconciliation identity/semantic request fingerprint 규칙을 사용한다. SW는 J를 replay하지 않는다. 양쪽 recovery artifacts를 검증한 뒤에만 선택 실행한다. Commit unknown이면 기존 status로 확인한다. Confirmed 결과 뒤 fresh segmented generation의 durable complete publication을 finalizing guard 아래 수행한다. Resolved reconciliation ID를 new manifest에 저장하여 cleanup 중 crash에도 같은 J를 새 B에 다시 projection하지 않는다.

현재 state/J format을 sync_root 의미로 몰래 바꾸지 않는다. `segmented-store/1` adapter는 기존 lineage fingerprint가 필요한 **Offline entry/reconciliation/legacy artifact 시점**에 complete legacy logical baseline을 materialize하여 기존 hash를 계산한다. 정상 online refresh마다 이 O(N) hash를 요구하지 않는다. Active legacy B/J/finalizing이 있으면 §33 migration을 미루고 기존 recovery를 유지한다. Frozen segment를 서버에서 복구할 수 없으면 fresh R로 J를 이동하지 않고 artifact/manual recovery blocked로 남긴다.

## 30. Full resync·retry·blocked의 구분

| 원인 | MUST 행동 |
| --- | --- |
| accepted baseline 없음 | base=null initial full |
| 같은 Ref의 missing/corrupt object | Available observation path로 exact repair, 이후 검증. Frozen B는 정확한 object 외 대체 금지 |
| global index invalid/base root corrupt | old evidence 보존, ONLINE/J없음이면 full validation; frozen J 있으면 blocked/정확한 B repair |
| namespace epoch 변경 | new NS complete full, old frozen/J/pending 별도 pin; 자동 rebase 금지 |
| unsupported protocol/schema/policy | 명시 upgrade/미활성 legacy selection; malformed response fallback 금지 |
| unavailable change log | complete trees/index가 있으면 diff; 없으면 full. R 연속성 추측 금지 |
| expired observation | fresh observation, same Ref staging만 explicit 재사용 |
| wrong principal/auth generation | 취소·재인증, 다른 사용자 B를 새 B로 수선하지 않음 |
| global raw constraint failure | target reject, old 유지, 서버 오류/정확한 full 검증; 반복 malformed를 sanitize 금지 |
| ENOSPC/durable failure | no successful publish/retire, old authority·pins/J 보존, persistence recovery |

Full resync는 정상 mode 권한을 우회하지 않는다. `OFFLINE/RECONCILIATION_REQUIRED/FINALIZING`에는 기존 선택·artifact·guard가 적용된다. Network timeout을 이유로 complete cache나 J를 삭제하지 않는다.

## 31. 큰 Snapshot restore/Mobile Wins — 별도 contract

CURRENT 일반 restore/MW request limit은 기본 26,214,400B다. `ApiBodyLimitMiddleware`는 Content-Length와 body chunk 누적을 검사하며 request gzip decoder는 없다. T6.6A 50k Snapshot 28,076,353B는 기본값을 넘지만 실제 413 test는 이 설계에서 실행하지 않았다. HTTP chunked transfer/response compression으로 해결하지 않는다.

Future large restore는 정상 sync와 다른 `/api/recovery/v1/` namespace다. Normal financial mutation semantics는 바꾸지 않는다.

| API | required contract |
| --- | --- |
| `POST /api/recovery/v1/uploads` | `{protocol:1,upload_id:UUID,intent:"restore"\|"mobile_wins",principal_id,expected_ns:NS,parts:[Part],reconciliation_id:ReconciliationId\|null,baseline_fingerprint:Hash\|null}`. Part=`{name:"snapshot"\|"journal",bytes:U64,sha256:Hash}`. Restore는 snapshot만·두 nullable fields null, MW는 snapshot/journal 순서·기존 ID와 B fingerprint 필수. 같은 upload ID+exact declaration은 reuse, 다르면 409 |
| `PUT /api/recovery/v1/uploads/{id}/parts/{name}/chunks/{index}` | identity octet-stream≤1MiB, canonical nonnegative integer index, `X-Chunk-SHA256` 64-hex header. Offset=index×1MiB, 마지막만 짧음. Repeated exact bytes 204, conflict409. Auth/owner/expiry/budget 검사 |
| `GET /api/recovery/v1/uploads/{id}` | `{protocol:1,upload_id,status:"staging"\|"ready"\|"committed"\|"expired",expires_at:Time,parts:[{name,bytes,sha256,received_ranges:[[U64,U64]]}],receipt:Receipt\|null}`. Ranges는 받은 chunk index의 sorted/disjoint half-open 구간이며 committed에는 저장한 final receipt |
| `POST /api/recovery/v1/uploads/{id}/commit` | `{protocol:1,upload_id,password,expected_server_fingerprint:Hash,confirm_server_changed:boolean,mobile_artifact_sha256:Hash\|null}`. Restore/MW에 맞는 기존 authorization/confirmation 유지 |

Create는 201, 같은 declaration retry는 200으로 위 status shape를 반환한다. GET은 200, commit 성공/retry는 200 Receipt다. `Receipt={protocol:1,upload_id,intent,ns_after:NS,revision_after:U64,result}`다. Restore result는 현재 admin 응답의 `{restored:{11개 table 이름:nonnegative row count}}`, MW result는 현재 `apply_mobile_wins`의 committed record를 그대로 쓴다(reconciliation_id/status/request_digest/fingerprint_version/request_fingerprint/baseline_fingerprint/pre_server_fingerprint/result_fingerprint/server_changed/server_artifact_filename/mobile_artifact_sha256/operation_count/operation_results/summary/committed_at). 기존 operation result·Summary contracts를 재사용하며 generic arbitrary receipt를 승인하지 않는다. MW의 mobile_artifact_sha256는 non-null, restore는 null이다. Password는 현재 입력 제약·검증을 재사용하고 upload metadata/log에 저장하지 않는다.

Recovery errors도 §17 error shape를 사용한다. 404 UPLOAD_NOT_FOUND는 action=blocked/ID 확인, 410 UPLOAD_EXPIRED는 blocked/새 upload 필요, 409 UPLOAD_CONFLICT는 blocked, 409 EPOCH_CHANGED는 blocked/새 선언·명시 확인, 409 SERVER_STATE_CHANGED는 blocked/기존 사용자 확인, 413 RESTORE_BUDGET은 blocked/지원 budget 검토, 422 RESTORE_INVALID는 blocked다. 401/403은 reauthenticate이며 auth가 다른 principal의 upload를 인수하지 못한다. 여기서 blocked는 현재 upload/commit 자동 진행 금지이며 새 upload 준비와 명시 복구까지 영구 금지라는 뜻은 아니다. Confirmed commit 뒤 status/receipt는 financial command 재실행을 허가하지 않는다.

각 part의 chunk 수는 ceil(bytes/1MiB), indices 0..count−1이고 gap/overlap/extra 금지다. 전체 part SHA와 exact byte length를 계산한 뒤 snapshot UTF-8/raw-money/Unicode/manifest/policy/actual migrated restore 검증, journal의 기존 ordered authoritative inputs·semantic ID를 검증한다. Parts를 서버 raw DB에 조금씩 적용하지 않는다. Snapshot part는 **그대로 v7 파일 bytes**, journal part는 C1 ordered operation array이며 legacy operation schema를 바꾸지 않는다.

MW의 declared baseline_fingerprint는 uploaded B의 기존 `snapshot_state_fingerprint`와 정확히 같아야 한다. Sync_root를 대신 넣지 않는다. Mobile artifact SHA는 현재와 같은 **client가 검증·보관한 recovery artifact identity**다. Server가 전송받지 않은 전체 mobile artifact 파일을 Snapshot/J 두 part만으로 재현·검증한다고 주장하지 않는다. Backend는 B/J 및 기존 semantic request fingerprint/operation identity를 검증하고 이 artifact identity를 receipt에 결합한다.

Staging은 private bounded disk quota·24시간 TTL·동시 session quota·decoded resource budget을 사용한다. Request compression은 v1에서 허용하지 않는다. 전체 budget `restore_bytes`는 capability에 명시하고 exceeded면 staging 413, source state 불변이다. Memory/CPU/disk peak를 검증하지 않은 budget을 광고하지 않는다. Complete payload를 stream-validate/임시 migrated DB로 검사할 수 있어야 하고 마지막 apply만 원 authoritative transaction이다.

Principal별 미완료 upload는 최대 2개, session의 두 part bytes 합은 restore_bytes 이하, private staging 총 quota는 최소 동시 허용 bytes와 검증 임시 DB/백업 필요량을 별도 산정한다. Chunk persist/hash 확인 뒤 received marker를 기록하고 acknowledge한다. Restart에 파일/marker가 불일치하면 해당 chunk를 missing으로 내려 재전송하게 할 뿐 ready/committed를 추정하지 않는다. Ready는 complete parts의 hash·구조 검증 완료 상태이며 commit 직전에도 file integrity를 확인한다. Committed receipt와 선언은 금융 DB metadata transaction에 남아 TTL expiry로 지우지 않는다. Receipt 보관 기간을 기존 reconciliation evidence보다 짧게 하여 자동 재적용을 허용하지 않는다.

Commit은 BEGIN IMMEDIATE에서 현재 auth/password·S fingerprint/confirmation을 다시 확인하고 mandatory pre_restore 또는 pre_reconcile_server와 mobile artifact 검증을 유지한다. Restore table replacement 또는 **Apply(B,J)**와 root bootstrap/epoch rotation·durable receipt 저장을 한 transaction으로 commit한다. 실패는 원 S·R·epoch·receipt로 rollback한다. Backup 파일은 안전장치로 보존한다.

Restore upload ID는 신규 large-restore command의 idempotency identity다. MW는 기존 reconciliation ID/서버 semantic fingerprint가 원본이며 upload ID로 우회하지 않는다. Committed retry도 declaration/B/J identity와 authorization을 확인하고 stored receipt만 반환하며 재적용하지 않는다. Response loss는 status 조회로 해결한다. 적용 뒤 epoch가 바뀌어도 같은 principal의 committed receipt 조회는 가능해야 한다. 미commit session의 expected_ns가 바뀌면 409, 새 upload/명시 확인이 필요하다. Client는 commit 전에 upload/원래 semantic identity를 durable하게 보존해야 한다.

**Rollout dependency:** 실제 사용자 segmented Offline/recovery의 일반 활성화 전에 이 large contract 또는 같은 보장을 제공하는 검증된 복구 경로가 필요하다. 작은 dataset만 한정할 경우에도 frozen B+허용 J+wrapper의 최악 budget과 모든 restore 경로를 입증하고 제한을 명시 승인해야 한다. 그 증명 없이 “현재 25MiB 미만”만으로 activation하지 않는다. 지금 허용하는 것은 isolated synthetic protocol 검토뿐이다.

## 32. Backup·pin·GC와 storage pressure

Current launch/foreground full Snapshot 및 최근 30개 standalone backup, mobile recovery artifact 30개·서버 pre_restore 정책을 유지한다. Current+previous generation 2개만으로 대체하지 않는다. Backup 파일·shared-object backup format 변경은 별도 사용자/compatibility 승인 사항이며 이 v1 필수 구현에 포함하지 않는다. 따라서 launch/foreground auxiliary backup·MW/artifact/restore는 O(N) 예외다.

Pins는 accepted, previous verified recoverable, frozen B, active J lineage, pending-required generation, reconciliation/artifacts, migration source/target, bounded download/lease를 모두 포함한다. Shared object는 모든 pin이 사라져야 삭제 가능하다. Pending/J의 source identity를 pin 없이 filename만 보존하는 것은 금지다.

GC는 local SQLite transaction으로 pin/refcount/edge 상태와 직렬화하며 publication transaction의 신규 pin을 보지 못한 채 삭제하지 않는다. Orphan staging은 lease/pin 없음과 age budget을 확인한 뒤 bounded batches로 제거한다. Reachability metadata가 손상되면 O(N) rebuild로 검증하고 추측 sweep하지 않는다. Crash 중 일부 orphan만 제거되어도 accepted graph는 완전해야 한다. Full mark/sweep·vacuum는 maintenance O(N)이며 normal refresh critical path가 아니다. Space 부족은 old complete B/J/pending을 지우는 대신 sync 실패·recovery UI로 처리한다.

## 33. Legacy migration·old clients·rollback

Capability 미지원 또는 segmented store 미활성 client는 현재 `/api/authoritative-state` full B-2 경로를 그대로 쓴다. 구 mobile/frontend와 Snapshot restore endpoint는 새 envelope를 받지 않는다. Dead API 제거는 T6.8 이후 별도 consumer 감사다.

Migration preconditions: ONLINE, active J/reconciliation 없음, unresolved pending 없음, 기존 v4 B의 owner/전체 raw/typed/money/Unicode/정책/hash/구조 검증 통과, 충분한 storage. Pending/frozen epoch가 있으면 기존 경로로 recovery 완료 전 conversion을 시작하지 않는다.

Migration은 old B를 pin하고 `segmented-store/1`에 rows·indexes·hot/control을 staging한다. Exact legacy materialization 결과가 original Snapshot/table hashes/ID/fingerprint 및 baseline logical/serialized equality를 만족하는지 확인한다. Local legacy B만으로 새 server epoch/R을 추측하지 않는다. 첫 new observation은 base=null이며 exact identical bytes만 명시 재사용한다. Namespace/Target에 결합한 complete new generation을 게시한 뒤 storage discriminator를 atomic switch한다. Journal/pending 파일의 version은 그대로다.

중단/실패는 old full B를 유지한다. Old binary rollback은 new segmented store를 해석하지 못하므로 before-activation rollback은 old pointer/B, after-activation rollback은 explicit full v4 export/materialization과 pending/J compatibility 검증을 요구한다. 무조건 old baseline.json로 되돌아가 새 J를 무시하지 않는다. Server code rollback도 새 DB checkpoint에 대한 별도 호환성 검증 없이 실행할 수 없다.

## 34. 미래 rollout과 구현 의존성

**DESIGN DEPENDENCY:** 본 C 명세 독립 감사 → canonical/schema/epoch/tracking/index/durability contracts 확정 → 구현 승인. 지금 제품 변경을 허가하지 않는다.

**IMPLEMENTATION DEPENDENCY:**

```text
D1 schema admission + epoch/bootstrap + writer fence
 → D2 capture coverage + sync pre-commit roots/index + exact maintained aggregates
 → D3 canonical objects + coherent observation/transfer + leases/GC
                         ↘
E1 C1/shape/raw facts parity → E2 local store/durability/pins
 → E3 complete index + tree diff + publisher → E4 pending/Offline/legacy adapter
                         ↗
R1 large restore/MW + artifacts/retention + migration/rollback
 → isolated new-client interoperability/full-resync/crash suites
 → performance gates (H/D fixed, N increased; compression comparison)
 → T6.6F independent integrated audit → explicit rollout authorization
```

Server는 old clients를 유지하면서 새 support를 미활성 상태로 준비해야 한다. DB schema migration/root bootstrap을 검증하기 전 capabilities의 v1 support를 광고하지 않는다. New mobile을 backend support보다 먼저 강제 활성화하지 않는다. Compression은 독립 승인 후보이며 이번 구현/설계가 배포한 것이 아니다.

## 35. Complexity·압축 비교와 measurable gate

N=전체 역사 row, H=hot/참조 working set와 required control/policy descriptor 크기, D=base 이후 changed rows, L=영향 leaf, P=전체 leaf 수, E=영향 reverse/constraint facts, B=전송·검증된 changed bytes다. PK/key/row string 길이를 실제 byte 입력으로 센다. Missed revisions에서 최종 raw 값이 원래대로 돌아와도 중간 많은 변경이 tree shape를 바꿨으면 L은 클 수 있다. Bounded-change 가정은 단순 net row 차이만이 아니라 해당 기간의 실제 변경/representation 변화도 제한한다. 무상한 settings/registry 이력을 H 밖의 숨은 상수로 취급하지 않는다.

| 작업 | backend discovery/root/index/금융 계산 | 전송·mobile·durable |
| --- | --- | --- |
| unchanged | fresh auth/context + root O(1), cached hot 또는 O(H) 계산 | small manifest/참조, reused hot; index/역사 재검증·full rewrite 없음 |
| 현재 카드 한 건 | capture O(D), B+paths O(L log P), facts trie O(256E), hot O(H)+indexed aggregates | changed leaves/paths+hot, bytes B 및 affected facts, 객체 신규 저장 + small pointer |
| historical update/delete | 같은 비용 + old/new references/aggregate/window 영향 | old/new range diff·tombstone membership, 필요한 closure; 대량 참조면 E 큼 |
| month close | 해당 월/관계 D와 hot, mandatory backup/full 예외 | D/L가 클 수 있음, 전체 백업 O(N); 모든 operation O(1) 아님 |
| cache miss | target objects lookup/path O(depth), financial re-evaluation 불필요 | missing bytes, cold initial miss면 N |
| full sync/restart/epoch bootstrap | O(N) validation/build, legacy sort 비용 가능 | N bytes/구조/hash/index·전체 저장 허용 |
| backup/MW/restore | complete v7 materialization·mandatory backups·Apply O(N+J) | standalone file/request·artifact O(N+J) |
| GC/compaction | bounded ongoing accounting, full sweep는 maintenance O(N/P) | active refresh에서 full graph mark 금지 |

조건부 정상 목표는 O(H + changed bytes + L log P + 256E)이며 단순 O(H+D)나 모든 operation O(1)을 주장하지 않는다. Current full financial validators/flat hash/lineage/full baseline encode가 남으면 정상 history-independent gate를 통과하지 못한다. No-change lease pin에 전체 graph 순회가 남아도 실패다. Network 단계는 tree miss 깊이/배치에 따라 늘 수 있어 B-3 1 GET/1 RTT를 무조건 유지한다고 약속하지 않는다. Inline/hints는 효율화일 뿐 완전성 근거가 아니다.

T6.6A HOST/synthetic 비교군은 10k raw **5,684,312B**, Snapshot **98.45%**, cold **97.05%**, gzip6 **108,916B**, Brotli4 **43,033B**, backend **1,348.5ms**, parser+typed **1,970.1ms**, publication **269.7ms**다. 서로 포함되는 timing을 더하지 않는다. New base64 framing·compression CPU·object HTTP headers/RTT도 비교에 포함한다. Hot raw 후보 167,812B가 full gzip보다 클 수 있다. 다양한 문자열 control gzip 568,847B와도 비교해야 한다.

Scaling 감사는 H/D 고정, N=1k/5k/10k/50k/100k에서 no-change/card/cash rebuild를 반복하고 rows read/bytes hashed·validated·written/HTTP entity/RTT/memory·median/p95를 측정한다. 정상 경로의 full history fetch/hash/serialize/write 횟수 **0**, control에 flat P 목록 없음, bounded leaf/hash-path/affected index 증가를 입증한다. Device 절대 latency 목표는 post-T6.6 gate 전 정하지 않는다.

## 36. Normative invariant catalog

Severity는 실제 violation이 구현되었을 때의 제안 등급이며 이번 새 발견 등급이 아니다. H=High, M=Medium. 필요한 proof와 관찰 가능한 실패를 각각 기록한다.

| ID·statement | 책임 | 필요한 증거 / 관찰 가능한 위반 | proposed test·등급 |
| --- | --- | --- | --- |
| I1 principal 일치 MUST | auth/coordinator | credential/principal/ticket / 다른 사용자 설치 | wrong principal·relogin, H |
| I2 epoch 정확 MUST | bootstrap/client | 새 epoch와 cache NS / rollback R 재사용 | DB backup restore/startup, H |
| I3 exact accepted base MUST | client store | base Target/provenance / 잘못된 base 위 patch | corrupt base/echo, H |
| I4 same coherent Target MUST | producer | R/context/root/terminal guard / mixed view | concurrent commit, H |
| I5 complete 11 table coverage MUST | trees/store | 모든 ranges/refs/count / 누락된 cold를 complete 선언 | omitted/duplicate leaf, H |
| I6 canonical safe bytes MUST | codec/client | raw token·Unicode·C1 / 표현 손실 accepted | surrogate/fractional/key matrix, M |
| I7 exact root MUST | both | child digest/count/order / altered subtree 통과 | stale parent/range reorder, H |
| I8 old/new membership 정확 MUST | diff | 양쪽 frontier 소진 / 삭제·이동 누락 | PK move/delete/split, H |
| I9 complete global facts MUST | both index | F(raw)=root 귀납 / cross-leaf UNIQUE 누락 | N4/PK collision, M |
| I10 reverse closure 완전 MUST | both index | old/new edges 영향집합 / dangling raw 관계 | FK SET NULL/cascade omission, H |
| I11 hot은 backend·same context MUST | producer/client | same-view presenters + raw 대응 / 다른 context hot | date/registry/hot mix, H |
| I12 client Category C 복제 MUST NOT | mobile | source inventory / 금융 재계산 gate | C-only controls, M |
| I13 incomplete publish MUST NOT | publisher | complete durable graph / partial authority | missing object·ENOSPC, H |
| I14 stale publish MUST NOT | coordinator/native store | commit fence + guards / old A가 B 덮음 | refresh/mutation/mode race, H |
| I15 GET≠receipt MUST | pending | 별도 confirmed proof / unknown 정리 | lost POST + sync, H |
| I16 frozen B/J 보존 MUST | Offline | pins/lineage/input journal / silent rebase | other-device+J, H |
| I17 crash recoverability MUST | native store | atomic current/previous complete / torn authority | 모든 §27 boundary, H |
| I18 live pin GC MUST NOT | GC | serialized pins/edges / 유일한 B 삭제 | GC-pointer/frozen race, H |
| I19 safe full resync MUST | coordinator | mode/evidence 보존 / J 삭제 후 재초기화 | expired log/cache corrupt, H |
| I20 exact legacy materialization MUST | adapter | v7 hashes/order/metadata equality / 다른 B 복원 | archived NULL/REAL/empty, H |
| I21 commit tracking atomic MUST | DB/finalizer | deferred fence·R/root parity / untracked commit | direct SQL/rollback/cascade, H |
| I22 lease auth/reachability MUST | transfer | original credential/path/TTL / hash로 무권한 data 조회 | expired token/guessed hash, H |
| I23 큰 복구 all-or-nothing MUST | recovery | chunks/hash/backup/one apply/receipt / 부분 DB 적용 | >25MiB/crash/retry, H |
| I24 30 backup 의미 보존 MUST | backup/GC | 별도 파일/artifact retention / 2gen으로 축소 | backup count/export, M |
| I25 steady-state full N 작업 MUST NOT | D/E integration | instrumented rows/bytes / hidden full scan | H/D fixed scaling, M |

## 37. Negative matrix·결정적 기대값

다음 34개는 미래 테스트 계획이며 이번에 실행한 앱 테스트가 아니다.

| 번호 | 입력/중단 | 기대값 |
| --- | --- | --- |
| 1 | wrong principal | 403/local reject, baseline/pending 그대로 |
| 2 | 같은 owner 새 auth generation | old request Cancelled, fresh ticket 없이는 publish 금지 |
| 3 | epoch 변경 | 409 full, frozen pins 보존 |
| 4 | unsupported schema | 422 blocked/upgrade, best effort 금지 |
| 5 | incorrect base root | local base reject, J 없으면 explicit full |
| 6 | missing required segment | CompleteTargetVerified 불가, exact repair |
| 7 | corrupted bytes | hash/표현 reject, old 유지 |
| 8 | duplicate leaf | range/PK/index reject |
| 9 | wrong leaf order | child/key order reject |
| 10 | incorrect key range | descriptor/body mismatch reject |
| 11 | cross-segment duplicate PK | global facts reject |
| 12 | N4 collision | 빈 key 포함 reject; 여러 null/distinct BINARY controls accept |
| 13 | referenced row 삭제 누락 | reverse/FK closure reject |
| 14 | historical row partition 이동 | old/new 전체 반영, missing side reject |
| 15 | cascade capture 누락 | current R/root/facts mismatch로 commit/observe 실패 |
| 16 | rolled-back source + capture commit | 같은 TX 원자성으로 둘 다 rollback; 누출이면 failure |
| 17 | source commit/root finalize 누락 | deferred fence COMMIT 실패, 원장 불변 |
| 18 | observation expires | 410 new observation, partial 설치 없음 |
| 19 | missed R | complete tree diff accept, R+1 요구 안 함 |
| 20 | 다른 장치 download 중 commit | pinned old coherent target 유지, client lineage guards 별도 |
| 21 | same R 다음 date | cold reuse + 새 hot/context, old hot reject |
| 22 | registry 변경 | supported compatibility 검증, unknown은 block |
| 23 | object publication 전 crash | old complete authority |
| 24 | manifest publication 중 crash | old accepted, staged는 권위 아님 |
| 25 | pointer 직전 crash | old, 새 ticket 검증 후에만 재게시 |
| 26 | pointer 직후 crash | new complete 또는 verified previous, no partial |
| 27 | pending retirement 전 crash | committed marker 남음, POST retry 금지 |
| 28 | frozen B 대상 GC | pin 때문에 삭제 불가 |
| 29 | unknown POST + sync 성공 | unknown 유지, submit success/새 POST 금지 |
| 30 | confirmed POST + cold missing | committed rebuild pending, 성공/retirement 없음 |
| 31 | legacy migration 중단 | old B/format/pins 보존 |
| 32 | restore >25MiB | legacy limit 유지, new chunk contract로만 bounded staging/atomic apply |
| 33 | individually valid leaves·globally invalid | complete index root/closure reject |
| 34 | old client legacy endpoint | 현재 v1 full response·B-2 behavior 그대로 |

추가 controls는 malformed nested Unicode/map keys, raw numeric rounding, idempotency case/combining/NUL, collisions/oversized leaf, wrong object path, context-only no-change, storage pressure, root-pin O(N), pointer commit 동안 logout, MW result/J cleanup crash다. Oracles는 backend 실제 presenters·actual migrated SQLite·native durable store이며 financial Dart 재계산이 아니다.

## 38. 내부 정합성·미해결 구현 proof

다음 12개는 **IMPLEMENTATION PROOF REQUIRED**이며 protocol 선택을 미룬 BLOCKING PROTOCOL DECISION과 구분한다.

1. C1 Python/Dart exact bytes, historical REAL·Unicode·generic policy supported vectors.
2. Trigger/admission/migration/bootstrap·direct writer/cascade coverage와 deferred fence COMMIT 동작.
3. Global F catalog·reverse closure completeness, incremental Patricia root와 full rebuild equality.
4. B+tree split/delete/frontier diff의 빠짐없는 old/new membership와 bounded update amplification.
5. Synchronous root/aggregate 유지가 기존 금융 response/rollback 결과를 바꾸지 않음.
6. Same-read-view hot/control·terminal guard·lease atomic pin과 object path authorization.
7. Lease/GC/refcount bookkeeping이 normal refresh에 hidden O(N)을 만들지 않음.
8. Android SQLite pragmas/VFS·commit fence·power-loss·I/O error·previous recovery.
9. Legacy v7/full baseline materialization·old B/J/pending·migration/rollback parity.
10. Chunk restore/MW resource limits·backup·idempotent receipt·one transaction·epoch 전이.
11. Backup/artifact 30개 보존·GC/storage exhaustion·frozen object repair 실패 처리.
12. 고정 H/D scaling·full gzip 비교·HTTP RTT/byte 계측·실기기 post-T6.6 gate.

현재 **BLOCKING PROTOCOL DECISION 0, 필수 제품 결정 0**이다. Restart epoch rotation, synchronous finalizer, B+tree leaves/Patricia facts, single local SQLite store, read-only observation POST, byte-preserving base64 transfer, explicit large-restore dependency를 선택하여 명세 공백을 남기지 않았다. 구현 증명이 실패하면 해당 구현/rollout을 차단하고 이 명세의 변경을 별도 감사받아야 한다. 완성 판정은 아직 구현되지 않은 알고리즘이 이미 안전하다는 주장이 아니다.

잔여 위험은 auth-session SQLite database-is-locked, metadata BEGIN IMMEDIATE contention, 미래 registry drift, backend detailed-payment 중복 계산, standalone backup/완전 복구의 O(N), base64/여러 tree RTT의 상수 비용이다. 기존 이슈를 해결했다고 주장하지 않는다. 압축·history paging·다른 journal mode·epoch 외부 anchor는 별도 승인/검증 대상이지 이 설계에서 활성화한 기능이 아니다.

## 39. 이번 변경 검증·안전성

수정은 이 문서, compact symbolic protocol examples, C1 scalar vectors뿐이다. Source/schema/API/trigger/constraint·T6.6B 계약을 대조하고, 예제 required fields/echo/base-target refs·error actions·state machines·legacy/order·pending/J·복잡도 조건을 검토했다.

실제로 실행한 검증:

| 검증 | 결과·증거 한계 |
| --- | --- |
| 12개 symbolic request/response | required shape/echo/동일 hash label의 Ref·Target 일치/R 순서/context/15분 lease/error action 모두 PASS. 상징 hash의 암호학적 재계산이나 새 endpoint 실행이 아님 |
| C1 scalar vectors | Python strict UTF-8에서 정상 8개·malformed surrogate 3개 PASS, 실제 UTF-8 길이/SHA와 composed/decomposed 구별 확인. Dart codec 구현 증명은 미래 gate |
| SQLite :memory: primitive | 3.45.1에서 미finalize commit 거부·정상 commit·context 누락·rollback·cascade capture·finalizer 뒤 write 거부 6개 PASS. 새 migrated capture 구현/33개 writer 완전성 증명은 아님 |
| source/문서 | 실제 11 table/12 projection, 33 trigger event 조합, 39개 절/25 invariant/34 negative 계획, 상대 link 존재 점검 |
| backend 기존 targeted | 아래 pytest **150 passed, 442 subtests passed**, 125.41초. Starlette의 httpx TestClient deprecation warning 1개 |
| frontend | `npm run build` PASS(1.20초) |
| Ruff | `backend/app backend/tests scripts` PASS |

실행 명령(개발 checkout, synthetic resources만):

```bash
cd /home/hjkerman/codex/money-note/backend
../.venv/bin/python -m pytest -q tests/test_authoritative_state.py tests/test_snapshot.py tests/test_snapshot_export_metadata.py tests/test_versioned_migrations.py tests/test_offline_reconciliation.py
cd /home/hjkerman/codex/money-note/frontend
npm run build
cd /home/hjkerman/codex/money-note
.venv/bin/ruff check backend/app backend/tests scripts
.venv/bin/python /tmp/money-note-t66c-spec-check.py
git diff --cached --check
```

`/tmp/money-note-t66c-spec-check.py`는 이번 문서 검토용 disposable 검사이며 제품/테스트 suite에 추가하지 않았다. 영속 입력은 두 JSON fixture와 이 명세다. 재부팅 후 임시 checker/log는 사라질 수 있으며 그 자체를 영구 재현 도구라고 주장하지 않는다. Full backend/Flutter/Android suite·실기기·새 endpoint/crash/power-loss protocol 시험은 **미실행**이다. 문서 전용 작업에서 이들을 통과했다고 주장하지 않는다.

Production DB/API/credential/.env/서비스에 접근하지 않았다. 새 migration/endpoint/segmented storage/delta/압축은 구현·활성화하지 않았고 APK 설치·배포도 없다. T6.6D/E 구현과 독립 T6.6C 감사는 시작하지 않았다. 다음 gate는 **별도의 독립 protocol 설계 감사**다.

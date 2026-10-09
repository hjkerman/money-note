# T6.6B — Hot/Cold authoritative state 분리 설계와 정확성 계약

## 1. 판정·범위·표기

**T6.6B DESIGN COMPLETE — READY FOR INDEPENDENT DESIGN AUDIT**

이 문서는 구현 승인이 아니라 독립 설계 감사의 입력이다. 권고는 **D: versioned content-addressed Snapshot segments + C: 재사용 가능한 완전한 로컬 cold 저장소**다. A의 lossless transport compression은 별도 선행 후보이고, B의 history paging은 독립 UI 과제다. 현재 제품에는 이 분리·변경 추적·segment 저장·새 root가 구현되어 있지 않다.

표기를 다음과 같이 구분한다.

- **CURRENT:** 시작 commit에서 소스로 확인한 동작.
- **PROPOSED:** 향후 구현에 요구하는 설계·안전 조건. 이번에 활성화하지 않는다.
- **ALTERNATIVE:** 비교 가능한 다른 방안.
- **REQUIRES DECISION:** 보수적 기본값을 바꾸는 제품 결정 또는 별도 기술 계약 승인.
- **UNPROVEN:** 설계 감사·prototype·failure injection·실측으로 아직 입증해야 할 부분.

시작 branch `main`, HEAD/main/origin/main/실제 remote main은 모두 `45ee6fb32ee33b236fc366b0931400d0d31b8f0f`, working tree는 clean이었다. 이번 변경은 문서뿐이다. 운영 DB·API·설정·credential에 접근하지 않았고 배포·APK 설치·제품 실행 경로 변경도 없다. 과거 T6.5/T6.6A 감사 보고서를 재작성하거나 새 독립 감사로 주장하지 않는다.

규범 원본은 [architecture.md](architecture.md)의 `서버 authority와 클라이언트 신뢰 경계`와 [domain-model.md](domain-model.md)다. [offline-mode.md](offline-mode.md), [security.md](security.md), [runbook.md](runbook.md)의 복구 계약도 보존한다. 이 문서의 미래 제안이 현재 wire/storage 계약을 암묵적으로 변경하지 않는다.

## 2. 측정 기준선과 해결해야 할 문제

아래는 새 T6.6B 실측이 아니라 **commit된 [T6.6A 보고서](t66a-payload-attribution.md)와 [aggregate](benchmarks/t66a/attribution.json)의 HOST/synthetic 증거**다. Seed 1234, 평가일 2026-10-05, UTC+540분, synthetic principal 1, 현행 registry, 동일 active 구성을 사용했다. 실기기 결과가 아니다.

| fixture | ledger / current / archive | bundle bytes | Snapshot bytes | typed state bytes | durable baseline bytes |
| --- | --- | --- | --- | --- | --- |
| current-like | 376 / 105 / 271 | 306,370 | 218,421 | 87,661 | 290,225 |
| 1k | 1,000 / 105 / 895 | 653,317 | 565,368 | 87,661 | 637,172 |
| 5k | 5,000 / 105 / 4,895 | 2,889,309 | 2,801,359 | 87,661 | 2,873,163 |
| 10k | 10,000 / 105 / 9,895 | 5,684,312 | 5,596,362 | 87,661 | 5,668,166 |
| confirmed-heavy 600 | 1,200 / 1,200 / 0 | 1,696,801 | 716,501 | 980,012 | 1,483,861 |

10k에서 Snapshot은 98.45%, ledger table 귀속은 5,587,084바이트다. 잠재 cold **9,891행의 row object**는 5,516,500바이트(97.05%)다. Archive 전체 9,895행과 다르며 active payment member/active recurring child를 제외한 분석 후보다. 이는 삭제 허가가 아니다.

| 10k HOST 단계 | T6.6A median | 포함 관계·해석 |
| --- | --- | --- |
| backend 요청 경계 | 1,348.5ms | construct·prepare·middleware 등을 포함 |
| construct / 내부 Snapshot export | 1,138.2 / 557.6ms | 서로 더하지 않음 |
| prepare / 내부 JSON render | 191.1 / 55.9ms | 서로 더하지 않음 |
| parser + typed candidate | 1,970.1ms | 모든 client admission 단계 포함 |
| raw-money / Unicode / presence-types | 538.226 / 18.599 / 202.508ms | parser 내부 |
| Snapshot-authority-relationships | 985.407ms | parser 내부, hash와 관계 검사의 합성 범주 |
| durable publication | 269.7ms | 전체 baseline encode·flush·검사·rename 경로 |

개별 median을 더해 end-to-end 실측으로 만들지 않는다. 이전 통합 감사의 10k 3,996.0ms는 별도 실행이다. 7,479,394바이트의 과거 10k는 typed entries 2,502개인 다른 구성으로, 이번 104개 fixture와 교환할 수 없다. 주 fixture의 기술적 회귀식 `body ≈ 95,265 + 558.882 × ledger_rows`도 고정 hot 구성에만 해당한다.

**목표:** 초기 설치·전체 복구는 O(N)을 허용하되, 고정된 hot 구성과 작은 실제 변경에서는 backend 읽기/변경 발견, 전송, client 검증, durable publication 모두가 전체 history N에 반복 비례하지 않게 한다. UI archive 숨김이나 압축 하나만으로 달성했다고 표현하지 않는다.

## 3. CURRENT 경로와 소스 근거

| 책임 | 실제 소스·함수 | 확인한 현재 계약 |
| --- | --- | --- |
| coherent bundle | [authoritative_state.py](../backend/app/services/authoritative_state.py): `_construct`, `_prepare`, `_terminal_guard` | 동일 read view·고정 평가 context, 원 credential, 별도 terminal freshness guard, bounded rebuild, all-or-nothing |
| wire model | [authoritative_schemas.py](../backend/app/authoritative_schemas.py): `AuthoritativeState`, `AuthoritativeProjections` | bundle v1, principal/authority/Snapshot/12 projections |
| full Snapshot | [snapshot.py](../backend/app/services/snapshot.py): `_export_snapshot`, `snapshot_state_fingerprint`, `_replace_snapshot_tables`, `restore_snapshot` | 11개 전체 table, v7 manifest/정확한 canonical SHA, replace·FK·복구 검증 |
| DB identity | [db.py](../backend/app/db.py), [db_migrations.py](../backend/app/db_migrations.py) | DB version 4; authoritative row trigger revision; migrated partial UNIQUE 등 |
| 금융 계산 | repositories/entries·panels·cash_flows, services/summary·card_payment_reads·card_payments·month | backend가 계산·선택·분류·할당·마감을 소유 |
| mobile admission | [authoritative_bundle.dart](../mobile/lib/src/authoritative_bundle.dart): `AuthoritativeBundle.decode` | UTF-8, raw token/duplicate key, JSON, Unicode, required/type, money, Snapshot/authority/관계, freeze, typed |
| raw 구조 검증 | [authoritative_snapshot_validation.dart](../mobile/lib/src/authoritative_snapshot_validation.dart), [authoritative_bundle_canonical.dart](../mobile/lib/src/authoritative_bundle_canonical.dart) | hashes, metadata, raw identity/reference/동일 필드, N4; 금융 projection 재계산 아님 |
| normal acquisition | [coherent_refresh_coordinator.dart](../mobile/lib/src/coherent_refresh_coordinator.dart): `acquire`, `_acquireBundle` | 1 bundle GET; candidate/envelope 동일 응답; ticket/auth/request/mutation guards |
| 게시·설치 | [app_state.dart](../mobile/lib/src/app_state.dart): `_refreshAuthoritativeState` | mode/lineage lock → complete baseline → guarded durable publish → eligible pending retirement → 전체 state 설치 |
| baseline | [offline_data.dart](../mobile/lib/src/offline/offline_data.dart): `OfflineBaseline` | schema v4, typed state + 전체 Snapshot + fingerprint + defaults + optional resolved reconciliation ID |
| 저장·lineage | [offline_store.dart](../mobile/lib/src/offline/offline_store.dart): `replaceBaseline`, `_writeJsonAtomic`, `recoveryLineageFingerprint` | whole JSON temp flush/readback/guarded rename; whole baseline lineage hash |
| provisional view | [offline_projection.dart](../mobile/lib/src/offline/offline_projection.dart): `OfflineProjection.from` | frozen B의 typed state에 input-only J를 임시 반영 |
| 서버 조정 | [offline_reconciliation.py](../backend/app/services/offline_reconciliation.py): `apply_mobile_wins` | 검증한 전체 B 복원 + ordered J 재생을 단일 transaction으로 commit; 별도 pre-server artifact |
| 별도 백업 | [local_snapshot_repository.dart](../mobile/lib/src/local_snapshot_repository.dart), AppState `saveLaunchSnapshot` | launch/foreground의 별도 full Snapshot, 최근 30개; normal 금융 GET 수와 분리 |

CURRENT OfflineBaseline v4는 envelope의 revision/evaluation_date를 별도 필드로 저장하지 않는다. Snapshot fingerprint와 typed context를 보존한다. 미래 manifest의 revision을 현행 baseline에 이미 저장한다고 가정하면 안 된다. 현재 local lineage fingerprint는 server state fingerprint와도 다르다.

운영 모델은 한 owner·한 장부지만 DB의 금융 row에는 사용자별 격리가 없다. 여러 active principal 생성 가능성을 배제하지 않는다. 미래 cache는 인증 principal에 격리하고, 별도의 dataset identity를 서버가 제공해야 한다. 같은 row ID나 같은 숫자 user ID만으로 다른 서버·DB·세션의 자료를 합치면 안 된다.

## 4. 신뢰 경계와 전체 소비자 inventory

CURRENT/PROPOSED 모두 backend가 Summary·judgment·discount·payment grouping/allocation·month-close·recurring/fixed 실행의 authority다. 모바일은 Category A/B의 표현·구조·identity·복구·generation·publication을 검증한다. Category C 금융 결과를 다시 계산하지 않는다. Hash는 byte/content commitment이지 서명·금융 계산 정확성 증명이 아니다.

다음 11개 표는 `SNAPSHOT_TABLES`와 일치한다. `B/J`는 frozen authoritative baseline과 input-only journal, `MW/SW`는 Mobile Wins/Server Wins다. 모든 raw table은 직접 UI 사용 여부와 무관하게 **전체 B 복원, MW, 백업·Snapshot integrity**에 필요하다. SW도 새 완전한 B를 게시하기 전 기존 B/J를 보존해야 한다.

| Snapshot table | 의미·성장 | 현재/과거·금융 의존성 | Offline·조정·복구 소비자 | UI·mutation 소비자 | integrity·분류 후보 |
| --- | --- | --- | --- | --- | --- |
| ledger_entries | 실제/예정 카드 원장, N 증가 | current·planned + archive의 active 결제/확인 child; 수정된 날짜는 ownership 아님 | B 전체, 카드/예정확인 J, MW source/epoch 보존 | 입력·archive·payment·confirm/edit/delete/month-close | id/payment_key/source+epoch; hot 관계 closure, 나머지 reusable cold |
| monthly_panels | fixed/frozen/claim/family, 미삭제 큐 증가 | month 필드만으로 cold 불가; fixed와 모든 claim/family/frozen이 현재 reserve/공제에 영향 | typed panel로 estimate, raw fixed→cash 소유, B/MW 전체 | panel CRUD·확인/취소·일괄정산 | id/type/fixed FK·epoch; 대부분 HOT/SHARED |
| cash_flows | 입출금 전체, 누적·미래 행 | 전체 과거≤today가 cash position, fixed/payment 연결, future cutoff | cash/fixed J, raw cash 소유, B/MW 전체 | current cash·과거조회·삭제·정산 | id/flag/date/exact money; 연결행 SHARED, 나머지 cold + 서버 aggregate |
| card_payment_batches | 결제 작업 batch | active 문맥; 새 마감이 이전 batch 계열을 제거 | typed payment estimate, 전체 B 재구성 | 결제 UI·month-close | id/status·active uniqueness; HOT/SHARED, 영구 결제 history라고 가정 금지 |
| card_payment_batch_items | batch와 원장 membership | archive도 current obligation에 필요 | B에서 payment_key/entry ownership 유지 | 결제·이월·late archive insertion | id, batch/key/entry 관계; active closure SHARED |
| card_payment_events | 실제납부/할인 event | active batch 중심이나 batch NULL 등 구조가 허용하는 행도 보존 | B 복원·event/cash/allocation 관계 | 결제 기록·취소·idempotent retry | id·전역 non-null idempotency BINARY UNIQUE; SHARED, 날짜만으로 cold 불가 |
| card_payment_allocations | event→payment_key 원금/할인 할당 | 현재 remaining이 과거 원장과 연결될 수 있음 | B 복원·event 총액/연결 검사 | 결제·취소·할인 override | id/event+key/금액/소유; SHARED, 관련 event와 함께 변경 |
| card_payment_deferrals | stable key 이월·원위치 metadata | 과거 사용월과 다음 payment_month 연결 | B의 되돌리기 정보 보존 | defer/cancel·결제 UI | key unique/원장·batch context; SHARED |
| notification_candidate_registrations | 알림 입력 dedup 등록 | 오래된 key도 재등록 방지; 마감 때 target ID rewrite | Offline 등록 중복 방지·J/MW에 필요 | 알림등록·ledger/claim/family 생성 | registration_key PK, target domain; 삭제된 target의 등록이 남는 것은 허용. 전체 FK로 강화 금지; lookup-index SHARED |
| app_settings | 비민감 설정·월별 policy/profile | 월별 key 이력 증가, 현재 계산과 과거 policy 해석 | supported Offline descriptors/defaults·B/MW | settings·정책·마감·Summary | key unique/money-string/민감 key 제외; active HOT, 이력 SHARED/COLD, registry CONTROL |
| app_labels | 웹/공유 화면 label 사전 | 보통 작지만 강제 크기 상한 없음; 금융 합계 입력 아님 | B/MW 전체 복원; mobile typed projection의 직접 입력은 아님 | `/api/labels`, frontend 표시·share 제목·label 변경 | key unique/Unicode; CONTROL/SHARED |

다음 12개는 `AuthoritativeProjections`의 정확한 필드다. 모든 typed projection은 동일 authoritative observation의 설치·baseline 구성에 참여한다. 작은 출력이어도 backend 입력이 작은 것은 아니다.

| Typed projection | raw/backend 입력 | 성장·current/역사 의존성 | Offline·UI 소비 | mutation/조정·복구 | 경계·refresh trigger |
| --- | --- | --- | --- | --- | --- |
| month_close_status | ledger/planned/panels/settings, 서버 날짜·timezone | 목록은 미확인 source 수; 날짜만 바뀌어도 변함 | 마감 안내·Offline 상태 기준 | confirm/month-close 후 SW/MW fresh install | HOT, eligibility/order는 서버 소유 |
| entries | current ledger + policy/allocation | 미마감 과거 current 포함; H 상한 없음 | 입력·현재 카드·J provisional view | 카드 CRUD·planned 확인·마감 | HOT, raw ID/필드 대응은 A/B |
| panels | monthly_panels + cash/family policy | fixed + 전체 미삭제 큐; 월별 bounded 아님 | 고정·Claim·Family·Frozen, J | panel CRUD·확인/정산 | HOT/SHARED, 원금과 서버 할인 구분 |
| summary | current/planned/panels, 전체 cash, active payment, settings | 결과 고정 형태; historical cash dependency | 잔고/지출가능액·보수적 estimate | 거의 모든 금융 변경·평가일 | HOT, aggregate 계산 backend |
| card_payment_status | active batch/items/events/allocations/deferrals + ledger/policy | active obligations 수; 과거 원장 포함 | 결제 화면·Offline 기준금액 | payment·defer·마감·정책 | HOT, exact grouping/remaining 재계산 금지 |
| judgment | Summary + 월 cash + 최근 마감월 counts/settings, 코드의 CATEGORY_LABELS | 작은 출력, history counts 조회 있음 | 회계감사/판단 표시, Offline provisional | 관련 금융/settings/context | HOT, 금융 판단 backend; app_labels와 다른 사전 |
| confirmed_planned_entries | planned source + source/epoch 소유 child | 평가월 source 수; child는 archive/NULL-date 가능 | 확인 목록·J | 확인/취소·child edit/delete·마감 | HOT + raw child closure SHARED |
| cash_flows | 직전월 시작~평가월 말 raw cash | 기간은 제한, 행 수 무제한; 전체 잔고의 대체물 아님 | cash 화면·J provisional | cash/fixed/payment·월 이동 | HOT, 과거 cash는 별도 B에 보존 |
| settings | 비민감 app_settings | 월 policy/profile 이력 증가 가능 | UI설정·Offline기준 | settings/정책·마감 | HOT/CONTROL 현행 전체전달; 미래 key별 분류 별도 승인 |
| owner_discount_month | 월별 owner 정책/registry + 관련 ledger | 현재 결과·per-entry projection 수 의존 | 할인 표시·Offline descriptor | 카드·할인 override·정책/context | HOT/CONTROL, backend evaluation |
| family_discount_month | 월별 family 정책/registry + panels | family 큐 증가에 영향 | Family·Offline descriptor | family/정책/context | HOT/CONTROL, family와 핵심 원장 결합 확대 금지 |
| transit_discount_profile | 해당 월 profile setting/registry | 작은 descriptor; history setting 별도 | 교통 표시·supported Offline estimate | profile 변경/context | HOT/CONTROL, registry 호환은 A/B |

11/11과 12/12의 coverage는 UI 목록만의 분리가 아니라 저장·복원·조정 소비자를 포함한다. auth users/sessions, audit, reconciliation receipt/operation-ID 기록은 Snapshot 11개에 **없다**. 그렇다고 미래 change tracking·receipt 안전성 검토에서 무시할 수는 없다.

## 5. Hot 정의와 성장 한계

PROPOSED `H`는 calendar 현재월 행만이 아니라 **현재 서버 projection 입력·참조의 관계 closure**다.

| Hot 구성 | source·업데이트 trigger | 크기·metadata |
| --- | --- | --- |
| 현재 financial view | 위 12개 typed projection; 모든 관련 write, 평가일/월/timezone/registry change | 보통 작지만 entries·confirmed·payment·panels는 무상한. principal/context/view identity에 결합 |
| raw working records | current/planned ledger, active obligations, active recurring child, fixed-linked cash, deferrals | source/epoch/payment key의 직접·역참조 포함; archived라도 hot 관계일 수 있음 |
| 정책·설정 | 현재 지원 registry/월 설정/defaults, labels | raw history와 compatibility metadata를 구분; registry change는 금융 row revision 없이도 가능 |
| 서버 aggregate | authoritative cash position/최근 마감 통계 등 | backend가 유지·계산한 값, raw Snapshot을 대체하지 않음 |
| dedup lookup | registration key·payment key·idempotency·source epoch의 persistent index | index 전체를 매번 메모리에 올리는 설계 금지; 필요한 lookup만. 완전성은 accepted root에 결합 |

Hot 응답에는 평가 date뿐 아니라 계산 의미를 식별할 context identity가 필요하다. CURRENT는 backend 내부 timezone을 고정하지만 wire에 timezone 전체를 독립 검증 witness로 제공하지 않는다. 미래 context/version marker는 재사용·무변경 판단용이지 모바일 month-close 재실행용이 아니다.

**보장하지 않는 것:** hot-state row 수의 절대 상한, 모든 refresh O(1), current-month만 있으면 모든 계산 가능하다는 주장. Active 한 달에 100k행이 있으면 H 자체가 크다. 서버가 전체 hot projections를 보내는 첫 설계는 O(H)이며 H 내부 delta는 T6.6C의 별도 판단이다.

## 6. Cold 정의·가변성·교차 경계

PROPOSED cold는 **현재 view에 원문을 반복 전달할 필요가 적고, 동일 content가 authoritative manifest에서 재사용 가능하다고 지정된 raw 자료**다. 과거 날짜나 archive라는 label만으로 불변·삭제 가능 판정을 하지 않는다.

| 후보 | CURRENT 가변성·교차 관계 | 미래 필요한 표현 |
| --- | --- | --- |
| archived ledger | `entries.update/delete`가 과거 변경 허용; closed-month 신규 입력은 직접 archive; 확인 child·결제 member일 수 있음 | 모든 행 durable 보존; 활성 관계는 hot 참조/작은 raw closure; 나머지 cold object 재사용 |
| 오래된 cash | 누적 잔고에 영향; 삭제 가능, payment/fixed 소유 시 별도 제약; 미래 발생일도 존재 | 서버 exact aggregate + 참조 대상 raw + 전체 cold 원문 |
| 종료한 recurring epoch | source ID·완전한 epoch·stable payment key가 ownership 증거; 날짜/제목 아님 | 과거 child와 현재 source의 연결, 삭제 시 metadata 해제까지 추적 |
| payment 계열 | 현재는 새 batch 구성 때 이전 events/allocations/items/batches 제거. 영구 archive가 아님 | 실제 잔존 행 전부 보존, delete/cascade도 change discovery에 포함 |
| 과거 settings/policy | 해당 사용월 정책이 과거 계산에 영향; 일부 설정 변경/정리 가능 | raw 이력과 current descriptor/registry 분리, 영향 projection 서버가 재생성 |
| registrations | target 삭제 후 key가 남아 dedup 의미 유지 | 전체 durable key index, target 생존을 무조건 요구하지 않음 |

**특별한 현재 변경:** [month.py](../backend/app/services/month.py)의 `close_current_month`는 current row를 archive에 **새 ID로 INSERT한 후 원래 행 DELETE**하며 stable payment key/epoch를 유지하고 registration target을 새 ID로 바꾼다. Future delta는 이를 단순 book_section UPDATE나 동일 row ID로 표현하면 안 된다. Date 변경은 month partition 간 이동, source 삭제는 FK/epoch 해제, payment 취소는 cash/allocation 변경을 동반한다. 재개방을 위한 별도 canonical reopen 기능은 이 검토에서 확인하지 않았지만 명시적 Snapshot restore/reset/Mobile Wins가 과거 전체를 교체할 수 있다.

| 교차 의존성 | 필요한 것 | 필요하지 않은 것 |
| --- | --- | --- |
| 현재 cash position ← 모든 과거≤today cash | backend authoritative exact aggregate, cutoff·future-date index; raw history는 복구용 | 모바일 full-history cash 재합산을 authority로 사용 |
| active payment ← archive ledger/event/deferral | backend current projection + stable key/raw 관계 closure | 독립 Dart grouping/allocation 엔진 |
| confirmed source ← archived child | source+epoch→child index와 실제 raw child; raw 필드 대응 | 제목/금액/날짜 유사성으로 소유 추측 |
| 최근 마감 판단 ← archive counts | 서버 월별 authoritative count/조회, last_closed context | 모바일 archive 전수 scan으로 judgment 재계산 |
| settings/history policy ← 과거 사용월 | 서버 policy 해석 + supported descriptor 및 원문 복구 | registry hash만으로 금융 정확성 증명 |
| MW Apply(B,J) ← 모든 table | 완전한 frozen B를 materialize할 수 있는 segment 집합 | 최신 hot view를 과거 B 대신 사용 |

## 7. Offline과 완전한 Snapshot 계약

CURRENT `OfflineProjection.from`은 baseline typed state를 복사하고 카드·cash·fixed·planned 확인의 input-only J를 임시 반영한다. 정책 descriptor를 지원하지 못할 때 보수적 estimate도 사용한다. full raw history를 canonical 금융 엔진으로 재생하는 것이 아니다. 서버 reconciliation이 확정 결과를 결정한다.

PROPOSED는 다음 네 가지를 분리한다.

1. **완전한 논리 Snapshot:** 11개 table의 정확한 행/관계, policy metadata, v7 manifest 의미가 모두 존재한다.
2. **물리 저장:** hot document + immutable raw segments + persistent structural indexes + generation manifest일 수 있다.
3. **한 번의 수신 bytes:** 바뀐 자료와 reuse evidence만일 수 있다.
4. **메모리 materialization:** hot view와 필요한 raw lookup만일 수 있다.

부분 hot 응답을 현재 v4 `OfflineBaseline`의 완전한 Snapshot으로 속여 넣지 않는다. Offline 진입 시 accepted B의 모든 raw content는 이미 durable하게 로컬에 있어야 한다. 예상치 못한 네트워크 단절·restart에서도 서버 없이 frozen B/J/필요 lookup을 사용할 수 있어야 한다. 신규 장치의 전체 초기화 중에는 incomplete cache를 Offline-capable baseline으로 게시하지 않는다.

MW는 현행 `Apply(B,J)`이며 `Apply(S,J)`가 아니다. Future adapter는 pinned B의 segments에서 **정확한 complete v7 Snapshot을 materialize**하고 legacy fingerprint/manifest를 계산한 뒤 기존 ordered J와 조정 identity를 보존한다. SW는 기존 B/J/artifact 보존·확인 및 새 baseline 게시 후에만 정리한다. `resolved_reconciliation_id`의 double-replay 방지도 유지한다.

현재 가능한 Offline 기능을 모두 보존하는 것이 기본값이다. 새 history UI 전 페이지를 Offline에서도 서버와 동일하게 계산한다는 **추가 제품 약속**은 하지 않는다. Raw 복구 data의 완전성과 이미 제공하던 Offline 화면/입력 기능의 보존은 필수다. 디스크 손상으로 frozen B의 필요한 segment를 잃으면 J를 새 B로 옮기지 않고 recovery blocked로 남긴다.

## 8. 대안 비교와 결정 행렬

평가는 설계 비교이며 실행 성능 보증이 아니다. A/B도 안전한 중간 단계로 유효하지만 최종 steady-state 목표를 단독으로 충족하지 못한다.

| 기준 | A: full bundle + 압축/집중 검증 개선 | B: UI history 분리 + full B 유지 | C: reusable cold store + 변경만 교체 | D: versioned segments + coherent manifest |
| --- | --- | --- | --- | --- |
| 정확성 복잡도 | 낮음, 기존 boundary | 낮음~중간, paging 일관성 추가 | 높음, 누락/전이/관계 증명 필요 | 높음, 명시적 root/closure/전이 계약 |
| Offline 호환 | 현행 유지 | 현행 유지 | 완전 cold pin이면 유지 | 완전 generation pin이면 유지 |
| Snapshot 복구 | 그대로 | 그대로 | adapter/whole hash 필요 | on-demand full materialization 필요 |
| pending/reconciliation | 그대로 | 그대로 | atomic generation + pinned B 필요 | 같은 조건, root 전이 증거 추가 |
| backend 계산 절감 | 압축만으로 없음 | full Snapshot이면 없음 | tracking 없으면 없음 | transaction tracking/aggregates 구현 시 가능 |
| network 절감 | 실측 gzip/br 매우 큼 | full Snapshot이 대부분이면 작음 | 변경량 기반 가능 | changed leaf/path 기반 가능 |
| mobile 검증 절감 | 아직 full N | full B면 여전히 N | accepted cold 검증 재사용 필요 | changed bytes + affected constraints 검증 |
| durable rewrite 절감 | full B 그대로 | full B 그대로 | 객체 재사용 가능 | immutable object + small root switch |
| 구현 복잡도 | 낮음~중간 | 중간 | 높음, ad-hoc cache 위험 | 높지만 identity/완전성 명시 가능 |
| migration | transport 호환성 검증 | UI/API 호환 | storage/protocol 전이 필요 | versioned storage/sync 전이 필요 |
| 장애/복구 | 현행 + codec limits | paging cache 별도 | cache miss/partial update 다수 | root atomicity·pin·GC·full resync 필요 |
| scalability | full N CPU/write | baseline N 유지 | 단순 whole manifest/hash면 N 남음 | 조건 충족 시 H+변경 closure+tree paths |
| backward compatibility | gzip capability 검증; Brotli 미보장 | 기존 full 소비자 유지 가능 | 명시적 capability 필요 | 기존 full v1/v7 경로 병존 필요 |
| 운영 위험 | 압축 CPU/메모리/negotiation | stale/중복 history page | cache invalidation·영속성 | tracking coverage·객체 수명·schema upgrade |

**권고:** D의 명시적 versioned root/segment 계약으로 C의 local reuse를 구현하는 장기 설계. A는 먼저 별도 승인·검증 가능한 전송 개선이고 B는 사용자 history 기능 개선으로 병행 가능하다. C를 filename/mtime/전역 revision만으로 구현하는 방안은 기각한다. D도 flat manifest를 매번 전송하거나 content hash를 매번 full scan해서 만들면 목표 실패다.

## 9. Full compression을 포함한 공정한 비용 비교

| 10k baseline/가상안 | entity bytes | backend | client validation | durable write |
| --- | --- | --- | --- | --- |
| CURRENT full identity | 5,684,312 | full construction | full decoded N | full 5,668,166-byte B |
| ALTERNATIVE full gzip6 | 108,916, 실험 실측 | 위 비용 + codec | **해제 후 동일 N**, Unicode/돈 검사 유지 | 동일 full B |
| ALTERNATIVE full Brotli4 | 43,033, offline 실측 | 위 비용 + codec | 동일 N; 현재 IOClient 지원 미확인 | 동일 full B |
| PROPOSED hot-only | 미측정; typed state 87,661B는 참고이지 유효 응답 크기 아님 | H 계산 + tracking 전제 | hot + control + raw closure | 완전 cached cold가 있을 때 작은 generation |
| PROPOSED hot+changed-cold | 미측정; hot/control + changed segments + proofs/framing | 변경발견 O(N)이면 이득 제한 | 변경 leaf·affected constraints·paths | 새 objects + manifest; full rewrite 없음 |

T6.6A disjoint view에서 cold row object를 제외한 합은 `5,684,312 − 5,516,500 = 167,812B`다. 이는 기존 raw remainder·typed values·control/structure 합계이며 **그대로 유효한 hot protocol body가 아니다**. 제거한 row의 comma, 달라질 manifest와 root, 관계 closure/segment proof 비용도 새로 정의해야 한다. 이 약 168KB를 raw full의 5.6MB와만 비교하면 과장이다. **108.9KB full gzip보다 raw 후보가 더 클 수도 있다.** 양쪽 모두 compression을 적용한 실측 비교가 미래 gate다. Category별 압축 크기를 더해 full 압축 크기로 취급하지 않는다.

다양성 10k는 raw 6,180,091 / gzip6 568,847 / Brotli4 477,248B다. 극도로 반복되는 10k의 98~99% 감소를 실제 사용자 공통 보장으로 쓰지 않는다. HOST gzip6 encode/decode 약 28.13/3.31ms, Brotli4 15.24/1.79ms, Dart gzip 해제 별도 약 5.04ms이며 phone 비용이 아니다. Compression은 backend full-ledger scan·Snapshot export/hash·client relationship checks·baseline encode를 없애지 않는다.

CURRENT local Uvicorn은 Content-Encoding 없음, 실제 Dart transport는 Accept-Encoding gzip이었다. 운영 proxy 설정은 미접근이다. Brotli 지원·압축 배포·적정 level은 별도 검토 사항이다.

## 10. PROPOSED identity와 cold reuse 계약

아래는 **의미 요구사항**이지 승인된 wire 필드명/schema가 아니다.

| identity/marker | 필요한 의미 |
| --- | --- |
| server + dataset epoch | endpoint 신뢰 대상과 DB 논리 세대. DB 교체/백업 복구/revision reset으로 과거 ID/R이 재사용되어도 분리. CURRENT에 dataset epoch 없음 |
| principal + local auth generation | 서버 principal과 현재 선택 user/session lineage. 재인증 뒤 과거 in-flight 응답 게시 금지 |
| schema/sync/storage/validator version | leaf 해석·root canonicalization·검증 결과 재사용 가능 범위. bundle/Snapshot/local baseline 축을 혼동하지 않음 |
| policy registry compatibility | 현재 generated registry/descriptor의 지원 범위. 현행 drift 위험을 해결했다고 주장하지 않음 |
| observed revision + evaluation context | revision은 opaque monotonic observation, +1 연속 가정 금지. 날짜/context만 변해도 hot view 변경 가능 |
| raw table roots + complete counts/key ranges | 모든 11개 table의 전체 집합과 중복/누락 검출. 빈 table도 명시적으로 포함 |
| content-addressed segment identity | canonical exact raw rows, table/namespace/columns/version/key range/order를 hash가 결합 |
| projection digest + view root | 동일 관측의 typed sections와 raw state/context를 함께 결합. 금융 계산을 증명하는 digest 아님 |
| validation receipt/index root | 어떤 owner/schema/validator/raw root 아래 구조 검사가 통과했는지 로컬 기록. 서버 인증 증명이 아닌 재사용 근거 |
| durable completeness + generation pointer | 모든 참조 object/index가 게시 전에 검증·저장됨. 파일명·mtime 또는 다운로드 완료 추정으로 대체 불가 |

재사용 조건: **새 authenticated coherent manifest가 동일 segment content identity를 참조**하고, local accepted immutable object가 동일 owner/dataset/version과 exact bytes hash/검증 provenance를 만족한다. Whole-state fingerprint가 바뀌어도 그 segment reference가 같으면 재사용할 수 있다. Whole revision이 같다는 사실만으로 날짜·registry·typed judgment까지 byte-identical하다고 가정하지 않는다.

같은 principal 재인증 시 durable raw content는 fresh metadata·지원 version 확인 후 재사용 가능하지만 auth-generation ticket은 새로 생성한다. 다른 principal은 격리한다. 실제 ledger가 공유되어 보이더라도 자동 cache 결합을 허용하지 않는다. 로그아웃 시 pending/J 처리 및 데이터 삭제 정책은 기존 계약을 유지하며, 이 설계가 자동 삭제를 새로 허가하지 않는다.

## 11. PROPOSED change discovery와 backend publication

CURRENT authoritative_revision은 11개 table INSERT/UPDATE/DELETE trigger로 **행마다** 증가한다. 한 POST가 여러 증가를 만들고 no-op UPDATE도 증가할 수 있다. 어떤 행이 변했는지, delete 이전 키, cold partition generation은 기록하지 않는다. schema/registry/timezone/date와 auth lineage도 같은 축이 아니다.

PROPOSED 변경발견은 full history 비교가 아니라 **금융 mutation과 동일 SQLite transaction에 기록한 변경 정보**를 사용한다.

1. INSERT/UPDATE/DELETE의 table·old/new canonical primary identity와 affected raw keys를 capture한다. cascade, source/epoch 해제, 월마감 copy/delete, registration rewrite, bulk reset, restore, MW, CLI/maintenance writer도 포함한다.
2. Persistent dirty keys/partition generations 또는 ordered bounded change log를 사용한다. Trigger-based capture와 repository-managed capture는 ALTERNATIVE이나, 모든 writer coverage를 입증해야 한다. 누락 writer가 있으면 epoch reset/full rebuild로 명시적으로 막는다.
3. Log 삭제 전 tombstone/old membership이 반영되어야 한다. 같은 key가 여러 번 바뀌면 최종 값으로 coalesce할 수 있지만 base→target 삭제/이동·관계 변화는 잃지 않는다. ID 재사용은 dataset epoch와 source instance 계약으로 구분한다.
4. 새 row와 영향 leaf/index를 갱신하고 persistent root를 계산한다. 내부 tracking/index bookkeeping이 financial revision을 다시 무한 증가시키지 않도록 별도 metadata 영역과 transaction 의미를 설계한다.
5. Manifest의 `R`에 대한 root는 **그 R의 완전한 DB 관측**을 가리켜야 한다. 비동기 root builder가 뒤처지면 published-root R과 live R을 섞어 성공시키지 않는다. 해당 관측의 변경량을 따라잡거나 bounded retry/명시적 retryable failure를 낸다.
6. Auth·schema·registry·evaluation context와 terminal freshness 보증은 B-1 수준으로 유지한다. 동일 R에서 context가 바뀌면 새 hot/view identity를 만든다.

서버가 full table을 scan하여 매번 cold hash를 다시 만든다면 content-addressing을 도입해도 backend O(N)은 남는다. Dirty discovery, hierarchical root update, 계산 입력 축소가 **함께** 필요하다. Old/new database replacement는 기존 R 재사용을 신뢰하지 않고 새 dataset epoch/full-root initialization이 필요하다.

**UNPROVEN:** transactional tracking coverage, root builder race/rollback, migration/bootstrap, log retention과 SQLite 비용은 T6.6C/D에서 prototype·실제 migrated DB negative tests가 필요하다. CURRENT 기능이라고 쓰지 않는다.

## 12. PROPOSED segment와 계층적 무결성

```text
authenticated coherent view identity
  ├─ principal / dataset / versions / R / evaluation context
  ├─ exact typed hot document digest
  ├─ policy / control digest
  └─ complete raw-state root
       ├─ table root × 11 (empty table도 명시)
       └─ persistent range tree
            ├─ unchanged subtree reference → accepted local objects
            └─ changed bounded leaves → exact raw rows + counts/ranges
```

이 구조는 개념안이다. root/leaf serialization을 다음처럼 명시해야 구현할 수 있다.

- Hash 입력은 domain separation, format/version, table/namespace, columns, canonical key/range, row order/count, exact normalized-to-contract value representation을 포함한다. Unicode normalization·trim·case folding·money rounding은 금지한다.
- Rows는 현행 supported raw contract의 모든 필수 필드를 보존한다. leaf마다 required/type/raw-money/duplicate-key/Unicode/domain 검사를 수행한다. Encoder의 replacement로 malformed string을 수선하지 않는다.
- Tree 내부 hash는 ordered child identities, 경계, count를 결합한다. 빠진 leaf, 중복/겹친 range, 다른 table leaf, 빈 table 누락을 검출해야 한다. root만 보내고 임의의 cache 일부를 complete로 간주하지 않는다.
- 전체 P개 leaf 목록을 매번 보내는 flat manifest는 O(P)다. 재사용 subtree reference와 변경 path, count/range proof를 사용하는 persistent balanced tree를 후보로 한다. Parent/child 순서 및 range coverage 검증 규칙을 protocol로 고정한다.
- Leaf는 bounded byte/row size로 분할하여 거대한 한 달 전체를 매번 다시 보내지 않게 한다. 크기와 split/merge 정책은 **UNPROVEN**, 임의 숫자를 성능 보장으로 정하지 않는다. Primary-key 기반 안정 shard와 history month index를 분리하는 방안을 권고한다. Month partition만 사용하면 날짜 이동과 거대 월 문제가 있다.
- 전역 UNIQUE/FK/ownership은 leaf hash로 입증되지 않는다. Accepted persistent identity/reverse-reference index를 root에 결합하고 변경/삭제가 영향 주는 **전체 structural closure**를 검증한다. 동일 leaf 안에서만 ID/N4를 검사하면 안 된다.
- Hash는 authenticated transport가 보장하는 origin을 대체하지 않는다. Forged/rehashed body의 금융 의미를 SHA가 증명하지 않는다. backend compromise를 독립 검출하는 설계가 아니다.

현재 Snapshot raw row order는 ledger `book_section, entry_kind, entry_date, sort_order, id`, panels `month,panel_type,sort_order,id`, cash `occurred_on,sort_order,id`, batches `id`, items `batch_id,id`, events `event_date,id`, allocations `payment_event_id,id`, deferrals `target_payment_month,entry_payment_key`, registrations `registration_key`, settings/labels `key`다. Future full export는 **이 exporter 순서와 SQLite NULL/문자 정렬 의미**를 재현해야 한다. PK leaf 순서로 단순 연결한 자료를 현행 v7 array/hash와 같다고 주장하지 않는다. Full materialization의 sort/merge 비용은 O(N) 이상일 수 있고 ordered index 설계는 별도 검토한다.

## 13. Flat hash와 compatibility 경계 — 중요한 설계 결정

CURRENT Snapshot의 table/data/content hash와 `snapshot_state_fingerprint`는 canonical JSON 전체에 대한 flat SHA-256이다. Canonical JSON은 UTF-8, sorted map keys, compact delimiters를 사용한다. Content hash에는 exported_at/recurring ownership metadata가 포함되고, state fingerprint는 `schema_version`, `range`, `card_charge_policy`, `data`를 결합한다. Principal·typed projections·revision/evaluation date·exported_at를 모두 결합한 hash가 아니다.

**서로 다른 segment SHA를 조합해 기존 whole-JSON SHA를 계산할 수 없다.** 또한 local `recoveryLineageFingerprint`는 전체 baseline JSON의 별도 hash다. 이 세 축을 무조건 매 refresh 재계산하면 mobile/backend N 비용이 남는다.

PROPOSED는 새 **sync root**와 existing full Snapshot fingerprint를 명확히 분리한다. Sync root는 segment-based complete state 및 typed/context를 결합하고 incremental update한다. Legacy v7 Snapshot/hash/ID는 **full export·restore·MW·필요한 전체 검증 시** 정확한 logical B를 materialize하여 계산한다. Sync root를 현행 `state_fingerprint` 필드에 몰래 넣거나 기존 SHA와 같다고 선언하지 않는다.

Materialization은 frozen B가 가진 원래 `exported_at`, `range`, schema/recurring ownership version, policy manifest/covered horizon, table columns와 ordering metadata를 사용해야 한다. 재구성 시점의 새 날짜·registry로 B의 policy를 생성하거나 synced_at를 바꾸면 동일 B가 아니다. 새 현재 관측의 export timestamp가 변하는 것과 frozen recovery identity를 보존하는 것을 구분한다. Empty table의 columns/count도 control에 보존한다.

이는 future **versioned sync/storage compatibility 계약의 명시적 신규 작업**이다. Snapshot v7 완전 export를 유지할 수 있지만, current bundle v1·baseline v4 consumer에 partial Snapshot이나 새로운 root 의미를 넣을 수는 없다. 새 transport/storage discriminator와 legacy adapter의 정확한 형식은 T6.6C 설계·독립 감사 대상이다. 이번에 version을 올리거나 format을 바꾸지 않았다.

Offline journal/metadata의 기존 lineage·reconciliation request identity도 새 manifest digest로 암묵 대체하면 안 된다. Migration은 accepted old B를 전체 검증한 뒤 새 representation을 만들고 logical equality·legacy materialization/hash를 확인하며 이전 generation을 보존한다. 기존 J/pending/finalizing이 있으면 원 lineage를 pin하고 기존 recovery를 완료하거나 감사된 lossless adapter를 써야 한다. 무승인 자동 J 재기준화는 금지다.

**ALTERNATIVE:** full legacy hashes를 매 refresh 유지하는 C는 구현할 수 있지만 O(N) 상한을 인정해야 한다. 모든 refresh에서 현행 flat fingerprint를 즉시 새로 검증한다는 조건을 절대 변경 불가로 두면 최종 scalability 목표와 충돌한다. 권고는 이를 숨기지 않고 새 sync/storage 계약을 독립 승인받는 것이다.

## 14. Structural validation 재사용과 범위

PROPOSED validation 재사용은 “서버를 믿으므로 검사 생략”이 아니다. 동일 immutable bytes가 이전에 accepted 되었고 fresh root가 그 bytes를 참조하며 지원 validator/version이 같다는 조건이다.

| 단계 | 반드시 수행할 검증 |
| --- | --- |
| 모든 manifest/hot refresh | authenticated owner/auth-generation, version/schema, required/type, exact money/raw numeric tokens, duplicate JSON keys, Unicode, authority/context/ticket/mode, root transition/completeness, hot raw references·동일 필드 |
| changed cold leaf | 위 표현 검사 + 모든 raw 필드/domain/PK/secondary uniqueness; hash/count/order/range; previous accepted state와 변경 identity 전이 |
| 변경된 관계 closure | persistent indexes로 cross-leaf FK/ownership/secondary uniqueness/삭제 영향 확인. N4는 전 table non-null key BINARY uniqueness, empty key도 포함 |
| unchanged cold object | 기존 accepted provenance·version/root reference 재사용; 파일을 읽을 때 content hash 검증. 파일명/mtime만으로 통과 금지 |
| full initialization/resync/schema upgrade | 전체 11개 table의 현행 A/B compatibility·관계 검사와 index 재구축; migrated SQLite constraints oracle |
| full v7 materialization/restore/MW | 전체 logical Snapshot 필수 tables/columns/order/count/hash/policy/identity와 actual restoreability; 기존 server validation 유지 |

Persistent index에는 최소 PK, ledger payment_key, source+epoch→child, batch item owner, event+payment_key allocation, event→cash/fixed→cash disjoint ownership, settings/labels keys, registration key, N4 non-null idempotency key가 포함된다. Event allocation 합계·raw cash 금액 대응처럼 기존 A/B의 저장 의미에 속한 검증은 영향 closure에서 유지한다. 이 목록은 금융 할인·remaining·close membership 재계산 허가가 아니다.

재사용 증명은 귀납적으로 구성한다. 처음에는 전체 validated generation을 만든다. 다음 전이에서는 base root를 정확히 식별하고, 바뀐 leaf/path의 old→new 대체 및 삭제·삽입 range coverage를 검증한다. 미변경 subtree의 내용은 이전과 동일하고 새 parent/root에도 결합되어야 한다. Changed keys의 incoming/outgoing references와 모든 관련 UNIQUE 영역을 accepted index에서 찾아 다시 검사한 후에만 새 validation receipt를 만든다. Local index digest는 서버 raw-state root와 같은 hash가 아니라, 그 raw root·validator version에 결합된 별도 derived provenance다. 이 귀납의 영향 closure가 빠짐없다는 입증이 미래 구현 감사의 핵심이다.

**UNPROVEN:** affected closure가 모든 전역 제약을 포함한다는 completeness proof. ID→object 하나만 확인해서 충분하다고 가정하지 않는다. Reverse index 누락·stale index root는 fail-closed/full rebuild다. Registry/validator upgrade가 기존 receipt 의미를 바꾸면 full revalidation 또는 명시적 compatibility proof가 필요하다. Future-registry drift는 기존 미해결 compatibility concern이다.

디스크 bitrot는 별도다. Content-addressed 이름이 실제 파일 불변성을 보장하지 않는다. 초기/restart recovery의 complete-store 검증은 O(N)을 허용하고, session 중 accepted immutable store는 hash-on-read 및 별도 scrub으로 확인한다. 임의 파일 훼손을 **읽지 않고 즉시 탐지한다는 보장은 불가능**하다. Offline 중 필요한 content가 손상되면 preserve J/pending, fail-closed, 복구 경로를 제시한다. 매 refresh 모든 cold bytes를 다시 hash하지 않는다는 가정과 기존 로컬 손상 threat model의 허용 범위는 독립 감사에서 확인해야 한다.

## 15. PROPOSED atomic durable publication

CURRENT `OfflineStore._writeJsonAtomic`은 complete payload를 temp에 flush하고 readback 검증 뒤 `beforePublish` guard와 rename을 동기적으로 수행한다. AppState는 lineage lock 아래 이를 사용한다. 이것을 segment별 overwrite로 약화하지 않는다. CURRENT 코드가 Android power-loss directory-fsync까지 증명한다고 표현하지 않는다.

PROPOSED 게시 순서:

1. Fresh authenticated manifest와 same-view hot 문서를 받고 current ticket/mode/owner를 검사한다.
2. 현재 accepted root에서 reuse 가능한 objects/indexes를 확인하고 missing/changed immutable objects만 download한다. 새 response component는 지정 view/root에 결합한다.
3. 모든 changed bytes와 affected raw constraints, completeness·root·context를 검증한다. 임시 cache에 있다고 authoritative가 된 것은 아니다.
4. 새 objects와 index nodes를 durable하게 저장하고 exact readback/hash를 확인한다. 기존 objects를 in-place 수정하지 않는다.
5. 모든 required objects를 참조하는 새 generation manifest를 durable하게 저장·readback한다. 기존 generation과 frozen B/J/pending pins를 유지한다.
6. Lineage lock 안에서 owner/auth/request/mutation/mode를 재검사하고 **한 active-generation pointer를 atomic switch**한다. Pointer는 manifest identity·previous generation을 식별하고 손상 검출 metadata를 갖는다.
7. 새 accepted generation의 recovery 가능성과 installation authority를 확인한 뒤, 기존 규칙으로 eligible **confirmed committed** pending만 retire한다.
8. 동일 complete candidate를 한 번에 UI/state에 설치하고 성공 notification을 보낸다.

Pointer가 switch되기 전에는 old generation이 유일한 authority다. Switch 후에는 new generation을 load할 수 있어야 하며 old는 recovery pin으로 남는다. Object write·directory entry·manifest·pointer의 flush/order/atomic replacement가 Android filesystem에서 보장되는지 **UNPROVEN**이다. Native/API 검토와 process-death/power-loss 범위 구분이 필요하고, 지원하지 못하면 구현 gate를 통과할 수 없다. 작은 pointer만 원자적이라고 incomplete object durability 문제가 사라지는 것은 아니다.

## 16. Crash/restart 계약

아래 new-generation 행동은 PROPOSED다. Restart 검증·repair는 필요하면 O(N)/추가 네트워크를 허용하지만 incomplete B를 게시하지 않는다.

| 중단 위치 | durable 상태·accepted authority | restart 행동·네트워크 |
| --- | --- | --- |
| download 전 | old root/B, pending/J 그대로 | old 복구; online fresh manifest 재요청 가능 |
| download 중/일부 완료 | old root + uncommitted temp/orphan | temp는 authority 아님; hash 검증 후 resume 또는 폐기, missing만 재요청 |
| validation 후 object 저장 전 | old authority | 검증 메모리 결과는 durable 증거 아님; 다시 검증/저장 |
| cold object publish 중 | old root, 일부 immutable objects | old 사용; 미참조 objects는 재사용 후보, 아직 complete 아님 |
| hot/index publish 중 | old root, staging hot/index | old 사용; root/version 불일치면 staging 배제 |
| manifest 생성 후 pointer 전 | old authority, complete staged generation | generation/ticket 확인 후 명시적 refresh로 재게시하거나 유지; obsolete ticket 자동 설치 금지 |
| pointer replacement 도중 | old 또는 new valid pointer여야 함 | 깨진 pointer는 verified previous generation 복구; 불명확하면 persistenceBlocked, pending/J 보존 |
| pointer 후 pending 전 | new complete B, committed pending 잔존 | 재조회/검증 후 동일 confirmed marker retire; POST 재전송 금지 |
| pending retirement 도중 | new complete B, marker 존재 또는 삭제 | 원자 삭제/identity 계약 확인; unknown을 committed로 승격 금지 |
| pending 삭제 후 UI 전 | new durable authority | restart에서 new load/install; 새 POST를 자동 발행하지 않음 |
| UI 후 notify 전 | new B와 state, notification 없음 | 다음 load는 new; notify 성공 여부가 commit 증거는 아님 |

새 generation load가 실패하면 old fallback은 **recoverable local authority**로만 사용한다. “fresh sync 성공”으로 알리거나 새 mutation의 완료를 추정하지 않는다. Offline frozen B가 old라면 별도 pin으로 유지하고 new online B로 몰래 교체하지 않는다. GC가 crash recovery의 previous generation을 제거해서도 안 된다.

## 17. Pending·mutation receipt·reconciliation

CURRENT/PROPOSED 불변식:

`durable pending → POST → confirmed receipt → committed/rebuild-pending → coherent acquisition → guarded durable complete baseline → eligible pending retirement → installation`

`outcomeUnknown`은 성공한 hot/manifest/segment GET으로 해결되지 않는다. 비멱등 POST를 자동 retry하지 않는다. 기존 payment/registration retry identity와 원 principal을 유지한다. `serverCommittedRebuildPending`은 POST가 이미 성공했으므로 read-only rebuild로 회복한다. Cold cache miss/validation/ENOSPC/manifest lease 만료는 rebuild 미완료이며 marker를 남기고 UI 성공을 알리지 않는다.

MW/SW finalizing에서는 현행 `allowBaselineWhileFinalizing`, mode guard, reconciliation ID와 result/status 확인을 유지한다. Reconciliation 결과 R의 새 complete generation이 durable해지기 전 J/artifact/pending을 지우지 않는다. 새 root는 server Apply(B,J)를 실행하지 않으며 receipt를 대신하지 않는다. Response loss는 동일 reconciliation ID의 기존 status/identity 확인 절차를 따른다.

## 18. 다중 장치·auth·coherent download 수명

| 경우 | PROPOSED 행동 |
| --- | --- |
| 다른 장치가 수정 | fresh manifest R/context를 조회; 바뀐 roots/paths만 취득, unchanged objects 재사용 |
| 여러 revision 누락 | 보존 change log 범위 내면 base-root→target 전이; 범위 밖이면 complete manifest/tree diff 또는 full resync. 무조건 R+1 chain 요구 안 함 |
| 동일 user 재인증 | 기존 bytes 재사용은 가능하나 fresh owner/version/epoch 확인; 이전 auth-generation request는 폐기 |
| 다른 user login | 다른 namespace; old pending/J 격리. same numeric ID/different server도 자동 합치지 않음 |
| schema/registry 변경 | compatibility 확인; unsupported는 fail-closed. full legacy route는 명시 협상된 호환 경로일 때만 |
| 오프라인 중 다른 장치 변경 | frozen B/J를 유지하고 기존 inspect/conflict/사용자 MW/SW 선택, 자동 merge 없음 |
| server DB 교체·revision reset | dataset epoch 불일치 → stale cache를 새 authority로 재사용하지 않음, pins 보존하며 resync |

Manifest·segments는 동일 pinned **observation**에 속한다. Manifest 이후 서버 commit이 발생해도 이전 coherent 관측 자체가 invalid mixed state가 되는 것은 아니다. Content-addressed server objects와 **bounded view lease/retention**이 필요하며, missing/expired view면 새 manifest부터 다시 시작한다. 매 segment 뒤 “현재 live R과 같아야 한다”를 요구해 무한 starvation을 만들지 않는다. Client ticket/mutation lineage guard는 별도로 유지한다.

서버 read transaction을 휴대폰 download 전체 동안 붙잡는 방안은 기각한다. 객체를 immutable하게 materialize하고 수명/인가를 부여해야 한다. Segment hash를 아는 것만으로 접근권을 주지 않는다. Credential 만료·철회·wrong principal은 download/publish를 막는다. Cache miss에서는 여러 GET/RTT가 필요할 수 있다. **모든 segmented refresh가 1 HTTP라는 약속은 하지 않는다.** B-3의 성공 정상 graph를 바꿀 때도 새 topology를 명시 측정해야 한다.

## 19. History paging과 lazy UI — 별도 계약

CURRENT archive 조회/수정 기능과 full B 복구를 구분한다. PROPOSED history page는 `(dataset, principal, schema, query/filter, view-root/revision, cursor)`에 결합한다. Month filter는 query 편의이고 물리 raw segment identity와 같을 필요가 없다.

- Cursor는 **서버의 실제 deterministic sort tuple + unique tie-breaker**를 사용한다. 날짜·sort_order·ID를 쓴다면 NULL, 동일 날짜, 문자열 collation 의미를 명시한다. Offset만으로 concurrent insert/delete 안정성을 주장하지 않는다.
- 같은 paging session은 pinned view R의 immutable pages/lease를 사용하거나 변경 시 restart 신호를 준다. 서로 다른 R의 pages를 합쳐 누락/중복 없는 history라 부르지 않는다.
- Historical edit/date move/delete는 old/new query window를 invalidate하며 tombstone/새 page identity를 반영한다. Cached page의 old revision 표시와 authoritative freshness를 구분한다.
- Offline에서는 이미 accepted complete raw B와 기존 provisional 기능을 유지한다. Online-only 새 page가 필요하면 unavailable을 표시할 수 있지만, 기존 제공 기능을 online-only로 바꾸려면 제품 승인이 필요하다.
- Historical derived discount/payment presentation은 서버 계산이다. Raw cache가 있다고 Dart에서 canonical history financial view를 새로 계산하지 않는다.

UI page를 덜 받더라도 full Snapshot transfer/hash/write가 남으면 B 단독의 N 비용은 해결되지 않는다.

## 20. Restore request 25MiB 상한

CURRENT [config.py](../backend/app/config.py)의 `MONEY_NOTE_SNAPSHOT_RESTORE_MAX_BYTES` 기본값은 **25 × 1024 × 1024 = 26,214,400B**다. [security.py](../backend/app/security.py)의 `ApiBodyLimitMiddleware`는 `/api/admin/snapshot/restore`, `/api/offline-reconciliation/mobile-wins` POST 등에 적용하며 Content-Length 사전 검사와 실제 ASGI body chunk 누적을 모두 사용한다. 운영 override 값은 접근하지 않아 모른다.

T6.6A 50k one-shot은 bundle 28,164,304B, Snapshot **28,076,353B**였다. Snapshot만 기본 상한보다 **1,861,953B** 크며 restore password/wrapper와 MW journal/artifact metadata가 추가된다. **실제 50k restore HTTP 413을 관측한 것은 아니다.** Backend request parser가 수신하는 정확한 직렬화와 설정을 포함해 향후 테스트해야 한다.

CURRENT에는 request Content-Encoding gzip을 해제하는 runtime 경로가 없다. Response compression은 request 제한을 해결하지 않고, HTTP chunked transfer도 누적 byte limit을 우회하지 않는다. 미래 request decompressor를 넣으면 middleware 순서에 따라 encoded/decoded 기준이 달라지므로 **두 budget과 expansion/memory/time limit을 명시**해야 한다. 상한만 무작정 올리는 것은 복구·메모리 안전 설계가 아니다.

PROPOSED 큰 복구의 별도 후보는 authenticated bounded chunk staging + complete restore manifest + 최종 password/identity 확인 + mandatory pre_restore + 단일 DB replacement/Apply transaction이다. 전체 input 검증이 끝나기 전 장부 일부를 적용하지 않는다. Upload retry identity, quotas, abandoned chunk GC, decoded-size·row limits, expiry, rollback/receipt가 새 protocol proof 의무다. 별도 승인 없이 구현하지 않는다. Full Snapshot file export·legacy restore interoperability 및 MW의 큰 B/J 제출 한계 모두를 다뤄야 한다.

## 21. Backend O(N) 제거의 의존성

| CURRENT 작업 | 역사 의존·비용 근거 | PROPOSED T6.6D 과제·한계 |
| --- | --- | --- |
| Snapshot export | 11개 table fetchall, 원문/관계/hashes/정책 horizon | dirty leaves + persistent roots. full export/backup는 여전히 O(N) |
| runtime ownership validators | entries/payment/export에서 원장·관계 전수 검사 가능 | affected structural closure·validated indexes; actual migrated constraints 보존 |
| confirmed source lookup | source와 candidate actual 비교의 O(C×N) 가능 | source+epoch indexed lookup. 알고리즘/소유 규칙 변경 아님 |
| Summary cash | 과거≤today cash를 Python exact-money 합산 | date-indexed exact aggregate/prefix structure, 미래 cutoff/삭제 반영. REAL SUM·int64 overflow로 계약 훼손 금지 |
| recent closed counts | archive month별 group/count | transactionally maintained per-month count 또는 index 전략 |
| payment | active batch join·allocations·policy, detailed status 중복 계산 | active input filtering/reuse, raw relationships 유지; 할인/할당 semantics 변경 금지 |
| current entries/panels | current·fixed/모든 큐 읽기 | relevant indexes/query plans, H 자체 성장 허용 |
| policy horizon/metadata | Snapshot row 날짜/월 스캔 | incremental min/max/refcount 등 정확한 metadata, delete/복구 반영 |
| JSON/model preparation | full raw JSON/model traversal | hot/changed segments만 serialize; legacy full export는 예외 |
| freshness/auth/schema | read identity·credential·terminal guard | 필요 control 비용 유지; schema registry 판별은 별도 버전 캐시 검증 |
| mandatory backup | 마감/reset/restore/일괄정산의 full pre_restore | 안전성 유지. immutable object 재사용/늦은 file materialization 가능성은 별도 감사, 필수 백업 생략 금지 |

Cold를 내려주지 않으면서 서버가 여전히 full Snapshot을 먼저 만들면 network만 줄어든다. 유지 aggregate·dirty marker·root가 mutation rollback/restore/MW와 같은 transaction으로 일치한다는 증명이 필요하다. 금융 계산을 모바일로 이동하는 대안은 기각한다. SQLite 교체나 일반 query 최적화 구현은 이번 범위가 아니다.

## 22. Mobile validation·저장 비용 의존성

CURRENT raw-money·JSON/Unicode·presence·Snapshot hash/relationship·freeze는 전체 수신 tree를 순회하고, `OfflineBaseline.toJson`/lineage hash/atomic readback도 전체 B를 사용한다. 단지 validator의 loop를 빠르게 해도 새 full N bytes의 필수 표현 검사는 남는다.

PROPOSED T6.6E는 §14의 validated immutable content 재사용과 versioned physical store를 전제로 한다. 바뀐 transport bytes에 raw preflight/Unicode/required/type를 모두 적용하고, changed rows의 raw 관계를 accepted persistent indexes로 검사하며, small manifest와 changed objects만 encode/write한다. 전체 B를 매번 in-memory object로 만드는 model API를 유지하면 freeze/encode 비용이 되살아난다. Lazy raw lookup과 explicit full materialization API가 필요하다.

CURRENT launch/foreground의 `saveLaunchSnapshot`은 정상 bundle과 별도 full Snapshot GET/파일 생성이다. 사용자가 보장받은 30개 backup 정책을 그대로 유지하면 **foreground 전체 operation**에는 N 전송/쓰기 비용이 남을 수 있다. Normal financial acquisition과 auxiliary backup 비용을 분리 보고해야 한다. 동일 segment를 참조하는 독립 backup generation + on-demand file export가 같은 보장인지 별도 설계/감사가 필요하다. 백업 빈도를 몰래 줄이거나 전체 end-to-end O(H+D)를 이미 달성한다고 주장하지 않는다.

## 23. Full resync와 실패 정책

| trigger | PROPOSED 처리 |
| --- | --- |
| cache missing/corrupt, stale index | old accepted authority와 증거를 pin, exact referenced objects repair 또는 새 full initialization |
| wrong base/root/range/count, 누락 delta | partial 전이 reject, fresh complete manifest/full state로 재시도 |
| expired log/view lease | 새 coherent view 취득; cached invalid input으로 억지 continuation 금지 |
| unsupported sync/schema/registry | fail-closed, 명시 compatibility 경로/upgrade. malformed response를 legacy fallback 성공으로 처리하지 않음 |
| owner/dataset epoch mismatch | namespace 격리, raw ID/R만으로 재사용 금지 |
| global raw constraint failure | 해당 generation 미게시; 서버 오류 표시/정확한 full validation, 자동 repair 금지 |
| ENOSPC/durable readback 실패 | old B 및 pending/J 보존, persistenceBlocked/rebuild pending; 사용자에게 incomplete 성공 금지 |

Full resync는 O(N)을 허용한다. 네트워크 fresh state를 받았다는 이유로 frozen Offline B/J 또는 ambiguous POST evidence를 교체하지 않는다. J가 있는 frozen B가 손상되면 **정확히 그 B**를 content identity로 복구할 수 있어야 한다. 서버에 더 이상 그 version이 없으면 fresh R로 J를 재기준화하지 않고 보존 artifact/사용자 복구 절차로 blocked 상태를 유지한다. 이는 완전 cold를 evict하지 않아야 하는 이유다.

새 장치 full initialization은 처음부터 전체 segments·global constraints·root completeness를 검증해 accepted generation을 만든다. Unsupported old client에는 기존 full v1 경로를 유지하는 명시 rollout 전략이 필요하지만, 새 path 오류의 hidden fallback으로 사용하지 않는다. Protocol 협상·이행 정책은 T6.6C 설계 승인 대상이다.

## 24. 저장 성장·retention·GC

PROPOSED immutable content는 동일 raw data의 여러 generation 중복 저장을 줄일 수 있지만, pointer/index/temp/orphan·변경 leaf 사본이 추가된다. Raw history 자체가 사라지지는 않는다. Compression at rest는 이번 권고의 필수 전제가 아니며 별도 exact-byte/readback/메모리 검토 대상이다.

- Pin roots: accepted current generation, 검증된 previous recovery generation, frozen Offline B, active J/metadata lineage, unresolved online pending/reconciliation에 필요한 generation, backup/recovery artifacts의 참조, in-flight bounded view lease.
- Current complete B의 leaf를 “오래된 cache”라며 evict하지 않는다. Full historical offline preservation을 선택한 이상 공간 절약보다 recovery 완전성이 우선이다.
- GC는 pin set을 durable하게 읽고 reachable objects를 표시한 뒤, 다른 게시 transaction과 충돌하지 않는 대상으로만 sweep한다. Temp/orphan은 authority가 아니지만 최근 write/lease 참조가 없는지 확인한다. Crash 후 mark 재시도는 가능하고 accepted object 삭제는 불가능해야 한다.
- Pointer publish·pin 등록·GC 사이 ABA/race, partial deletion, index 손상을 failure injection으로 검증한다. Filename-age-only 삭제 금지. Corrupt GC index는 full reachability rebuild로 복구하며 추측 삭제하지 않는다.
- 현행 최근 30개 standalone backup과 recovery artifact 정책을 임의로 하나의 previous pointer로 축소하지 않는다. 미래 shared-object backup을 채택하면 30개 보존 generation 모두 pin하고 파일 export가 가능해야 한다.
- 여유 공간 부족 시 old authority/J/pending을 보존하고 새 sync를 중단한다. 추가 저장 상한·staging concurrency는 prototype으로 정하며, mandatory history를 온라인 전용으로 바꾸는 것은 제품 결정이다.

## 25. Workload scenario matrix

다음은 D+C가 구현·검증되었을 때의 PROPOSED 행동이다. CURRENT 구현 성능으로 주장하지 않는다. `Δ`는 changed leaves/affected indexes/paths, `full`은 전체 초기화·복구를 뜻한다.

| 시나리오 | 서버 계산·전송 | client 검증·invalidation | 게시·fallback |
| --- | --- | --- | --- |
| A 무변경 refresh | fresh auth/context/root; context도 같으면 reuse, typed 비금융 표시 변동은 새 hot | control/ticket + 실제 바뀐 hot; cold 재전송 없음 | small generation/metadata 또는 명시 no-change; synced time semantics 유지 |
| B 현재 카드 한 건 | insert + hot 금융 projection + Δ | new row/raw 관계, hot/raw 대응, index update | complete root publish 후 confirmed pending retire |
| C 현재 cash 한 건 | exact cash aggregate + hot + cash Δ | amount/flag/date/reference, hot/current range | 동일 guarded publish |
| D 현재 policy 변경 | backend 관련 금융 결과 재계산, setting/control Δ | supported registry/metadata; raw history unchanged 재사용 | unsupported compatibility면 reject, 금융 Dart 재계산 금지 |
| E 과거 거래 수정 | old/new leaf·month index·active 관계/aggregate 영향 + hot | raw identity/epoch/source 유지 또는 명시 변경, page invalidation | touched segments 교체; 영향이 크면 Δ 커질 수 있음 |
| F 과거 거래 삭제 | tombstone/cascade/ownership 해제 + aggregate/hot | reverse closure·page 삭제, payment 제한 서버 판단 | stale raw reference 남으면 reject; full은 missing proof 때 |
| G 새 월/period | time/context invalidation, 서버 새 hot/eligibility; 실제 month-close는 많은 writes + mandatory backup | 새 raw closure와 정책, copy/delete identity | 마감은 O(해당 작업량), full backup 예외; local clock으로 B advance 금지 |
| H recurring/fixed 확인 | source+child 또는 panel+cash transaction, hot+Δ | source+epoch/flow uniqueness, previous refs | receipt 확인·complete generation 후 pending retire |
| I app restart | offline면 서버 없음; online fresh manifest, 별도 backup 현재 존재 | durable pointer/index/complete-store recovery 검증은 O(N) 허용 | new UI install은 validated B; aux full backup 비용 분리 |
| J 수 주 Offline | B frozen/J input-only; reconnect inspect/conflict | B/J lineage·operation sequence 보존 | MW/SW 확정 후 fresh complete B; 무조건 incremental 아님 |
| K 다른 장치 update | base→target Δ 또는 tree diff, auth fresh | stale ticket reject·new roots | 로그 만료면 full; J 있으면 reconciliation |
| L 일부 cold 소실 | exact object repair; frozen version 없으면 복구 불가 표시 | missing content complete로 통과 금지 | J/pending 보존, 필요 full resync/수동 artifact recovery |
| M schema upgrade | versioned metadata·변경된 segments 또는 full | 전체 affected compatibility/validator receipt 재검증 | lossless migration 입증 전 old pin, unsupported block |
| N fingerprint/R mismatch | whole identity/context 재조회, 원인 판별 | root와 legacy fingerprint 혼동 금지; tampered transition reject | partial install 금지, safe full resync |
| O Offline reconciliation | 기존 Apply(B,J)/SW transaction, complete v7 materialization 필요 | resolved reconciliation ID, fresh result root·raw constraints | artifacts/J를 새 B durable 전에 제거 금지 |
| P 새 장치 full restore | full segments 또는 full Snapshot, O(N) | 전체 표현/hash/관계/restoreability | 25MiB 문제 별도 protocol gate, initial complete 전 Offline-ready 금지 |

## 26. Cost model과 복잡도 주장 조건

정의: `N` 전체 historical raw rows, `H` 실제 hot/관계 working set, `D` 변경 행과 영향 closure, `P` bounded leaf 수, `b` leaf byte 상한, `L` 변경 leaf 수, `M` 변경 tree/index path nodes. 개별 문자열/row 크기도 입력량으로 센다. Partition을 월 수로만 정의하지 않는다.

| 대안 | 정상 refresh의 개념적 비용 | 누락하면 안 되는 조건 |
| --- | --- | --- |
| A | server/client/write O(N+H); wire는 compressed N | codec 상수 감소이지 N 제거 아님 |
| B | UI page 비용 감소, full B 비용 O(N+H) | Snapshot이 남으면 sync 개선 아님 |
| C 단순 cache | 전송 감소 가능; full hash/manifest/encode면 O(N) 잔존 | R만 비교하거나 cold 전수 hash는 최종 목표 실패 |
| D+C 권고 | hot O(H), changed leaf bytes O(L×b), tree/index paths 대략 O(D log P), control은 bounded root + 변경 proofs | transactional discovery, balanced bounded leaves, accepted index/provenance, no whole flat hash/rewrite in steady state |

`O(H+D)`를 무조건 보장하지 않는다. 균형 tree라면 path 비용 `log P`, rebalancing·역참조 closure·변경한 거대 H·길어진 log가 있다. Full manifest P목록, global ID set 재생성, revision당 full history query, whole baseline lineage hash가 남으면 sublinear 주장은 무효다. 유지 indexes는 storage O(N)이고 bootstrap/검증·GC/full recovery는 O(N) 또는 정렬 비용을 허용한다.

No-change에도 auth·context·hot 계산은 필요할 수 있다. 동일 financial R에서 judgment의 비금융 표시가 달라지는 경우도 fresh hot view로 다룬다. Cold cache miss·대량 history edit·월마감·restore/MW는 D 또는 full이 크며 steady-state 한 건 mutation과 같은 비용을 요구하지 않는다.

## 27. 성능 acceptance와 미래 scaling benchmark

PROPOSED T6.6F/T6.9 감사는 hot 구성·seed·평가 context·문자 다양성을 고정하고 history 1k/5k/10k/50k/100k를 늘린다. 각 규모에서 no-change refresh, 현재 카드/cash 한 건 + authoritative rebuild, confirmed-heavy, 한 달 hot 대량 case를 구분한다.

- Request method/path·금융/auxiliary·RTT dependency stages·compressed entity/raw bytes·cache misses를 모두 기록한다. Cold miss의 추가 GET를 숨기지 않는다.
- Backend rows read/query plan·dirty keys·leaf/root bytes hashed·active aggregate 작업량을 계측한다. 고정 H/D에서 history 전체 fetchall/hash가 **0**인 steady-state path를 입증한다.
- Mobile raw-money/Unicode/presence/hash/relationship 대상 byte/row 수, index lookups, full materialization 횟수를 기록한다. 재사용한 raw data의 safety provenance도 검증한다.
- Durable 새 write/readback bytes·pointer/index 비용·pinned disk/peak memory를 측정한다. 정상 steady-state에 전체 B encode/rewrite가 **0**인지 확인한다.
- Tree paths의 log 성장과 control 증가를 분리한다. 고정 H/D에서 history linear slope가 남으면 원인을 제시하고 목표 통과로 선언하지 않는다. 절대 ms 상한은 실기기 gate 전 임의로 정하지 않는다.
- warmup/sample/median/p95/IQR을 기록하고 장시간 100k는 resource cap을 둔다. Initial/full resync/restore·crash validation O(N)은 별도 workload로 측정한다.
- Full gzip을 비교군으로 유지하고 representative/less-repetitive 양쪽에서 network/CPU/write를 분리한다. Host를 실제 phone·UFS·GC/frame 수치로 표현하지 않는다.

## 28. 제품 결정 register와 기술 미결정

| 항목 | 기본 설계 결정 | 별도 승인 필요한 변경 |
| --- | --- | --- |
| 기존 Offline 기능·역사 raw B | **보존**, 전부 local pin | 일부 history online-only/기존 기능 축소 |
| 완전 Snapshot recovery·MW | **보존**, materialization full 허용 | partial-only recovery나 MW 기능 제거 |
| 초기/전체 복구 지연 | O(N) 허용, progress/실패 상태 명시 | 새 user-visible SLA/제한 도입 |
| local 추가 staging/index 공간 | 최소 필요한 공간 확보 실패 시 old B 유지·중단 | history eviction 또는 백업 보존 개수 축소 |
| launch/foreground 30개 backup | 현재 의미 유지, 전체 operation 비용 별도 보고 | 빈도/내용/보존 보장 변경 |
| input-only J·금융 authority | **보존** | client canonical financial engine 확대는 기각 |

보수적 기본값으로 설계를 완료하는 데 **차단하는 제품 결정은 0개**다. 상기 optional tradeoff를 승인받지 않은 상태에서는 기능을 줄이지 않는다.

**REQUIRES DECISION — 별도 기술 설계 승인:** 새 sync root 의미와 version discriminator, physical baseline/lineage adapter, server dataset epoch/bootstrap, change capture 방식/retention, immutable segment lease, request-size 복구 protocol. 이것은 이번 문서 commit으로 구현 허가를 얻은 것이 아니다.

**UNPROVEN — prototype 필요:** Android durable ordering/fsync와 fallback, persistent index completeness, leaf split/merge 비용·size, migration/crash compatibility, bitrot 검증 수명, legacy exact JSON/hash 재구성, 큰 Snapshot upload/서버 peak memory, auxiliary backup의 segment reuse 가능성. 미래 registry drift·auth-session SQLite database-is-locked·backend detailed payment 중복 계산도 미해결이다.

## 29. T6.6C/D/E 의존성 지도

```text
T6.6A 측정 → T6.6B 설계 → 별도 독립 설계 감사
                              │
                 T6.6C version/identity/root/전이·fallback 설계
                         ┌────┴────┐
                 T6.6D 변경 추적    T6.6E 저장/provenance/validation 설계
                 + root/aggregate   + atomic generation/legacy adapter
                         └────┬────┘
                    승인 후 transport/storage 통합 구현
                              ↓
                   T6.6F 독립 correctness/performance 감사
                              ↓
                   post-T6.6 실기기 gate / T6.9 큰 규모 검증
```

Backend change tracking/root가 정확히 만들어져야 incremental transport의 비용 이득을 주장할 수 있다. Mobile complete cold store/provenance가 있어야 unchanged validation 재사용이 안전하다. 두 쪽 contract를 먼저 함께 설계하고 producer·consumer를 순차 구현해야 한다. Alphabetical 순서대로 delta부터 활성화해서는 안 된다.

Compression은 이 root/storage redesign과 독립적으로 승인·호환성/메모리/negotiation 검증 후 도입할 수 있다. History paging도 baseline 완전성과 독립적으로 설계하되 revision/view binding은 공유한다. 큰 restore/MW request protocol은 정상 delta만으로 해결되지 않아 별도 선행 compatibility gate다. 이번에는 C/D/E 구현을 시작하지 않았다.

## 30. 정확성 proof obligations와 negative tests

독립 설계 감사와 미래 구현 테스트는 적어도 다음을 확인해야 한다. 이는 실행 완료한 새 테스트 목록이 아니다.

| proof obligation | 제안 negative/valid controls |
| --- | --- |
| complete state coverage | 11 table 각각 누락·빈 table 위조·columns/count 불일치; 12 typed section 누락; legitimate empty |
| origin/owner/lineage | wrong principal, same ID/different server/epoch, logout/relogin, delayed same-user old session |
| coherent view | hot R와 cold R 혼합, eval context 변경, terminal retry, segment download 중 다른 device commit, expired lease |
| segment/root completeness | leaf omission/reorder/duplicate/overlap, wrong table/range/schema, stale parent, forged counts, arbitrary rehash, root under different version |
| exact representation | ±2^53 경계·fractional/raw token, duplicate JSON keys, malformed UTF-8/UTF-16 escape·map keys, valid Korean/emoji/NUL where allowed, no normalization |
| global identities | duplicate PK/payment key across leaves, N4 null controls/empty duplicate/case/combining distinct BINARY, source+epoch wrong/duplicate, same numeric IDs in valid distinct namespaces |
| raw relationships | delete referenced child/cash, allocation owner/cash total mismatch, fixed/payment shared cash, stale reverse index, registration의 삭제 target 허용 control |
| historical mutation | old archive edit/delete/date move, month-close copy/new ID + old tombstone + registration rewrite, template detach, late closed-month insertion, deferral revert |
| change tracking | commit/rollback, cascade/bulk/restore/MW/maintenance, noop/ABA, skipped log, trimmed history, revision reset, builder lag, schema/registry/date-only change |
| migration/legacy equality | full v7 table order·hash/ID/fingerprint 동일성, baseline logical equality, old B+J lineages, resolved reconciliation ID, unsupported registry |
| publication | 모든 §16 boundary process interruption, beforePublish stale generation, object not flushed/pointer flushed, ENOSPC/readback failure, old pointer recovery |
| pending | confirmed POST + cache failure, lost POST response + 성공 GET, idempotent confirmed retry, pointer durable/retire failure, new POST 금지 유지 |
| Offline/MW/SW | complete B offline restart, J EOF/sequence/operation-ID rules, other-device conflict, full B materialization failure, missing frozen leaf, artifact preservation, J double replay 금지 |
| retention/GC | active/previous/frozen/artifact/lease pin, pointer-GC race, orphan cleanup 중 crash, storage pressure, only recoverable generation 삭제 시도 |
| full recovery/size | cache corruption/full resync, legacy full route negotiation, ≥25MiB body·chunk 누적·expansion cap, actual migrated SQLite restore parity |
| trust boundary | Category C-only close/grouping/derived amount 차이를 client algorithm oracle로 reject하지 않음; 독립 A/B 위반은 계속 reject |
| complexity | 고정 H/D와 증가 N에서 hidden fetchall/full hash/full encode/flat P manifest 탐지; oversized month·dense references·less-repetitive control |

Full-resync path와 steady-state path 모두 같은 logical state·typed financial candidate·Snapshot export·reconciliation 결과를 낼 수 있어야 한다. 유한 corpus는 universal correctness proof가 아니며 oracle는 실제 backend presenters와 actual migrated SQLite다. 모바일 금융 재계산 oracle는 사용하지 않는다.

## 31. 권고·기각·독립 감사 gate

**권고 설계:** D+C를 장기 target으로 채택할 후보로 제출한다. Cold는 삭제하는 자료가 아니라 immutable bytes로 재사용하는 완전한 authoritative B의 구성이다. Server-generated hot view와 changed raw segments를 동일 coherent manifest 아래 묶고, complete logical state를 durable root switch로 게시한다. A를 wire 비교·가능한 독립 단기 개선으로, B를 별도 history UX로 유지한다.

**기각/보류:** archive 불변 가정, date-only cold 분류, filename/mtime cache, global R만으로 세션/정책/context 판별, partial B의 기존 baseline 주입, old/new flat SHA 혼용, P전체 manifest 매번 전송, leaf 안에서만 UNIQUE 검사, hot GET으로 POST unknown 해소, J를 최신 B에 자동 rebase, mandatory backup/Offline 기능 축소, Dart 금융 엔진 확장.

독립 auditor는 특히 §13의 flat-hash/new-root compatibility, §14의 global structural closure·bitrot assumptions, §15의 durable ordering, §17의 receipt/J semantics, §20의 큰 복구, §21–22의 hidden O(N)을 반증해야 한다. 새 protocol/storage 설계가 이 의무를 만족하지 못하면 구현을 시작하지 않는다. **DESIGN COMPLETE는 future mechanism의 correctness나 independent approval을 뜻하지 않는다.**

## 32. 이번 문서 검증·재현·안전성

소스 참조·11/12 inventory·export ordering·revision trigger·actual migrated N4 constraint·현재 raw validators·publication guard·reconciliation transaction·request middleware를 읽어 대조했다. Byte figures는 T6.6A committed aggregate와 대조하고, 겹치는 timing categories를 합산하지 않았다. Reference paths/Markdown links와 `git diff --check`를 검증한다. 실행한 검사 결과는 아래 검증 기록에 기재한다.

재현용 read-only 입력은 [scripts/benchmarks/README.md](../scripts/benchmarks/README.md)의 T6.6A 도구와 [environment.json](benchmarks/t66a/environment.json)이다. 기존 큰 `/tmp` body나 운영 사본 없이 committed aggregate와 source로 이 설계 근거를 확인할 수 있다. 신규 synthetic benchmark·실기기 측정을 수행했다고 주장하지 않는다.

문서만 변경하므로 full backend/Flutter/Android 회귀가 자동 필수는 아니다. 저장소 지침에 따라 isolated backend targeted validation과 frontend production build를 실행하고, 실제 결과만 기록한다. 운영을 읽는 deploy dry-run은 실행하지 않는다.

이번 실제 실행 기록:

| 검사 | 실행·결과 |
| --- | --- |
| 소스·수치·문서 정합 | Python AST로 `SNAPSHOT_TABLES`/`AuthoritativeProjections`와 matrix 대조: **11/11, 12/12**. Markdown local links 존재 확인, committed raw byte figures/산식 대조: PASS |
| 격리 backend | backend cwd에서 `../.venv/bin/python -m pytest -q tests/test_authoritative_state.py tests/test_snapshot.py tests/test_snapshot_export_metadata.py tests/test_versioned_migrations.py tests/test_offline_reconciliation.py`: **150 passed, 442 subtests passed, warning 1**, 125.70초 |
| 정적 검사 | `.venv/bin/python -m ruff check backend/app backend/tests scripts`: PASS |
| frontend build | `npm --prefix frontend run build`: PASS; TypeScript와 Vite production build. 배포하지 않음 |
| patch 검사 | `git diff --check`: PASS; 최종 staged diff에서도 재확인 |

Backend 경고는 기존 Starlette TestClient/httpx deprecation이다. 테스트는 `IsolatedDatabaseTestCase` 및 reconciliation fixture의 새 임시 SQLite를 사용했다. 전체 backend suite·frontend test/lint·Flutter/Android suite/APK·새 성능 benchmark는 문서 전용 변경에서 실행하지 않았다. 이전 T6.6A의 full regression 수를 이번 실행으로 재사용하지 않는다. 위 inline 문서 검증은 별도 제품 진단 코드를 추가하지 않는다.

제품 runtime, 금융 algorithm, protocol/schema/version, baseline/journal/pending format은 모두 그대로다. T6.6C/D/E 구현·compression 활성화·deployment·production access는 없다.

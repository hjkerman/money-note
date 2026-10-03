# SQLite 스키마 버전과 구 DB 호환성

서버 DB와 계산 결과가 원본이라는 원칙은 [도메인 모델](domain-model.md)을 따른다. 이 문서는 startup의 구조 migration과 명시적인 one-time 데이터 의미 checkpoint를 설명한다. Snapshot JSON의 `schema_version`과 DB의 `PRAGMA user_version`은 별개의 버전이다.

## 현재 경로

- 현재 DB 버전은 `4`이며 `backend/app/db_migrations.py`의 `CURRENT_SCHEMA_VERSION`이 코드 원본이다. 단일 SQLite DB이므로 별도 ledger 테이블 대신 `PRAGMA user_version`을 사용한다. 이 값은 Snapshot에 포함하지 않는다.
- 빈 DB는 `SCHEMA`로 현재 테이블·인덱스·revision trigger·기본값을 만들고 기존 기본값 정규화를 한 transaction에서 끝내고 recurring identity checkpoint를 검증한 뒤 버전 4로 표시한다.
- `user_version=0`이고 테이블이 있는 DB는 **CREATE IF NOT EXISTS 실행 전** 구조를 검사한다. 지원 세대의 필수 테이블 집합은 핵심 12개 → 카드 batch 관계 2개 → 알림 등록 → offline reconciliation 관계 2개 → authoritative revision 1개 순서다. 카드 batch, 현금 fixed, 알림 도입 전/후, Offline Phase 2와 현행 구조를 서로 다른 era contract로 식별한다. 그 세대에 필수인 표가 빠졌으면 빈 표를 재생성하지 않고 시작을 거부한다. 예를 들어 current-looking DB의 `card_payment_batch_items`가 사라진 경우 기존 batch 의무를 잃은 상태를 version 3으로 승인하지 않는다.
- 세대별 필수 **authoritative** 컬럼·PK identity·UNIQUE 관계·critical FK를 검사한다. `batch_id`, `discount_override`처럼 그 시대에 이미 존재한 금융 입력의 누락은 후대 additive migration으로 수선하지 않는다. 현재-unversioned DB는 revision table이 있으면 현행 필수 컬럼·인덱스·trigger까지 먼저 검사한다. 자동 생성되는 정수 ID 표는 단순 `PRAGMA table_info`의 PK 표식뿐 아니라 SQLite rowid alias 및 `AUTOINCREMENT` 계약도 검사한다. 같은 이름의 인덱스라도 필요한 uniqueness/대상 컬럼/조건이 다르면 거부한다. revision trigger가 남아 있는데 revision table이 없다면 손상된 현재 세대로 판단한다. 과거 세대에 실제 없던 관계·컬럼만 migration 대상으로 인정하며, 알 수 없는 혼합/누락을 `NULL`이나 0으로 추측해 복구하지 않는다. 인정한 legacy DB만 1→2→3을 순서대로 수행한다.
- 이미 버전 3인 DB는 과거 backfill을 재실행하지 않는다. 현재 `SCHEMA`의 모든 필수 컬럼, 인덱스·revision trigger 및 핵심 PK/UNIQUE/FK 관계를 확인한다. 과거부터 남은 추가 컬럼은 허용한다. 미래/음수 버전은 거부한다.
- 각 numbered migration은 `BEGIN IMMEDIATE` 안에서 DDL/DML, 최종 검증, `user_version` 갱신을 수행한 뒤 commit한다. 실패한 단계는 통째로 rollback된다. 앞선 완료 단계는 해당 버전으로 남아 다음 startup에서 재개된다. SQLite `executescript()`는 암묵적 commit이 있으므로 migration transaction 안에서 사용하지 않는다.
- 이 경로는 정상 startup에서 과거 행의 금액·할인·날짜·ID를 재계산하지 않는다. 원래 `REAL` affinity였던 초기 DB의 물리적 금액 컬럼을 강제로 rebuild하지 않는다. 기존 데이터 의미를 보존하며, 새 DB의 금액 컬럼은 `INTEGER`다.
- 모든 지원 시대/current-versioned에서 DDL·backfill·version 승격 전에 영속 금액/금액 설정을 read-only로 검사한다. 관측한 값이 정확한 정수이고 `abs(value)<=2^53−1`이어야 하며, historical REAL의 정수값도 같은 계약이다. 범위 밖/소수 값은 원본 checkpoint를 보존하고 기동을 거부한다. 설정 정규화는 float가 아니라 exact integer parsing을 사용한다. 원래 입력이 이미 과거 저장에서 손실된 경우 그것을 추측 복구하지 않는다. numbered framework/DB version 3 및 실제 컬럼 affinity는 바꾸지 않는다.

| 버전 | 책임 | 영속 상태 |
| --- | --- | --- |
| 0 | 비어 있거나 인정된 unversioned legacy | 빈 파일은 바로 현재 schema를 만들고 3으로 표시. 기존 파일은 schema admission 후 업그레이드 |
| 1 | 테이블·누락 컬럼 보강, `installments` 정리, 생성 키·confirmation/deferral 필드 보강, 기본 설정/라벨 seed | 기존 데이터는 보존. 완료된 1만 기록 |
| 2 | 역사적 label·도메인 이름, retired key, 금액 문자열, 유동성 key, planned due-day backfill | 충돌하는 old/new 설정값은 거부하고 1로 rollback |
| 3 | 최종 인덱스·authoritative revision trigger와 구조 검증 | 이전 구조 계약 |
| 4 | 증명 가능한 역사적 explicit recurring 생성 epoch materialization 및 canonical 검증 | 구조 변경 없는 one-time semantic checkpoint; 모호하면 version 3 상태로 rollback |

## 이전 조건부 startup 동작의 inventory

다음은 T5 전 `backend/app/db.py:init_db()`에 함께 있던 경로다. 위치는 이후 `backend/app/db_migrations.py`의 numbered 단계로 옮겼다. Git commit은 예시가 실제 소스에 나타난 시기를 가리키며 모든 과거 DB 파일의 지원 약속을 뜻하지 않는다.

| 논리 경로 | 원래 위치/대표 시대 | 입력 상태 → 구조·데이터 변화 | 이전 transaction/repeat 동작 | 현행 테스트 |
| --- | --- | --- | --- | --- |
| `SCHEMA` fresh seed | `db.py:SCHEMA`, 초기부터 | 테이블·인덱스·설정/라벨 기본값 생성 | `executescript()`로 먼저 commit 가능; `IF NOT EXISTS`로 매번 재시도 | fresh, current characterization |
| `installments` 제거 | `init_db`, `cfd047f` | legacy 표 삭제 | 매 startup DROP | pre-batch fixture, historical matrix |
| ledger/panel 필드 보강 | `init_db`, `f3e4e5d`→`214fd92` | due/confirmation, 할인 override, 사용 장소, source planned relation, fixed cash-flow link 추가 | PRAGMA column 확인 후 ALTER | 네 시대 fixture, v5/v6 Snapshot |
| payment/deferral identity | `init_db`, `f3e4e5d` 이후 | 누락된 payment key 생성, event batch/idempotency/request fingerprint 및 deferral 원위치 필드 추가 | null 대상 key만 보강; 재실행 시 신규 행만 처리 | batch/Phase2 fixture, card payment tests |
| recurring/급여 관계 | `init_db`, `53ff6e1` 이후 | cash `is_primary_income`, planned `confirmed_month`, panel `confirmed_month` backfill | 일부 기존 행만 UPDATE | fixed fixture, month/fixed tests |
| reconciliation fingerprint | `init_db`, `214fd92` 이후 | fingerprint version/request fingerprint nullable 열 추가 | PRAGMA column 확인 후 ALTER | Phase2 fixture, reconciliation tests |
| revision/counting trigger | `SCHEMA`, `120be91` 이후 | Snapshot 대상 표 변경 시 단조 revision 증가 | `CREATE TRIGGER IF NOT EXISTS`, 매 startup 검사 | refresh revision tests |
| 도메인/라벨 정리 | `init_db` + helper, `a52cb0b` 전후 | settlement→family_card, 고정지출/세부내역 라벨, 은퇴한 interest/family limit 제거 | 매 startup 조건부 UPDATE/DELETE | settings + historical tests |
| 유동성/금액 값 정리 | `_normalize_money_settings`, `_migrate_liquidity_names` | legacy key→현재 key, 정수 금액 문자열, 같은 값은 dedupe·충돌은 거부 | 기존 `executescript` 뒤 DML transaction; 실패 전 DDL은 이미 남을 수 있었음 | settings conflict/equal, historical tests |
| 카드 planned due-day | `_backfill_planned_due_days` | `매월 N일` 제목에서 due-day와 분류 보강 | null planned 행만 재시도 | historical matrix |
| legacy 할인 표시 필드 | `_drop_legacy_column` | `discount_checked` 제거 시도; SQLite 제약으로 불가하면 보존 | 과거에는 startup마다 시도 | Snapshot compatibility tests |

과거 구현의 `SCHEMA` 실행은 `sqlite3.executescript()`였으므로 뒤의 legacy backfill이 실패하면 이미 생성된 테이블/trigger가 durable할 수 있었다. T5는 단계별 version marker와 rollback으로 이 모호성을 제거한다. 단계 1이 완료되고 단계 2가 실패하면 DB는 명시적으로 버전 1이며, 서비스 startup은 실패하고 다음 실행에서 단계 2부터 재개한다.

## Git 이력 기반 synthetic schema matrix

`backend/tests/fixtures/schema_*.sql`은 다음 Git 커밋의 `SCHEMA` 문자열에서 가져온 **코드 기반 빈 schema**다. 금융 row는 테스트가 직접 삽입하며 운영 DB/Snapshot에서 복사하지 않는다. 각 fixture는 실제 Git 시기의 구조를 대표하지만 그 이전·미확인 파일까지 지원한다고 해석하지 않는다.

| Fixture | Git 기준 | 주요 차이 | 업그레이드 계약 |
| --- | --- | --- | --- |
| `pre_batch` | `cfd047f` | 카드 batch 없음, 금액 REAL affinity, 옛 유동성 key | 현재 컬럼/테이블·설정값 보강, 원본 금융 row/ID 보존 |
| `card_batches` | `f3e4e5d` | batch 도입, 구형 fixed/reconciliation 상태 | 현재 관계·fingerprint 보강 |
| `fixed_expenses` | `53ff6e1` | 현금 fixed 확인 관계 포함, reconciliation 없음 | confirmation/date 의미 보존 |
| `pre_notification` | `1da7512` | 현행 금융 필드, 알림 등록 이전 | 이미 존재한 금융 입력은 보존; 아직 없던 알림·reconciliation 표만 생성 |
| `notification` | `7cc7323` 및 동일 구조의 Phase 1/1.5 | 알림 등록 표 포함, reconciliation 이전 | 등록 identity 보존; 아직 없던 reconciliation 표만 생성 |
| `offline_phase2` | `214fd92` | reconciliation 테이블은 있으나 후속 fingerprint/revision 필드 미완성 | 최신 fingerprint와 revision 경계 보강 |
| current unversioned | T4.5 `7c0e601`의 `SCHEMA` | 현재 구조지만 marker 없음 | 데이터 backfill은 한 번만, 버전 4 설치 |

Unknown table/column 또는 해당 세대의 필수 테이블·identity·관계가 빠진 unversioned DB는 fresh로 오인하지 않는다. 모든 지원 era에서 존재한 `ledger_entries.aux_amount_value`, `cash_flows.title` 같은 원본 컬럼의 누락은 임의의 `NULL`/0으로 복구하지 않고 거부한다. 반면 실제로 나중에 추가된 `source_planned_entry_id`, `confirmed_month`, 결제/재조정 fingerprint 등은 해당 역사적 구조에서만 migration 대상으로 인정한다. `installments`는 과거 삭제 경로라 유일한 추가 허용 표다. 이전 단계에서 crash한 버전 1·2는 해당 단계 이후만 재개한다. 테스트는 필수 테이블 전체 누락, 동일 이름의 잘못된 UNIQUE 인덱스·PK/FK 손상, 9,880원 batch 의무 손실 반례, 부분 금융 UPDATE·최종 index 설치 실패를 검증한다.

버전 표식이 없는 과거 DB에서 서로 다른 Git 시대의 schema와 데이터가 완전히 동일한 경우에는 어느 시대에서 왔는지 파일만으로 증명할 수 없다. 예를 들어 fixed 관계 컬럼이 제거됐지만 확인된 fixed 행도 없는 파일은 더 이른 batch 시대와 구별할 증거가 없다. 데이터 관계의 추측 복원은 하지 않으며, 확인된 fixed 행이 남아 있다면 그 누락을 손상으로 거부한다. 운영 파일의 임의 수선 경로는 제공하지 않는다.

지원 historical fixture에는 동일한 합성 금융 입력을 넣는다. 예정 수입 400,000원, 카드 지출 10,000원(서버 계산 할인 120원), planned 카드 정기결제 3,000원, 현금 유출 500원, 별도 Family Card 표시 2,000원이다. 업그레이드와 재시작 후 `current_summary_values()`의 기대값은 카드 부담 9,880원, 현금흐름 −500원, 잔여 유동성 386,620원, Family Card 원금 표시 2,000원이다. Family Card 표시는 잔여 유동성에 합산하지 않는다. 테스트는 원본 금융 행의 금액·ID, due-day backfill과 이 기대값을 함께 고정한다.

## Snapshot과 배포

### Revision trigger 계약

현재-unversioned admission과 version 3/4 검증은 revision trigger의 이름만 신뢰하지 않는다. 대상 표, AFTER INSERT/UPDATE/DELETE event, `authoritative_state_revision` id=1에 대한 `revision = revision + 1` 효과를 명시적으로 검사한다. 공백·대소문자·identifier quoting·주석은 정규화하지만 WHEN, 다른 대상/event, no-op, 감소·다른 revision 행 갱신은 승인하지 않는다. 금융 대상 표나 revision을 변경하는 예상 밖 trigger도 거부해 증가분 상쇄를 막는다. Revision state는 id=1의 단일 비음수 정수 행이어야 한다.

이 검증은 metadata를 읽으며 실제 금융 DML probe, 자동 수선, migration 재실행을 하지 않는다. 손상된 현재 구조는 version 승격 전에 보존하고 거부한다. 역사적 schema는 기존 numbered migration이 현행 trigger를 생성한 뒤 같은 계약을 검증한다.

Snapshot v4/v5/v6/v7은 계속 지원한다. Restore는 현재 DB의 데이터 테이블을 서버 transaction 안에서 교체하며 DB 파일의 `user_version`을 Snapshot에서 가져오지 않는다. 기존 DB가 unversioned라면 **먼저 startup migration**이 끝나야 restore endpoint가 제공된다. Restore의 임시 dry-run DB는 현재 `SCHEMA`를 사용하지만 서비스 DB로 승격하지 않는다. Restore 후 재기동은 버전 4의 schema와 canonical recurring sanity check를 수행하며, 현재 export는 v7이다.

`user_version`은 **DB 구조와 명시적 semantic checkpoint**, Snapshot `schema_version`은 **가져오는 데이터의 호환 의미**를 식별한다. 이미 version 3인 DB에도 v4~v6 데이터가 복원될 수 있다. v6의 연결된 현금성 고정지출에서 누락된 `confirmed_month`는 원문 manifest 검증 후 Snapshot import 경계에서 검증된 `spent_on`의 월로 복원한다. 연결된 현금흐름의 소유·역할·처리일이 모순되거나 같은 현금흐름을 두 고정지출이 공유하면 dry-run에서 복원을 거부한다. fixed의 `confirmed_at`은 실제 날짜·시각으로 해석 가능해야 하며, v6/v7에서 확인 시각 또는 확인 월만 있고 cash-flow 연결이 없는 행도 거부한다. v4~v6 카드 정기결제의 명시적 source ID는 Snapshot에 없으므로 원본 확인 시각과 변경되지 않은 생성 행·월내 유일성이 일치할 때 import 경계에서 현행 source ID를 영속화한다. 기존 미연결 행은 수정 전에만 같은 증거로 결합할 수 있다. **삭제 시 mutable 필드 재매칭으로 새 관계를 만들지 않는다.** 명시적 source가 있는 현재 행은 legacy 추론에서 제외한다. 관계가 불명확하면 취소 전에 거부하며, 현재 DB migration을 재실행하거나 v7 관계를 추측하지 않는다.

구 API 이미지로 artifact rollback해도 DB는 자동으로 이전 버전이 되지 않는다. schema 변경 릴리스의 이전 이미지 호환성은 배포 전에 따로 검증해야 한다. 운영 DB 접근·복구·배포 절차는 [runbook](runbook.md)을 따른다.

## Version 4 recurring identity checkpoint

이전 배포 writer는 source ID/payment key를 보존하지만 child 확인 epoch는 NULL로 남겼다. schema version 3이라는 사실만으로 그 데이터가 current canonical이라고 판단할 수 없다. Version 4는 `recurring_compatibility.py`의 proof-only 계획을 기존 migration transaction 안에서 실행한다. 모든 관계를 검증한 뒤 epoch 컬럼만 UPDATE하고 `user_version=4`를 같은 COMMIT으로 기록한다. 금액·ID·content·발생일을 변경하지 않는다. DELETE/WAL의 commit 전 process kill 또는 backfill/최종 검증 실패는 version 3과 전체 원본 행을 보존한다. 성공한 version 4는 다시 backfill하지 않는다.

Retired identity가 DB만으로 증명되지 않으면 DB와 함께 보존한 `snapshot-backups/`의 manifest 검증된 v7 문서를 evidence로 읽는다. Source ID와 source 생성 시각, stable payment key로 유일한 원래 epoch를 증명해야 하며 서로 다른 epoch 증거가 있으면 거부한다. Filename·mtime·mutable content·amount는 증거가 아니다. 완전한 canonical DB에는 witness를 요구하지 않는다. Summary나 export에서 lazy repair하지 않으며, 검증에 실패한 DB/증거를 자동 편집하지 않는다.

현재 export의 `recurring_ownership_version=1` 표식은 content manifest에 포함된다. 표식 없는 역사적 v7만 같은 proof-only 변환을 임시 import 표현에 적용하고, 이후에는 현재와 동일한 canonical invariant를 검사한다. Source 없는 이전 v7은 현재 시각/제목만으로 새 소유자를 추측하지 않는다. v4~v6 기존 normalization과 exact-money admission은 유지한다. Version 4 DB를 구 코드로 되돌릴 때는 해당 코드의 startup version 지원을 따로 확인해야 하며 version을 임의로 낮추지 않는다.

과거 월마감은 archive 행을 INSERT/delete로 복사해 행 ID와 생성 시각을 새로 부여했다. Archive 복사 시각이 다음 확인과 같은 초여도, 검증된 stable key/source evidence가 해당 행의 별도 마감 epoch를 유일하게 증명한 경우에만 새 확인의 경쟁 후보에서 제외한다. 미증명·상충 후보를 임의로 제외하거나 가장 가까운 행을 선택하지 않는다.

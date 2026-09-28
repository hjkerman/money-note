# SQLite 스키마 버전과 구 DB 호환성

서버 DB와 계산 결과가 원본이라는 원칙은 [도메인 모델](domain-model.md)을 따른다. 이 문서는 startup 시 DB 파일의 구조를 변경하는 경계만 설명한다. Snapshot JSON의 `schema_version`과 DB의 `PRAGMA user_version`은 별개의 버전이다.

## 현재 경로

- 현재 DB 버전은 `3`이며 `backend/app/db_migrations.py`의 `CURRENT_SCHEMA_VERSION`이 코드 원본이다. 단일 SQLite DB이므로 별도 ledger 테이블 대신 `PRAGMA user_version`을 사용한다. 이 값은 Snapshot에 포함하지 않는다.
- 빈 DB는 `SCHEMA`로 현재 테이블·인덱스·revision trigger·기본값을 만들고 기존 기본값 정규화를 한 transaction에서 끝낸 뒤 버전 3으로 표시한다.
- `user_version=0`이고 테이블이 있는 DB는 역사적 핵심 테이블·컬럼을 검증한다. 모르는 테이블/컬럼, 빠진 핵심 구조, 모순된 관계는 수정하지 않고 시작을 거부한다. 인정한 legacy DB만 1→2→3을 순서대로 수행한다.
- 이미 버전 3인 DB는 과거 backfill을 재실행하지 않는다. 필수 테이블과 금융·복구 핵심 컬럼, 인덱스·revision trigger 및 주요 UNIQUE 제약만 확인한다. 미래/음수 버전은 거부한다.
- 각 numbered migration은 `BEGIN IMMEDIATE` 안에서 DDL/DML, 최종 검증, `user_version` 갱신을 수행한 뒤 commit한다. 실패한 단계는 통째로 rollback된다. 앞선 완료 단계는 해당 버전으로 남아 다음 startup에서 재개된다. SQLite `executescript()`는 암묵적 commit이 있으므로 migration transaction 안에서 사용하지 않는다.
- 이 경로는 정상 startup에서 과거 행의 금액·할인·날짜·ID를 재계산하지 않는다. 원래 `REAL` affinity였던 초기 DB의 물리적 금액 컬럼을 강제로 rebuild하지 않는다. 기존 데이터 의미를 보존하며, 새 DB의 금액 컬럼은 `INTEGER`다.

| 버전 | 책임 | 영속 상태 |
| --- | --- | --- |
| 0 | 비어 있거나 인정된 unversioned legacy | 빈 파일은 바로 현재 schema를 만들고 3으로 표시. 기존 파일은 schema admission 후 업그레이드 |
| 1 | 테이블·누락 컬럼 보강, `installments` 정리, 생성 키·confirmation/deferral 필드 보강, 기본 설정/라벨 seed | 기존 데이터는 보존. 완료된 1만 기록 |
| 2 | 역사적 label·도메인 이름, retired key, 금액 문자열, 유동성 key, planned due-day backfill | 충돌하는 old/new 설정값은 거부하고 1로 rollback |
| 3 | 최종 인덱스·authoritative revision trigger와 구조 검증 | 현재 startup 계약 |

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
| `offline_phase2` | `214fd92` | reconciliation 테이블은 있으나 후속 fingerprint/revision 필드 미완성 | 최신 fingerprint와 revision 경계 보강 |
| current unversioned | T4.5 `7c0e601`의 `SCHEMA` | 현재 구조지만 marker 없음 | 데이터 backfill은 한 번만, 버전 3 설치 |

Unknown table/column 또는 핵심 구조가 빠진 unversioned DB는 fresh로 오인하지 않는다. `installments`는 과거 삭제 경로라 유일한 추가 허용 표다. 이전 단계에서 crash한 버전 1·2는 해당 단계 이후만 재개한다. 테스트는 부분 금융 UPDATE·최종 index 설치 실패를 주입하고 version marker와 데이터 rollback을 확인한다.

## Snapshot과 배포

Snapshot v4/v5/v6/v7은 계속 지원한다. Restore는 현재 DB의 데이터 테이블을 서버 transaction 안에서 교체하며 DB 파일의 `user_version`을 Snapshot에서 가져오지 않는다. 기존 DB가 unversioned라면 **먼저 startup migration**이 끝나야 restore endpoint가 제공된다. Restore의 임시 dry-run DB는 현재 `SCHEMA`를 사용하지만 서비스 DB로 승격하지 않는다. Restore 후 재기동은 버전 3의 최소 sanity check만 수행하며, 현재 export는 v7이다.

구 API 이미지로 artifact rollback해도 DB는 자동으로 이전 버전이 되지 않는다. schema 변경 릴리스의 이전 이미지 호환성은 배포 전에 따로 검증해야 한다. 운영 DB 접근·복구·배포 절차는 [runbook](runbook.md)을 따른다.

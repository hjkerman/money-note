# DB 명세

이 문서는 현재 구현된 SQLite DB 기준이다. DB는 서버의 source of truth이며, Excel 파일은 초기 import와 export snapshot에 사용된다.

## 기본 정보

- DB 종류: SQLite
- 기본 경로: `data/money-note.sqlite3`
- 환경변수로 변경 가능: `MONEY_NOTE_DB_PATH`
- 초기화 위치: `backend/app/db.py`

서버 시작 시 `init_db()`가 실행되어 테이블, 인덱스, 기본 설정값, 기본 라벨이 생성된다.

## 전체 구조

테이블:

- `ledger_entries`: 현재 월 기록과 동적으로 append되는 전체 기록
- `archive_rows`: 과거 Excel 전체 기록 시트의 hard data 보존 영역
- `monthly_panels`: 고정지출, 동결, 청구, 타인정산 패널
- `app_settings`: 계산과 서버 동작에 쓰는 설정값
- `workbook_labels`: Excel 표시 문구
- `users`: 로그인 사용자
- `auth_sessions`: 로그인 세션
- `share_sessions`: 가족 공유 페이지 장기 세션
- `cash_flows`: 현금 입출금 기록
- `installments`: 할부 기록
- `card_payment_events`: 즉시결제와 수기 할인액 처리 기록
- `card_payment_allocations`: 결제/할인액의 사용내역별 배분
- `card_payment_deferrals`: 통행료/하이패스 이월과 원본 장부 상태
- `audit_logs`: 변경 API 감사 로그

인덱스:

- `idx_ledger_section_order`
- `idx_ledger_date`
- `idx_archive_rows_order`
- `idx_panels_month_type_order`
- `idx_auth_sessions_token`
- `idx_auth_sessions_user`
- `idx_cash_flows_order`
- `idx_installments_active_order`

## `ledger_entries`

금전 사용 기록의 구조화된 테이블이다.

용도:

- `book_section = current`: `당월 기록` 시트의 메인 기록 테이블
- `book_section = archive`: 월마감 이후 `전체 기록(본인)` 시트 하단에 append되는 동적 기록

스키마:

```sql
CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_section TEXT NOT NULL CHECK (book_section IN ('current', 'archive')),
    entry_kind TEXT NOT NULL DEFAULT 'expense',
    entry_date TEXT,
    date_label TEXT,
    group_label TEXT,
    title TEXT NOT NULL DEFAULT '',
    usage_place TEXT,
    usage_item TEXT,
    amount_value REAL,
    amount_expr TEXT,
    aux_amount_value REAL,
    aux_amount_expr TEXT,
    extra_value TEXT,
    sort_order INTEGER NOT NULL,
    due_day INTEGER,
    confirmed_at TEXT,
    spending_category TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

컬럼:

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER | PK |
| `book_section` | TEXT | `current` 또는 `archive` |
| `entry_kind` | TEXT | `expense`, `planned`, `late_expense` 등 기록 종류 |
| `entry_date` | TEXT | 실제 날짜. `YYYY-MM-DD` |
| `date_label` | TEXT | Excel에 표시할 날짜 문자열. 예: `2026.06.03.` |
| `group_label` | TEXT | 날짜가 아닌 그룹 라벨. 예: `나갈 돈` |
| `title` | TEXT | Excel 호환 적요. 새 당월 지출은 `[사용처] 사용항목` 형식 |
| `usage_place` | TEXT | 앱에서 분리 입력한 사용처 |
| `usage_item` | TEXT | 앱에서 분리 입력한 사용항목 |
| `amount_value` | REAL | 계산 완료된 금액 |
| `amount_expr` | TEXT | Excel 수식 또는 수식 문자열 |
| `aux_amount_value` | REAL | 전체 기록 `E`열 보조 금액 |
| `aux_amount_expr` | TEXT | 전체 기록 `E`열 보조 수식 |
| `extra_value` | TEXT | 전체 기록 `F`열 추가 값 |
| `sort_order` | INTEGER | 사용자 정의 정렬 순서 |
| `due_day` | INTEGER | 카드 정기결제 결제일 |
| `confirmed_at` | TEXT | 확인 처리 시각 |
| `spending_category` | TEXT | `essential`, `questionable`, 또는 `NULL` |
| `payment_key` | TEXT | 월마감 전후에도 유지되는 카드 결제 배분용 고유 키 |
| `created_at` | TEXT | 생성 시각 |
| `updated_at` | TEXT | 수정 시각 |

Excel 매핑:

| Excel 위치 | DB 컬럼 |
| --- | --- |
| `당월 기록!B` | `date_label` 또는 `group_label` |
| `당월 기록!C` | `title` |
| `당월 기록!D` | `amount_value` 또는 `amount_expr` |
| `전체 기록(본인)!B` | `date_label` 또는 `group_label` |
| `전체 기록(본인)!C` | `title` |
| `전체 기록(본인)!D` | `amount_value` 또는 `amount_expr` |
| `전체 기록(본인)!E` | `aux_amount_value` 또는 `aux_amount_expr` |
| `전체 기록(본인)!F` | `extra_value` |

정렬:

```sql
SELECT *
FROM ledger_entries
WHERE book_section = ?
ORDER BY sort_order, id;
```

월마감 규칙:

- `current`의 가장 오래된 미마감 월에 속한 `entry_kind != 'planned'` 행만 `archive`로 복사된다.
- 복사본은 기존 archive 동적 기록의 마지막 `sort_order` 뒤에 붙는다.
- 원본 current 행은 삭제된다.
- `planned` 행은 삭제되지 않는다.
- 현재 달은 매월 27일부터 명시 확인 후 조기 월마감할 수 있다.
- 새 달 기록이 이미 있어도 가장 오래된 미마감 월만 이동한다.
- `last_closed_month` 이하 날짜로 새 일반 지출을 입력하면 `archive`에 바로 추가된다.
- `late_expense`는 카드사가 뒤늦게 매입한 전월 기록이며 처음부터 archive에 추가된다.

## `archive_rows`

과거 Excel `전체 기록(본인)` 시트의 hard data 보존 테이블이다.

도입 이유:

- 과거 기록 중 현재 양식과 칸/적요/보조열 사용 방식이 다른 데이터가 있다.
- 이 데이터는 현재 DB 구조로 무리하게 흡수하지 않고, 원본의 행 단위 hard data로 보존한다.
- export 시 이 영역은 template workbook의 기존 스타일과 값을 가능한 유지하고, 새 archive 기록은 그 아래에 append한다.

스키마:

```sql
CREATE TABLE IF NOT EXISTS archive_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_row INTEGER NOT NULL,
    b_value TEXT,
    c_value TEXT,
    d_value REAL,
    e_value TEXT,
    f_value TEXT,
    merge_down INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

컬럼:

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER | PK |
| `source_row` | INTEGER | 원본 Excel 행 번호 |
| `b_value` | TEXT | 원본 B열 값 |
| `c_value` | TEXT | 원본 C열 값 |
| `d_value` | REAL | 원본 D열 금액 |
| `e_value` | TEXT | 원본 E열 값 |
| `f_value` | TEXT | 원본 F열 값 |
| `merge_down` | INTEGER | B열 병합이 아래로 몇 행 이어지는지 |
| `sort_order` | INTEGER | hard row 정렬 순서 |
| `created_at` | TEXT | 생성 시각 |

append 시작 행 계산:

```text
max(source_row + merge_down) + 1
```

즉, hard archive 영역의 마지막 병합 범위 아래부터 `ledger_entries.book_section = archive` 데이터가 append된다.

## `monthly_panels`

`당월 기록` 시트 우측의 동적 패널 테이블이다.

대상 패널:

- `fixed`: 고정지출
- `frozen`: 동결
- `claim`: 청구
- `settlement`: 타인정산

스키마:

```sql
CREATE TABLE IF NOT EXISTS monthly_panels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,
    panel_type TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    amount_value REAL,
    amount_expr TEXT,
    sort_order INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

컬럼:

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER | PK |
| `month` | TEXT | 대상 월. `YYYY-MM` |
| `panel_type` | TEXT | `fixed`, `frozen`, `claim`, `settlement` |
| `title` | TEXT | 항목명 |
| `amount_value` | REAL | 계산 완료된 금액 |
| `amount_expr` | TEXT | Excel 수식 또는 수식 문자열 |
| `sort_order` | INTEGER | 사용자 정의 정렬 순서 |
| `created_at` | TEXT | 생성 시각 |
| `updated_at` | TEXT | 수정 시각 |

Excel 배치 규칙:

- `fixed` 테이블을 먼저 그린다.
- `frozen` 테이블은 fixed 테이블보다 세 행 아래에 그린다.
- `claim` 테이블은 frozen 테이블보다 세 행 아래에 그린다.
- `settlement` 테이블은 claim 테이블보다 세 행 아래에 그린다.

요약 수식 연동:

- `J4` 송금/예치: `fixed` 패널 금액 범위 합계
- `J6` 동결자산: `frozen` 패널 금액 범위 합계

패널 row count가 바뀌면 export 시 위 수식 범위도 함께 바뀐다.

## `app_settings`

앱/서버 설정값 테이블이다. 현재는 요약 계산의 변경 가능한 값들을 보관한다.

스키마:

```sql
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

기본값:

```sql
INSERT OR IGNORE INTO app_settings(key, value) VALUES
('base_next_month_liquidity', '400000'),
('interest_expense', '0'),
('liquidity_status', '0');
```

설정 key:

| key | 설명 |
| --- | --- |
| `base_next_month_liquidity` | 익월 유동성 계산의 기준 금액 |
| `interest_expense` | 이자지출 |
| `liquidity_status` | 유동성 현황 |
| `settlement_card_limit` | 가족카드 한도 판단 기준 |
| `share_pin_hash` | 가족 공유 PIN의 PBKDF2-SHA256 해시 |
| `share_pin_is_default` | 공유 PIN이 기본값 `0000`이면 `1`, 사용자가 변경했으면 `0` |

익월 유동성 계산:

```text
base_next_month_liquidity
- card_total
- transfer_or_deposit_total
- interest_expense
- frozen_asset_total
+ liquidity_status
```

Excel export 시 `J9`에는 같은 의미의 수식이 기록된다.

## `workbook_labels`

Excel에 표시되는 제목과 라벨을 관리하는 테이블이다. 구조는 고정하되, 표시 문구는 사용자가 바꿀 수 있게 하기 위한 테이블이다.

스키마:

```sql
CREATE TABLE IF NOT EXISTS workbook_labels (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

기본값:

| key | 기본 value | 표시 위치 |
| --- | --- | --- |
| `current_header_date` | 날짜 | `당월 기록!B2` |
| `current_header_title` | 적요 | `당월 기록!C2` |
| `current_header_amount` | 금액 | `당월 기록!D2` |
| `archive_header_date` | 날짜 | `전체 기록(본인)!B2` |
| `archive_header_title` | 적요 | `전체 기록(본인)!C2` |
| `archive_header_amount` | 금액 | `전체 기록(본인)!D2` |
| `panel_fixed_title` | 현금성 고정지출 | fixed 패널 제목 |
| `panel_frozen_title` | 동결 | frozen 패널 제목 |
| `panel_claim_title` | 청구 | claim 패널 제목 |
| `panel_settlement_title` | 타인정산 | settlement 패널 제목 |
| `panel_header_title` | 적요 | 패널 항목명 헤더 |
| `panel_header_amount` | 금액 | 패널 금액 헤더 |
| `summary_title` | 요약 | `당월 기록!I2` |
| `summary_card_total_label` | 카드대금 | `당월 기록!I3` |
| `summary_transfer_or_deposit_label` | 송금/예치 | `당월 기록!I4` |
| `summary_interest_expense_label` | 이자지출 | `당월 기록!I5` |
| `summary_frozen_asset_label` | 동결자산 | `당월 기록!I6` |
| `summary_liquidity_status_label` | 유동성 현황 | `당월 기록!I7` |
| `summary_next_month_liquidity_label` | 익월 유동성 | `당월 기록!I9` |

## `users`

로그인 사용자를 저장하는 테이블이다. 현재 서비스는 1인 사용을 전제로 하지만, 테이블은 여러 사용자를 저장할 수 있게 둔다.

스키마:

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

컬럼:

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER | PK |
| `username` | TEXT | 로그인 ID |
| `password_hash` | TEXT | PBKDF2-SHA256 비밀번호 해시 |
| `display_name` | TEXT | 화면 표시 이름 |
| `is_active` | INTEGER | 활성 여부. `1`이면 활성 |
| `created_at` | TEXT | 생성 시각 |
| `updated_at` | TEXT | 수정 시각 |

비밀번호는 평문으로 저장하지 않는다. 서버는 salt가 포함된 PBKDF2-SHA256 해시를 저장한다.

## `auth_sessions`

로그인 세션을 저장하는 테이블이다. 브라우저에는 raw session token이 HttpOnly cookie로 저장되고, DB에는 token hash만 저장된다.

스키마:

```sql
CREATE TABLE IF NOT EXISTS auth_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

컬럼:

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER | PK |
| `user_id` | INTEGER | `users.id` |
| `session_token_hash` | TEXT | session token의 SHA-256 hash |
| `expires_at` | TEXT | 세션 만료 시각 |
| `created_at` | TEXT | 생성 시각 |
| `last_seen_at` | TEXT | 마지막 사용 시각 |

기본 세션 만료 기간은 `MONEY_NOTE_SESSION_DAYS`로 조정한다.

## `share_sessions`

가족 공유 PIN 통과 후 발급되는 공유 전용 장기 세션이다.

- 본체 로그인 세션과 분리된다.
- raw token은 브라우저 cookie에, SHA-256 token hash는 DB에 저장한다.
- 기본 유효기간은 10년이지만 브라우저 또는 카카오톡 앱이 사이트 데이터를 삭제하면 cookie는 사라질 수 있다.
- 공유 PIN을 변경하면 모든 `share_sessions` 행을 삭제한다.

## `cash_flows`

현금 입출금 기록이다. `liquidity_status` 계산에 더해진다.

주요 컬럼:

| 컬럼 | 설명 |
| --- | --- |
| `occurred_on` | 발생일. `YYYY-MM-DD` |
| `title` | 적요 |
| `amount_value` | 입금은 양수, 출금은 음수 |
| `sort_order` | 정렬 순서 |
| `is_primary_income` | 해당 월 결제 심사의 주 수입이면 `1` |

같은 결제월의 `is_primary_income = 1`인 양수 입금 합계는 파산심사위원회의 기준 수입으로 사용된다.

## `installments`

할부 항목이다. 활성 항목의 월 납입액은 카드대금 요약에 포함된다.

주요 컬럼:

| 컬럼 | 설명 |
| --- | --- |
| `title` | 적요 |
| `principal_amount` | 할부 원금 |
| `fee_rate` | 수수료율 |
| `fee_amount` | `principal_amount * fee_rate / 100`을 원 단위 올림한 값 |
| `months` | 총 개월수 |
| `remaining_months` | 남은 개월수 |
| `start_month` | 시작 월. `YYYY-MM` |
| `is_active` | 활성 여부 |

월마감 시 활성 할부의 `remaining_months`가 1 줄고, 0이 되면 `is_active = 0`이 된다.

## `card_payment_events`

한 번의 즉시결제 또는 수기 할인액 처리를 기록한다.

| 컬럼 | 설명 |
| --- | --- |
| `event_date` | 처리일. 즉시결제/할인은 익월 14일까지 허용 |
| `event_type` | `immediate` 또는 `discount` |
| `total_amount` | 해당 event의 allocation 합계 |
| `note` | 선택적 메모 |
| `cash_flow_id` | 즉시결제에서 자동 생성된 현금흐름 ID. 할인은 `NULL` |

## `card_payment_allocations`

결제 event의 금액을 원래 카드 사용내역에 배분한다.

| 컬럼 | 설명 |
| --- | --- |
| `payment_event_id` | `card_payment_events.id` |
| `entry_payment_key` | 월마감 전후에도 유지되는 `ledger_entries.payment_key` |
| `amount_value` | 해당 사용내역에 배분한 즉시결제 또는 할인액 |

하나의 사용내역에 여러 번 일부결제할 수 있고, 한 번의 결제 event를 여러 사용내역에 나눠 배분할 수 있다.

단, 적요에 `통행료` 또는 `하이패스`가 포함된 항목은 할인과 일부결제를 허용하지 않고 남은 금액 전액만 즉시결제할 수 있다.

## `card_payment_deferrals`

통행료/하이패스 항목을 다음 결제월로 이월할 때 원본 장부 상태를 보관한다.

| 컬럼 | 설명 |
| --- | --- |
| `entry_payment_key` | 이월한 `ledger_entries.payment_key`. PK |
| `from_payment_month` | 이월을 선택한 결제월 |
| `target_payment_month` | 실제 처리 대상으로 넘긴 다음 결제월 |
| `original_book_section` | 이월 전 `current` 또는 `archive` |
| `original_entry_date` | 이월 전 실제 날짜 |
| `original_date_label` | 이월 전 표시 날짜 |
| `original_group_label` | 이월 전 그룹 라벨 |
| `original_title` | 이월 전 적요 |
| `original_sort_order` | 이월 전 정렬 위치 |

이월 시 원본 `ledger_entries` 행 자체를 현재 월 장부 맨 앞으로 옮긴다.

- `book_section = current`
- 내부 `entry_date = 이월을 선택한 결제월의 1일`
- 화면/Excel 표시 날짜인 `date_label`, `group_label`은 빈 문자열
- `title` 앞에는 `[이월]` 추가
- 기존 현재 월 장부의 최소 `sort_order`보다 1 작은 값을 사용해 맨 앞에 배치

같은 결제월에 `이번 달에 처리`를 선택하면 보관한 원본 상태를 복원하고 이월 행을 삭제한다. 월마감 후에는 `[이월]` 장부 행이 일반 당월 사용내역처럼 archive로 이동한다.

## 청구·타인정산 처리

`monthly_panels`의 `claim`, `settlement` 항목은 장기 기록이 아니라 가족에게 전달하기 전까지 유지하는 임시 큐다. 미마감 장부 월과 무관하게 달력상 현재 연-월을 사용한다. `일괄 처리 완료` 시 선택한 타입의 현재 월 행을 삭제한다. 이 동작은 다른 패널 타입과 월마감에 영향을 주지 않는다.

## `audit_logs`

변경 API의 최소 감사 정보를 저장한다.

| 컬럼 | 설명 |
| --- | --- |
| `occurred_at` | 요청 처리 시각 |
| `actor_username` | 로그인 사용자명. 인증 전 요청은 `anonymous` |
| `method` | `POST`, `PATCH`, `DELETE` |
| `path` | API 경로. query와 요청 본문은 저장하지 않음 |
| `status_code` | HTTP 결과 코드 |

`DELETE /api/audit-logs`는 전체 행을 삭제하며, 초기화 요청 자체는 다시 기록하지 않는다.

## Export와 DB의 관계

export 입력:

- `archive_rows`
- `ledger_entries WHERE book_section = 'archive'`
- `ledger_entries WHERE book_section = 'current'`
- `monthly_panels`
- `workbook_labels`
- `app_settings`
- 할부는 Excel export에 별도 표로 쓰지 않고, 요약의 카드대금 계산에 반영한다.

export 정책:

- 원본 template workbook이 있으면 기존 시트 스타일과 hard archive 영역을 유지한다.
- `당월 기록`은 DB의 current 기록과 monthly panel 기준으로 다시 그린다.
- `전체 기록(본인)`의 hard archive 영역은 보존하고, dynamic archive 기록은 그 아래에 append한다.
- 현재 월 메인 기록의 날짜 셀은 같은 날짜가 연속되면 B열을 병합한다.
- archive append 기록의 날짜 셀도 같은 날짜가 연속되면 B열을 병합한다.
- 월마감으로 append된 직전월 기록은 노란 배경으로 표시한다.

## Import와 DB의 관계

초기 import는 `backend/scripts/import_xlsx.py`가 수행한다.

동작:

- `당월 기록`의 메인 기록을 `ledger_entries.current`로 읽는다.
- `당월 기록`의 우측 패널을 `monthly_panels`로 읽는다.
- `전체 기록(본인)`의 기존 기록은 `archive_rows` hard data로 읽는다.
- 요약 계산 기준값은 `app_settings`로 읽는다.
- Excel 표시 문구는 `workbook_labels`로 읽는다.

`--replace` 옵션을 사용하면 기존 `ledger_entries`, `archive_rows`, `monthly_panels`, `workbook_labels`를 비우고 다시 import한다. `app_settings`는 key 단위 upsert로 갱신된다.

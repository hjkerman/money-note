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

인덱스:

- `idx_ledger_section_order`
- `idx_ledger_date`
- `idx_archive_rows_order`
- `idx_panels_month_type_order`

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
    amount_value REAL,
    amount_expr TEXT,
    aux_amount_value REAL,
    aux_amount_expr TEXT,
    extra_value TEXT,
    sort_order INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

컬럼:

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER | PK |
| `book_section` | TEXT | `current` 또는 `archive` |
| `entry_kind` | TEXT | `expense`, `planned` 등 기록 종류 |
| `entry_date` | TEXT | 실제 날짜. `YYYY-MM-DD` |
| `date_label` | TEXT | Excel에 표시할 날짜 문자열. 예: `2026.06.03.` |
| `group_label` | TEXT | 날짜가 아닌 그룹 라벨. 예: `나갈 돈` |
| `title` | TEXT | 적요 |
| `amount_value` | REAL | 계산 완료된 금액 |
| `amount_expr` | TEXT | Excel 수식 또는 수식 문자열 |
| `aux_amount_value` | REAL | 전체 기록 `E`열 보조 금액 |
| `aux_amount_expr` | TEXT | 전체 기록 `E`열 보조 수식 |
| `extra_value` | TEXT | 전체 기록 `F`열 추가 값 |
| `sort_order` | INTEGER | 사용자 정의 정렬 순서 |
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

- `current`의 `entry_kind != 'planned'`인 행은 `archive`로 복사된다.
- 복사본은 기존 archive 동적 기록의 마지막 `sort_order` 뒤에 붙는다.
- 원본 current 행은 삭제된다.
- `planned` 행은 삭제되지 않는다.

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
| `panel_fixed_title` | 고정지출 | fixed 패널 제목 |
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

## Export와 DB의 관계

export 입력:

- `archive_rows`
- `ledger_entries WHERE book_section = 'archive'`
- `ledger_entries WHERE book_section = 'current'`
- `monthly_panels`
- `workbook_labels`
- `app_settings`

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


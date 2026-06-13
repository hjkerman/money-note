# DB 명세

이 문서는 현재 구현된 SQLite DB 기준이다. 서버 DB가 source of truth다.

## 공통 규칙

- 날짜는 `YYYY-MM-DD` 문자열이다.
- 월은 `YYYY-MM` 문자열이다.
- 돈은 원 단위 정수로 저장한다. 수수료율 같은 비율만 소수를 허용한다.
- `created_at`, `updated_at`은 SQLite `CURRENT_TIMESTAMP` 문자열이다.

## 주요 테이블

- `ledger_entries`: 당월/전체 지출, 카드 정기결제, 전월 매입 지연 보정
- `monthly_panels`: 현금성 고정지출, 동결, 청구, 가족카드
- `app_settings`: 유동성, 이자지출, 카드 한도 등 설정값
- `app_labels`: 화면 표시 문구
- `cash_flows`: 현금 입출금
- `card_payment_events`: 즉시결제/할인액 처리 이벤트
- `card_payment_allocations`: 결제/할인 이벤트의 항목별 배분
- `card_payment_deferrals`: 통행료/하이패스 이월 상태
- `users`: 본체 사용자 계정
- `auth_sessions`: 본체 로그인 세션
- `share_sessions`: 가족 공유 페이지 세션
- `audit_logs`: 변경 API 감사 로그

## `ledger_entries`

장부의 중심 테이블이다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER PK | 내부 식별자 |
| `book_section` | TEXT | `current` 또는 `archive` |
| `entry_kind` | TEXT | `expense`, `planned`, `late_expense` 등 |
| `entry_date` | TEXT | 사용일 |
| `date_label` | TEXT | 화면 표시용 날짜 보조 문자열 |
| `group_label` | TEXT | 화면 표시용 그룹 보조 문자열 |
| `title` | TEXT | 대표 적요 |
| `usage_place` | TEXT | 사용처 |
| `usage_item` | TEXT | 사용항목 |
| `amount_value` | REAL | 사용금액 |
| `amount_expr` | TEXT | 과거 호환용 문자열 필드 |
| `aux_amount_value` | REAL | 보조 금액 |
| `aux_amount_expr` | TEXT | 보조 금액 문자열 |
| `extra_value` | TEXT | 기타 값 |
| `sort_order` | INTEGER | 정렬 순서 |
| `due_day` | INTEGER | 카드 정기결제일 |
| `confirmed_at` | TEXT | 확인 처리 시각 |
| `confirmed_month` | TEXT | 카드 정기결제를 확인한 대상 월 |
| `spending_category` | TEXT | `essential`, `questionable`, `dignity`, 또는 `NULL` |
| `payment_key` | TEXT | 카드 결제/할인 배분용 안정 키 |

정렬:

- 카드 정기결제는 `due_day`, `sort_order`, `id` 순
- 일반 지출은 `entry_date`, `sort_order`, `id` 순

## `monthly_panels`

당월 하위 큐 성격의 테이블이다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER PK | 내부 식별자 |
| `month` | TEXT | 대상 월 |
| `panel_type` | TEXT | `fixed`, `frozen`, `claim`, `family_card` |
| `title` | TEXT | 적요 |
| `spent_on` | TEXT | 사용일 |
| `amount_value` | REAL | 금액 |
| `discount_amount` | REAL | 할인액 |
| `amount_expr` | TEXT | 과거 호환용 문자열 필드 |
| `sort_order` | INTEGER | 정렬 순서 |
| `due_day` | INTEGER | 필요 시 사용하는 결제일 |
| `confirmed_at` | TEXT | 처리 완료 시각 |

정렬:

- 날짜가 있는 행이 먼저 온다.
- 같은 날짜 안에서는 `sort_order`, `id` 순이다.

## `app_settings`

앱 설정값이다.

| key | 의미 |
| --- | --- |
| `base_next_month_liquidity` | 이달 기준 수입 기록이 없을 때 쓰는 기본 예정 수입 |
| `interest_expense` | 이자 지출 |
| `liquidity_status` | 현재 유동성 현황 |
| `card_limit` | 본인카드와 가족카드 합산 사용률을 판단할 카드 한도 |
| `owner_card_last4` | 본인회원 카드 끝 4자리 |
| `family_card_last4` | 가족카드 끝 4자리 |

## `app_labels`

화면 표시 문구를 저장한다.

대표 key:

| key | 의미 |
| --- | --- |
| `panel_fixed_title` | 현금성 고정지출 제목 |
| `panel_frozen_title` | 동결 제목 |
| `panel_claim_title` | 청구 제목 |
| `panel_family_card_title` | 가족카드 제목 |
| `panel_family_card_title` | 가족카드 제목 |
| `summary_title` | 요약 제목 |
| `summary_card_total_label` | 카드대금 라벨 |
| `summary_next_month_liquidity_label` | 익월 유동성 라벨 |

## `cash_flows`

현금 입출금 기록이다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER PK | 내부 식별자 |
| `occurred_on` | TEXT | 발생일 |
| `title` | TEXT | 적요 |
| `amount_value` | REAL | 입금은 양수, 출금은 음수 |
| `sort_order` | INTEGER | 정렬 순서 |
| `is_primary_income` | INTEGER | 이달 기준 수입이면 `1` |

## 카드 결제 테이블

### `card_payment_events`

즉시결제와 할인액 처리 이벤트다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `event_date` | TEXT | 처리일 |
| `event_type` | TEXT | `immediate` 또는 `discount` |
| `total_amount` | REAL | 처리 총액 |
| `note` | TEXT | 메모 |
| `cash_flow_id` | INTEGER | 즉시결제가 만든 현금흐름 id |

### `card_payment_allocations`

이벤트 금액을 사용내역별로 배분한다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `payment_event_id` | INTEGER | `card_payment_events.id` |
| `entry_payment_key` | TEXT | `ledger_entries.payment_key` |
| `amount_value` | REAL | 배분 금액 |

### `card_payment_deferrals`

통행료/하이패스 이월 상태다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `entry_payment_key` | TEXT PK | 이월된 사용내역의 `payment_key` |
| `from_payment_month` | TEXT | 원래 결제월 |
| `target_payment_month` | TEXT | 이월 목표 결제월 |
| `original_*` | 여러 컬럼 | 이월 취소를 위한 원래 장부 상태 |

## 사용자와 세션

### `users`

본체 사용자의 로그인 정보를 저장한다. 현재 운용 전제는 1인 사용자다.

### `auth_sessions`

본체 로그인 세션이다. 브라우저 cookie 또는 bearer token으로 사용된다.

### `share_sessions`

청구/가족카드 공유 페이지용 세션이다. 본체 로그인과 분리된다.

## `audit_logs`

변경 API의 사용자, 메서드, 경로, 상태 코드만 저장한다. 요청 본문, 비밀번호, 세션 토큰은 저장하지 않는다.

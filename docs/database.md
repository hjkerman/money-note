# DB 명세

이 문서는 현재 구현된 SQLite DB 기준이다. 서버 DB가 source of truth다.

## 공통 규칙

- 날짜는 `YYYY-MM-DD` 문자열이다.
- 월은 `YYYY-MM` 문자열이다.
- 돈은 원 단위 정수로 저장한다. 수수료율 같은 비율만 소수를 허용한다.
- 금액 컬럼은 새 DB 생성 시 `INTEGER` 타입을 사용한다.
- 구버전 JSON snapshot/백업에 `1000.0` 또는 `1000.9`처럼 float 금액이 들어 있으면 restore/import 시 소수점 아래를 절삭해 `1000`으로 정규화한다.
- 일반 API 입력에서는 원화 금액을 정수로 보내는 것을 원칙으로 한다.
- `created_at`, `updated_at`은 SQLite `CURRENT_TIMESTAMP` 문자열이다.
- 할인 정책, 자동/유효 할인액, 실결제액, 교통·통행 태그는 DB 중복 컬럼이 아니라 조회 시 서버가 만드는 API 투영값이다.

## 주요 테이블

- `ledger_entries`: 당월/전체 지출, 카드 정기결제, 전월 매입 지연 보정
- `monthly_panels`: 현금성 고정지출, 동결, 청구, 가족카드
- `app_settings`: 유동성, 카드 한도 등 설정값
- `app_labels`: 화면 표시 문구
- `cash_flows`: 현금 입출금
- `card_payment_batches`: 월마감이 만든 이번달 결제 작업함
- `card_payment_batch_items`: 결제 작업함에 포함된 원장 항목
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
| `amount_value` | INTEGER | 사용금액. 원화 정수 금액 |
| `amount_expr` | TEXT | 과거 호환용 문자열 필드 |
| `aux_amount_value` | INTEGER | 원장 항목의 수동 할인액 override. 실결제액 직접 수정 시 `amount_value - 실결제액`을 원화 정수 금액으로 저장한다. |
| `aux_amount_expr` | TEXT | 보조 금액 문자열 |
| `extra_value` | TEXT | 기타 값 |
| `sort_order` | INTEGER | 정렬 순서 |
| `due_day` | INTEGER | 카드 정기결제일 |
| `confirmed_at` | TEXT | 확인 처리 시각 |
| `confirmed_month` | TEXT | 카드 정기결제를 확인한 대상 월 |
| `source_planned_entry_id` | INTEGER nullable FK | 카드 정기결제 확인으로 생성된 지출이 참조하는 원본 planned 템플릿 id. 템플릿 삭제 시 `NULL` |
| `spending_category` | TEXT | `essential`, `questionable`, `dignity`, 또는 `NULL` |
| `payment_key` | TEXT | 카드 결제/할인 배분용 안정 키 |
| `discount_override` | INTEGER | `1`이면 기본 할인 계산 대신 `aux_amount_value`를 수동 할인액으로 사용 |

정렬:

- 카드 정기결제는 `due_day`, `sort_order`, `id` 순
- 일반 지출은 `entry_date`, `sort_order`, `id` 순

API의 `discount_policy`, `automatic_discount_eligible`, `automatic_discount_amount`, `effective_discount_amount`, `effective_amount_value`, `is_transport`, `is_toll`은 이 테이블 컬럼이 아니다. 서버의 `card_charge` 모듈이 원본 금액, 사용월, 카드 종류, 월 정책과 수동 override를 결합해 응답에만 덧붙인다.

## `monthly_panels`

당월 하위 큐 성격의 테이블이다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER PK | 내부 식별자 |
| `month` | TEXT | 대상 월 |
| `panel_type` | TEXT | `fixed`, `frozen`, `claim`, `family_card` |
| `title` | TEXT | 적요 |
| `spent_on` | TEXT | 사용일. `frozen`에서는 등록일자, 확인된 `fixed`에서는 실제 처리일 |
| `amount_value` | INTEGER | 금액. 원화 정수 금액 |
| `discount_amount` | INTEGER | 청구/가족카드 항목의 수동 할인액 override. 원화 정수 금액 |
| `discount_override` | INTEGER | `1`이면 기본 할인 계산 대신 `discount_amount`를 수동 할인액으로 사용 |
| `amount_expr` | TEXT | 과거 호환용 문자열 필드 |
| `sort_order` | INTEGER | 정렬 순서 |
| `due_day` | INTEGER | 필요 시 사용하는 결제일 |
| `confirmed_at` | TEXT | 처리 완료 시각 |
| `confirmed_month` | TEXT | 현금성 고정지출을 확인한 예산 주기 `YYYY-MM`. 밀린 월마감의 reset 범위를 제한한다. |
| `confirmed_cash_flow_id` | INTEGER nullable FK | 확인된 현금성 고정지출이 생성한 `cash_flows.id`. 월마감 후 다음 주기에는 `NULL` |

정렬:

- 날짜가 있는 행이 먼저 온다.
- 같은 날짜 안에서는 `sort_order`, `id` 순이다.

API의 할인 정책·자동 할인·유효 할인·실결제 투영 필드는 이 테이블에 저장하지 않는다. 원본 금액과 수동 override만 저장하고 최종값은 서버가 매 조회 때 계산한다.

`fixed` 확인은 템플릿 삭제나 금액 수정이 아니다. `monthly_panels.amount_value`는 다음 주기에도 유지되는 reserve/upper bound다. 이번 주기의 실제 출금액은 연결된 `cash_flows.amount_value`에 음수로 저장하며, API의 `confirmed_amount_value`는 이 연결 행의 절댓값을 조회 시 투영한다. `confirmed_at`과 유효한 `confirmed_cash_flow_id`가 함께 있어야 완료 상태다. 실제액이 reserve와 다르면 그 차이만큼 잔여 유동성이 확인 시 조정된다. 월마감은 확인 필드와 연결만 비워 다음 주기 템플릿을 재활성화하며 기존 현금흐름을 삭제하지 않는다.

확인 처리일은 서버 기준 오늘보다 미래일 수 없다. `confirmed_month`는 실제 처리일의 월이며, 월마감은 마감 대상 월과 같은 값인 템플릿만 reset한다. 따라서 밀린 과거 월마감이 더 나중 주기에 확인한 고정지출을 되돌리지 않는다.

카드 정기결제 template은 `ledger_entries.entry_kind='planned'` 행의 `amount_value`에 예정 원금을 유지한다. 이번 주기 실제 원금은 확인으로 생성된 `expense.amount_value`에 저장되고 `source_planned_entry_id`가 template을 가리킨다. 할인과 실결제액은 기존 원장 필드와 서버 카드 정책을 그대로 사용한다. 따라서 별도 actual 컬럼이나 Snapshot 필드는 없다. Snapshot v7은 기존 `monthly_panels`, `cash_flows`, `ledger_entries` 관계를 함께 보존하므로 reserve와 실제액을 모두 복원한다.

카드 계산식 자체는 DB 컬럼이나 테이블로 저장하지 않는다. 본인·가족·통행료·교통카드의 사용월별 계산식 이력은 서버 코드의 `card_charge` 레지스트리가 관리한다. 본인/가족 월별 혜택 여부와 교통카드의 월별 프로필 선택 이력만 `app_settings`에 저장한다. 이 분리는 카드 교체 시 새 효력 시작월을 추가하면서 과거 Snapshot과 거래를 기존 정책으로 재계산할 수 있게 한다.

## `app_settings`

앱 설정값이다.

| key | 의미 |
| --- | --- |
| `scheduled_income` | 다음 월마감 실행일에 실제 `급여` 현금 유입으로 확정할 기본 예정 수입. 반복 설정값이며 Summary 잔여 유동성에는 직접 더하지 않음 |
| `cash_flow_balance` | Active 계좌의 초기·수동 보정값. Summary에서는 서버 기준일까지 발생한 현금흐름 누계와 합산한다. |
| `card_limit` | 본인카드와 가족카드 합산 사용률을 판단할 카드 한도 |
| `owner_card_last4` | 본인회원 카드 끝 4자리 |
| `family_card_last4` | 가족카드 끝 4자리 |
| `card_discount_policy:owner:{YYYY-MM}` | 해당 월 본인카드 혜택 `enabled`/`disabled` |
| `card_discount_policy:family:{YYYY-MM}` | 해당 월 가족카드 혜택 `enabled`/`disabled` |
| `card_charge_profile:transit:{YYYY-MM}` | 해당 월부터 적용할 교통카드 프로필 `none`/`owner` |

교통카드 프로필은 거래 사용월보다 늦지 않은 가장 최근 설정을 선택한다. `owner`는 본인카드 계산식뿐 아니라 해당 사용월의 본인카드 혜택 상태까지 따른다. 키가 없으면 구버전과 같은 `none`으로 해석한다. 현재 구현은 월 단위 이력이므로 같은 월 안에서 설정 전후 거래를 나누지 않는다.

## `app_labels`

화면 표시 문구를 저장한다.

대표 key:

| key | 의미 |
| --- | --- |
| `panel_fixed_title` | 현금성 고정지출 제목 |
| `panel_frozen_title` | 동결 제목 |
| `panel_claim_title` | 청구 제목 |
| `panel_family_card_title` | 가족카드 제목 |
| `summary_title` | 요약 제목 |
| `summary_card_total_label` | 카드대금 라벨 |
| `summary_cash_flow_balance_label` | 현금흐름 반영액 라벨 |
| `summary_remaining_liquidity_label` | 잔여 유동성 라벨 |

서버 시작 시 기존 DB의 유동성 설정·라벨 key를 트랜잭션 안에서 현재 이름으로 이동한다. 새 key가 없으면 기존 값을 옮기고, 둘이 같은 값이면 새 key를 유지한 뒤 기존 key를 삭제한다. 값이 다르면 조용히 덮어쓰지 않고 시작을 중단한다. 사용자 지정 라벨 값은 key만 이동하고 그대로 보존한다.

구 DB migration 전용 대응표:

- `base_next_month_liquidity` → `scheduled_income`
- `liquidity_status` → `cash_flow_balance`
- `summary_liquidity_status_label` → `summary_cash_flow_balance_label`
- `summary_next_month_liquidity_label` → `summary_remaining_liquidity_label`

## `cash_flows`

현금 입출금 기록이다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER PK | 내부 식별자 |
| `occurred_on` | TEXT | 발생일 |
| `title` | TEXT | 적요 |
| `amount_value` | INTEGER | 입금은 양수, 출금은 음수. 원화 정수 금액 |
| `sort_order` | INTEGER | 정렬 순서 |
| `is_primary_income` | INTEGER | 이달 기준 수입이면 `1` |

월마감이 성공하면 월마감 실행일로 `title='급여'`, `amount_value=scheduled_income`, `is_primary_income=1`인 행을 생성한다. 사용자가 월마감과 함께 실제 자금을 꺼낸 것으로 보므로 생성 즉시 Summary의 `cash_flow_balance`에 포함한다. 별도 누적 설정은 사용하지 않는다. 이 행은 일반 현금흐름과 동일하게 Snapshot 및 pre_restore에 포함되고 장부 전체 초기화 대상이다.

## 카드 결제 테이블

### `card_payment_batches`

월마감 직후 생성되는 결제 작업함이다.

카드 결제 화면은 달력상 직전월을 자동 조회하지 않고, 현재 활성 batch만 본다. 새 월마감이 실행되면 이전 batch와 그 즉시결제/할인 이벤트는 임시 작업 데이터로 보고 삭제된다. 사용자는 이전 batch를 다시 선택하지 않는다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER PK | 내부 식별자 |
| `usage_month` | TEXT | 월마감된 사용월. 예: `2026-06` |
| `source` | TEXT | 생성 원인. 현재는 `month_close` |
| `status` | TEXT | 현재는 `active` 중심으로 사용 |
| `created_at` | TEXT | 생성 시각 |

### `card_payment_batch_items`

활성 결제 작업함에 포함된 원장 항목 목록이다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | INTEGER PK | 내부 식별자 |
| `batch_id` | INTEGER | `card_payment_batches.id` |
| `entry_id` | INTEGER | `ledger_entries.id` |
| `entry_payment_key` | TEXT | `ledger_entries.payment_key` |
| `created_at` | TEXT | 생성 시각 |

### `card_payment_events`

즉시결제와 할인액 처리 이벤트다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `batch_id` | INTEGER | 이 이벤트가 속한 `card_payment_batches.id` |
| `event_date` | TEXT | 처리일 |
| `event_type` | TEXT | `immediate` 또는 `discount` |
| `total_amount` | INTEGER | 처리 총액. 원화 정수 금액 |
| `note` | TEXT | 메모 |
| `cash_flow_id` | INTEGER | 즉시결제가 만든 현금흐름 id |
| `idempotency_key` | TEXT nullable unique | 논리적으로 같은 결제 요청의 재전송을 식별하는 client key. 구버전 행은 `NULL` |
| `request_fingerprint` | TEXT nullable | 날짜, 유형, 메모, 배분을 canonical하게 정규화한 SHA-256. 같은 key의 payload 변경을 거부한다. |

### `card_payment_allocations`

이벤트 금액을 사용내역별로 배분한다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `payment_event_id` | INTEGER | `card_payment_events.id` |
| `entry_payment_key` | TEXT | `ledger_entries.payment_key` |
| `amount_value` | INTEGER | 배분 금액. 원화 정수 금액 |

### `card_payment_deferrals`

통행료/하이패스 이월 상태다.

이월은 결제 작업함에서는 다음 결제월로 넘기는 선택이지만, 원장에서는 다음 달 맨 위에 `[이월] [n월 사용 내역] ...` 형태로 남는다. 이유는 이월된 금액이 다음 결제월의 유동성에 영향을 주기 때문이다. 다만 이 원장 항목은 그 달 월마감 전까지 결제 작업함에 자동 노출되지 않는다. 해당 달을 월마감하면 새 batch에 편입된다.

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

## 시작 시 additive migration

기존 운영 DB는 서버 시작 시 파괴적 재생성 없이 다음 nullable 컬럼과 인덱스를 추가한다.

- `ledger_entries.source_planned_entry_id`
- `monthly_panels.confirmed_month`
- `card_payment_events.idempotency_key`
- `card_payment_events.request_fingerprint`
- nullable idempotency key의 부분 unique index와 planned 관계 조회 index

기존에 연결된 현금성 고정지출은 유효한 `spent_on`에서 `confirmed_month`를 backfill한다. 과거 정기결제 지출은 관계를 추측해 DB에 기록하지 않으며, 조회 경계에서만 기존 제목·금액 매칭을 호환 fallback으로 사용한다. 구버전 카드 결제 이벤트의 idempotency 필드는 `NULL`로 남는다.

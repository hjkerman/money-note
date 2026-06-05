# CSV 백업 포맷

이 문서는 `money-note`의 CSV 백업 zip 포맷을 설명한다. 이 포맷은 SQLite 내부 구현을 다른 서버나 새 앱으로 옮길 때 참고할 수 있는 장기 보존용 계약으로 취급한다.

## 파일 형식

CSV 백업은 하나의 `.zip` 파일이다.

파일명 예시:

```text
money-note-csv-backup-20260605-093012.zip
```

zip 내부에는 `manifest.csv`와 테이블별 CSV 파일이 들어간다.

```text
manifest.csv
ledger_entries.csv
monthly_panels.csv
app_settings.csv
app_labels.csv
cash_flows.csv
installments.csv
card_payment_events.csv
card_payment_allocations.csv
card_payment_deferrals.csv
```

## 공통 규칙

- 문자 인코딩은 UTF-8이다.
- 각 CSV의 첫 줄은 헤더다.
- 헤더명은 DB 컬럼명과 같다.
- 빈 문자열은 import 시 `NULL`로 복원한다.
- 돈 금액은 원 단위 정수 문자열로 저장한다. 비율인 `fee_rate`만 소수일 수 있다.
- 날짜는 `YYYY-MM-DD`, 월은 `YYYY-MM` 문자열을 사용한다.
- `created_at`, `updated_at` 같은 시각 문자열은 그대로 보존한다.
- 사용자 계정, 세션, 공유 세션, 감사 로그는 백업 대상이 아니다.

## manifest.csv

백업 파일의 최소 식별 정보다.

| key | 의미 |
| --- | --- |
| `format` | 항상 `money-note-csv-backup` |
| `created_at` | 백업 생성 시각. 파일명과 같은 `YYYYMMDD-HHMMSS` 형식 |
| `tables` | 포함된 테이블명 목록. 세미콜론으로 구분 |

## ledger_entries.csv

당월/전체 기록과 카드 정기결제를 저장한다.

주요 컬럼:

| 컬럼 | 의미 |
| --- | --- |
| `id` | 내부 식별자 |
| `book_section` | `current` 또는 `archive` |
| `entry_kind` | 일반 지출은 `expense`, 카드 정기결제는 `planned`, 전월 보정은 `late_expense` |
| `entry_date` | 사용일 |
| `date_label`, `group_label` | 화면 표시용 보조 문자열 |
| `title` | 대표 적요 |
| `usage_place` | 사용처 |
| `usage_item` | 사용항목 |
| `amount_value` | 사용금액 |
| `due_day` | 카드 정기결제일 |
| `confirmed_at` | 확인 처리 시각 |
| `confirmed_month` | 카드 정기결제를 확인한 대상 월 |
| `spending_category` | `essential`, `questionable`, `dignity`, 또는 빈 값 |
| `payment_key` | 카드 결제 allocation이 참조하는 안정 키 |

## monthly_panels.csv

현금성 고정지출, 동결, 청구, 타인정산을 저장한다.

| 컬럼 | 의미 |
| --- | --- |
| `month` | 대상 월 |
| `panel_type` | `fixed`, `frozen`, `claim`, `settlement` |
| `title` | 적요 |
| `spent_on` | 사용일. 청구/타인정산에서 주로 사용 |
| `amount_value` | 금액 |
| `discount_amount` | 할인액 |
| `due_day` | 필요 시 사용하는 결제일 |
| `confirmed_at` | 처리 완료 시각 |

## app_settings.csv

앱 설정값이다.

대표 key:

| key | 의미 |
| --- | --- |
| `base_next_month_liquidity` | 주 수입 기록이 없을 때 쓰는 기본 유동성 기준 |
| `interest_expense` | 이자 지출 |
| `liquidity_status` | 현재 유동성 현황 |
| `settlement_card_limit` | 가족카드 한도 감시 기준 |

## app_labels.csv

화면에 표시되는 라벨을 저장한다. 기능 구조는 유지하되 문구만 바꾸고 싶을 때 사용한다.

예:

| key | 의미 |
| --- | --- |
| `panel_fixed_title` | 현금성 고정지출 제목 |
| `panel_frozen_title` | 동결 제목 |
| `panel_claim_title` | 청구 제목 |
| `panel_settlement_title` | 타인정산 제목 |
| `summary_title` | 요약 제목 |

## cash_flows.csv

현금 입출금 기록이다.

| 컬럼 | 의미 |
| --- | --- |
| `occurred_on` | 발생일 |
| `title` | 적요 |
| `amount_value` | 입금은 양수, 출금은 음수 |
| `is_primary_income` | 주 수입이면 `1`, 아니면 `0` |

## installments.csv

할부 기록이다.

| 컬럼 | 의미 |
| --- | --- |
| `title` | 적요 |
| `principal_amount` | 원금 |
| `fee_rate` | 수수료율 |
| `fee_amount` | 수수료 |
| `months` | 전체 개월 수 |
| `remaining_months` | 남은 개월 수 |
| `start_month` | 시작 월 |
| `is_active` | 활성 여부 |

## card_payment_events.csv

즉시결제와 할인액 처리 이벤트다.

| 컬럼 | 의미 |
| --- | --- |
| `event_date` | 처리일 |
| `event_type` | `immediate` 또는 `discount` |
| `total_amount` | 처리 총액 |
| `note` | 메모 |
| `cash_flow_id` | 즉시결제가 만든 현금흐름 id. 할인은 보통 비어 있다 |

## card_payment_allocations.csv

결제/할인 이벤트가 어떤 카드 사용내역에 얼마씩 배분됐는지 저장한다.

| 컬럼 | 의미 |
| --- | --- |
| `payment_event_id` | `card_payment_events.id` |
| `entry_payment_key` | `ledger_entries.payment_key` |
| `amount_value` | 배분 금액 |

## card_payment_deferrals.csv

통행료/하이패스 이월 상태를 저장한다.

| 컬럼 | 의미 |
| --- | --- |
| `entry_payment_key` | 이월된 사용내역의 `payment_key` |
| `from_payment_month` | 원래 결제월 |
| `target_payment_month` | 이월 목표 결제월 |
| `original_*` | 이월 취소를 위해 보관하는 원래 장부 상태 |

## Import 정책

CSV 복원은 기존 가계부 운용 데이터를 백업 내용으로 교체한다.

복원 대상:

- `ledger_entries`
- `monthly_panels`
- `app_settings`
- `app_labels`
- `cash_flows`
- `installments`
- `card_payment_events`
- `card_payment_allocations`
- `card_payment_deferrals`

복원하지 않는 것:

- `users`
- `auth_sessions`
- `share_sessions`
- `audit_logs`

즉, 복원 후에도 로그인 계정과 공유 세션, 관리 로그는 그대로 남는다.

## 재개발 시 주의점

- `payment_key`는 결제/할인 배분의 핵심 참조값이므로 새 시스템에서도 보존해야 한다.
- `id`는 같은 DB 안에서만 안정적이다. 새 시스템으로 옮길 때는 `payment_key`, 날짜, 정렬값을 함께 사용해 참조를 재구성하는 편이 안전하다.
- `sort_order`는 같은 날짜 안의 입력 순서를 보존하기 위한 값이다.
- 청구/타인정산은 전달용 임시 큐라 일괄 처리 후 사라질 수 있다.
- 감사 로그는 백업하지 않는다. 백업 파일은 장부 복원용이지 행위 추적 보존용이 아니다.

# CSV 데이터 덤프 포맷

`money-note`의 CSV 백업은 장부 데이터를 장기 보존하기 위한 raw data dump다.
목표는 과거 DB 스키마를 완벽히 재현하는 것이 아니라, 나중에 컬럼이 늘거나 줄어도 실제 튜플을 최대한 살려 import하는 것이다.

## 파일 형식

다운로드되는 파일은 CSV 한 개다.

```text
money-note-data-dump-20260605-093012.csv
```

모든 행에는 `__table` 컬럼이 있다.
이 값이 해당 행을 어느 DB 테이블에 넣을지 결정한다.

예:

```csv
__table,__key,__value,id,book_section,title,amount_value
__meta,format,money-note-data-dump,,,,
ledger_entries,,,1,current,[어딘가] 세부내역,12000
monthly_panels,,,1,,청구 항목,30000
```

`__meta` 행은 데이터가 아니라 덤프 자체의 설명이다.

## 포함 테이블

| `__table` 값 | 의미 |
| --- | --- |
| `ledger_entries` | 당월 지출, 전체 기록, 카드 정기결제, 전월 매입 지연 보정 |
| `monthly_panels` | 현금성 고정지출, 동결, 청구, 가족카드 |
| `app_settings` | 앱 설정 |
| `app_labels` | 화면 라벨 |
| `cash_flows` | 현금 입출금 |
| `installments` | 할부 |
| `card_payment_events` | 즉시결제/할인 이벤트 |
| `card_payment_allocations` | 결제/할인 배분 |
| `card_payment_deferrals` | 통행료/하이패스 이월 |

## 공통 규칙

- 문자 인코딩은 UTF-8이다. Import는 UTF-8 BOM이 붙은 파일도 읽을 수 있다.
- 첫 줄은 헤더다.
- 빈 문자열은 import 시 보통 `NULL`로 취급한다. 단, `app_settings.value`와 `app_labels.value`는 비어 있는 문자열 자체가 의미 있는 값일 수 있어 그대로 보존한다.
- 돈 금액은 원 단위 정수 문자열로 저장한다. 비율인 `fee_rate`만 소수일 수 있다.
- 날짜는 `YYYY-MM-DD`, 월은 `YYYY-MM` 문자열을 사용한다.
- 사용자 계정, 로그인 세션, 공유 세션, 관리 로그는 덤프 대상이 아니다.

## Import 정책

Import는 관대한 데이터 복원을 목표로 한다.

- 현재 DB에 존재하는 컬럼만 INSERT한다.
- CSV에 있지만 현재 DB에 없는 컬럼은 버린다.
- 현재 DB에 있지만 CSV에 없는 컬럼은 DB 기본값 또는 `NULL`로 채운다.
- 필수 컬럼이 빠져 DB가 행을 넣을 수 없는 경우에는 import가 실패할 수 있다.
- 직전 버전의 테이블별 CSV zip도 계속 읽을 수 있다.

복원하지 않는 테이블:

- `users`
- `auth_sessions`
- `share_sessions`
- `audit_logs`

## 재개발 시 주의점

- `payment_key`는 카드 결제/할인 배분의 핵심 참조값이므로 보존하는 편이 좋다.
- `id`는 같은 DB 안에서만 안정적이다. 새 시스템으로 옮길 때는 `payment_key`, 날짜, 정렬값을 함께 보는 편이 안전하다.
- `sort_order`는 같은 날짜 안의 입력 순서를 보존하기 위한 값이다.
- 청구/가족카드는 전달용 임시 큐다. 일괄 처리 후 사라질 수 있다.

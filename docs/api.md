# API 명세

이 문서는 현재 구현된 `money-note` 서버 API 기준이다. 서버는 FastAPI로 구현되어 있으며, 기본 실행 주소는 Docker Compose 기준 `http://localhost:18080`이다.

## 공통 규칙

- 요청/응답 형식: JSON
- 인증: 공개 예외를 제외한 앱 API는 로그인 cookie 또는 bearer token 필요
- 날짜 형식: `YYYY-MM-DD`
- 월 형식: `YYYY-MM`
- 금액 필드:
  - `amount_value`: 계산 완료된 숫자 금액
  - `amount_expr`: Excel 수식 또는 수식성 문자열. 값이 있으면 export 시 셀 수식으로 기록된다.
- 정렬:
  - `sort_order` 오름차순, 동률이면 `id` 오름차순
  - 사용자가 직접 정렬을 바꾸는 경우 reorder API를 사용한다.

## 상태 확인

### `GET /health`

서버 생존 여부를 확인한다.

응답:

```json
{
  "status": "ok"
}
```

## 인증

가계부 본체 API는 패스워드 기반 세션 인증을 사용한다. 로그인에 성공하면 서버가 HttpOnly cookie를 내려주며, 프론트엔드는 이후 요청에 cookie를 포함한다.

macOS Tauri 앱처럼 WebView cookie 저장이 흔들릴 수 있는 클라이언트를 위해 로그인 응답에는 `session_token`도 포함된다. 프론트엔드는 이 값을 저장하고 이후 요청에 `Authorization: Bearer ...` 헤더로 함께 보낸다.

로그인 없이 호출 가능한 예외:

- `GET /health`
- `GET /share/{panel_type}`: 유효한 공유 세션이 없으면 PIN 입력 화면 반환
- `GET /api/share/{panel_type}`: 유효한 공유 세션 필요
- `POST /api/share/unlock`

공유 PIN의 초기값은 `0000`이다. 가족은 기본 PIN `0000`으로도 공유 페이지에 접근할 수 있다. 본체 로그인 사용자는 기본 PIN을 다른 값으로 변경할 때까지 경고를 받는다. 나머지 앱 API는 본체 로그인 인증이 필요하다.

### `POST /api/auth/login`

로그인한다.

요청:

```json
{
  "username": "your-username",
  "password": "your-password"
}
```

응답:

```json
{
  "id": 1,
  "username": "your-username",
  "display_name": "사용자",
  "session_token": "...",
  "share_pin_needs_change": true
}
```

성공 시 `money_note_session` cookie도 설정된다.

### `POST /api/auth/logout`

현재 세션을 삭제하고 cookie를 제거한다.

응답:

```json
{
  "ok": true
}
```

### `GET /api/auth/me`

현재 로그인한 사용자를 조회한다.

응답:

```json
{
  "id": 1,
  "username": "your-username",
  "display_name": "사용자",
  "session_token": null,
  "share_pin_needs_change": false
}
```

로그인하지 않은 경우 `401`을 반환한다.

## 금전 기록

### `GET /api/entries/{section}`

`current` 또는 `archive` 영역의 금전 기록을 조회한다.

경로 변수:

- `section`: `current` 또는 `archive`

응답 필드:

```json
[
  {
    "id": 1,
    "book_section": "current",
    "entry_kind": "expense",
    "entry_date": "2026-06-01",
    "date_label": "2026.06.01.",
    "group_label": null,
    "title": "[카페] 커피",
    "usage_place": "카페",
    "usage_item": "커피",
    "amount_value": 4500,
    "amount_expr": null,
    "aux_amount_value": null,
    "aux_amount_expr": null,
    "extra_value": null,
    "sort_order": 3,
    "due_day": null,
    "confirmed_at": null,
    "spending_category": "questionable"
  }
]
```

`book_section` 의미:

- `current`: `당월 기록` 시트에 표시되는 현재 월 데이터
- `archive`: `전체 기록(본인)` 시트의 동적 append 대상 데이터

`entry_kind` 의미:

- `expense`: 일반 지출
- `planned`: 카드 정기결제 항목. 확인하면 같은 사용처/사용항목 구조로 당월 지출에 편입된다.

### `POST /api/entries`

금전 기록을 직접 생성한다.

요청:

```json
{
  "book_section": "current",
  "entry_kind": "expense",
  "entry_date": "2026-06-03",
  "date_label": "2026.06.03.",
  "group_label": null,
  "title": "[한국전력] 전기요금",
  "usage_place": "한국전력",
  "usage_item": "전기요금",
  "amount_value": 12345,
  "amount_expr": null,
  "aux_amount_value": null,
  "aux_amount_expr": null,
  "extra_value": null,
  "sort_order": 30,
  "due_day": null,
  "confirmed_at": null,
  "spending_category": null
}
```

응답: 생성된 `LedgerEntry`.

### `PATCH /api/entries/{entry_id}`

금전 기록 일부를 수정한다.

요청 예시:

```json
{
  "title": "수정된 적요",
  "usage_place": "수정된 사용처",
  "usage_item": "수정된 사용항목",
  "amount_value": 15000,
  "spending_category": "essential",
  "sort_order": 31
}
```

응답: 수정된 `LedgerEntry`.

### `DELETE /api/entries/{entry_id}`

금전 기록을 삭제한다.

응답:

```json
{
  "deleted": true
}
```

## 카드 정기결제

### `POST /api/month/current/planned`

고정지출 탭의 `카드 정기결제` 항목을 추가한다. 기존 planned 항목 뒤에 붙으며, 뒤쪽 현재 기록의 `sort_order`는 자동으로 밀린다.

요청:

```json
{
  "title": "[통신사] 통신요금",
  "usage_place": "통신사",
  "usage_item": "통신요금",
  "amount_value": 50000,
  "amount_expr": null,
  "due_day": 11
}
```

응답: 생성된 `LedgerEntry`.

### `DELETE /api/month/current/planned/{entry_id}`

카드 정기결제 항목을 삭제한다.

`entry_kind = planned`인 카드 정기결제 항목만 삭제한다.

응답:

```json
{
  "deleted": true
}
```

### `POST /api/month/current/planned/reorder`

카드 정기결제 항목만 사용자 지정 순서로 재정렬한다.

요청:

```json
{
  "ordered_ids": [12, 10, 11]
}
```

응답: 재정렬된 planned 기록 목록.

## 당월 기록 정렬

### `POST /api/month/current/reorder`

`current` 영역 전체 기록을 사용자 지정 순서로 재정렬한다.

요청:

```json
{
  "ordered_ids": [3, 1, 2]
}
```

`ordered_ids`에 빠진 기존 ID는 기존 상대 순서를 유지한 채 뒤에 붙는다.

응답: 재정렬된 current 기록 목록.

## 당월 패널

패널은 `당월 기록` 시트 우측의 `고정지출`, `동결`, `청구`, `타인정산` 테이블을 뜻한다.

`panel_type` 값:

- `fixed`: 고정지출
- `frozen`: 동결
- `claim`: 청구
- `settlement`: 타인정산

### `GET /api/month/current/panels`

현재 월 패널 항목을 조회한다. 현재 월은 `current` 기록 중 가장 이른 `entry_date`의 `YYYY-MM`으로 판단한다. 현재 기록에 날짜가 없으면 서버의 오늘 날짜 월을 사용한다.

응답:

```json
[
  {
    "id": 1,
    "month": "2026-06",
    "panel_type": "fixed",
    "title": "월세",
    "amount_value": 500000,
    "amount_expr": null,
    "sort_order": 4
  }
]
```

### `POST /api/month/current/panels`

패널 항목을 생성한다.

요청:

```json
{
  "month": "2026-06",
  "panel_type": "frozen",
  "title": "손대면 미래의 내가 화냄",
  "amount_value": 100000,
  "amount_expr": null,
  "sort_order": 20
}
```

응답: 생성된 `MonthlyPanel`.

### `PATCH /api/month/current/panels/{panel_id}`

패널 항목 일부를 수정한다.

요청 예시:

```json
{
  "title": "수정된 패널 항목",
  "amount_value": 120000
}
```

응답: 수정된 `MonthlyPanel`.

### `DELETE /api/month/current/panels/{panel_id}`

패널 항목을 삭제한다.

응답:

```json
{
  "deleted": true
}
```

### `DELETE /api/month/current/panels/type/{panel_type}`

현재 월의 특정 패널 타입 항목을 전부 삭제한다. 웹 UI의 청구/타인정산 `초기화` 버튼이 이 API를 사용한다.

응답:

```json
{
  "deleted": 3
}
```

## 요약

### `GET /api/month/current/summary`

`당월 기록` 요약값을 계산한다.

응답:

```json
{
  "base_next_month_liquidity": 400000,
  "card_total": 123456,
  "installment_monthly_total": 33900,
  "transfer_or_deposit_total": 500000,
  "interest_expense": 0,
  "frozen_asset_total": 100000,
  "liquidity_status": 200000,
  "next_month_liquidity": -23456
}
```

계산식:

```text
next_month_liquidity
= base_next_month_liquidity
  - card_total
  - transfer_or_deposit_total
  - interest_expense
  - frozen_asset_total
  + liquidity_status
```

현재 구현상 `card_total`은 `current` 영역 전체 `amount_value` 합계와 활성 할부의 월 납입액 합계다.

## 월마감

### `POST /api/month/current/close`

현재 월 기록을 전체 기록으로 넘긴다.

동작:

- `book_section = current`이고 `entry_kind != planned`인 항목을 `archive`로 복사한다.
- 복사된 항목은 `archive`의 마지막 `sort_order` 뒤에 append된다.
- 원래 `current`에 있던 비-planned 항목은 삭제된다.
- `planned` 항목, 즉 카드 정기결제는 현재 월에 남는다.

응답:

```json
{
  "archived": 15,
  "deleted_from_current": 15
}
```

## 카드 결제 관리

### `GET /api/card-payments/current`

현재 결제월의 결제 현황을 조회한다. 대상은 직전월 1일~말일 사용내역이다.

응답에는 원래 결제액, 즉시결제 누적, 할인액 누적, 남은 결제액, 주 수입 합계, 항목별 배분 상태와 당월 결제 기록이 포함된다.

### `POST /api/card-payments/events`

즉시결제 또는 수기 할인액을 항목별로 배분한다.

```json
{
  "event_date": "2026-06-04",
  "event_type": "immediate",
  "note": "",
  "allocations": [
    {
      "entry_payment_key": "payment-key",
      "amount_value": 3000
    }
  ]
}
```

- `event_type = immediate`: 연결된 현금흐름 출금을 생성한다.
- `event_type = discount`: 원래 사용금액은 유지하고 남은 결제금액만 줄인다.
- 하나의 항목에 남은 금액 일부만 배분할 수 있다.
- 익월 14일까지 처리 가능하다.

### `DELETE /api/card-payments/events/{event_id}`

결제 또는 할인 기록을 취소한다. 즉시결제라면 연결된 현금흐름도 함께 삭제한다.

### `POST /api/card-payments/acknowledge-liquidity-reset`

14일 경과 후 정규결제 완료 의제로 인해 사용자가 실제 유동성 현황을 수동 보정했음을 기록한다.

## 읽기 전용 공유

현재 외부 공유 대상은 `청구`와 `타인정산`이다.

허용되는 `panel_type`:

- `claim`: 청구
- `settlement`: 타인정산

### `GET /api/share/{panel_type}`

유효한 공유 세션에서 읽기 전용 공유 데이터를 JSON으로 반환한다.

응답:

```json
{
  "month": "2026-06",
  "panel_type": "claim",
  "title": "청구",
  "rows": [
    {
      "id": 10,
      "month": "2026-06",
      "panel_type": "claim",
      "title": "가족 장보기",
      "amount_value": 25000,
      "amount_expr": null,
      "sort_order": 18
    }
  ],
  "total": 25000
}
```

### `GET /share/{panel_type}`

읽기 전용 공유 데이터를 HTML 페이지로 반환한다. 앱 설치를 원치 않는 가족에게 보여주기 위한 웹 뷰다.

예시:

- `/share/claim`
- `/share/settlement`

공유 세션이 없으면 카카오톡 인앱 브라우저에서도 사용할 수 있는 네 자리 PIN 입력 화면을 먼저 표시한다. 새 DB의 기본 PIN은 `0000`이다.

### `POST /api/share/pin`

본체 로그인 사용자가 가족 공유용 숫자 네 자리 PIN을 설정한다. PIN 변경 시 기존 공유 세션을 모두 삭제한다. `0000`을 설정하면 기본 PIN 변경 경고는 계속 유지된다.

```json
{
  "pin": "1234"
}
```

### `POST /api/share/unlock`

공유 PIN을 확인하고 최대 10년의 공유 전용 cookie를 발급한다.

```json
{
  "pin": "1234"
}
```

## 할부

### `GET /api/installments`

활성 할부 항목을 조회한다.

응답 예시:

```json
[
  {
    "id": 1,
    "title": "노트북",
    "principal_amount": 1000000,
    "fee_rate": 1.7,
    "fee_amount": 17000,
    "months": 6,
    "remaining_months": 6,
    "start_month": "2026-06",
    "sort_order": 1,
    "is_active": 1,
    "monthly_amount": 169500
  }
]
```

`monthly_amount`는 `(principal_amount + fee_amount) / months`를 원 단위 올림한 값이다.

### `POST /api/installments`

할부 항목을 생성한다.

요청:

```json
{
  "title": "노트북",
  "principal_amount": 1000000,
  "fee_rate": 1.7,
  "months": 6,
  "remaining_months": 6,
  "start_month": "2026-06",
  "sort_order": 1
}
```

### `DELETE /api/installments/{installment_id}`

할부 항목을 삭제한다.

## 현금흐름

### `GET /api/cash-flows`

현금 입출금 기록을 조회한다.

### `POST /api/cash-flows`

현금 입출금 기록을 생성한다. 입금은 양수, 출금은 음수 금액을 사용한다.

### `DELETE /api/cash-flows/{flow_id}`

현금 입출금 기록을 삭제한다.

## 서버 설정

### `GET /api/settings`

서버 설정값을 조회한다.

응답:

```json
{
  "base_next_month_liquidity": "400000",
  "interest_expense": "0",
  "liquidity_status": "0",
  "settlement_card_limit": "5800000"
}
```

설정값:

- `base_next_month_liquidity`: 익월 유동성 계산의 기준 금액
- `interest_expense`: 이자지출
- `liquidity_status`: 유동성 현황
- `settlement_card_limit`: 가족카드 한도 감시 기준 금액

### `PATCH /api/settings/{key}`

설정값을 수정한다.

요청:

```json
{
  "value": "450000"
}
```

응답:

```json
{
  "base_next_month_liquidity": "450000"
}
```

허용 key:

- `base_next_month_liquidity`
- `interest_expense`
- `liquidity_status`
- `settlement_card_limit`

## 엑셀 표시 라벨

### `GET /api/labels`

엑셀 export에 사용할 표시 문구를 조회한다.

응답 예시:

```json
{
  "current_header_date": "날짜",
  "current_header_title": "적요",
  "current_header_amount": "금액",
  "panel_fixed_title": "고정지출",
  "panel_frozen_title": "동결",
  "panel_claim_title": "청구",
  "panel_settlement_title": "타인정산",
  "summary_next_month_liquidity_label": "익월 유동성"
}
```

### `PATCH /api/labels/{key}`

엑셀 표시 문구를 수정한다.

요청:

```json
{
  "value": "잔액"
}
```

응답:

```json
{
  "summary_next_month_liquidity_label": "잔액"
}
```

허용 key는 현재 DB의 `workbook_labels`에 존재하는 key다.

## 엑셀 export

### `POST /api/export`

현재 DB 내용을 엑셀 파일로 export한다.

동작:

- `exports/money-note-YYYYMMDD-HHMMSS.xlsx` 생성
- `exports/latest.xlsx` 갱신
- 설정된 template workbook이 있으면 해당 파일의 스타일과 기존 hard archive 영역을 기반으로 export한다.

응답:

```json
{
  "filename": "money-note-20260603-153000.xlsx",
  "latest": "latest.xlsx"
}
```

### `GET /api/export/latest.xlsx`

가장 최근 export 파일을 다운로드한다.

응답:

- 파일: `money-note-latest.xlsx`

아직 export가 생성되지 않았으면 `404`를 반환한다.

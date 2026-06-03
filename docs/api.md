# API 명세

이 문서는 현재 구현된 `money-note` 서버 API 기준이다. 서버는 FastAPI로 구현되어 있으며, 기본 실행 주소는 Docker Compose 기준 `http://localhost:18080`이다.

## 공통 규칙

- 요청/응답 형식: JSON
- 인증: 현재 없음
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

공개 예외:

- `GET /health`
- `GET /share/{panel_type}`
- `GET /api/share/{panel_type}`

위 공개 예외를 제외한 앱 API는 인증이 필요하다.

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
  "display_name": "사용자"
}
```

성공 시 `money_note_session` cookie가 설정된다.

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
  "display_name": "사용자"
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
    "title": "커피",
    "amount_value": 4500,
    "amount_expr": null,
    "aux_amount_value": null,
    "aux_amount_expr": null,
    "extra_value": null,
    "sort_order": 3
  }
]
```

`book_section` 의미:

- `current`: `당월 기록` 시트에 표시되는 현재 월 데이터
- `archive`: `전체 기록(본인)` 시트의 동적 append 대상 데이터

`entry_kind` 의미:

- `expense`: 일반 지출
- `planned`: `나갈 돈` 항목

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
  "title": "서버에게 바친 전기요금",
  "amount_value": 12345,
  "amount_expr": null,
  "aux_amount_value": null,
  "aux_amount_expr": null,
  "extra_value": null,
  "sort_order": 30
}
```

응답: 생성된 `LedgerEntry`.

### `PATCH /api/entries/{entry_id}`

금전 기록 일부를 수정한다.

요청 예시:

```json
{
  "title": "수정된 적요",
  "amount_value": 15000,
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

## 당월 `나갈 돈`

### `POST /api/month/current/planned`

`당월 기록`의 `나갈 돈` 그룹에 항목을 추가한다. 기존 planned 항목 뒤에 붙으며, 뒤쪽 현재 기록의 `sort_order`는 자동으로 밀린다.

요청:

```json
{
  "title": "카드값: 지난달의 나 수습비",
  "amount_value": 50000,
  "amount_expr": null
}
```

응답: 생성된 `LedgerEntry`.

### `DELETE /api/month/current/planned/{entry_id}`

`나갈 돈` 항목만 삭제한다.

응답:

```json
{
  "deleted": true
}
```

### `POST /api/month/current/planned/reorder`

`나갈 돈` 항목만 사용자 지정 순서로 재정렬한다.

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

## 요약

### `GET /api/month/current/summary`

`당월 기록` 요약값을 계산한다.

응답:

```json
{
  "base_next_month_liquidity": 400000,
  "card_total": 123456,
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

현재 구현상 `card_total`은 `current` 영역 전체 `amount_value` 합계다.

## 월마감

### `POST /api/month/current/close`

현재 월 기록을 전체 기록으로 넘긴다.

동작:

- `book_section = current`이고 `entry_kind != planned`인 항목을 `archive`로 복사한다.
- 복사된 항목은 `archive`의 마지막 `sort_order` 뒤에 append된다.
- 원래 `current`에 있던 비-planned 항목은 삭제된다.
- `planned` 항목, 즉 `나갈 돈`은 현재 월에 남는다.

응답:

```json
{
  "archived": 15,
  "deleted_from_current": 15
}
```

## 읽기 전용 공유

현재 외부 공유 대상은 `청구`와 `타인정산`이다.

허용되는 `panel_type`:

- `claim`: 청구
- `settlement`: 타인정산

### `GET /api/share/{panel_type}`

읽기 전용 공유 데이터를 JSON으로 반환한다.

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

## 서버 설정

### `GET /api/settings`

서버 설정값을 조회한다.

응답:

```json
{
  "base_next_month_liquidity": "400000",
  "interest_expense": "0",
  "liquidity_status": "0"
}
```

설정값:

- `base_next_month_liquidity`: 익월 유동성 계산의 기준 금액
- `interest_expense`: 이자지출
- `liquidity_status`: 유동성 현황

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

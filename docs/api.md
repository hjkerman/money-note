# API 명세

이 문서는 현재 구현된 `money-note` 서버 API 기준이다. 서버는 FastAPI로 구현되어 있으며, 기본 실행 주소는 Docker Compose 기준 `http://localhost:18080`이다.

## 공통 규칙

- 요청/응답 형식: JSON
- 인증: 공개 예외를 제외한 앱 API는 로그인 cookie 또는 bearer token 필요
- 세션 복원: 앱 시작 시 `GET /api/auth/me`를 먼저 호출한다. `401`이면 로그인 화면을 보여준다.
- 날짜 형식: `YYYY-MM-DD`. 날짜 입력 schema는 실제 달력 날짜로 검증하므로 `2026-02-30` 같은 값은 `422`다.
- 월 형식: `YYYY-MM`
- 금액 형식: 원화 정수. 비율 설정처럼 명시된 예외가 아니면 소수점 금액을 쓰지 않는다.
- 금액 필드:
  - `amount_value`: 계산 완료된 숫자 금액
  - `amount_expr`: 과거 호환용 문자열 필드. 신규 화면에서는 계산된 금액을 중시한다.
- 요청 본문 제한:
  - `POST`, `PATCH`, `DELETE` API는 기본 `1 MiB`를 넘는 요청 본문을 `413`으로 거부한다.
  - snapshot restore만 백업 파일을 위해 별도 기본 상한 `25 MiB`를 사용한다.
  - 두 상한은 `Content-Length`가 없거나 chunked 전송인 경우에도 실제 수신 바이트에 적용된다.
- 서버 표시 투영:
  - 할인 정책, 자동 할인 가능 여부, 자동/유효 할인액, 실결제액, 교통·통행 태그는 서버가 계산해 조회 응답에 포함한다.
  - 이 필드는 DB 컬럼이 아니며 웹/모바일이 다시 계산하지 않는다.
- 정렬:
  - `sort_order` 오름차순, 동률이면 `id` 오름차순
  - 사용자가 직접 정렬을 바꾸는 경우 reorder API를 사용한다.

모바일 앱 구현 메모:

- 서버 DB가 단일 원본이다. 모바일 앱은 로컬 장부를 별도로 authoritative하게 유지하지 않는다.
- 웹은 `/api/auth/login`의 HttpOnly cookie를 사용한다.
- 모바일은 `/api/auth/mobile-login`의 `session_token`을 `Authorization: Bearer ...`로 보낸다.
- 변경 API를 호출한 뒤에는 관련 조회 API를 다시 호출해 서버 계산 결과를 화면에 반영한다.
- 파일 다운로드 API는 JSON이 아니라 blob/file 응답일 수 있다. 대표적으로 snapshot export와 APK 다운로드가 그렇다.
- `claim`과 `family_card`는 회수 예정 정보이며, 당월 소비 원장/소비 통계/잔여 유동성 계산에 직접 넣지 않는다.

## 상태 확인

### `GET /health`

서버 생존 여부를 확인한다.

응답:

```json
{
  "status": "ok"
}
```

## 관리 로그

관리 로그는 변경 API의 시각, 사용자, HTTP 방식, 경로, 결과 코드만 보존한다. 요청 본문, 비밀번호, 세션 토큰은 저장하지 않는다.

### `GET /api/audit-logs`

최근 관리 로그를 최신순으로 최대 300개 조회한다.

### `DELETE /api/audit-logs`

관리 로그 전체를 초기화한다. 초기화 요청 자체는 새 관리 로그를 만들지 않는다.

응답:

```json
{
  "deleted": 42
}
```

## 인증

가계부 본체 API는 패스워드 기반 세션 인증을 사용한다. 로그인에 성공하면 서버가 HttpOnly cookie를 내려주며, 프론트엔드는 이후 요청에 cookie를 포함한다.

웹과 모바일의 토큰 발급 경로를 분리한다. 웹 `POST /api/auth/login`은 HttpOnly cookie를 설정하고 응답의 `session_token`은 `null`이다. 모바일 앱만 `POST /api/auth/mobile-login`에서 장기 Bearer 토큰을 받는다.

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
  "session_token": null,
  "share_pin_needs_change": true
}
```

성공 시 `money_note_session` cookie도 설정된다.

### `POST /api/auth/mobile-login`

모바일 앱에서 로그인한다. 요청 형식과 응답 형식은 `POST /api/auth/login`과 같다.

차이:

- `money_note_session` cookie를 설정하지 않는다.
- 응답의 `session_token`은 `MONEY_NOTE_MOBILE_SESSION_DAYS` 기준의 장기 Bearer 토큰이다.
- 이후 모바일 앱은 `Authorization: Bearer ...` 헤더로 인증한다.

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

### `PATCH /api/auth/password`

현재 로그인 사용자의 비밀번호를 변경한다.

요청:

```json
{
  "current_password": "현재 비밀번호",
  "new_password": "새 비밀번호"
}
```

응답:

```json
{
  "changed": true
}
```

현재 비밀번호가 맞지 않으면 `422`를 반환한다.
새 비밀번호는 12자 이상이어야 한다. 변경에 성공하면 웹·모바일을 포함한 해당 사용자의 기존 로그인 세션을 모두 종료하므로 다시 로그인해야 한다.

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
    "spending_category": "questionable",
    "payment_key": "...",
    "discount_policy": "enabled",
    "automatic_discount_eligible": true,
    "automatic_discount_amount": 54,
    "effective_discount_amount": 54,
    "effective_amount_value": 4446,
    "is_transport": false,
    "is_toll": false
  }
]
```

서버 표시 투영 필드:

- `discount_policy`: 해당 항목에 실제 적용한 월 혜택 상태. 교통카드 `owner` 프로필이면 본인카드 상태를 반환한다.
- `automatic_discount_eligible`: 기본 자동 할인 대상 여부
- `automatic_discount_amount`: 기본 정책상 예상 할인액
- `effective_discount_amount`: 월 정책과 수동 override를 모두 반영한 최종 할인액
- `effective_amount_value`: `amount_value - effective_discount_amount`
- `is_transport`, `is_toll`: 서버 키워드 정책에 따른 표시 태그

클라이언트는 할인율이나 키워드를 자체 적용하지 않고 이 값을 그대로 사용한다.

`book_section` 의미:

- `current`: `당월 기록` 시트에 표시되는 현재 월 데이터
- `archive`: `전체 기록(본인)` 시트의 동적 append 대상 데이터

`entry_kind` 의미:

- `expense`: 일반 지출
- `planned`: 카드 정기결제 항목. 확인하면 같은 사용처/사용항목 구조로 당월 지출에 편입된다.
- `late_expense`: 카드사가 월말 이후 매입한 직전월 사용내역

### `POST /api/entries`

금전 기록을 직접 생성한다.

`book_section = current`, `entry_kind = expense`인 일반 지출은 `entry_date`, `usage_place`, `amount_value`가 필수다. `usage_item`은 비워둘 수 있다.
현금흐름을 제외한 사용자 입력 금액은 0 이상이어야 한다.

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

`entry_kind`, `due_day`, `confirmed_at`, `confirmed_month`, `discount_override` 같은 상태 전이 필드는 이 generic PATCH에서 허용하지 않는다. 정기결제 확인과 할인 변경은 각각의 전용 endpoint를 사용한다. 정의되지 않은 필드를 보내면 `422`를 반환한다.

`spending_category` 허용값:

- `essential`: 안 썼으면 큰일 났을 돈
- `questionable`: 꼭 써야 했을까...?
- `dignity`: 최소한의 품위유지비
- `null`: 미분류

### `DELETE /api/entries/{entry_id}`

금전 기록을 삭제한다.

즉시결제 allocation이 한 건이라도 있는 카드 원장 항목은 일부·전액 여부와 무관하게 `409`로 거부한다. 이미 지급한 거래의 현금 출금 이력을 일반 원장 편집으로 다시 쓰지 않기 위한 규칙이다. 미결제 항목과 할인 처리만 있는 항목은 기존처럼 삭제할 수 있다.

응답:

```json
{
  "deleted": true
}
```

## 카드 정기결제

### `POST /api/month/current/planned`

고정지출 탭의 `카드 정기결제` 항목을 추가한다. 기존 planned 항목 뒤에 붙으며, 뒤쪽 현재 기록의 `sort_order`는 자동으로 밀린다.

`due_day`, `usage_place`, `amount_value`는 필수이며 `usage_item`은 비워둘 수 있다.

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

### `POST /api/month/current/planned/{entry_id}/confirm`

카드 정기결제 항목을 당월 지출로 편입한다.

- `entry_kind = planned` 항목만 대상이다.
- 새 당월 지출은 기존 planned 항목의 사용처와 사용항목을 따르며, 요청의 `actual_amount`가 있으면 이번 주기의 실제 원금으로 사용한다. 생략하면 template 예정 원금을 사용한다.
- 원래 planned 항목은 삭제하지 않고 현재 월에 확인된 상태로 숨겨진다.
- 새 지출은 `source_planned_entry_id`로 원본 planned 항목을 명시적으로 참조한다. 동일 제목·금액의 수동 지출과 혼동하지 않는다.
- 월마감 후 다음 달에는 template 예정 원금을 유지한 같은 planned 항목이 다시 보인다.
- 선택 요청 본문 `entry_date`를 보내면 그 날짜를 새 지출의 사용일로 사용한다. 생략하면 `due_day`를 기준으로 한 이번 달 날짜를 사용한다.
- 확인 시 `due_day`는 바뀌지 않는다. `entry_date`는 앱 기준 현재 월의 날짜여야 한다.

선택 요청:

```json
{
  "entry_date": "2026-06-17",
  "actual_amount": 52000
}
```

`actual_amount`는 0원 이상이다. 서버는 이 실제 원금에 기존 카드 할인 정책을 적용하여 생성 expense의 할인액과 실결제액을 확정한다. planned template의 `amount_value`와 `due_day`는 바뀌지 않는다. 확인을 잘못했다면 월마감 전에 생성된 원장 expense를 삭제해 template을 미확인 상태로 되돌린 뒤 다시 확인한다.

응답:

```json
{
  "planned": {},
  "entry": {}
}
```

### `GET /api/month/current/planned/{entry_id}/preview?actual_amount=52000`

카드 정기결제의 이번 실제 원금을 저장하지 않고 서버 카드 정책으로 투영한다. Web과 Mobile은 할인 공식을 복제하지 않고 이 응답을 확인 전 preview로 사용한다.

응답:

```json
{
  "amount_value": 52000,
  "discount_policy": "flat_statement",
  "automatic_discount_eligible": true,
  "effective_discount_amount": 624,
  "effective_amount_value": 51376
}
```

### `GET /api/month/current/planned/confirmed`

이번 달에 이미 확인하여 원장에 편입한 카드 정기결제 원본을 조회한다. 응답은 `LedgerEntry` 배열이며, 각 항목의 `entry_date`에는 가능한 경우 이번 달에 생성된 대응 지출의 실제 승인일을 투영한다. `amount_value`는 template 예정 원금이고, `confirmed_amount_value`, `confirmed_effective_discount_amount`, `confirmed_effective_amount_value`는 대응 expense에서 투영한 이번 실제 원금·할인·실결제액이다.

### `DELETE /api/month/current/planned/{entry_id}`

카드 정기결제 항목을 삭제한다.

`entry_kind = planned`인 카드 정기결제 항목만 삭제한다.

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

패널은 `당월 기록` 시트 우측의 `고정지출`, `동결`, `청구`, `가족카드` 테이블을 뜻한다.

`panel_type` 값:

- `fixed`: 고정지출
- `frozen`: 동결
- `claim`: 청구
- `family_card`: 가족카드

### `GET /api/month/current/panels`

현재 월 패널 항목을 조회한다. `fixed`는 월 반복 관리 항목으로 확인 전·후 행을 모두 포함한다. `confirmed_at`과 `confirmed_cash_flow_id`가 모두 있는 행만 이번 주기에 현금흐름으로 확인 처리된 템플릿이다. 둘 중 하나라도 없으면 미지급 의무로 취급한다. `frozen`은 사용자가 삭제할 때까지 유지되는 확보 금액 큐이며, `claim`과 `family_card`는 처리 전까지 유지되는 회수 예정 큐다. 따라서 세 타입 모두 등록 월과 무관하게 미처리 항목 전체를 포함한다.

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
    "sort_order": 4,
    "spent_on": null,
    "confirmed_at": null,
    "confirmed_cash_flow_id": null,
    "discount_policy": "disabled",
    "automatic_discount_eligible": false,
    "automatic_discount_amount": 0,
    "effective_discount_amount": 0,
    "effective_amount_value": 500000
  }
]
```

패널의 표시 투영 필드는 원장과 같은 의미다. `claim`은 본인카드 월 정책, `family_card`는 가족카드 월 정책을 사용한다. `fixed`, `frozen`에는 자동 카드 할인을 적용하지 않는다.

### `POST /api/month/current/panels`

패널 항목을 생성한다.

요청:

```json
{
  "month": "2026-06",
  "panel_type": "frozen",
  "title": "손대면 미래의 내가 화냄",
  "spent_on": "2026-06-18",
  "amount_value": 100000,
  "amount_expr": null,
  "sort_order": 20
}
```

응답: 생성된 `MonthlyPanel`.

### `POST /api/month/current/panels/{panel_id}/confirm-fixed`

현금성 고정지출 템플릿을 선택한 처리일의 실제 현금 유출로 확인한다.

요청:

```json
{
  "occurred_on": "2026-08-27",
  "actual_amount": 112430
}
```

`actual_amount`는 0원 이상이며 생략하면 template `amount_value`를 사용한다. 서버는 같은 트랜잭션에서 실제액의 음수 현금흐름을 만들고, 패널의 `spent_on`, `confirmed_at`, `confirmed_month`, `confirmed_cash_flow_id`를 기록한다. 원래 템플릿 예정액과 제목은 바뀌지 않는다. 응답과 확인 목록의 `confirmed_amount_value`는 연결된 cash flow의 절댓값이다. 이미 확인된 항목이나 `fixed`가 아닌 패널은 `422`를 반환한다. 처리일이 서버 기준 오늘보다 미래여도 `422`를 반환하며 예약 확인으로 해석하지 않는다.

응답:

```json
{
  "panel": {"id": 1, "amount_value": 150000, "confirmed_amount_value": 112430, "confirmed_cash_flow_id": 42},
  "cash_flow": {"id": 42, "occurred_on": "2026-08-27", "amount_value": -112430}
}
```

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

이 generic PATCH는 제목, 금액, 표시 순서처럼 일반 편집 필드만 받는다. `panel_type`, `month`, `spent_on`, `confirmed_at`, `confirmed_cash_flow_id`, 할인 상태 같은 도메인 상태는 허용하지 않으며 전용 확인·할인 endpoint를 사용한다. 정의되지 않은 필드를 보내면 `422`를 반환한다.

### `DELETE /api/month/current/panels/{panel_id}`

패널 항목을 삭제한다.

응답:

```json
{
  "deleted": true
}
```

### `DELETE /api/month/current/panels/type/{panel_type}`

특정 패널 타입 항목을 전부 삭제한다. `claim`과 `family_card`는 월과 무관하게 현재 남아 있는 회수 예정 큐 전체를 삭제한다.

응답:

```json
{
  "deleted": 3
}
```

### `POST /api/month/current/panels/type/{panel_type}/complete`

청구 또는 가족카드의 현재 남아 있는 회수 예정 큐 전체를 월 값과 무관하게 일괄 처리 완료하고 삭제한다. `claim`, `family_card`만 허용하며 다른 패널과 월마감에는 영향을 주지 않는다.

실행 직전 서버는 현재 장부 상태를 `pre_restore` snapshot으로 자동 저장한다.

응답:

```json
{
  "completed": 4
}
```

## 요약

### `GET /api/month/current/summary`

`당월 기록` 요약값을 계산한다.

응답:

```json
{
  "scheduled_income": 400000,
  "cash_flow_balance": 200000,
  "remaining_liquidity": -23456,
  "current_spending_total": 124956,
  "current_discount_total": 1500,
  "card_total": 123456,
  "planned_recurring_total": 68990,
  "fixed_cash_total": 431010,
  "transfer_or_deposit_total": 500000,
  "frozen_asset_total": 100000,
  "claim_original_total": 50000,
  "claim_net_total": 49400,
  "family_card_original_total": 80000,
  "family_card_net_total": 80000,
  "visible_cash_flow_total": 120000
}
```

이 응답은 웹과 모바일 요약 카드의 권위 있는 합계다. 클라이언트는 조회한 행을 다시 합산해 이 값을 대체하지 않는다.

표준 유동성 key:

- `scheduled_income`: 월마감 실행일의 실제 `급여`를 생성하고, 현행 pre-funding 모델에서 아직 들어오지 않은 다음 급여로 한 번 선반영하는 기본 예정 수입
- `cash_flow_balance`: 수동 보정값과 서버 기준일 현재까지 발생한 현금흐름 누계를 합친 Active 계좌의 실제 잔액. 미래 날짜 현금흐름은 제외
- `remaining_liquidity`: 현재 예산 주기에서 이미 약속된 금액을 제외하고 추가로 사용할 수 있는 잔여 유동성

과거 유동성 alias는 일반 Summary 응답에서 제거됐다. 구버전 이름은 v4 Snapshot restore migration에서만 해석한다.

- `current_spending_total`: 본인 원장의 할인 전 사용금액
- `current_discount_total`: 본인 원장의 유효 할인액
- `card_total`: 본인 원장의 할인 후 카드대금
- `fixed_cash_total`: 확인 여부와 무관한 현금성 고정지출 템플릿 총액
- `claim_*`: 현재 남은 청구 큐의 원금/실부담 합계
- `family_card_*`: 현재 남은 가족카드 큐의 원금/실결제 합계
- `visible_cash_flow_total`: 기본 화면 조회 범위인 직전 월 1일부터 당월 말일까지 현금흐름 합계

`planned_recurring_total`은 확인 여부와 무관한 카드 정기결제 전체 예정액이다. 카드 정기결제 패널의 총계는 이 값을 표시한다.

`transfer_or_deposit_total`은 기존 API 호환 이름을 유지하지만, 화면에서는 `고정지출`로 표시한다. 이 값은 현금성 고정지출 패널과 `planned_recurring_total`을 합산한다.

잔여 유동성 계산에서는 중복 차감을 피하기 위해, 카드 지출로 편입되지 않은 카드 정기결제 예정액만 고정지출 차감분으로 사용한다. 즉 카드 정기결제를 `확인`하면 표시용 고정지출 총합은 유지되지만, 유동성 계산에서는 카드대금으로 이동한다.

계산식:

```text
remaining_liquidity
= scheduled_income
  + cash_flow_balance
  - card_total
  - active_card_payment_unpaid_total
  - liquidity_fixed_total
  - frozen_asset_total
```

현행 pre-funding 모델의 `scheduled_income`은 아직 현금흐름으로 실현되지 않은 다음 급여를 현재 소비 재원으로 인정하는 항목이다. 월마감 실행일에 생성된 `급여`는 이미 확보된 현금으로 `cash_flow_balance`에 들어가고, 보존된 설정값은 그 이후 받을 다음 급여를 선반영한다. 따라서 두 항이 같은 금액이어도 같은 급여를 중복 집계한 것이 아니다.

`liquidity_fixed_total`은 응답 필드가 아니라 내부 계산값이다. `아직 확인되지 않은 현금성 고정지출 reserve + 아직 카드 지출로 확인되지 않은 카드 정기결제 예정 원금`이다. 현금성 고정지출을 확인하면 reserve 차감은 사라지고 입력한 실제액의 음수 현금흐름이 생긴다. 실제액이 reserve와 같으면 잔여 유동성은 그대로이고, 다르면 그 차액만 자동으로 조정된다.

`cash_flow_balance`는 `occurred_on <= calendar_date`인 현금흐름만 합산한다. 월마감 자동 `급여`는 실행일로 생성되므로 즉시 잔액에 반영된다. 사용자가 별도로 입력한 미래 날짜 현금흐름은 기존대로 해당 날짜 전 Summary 잔액에서 제외되며, 현금흐름 조회 API와 Snapshot에는 행 자체가 그대로 존재한다.

Summary의 모든 구성값은 하나의 SQLite read transaction에서 계산한다. 한 응답 안의 예정 수입, 실제 잔액, 카드 의무, 고정 의무, 동결과 잔여 유동성이 서로 다른 commit 시점에서 섞이지 않는다.

`card_total`은 본인 당월 카드 지출의 할인 후 금액이다. 청구 탭 금액은 청구 표시 합계와 공유 청구서의 실청구액에는 반영하지만, `remaining_liquidity` 계산에는 넣지 않는다.
청구와 가족카드는 회수 예정 금액으로 보며, 당월 소비 통계와 `당월` 큰 탭 합계에도 넣지 않는다.

`active_card_payment_unpaid_total`은 응답 필드가 아니라 활성 결제 batch의 내부 미지급 채무 합계다. 월마감 전 `card_total`이 담당하던 카드 의무를 월마감 후 이어받는다. 이월되어 당월 원장에 다시 들어간 항목은 중복 차감을 피하기 위해 제외한다. 즉시결제 시에는 연결된 음수 현금흐름과 같은 금액만큼 이 합계가 줄어 잔여 유동성이 유지된다. 결제일 경과 후 실제 계좌 잔액을 수동 보정하고 해당 결제월의 보정 완료를 확인한 경우에는 기록상 잔액을 결제 API에 남겨도 Summary에서 다시 차감하지 않는다.

## 판단

### `GET /api/judgment/current`

프론트에서 표시하는 판단 문구와 분류 라벨을 백엔드 판단 모듈 기준으로 조회한다.

응답 예시:

```json
{
  "category_labels": {
    "essential": "안 썼으면 큰일 났을 돈",
    "questionable": "꼭 써야 했을까...?",
    "dignity": "최소한의 품위유지비",
    "unclassified": "미분류"
  },
  "stat_tones": [
    {
      "key": "essential",
      "title": "안 썼으면 큰일 났을 돈",
      "caption": "안 썼으면 일이 커졌을 돈. 생존 인프라입니다."
    }
  ],
  "claim_categories": {},
  "budget": {
    "level": "quiet",
    "message": "장부는 대체로 평온합니다. 소비는 있었고 재난으로 분류되지는 않았습니다."
  },
  "credit": {
    "level": "warning",
    "message": "추정치가 한도의 30%를 넘었습니다. 아직 사고는 아니지만, 카드 명의자의 표정은 회계감사 모드입니다."
  },
  "payment": {
    "level": "quiet",
    "message": "현재 결제 압박은 낮습니다. 파산심사위원회가 관찰 의견만 남깁니다."
  }
}
```

프론트는 이 응답을 표시만 한다. 분류 변경, 할인 반영, 청구 추가처럼 서버에 변경사항이 저장되면 프론트가 다시 동기화하면서 이 판단 결과도 함께 갱신한다.

`budget` 판단의 현금흐름 feature는 서버 기준일이 속한 달의 1일부터 말일까지 발생한 행만 사용한다. 이는 현재 예산 주기의 활동을 평가하기 위한 범위다. Summary의 누적 `cash_flow_balance` 의미와 계산은 바뀌지 않으며, `credit`과 `payment` 판단 계약도 이 변경으로 재설계하지 않는다.

## 월마감

### `GET /api/month/current/status`

달력상 현재 월과 가장 오래된 미마감 월을 조회한다.

```json
{
  "calendar_date": "2026-07-01",
  "calendar_month": "2026-07",
  "oldest_open_month": "2026-06",
  "last_closed_month": "2026-05",
  "needs_close": true,
  "is_early_close": false,
  "early_close_available": false,
  "early_close_start_day": 27,
  "can_close": true,
  "unconfirmed_recurring_items": [
    {"kind": "fixed", "id": 7, "title": "관리비", "amount_value": 80000},
    {"kind": "planned", "id": 12, "title": "통신사", "detail": "통신요금", "amount_value": 55000, "due_day": 15}
  ]
}
```

`needs_close = true`이면 웹 첫 화면에서 월마감 검토 경고를 표시한다. `unconfirmed_recurring_items`는 마감 대상 주기의 실제액이 아직 확정되지 않은 현금성 고정지출과 카드 정기결제다.

### `POST /api/month/current/close`

현재 장부에서 가장 오래된 미마감 월 하나만 전체 기록으로 넘긴다. 현재 달은 매월 27일부터 조기 마감할 수 있으며 명시적 확인값이 필요하다.

요청:

```json
{
  "allow_early_close": false,
  "allow_unconfirmed_recurring": false,
  "target_month": "2026-06"
}
```

`target_month`는 재시도할 논리 작업의 월을 고정한다. 현재 Web과 Mobile은 상태 API의 `oldest_open_month`를 반드시 보낸다. 오래된 호환 호출을 위해 생략은 허용하지만, 안정적인 재시도에는 대상 월을 명시해야 한다.

`oldest_open_month`는 원장 행 존재 여부만으로 결정하지 않는다. `last_closed_month`가 있으면 그 다음 예산 주기를 우선하므로 카드 지출이 0건인 달도 정상적으로 월마감할 수 있다. 빈 달도 급여 생성, 반복 템플릿 reset, 활성 결제 batch 생성과 동일 target 재시도 idempotency를 그대로 수행한다.

미확인 정기지출이 있으면 `allow_unconfirmed_recurring=false`인 요청은 변경과 pre_restore 생성 전에 `422`로 중단된다. Web과 Mobile은 해당 목록을 보여준 뒤 사용자가 `그래도 월마감`을 선택한 경우에만 `true`로 다시 요청한다. 이 값은 경고를 인지했다는 explicit override이며 미확인 항목을 자동 확인하거나 삭제하지 않는다.

동작:

- 가장 오래된 미마감 월의 `book_section = current`, `entry_kind != planned` 항목만 `archive`로 복사한다.
- 복사된 항목은 `archive`의 마지막 `sort_order` 뒤에 append된다.
- 해당 월의 원래 `current` 비-planned 항목만 삭제된다.
- 새 달 기록이 먼저 입력되어 있어도 그대로 남는다.
- 조기 마감 후 같은 달 날짜로 추가한 일반 지출은 `archive`에 바로 저장된다.
- `planned` 항목, 즉 카드 정기결제는 현재 월에 남고, 닫힌 달의 확인 상태는 초기화되어 다음 사이클에서 다시 확인할 수 있다.
- 확인된 현금성 고정지출 템플릿도 미확인 상태로 돌아오지만, 확인 시 생성된 과거 현금흐름은 유지된다.
- 월마감 실행일로 설정의 기본 예정 수입만큼 `급여` 현금 유입을 생성하고 `is_primary_income=1`로 표시한다. 사용자가 이 날 실제 자금을 꺼낸 것으로 보아 Active 계좌 잔액에 즉시 반영한다.
- 같은 `target_month`를 다시 요청하면 이미 마감된 결과로 처리하며 archive, 급여, 결제 batch를 중복 생성하지 않는다.
- 월마감은 SQLite write transaction을 먼저 확보한 뒤 실제 마감 대상을 다시 확인한다. archive 이동, 급여 생성, 결제 batch 생성, 대상 주기 상태 reset은 한 트랜잭션이며 하나라도 실패하면 모두 rollback된다.
- 현금성 고정지출은 `confirmed_month = target_month`인 템플릿만 다음 주기용 미확인 상태로 돌린다. 밀린 월마감이 이후 주기의 확인 상태를 건드리지 않는다.

응답:

```json
{
  "closed_month": "2026-06",
  "archived": 15,
  "deleted_from_current": 15
}
```

## 카드 결제 관리

### `GET /api/card-discounts/months/{month}?scope=owner|family`

사용월 기준 할인 혜택 설정과 항목별 할인액을 조회한다.

- `scope=owner`: 본인회원 카드. 당월 지출과 청구에 적용한다.
- `scope=family`: 가족카드. 가족카드에 적용한다.
- `policy`: `enabled`, `disabled`
- 저장된 정책이 없으면 본인회원 카드는 `enabled`, 가족카드는 `disabled`로 간주한다.
- `policy = disabled`이면 계산상 할인액은 모두 0원이다.
- 그 외에는 해당 사용월의 카드 정책을 적용한다. 현재 본인카드와 가족카드는 각각 `floor(amount_value * 0.012)`를 사용한다.
- 통행료카드는 별도 카드 정책으로 분류하며 자동 할인액은 항상 0원이다.
- 교통카드는 월별 프로필이 `none`이면 자동 할인액 0원, `owner`이면 본인카드 계산식과 해당 월 본인카드 혜택 상태를 따른다.
- `discount_override = 1`이면 기본 할인 계산 대신 저장된 할인액을 쓴다. 저장된 할인액이 0원이면 할인 제외로 취급한다.

### `PATCH /api/card-discounts/months/{month}?scope=owner|family`

본인회원 카드와 가족카드의 월별 할인 혜택 여부를 서로 독립적으로 저장한다.

```json
{ "policy": "enabled" }
```

### `GET /api/card-discounts/profiles/transit/{month}`

해당 사용월에 유효한 교통카드 할인 프로필을 조회한다. 저장된 이력이 없으면 기존 동작인 `none`을 반환한다.

```json
{
  "card": "transit",
  "month": "2026-08",
  "profile": "none"
}
```

### `PATCH /api/card-discounts/profiles/transit/{month}`

교통카드 프로필을 해당 월부터 적용되는 이력으로 저장한다. `owner`는 본인카드 계산식과 본인카드의 해당 월 혜택 `enabled`/`disabled` 상태를 함께 따른다. `none`은 자동 할인을 적용하지 않는다.

```json
{ "profile": "owner" }
```

설정은 월 단위다. 같은 월에 값을 다시 바꾸면 해당 월 키를 덮어쓰므로 그 월의 교통카드 거래 전체가 새 값으로 재계산되며 이전 월은 유지된다. 통행료카드에는 영향을 주지 않는다.

### `PATCH /api/card-discounts/entries/{entry_payment_key}`

원장 항목의 개별 할인 예외를 저장한다. 웹 UI에서는 할인 제외에 사용하며, `discount_amount = 0`을 저장하면 해당 항목은 기본 1.2% 할인을 쓰지 않는다.

요청:

```json
{
  "discount_amount": 0
}
```

### `DELETE /api/card-discounts/entries/{entry_payment_key}`

원장 항목의 개별 할인 예외를 삭제한다. 삭제 후에는 월별 할인 정책에 따라 기본 할인 계산으로 돌아간다.

응답:

```json
{
  "deleted": true
}
```

### `GET /api/card-payments/current`

마지막 월마감이 만든 활성 결제 batch의 현황을 조회한다. 대상 월은 달력상 직전월을 클라이언트가 추정하지 않고 batch의 `usage_month`를 따른다. 활성 batch가 없으면 행 목록은 비어 있다.

응답에는 원래 결제액, 즉시결제 누적, 할인액 누적, 남은 결제액, 이달 기준 수입 합계, 항목별 배분 상태와 당월 결제 기록이 포함된다.

카드 결제 화면의 안내용 항목별 필드:

- `is_toll`: 적요에 `통행료` 또는 `하이패스`가 포함되면 `true`
- `is_deferred`: 현재 결제월에서 다음 달 처리로 이월한 항목
- `is_carried_over`: 이전 결제월에서 이월되어 이번 달 맨 앞에 들어온 항목
- `is_group`: 화면 표시용 묶음 항목. 통행료/하이패스 항목이 여러 건이면 결제 화면에서 하나의 행으로 합쳐 보인다.
- `payment_keys`, `entry_ids`, `payment_parts`: 묶음 항목을 실제 원본 장부 행과 결제 배분으로 다시 펼칠 때 쓰는 참조값이다.

### `POST /api/card-payments/events`

즉시결제를 항목별로 배분한다. `event_type = discount`는 기존 데이터와의 호환을 위해 남아 있지만, 일반 웹 UI에서는 수기 할인액 입력을 제공하지 않는다.

```json
{
  "idempotency_key": "web-20260604-payment-0001",
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

`idempotency_key`는 16~128자의 영문·숫자와 `._:-`로 구성한다. 같은 key와 같은 payload를 재전송하면 새 이벤트나 현금흐름을 만들지 않고 기존 성공 결과를 반환한다. 같은 key에 다른 payload를 보내면 `422`를 반환한다. 서버는 write transaction 안에서 활성 batch와 최신 remaining amount를 다시 계산하므로 서로 다른 key의 동시 요청도 초과결제를 만들 수 없다.

- `event_type = immediate`: 연결된 현금흐름 출금을 생성한다.
- `event_type = discount`: 호환용이다. 원래 사용금액은 유지하고 남은 결제금액만 줄인다.
- 하나의 항목에 남은 금액 일부만 배분할 수 있다.
- 즉시결제는 익월 14일까지 처리 가능하다.
- 사용월 할인 정책이 `disabled`이면 할인액 처리가 거부된다.
- 통행료/하이패스 항목도 일반 항목처럼 일부 즉시결제할 수 있다.

### `PATCH /api/month/current/panels/{panel_id}/discount`

청구 또는 가족카드 항목의 개별 할인 예외를 기록한다. 웹 UI에서는 `할인 제외`를 누르면 할인액 0원, `할인 적용`을 누르면 기본 1.2% 할인 계산으로 돌아간다. 원래 금액은 유지하며 화면과 공유 페이지의 실제 금액은 `원래 금액 - 할인액`으로 계산한다. 청구는 본인회원 카드 정책을, 가족카드는 가족카드 정책을 따른다.

청구와 가족카드는 `spent_on` 기준으로 정렬된다. 같은 날짜라면 `sort_order`, `id` 순서로 먼저 입력한 항목이 위에 온다.

### `DELETE /api/month/current/panels/{panel_id}/discount`

청구 또는 가족카드 항목의 개별 할인 예외를 삭제한다. 삭제 후에는 월별 할인 정책에 따라 기본 할인 계산으로 돌아간다.

응답:

```json
{
  "deleted": true
}
```

### `DELETE /api/card-payments/events/{event_id}`

결제 또는 할인 기록을 취소한다. 즉시결제라면 연결된 현금흐름도 함께 삭제한다.

### `POST /api/card-payments/acknowledge-liquidity-reset`

14일 경과 후 기록상 미결제액을 확인한 사용자가 실제 현금흐름 반영액을 수동 보정했음을 기록한다. 남은 금액 자체를 삭제하거나 0원으로 바꾸는 API는 아니다.

### `POST /api/card-payments/late-entries`

카드사가 월말 이후 뒤늦게 매입한 직전월 사용내역을 추가한다.

```json
{
  "entry_date": "2026-05-31",
  "usage_place": "카드사 지연매입",
  "usage_item": "월말 사용내역",
  "amount_value": 12345
}
```

- 날짜는 직전월만 허용한다.
- archive에 `entry_kind = late_expense`로 추가한다.
- 추가 즉시 이번달 결제 대상에 포함된다.
- 이번달 결제 화면에서는 결제 대상 장부 행을 삭제할 수 있다. 삭제 시 해당 행의 즉시결제, 할인, 이월 참조도 함께 정리된다.
- 청구 탭의 항목은 `monthly_panels`에 저장되므로 이 결제 대상 묶음에 포함되지 않는다.
- 카드사 환급은 과거 기록을 삭제하지 않고 현금흐름 입금으로 기록한다.

### `POST /api/card-payments/deferrals/{entry_payment_key}`

카드 사용내역을 다음 결제월로 이월한다. 매월 14일까지, 아직 결제나 할인이 반영되지 않은 항목에만 사용할 수 있다. 적요 문자열로 이월 가능 여부를 제한하지 않는다.

이월 시 원본 장부 행을 현재 월 사용내역 맨 앞으로 옮기고 날짜 표시를 비우며 적요 앞에 `[이월]`을 붙인다. 이월 항목은 현재 결제월 합계와 자동 배분에서 제외된다.

### `DELETE /api/card-payments/deferrals/{entry_payment_key}`

현재 결제월에서 선택한 이월을 취소하고 `이번 달에 처리` 대상으로 되돌린다. 장부 행의 원래 날짜, 적요, 영역, 정렬 위치를 복원한다. 이월 취소는 매월 14일까지 가능하며 15일부터는 이월이 확정된다.

## 읽기 전용 공유

현재 외부 공유 대상은 `청구`와 `가족카드`이다.

허용되는 `panel_type`:

- `claim`: 청구
- `family_card`: 가족카드

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
  "total": 25000,
  "discount_total": 0,
  "minimum_payment_month": "2026-07",
  "minimum_total": 25000,
  "minimum_discount_total": 0
}
```

### `GET /share/{panel_type}`

읽기 전용 공유 데이터를 HTML 페이지로 반환한다. 앱 설치를 원치 않는 가족에게 보여주기 위한 웹 뷰다.

예시:

- `/share/claim`
- `/share/family_card`

공유 세션이 없으면 카카오톡 인앱 브라우저에서도 사용할 수 있는 네 자리 PIN 입력 화면을 먼저 표시한다. 새 DB의 기본 PIN은 `0000`이다.

공유 페이지에는 `최소 결제` 버튼이 있다. 서버는 각 미정산 행의 사용월 다음 달을 카드 결제 회차로 보고, 남아 있는 행 중 가장 이른 회차를 `minimum_payment_month`로 반환한다. 버튼을 누르면 해당 회차의 행만 표시하고 할인액과 실결제 합계를 다시 계산한다. 그 회차의 행을 모두 처리해 삭제하면 다음으로 이른 회차가 자동으로 최소 결제 대상이 된다.

공유 페이지의 안내는 `2026년 8월 최소 결제 금액`처럼 결제 연월을 함께 표시한다. 다시 `전체 보기`를 누르면 모든 미정산 항목을 표시한다.

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

## 현금흐름

### `GET /api/cash-flows`

현금 입출금 기록을 조회한다.

선택적 query parameter:

- `from=YYYY-MM-DD`: 해당 날짜 이후 기록을 조회한다. 시작일을 포함한다.
- `to=YYYY-MM-DD`: 해당 날짜 이전 기록을 조회한다. 종료일을 포함한다.
- `limit=N`: 날짜 조건을 적용한 결과 중 최신 N건을 조회한다. 1 이상이어야 한다.

세 조건은 함께 사용할 수 있다. 아무 조건도 지정하지 않으면 기존과 같이 전체 현금흐름을 최신순으로 반환한다.

```http
GET /api/cash-flows?from=2026-07-01&to=2026-07-31&limit=100
```

### `POST /api/cash-flows`

현금 입출금 기록을 생성한다. 입금은 양수, 출금은 음수 금액을 사용한다.

### `DELETE /api/cash-flows/{flow_id}`

현금 입출금 기록을 삭제한다.

카드 즉시결제 이벤트에 연결된 현금흐름은 `409`로 거부한다. 해당 출금을 취소하려면 `DELETE /api/card-payments/events/{event_id}`를 사용해야 하며, 이 전용 경로가 결제 이벤트·allocation·연결 현금흐름을 함께 삭제한다. 일반 수동 현금흐름과 현금성 고정지출의 기존 삭제/재활성화 동작은 유지한다.

## 서버 설정

### `GET /api/settings`

서버 설정값을 조회한다.

응답:

```json
{
  "scheduled_income": "400000",
  "cash_flow_balance": "0",
  "card_limit": "5800000",
  "owner_card_last4": "",
  "family_card_last4": ""
}
```

설정값:

- `scheduled_income`: 기본 예정 수입
- `cash_flow_balance`: 현금흐름 수동 보정값
- `card_limit`: 본인카드 사용률 Judgment의 기준 카드 한도. 가족 부담 지출은 본인 신용 압박에 합산하지 않는다.
- `owner_card_last4`: 본인회원 카드 끝 4자리. 비워둘 수 있다.
- `family_card_last4`: 가족카드 끝 4자리. 비워둘 수 있다.

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
  "scheduled_income": "450000"
}
```

허용 key:

- `scheduled_income`
- `cash_flow_balance`
- `card_limit`
- `owner_card_last4`
- `family_card_last4`

과거 또는 제거된 설정 key로 수정하는 요청은 `404 unknown setting`을 반환한다. Snapshot v7도 현재 DB key만 저장하며, 복원 파일에 제거된 설정·라벨이 있으면 manifest 검증 후 버린다.

## 앱 표시 라벨

### `GET /api/labels`

화면에 표시할 문구를 조회한다.

응답 예시:

```json
{
  "current_header_date": "날짜",
  "current_header_title": "적요",
  "current_header_amount": "금액",
  "panel_fixed_title": "고정지출",
  "panel_frozen_title": "동결",
  "panel_claim_title": "청구",
  "panel_family_card_title": "가족카드",
  "summary_cash_flow_balance_label": "현금흐름 반영액",
  "summary_remaining_liquidity_label": "잔여 유동성"
}
```

### `PATCH /api/labels/{key}`

화면 표시 문구를 수정한다.

요청:

```json
{
  "value": "잔액"
}
```

응답:

```json
{
  "summary_remaining_liquidity_label": "잔액"
}
```

허용 key는 현재 DB의 `app_labels`에 존재하는 key다.

## 관리자 작업

### `GET /api/admin/snapshot`

장부 운용 데이터 전체와 비민감 운영 설정을 JSON snapshot 파일로 내려받는다.

응답:

- Content-Type: `application/json`
- 파일명: `money-note-snapshot-...money-note-snapshot.json`

포함:

- `schema_version`
- `exported_at`
- `range`
- `card_charge_policy`: 카드별 정책 이력, 교통카드 프로필 선택 의미와 교통·통행 분류 규칙의 검증용 명세
- `manifest`: canonical JSON 기준 SHA-256 무결성 정보. `manifest` 자기 자신은 hash 대상에서 제외한다.
- 전체 `ledger_entries`, `monthly_panels`, `cash_flows`
- 전체 `card_payment_batches`, `card_payment_batch_items`
- 전체 `card_payment_events`, `card_payment_allocations`, `card_payment_deferrals`
- 비민감 `app_settings`
- `app_labels`

제외:

- `users`
- `auth_sessions`
- `share_sessions`
- `audit_logs`
- 비밀번호/해시, 세션 토큰, 공유 PIN 해시

### `GET /api/admin/apk`

서버에 배치된 Android APK 파일을 내려받는다. 모바일 앱 배포 편의를 위한 파일 다운로드 API이며, 로그인한 사용자만 호출할 수 있다.

응답:

- Content-Type: `application/vnd.android.package-archive`
- 파일명: 서버 환경변수 `MONEY_NOTE_APK_FILENAME` 값

서버 환경변수 `MONEY_NOTE_APK_PATH`가 비어 있거나 해당 파일이 없으면 `404`와 `apk file not found`를 반환한다. 이 API는 장부 데이터를 읽거나 수정하지 않는다.

### `POST /api/admin/snapshot/restore`

JSON snapshot을 복원한다. 현재 비밀번호를 다시 확인하며, 장부 운용 데이터와 비민감 운영 설정을 snapshot 내용으로 교체한다.

요청:

파일 원문 문자열로 보내는 방식:

```json
{
  "password": "현재 계정 비밀번호",
  "snapshot_text": "{\"schema_version\":7,...}"
}
```

이미 JSON 객체로 파싱한 뒤 보내는 방식:

```json
{
  "password": "현재 계정 비밀번호",
  "snapshot": {
    "schema_version": 7,
    "exported_at": "2026-06-11T00:00:00Z",
    "range": {
      "scope": "all"
    },
    "card_charge_policy": {
      "schema_version": 2,
      "covered_through": "2026-06",
      "classifier": {"schema_version": 1},
      "profile_selectors": {"transit": {"schema_version": 1}},
      "cards": {}
    },
    "manifest": {
      "algorithm": "sha256",
      "tables": {
        "ledger_entries": {
          "columns": ["..."],
          "row_count": 10,
          "sha256": "..."
        }
      },
      "data_sha256": "...",
      "card_charge_policy_sha256": "...",
      "content_sha256": "..."
    },
    "data": {}
  }
}
```

`snapshot_text` 또는 `snapshot` 중 하나를 보낸다. 웹 프론트엔드는 브라우저가 읽은 파일 원문을 `snapshot_text`로 보낸다.

응답:

```json
{
  "restored": {
    "ledger_entries": 10,
    "monthly_panels": 4
  }
}
```

`users`, `auth_sessions`, `share_sessions`, `audit_logs`는 복원 대상이 아니다. snapshot 구조가 맞지 않거나 지원하지 않는 `schema_version`, manifest 불일치, 과거 카드 정책 보존 실패, 필수 테이블/컬럼 누락, 외래키 오류가 있으면 `400`을 반환한다.

요청 본문은 기본 25 MiB로 제한한다. `Content-Length`가 없거나 chunked 전송이어도 누적 본문이 `MONEY_NOTE_SNAPSHOT_RESTORE_MAX_BYTES`를 넘으면 `413`을 반환한다.

하위호환 정책상 manifest 검증을 통과한 snapshot의 알 수 없는 컬럼은 현재 서버 DB에 삽입하지 않고 무시한다. 구버전 snapshot에 현재 서버의 새 컬럼이 없으면 DB 기본값 또는 `NULL` 허용 정책을 따른다. 단, 필수 테이블 누락, 민감 설정 포함, manifest 불일치, 외래키 오류, 기본값 없는 `NOT NULL` 컬럼 누락은 복원 실패로 처리한다.

현재 서버는 `schema_version = 7`을 생성하고 v4, v5, v6, v7을 복원한다. v6은 `monthly_panels.confirmed_cash_flow_id`를 포함하고, v7은 `ledger_entries.source_planned_entry_id`, `monthly_panels.confirmed_month`, `card_payment_events.idempotency_key`, `request_fingerprint`를 추가로 보존한다. 구버전에서 이 nullable 필드가 없으면 미연결 또는 비-idempotent 과거 행으로 복원한다. 지원 버전의 `card_charge_policy`와 주요 상단 메타데이터는 데이터와 함께 SHA-256 검증 대상이다. v4는 원문 manifest를 먼저 검증한 뒤 유동성 설정과 라벨의 과거 key를 현재 key로 정규화한다. 같은 의미의 old/new key가 함께 있고 값이 다르면 복원을 중단한다. 카드 정책 명세 v2는 교통카드 프로필 선택기의 의미도 검증한다. 2026-08-20에 남아 있던 v4 Snapshot 전환을 위해 내부 카드 정책 명세 v1 읽기 경로를 유지하며, 파일 형식 v3 이하는 지원하지 않는다. Snapshot 당시 정책이나 분류 규칙이 현재 서버에서 바뀌었으면 복원하지 않으며, 명세의 `covered_through` 이후부터 적용되는 새 binding 추가만 허용한다. 프로필 선택 이력은 비민감 `app_settings` 데이터로 함께 복원한다. 이 명세는 Snapshot에서 임의 정책을 실행하기 위한 입력이 아니다.

Snapshot export는 하나의 SQLite read transaction에서 모든 테이블을 읽어 서로 다른 commit 시점이 섞이지 않게 한다. 복원은 운영 DB를 건드리기 전에 동일한 삽입 경로로 임시 DB dry-run을 수행한다. 실제 복원은 write transaction을 먼저 확보한 뒤 같은 transaction의 운영 상태로 `pre_restore-...money-note-snapshot.json` 파일을 반드시 저장하고 데이터를 교체한다. 이 파일의 manifest·dry-run 검증에 실패하면 복원을 중단한다.

dry-run은 외래키뿐 아니라 명백한 핵심 관계 손상도 거부한다. 현재 검사는 중복된 non-null `ledger_entries.payment_key`, 복수 active 결제 batch, 결제 이벤트 총액과 allocation 합계 불일치, 즉시결제 이벤트와 연결 현금흐름 절댓값 불일치다. Summary나 Judgment를 다시 계산하는 두 번째 회계 엔진은 두지 않는다.

월마감, 장부 전체 초기화, 청구 일괄 처리 완료, 가족카드 일괄 처리 완료도 실행 직전 현재 장부 상태를 `pre_restore` snapshot으로 자동 저장한다.

### `GET /api/admin/operation-stats`

운영 데이터 크기와 테이블별 row count를 조회한다. 설정 모달 하단의 운영 데이터 크기 섹션에서 사용한다.

응답:

```json
{
  "db_file_size_bytes": 131072,
  "empty_db_size_bytes": 98304,
  "estimated_data_size_bytes": 32768,
  "pre_restore_total_size_bytes": 24576,
  "pre_restore_count": 3,
  "table_row_counts": {
    "ledger_entries": 42,
    "monthly_panels": 5
  }
}
```

`estimated_data_size_bytes`는 현재 SQLite 파일 크기에서 빈 스키마 DB 파일 크기를 뺀 추정값이다. SQLite page 구조상 실제 순수 데이터 크기와 완전히 같지는 않다.

### `GET /api/admin/snapshot/pre-restore`

서버가 snapshot restore 직전에 자동 저장한 `pre_restore` 목록을 조회한다.

응답:

```json
{
  "backups": [
    {
      "filename": "pre_restore-20260611T010101Z.money-note-snapshot.json",
      "created_at": "2026-06-11T01:01:02Z",
      "size_bytes": 12345,
      "snapshot_id": "canonical-content-sha256",
      "exported_at": "2026-06-11T01:01:01Z"
    }
  ]
}
```

### `DELETE /api/admin/snapshot/pre-restore/{filename}`

특정 `pre_restore` snapshot 파일을 삭제한다. 로그인은 필요하지만, 현재 비밀번호 재확인은 요구하지 않는다.

`filename`은 `pre_restore-YYYYMMDDTHHMMSSZ.money-note-snapshot.json` 또는 같은 초에 여러 개가 만들어질 때의 `pre_restore-YYYYMMDDTHHMMSSZ-2.money-note-snapshot.json` 형식만 허용하며, 서버는 `snapshot-backups` 디렉터리 밖의 파일을 삭제하지 않는다.

응답:

```json
{
  "deleted": true
}
```

### `DELETE /api/admin/snapshot/pre-restore`

조회 가능한 모든 `pre_restore` snapshot 파일을 일괄 삭제한다. 로그인은 필요하지만, 현재 비밀번호 재확인은 요구하지 않는다. 서버는 정해진 filename 형식을 만족하는 유효한 `pre_restore` 파일만 삭제한다.

응답:

```json
{
  "deleted": 3
}
```

### `POST /api/admin/snapshot/pre-restore/{filename}/restore`

특정 `pre_restore` snapshot을 선택해 되돌린다.

요청:

```json
{
  "password": "현재 계정 비밀번호"
}
```

이 복원도 일반 snapshot restore와 동일하게 현재 비밀번호 확인, filename 검증, manifest 검증, 임시 DB dry-run, mandatory 새 `pre_restore` 생성, 실제 restore 절차를 거친다.

### `POST /api/admin/reset-ledger-data`

현재 비밀번호를 다시 확인한 뒤 장부 운용 데이터를 모두 초기화한다.

실행 직전 서버는 현재 장부 상태를 `pre_restore` snapshot으로 자동 저장한다.

요청:

```json
{
  "password": "현재 계정 비밀번호"
}
```

응답:

```json
{
  "deleted": {
    "ledger_entries": 0,
    "monthly_panels": 0,
    "cash_flows": 0
  }
}
```

삭제 대상은 당월/전체 기록, 월별 패널, 현금흐름, 카드 결제/할인/이월 데이터다. 사용자 계정, 로그인 세션, 공유 PIN, 앱 설정, 관리 로그는 유지한다.

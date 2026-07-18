# API 명세

이 문서는 현재 구현된 `money-note` 서버 API 기준이다. 서버는 FastAPI로 구현되어 있으며, 기본 실행 주소는 Docker Compose 기준 `http://localhost:18080`이다.

## 공통 규칙

- 요청/응답 형식: JSON
- 인증: 공개 예외를 제외한 앱 API는 로그인 cookie 또는 bearer token 필요
- 세션 복원: 앱 시작 시 `GET /api/auth/me`를 먼저 호출한다. `401`이면 로그인 화면을 보여준다.
- 날짜 형식: `YYYY-MM-DD`
- 월 형식: `YYYY-MM`
- 금액 형식: 원화 정수. 비율 설정처럼 명시된 예외가 아니면 소수점 금액을 쓰지 않는다.
- 금액 필드:
  - `amount_value`: 계산 완료된 숫자 금액
  - `amount_expr`: 과거 호환용 문자열 필드. 신규 화면에서는 계산된 금액을 중시한다.
- 정렬:
  - `sort_order` 오름차순, 동률이면 `id` 오름차순
  - 사용자가 직접 정렬을 바꾸는 경우 reorder API를 사용한다.

모바일 앱 구현 메모:

- 서버 DB가 단일 원본이다. 모바일 앱은 로컬 장부를 별도로 authoritative하게 유지하지 않는다.
- 로그인 성공 응답의 `session_token`은 cookie 사용이 불편한 클라이언트에서 `Authorization: Bearer ...`로 보낼 수 있다.
- 변경 API를 호출한 뒤에는 관련 조회 API를 다시 호출해 서버 계산 결과를 화면에 반영한다.
- 파일 다운로드 API는 JSON이 아니라 blob/file 응답일 수 있다. 대표적으로 snapshot export와 APK 다운로드가 그렇다.
- `claim`과 `family_card`는 회수 예정 정보이며, 당월 소비 원장/소비 통계/익월 유동성 계산에 직접 넣지 않는다.

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

cookie 저장을 쓰기 어려운 클라이언트를 위해 로그인 응답에는 `session_token`도 포함된다. 프론트엔드는 이 값을 저장하고 이후 요청에 `Authorization: Bearer ...` 헤더로 함께 보낼 수 있다. 모바일 앱은 웹 cookie 세션과 유효기간을 분리하기 위해 `POST /api/auth/mobile-login`을 사용한다.

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
    "payment_key": "..."
  }
]
```

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

`spending_category` 허용값:

- `essential`: 안 썼으면 큰일 났을 돈
- `questionable`: 꼭 써야 했을까...?
- `dignity`: 최소한의 품위유지비
- `null`: 미분류

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
- 새 당월 지출은 기존 planned 항목의 사용처, 사용항목, 금액 구조를 따른다.
- 원래 planned 항목은 삭제하지 않고 현재 월에 확인된 상태로 숨겨진다.
- 월마감 후 다음 달에는 같은 planned 항목이 다시 보인다.

응답:

```json
{
  "planned_entry": {},
  "expense_entry": {}
}
```

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

현재 월 패널 항목을 조회한다. `fixed`는 월 반복 관리 항목으로 항상 포함된다. `claim`과 `family_card`는 월별 소비가 아니라 회수 예정 큐이므로, 사용자가 일괄 처리 완료하기 전까지 월과 무관하게 모두 포함된다. `frozen`은 요청 시점의 현재 월 항목만 포함된다.

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

특정 패널 타입 항목을 전부 삭제한다. `claim`과 `family_card`는 월과 무관하게 현재 남아 있는 회수 예정 큐 전체를 삭제한다.

응답:

```json
{
  "deleted": 3
}
```

### `POST /api/month/current/panels/type/{panel_type}/complete`

청구 또는 가족카드의 현재 남아 있는 회수 예정 큐 전체를 일괄 처리 완료하고 삭제한다. `claim`, `family_card`만 허용하며 다른 패널과 월마감에는 영향을 주지 않는다.

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
  "base_next_month_liquidity": 400000,
  "card_total": 123456,
  "planned_recurring_total": 68990,
  "transfer_or_deposit_total": 500000,
  "interest_expense": 0,
  "frozen_asset_total": 100000,
  "liquidity_status": 200000,
  "next_month_liquidity": -23456
}
```

`planned_recurring_total`은 확인 여부와 무관한 카드 정기결제 전체 예정액이다. 카드 정기결제 패널의 총계는 이 값을 표시한다.

`transfer_or_deposit_total`은 기존 API 호환 이름을 유지하지만, 화면에서는 `고정지출`로 표시한다. 이 값은 현금성 고정지출 패널과 `planned_recurring_total`을 합산한다.

익월 유동성 계산에서는 중복 차감을 피하기 위해, 카드 지출로 편입되지 않은 카드 정기결제 예정액만 고정지출 차감분으로 사용한다. 즉 카드 정기결제를 `확인`하면 표시용 고정지출 총합은 유지되지만, 유동성 계산에서는 카드대금으로 이동한다.

계산식:

```text
next_month_liquidity
= base_next_month_liquidity
  - card_total
  - liquidity_fixed_total
  - interest_expense
  - frozen_asset_total
  + liquidity_status
```

`liquidity_fixed_total`은 응답 필드가 아니라 내부 계산값이다. `현금성 고정지출 + 아직 카드 지출로 확인되지 않은 카드 정기결제 예정액`이다.

`card_total`은 본인 당월 카드 지출의 할인 후 금액이다. 청구 탭 금액은 청구 표시 합계와 공유 청구서의 실청구액에는 반영하지만, `next_month_liquidity` 계산에는 넣지 않는다.
청구와 가족카드는 회수 예정 금액으로 보며, 당월 소비 통계와 `당월` 큰 탭 합계에도 넣지 않는다.

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
    "level": "steady",
    "message": "청구와 가족카드가 당월 지출보다 활발합니다. 가족이라는 제도가 회계상으로도 실재합니다."
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
  "can_close": true
}
```

`needs_close = true`이면 웹 첫 화면에서 월마감 검토 경고를 표시한다.

### `POST /api/month/current/close`

현재 장부에서 가장 오래된 미마감 월 하나만 전체 기록으로 넘긴다. 현재 달은 매월 27일부터 조기 마감할 수 있으며 명시적 확인값이 필요하다.

요청:

```json
{
  "allow_early_close": false
}
```

동작:

- 가장 오래된 미마감 월의 `book_section = current`, `entry_kind != planned` 항목만 `archive`로 복사한다.
- 복사된 항목은 `archive`의 마지막 `sort_order` 뒤에 append된다.
- 해당 월의 원래 `current` 비-planned 항목만 삭제된다.
- 새 달 기록이 먼저 입력되어 있어도 그대로 남는다.
- 조기 마감 후 같은 달 날짜로 추가한 일반 지출은 `archive`에 바로 저장된다.
- `planned` 항목, 즉 카드 정기결제는 현재 월에 남고, 닫힌 달의 확인 상태는 초기화되어 다음 사이클에서 다시 확인할 수 있다.

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
- 그 외에는 기본 할인액을 `floor(amount_value * 0.012)`로 계산한다.
- `discount_override = 1`이면 기본 할인 계산 대신 저장된 할인액을 쓴다. 저장된 할인액이 0원이면 할인 제외로 취급한다.

### `PATCH /api/card-discounts/months/{month}?scope=owner|family`

본인회원 카드와 가족카드의 월별 할인 혜택 여부를 서로 독립적으로 저장한다.

```json
{ "policy": "enabled" }
```

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

현재 결제월의 결제 현황을 조회한다. 대상은 직전월 1일~말일 사용내역이다.

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

14일 경과 후 정규결제 완료 의제로 인해 사용자가 실제 유동성 현황을 수동 보정했음을 기록한다.

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
  "total": 25000
}
```

### `GET /share/{panel_type}`

읽기 전용 공유 데이터를 HTML 페이지로 반환한다. 앱 설치를 원치 않는 가족에게 보여주기 위한 웹 뷰다.

예시:

- `/share/claim`
- `/share/family_card`

공유 세션이 없으면 카카오톡 인앱 브라우저에서도 사용할 수 있는 네 자리 PIN 입력 화면을 먼저 표시한다. 새 DB의 기본 PIN은 `0000`이다.

공유 페이지에는 `최소 결제` 버튼이 있다. 버튼을 누르면 공유 페이지 접속일 기준 현재 월 사용분은 흐리게 표시하고, 직전월 이전 사용분과 `이자`가 포함된 항목을 최소 결제 대상으로 선명하게 남긴다. 다시 `전체 보기`를 누르면 모든 항목을 같은 선명도로 표시한다.

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

## 서버 설정

### `GET /api/settings`

서버 설정값을 조회한다.

응답:

```json
{
  "base_next_month_liquidity": "400000",
  "interest_expense": "0",
  "liquidity_status": "0",
  "card_limit": "5800000",
  "owner_card_last4": "",
  "family_card_last4": ""
}
```

설정값:

- `base_next_month_liquidity`: 이달 기준 수입 기록이 없을 때 쓰는 기본 예정 수입
- `interest_expense`: 이자지출
- `liquidity_status`: 유동성 현황
- `card_limit`: 본인카드와 가족카드 합산 사용률을 판단할 카드 한도
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
  "base_next_month_liquidity": "450000"
}
```

허용 key:

- `base_next_month_liquidity`
- `interest_expense`
- `liquidity_status`
- `card_limit`
- `owner_card_last4`
- `family_card_last4`

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
  "summary_next_month_liquidity_label": "익월 유동성"
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
  "summary_next_month_liquidity_label": "잔액"
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
- `manifest`: canonical JSON 기준 SHA-256 무결성 정보. `manifest` 자기 자신은 hash 대상에서 제외한다.
- 전체 `ledger_entries`, `monthly_panels`, `cash_flows`
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
  "snapshot_text": "{\"schema_version\":3,...}"
}
```

이미 JSON 객체로 파싱한 뒤 보내는 방식:

```json
{
  "password": "현재 계정 비밀번호",
  "snapshot": {
    "schema_version": 3,
    "exported_at": "2026-06-11T00:00:00Z",
    "range": {
      "scope": "all"
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
      "data_sha256": "..."
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

`users`, `auth_sessions`, `share_sessions`, `audit_logs`는 복원 대상이 아니다. snapshot 구조가 맞지 않거나 지원하지 않는 `schema_version`, manifest 불일치, 필수 테이블/컬럼 누락, 외래키 오류가 있으면 `400`을 반환한다.

하위호환 정책상 manifest 검증을 통과한 snapshot의 알 수 없는 컬럼은 현재 서버 DB에 삽입하지 않고 무시한다. 구버전 snapshot에 현재 서버의 새 컬럼이 없으면 DB 기본값 또는 `NULL` 허용 정책을 따른다. 단, 필수 테이블 누락, 민감 설정 포함, manifest 불일치, 외래키 오류, 기본값 없는 `NOT NULL` 컬럼 누락은 복원 실패로 처리한다.

복원은 운영 DB를 건드리기 전에 동일한 삽입 경로로 임시 DB dry-run을 수행한다. 또한 실제 복원 직전 현재 운영 DB를 `pre_restore-...money-note-snapshot.json` 파일로 반드시 저장하고, 이 파일의 manifest 검증에 실패하면 복원을 중단한다.

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
      "snapshot_id": "canonical-data-sha256",
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

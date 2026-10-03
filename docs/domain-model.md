# Money Note Domain Model

> 이 문서는 Money Note의 도메인 모델에 대한 기준 문서다.
>
> 구현, 리팩토링, 스키마 변경, UI 변경은 이 문서의 정의를 우선한다.
>
> 코드가 이 문서와 충돌한다면, 코드가 아니라 도메인 모델이 맞는지 먼저 검토한다.

---

# 1. Money Note의 목적

Money Note의 목적은 다음 질문에 답하는 것이다.

Money Note는 단일-owner 서비스다. 서로 다른 소유자의 장부 격리·권한 모델은 지원하지 않는다. 다만 현재 `users` 테이블, 사용자 생성 CLI와 인증 API는 복수의 active principal을 수용한다. 이 구현상 가능성을 단일 principal 강제 보장으로 오인하지 않는다. 재시도 artifact의 소유자 확인은 기존 한 파일에만 보존하며, 같은 owner의 logout/login·토큰 갱신·재시작에도 session/retry correctness는 필요하다. 별도 multi-user 장부나 저장소 namespace를 만들지 않는다.

> 나는 실제로 얼마를 썼는가?
>
> 현재 예산 주기에서 실제로 얼마를 더 감당할 수 있는가?

따라서 Money Note는 단순한 가계부가 아니다.

모든 금액을 단순 합산하지 않으며, 금액의 성격에 따라 구분한다.

예를 들어:

- 실제 소비
- 가족에게 청구할 금액
- 카드사 청구 예정 금액
- 예산 주기의 현금흐름

은 서로 다른 의미를 가진다.

---

# 2. 핵심 원칙

Money Note의 모든 계산은 다음 원칙을 따른다.

## 정확한 원화 금액의 제품 범위

authoritative 금액은 **−9,007,199,254,740,991 ~ +9,007,199,254,740,991원**(`±(2^53−1)`)의 정확한 정수다. 개별 도메인의 기존 비음수/nullable 규칙은 별도로 유지한다. 이 범위는 JavaScript Number와 historical SQLite REAL에도 모든 정수가 정확히 표현되는 공통 범위다. 개인 가계부에 full-int64 외부 호환 요구는 없으며, 이전 signed-64-bit validator를 end-to-end exact 지원 보장으로 해석하지 않는다. 이번 결정은 그 nominal 범위를 명시적으로 축소한다. BigInt/decimal-string 프로토콜이나 arbitrary precision 제품을 추가하지 않는다.

입력·금액 설정·migration admission·v7 Snapshot은 손실 없이 정수/범위를 검사한다. 정수형 REAL은 이 범위에서만 허용한다. 이미 범위 밖으로 반올림된 과거 REAL을 원래 값으로 추측 복구하지 않는다. DB의 historical REAL 컬럼을 rebuild하지 않는다. 금액 계약 자체는 Snapshot 버전을 변경하지 않으며, DB version 4는 별도의 recurring identity 호환 checkpoint다.

Summary와 결제 배분/할인 이벤트 누계는 Python 정수로 계산한다. **계산 중간값**은 외부 금액 범위나 SQLite int64보다 커도 정확하게 상쇄할 수 있다. 응답에 노출하는 각 명명된 금액/합계는 다시 제품 범위를 검사한다. 개별 행이 유효해도 합계가 범위 밖이면 해당 금융 조회는 controlled `422` domain error이며 근사값·overflow·wrap을 반환하지 않는다. 이는 그 행을 자동 삭제하거나 금액을 바꾸라는 뜻이 아니다. 개별 저장 값의 유효성과 전체 조회 합계의 유효성은 별개의 조건이다.

웹·모바일은 같은 범위를 입력/응답/local baseline/journal에서 검사하며 서버 계산을 대체하지 않는다. Offline journal은 잘못된 값 또는 범위 밖 예상 합계를 append 전에 거부한다. 할인 **비율**과 진단용 사용률은 금액과 구별한다. 기존 Decimal 1.2%/floor 정책과 10,000→9,880원 의미는 유지한다. 실제 운영 데이터가 새 범위에 있는지 이번 작업에서 조회하지 않았으며 배포 전 일관된 사본에서 값과 관련 합계를 따로 확인해야 한다.

## 원칙 1

원장은 사실(Fact)을 기록한다.

원장에는 실제로 발생한 소비만 기록한다.

회수 예정 금액이나 예상 금액은 원장이 아니다.

---

## 원칙 2

당월 지출 총합은 "내가 최종적으로 부담하는 실제 소비"다.

가족에게 청구하거나 가족카드로 정리할 금액은 회수 예정 금액이며, 당월 지출 총합에 넣지 않는다.

예를 들어:

- 내가 카드로 10,000원을 결제했다.
- 나중에 가족에게 10,000원을 받을 예정이다.

이 경우 Money Note의 목적상 이 금액은 "내 소비"가 아니라 "회수 예정 금액"이다.

따라서 당월 지출 총합에는 포함하지 않는다.

---

## 원칙 3

청구 예정 금액은 소비 통계에 포함하지 않는다.

소비 통계의 목적은

> 내가 무엇에 돈을 사용했는가

를 보는 것이다.

따라서 회수 예정 금액은 통계 대상이 아니다.

---

## 원칙 4

유동성은 실제 감당해야 하는 현금흐름이다.

유동성은

> 내가 현재 예산 주기를 실제로 감당할 수 있는가

를 보기 위한 값이다.

따라서 단순 장부 합계가 아니라 실제 현금 유출입 기준으로 계산한다.

---

## 원칙 5

서버는 런타임 데이터와 계산 결과의 단일 진실 원천이다.

- SQLite DB가 영속 데이터의 원본이다.
- 할인 가능 여부, 자동 할인액, 수동 override 반영액, 실결제액, 카드대금, 고정지출, 유동성, 청구·가족카드 합계는 서버가 계산한다.
- 기준일과 기준 월은 서버의 `app_today()` 및 월 상태 API가 결정한다.
- 웹과 모바일은 서버 응답을 표시하고 사용자 입력을 전달하는 클라이언트다.
- 웹과 모바일에 1.2% 할인율, 교통·통행 키워드, 요약 합계 계산식을 별도로 복제하지 않는다.
- 변경 API 호출 뒤에는 관련 조회 API를 다시 호출해 서버가 확정한 상태를 화면에 반영한다.

`LedgerEntry`와 `MonthlyPanel` 응답의 다음 필드는 저장 컬럼이 아니라 서버 표시 투영값이다.

- `discount_policy`
- `automatic_discount_eligible`
- `automatic_discount_amount`
- `effective_discount_amount`
- `effective_amount_value`
- 원장의 `is_transport`, `is_toll`

클라이언트가 이 값을 자체 계산으로 보정하면 서버와 화면의 의미가 갈라지므로 금지한다.

---
## 원칙 6

모바일 Offline Mode는 서버 authoritative 원칙의 예외가 아니라 임시 기록 경계다.

- baseline은 완전히 성공한 마지막 정상 서버 동기화 응답과 같은 시점의 검증된 authoritative Snapshot B를 모바일에 원자적으로 보존한 것이다. Snapshot을 mutable offline database로 사용하지 않는다.
- offline journal에는 카드 사용, 현금 입출금, 현금성 고정지출 확인, 카드 정기결제 확인의 authoritative input만 append한다. 카드 사용 시 사용자가 직접 입력한 실결제액은 수동 override input이며 서버 계산 결과와 구분한다.
- Offline 화면의 잔여 유동성·카드대금·월 지출·현금흐름 반영액은 허용 operation의 명백한 delta만 적용한 display-only estimate다. 기준 월 판정과 server-only transition을 클라이언트에 복제하지 않는다.
- 신규 본인카드 사용의 자동 할인 estimate는 마지막 정상 baseline에 서버가 포함한 버전드 projection descriptor만 해석할 수 있다. 모바일에 할인율·카드 분류·정책 선택 규칙을 하드코딩하지 않으며, descriptor가 없거나 알 수 없는 형식이면 gross amount로 보수적으로 표시한다.
- projection descriptor와 그 계산 결과는 authoritative 정책이나 replay input이 아니다. 서버 복구 후에는 같은 journal input을 서버가 현행 사용월 정책으로 다시 계산한다.
- 현금흐름 estimate는 device-local today까지 발생한 건만 반영하며 reconciliation 후 서버가 authoritative 날짜·정책으로 다시 계산한다.
- estimate는 `오프라인 예상값`으로 표시하고 journal, Snapshot restore 또는 reconciliation payload에 넣지 않는다.
- 서버 복구 확인은 자동 reconciliation 권한이 아니다. 모바일은 `RECONCILIATION_REQUIRED`로 전환하여 모든 write를 막고 사용자의 적용/폐기 선택을 저장한다.
- Phase 2 Mobile Wins는 server-side 단일 transaction에서 정확히 `Apply(B, J)`를 실행하고 Server Wins는 J를 replay하지 않는다. 양쪽 recovery point 검증과 explicit confirmation 없이는 시작하지 않으며, committed 결과 확인과 fresh authoritative rebuild 전에는 journal과 recovery metadata를 삭제하지 않는다.

상세 상태 머신, operation matrix, 저장 형식과 Snapshot 재사용 계획은 [모바일 Offline Mode](offline-mode.md)를 따른다.

---


# 3. 원장 (ledger_entries)

ledger_entries는 Money Note의 핵심 원장이다.

의미:

> 내가 실제로 사용한 돈

포함:

- 카드 사용
- 현금 사용
- 계좌이체 사용
- 기타 실제 소비

포함하지 않음:

- 회수 예정 금액
- 청구 예정 금액
- 통계용 가상 값

ledger_entries는 시스템의 가장 중요한 데이터다.

---

# 4. 카드 할인

Money Note는 카드 할인 효과를 고려한다.

할인 계산에서는 돈을 매개한 카드를 다음 네 종류의 독립 객체로 취급한다.

| 카드 | 현재 자동 할인 정책 | 월별 혜택 스위치 |
| --- | --- | --- |
| 본인카드 | 사용금액의 1.2% 청구할인 | 본인카드 스위치 |
| 가족카드 | 사용금액의 1.2% 청구할인 | 가족카드 스위치 |
| 통행료카드 | 자동 할인 없음 | 없음 |
| 교통카드 | `자동 할인 없음` 또는 `본인카드와 동일` | 선택한 프로필에 따름 |

본인카드와 가족카드는 현재 우연히 같은 할인식을 사용한다. 같은 실물 카드에서 파생되었다는 상속 관계로 모델링하지 않으며, 서로 독립된 정책 이력과 월별 혜택 상태를 가진다. 한쪽 정책이 바뀌어도 다른 쪽이 자동으로 바뀌지 않는다.

현재 본인카드와 가족카드의 기본 계산식:

- 기본 할인율 1.2%
- 할인액 = floor(사용금액 × 0.012)

통행·하이패스 문구가 있는 거래는 통행료카드로, 교통·대중교통·버스·지하철 문구가 있는 거래는 교통카드로 분류한다. 그 밖의 원장과 Claim은 본인카드, Family Card 패널은 가족카드를 기본 카드로 사용한다.

정책 선택과 실결제액 계산의 단일 진실 원천은 `backend/app/services/card_charge/`다. 사용월별 정책 이력을 코드 레지스트리에 보존하므로, 나중에 카드를 바꾸더라도 과거 거래를 새 정책으로 재해석하지 않는다. 일반적인 카드 교체를 위한 정책 편집 UI는 두지 않는다.

교통카드는 현재 두 프로필 중 하나를 사용한다.

- `자동 할인 없음`: 교통카드 자체의 자동 할인액은 항상 0원이다.
- `본인카드와 동일`: 해당 사용월의 본인카드 계산식과 본인카드 월별 혜택 `enabled`/`disabled` 상태를 함께 따른다.

웹과 모바일 설정의 `본인카드와 동일` 체크박스는 이 두 프로필만 선택한다. 선택 이력은 `app_settings`의 `card_charge_profile:transit:{YYYY-MM}`에 저장하고, 거래 사용월보다 늦지 않은 가장 최근 설정을 적용한다. 설정이 없는 구버전 데이터는 `자동 할인 없음`으로 해석한다. 통행료카드는 이 선택과 무관하며 항상 자동 할인 없음이다.

프로필 변경의 효력 단위는 현재 **월**이다. 현재 월에 설정을 바꾸면 그 월의 교통카드 거래 전체가 새 프로필로 다시 계산되며, 이전 월 거래는 바뀌지 않는다. 설정 버튼을 누른 정확한 시각 이후 거래만 바꾸는 기능은 아직 지원하지 않는다. 이를 지원하려면 거래에 적용 정책을 고정하거나 시각 단위 정책 이력을 추가해야 한다.

평가 문맥에는 `title`, `merchant`, `spending_category`를 함께 전달한다. 현재 단일 할인율 정책은 이 문맥으로 할인율을 바꾸지 않지만, 향후 `[의료]`, `[쇼핑]` 같은 분류별 정책을 추가할 수 있는 입력 경계로 보존한다.

---

## 할인 적용 여부

월별로 할인 적용 여부를 설정한다.

### 할인 적용 월

할인 적용

### 할인 미적용 월

모든 할인액 = 0

본인카드와 가족카드의 월별 적용 여부는 서로 독립적으로 저장한다. 통행료카드는 월 스위치를 사용하지 않는다. 교통카드는 `본인카드와 동일` 프로필일 때만 본인카드의 해당 월 스위치를 따른다.

새 카드 사용내역의 사용처 또는 사용내역에 `도시가스`, `가스요금`, `전기`, `전력`, `수도`가 부분 문자열로 포함되면 최초 할인 선택은 **할인 제외**다. Claim/Family Card는 입력 제목에 같은 규칙을 적용하고, 새 카드 정기결제 원본의 기본 제외는 확인으로 생성된 카드 사용에도 이어진다. 이는 등록 시점의 기본값이며 사용자는 명시적으로 `할인 적용`을 선택할 수 있다. 서버는 등록 transaction에서 이 기본 제외를 저장하므로 이후 조회·수정·재접속이 키워드로 사용자 선택을 다시 덮어쓰지 않는다. 모바일의 키워드 검사는 입력 체크박스 초기 상태만 위한 힌트이고 금융 할인액은 서버가 결정한다. 알림 후보의 카드 정체성과 거래 사용월 정책은 그대로 유지하며, 명시적 체크 선택이 공과금 기본값보다 우선한다. 반면 통행료는 별도 카드 정책상 자동 할인이 없는 기존 hard exclusion이다.

---

## discount_override

공과금 기본 제외는 explicit 금융 입력이 없을 때만 적용한다. `discount_enabled`, `discount_override_amount`뿐 아니라 계속 지원하는 `discount_override`/`aux_amount_value`의 수동 할인도 보존한다. 패널의 `discount_amount`/`discount_override`도 같은 의미를 유지한다. 한국전력 원금 10,000원에 수동 할인 120원이면 부담은 9,880원이다. Offline journal은 기존 boolean/override-amount 입력만 사용하며 구 DB 필드나 계산된 부담을 새 authoritative 입력으로 추가하지 않는다.

Claim/Family 생성에서 `discount_enabled=false`만 전달해도 명시적 할인 제외(`discount_override=1`, 수동 할인액 0)의 의미다. 별도 redundant flag가 없어도 무시하지 않는다. 이미 입력한 monetary override는 boolean보다 우선하고, 명시적 boolean은 공과금 기본값·월별 정책보다 우선한다. 통행료의 기존 hard-exclusion 의미는 변경하지 않는다.

discount_override는

> 기본 할인 계산을 사용하지 않고 저장된 할인액을 강제 적용한다

는 의미다.

즉:

- 기본 할인 계산 사용
- 저장된 할인액 사용

을 구분하기 위한 값이다.

수동 override는 카드 종류와 월별 혜택 상태보다 항상 우선한다. 따라서 통행료카드나 교통카드도 사용자가 실결제액을 직접 입력한 경우에는 저장된 수동 할인액으로 실결제액을 계산한다.

---

## 후불 하이패스 통행료

후불 하이패스카드는 본인 신용카드 청구서에 합산되지만 할인 계산에서는 별도 통행료카드다.

- 하이패스 차로에서 발생한 통행료는 본인 카드 청구서에 합산된다.
- 통행료에는 본인 카드의 기본 1.2% 할인을 적용하지 않는다.
- 하이패스 거래는 무승인 거래이므로 우리카드 승인 푸시가 오지 않는다.
- 사용일, 매입일, 실제 결제월이 서로 다를 수 있다.

`고속도로 통행료+` 알림 원문은 지출을 놓치지 않기 위한 입력 보조 자료다. 알림을 수집했다는 사실만으로 원장에 자동 등록하지 않는다. 사용자가 금액, 사용일, 본인 사용 또는 청구 사용 여부를 확인하고 등록했을 때만 원장 또는 Claim의 사실이 된다.

`고속도로 통행료+` 알림은 모바일 로컬에 원문과 등록 후보를 보관한다. 날짜·시각은 필수이며 금액을 확인하지 못한 알림은 빈 금액의 `partial` 후보로 남겨 사용자가 직접 채운다. 기존에 원문 로그로만 쌓인 알림은 후보로 소급 변환하지 않는다.

## 모바일 알림의 로컬 후보 경계

우리카드와 통행료 알림 후보 기능은 실사용 입력 보조 경로다. 모바일 설정의 `최근 납치한 알림`에서 출처별 원문과 파싱 결과를 확인한다.

알림 원문과 후보는 모바일 로컬에만 저장한다. Android의 `새 내역 발견!` 알림에서는 통행료 후보도 본인카드 미확인 건수로 합산하지만, 후보 화면에서는 통행료 묶음을 그대로 구분한다. 후보 생성과 알림 표시는 원장, Claim, Family Card, 카드대금, Snapshot에 영향을 주지 않는다. 사용자가 후보를 확인하고 `등록`을 눌러 기존 서버 API가 성공한 시점부터 서버 데이터가 된다. 통행료 후보는 할인 제외로 등록한다.

우리카드 알림의 `할인 적용` 체크 기본값은 알림에 매칭된 카드 정체성의 **거래 사용월** 정책을 따른다. 가족카드 알림이면 등록 대상이 `가족 사용`(Family Card)인지 `본인 사용`(원장)인지와 무관하게 가족카드 정책을 초기값으로 쓴다. 등록 대상은 회계상 귀속을 결정하며 카드 알림의 출처를 바꾸지 않는다. 사용자가 체크를 직접 변경하면 그 후보의 명시적 선택을 대상 전환에도 유지하고 최종 등록 입력으로 전달한다. 온라인 과거월은 서버 월 정책 API로 확인하고 오프라인은 frozen baseline의 서버 정책 설정·기본값을 사용한다. 정책을 알 수 없으면 현재 월로 추정하지 않고 명시적 선택을 요구한다. Claim/Family Card 후보의 사용월과 최초 할인 제외 의도는 생성 요청에 함께 넣는다. 동일 후보 key의 다른 authoritative 입력은 성공 재사용이 아니라 충돌로 거절한다. 서버의 자동 할인 결과는 계속 서버 카드 계산기가 결정한다.

수동 Claim/Family Card 등록의 최초 할인 적용/제외 의도도 패널 생성과 하나의 서버 transaction에서 저장한다. 등록 후 사용자가 별도로 선택하는 할인·실결제 수정은 독립된 수정 operation이다. Offline 알림 등록 identity는 frozen B와 J 전체에서 한 번만 금융 효과를 가질 수 있으며, 예상값은 그 identity나 서버 계산 결과를 대신하지 않는다.

우리카드 파싱 실패·할부 수동처리와 통행료 파싱 실패·금액 미확인 상태는 `알림 파싱 확인 필요` 알림으로 별도 안내한다. 이 확인 알림 역시 모바일 로컬 관측 상태일 뿐 서버 장부의 사실이 아니다.

Android 리스너 재연결 시 알림창에 남은 지원 알림은 다시 관측할 수 있다. 이때 중복 후보를 만들지 않도록 `notificationKey + postTime` 기반 처리 이력과 등록·삭제 상태를 모바일 로컬에 마지막 관측 후 7일, 최대 512건 유지한다. 후보와 원문을 삭제해도 처리 이력의 보관 기한은 독립적으로 적용되며, 이 로컬 안전장치는 서버의 도메인 데이터가 아니다.

---

# 5. 카드대금 (card_payment)

card_payment는 카드사에 실제로 청구될 것으로 예상되는 금액이다.

의미:

> 카드사에 갚아야 할 돈

원장 금액과는 다르다.

예:

사용금액

10,000원

할인

120원

카드대금

9,880원

## 월마감 batch

`card_payment` 화면의 기준은 달력상 직전월이 아니라 월마감 이벤트다.

월마감을 실행하면 해당 사용월의 원장 항목으로 활성 `card_payment_batch`가 생성된다. 결제 화면은 이 활성 batch만 보여준다.

새 월마감이 실행되면 이전 batch는 완료된 임시 작업장으로 보고 삭제한다. 이전 batch의 즉시결제 이벤트, 할인 이벤트, 배분 내역도 함께 삭제된다. 실제 장부 원장과 현금흐름 기록은 남아 있으므로 과거 batch 선택 기능은 두지 않는다.

## 이월 항목

하이패스/통행료처럼 사용일, 매입일, 결제월이 어긋나는 항목은 결제 화면에서 다음 결제월로 이월할 수 있다.

이월된 항목은 원장에서는 다음 달 맨 위에 `[이월] [n월 사용 내역] ...` 형태로 남는다.

이유:

> 이월된 금액은 다음 결제월의 유동성에 영향을 주기 때문이다.

단, 이월된 원장 항목이 생겼다고 해서 즉시 다음 결제 batch에 보이는 것은 아니다. 그 항목이 속한 달을 월마감해야 새 batch에 편입된다.

예:

- 5월 30일 하이패스 사용
- 6월 결제 화면에서 이월 선택
- 6월 원장 맨 위에 `[이월] [5월 사용 내역] ...`로 표시
- 6월 월마감 실행
- 7월 결제 batch에 편입

## 동결 금액

동결 금액은 실제로 보유하고 있지만 현재 잔여 유동성에서 제외해 둔 돈을 관리하는 목록이다.

- 원장이나 월별 소비 기록이 아니다.
- 이번 달 또는 미래 지출처럼 특정 사용 목적이나 귀속 월을 별도로 추적하지 않는다.
- 특정 카드 지출과 어떤 동결 항목이 대응한다고 추정하지 않는다.
- 등록 월이 지나도 자동으로 사라지거나 숨겨지지 않는다.
- 사용자가 개별 항목을 삭제할 때까지 웹과 모바일의 동결 목록에 계속 표시한다.
- 잔여 유동성의 동결자산 총액도 같은 전체 미삭제 목록을 기준으로 계산한다.
- 소비액에 다시 합산하거나 소비 총액에서 임의로 제외하지 않고, 현재 자유롭게 사용할 수 있는 유동성을 평가할 때만 반영한다.

---

# 6. Claim

Claim은 가족에게 회수할 예정인 금액이다.

의미:

> 내가 먼저 부담했지만 나중에 돌려받을 돈

예:

- 내가 가족 식비를 결제
- 내 카드로 먼저 결제
- 나중에 가족에게 청구

---

## Claim의 특징

Claim은 소비가 아니다.

Claim은 원장이 아니다.

Claim은 회수 예정 정보다.

Claim은 사용자가 `일괄 처리 완료` 또는 개별 삭제를 수행하기 전까지 월이 바뀌어도 남아 있어야 한다.

따라서 Claim 조회는 달력상 현재 월로 제한하지 않는다.

---

## Claim 계산 기준

Claim은 실부담액 기준으로 계산한다.

예:

사용금액

10,000원

카드 할인

120원

실부담액

9,880원

Claim

9,880원

---

## Claim이 들어가지 않는 곳

Claim은 다음에 포함되지 않는다.

- 당월 지출 총합
- 소비 통계
- 잔여 유동성

Claim은 제거가 확정되었지만 시점은 미정인 운영 기능이다. 사용자가 생활비와 예외적인 큰 지출까지 가족 지원 없이 자체 소득·자산으로 감당할 수 있는 현실적 경제적 독립 상태가 제거 조건이다. 그전까지 현재 도메인 의미와 데이터를 유지하며, 제거 범위와 Snapshot 전환 순서는 [청구 기능 제거 가이드](claim-removal.md)를 따른다.

---

# 7. 가족카드 (Family Card)

가족카드는 동생이 사용하는 가족카드 내역을 관리하는 기능이다.

제거 자체는 확정되어 있지만 특정 기간이나 날짜를 조건으로 삼지 않는다. 사용자가 생활비뿐 아니라 예외적인 큰 지출도 가족 지원 없이 감당할 수 있는 현실적 경제적 독립 상태가 될 때까지 정상 운영 기능으로 유지한다. 다만 Money Note의 핵심 도메인은 아니다.

---

## 기존 settlement의 의미

기존 코드와 DB에는 `settlement` / `타인정산`이라는 이름이 남아 있었다.

현재 사용 맥락을 확인하면 이는 독립적인 정산 도메인이 아니라 가족카드 사용 내역을 의미했다.

따라서 Money Note에서는 다음과 같이 통일한다.

- `settlement` → `family_card`
- `타인정산` → `가족카드`
- `monthly_panels.panel_type = "settlement"` → `"family_card"`

이전 명칭은 서버 시작 시 정규화 대상이다.

---

## Claim과 가족카드의 차이

Claim:

- 내 카드로 먼저 결제한 뒤 가족에게 청구하는 금액
- 본인회원 카드 할인 정책을 따른다.
- 별도 설정이 없으면 본인회원 카드는 할인 혜택이 있는 달로 본다.
- 공유 청구서로 보여줄 수 있다.

Family Card:

- 가족카드 자체의 사용 내역
- 가족카드 할인 정책을 따로 가진다.
- 별도 설정이 없으면 가족카드는 할인 혜택이 없는 달로 본다.
- 내 소비 통계와 유동성에 직접 반영하지 않는다.

둘 다 회수 예정 금액이며, 내 소비 원장과 분리한다.

둘 다 사용자가 처리 완료 또는 개별 삭제를 수행하기 전까지 월이 바뀌어도 남아 있어야 한다.

따라서 Claim과 Family Card 조회는 달력상 현재 월 필터에 갇히지 않는다.

공유 페이지의 최소 결제 회차는 별도 상태로 저장하지 않는다. 서버는 남아 있는 각 행의 `spent_on` 사용월 다음 달을 결제 회차로 계산하고, 가장 이른 회차를 현재 최소 결제 대상으로 선택한다. 해당 회차의 행이 모두 처리되어 삭제되면 다음 회차가 자동으로 선택된다.

---

## 중요

가족카드 기능은 현재 운영상 필요하므로 정상 기능 수준으로 유지한다.

그러나 장기적으로는 제거 후보 기능이다.

제거는 미래의 가족카드 독립 시점에만 허용된다.

그 전까지는 가족카드 데이터를 임의로 제거하지 않는다.

시스템은 언제든 가족카드 기능을 제거할 수 있도록 설계되어야 한다.

따라서 가족카드는:

* 원장
* 카드대금
* 유동성
* Claim

과 강하게 결합되어서는 안 된다.

---

## 제거 기준

가족카드 기능을 제거하는 시점에는 가족카드 데이터 전체 삭제를 허용한다.

단, 가족카드 데이터를 모두 삭제하더라도 다음 값은 변하면 안 된다.

* ledger_entries
* 당월 지출 총합
* 소비 통계
* 카드대금
* 잔여 유동성
* Claim 계산

이 조건이 만족되지 않는다면 설계가 잘못된 것이다.

---

## 설계 원칙

가족카드는 제거 예정 기능이다.

따라서:

* 핵심 도메인으로 승격하지 않는다.
* 핵심 계산에 침투시키지 않는다.
* 제거 비용을 최소화한다.
* 신규 기능이 가족카드에 의존하지 않도록 한다.

## 제거 가능성 점검

2026-08 카드 정책 모듈화 시점에 가족카드 경계를 다시 점검했다.

- 저장소: `monthly_panels.panel_type = "family_card"` 행만 사용하며 전용 핵심 테이블은 없다.
- 계산: 당월 소비, 카드대금, Claim, 유동성 계산은 가족카드 없이 독립적으로 동작한다.
- 할인: `card_charge` 정책 레지스트리의 `FAMILY` 항목과 가족카드 월 스위치만 제거하면 나머지 세 카드 계산은 영향을 받지 않는다.
- 표현: 가족카드 공유 API, 판단 문구, 웹 feature, 모바일 정산 화면, 설정의 카드 끝 4자리와 응답 타입은 기능 제거 시 함께 삭제해야 한다.
- 백업: 가족카드 행과 비민감 설정은 일반 `monthly_panels`/`app_settings` 데이터로 포함된다. 제거 시 해당 행과 설정 삭제를 허용하며 Snapshot 형식의 핵심 테이블 의미는 바뀌지 않는다.

따라서 현재 구조는 가족카드를 한 디렉터리만 지워 제거할 수 있는 형태는 아니지만, 핵심 원장·카드대금·유동성을 수정하지 않고 경계에 열거된 기능 코드와 데이터만 제거할 수 있다. 신규 공통 모듈이 가족카드 응답이나 화면 타입에 의존해서는 안 된다.

---

# 8. 잔여 유동성 (Remaining Liquidity)

잔여 유동성은 해당 예산 주기에서 이미 다른 용도로 약속된 금액을 제외하고 추가로 사용할 수 있는 금액이다.

의미:

> 현재 예산 주기를 감당할 수 있는가?

---

잔여 유동성은

- 기본 예정 수입
- 카드대금
- 고정지출
- 현재 자산 상태

등을 이용해 계산한다.

---

현재 계산식은 다음과 같다.

```text
remaining_liquidity
= scheduled_income
  + cash_flow_balance
  - card_total
  - active_card_payment_unpaid_total
  - liquidity_fixed_total
  - frozen_asset_total
```

웹·모바일의 `잔여 유동성` 자리에 표시하는 값은 서버가 같은 read transaction에서 계산한 `current_month_spendable`이다. 기존 `remaining_liquidity`는 다음 급여를 선반영한 계산 단계로 API에 남지만, 이미 처리된 현금성 고정지출 템플릿의 다음 발생분을 아직 reserve하지 않는다. 표시용 추가 사용 가능액은 다음과 같다.

```text
current_month_spendable
= remaining_liquidity
  - (fixed_cash_total - pending_fixed_cash_total)
  + early_executed_next_period_fixed_total
```

괄호 안은 확인된 템플릿의 **예정액**이며 실제 처리액이 아니다. 미확인 템플릿 예정액은 이미 `remaining_liquidity`에서 차감되므로 다시 빼지 않는다. 확인된 템플릿은 이번 실제 출금이 현금 잔액에 반영됐지만 다음 한 번의 발생분을 다시 대비해야 한다. 서버가 이 값을 제공하며 웹·모바일은 원장 행으로 재계산하지 않는다. 2026-09-30 특성 반례에서는 기존 계산 2,816원, 확인된 고정지출 예정액 20,000원, 추가 사용 가능액 −17,184원이다. 고정지출 820,000원 전체를 처리한 뒤의 별도 synthetic 반례에서는 기존 계산 1,261,930원, 추가 사용 가능액 441,930원이다. 이는 미래 급여 선반영을 제거한 새 재무 모델이 아니라 현재 모델의 한 주기 고정지출 reserve를 보강한 표시 지표다.

카드 의무는 사용 시점부터 실제 지급까지 정확히 한 번 차감한다. 월마감 전에는 당월 원장의 할인 후 `card_total`이 의무를 나타내고, 월마감으로 원장이 archive로 이동하면 활성 결제 batch의 할인·즉시결제를 반영한 미결제액 `active_card_payment_unpaid_total`이 그 자리를 이어받는다. 즉시결제는 같은 금액만큼 미결제액과 `cash_flow_balance`를 함께 줄이므로 잔여 유동성을 다시 줄이지 않는다. 이월 항목은 당월 원장으로 돌아와 `card_total`에 포함되므로 활성 batch 미결제액에서는 제외한다.

실제 즉시결제 allocation이 일부라도 생긴 원장 행은 일반 원장 삭제로 지우지 않는다. 즉시결제가 만든 음수 현금흐름도 일반 현금흐름 삭제로 지우지 않는다. 결제 이벤트 취소가 allocation과 연결 현금흐름을 함께 되돌리는 authoritative reversal이며, 이 경계를 통해 과거 실제 은행 출금과 카드채무가 서로 다른 상태로 갈라지는 것을 막는다.

결제일 경과 후 사용자가 실제 계좌 잔액을 수동 보정하고 해당 결제월의 `현금흐름 보정 완료`를 확인하면, 활성 batch의 기록상 잔액은 결제 화면에 보존하되 Summary에서는 이미 실제 잔액에 반영된 의무로 보아 다시 차감하지 않는다. `active_card_payment_unpaid_total`은 이 상태 전이용 내부 계산값이며 Summary 응답에 중복 노출하지 않는다.

- `scheduled_income`: DB에 같은 이름으로 저장되는 기본 예정 수입. 현행 pre-funding 모델에서 아직 들어오지 않은 다음 급여를 현재 소비 재원으로 한 번 선반영한다.
- `cash_flow_balance`: Money Note가 추적하는 Active 계좌의 실제 잔액. DB의 같은 이름인 수동 보정값과 서버 기준일 현재까지 발생한 현금흐름 누계의 합
- `liquidity_fixed_total`: 아직 확인되지 않은 현금성 고정지출과 아직 원장 지출로 확인되지 않은 카드 정기결제 예정액

예산 주기는 매월 1일부터 말일까지다. 월마감은 사용자가 해당 주기의 소비를 끝내고 다음 카드대금에 쓸 자금을 실제로 꺼내는 사건이다. 월마감이 성공하면 설정의 `scheduled_income`과 같은 금액의 양수 현금흐름 `급여`를 **월마감 실행일**로 만들고 `is_primary_income=1`로 표시한다. 따라서 생성 즉시 `cash_flow_balance`에 포함된다. 월마감 시점의 금액을 확정하므로 이후 설정 변경은 과거 급여 행을 바꾸지 않는다.

별도 `scheduled_income` 항은 아직 현금흐름으로 확정되지 않은 다음 급여를 한 번 선반영한다. 월마감 실행일에 설정 금액의 급여가 실제 현금흐름으로 확정되면 그 행은 확보된 현금이 되고, 보존된 설정값은 그 이후 받을 다음 급여의 예정액 역할을 한다. 같은 숫자가 두 항에 있어도 서로 다른 예산 주기의 재원을 뜻한다.

`cash_flow_balance`는 아직 출금되지 않은 예정 지출, 미확인 현금성 고정지출, 동결 자금, 미래 급여와 `remaining_liquidity`를 뜻하지 않는다. Active 계좌에 실제로 존재하는 돈과 그중 추가로 사용할 수 있는 돈은 다를 수 있다.

현금성 고정지출은 반복 템플릿이며 미지급 의무다. 템플릿의 `amount_value`는 다음 주기에도 재사용하는 보수적 reserve/upper bound이고, 확인할 때 입력하는 실제 출금액은 이번 주기에 실제 발생한 사실이다. 확인 전에는 template 예정액이 `liquidity_fixed_total`로 `remaining_liquidity`에서 한 번 차감된다. 확인하면 pending obligation을 제거하고 입력한 실제액의 음수 `cash_flows`를 생성해 `cash_flow_balance`를 줄이되, template 예정액은 바꾸지 않는다. 실제액이 예정액보다 작으면 차액이 잔여 유동성으로 돌아오고, 더 크면 초과분만큼 잔여 유동성이 더 줄어든다. 실제액과 예정액이 같을 때만 확인 전후 잔여 유동성이 같다. 이번 주기에 발생하지 않았음을 명시적으로 확정할 수 있도록 실제액 0원도 허용한다. 실제 지급 확인이므로 처리일은 서버 기준 오늘보다 미래일 수 없다. `confirmed_at`만 있고 연결된 현금흐름이 없는 구형·불완전 상태는 확인 완료로 보지 않는다.

표시용 `fixed_cash_total`과 고정지출 총합은 확인 여부와 실제액에 무관한 전체 템플릿 예정액이다. `confirmed_month`는 집행한 **금융 주기**이고 `spent_on`과 연결된 현금흐름의 `occurred_on`은 **실제 송금일**이다. 보통 두 월이 같지만, 말일 월마감 뒤에는 다음 달분을 같은 날 송금할 수 있다. 예를 들어 9월 마감 뒤 9월 30일에 집행한 10월분은 확인 월 `2026-10`, 실제 송금일 `2026-09-30`을 함께 보존한다. 템플릿 시작 월보다 앞선 금융 주기의 확인은 거부한다.

월마감은 달력을 앞당기지 않는다. 현재 달 마감은 calendar library로 계산한 실제 마지막 날에만 명시적 확인 후 가능하고, 이미 지난 미마감 달의 처리 가능성은 유지한다. 월마감은 예정 수입을 실제 실행일의 현금흐름으로 한 번 실현하고, **현금성 고정지출만** 익월분 조기 집행 가능성을 연다. 카드 정기결제는 달력 기준으로 남으며 마감한 같은 달에는 재확인할 수 없다. 웹·모바일은 서버의 `can_confirm_fixed`/`fixed_execution_month`와 `card_recurring_confirmation_available`을 사용한다.

조기 집행 전 익월 고정지출은 reserve 한 번, 조기 집행 후에는 실제 출금 한 번으로 반영한다. 위 식의 `early_executed_next_period_fixed_total`은 아직 실제 달력이 확인 월에 진입하지 않은 조기 처리 템플릿의 **예정액**이다. 다음 발생분 reserve를 같은 날 미리 붙여 이중 차감하지 않는다. 실제 10월 1일에는 확인 상태·9월 송금 기록을 유지한 채 11월 발생분 reserve를 정상적으로 대비한다. 10월분을 다시 출금하거나 미확인으로 되돌리지 않는다.

월마감은 마감 대상 월과 같은 확인 상태만 다음 주기용 미확인 상태로 돌리고 이미 기록한 현금흐름은 보존한다. 따라서 밀린 과거 월마감이 이후 주기에 이미 확인한 템플릿을 되돌리지 않는다. 연결된 현금흐름을 기존 확인 취소 경로로 삭제하면 템플릿도 원래 reserve 금액의 미확인 상태로 돌아가므로, 잘못 입력한 실제액은 이 취소 후 다시 확인한다. 조기 처리의 취소도 같은 transaction에서 이 의미를 보존한다.

기존 v7 Snapshot은 확인 월·실제 송금일·연결 ID·`last_closed_month`를 이미 표현하므로 형식을 올리지 않는다. 다른 확인 월을 가진 조기 처리는 **실제 말일 + 해당 실제 월의 완료된 월마감 + 바로 다음 확인 월**이 증명될 때만 복원한다. v6의 누락된 확인 월은 기존대로 실제 처리일의 월로 정규화하며 새 조기 처리 의미를 추측하지 않는다. 월마감은 온라인 전용이다. 기존 Offline fixed journal은 서버가 제공한 baseline 처리 가능성을 사용하며 원래 입력만 replay하고, 로컬 예상값은 서버 권위 입력이 아니다.

Offline의 조기 처리 예상값은 서버가 제공한 확인 월/처리 대상 월을 보존한다. 기기 달력이 그 월에 도달하면 다음 반복분 reserve를 예상 표시에 반영하되 baseline의 서버 기준월과 eligibility를 앞당기거나 journal에 파생 금액을 저장하지 않는다. 이미 baseline에서 확정된 조기 처리와 아직 journal에 있는 조기 처리 모두 같은 원칙을 따른다. 실제 서버 상태는 정상 동기화 또는 기존 reconciliation 절차로만 확정된다.

`fixed_cash_processed_total`은 확인된 현금성 고정지출 템플릿에 연결된 현금흐름의 실제 출금액 합계로 서버가 계산한다. 웹·모바일 고정지출 화면은 `실제 처리액 / 총 전체 예정액`을 표시하며, 이 표시용 처리액을 잔여 유동성에서 다시 차감하지 않는다.

카드 정기결제의 template `amount_value`도 다음 주기의 예정 원금이다. 확인할 때 사용자가 이번 주기의 실제 원금을 확정하며, 서버는 그 실제 원금에 기존 카드 할인 정책을 적용해 할인액과 실결제 예상액을 계산하고 생성된 원장 expense에 저장한다. template 예정 원금과 `due_day`는 변경하지 않는다. 잘못 확인한 경우 월마감 전에 생성된 원장 expense를 삭제하면 template이 미확인 상태로 복귀하고 다시 확인할 수 있다.

월마감 대상 주기에 미확인 현금성 고정지출 또는 카드 정기결제가 있으면 서버는 정상 요청을 거부하고 항목 목록을 제공한다. Web과 Mobile은 목록을 보여준 뒤 사용자가 `그래도 월마감`을 명시적으로 선택한 경우에만 override를 보낸다. 이 경고는 실제 미발생이나 청구 지연을 허용하기 위한 soft guard이며 hard block이 아니다. 검사와 override 재확인은 기존 월마감 write transaction 안에서 수행한다.

예산 주기의 존재는 카드 지출 행 존재 여부로 결정하지 않는다. `last_closed_month`가 있으면 그 다음 달이 마감 대상이며, 원장 지출이 0건인 빈 달도 급여 확정, 반복 템플릿 reset, 결제 batch 생성과 `last_closed_month` 전진을 수행한다. 같은 target 재실행은 빈 달에서도 중복 급여나 batch를 만들지 않는다.

`이달 기준 수입` 표시가 있는 현금흐름 입금 합계는 현재 카드 결제 압박 Judgment의 기준 수입이다. 월마감이 만든 `급여`도 이 표식을 가진다. 급여 발생월은 월마감 실행일의 달이므로 말일 마감 뒤 다음 달 결제 batch에는 같은 달 기준 수입이 없을 수 있으며, 이 경우 Judgment는 `scheduled_income`을 fallback으로 사용한다. 이 기준의 미래 변경은 [미래 재무 건전화 전환](future-financial-health-transition.md)에서 결정한다.

다음 급여를 미리 담보로 쓰지 않게 되는 미래에는 월 주기와 실제 급여 현금흐름은 유지하고 계산식에서 별도 `scheduled_income` 선반영만 제거한다. 전환 조건과 Judgment 후속 결정은 [미래 재무 건전화 전환](future-financial-health-transition.md)에 기록한다.

---

중요:

Claim과 가족카드는 직접 반영하지 않는다.

---

# 9. 소비 통계

소비 통계는

> 내가 무엇에 돈을 사용했는가

를 분석하기 위한 기능이다.

---

포함:

- 실제 소비

제외:

- Claim
- 가족카드
- 회수 예정 금액

---

## 정기결제 확인 identity와 금융 응답 경계

- 생성 지출은 `source_planned_entry_id`와 함께 기존 `confirmed_month`/`confirmed_at` 컬럼에 원본 확인 epoch를 보존한다. 제목·금액·발생일 수정은 epoch를 바꾸지 않는다. 취소는 source ID와 확인 월·시각이 모두 일치하는 확인만 같은 transaction에서 해제한다. 이전 생성 지출을 삭제해도 새 확인을 해제하지 않는다. 월마감 archive에도 epoch를 보존하며, 수정된 발생월의 마감으로 archive에 옮겨진 활성 생성 지출도 같은 identity로 취소한다.
- 확인 목록도 source ID와 확인 epoch로 실제 생성 지출을 조회한다. 원래 5,000원인 지출을 다른 발생월·7,000원으로 수정해도 원본 확인의 projection은 실제 연결된 7,000원을 보여준다. archive의 발생일 NULL도 기존 nullable 계약대로 허용하며 실제 지출 연결을 끊지 않는다(current 지출의 NULL 발생일 PATCH는 계속 거부). actual이 없거나 유일하지 않으면 오류로 중단하며 template 금액으로 숨기지 않는다. current/archive 위치와 mutable 발생일·제목·사용처·내역은 소유 selector가 아니다.
- 현재 Snapshot의 활성 정기결제 확인은 원본 planned ID와 완전한 확인 epoch(`confirmed_month`, `confirmed_at`)가 일치하는 생성 expense **정확히 한 건**을 소유해야 한다. 생성 지출 누락, epoch 전체/부분 누락, source 누락·불일치, 중복 소유를 거부한다. 제목·장소·원금·발생일은 수정 가능한 사실이지 소유 identity가 아니다. Fixed/recurring timestamp의 offset hour는 0~23, minute는 0~59여야 하며 실제 날짜·시각도 파싱 가능해야 한다. 확인 clock time을 발생일과 같도록 강제하지 않는다.
- 원본의 확인 월/시각도 all-or-nothing이다. 부분 epoch는 Snapshot 복원과 runtime 수정·취소·재확인에서 거부한다. 마감되지 않은 생성 epoch가 있는데 원본 확인이 모두 없는 상태도 정상 관계가 아니다. 월마감으로 이미 종료한 epoch의 생성 지출은 보존할 수 있다. 이 구분에 새 값을 추측해 넣지 않는다.
- v4~v6 Snapshot은 원문 manifest 검증 뒤 증명 가능한 source/epoch만 정규화하고 위 canonical 소유 계약을 검사한다. 증명되지 않는 활성 확인은 복원 전에 거부한다. 현재 exporter의 v7은 manifest에 결합한 `recurring_ownership_version=1`을 포함하며 누락된 epoch를 보정하지 않는다. 표식이 없는 역사적 v7은 아래 증명 규칙으로만 정규화한다. 현재 export도 같은 소유 계약을 검사하며 runtime 확인 조회·수정·취소·재확인은 불완전한 관계를 fail closed한다. 이미 종료한 epoch의 지출은 원본의 새 확인과 구별해 보존한다. 정상 template 삭제는 실제 지출을 남기되 source FK와 epoch 메타데이터를 함께 해제한다. Snapshot 형식은 v7이며 DB version 4에서 identity checkpoint를 한 번 실행한다. 실제 지출을 추측 생성하지 않는다.
- 이전 배포 코드의 explicit recurring 확인은 생성 expense에 source ID와 고유 payment key를 저장했지만 생성 epoch는 저장하지 않았다. DB version 3 이하의 startup checkpoint와 표식 없는 역사적 v7 import에서만 `recurring_compatibility.py`가 빠진 양쪽 child epoch를 채운다. planned source 자체의 epoch를 새로 만들지 않는다. source ID·source 생성 시각·payment key가 동일하고 원래 INSERT/확인 UPDATE 시각의 순방향 0~1초 구간에 명시적으로 연결된 후보가 정확히 하나인 경우만 그 source epoch를 증거로 사용한다. 제목·장소·내역·원금·발생일·current/archive 위치는 증거가 아니다. 더 긴 지연이나 재복원으로 생성 시각이 바뀐 retired expense는 같은 stable identity와 원래 epoch를 증명하는 검증된 `snapshot-backups/`의 v7 recovery 문서가 필요하다. 상충 증거·source 재사용·복수 후보·source 없는 manual lookalike는 거부하며 가장 가까운 후보를 선택하지 않는다.
- 이 checkpoint는 모든 증명과 canonical 검증을 마친 뒤 하나의 transaction에서 생성 expense의 `confirmed_month`/`confirmed_at`만 채우고 version 4를 기록한다. 금액·할인·실제 행·ID를 바꾸지 않으며 기존 revision trigger의 증가만 발생한다. 실패/중단 시 전체 rollback하고, version 4 startup은 검증만 수행해 재보정하지 않는다. Summary·export는 strict 상태만 읽는다. 역사적 v7은 원문 manifest와 금액 검증 후 임시 표현에서 정규화하며 원본 recovery 파일은 재작성하지 않는다. 새 canonical v7의 표식도 manifest로 보호되므로 제거·변경한 원문은 재해시 없이 승인하지 않는다. 증거 없는 오래된 파일의 자동 수선은 제공하지 않는다.
- 금융 변경 API와 할인 월 정책/교통 프로필 변경은 필수 status 계산·presenter·response model 검증·최종 JSON 응답 bytes 준비를 commit 전에 끝낸다. HTTP router가 하나의 기존 business transaction connection을 command와 필수 response 계산에 빌려주며 중첩 BEGIN/commit을 만들지 않는다. 준비된 Response를 반환해 FastAPI의 handler 종료 후 재직렬화를 우회한다. 정책 status도 같은 connection에서 새 uncommitted 값을 본다. 커밋 전 변환 오류는 금융 행·정책·등록 identity·revision을 함께 rollback한다. socket 전송은 transaction 밖이고 유실은 ambiguous outcome이다. 기존 idempotency가 있는 작업만 동일 identity로 재확인하며 일반 생성에 새 exactly-once 보장을 추가하지 않는다.
- 모바일 submit 완료는 서버 저장뿐 아니라 coherent refresh, baseline durable publication, 화면 설치까지 요구한다. 서버 저장 후 재구성 실패는 `serverCommittedRebuildPending`으로 보존해 재전송과 stale Offline epoch를 막고 read-only rebuild로 복구한다. 요청 결과를 모르는 `outcomeUnknown`은 별개이며 새 기준 데이터를 읽은 것만으로 그 요청의 완료를 추측하지 않는다.

# 10. 카드번호 마지막 4자리

Money Note는 카드사 알림 자동입력을 고려한다.

따라서 카드번호 마지막 4자리를 설정으로 관리한다.

필수 설정:

- owner_card_last4
- family_card_last4

의미:

- owner_card_last4: 본인회원 카드 식별값
- family_card_last4: 가족카드 식별값

---

# 11. Snapshot 백업

## 영속 금융 관계 계약

- 카드 batch item의 `entry_id`와 `entry_payment_key`는 같은 원장 행을 식별한다. 한 원장 key는 하나의 batch에만 속한다(완료 batch 포함). 하나의 결제는 여러 원장에 배분할 수 있고 한 원장은 여러 별도 결제로 나눠 낼 수 있지만, `(payment_event_id, entry_payment_key)` 배분은 한 건이며 이벤트의 batch 소유권과 일치해야 한다. 실제 출금 cash flow는 두 결제 이벤트가 공유하지 않는다. 과거 `batch_id=NULL` 이벤트는 새 batch에 추측 결합하지 않는다.
- batch에 소유된 원장 지출도 유효한 0 이상 정수 원금을 필수로 갖는다. archive 위치라는 이유로 PATCH에서 NULL 원금을 허용하거나 미지급액에서 조용히 제외하지 않는다. 관계 없는 과거 nullable 행 전체를 NOT NULL로 바꾸는 계약은 아니다.
- 명시적 recurring 생성 지출은 `source_planned_entry_id + confirmed_month + confirmed_at`으로 소유권을 증명하고 활성 확인은 정확히 한 생성 지출을 소유한다. 생성 지출의 `amount_value`는 0 이상 정수 원 단위로 반드시 존재해야 한다. 0원 실제 확인은 지원하지만 NULL/누락은 0원으로 해석하지 않는다. 선택적인 할인/override 금액의 NULL은 기존 정책 의미를 유지한다. 지원 historical REAL affinity의 `5000.0`도 정수 원금이며 소수 원금은 유효하지 않다.
- current/archive는 보관 위치이지 확인 identity가 아니다. 종료된 예전 epoch의 지출이 current에 있고 새로운 활성 epoch 지출이 archive에 있어도 source/epoch가 유일하면 정상이다. 같은 논리 원장(payment key)이나 같은 소유 epoch가 양쪽에 중복되면 거부한다. 수정된 실제 날짜·금액·제목으로 소유권을 다시 판단하지 않으며, 월마감의 미확인 경고도 명시적 source/epoch를 사용한다.
- 같은 canonical 계약을 금융 읽기, 쓰기 commit 전, export, legacy 정규화 후 restore, mandatory recovery 및 reconciliation 검증 경계에서 사용한다. 손상 관계는 fail closed하며 중복 삭제·소유 선택·원금 추측 복구를 하지 않는다. Snapshot v4~v7은 유지한다. DB version 4의 별도 identity checkpoint는 아래 역사적 호환 규칙만 수행한다.

서버 DB는 Money Note의 단일 원본이다.

Snapshot은 원본 DB를 대체하는 별도 저장소가 아니라, 장부 운용 데이터 전체와 비민감 운영 설정을 JSON 파일로 잠시 옮겨 담는 백업/복원 형식이다.

새 Snapshot 형식은 `schema_version = 7`이다. v7은 확인된 현금성 고정지출의 확인 월, 정기결제 원본과 생성 지출의 명시적 관계, 카드 결제 idempotency 정보를 추가로 보존한다. v6의 현금흐름 연결과 v4~v6의 nullable 신규 필드 누락을 계속 허용하며, 유동성 설정·라벨 key가 과거 이름인 v4 Snapshot도 복원한다. 파일 형식 v3 이하는 지원하지 않는다.

정기지출 실제액 확정은 Snapshot schema를 늘리지 않는다. 현금성 고정지출 reserve는 `monthly_panels.amount_value`, 실제 출금은 연결된 `cash_flows.amount_value`, 카드 정기결제 예정 원금은 planned 행, 실제 원금은 `source_planned_entry_id`로 연결된 expense 행에 이미 저장된다. 따라서 Snapshot v7의 기존 테이블·관계 보존만으로 template과 이번 실제액을 모두 export/restore하며 API의 `confirmed_*` 투영값을 중복 저장하지 않는다.

Snapshot은 canonical JSON 기준 SHA-256 manifest를 포함한다.

Manifest 원칙:

- `manifest` 자기 자신은 hash 대상에서 제외한다.
- `data` 전체 hash를 기록한다.
- 각 테이블의 컬럼 목록, row count, 테이블별 hash를 기록한다.
- `schema_version`, `exported_at`, `range`, `card_charge_policy`, `data`를 합친 전체 content hash를 기록한다.
- restore 시 manifest가 재계산 결과와 다르면 복원하지 않는다.

`card_charge_policy`는 Snapshot 생성 당시의 카드 실결제액 계산 전제를 기록한다.

- 카드별 사용월 정책 binding과 `policy_id`
- 정책 종류와 할인율 같은 계산 매개변수
- 교통·통행 분류 키워드, 판정 방식과 우선순위
- 교통카드 프로필 선택기의 모드, 기본값과 본인카드 위임 의미
- 서버 기준월과 Snapshot 데이터가 포괄하는 마지막 월 `covered_through`

이 명세는 실행 가능한 설정이 아니라 감사와 복원 검증 자료다. 새 Snapshot을 복원할 때 당시 정책이 현재 서버에 그대로 남아 있지 않으면, 서버는 과거 금액을 다른 정책으로 조용히 재계산하지 않고 복원을 차단한다. Snapshot 생성월 이후부터 적용되는 정책 binding을 현재 서버가 추가로 가진 경우에는 과거 계산을 바꾸지 않으므로 복원을 허용한다.

하위호환 원칙:

- restore는 먼저 snapshot 원문 기준으로 manifest를 검증한다.
- 버전 4, 5, 6, 7은 manifest 검증 후 당시 `card_charge_policy`가 현재 서버에 보존되어 있는지 확인한다. 생성월 이후의 새 binding 추가만 허용한다.
- v4의 `base_next_month_liquidity`, `liquidity_status`, `summary_next_month_liquidity_label`, `summary_liquidity_status_label`은 원문 manifest 검증이 끝난 뒤 각각 현재 표준 key로 정규화한다.
- Snapshot에 같은 의미의 새 key와 기존 key가 동시에 있고 값이 다르면 복원을 중단한다.
- 파일 형식 v3 이하는 복원하지 않는다.
- 장기 지원 대상은 현행 파일/정책 명세다. 직전 내부 명세 호환은 새 형식 Snapshot을 실제로 확보할 때까지만 전환 경로로 유지하고, 확보 후 코드와 테스트에서 제거한다.
- 검증을 통과한 뒤 현재 서버 스키마에 없는 컬럼은 무시한다.
- 현재 서버 스키마에 새로 생긴 컬럼이 snapshot에 없으면 의미 보존 규칙을 먼저 적용하고, 호환 기본값이 정의된 나머지 필드만 DB 기본값 또는 `NULL` 정책에 맡긴다. v6에서 확인된 현금성 고정지출은 연결된 현금흐름과 유효한 `spent_on`이 있을 때 확인 월을 복원한다. 누락된 날짜 등 의미를 결정할 수 없는 상태는 restore 전에 거부한다. v7의 확인 월은 다시 추론하지 않는다.
- 연결된 고정지출 확인은 현금흐름 한 건에 원본 한 건만 대응하며, 처리일과 현금흐름 발생일이 같고 해당 현금흐름은 다른 카드 결제나 급여에 속하지 않아야 한다. 실제 출금액은 template reserve와 다를 수 있다. 모순된 관계는 임시 DB dry-run에서 복원을 거부하고 원래 서버 상태를 보존한다.
- v4~v6 카드 정기결제 Snapshot에는 생성 지출의 `source_planned_entry_id`가 없다. manifest 검증 후, 원본 확인 시각과 변경되지 않은 지출 행 및 월내 유일성이 일치할 때만 복원 경계에서 `source_planned_entry_id`를 영속화한다. 같은 확인 시각에 생성된 지출이 여럿이면 자동 결합하지 않는다. 기존 source 없는 행의 수정은 수정 **전**에 같은 증거로 결합한다. 삭제 시점의 제목·장소·금액 같은 mutable 필드로 관계를 새로 추측하지 않는다. 삭제는 영속화된 source와 원본 확인을 **한 금융 transaction**에서 함께 취소하며, 관계가 불명확하면 삭제 전에 거부한다. 과거 버전에서 이미 수정돼 원래 필드가 사라진 미결합 행도 생성 시각상 확인 관계가 가능하면 파괴적 변경을 거부하고 수동 복구를 요구한다. v7의 명시적 source가 있는 원본은 legacy 추론 후보가 아니다.
- 복원 순서는 원문 검증 → 버전별 legacy 정규화 → canonical 정기결제 소유 검증 → 임시 DB dry-run → mandatory recovery backup/transactional 교체다. 새 v7은 생성 expense와 source 양쪽의 확인 epoch를 반드시 보존한다. 표식 없는 역사적 v7의 명시적 source 연결은 증명 가능한 epoch만 임시 표현에 채운 뒤 동일 canonical 검증을 통과해야 한다. 부분 epoch, source/child 부재 및 모호한 소유권은 거부한다. 불명확한 legacy 활성 관계도 정규화 후 검증을 통과할 수 없으며 목적지 DB는 변경하지 않는다.
- fixed 확인의 `confirmed_at`은 실제 달력 날짜와 시각으로 파싱 가능해야 한다. 비어 있거나 불가능한 timestamp는 manifest가 맞아도 복원을 거부하지만, 확인 시각의 날짜를 지출 발생일과 동일하도록 강제하지 않는다. v6/v7에서 확인 시각 또는 확인 월만 있고 cash-flow 관계가 없는 고정지출은 정상 확인으로 추측하지 않고 복원을 거부한다.
- `NOT NULL`인데 기본값이 없는 필수 컬럼이 누락된 경우에는 dry-run restore 단계에서 실패해야 한다.
- 알 수 없는 필드가 있다는 이유만으로 백업 파일을 손상으로 보지 않는다. 단, manifest가 그 알 수 없는 필드까지 포함한 원문과 일치해야 한다.
- 민감 설정, 필수 테이블 누락, 외래키 오류, manifest 불일치는 계속 복원 차단 사유다.
- v7의 authoritative 금액과 금액 설정은 lossless 정수/safe-integer 제품 범위 검증 뒤 정규화한다. `5000`, `5000.0`과 기존에 지원한 동일 값의 숫자 문자열은 허용하지만 `-0.5`, `5000.5`, non-finite, 잘못된 문자열 및 `abs(value)>2^53−1`은 거부한다. nullable 금액은 해당 관계의 기존 계약에 따라 판단하며 NULL을 0으로 보강하지 않는다.
- JSON 파일/HTTP Snapshot/baseline 원문 숫자도 검사한다. `-1e-400` 또는 `5000.00000000000001`이 JSON decoder에서 0/정수로 변해도 승인하지 않는다. 일반 금융 command 및 Offline journal의 accepted 금액 입력도 같은 raw-token 검증과 기존 integer-money model 검증을 통과해야 한다. body·manifest hash·operation/retry identity를 재작성하지 않는다.
- v4~v6의 문서화된 REAL/소수 금액 절삭 호환은 제품 범위 안의 해당 버전에만 남긴다. v7은 이 경로로 들어가지 않는다. 범위 밖 legacy 값도 거부하며 과거의 소수/REAL 표현에 정확한 원본 정밀도를 사후 보장하지 않는다. export는 malformed runtime 금액을 정상 파일로 내보내지 않는다. 일반 정수형 REAL의 JSON shape/fingerprint를 유지한다. Snapshot version·금융 계산식·reconciliation protocol을 바꾸지 않는다.

Snapshot에 포함하는 것:

- 전체 `ledger_entries`
- 전체 `monthly_panels`
- 전체 `cash_flows`
- 전체 `card_payment_batches`
- 전체 `card_payment_batch_items`
- 전체 `card_payment_events`
- 전체 `card_payment_allocations`
- 전체 `card_payment_deferrals`
- 비민감 운영 `app_settings`
- `app_labels`
- 카드 할인 정책 검증 명세 `card_charge_policy`

Claim과 Family Card는 원장이 아니라 회수 예정 정보다.

실제 운영에서는 가족카드 사용액이나 집안 생활비를 받은 뒤 처리가 끝난 항목을 삭제하며 관리한다.

월이 바뀌었다는 이유만으로 Claim 또는 Family Card 항목을 숨기거나 삭제하지 않는다.

따라서 Snapshot은 Claim과 Family Card뿐 아니라 명시적 제외 대상을 뺀 장부 운용 데이터 전체를 백업한다.

Snapshot에 포함하지 않는 것:

- `users`
- `auth_sessions`
- `share_sessions`
- `audit_logs`
- 비밀번호, 비밀번호 해시, 세션 토큰
- 공유 PIN 해시

Snapshot restore는 위험 작업이다.

복원 시 장부 운용 데이터는 snapshot 내용으로 교체되며, 현재 계정 비밀번호를 다시 확인해야 한다.

사용자 계정, 본체 로그인 세션, 가족 공유 세션, 관리 로그는 snapshot restore 대상이 아니다.

Restore 안전 원칙:

- export는 하나의 SQLite read transaction에서 모든 테이블을 읽어 하나의 commit 시점만 담는다.
- 운영 DB를 수정하기 전에 snapshot 구조와 manifest를 검증한다.
- 운영 DB를 수정하기 전에 동일한 삽입 경로로 임시 DB dry-run restore를 수행한다.
- dry-run에서 외래키 오류가 발생하면 운영 DB를 건드리지 않는다.
- 실제 restore, reset, 월마감과 정산 일괄 완료는 write transaction을 먼저 확보한다. 같은 transaction의 현재 운영 DB를 `pre_restore` snapshot으로 반드시 저장한 뒤 위험 변경을 수행해, backup 이후 다른 write가 끼어들었다가 삭제되는 경로를 막는다.
- `pre_restore` 파일 생성, JSON parse, manifest 검증 중 하나라도 실패하면 restore를 중단한다.
- 실제 restore 도중 예외가 발생하면 트랜잭션 rollback으로 기존 운영 DB를 보존한다.
- `pre_restore`는 서버의 DB 디렉터리 아래 `snapshot-backups/`에 저장한다.
- 사용자는 설정 모달 또는 관리자 API로 `pre_restore` 목록 조회, 삭제, 되돌리기를 수행할 수 있어야 한다.
- `pre_restore` 되돌리기도 일반 restore와 동일한 비밀번호 확인, manifest 검증, dry-run, 새 `pre_restore` 생성 절차를 거친다.
- `pre_restore` 파일 접근은 정해진 filename 형식만 허용하며, `snapshot-backups/` 밖의 파일은 절대 읽지 않는다.

모바일 앱은 실행 시와 백그라운드에서 포그라운드로 복귀할 때 서버에서 전체 snapshot을 내려받아 앱 전용 저장소에 새 파일로 보관한다.

브라우저 웹앱은 로컬 파일시스템을 안정적으로 제어할 수 없으므로 자동 누적 백업을 구현하지 않는다.

모바일 앱은 기존 파일을 덮어쓰지 않고 최근 30개 snapshot을 유지한다. 30개를 넘으면 가장 오래된 파일부터 삭제한다.

모바일 snapshot은 자동 복원하지 않는다. 사용자가 특정 파일을 명시적으로 선택하고 비밀번호를 다시 확인한 경우에만 서버 restore API를 호출한다.

새 snapshot은 서버가 생성한 manifest를 포함한 단일 JSON 파일이며, 복원 시 서버가 JSON 구조, `schema_version`, manifest, 카드 할인 정책 일치 여부와 dry-run을 다시 검증한다. 형식상 정상인 파일의 논리적 누락은 hash만으로 검출할 수 없으므로 서버의 mandatory `pre_restore`가 마지막 복구 지점이다.

---

# 12. 문서 우선 원칙

Money Note를 수정할 때는 다음 순서를 따른다.

1. domain-model.md 확인
2. 현재 코드 확인
3. 구현 수정

도메인 모델을 코드에 맞추지 않는다.

코드를 도메인 모델에 맞춘다.

---

# 13. 미래 방향

Money Note의 핵심은 다음 네 가지다.

- ledger_entries
- claim
- card_payment
- liquidity

이 네 가지는 장기적으로 유지된다.

반면 가족카드는 과도기적 기능이며, 장기적으로 제거될 예정이다.
리팩토링 시 가족카드는 핵심 기능으로 취급하지 않는다.
오히려 제거가 쉽도록 유지하는 것을 목표로 한다.

리팩토링과 기능 추가는 이 원칙을 해치지 않는 범위에서 수행한다.

과거 월마감은 archive 행을 INSERT/delete로 복사해 행 ID와 생성 시각을 새로 부여했다. Archive 복사 시각이 다음 확인과 같은 초여도, 검증된 stable key/source evidence가 해당 행의 별도 마감 epoch를 유일하게 증명한 경우에만 새 확인의 경쟁 후보에서 제외한다. 미증명·상충 후보를 임의로 제외하거나 가장 가까운 행을 선택하지 않는다.

# 미래 재무 건전화 전환

이 문서는 사용자가 다음 달 급여를 담보로 현재 신용카드를 쓰지 않게 되는 시점에 필요한 후속 변경을 기록한다. 현재 계산이나 Judgment를 자동으로 바꾸는 지시가 아니다.

## 현재 확정된 운용

- 예산 주기는 달력 월과 같다. 시작일은 매월 1일이고 종료일은 말일이다.
- 설정의 `scheduled_income`은 매월 들어올 실제 급여의 기본 금액이다.
- 월마감이 성공하면 닫힌 달의 다음 달 1일자로 `급여` 양수 `cash_flows` 행을 한 건 생성하고 `is_primary_income=1`로 표시한다.
- 월마감 시점의 설정 금액을 기록하므로 이후 기본 예정 수입을 바꾸어도 이미 기록된 급여는 바뀌지 않는다.
- Summary의 `cash_flow_balance`는 수동 보정값과 전체 기간 현금흐름 누계다. 따라서 월마감으로 확정된 급여는 이후 잔여 유동성에 계속 남는다.
- 현재 Summary는 이 누계와 별도로 `scheduled_income`을 한 번 더 더한다. 이 항은 아직 현금흐름으로 확정되지 않은 다음 급여를 현재 카드 사용의 재원으로 선반영한다.

```text
현재 remaining_liquidity
= 다음 급여 예정액(scheduled_income)
  + 누적 현금흐름(cash_flow_balance)
  - card_total
  - liquidity_fixed_total
  - interest_expense
  - frozen_asset_total
```

월마감이 만든 `급여`는 실제 현금흐름이므로 Snapshot, pre_restore, 초기화, 현금흐름 조회와 삭제의 기존 규칙을 그대로 따른다. 별도 누적 설정이나 DB 컬럼은 두지 않는다.

## 미래 전환 조건

다음 급여를 미리 담보로 잡지 않고, 이미 확보된 현금 범위 안에서만 카드를 사용하기 시작하면 `scheduled_income`의 직접 선반영을 잔여 유동성 계산에서 제거한다.

전환 후 후보 계산:

```text
건전화 이후 remaining_liquidity
= cash_flow_balance
  - card_total
  - liquidity_fixed_total
  - interest_expense
  - frozen_asset_total
```

이때도 다음은 바꾸지 않는다.

- 달력 월 예산 주기
- 월마감이 `급여` 실제 입금을 생성하는 상태 전이
- 전체 기간 실제 현금흐름 누계
- 현금성 정기지출의 미확인 의무 → 실제 출금 전환
- Claim과 Family Card를 유동성에 직접 포함하지 않는 정책

즉 미래 변경의 핵심은 “월별 현금흐름만 다시 계산”이 아니라, 아직 들어오지 않은 다음 급여를 직접 더하는 `scheduled_income` 항을 제거하는 것이다.

## Judgment에서 결정할 것

현재 본인 앱 Judgment는 `budget`, `credit`, `payment` 세 축을 반환한다. 건전화 전환 전에 다음을 결정한다.

1. `payment`가 계속 해당 결제월의 `이달 기준 수입`을 분모로 볼지, 이미 확보된 잔여 유동성으로 결제 가능 여부를 볼지 결정한다.
2. `remaining_liquidity`에는 카드대금이 이미 차감되어 있으므로 남은 결제액을 같은 값과 단순 비율로 다시 비교해 이중 평가하지 않는다.
3. 잔여 유동성 0원, 음수, 결제일까지 14일·5일·2일·당일·연체 상태의 등급을 정한다.
4. `budget`과 `payment`가 같은 부족 상태를 중복 경고할지 역할을 분리한다.
5. 실제 급여가 설정 금액과 달랐을 때 차이를 Judgment가 지적할지 결정한다.
6. Claim 제거와 향후 Family Card 제거가 핵심 판단을 바꾸지 않도록 feature 경계를 재확인한다.

현행 입력값과 분기 순서는 [Judgment 문구 관리](judgment-messages.md)의 `현행 Judgment 데이터 흐름`을 기준으로 한다. 정책을 결정한 뒤 입력 feature와 등급 경계를 테스트로 먼저 고정하고 문구 pool을 수정한다.

## 전환 전 검증

- 실제 Snapshot 사본으로 전환 전후 잔여 유동성을 비교한다.
- 월마감 한 번당 `급여`가 정확히 한 건만 생성되는지 확인한다.
- 월마감 실패 시 원장 이동, 급여, 결제 batch가 모두 rollback되는지 확인한다.
- 수동으로 같은 급여를 중복 입력하지 않는 운영 규칙을 확인한다.
- 즉시결제 현금 유출과 남은 카드대금이 판단에서 이중 차감되지 않는지 확인한다.
- 웹과 모바일이 서버 Summary와 Judgment를 그대로 표시하는지 확인한다.

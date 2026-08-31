# 미래 재무 건전화 전환

이 문서는 사용자가 다음 달 급여를 담보로 현재 신용카드를 쓰지 않게 되는 시점에 필요한 후속 변경을 기록한다. 현재 계산이나 Judgment를 자동으로 바꾸는 지시가 아니다.

## 현재 확정된 운용

- 예산 주기는 달력 월과 같다. 시작일은 매월 1일이고 종료일은 말일이다.
- 설정의 `scheduled_income`은 매월 들어올 실제 급여의 기본 금액이다.
- 월마감이 성공하면 월마감 실행일로 `급여` 양수 `cash_flows` 행을 한 건 생성하고 `is_primary_income=1`로 표시한다. 이는 사용자가 장부 정리와 함께 다음 카드대금에 쓸 자금을 실제로 꺼낸 사건이다.
- 월마감 시점의 설정 금액을 기록하므로 이후 기본 예정 수입을 바꾸어도 이미 기록된 급여는 바뀌지 않는다.
- Summary의 `cash_flow_balance`는 Money Note가 추적하는 Active 계좌의 실제 잔액이다. 정확히는 수동 보정값과 `occurred_on <= app_today()`인 전체 기간 현금흐름 누계다.
- 월마감 급여는 실행일에 생성되어 즉시 `cash_flow_balance`에 들어가고 이후 누계에 남는다. 사용자가 별도로 입력한 미래 날짜 현금흐름은 여전히 발생일 전 잔액에서 제외한다.
- 현재 Summary는 이 누계와 별도로 `scheduled_income`을 한 번 더 더한다. 이 항은 아직 현금흐름으로 확정되지 않은 다음 급여를 현재 카드 사용의 재원으로 선반영한다.

```text
현재 remaining_liquidity
= 다음 급여 예정액(scheduled_income)
  + 누적 현금흐름(cash_flow_balance)
  - card_total
  - liquidity_fixed_total
  - frozen_asset_total
```

월마감이 만든 `급여`는 실행일에 발생한 실제 현금흐름 행이므로 Snapshot, pre_restore, 초기화, 현금흐름 조회와 삭제의 기존 규칙을 그대로 따른다. 생성 즉시 Active 계좌 잔액이다. 별도 누적 설정이나 DB 컬럼은 두지 않는다.

`cash_flow_balance`는 예정 지출, 미확인 고정 의무, 동결, 미래 급여와 잔여 유동성을 포함하는 포괄 지표가 아니다. Active 계좌에 실제로 있는 돈과 그중 자유롭게 쓸 수 있는 돈은 다를 수 있다.

## 미래 전환 조건

다음 급여를 미리 담보로 잡지 않고, 이미 확보된 현금 범위 안에서만 카드를 사용하기 시작하면 `scheduled_income`의 직접 선반영을 잔여 유동성 계산에서 제거한다.

전환 후 후보 계산:

```text
건전화 이후 remaining_liquidity
= cash_flow_balance
  - card_total
  - liquidity_fixed_total
  - frozen_asset_total
```

이때도 다음은 바꾸지 않는다.

- 달력 월 예산 주기
- 월마감이 `급여` 실제 입금을 생성하는 상태 전이
- 전체 기간 실제 현금흐름 누계
- 현금성 정기지출의 미확인 의무 → 실제 출금 전환. 확인 전후 `remaining_liquidity`는 같아야 한다.
- Claim과 Family Card를 유동성에 직접 포함하지 않는 정책

즉 미래 변경의 핵심은 “월별 현금흐름만 다시 계산”이 아니라, 아직 들어오지 않은 다음 급여를 직접 더하는 `scheduled_income` 항을 제거하는 것이다.

## Judgment에서 결정할 것

현재 본인 앱 Judgment는 `budget`, `credit`, `payment` 세 축을 반환한다. 건전화 전환 전에 다음을 결정한다.

1. `payment`가 계속 해당 결제월의 `이달 기준 수입`을 분모로 볼지, 이미 확보된 잔여 유동성으로 결제 가능 여부를 볼지 결정한다.
2. current ledger 기반 Summary의 `card_total`, 월마감 이후 활성 결제 batch의 `remaining_amount`, 즉시결제·선결제가 만드는 음수 cash flow는 서로 다른 상태다. 현재 구현의 어떤 카드채무가 `remaining_liquidity`에 이미 반영됐다고 단정하지 않는다.
3. 건전화 전환 직전에 당시 코드를 다시 검토하여 카드 사용·결제 batch·실제 출금을 한 번만 반영하는 기준을 정한다. 이번 문서에서는 미래 카드대금 계산식을 확정하지 않는다.
4. 잔여 유동성 0원, 음수, 결제일까지 14일·5일·2일·당일·연체 상태의 등급을 정한다.
5. `budget`과 `payment`가 같은 부족 상태를 중복 경고할지 역할을 분리한다.
6. 실제 급여가 설정 금액과 달랐을 때 차이를 Judgment가 지적할지 결정한다.
7. Claim 제거와 향후 Family Card 제거가 핵심 판단을 바꾸지 않도록 feature 경계를 재확인한다.

현행 입력값과 분기 순서는 [Judgment 문구 관리](judgment-messages.md)의 `현행 Judgment 데이터 흐름`을 기준으로 한다. 정책을 결정한 뒤 입력 feature와 등급 경계를 테스트로 먼저 고정하고 문구 pool을 수정한다.

명시적 미래 TODO: 재무 건전화 전환 시 current ledger의 `card_total`, 활성 payment batch의 미결제 채무, 실제 결제 cash flow를 최신 repo 전체에서 다시 추적하고, 각 채무를 상태 전이 중 정확히 한 번만 `remaining_liquidity`에 반영하는 모델을 결정한다. 단순히 batch `remaining_amount`를 현행 식에 더하지 않는다.

## AI 회계감사 Export 의존성

모바일의 ChatGPT/AI 회계감사 Markdown은 현재 `scheduled_income`의 다음 급여 선반영을 의도된 과도기 운용 모델로 설명한다. 따라서 재무 건전화 전환 시 Summary 계산만 바꾸고 감사 자료를 그대로 두면 AI가 종료된 모델을 현재 사실로 해석하게 된다.

전환 시 다음을 한 작업으로 검토한다.

- `mobile/lib/src/ai_audit_report.dart`의 `재무 운용 기준`에서 다음 급여 선반영 설명을 제거하거나 건전화 이후 설명으로 바꾼다.
- `mobile/assets/ai_audit_instructions.md`의 과도기 모델, 다음 급여 담보, 미래 목표 문구를 현재 상태에 맞게 바꾼다.
- `scheduled_income`을 감사 기준선으로 계속 제공할지, 실제 주 수입 이력을 다른 방식으로 제공할지 재검토한다.
- `remaining_liquidity`의 설명을 건전화 이후 공식 semantics에 맞게 갱신한다.
- AI가 더 이상 obsolete한 과도기 모델을 기준으로 감사하지 않는지 회귀 테스트로 확인한다.

## 전환 전 검증

- 실제 Snapshot 사본으로 전환 전후 잔여 유동성을 비교한다.
- 사용자가 입력한 future-dated cash flow가 발생일 전 Active 계좌 잔액에 들어가지 않는지 확인한다.
- 월마감 급여가 실행일에 즉시 Active 계좌 잔액에 들어가는지 확인한다.
- 월마감 한 번당 `급여`가 정확히 한 건만 생성되는지 확인한다.
- 월마감 실패 시 원장 이동, 급여, 결제 batch가 모두 rollback되는지 확인한다.
- 수동으로 같은 급여를 중복 입력하지 않는 운영 규칙을 확인한다.
- current ledger `card_total`, batch `remaining_amount`, 즉시결제 현금 유출이 계산과 판단에서 이중 차감되지 않는지 확인한다.
- 웹과 모바일이 서버 Summary와 Judgment를 그대로 표시하는지 확인한다.
- ChatGPT/AI 회계감사 Markdown과 지침이 전환 이후 재무 모델을 설명하는지 확인한다.

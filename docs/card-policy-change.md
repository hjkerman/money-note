# 카드 교체와 할인 정책 변경

이 문서는 실제 카드를 바꾸는 날 Money Note의 실결제액 정책을 안전하게 교체하기 위한 절차다. 카드는 자주 바뀌지 않으므로 설정 UI 대신 코드에 사용월별 정책 이력을 명시한다.

## 먼저 구분할 것

할인 계산에서 카드는 네 개의 독립 객체다.

- `OWNER`: 본인카드
- `FAMILY`: 가족카드
- `TOLL`: 후불 하이패스/통행료카드
- `TRANSIT`: 교통카드

본인카드와 가족카드는 현재 1.2%라는 같은 계산식을 우연히 쓸 뿐이다. 한 카드의 교체가 다른 카드의 정책 변경을 뜻하지 않는다. 실제로 바뀐 카드의 이력만 수정한다.

## 절대 하지 않을 일

- `backend/app/services/card_charge/registry.py`의 기존 binding을 새 할인율로 덮어쓰지 않는다.
- 웹이나 모바일에 할인율과 키워드 계산을 추가하지 않는다.
- 과거 거래의 `amount_value` 또는 수동 override를 일괄 수정하지 않는다.
- 본인카드를 바꿨다는 이유로 가족카드·통행료카드·교통카드 정책을 함께 바꾸지 않는다.

기존 binding을 수정하면 과거 거래와 Snapshot을 조회할 때 새 카드 정책으로 다시 계산되어 당시 카드대금이 달라진다.

## 교체 절차

1. 새 카드의 실제 사용 시작월을 `YYYY-MM`로 정한다.
2. 혜택 유형을 고른다.
   - 청구할인형 단일 비율: `FlatStatementDiscountPolicy`
   - 자동 실결제액 계산을 하지 않음: `NoAutomaticDiscountPolicy`
   - 항목별 비율이 필요하면 새 policy class를 추가한다.
3. `registry.py`에서 해당 카드 타임라인 끝에 새 `PolicyBinding`을 추가한다.
4. 새 policy class는 할인 계산뿐 아니라 `snapshot_definition()`으로 안정적인 정책 ID, 종류와 계산 매개변수를 반환해야 한다.
5. 분류 키워드나 우선순위를 바꾸면 `card_classifier_manifest()` 명세도 실제 로직과 함께 갱신한다.
6. `backend/tests/test_card_charge.py`에 변경 직전 월과 시작월의 예상값을 추가한다.
7. 백엔드 전체 테스트와 기존 Snapshot v3/v4 복원 테스트를 실행한다.
8. 배포 직후 새 Snapshot을 내려받아 `card_charge_policy`에 새 시작월 binding이 있고 과거 binding이 남아 있는지 확인한다.
9. API 응답 형식을 바꾸지 않았다면 백엔드 컨테이너만 재빌드해 배포한다.

Snapshot v4는 생성 당시 정책 명세를 데이터와 함께 해시한다. 과거 binding을 덮어쓰면 기존 v4 Snapshot과 현재 서버 정책이 달라져 복원이 차단되는 것이 정상이다. 복원을 통과시키려고 과거 Snapshot을 편집하지 말고, 기존 binding을 되살린 뒤 새 시작월 binding을 추가한다.

Snapshot 생성월 이후부터 적용되는 새 binding을 타임라인 끝에 추가하는 것은 기존 v4 Snapshot 복원을 막지 않는다. 반대로 기존 Snapshot 생성월 이전이나 같은 월부터 적용되는 binding을 뒤늦게 추가하면 과거 금액을 재해석하므로 복원이 차단된다.

예를 들어 본인카드만 2027년 3월부터 자동 할인 없는 카드로 바뀐다면 개념상 다음처럼 추가한다.

```python
DiscountCard.OWNER: (
    PolicyBinding(
        "0001-01",
        FlatStatementDiscountPolicy("owner-flat-statement-1.2"),
    ),
    PolicyBinding(
        "2027-03",
        NoAutomaticDiscountPolicy("owner-no-automatic-discount"),
    ),
),
```

가족카드 타임라인은 이 변경과 무관하므로 그대로 둔다.

## 항목별 정책을 추가할 때

`CardChargeInput`에는 다음 문맥이 이미 전달된다.

- `title`
- `merchant`
- `spending_category`
- 사용월과 원금

새 정책은 이 문맥으로 `[의료]`, `[쇼핑]` 같은 태그나 가맹점별 규칙을 판단할 수 있다. 현재 1.2% 정책은 문맥을 받기만 하고 할인율을 달리하지 않는다.

항목별 규칙을 추가해도 수동 실결제액 override가 항상 최우선이어야 한다. 자동 계산이 불확실한 카드는 `NoAutomaticDiscountPolicy`로 두고 사용자가 필요한 항목만 실결제액을 직접 보정하는 편이 안전하다.

## 배포 후 확인

- 변경 시작월 이전 거래의 할인액이 그대로다.
- 변경 시작월부터 새 정책이 적용된다.
- 본인/가족 월별 혜택 스위치가 독립적으로 동작한다.
- 통행료와 교통카드 자동 할인은 0원이다.
- 수동 실결제액 보정이 모든 카드에서 자동 정책보다 우선한다.
- 카드대금, Claim, 공유 페이지, 요약과 결제 화면이 같은 실결제액을 표시한다.

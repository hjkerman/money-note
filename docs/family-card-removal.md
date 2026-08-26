# 가족카드 제거 가이드

`family_card`는 동생이 독립 카드를 쓰기 전까지만 유지하는 과도기적 운영 기능이다. 제거 시점에는 관련 데이터 전체 삭제를 허용하지만, 본인 원장과 핵심 계산은 바뀌면 안 된다.

## 현재 경계

- 저장: `monthly_panels.panel_type = "family_card"`
- 설정: `family_card_last4`, `card_discount_policy:family:{YYYY-MM}`
- 라벨: `panel_family_card_title`
- 할인: `card_charge`의 `DiscountCard.FAMILY` 정책 이력
- API: 가족카드 패널 CRUD/일괄 처리, `/share/family_card`, summary의 `family_card_*`
- 웹: `features/familyCard`, 당월 탭, 설정, 패널 handler와 타입
- 모바일: 정산 화면, 카드 끝 4자리 설정, 알림 후보의 가족 사용 경로와 타입
- 판단: 가족카드 공유 문구와 카드 한도 사용률 보조 입력
- 백업: 일반 `monthly_panels`, `app_settings`, `app_labels` 행으로 포함

전용 핵심 테이블은 없으며, 가족카드 행은 원장·Claim·현금흐름·카드결제 batch에 편입되지 않는다.

## 제거 순서

1. 제거 직전 Snapshot과 SQLite 하드카피를 만든다.
2. `family_card` 패널 행, 가족카드 설정과 라벨을 삭제한다.
3. 가족카드 공유 route/service와 전용 판단 문구를 제거한다.
4. summary 응답의 `family_card_original_total`, `family_card_net_total`을 제거하고 API 타입을 함께 갱신한다.
5. 웹의 family card feature, 탭, 설정, handler/type 분기를 제거한다.
6. 모바일의 가족카드 정산, 설정, 알림 후보 라우팅과 모델 필드를 제거한다.
7. `card_charge` 레지스트리와 enum에서 `FAMILY`만 제거한다. 본인·통행료·교통카드 정책은 수정하지 않는다.
8. Snapshot 복원이 제거된 가족카드 행과 알 수 없는 설정을 하위호환 정책에 따라 안전하게 무시하거나 명시적으로 폐기하는지 확인한다.
9. 아래 불변 조건과 전체 빌드를 검증한다.

## 불변 조건

가족카드 제거 전후에 다음 값과 동작은 같아야 한다.

- `ledger_entries` 행과 금액
- Claim 행과 실청구액
- 당월 지출 총합과 소비 통계
- 카드대금과 결제 batch
- 현금흐름과 잔여 유동성
- 본인카드, 통행료카드, 교통카드의 할인 결과
- 월마감, Snapshot, Pre-restore

가족카드 제거 때문에 위 계산을 수정해야 한다면 feature 경계가 다시 오염된 것이다.

## 현재 감사 결과

2026-08 카드 정책 모듈화 시점 기준으로 제거 가능성은 유지된다. 가족카드 참조는 UI/API/공유/설정/응답 타입에 걸쳐 있어 한 폴더 삭제만으로 끝나지는 않지만, 핵심 원장·카드대금·유동성 코드를 변경하지 않고 열거된 경계만 제거할 수 있다. 신규 공통 모듈은 가족카드 화면이나 패널 응답에 의존하지 않아야 한다.

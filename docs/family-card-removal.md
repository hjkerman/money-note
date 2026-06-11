# 가족카드 제거 가이드

family_card는 과도기적 부가 기능이며 제거 가능해야 한다.

## 제거 대상

- family_card 탭
- family_card 입력 UI
- family_card 조회 UI
- family_card 관련 API
- family_card 관련 TypeScript 타입
- family_card 관련 Python 모델/서비스
- family_card_last4
- family_card_enabled
- family_card 테스트

## 제거하면 안 되는 것

다음 핵심 계산은 family_card 제거로 수정되어서는 안 된다.

- ledger_entries
- claim
- card_payment
- liquidity
- monthly summary
- 소비 통계
- 카드대금 계산

## 제거 후 검증

- 앱이 family_card 설정 없이 정상 실행됨
- 당월 지출 총합 정상
- 소비 통계 정상
- card_payment 정상
- liquidity 정상
- npm build 통과
- backend test 통과

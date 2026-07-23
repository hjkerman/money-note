# Money Note Agent Guide
1. 반드시 읽을 문서
- docs/domain-model.md
- docs/runbook.md
- docs/known-issues.md

2. 규칙
- domain-model.md를 단일 진실 원천(Source of Truth)으로 취급
- 서버 DB와 서버 API 계산 결과를 런타임 단일 진실 원천으로 취급
- 할인 가능 여부, 할인액, 실결제액, 요약 합계, 기준 월을 웹/모바일에서 다시 추론하지 말 것
- family_card는 비핵심 도메인 기능. ledger_entries, claim, card_payment, liquidity와 강하게 결합하지 말 것.
- 인증/백업/복원 변경 전 docs/security.md와 docs/runbook.md 확인
- 성공 로그 전체 출력 금지
- 실패 시에만 tail 출력
- git diff 전체보다 git diff --stat 우선
- npm build, backend 검증 수행

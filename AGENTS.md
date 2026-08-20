# Money Note Agent Guide
1. 반드시 읽을 문서
- docs/project-state.md
- docs/domain-model.md
- docs/known-issues.md
- 운영·배포·백업·복원 작업이면 docs/runbook.md

2. 규칙
- domain-model.md를 단일 진실 원천(Source of Truth)으로 취급
- 서버 DB와 서버 API 계산 결과를 런타임 단일 진실 원천으로 취급
- 할인 가능 여부, 할인액, 실결제액, 요약 합계, 기준 월을 웹/모바일에서 다시 추론하지 말 것
- 카드 종류 분류, 자동 할인, 수동 override, 실결제액 계산은 `backend/app/services/card_charge/`만 수정할 것
- 모바일 회계감사 역할과 판단 지침의 단일 원본은 `mobile/assets/ai_audit_instructions.md`다. 문구 보강 시 Dart 코드에 지침 사본을 만들지 말 것.
- family_card는 비핵심 도메인 기능. ledger_entries, claim, card_payment, liquidity와 강하게 결합하지 말 것.
- 인증/백업/복원 변경 전 docs/security.md와 docs/runbook.md 확인
- 성공 로그 전체 출력 금지
- 실패 시에만 tail 출력
- git diff 전체보다 git diff --stat 우선
- npm build, backend 검증 수행
- 사용자가 커밋과 푸시를 함께 요청하면 검증 후 커밋·푸시하고 런타임 변경 범위에 맞춰 운영 배포까지 수행할 것. `backend/`, `frontend/`, `docker-compose.yml` 변경은 `scripts/deploy-server.sh`, `mobile/` 변경은 `scripts/release-mobile.sh`를 사용한다. 문서만 바뀐 경우에는 배포하지 않는다. 사용자가 배포 제외를 명시하면 배포하지 않으며, 배포 설정이 없거나 실패하면 그 사실을 명확히 보고할 것.

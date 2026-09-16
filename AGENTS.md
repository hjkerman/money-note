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
- 이 서버에서 개발·테스트는 `/home/hjkerman/codex/money-note`에서 수행한다. `/opt/money-note`는 production이며 개발 working tree가 아니다.
- Git working copy, production artifact, 영속 데이터는 분리한다. production DB·Snapshot·`.env`를 개발환경으로 복사하거나 테스트 대상으로 사용하지 않는다.
- 커밋·push는 배포 허가가 아니다. 명시적인 deployment 요청이 있을 때만 `scripts/deploy-server.sh --apply` 또는 `scripts/release-mobile.sh --apply`를 사용한다. 두 명령의 기본값은 읽기 전용 dry-run이다.
- 개발 API는 `scripts/dev-server.sh`의 `127.0.0.1:18081`과 `work/dev-data`를 사용한다. 운영 API `18080`에 테스트 요청을 보내거나 개발 checkout에서 기본 `docker compose up`을 실행하지 않는다.
- 초기 구성, 검증 명령, staging·rollback·보관 한도는 `docs/runbook.md`의 서버 내 개발·배포 절을 따른다. production 직접 수정, 서비스 restart/reload, DB migration은 명시적 운영 작업에서만 허용한다.

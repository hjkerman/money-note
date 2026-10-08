# Money Note Agent Guide
1. 반드시 읽을 문서
- docs/project-state.md
- docs/domain-model.md
- docs/known-issues.md
- trust boundary·bundle admission·correctness 감사 작업이면 docs/architecture.md의 `서버 authority와 클라이언트 신뢰 경계`
- 운영·배포·백업·복원 작업이면 docs/runbook.md

2. 규칙
- domain-model.md를 단일 진실 원천(Source of Truth)으로 취급
- 서버 DB와 서버 API 계산 결과를 런타임 단일 진실 원천으로 취급
- 할인 가능 여부, 할인액, 실결제액, 요약 합계, 기준 월을 웹/모바일에서 다시 추론하지 말 것
- 서버는 확정 금융 projection의 authority이며, 모바일은 안전한 wire/구조/identity·Snapshot 복구 가능성·generation·durable baseline·Offline/pending/reconciliation 경계를 검증한다. OfflineProjection은 input-only journal에 대한 임시 예상 view이지 canonical backend 계산 엔진이 아니다.
- 새 모바일 금융 검증 의무는 기존 계약, 구체적 위협/실패, trusted backend 보증의 부족, 금융 알고리즘 복제 여부, Offline·호환성·성능 영향을 제시해야 한다. backend projection을 독립 재계산한 결과와 다르다는 이유만으로 mobile blocker를 자동 선언하지 말 것. 필수 구조·저장·복구 검사도 서버 신뢰를 이유로 완화하지 말 것.
- 모바일을 독립 금융 검증 엔진으로 확장하려면 명시적 architecture 결정이 필요하다. 신뢰 경계의 규범 원본은 docs/architecture.md에 두고, 과거 감사 반례는 보존하며 문서 변경을 구현 결함의 수정으로 표현하지 말 것.
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

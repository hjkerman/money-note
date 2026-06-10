# Money Note Agent Guide
1. 반드시 읽을 문서
- docs/domain-model.md
- docs/runbook.md
- docs/known-issues.md

2. 규칙
- domain-model.md를 단일 진실 원천(Source of Truth)으로 취급
- family_card는 제거 예정 기능
- 성공 로그 전체 출력 금지
- 실패 시에만 tail 출력
- git diff 전체보다 git diff --stat 우선
- npm build, backend 검증 수행

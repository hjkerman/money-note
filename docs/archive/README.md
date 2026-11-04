# 역사 기록

이 디렉터리는 owner가 승인한 Repository Hygiene Batch 1의 보관 위치다. 과거 판정·실패·예외를 현재 정책으로 덮어쓰지 않는다. 현행 규범은 [문서 안내](../README.md), 진행 상태는 [로드맵](../development-reports/money-note-final-optimization-and-closure-roadmap.md)을 따른다.

- [Phase 1 완화·종결 장부](phase1/phase1-mitigation-plan.md): 최초 p95 실패·거부/원복·owner 한정 예외·재채택 이력 보존.
- Phase 1 조사: [P1-01](phase1/p1-01-monthly-expense-lazy-widget-results.md), [P1-02](phase1/p1-02-flutter-rebuild-derived-state-results.md), [P1-03](phase1/p1-03-snapshot-save-validation-performance-results.md), [P1-04](phase1/p1-04-backend-sql-presenter-performance-results.md), [Refresh](phase1/p1-r-mobile-refresh-performance-results.md). 조사 compact 근거5개는 `phase1/evidence/`에 원본 bytes로 보존한다.
- [Phase 2 N02 조사](phase2/phase2-n02-snapshot-reuse-investigation.md): DEFER·독립 Snapshot GET 유지. N01 결함·수정·PASS 이력과 current evidence는 [Phase2 장부](../development-reports/phase2-mobile-network-optimization-candidates.md) 및 기존 benchmarks 경로를 유지한다.
- [Phase 3 수용·검증·게시](phase3/phase3-cleanup-candidate-inventory.md), [폐기된 Claim 제거 계획](phase3/claim-removal-plan-superseded.md). Claim은 [현행 정책](../domain-model.md#claim-유지-정책)에 따라 무기한 유지한다.
- [과거 디스크 조사](repository-hygiene/money-note-disk-cleanup-audit.md): 당시 용량이며 현재 측정으로 사용하지 않는다.
- [Batch 1 실행 기록](batch1-cleanup-record.md).

역사 JSON·압축 근거 안의 당시 명령/원경로 문자열은 수정하지 않았다. 재현 시 [이동 대응표](../benchmarks/repository-hygiene-batch1.json)의 old/new 경로를 적용한다. B03 source lock·G1 고정 문서/proof·현재 회귀 fixture는 이동하지 않았다. archive 이동은 Git blob 용량을 줄이지 않으며 현재 branch 게시가 운영 배포 승인은 아니다.

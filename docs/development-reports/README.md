# 최적화·개선·감사 작업 기록

Phase3 D01–D03·Claim 유지 정책은 owner 수용과 안전 게시를 마쳐 **CLOSED**다. Phase4는 미착수이며 별도 승인이 필요하다. 아래 로드맵을 기준으로 진행하고 장기 유지 문서는 [상위 문서 안내](../README.md)에 둔다.

## 현재 로드맵·P1 결과

Batch 1에서 완료된 P1·N02·Phase3 기록과 과거 디스크 조사를 [archive](../archive/README.md)로 옮겼다. 링크를 갱신했으며 원 판정·owner 예외·Claim 무기한 유지 정책은 변하지 않는다.

- [money-note-final-optimization-and-closure-roadmap.md](money-note-final-optimization-and-closure-roadmap.md)
- [phase2-mobile-network-optimization-candidates.md](phase2-mobile-network-optimization-candidates.md) — 이전 단계, N01 ACCEPTED·N02 조사 DEFER, 독립 Snapshot GET 유지 권고
- [phase1-mitigation-plan.md](../archive/phase1/phase1-mitigation-plan.md) — 현재 공유 계획·구현/감사 장부, Phase 1 CLOSED·최종 감사 PASS / R 채택·S/U 보류
- [p1-r-mobile-refresh-performance-results.md](../archive/phase1/p1-r-mobile-refresh-performance-results.md)
- [p1-04-backend-sql-presenter-performance-results.md](../archive/phase1/p1-04-backend-sql-presenter-performance-results.md)

## 이전 P1 결과·보류 후보

- [p1-01-monthly-expense-lazy-widget-results.md](../archive/phase1/p1-01-monthly-expense-lazy-widget-results.md) — 원래 경로 보존
- [p1-02-flutter-rebuild-derived-state-results.md](../archive/phase1/p1-02-flutter-rebuild-derived-state-results.md) — 원래 경로 보존
- [p1-03-snapshot-save-validation-performance-results.md](../archive/phase1/p1-03-snapshot-save-validation-performance-results.md) — 원래 경로 보존

P1-R-01 최초 p95 기준 미달·원복은 보존한다. 독립 거부 검토 A와 owner의 한정1회 예외 승인 뒤 동일 B를 재복원해 활성132건 통과로 채택했다. P1-S는 digest 비용 조건 실패로 미구현·보류했다. P1-U는 보류, P1-05는 소유자 결정으로 제외했다. 실제 구현·감사 지적은 위 공유 장부를 갱신하며 Phase1 종료나 다음 단계 진입은 자동이 아니다.

## 기존 단계별 설계·구현 기록

- [T6.5](../t65/README.md)
- [T6.6 설계·구현](../t66/)
- [측정·감사 근거](../benchmarks/)

## 원래 경로를 유지한 기록

아래는 기존102개 기록의 목차다. Batch 1의 P1·디스크 조사와 Batch 2에서 검증된 과거 보고서는 archive로 이동하고 링크를 갱신했다. 고정 경로·소비자·복구 의존성이 있는 예외와 동결 근거는 원위치 보존한다. 실제 이동·제외 목록과 게시 차단 상태는 [위생 기록](../archive/repository-hygiene/batch2-closure.md)에 있다. 로컬 미추적 대용량 근거는 게시하지 않는다.

### 이전 P1·위생 조사

- [money-note-disk-cleanup-audit.md](../archive/repository-hygiene/money-note-disk-cleanup-audit.md)
- [p1-01-monthly-expense-lazy-widget-results.md](../archive/phase1/p1-01-monthly-expense-lazy-widget-results.md)
- [p1-02-flutter-rebuild-derived-state-results.md](../archive/phase1/p1-02-flutter-rebuild-derived-state-results.md)
- [p1-03-snapshot-save-validation-performance-results.md](../archive/phase1/p1-03-snapshot-save-validation-performance-results.md)

### 실기기 Gate·플랫폼 개선·감사

- [real-device-gate-g1-a01-integrated-architecture.md](../real-device-gate-g1-a01-integrated-architecture.md)
- [real-device-gate-g1-a01-static-platform-reassessment.md](../real-device-gate-g1-a01-static-platform-reassessment.md)
- [real-device-gate-g1-conditional-adoption-and-normative-application-plan.md](../real-device-gate-g1-conditional-adoption-and-normative-application-plan.md)
- [real-device-gate-g1-fs1-independent-audit.md](../real-device-gate-g1-fs1-independent-audit.md)
- [real-device-gate-g1-fs1-technical-spec.md](../real-device-gate-g1-fs1-technical-spec.md)
- [real-device-gate-g1-n2-independent-normative-review.md](../real-device-gate-g1-n2-independent-normative-review.md)
- [real-device-gate-g1-n3-exact-normative-application.md](../real-device-gate-g1-n3-exact-normative-application.md)
- [real-device-gate-g1-n5-independent-application-consistency.md](../real-device-gate-g1-n5-independent-application-consistency.md)
- [real-device-gate-g1-o2-contract-corrections.md](../real-device-gate-g1-o2-contract-corrections.md)
- [real-device-gate-g1-o2-corrected-proposal.md](../real-device-gate-g1-o2-corrected-proposal.md)
- [real-device-gate-g1-o3-invalidation-boundary-correction.md](../real-device-gate-g1-o3-invalidation-boundary-correction.md)
- [real-device-gate-g1-p01-technical-proof-plan.md](../real-device-gate-g1-p01-technical-proof-plan.md)
- [real-device-gate-g1-r01-independent-contract-review.md](../archive/device-gate/history/real-device-gate-g1-r01-independent-contract-review.md)
- [real-device-gate-g1-r02-independent-contract-rereview.md](../real-device-gate-g1-r02-independent-contract-rereview.md)
- [real-device-gate-g1-r03-independent-f02-closure.md](../real-device-gate-g1-r03-independent-f02-closure.md)
- [real-device-gate-g1-safety-contract-proposal.md](../real-device-gate-g1-safety-contract-proposal.md)
- [real-device-gate-g1-safety-contract.md](../real-device-gate-g1-safety-contract.md)
- [real-device-gate-g1-status-annotation-correction.md](../archive/device-gate/history/real-device-gate-g1-status-annotation-correction.md)
- [real-device-gate-g1-status-annotation-independent-review.md](../archive/device-gate/history/real-device-gate-g1-status-annotation-independent-review.md)
- [real-device-gate-g1-supplementary-amendment-proposal.md](../real-device-gate-g1-supplementary-amendment-proposal.md)
- [real-device-gate-g2-n01-exception-amendment-proposal.md](../real-device-gate-g2-n01-exception-amendment-proposal.md)
- [real-device-gate-g2-n02-independent-exception-review.md](../real-device-gate-g2-n02-independent-exception-review.md)
- [real-device-gate-g2-p01-restricted-campaign-proposal.md](../real-device-gate-g2-p01-restricted-campaign-proposal.md)
- [real-device-gate-g2-r01-independent-safety-review.md](../real-device-gate-g2-r01-independent-safety-review.md)
- [real-device-gate-g2-r02-independent-sc10-review.md](../real-device-gate-g2-r02-independent-sc10-review.md)
- [real-device-gate-g2-sc10-clarification.md](../real-device-gate-g2-sc10-clarification.md)
- [real-device-gate-prep01-headless-emulator-foundation.md](../real-device-gate-prep01-headless-emulator-foundation.md)
- [real-device-gate-prep02-isolated-android-smoke.md](../archive/device-gate/history/real-device-gate-prep02-isolated-android-smoke.md)
- [real-device-gate-prep03-independent-isolation-audit.md](../archive/device-gate/history/real-device-gate-prep03-independent-isolation-audit.md)
- [real-device-gate-prep04-isolation-remediation.md](../archive/device-gate/history/real-device-gate-prep04-isolation-remediation.md)
- [real-device-gate-prep05-independent-remediation-reaudit.md](../archive/device-gate/history/real-device-gate-prep05-independent-remediation-reaudit.md)
- [real-device-gate-prep06-adb-lifecycle-remediation.md](../archive/device-gate/history/real-device-gate-prep06-adb-lifecycle-remediation.md)
- [real-device-gate-prep07-independent-fail-closed-review.md](../archive/device-gate/history/real-device-gate-prep07-independent-fail-closed-review.md)
- [real-device-gate-prep08-adb-dispatch-boundary-remediation.md](../archive/device-gate/history/real-device-gate-prep08-adb-dispatch-boundary-remediation.md)
- [real-device-gate-prep09-independent-dispatch-audit.md](../archive/device-gate/history/real-device-gate-prep09-independent-dispatch-audit.md)
- [real-device-gate-prep10-f01-architecture-decision.md](../real-device-gate-prep10-f01-architecture-decision.md)

### T6.6 구현·감사

- [t66e3-implementation.md](../t66e3-implementation.md)
- [t66e3-independent-audit.md](../t66e3-independent-audit.md)
- [t66e4-a01-correction.md](../t66e4-a01-correction.md)
- [t66e4-a01-independent-reaudit.md](../t66e4-a01-independent-reaudit.md)
- [t66e4-implementation-resumption.md](../t66e4-implementation-resumption.md)
- [t66e4-implementation.md](../t66e4-implementation.md)
- [t66e4-independent-audit.md](../t66e4-independent-audit.md)
- [t66e4-p0-implementation.md](../t66e4-p0-implementation.md)
- [t66e4-p0-independent-audit.md](../t66e4-p0-independent-audit.md)
- [t66e4-ra01-correction.md](../t66e4-ra01-correction.md)
- [t66e4-ra01-independent-reaudit.md](../t66e4-ra01-independent-reaudit.md)

### T6.6F 성능·개선·감사

- [t66f-b01-backend-concurrency-investigation.md](../archive/legacy-performance/t66f-b01-backend-concurrency-investigation.md)
- [t66f-b01-independent-validation.md](../archive/legacy-performance/t66f-b01-independent-validation.md)
- [t66f-b02-a01-cold-acquisition-investigation.md](../t66f-b02-a01-cold-acquisition-investigation.md)
- [t66f-b02-a01-targeted-correction.md](../archive/legacy-performance/t66f-b02-a01-targeted-correction.md)
- [t66f-b02-a02-100k-acquisition-investigation.md](../t66f-b02-a02-100k-acquisition-investigation.md)
- [t66f-b02-a02-targeted-correction.md](../t66f-b02-a02-targeted-correction.md)
- [t66f-b02-e2-object-budget-investigation.md](../archive/legacy-performance/t66f-b02-e2-object-budget-investigation.md)
- [t66f-b02-independent-targeted-audit.md](../t66f-b02-independent-targeted-audit.md)
- [t66f-b02-large-profile-implementation.md](../archive/legacy-performance/t66f-b02-large-profile-implementation.md)
- [t66f-b03-ic01-p01-100k-lease-feasibility.md](../archive/legacy-performance/t66f-b03-ic01-p01-100k-lease-feasibility.md)
- [t66f-b03-ic01-p02-prepared-statement-reuse.md](../archive/legacy-performance/t66f-b03-ic01-p02-prepared-statement-reuse.md)
- [t66f-b03-ic01-p03-real-path-lease-verification.md](../archive/legacy-performance/t66f-b03-ic01-p03-real-path-lease-verification.md)
- [t66f-b03-ic01-p04-late-stage-differential-diagnosis.md](../archive/legacy-performance/t66f-b03-ic01-p04-late-stage-differential-diagnosis.md)
- [t66f-b03-ic01-p05-backend-artifact-handoff.md](../archive/legacy-performance/t66f-b03-ic01-p05-backend-artifact-handoff.md)
- [t66f-b03-ic01-targeted-correction.md](../archive/legacy-performance/t66f-b03-ic01-targeted-correction.md)
- [t66f-b03-ic02-ir03-n01-n02-correction.md](../archive/legacy-performance/t66f-b03-ic02-ir03-n01-n02-correction.md)
- [t66f-b03-ic03-installation-generation-correction.md](../archive/legacy-performance/t66f-b03-ic03-installation-generation-correction.md)
- [t66f-b03-ic04-exception-safe-lifecycle-correction.md](../archive/legacy-performance/t66f-b03-ic04-exception-safe-lifecycle-correction.md)
- [t66f-b03-ic05-ownership-entry-handoff-correction.md](../archive/legacy-performance/t66f-b03-ic05-ownership-entry-handoff-correction.md)
- [t66f-b03-ic06-pep669-monitoring-preflight-correction.md](../archive/legacy-performance/t66f-b03-ic06-pep669-monitoring-preflight-correction.md)
- [t66f-b03-independent-instrumentation-audit.md](../t66f-b03-independent-instrumentation-audit.md)
- [t66f-b03-ir01-independent-reaudit-scope.md](../archive/legacy-performance/t66f-b03-ir01-independent-reaudit-scope.md)
- [t66f-b03-ir02-audit-candidate-freeze.md](../archive/legacy-performance/t66f-b03-ir02-audit-candidate-freeze.md)
- [t66f-b03-ir03-independent-correctness-reaudit.md](../archive/legacy-performance/t66f-b03-ir03-independent-correctness-reaudit.md)
- [t66f-b03-ir04-independent-final-reaudit.md](../archive/legacy-performance/t66f-b03-ir04-independent-final-reaudit.md)
- [t66f-b03-ir05-independent-correctness-closure.md](../archive/legacy-performance/t66f-b03-ir05-independent-correctness-closure.md)
- [t66f-b03-ir06-independent-lifecycle-closure.md](../archive/legacy-performance/t66f-b03-ir06-independent-lifecycle-closure.md)
- [t66f-b03-ir07-independent-pep669-closure.md](../t66f-b03-ir07-independent-pep669-closure.md)
- [t66f-b03-logical-cost-instrumentation.md](../t66f-b03-logical-cost-instrumentation.md)
- [t66f-b04-phase-b-measurement-feasibility.md](../archive/legacy-performance/t66f-b04-phase-b-measurement-feasibility.md)
- [t66f-b05-lookup-hot-body-decode-optimization.md](../archive/legacy-performance/t66f-b05-lookup-hot-body-decode-optimization.md)
- [t66f-b05a-engine-admission-real-flutter-ab.md](../archive/legacy-performance/t66f-b05a-engine-admission-real-flutter-ab.md)
- [t66f-b05b-independent-5k-on-ab-replication.md](../archive/legacy-performance/t66f-b05b-independent-5k-on-ab-replication.md)
- [t66f-b06-cold-acquisition-critical-path-analysis.md](../archive/legacy-performance/t66f-b06-cold-acquisition-critical-path-analysis.md)
- [t66f-b07-bounded-connect-schema-attribution.md](../archive/legacy-performance/t66f-b07-bounded-connect-schema-attribution.md)
- [t66f-b08-expected-revision-contract-reuse.md](../archive/legacy-performance/t66f-b08-expected-revision-contract-reuse.md)
- [t66f-b09-engine-admission-real-flutter-cold-ab.md](../archive/legacy-performance/t66f-b09-engine-admission-real-flutter-cold-ab.md)
- [t66f-b10-independent-phase-b-closure-adjudication.md](../t66f-b10-independent-phase-b-closure-adjudication.md)
- [t66f-b11-applied-amendment-independent-consistency-review.md](../t66f-b11-applied-amendment-independent-consistency-review.md)
- [t66f-b11-approval-preflight.md](../archive/legacy-performance/t66f-b11-approval-preflight.md)
- [t66f-b11-approved-amendment-application.md](../t66f-b11-approved-amendment-application.md)
- [t66f-b11-normative-deferral-proposal.md](../t66f-b11-normative-deferral-proposal.md)
- [t66f-b11-post-amendment-closure-readjudication.md](../t66f-b11-post-amendment-closure-readjudication.md)
- [t66f-phase-b-continuation.md](../t66f-phase-b-continuation.md)
- [t66f-phase-b-final-evidence-closure.md](../t66f-phase-b-final-evidence-closure.md)
- [t66f-phase-b-independent-verification.md](../t66f-phase-b-independent-verification.md)

### T6.9 이관·실행 준비

- [t69-pre01-transferred-evidence-collection-plan.md](../t69-pre01-transferred-evidence-collection-plan.md)
- [t69-pre02-independent-execution-readiness-review.md](../t69-pre02-independent-execution-readiness-review.md)
- [t69-pre03-100k-baseline-recovery-feasibility.md](../t69-pre03-100k-baseline-recovery-feasibility.md)
- [t69-pre04-execution-readiness-plan-revision.md](../t69-pre04-execution-readiness-plan-revision.md)
- [t69-pre05-independent-e3-bookkeeping-seam-review.md](../t69-pre05-independent-e3-bookkeeping-seam-review.md)

Phase 1은 owner 전달 최종 독립 감사 **PASS — MITIGATION ACCEPTED**로 종료했다. Phase 2는 후보 감사와 owner 승인 후 N01만 구현했고, 현재 검증 PARTIAL·독립 변경 감사 대기다.

Phase 2 전송량 기준선과 N01 gzip 우선·N02 조건부 shortlist는 위 단일 후보 문서에 있다. 이 원 조사 뒤 N01 한정 backend 구현을 수행했으며 최신 상태는 후보 문서 §9에 있다.

P2-N01 한정 backend gzip 구현과 자원 측정은 후보 문서 §9에 기록했다. trailer 거부 신규 회귀1건은 미충족이며 채택·배포 승인이 아니다. 다른 후보는 구현하지 않았다.

N01-A01 모바일 raw gzip 검증 수정과 101 host PASS는 후보 문서 §10에 기록했다. 과거 PARTIAL·REWORK를 보존하며 최종 채택은 독립 재감사 뒤 별도다.

두 번째 correction N01-A01-R1의 정확한 reserved-block witness·이중 decoder·추가 pass 비용은 후보 문서 §11에 있다. 첫 correction 뒤 targeted REWORK를 보존한다.

- [phase2-n02-snapshot-reuse-investigation.md](../archive/phase2/phase2-n02-snapshot-reuse-investigation.md) — N01 최종 수용, N02 복구 시점·구조 동등성·gzip 이후 이득·DEFER 처분.

- [phase3-cleanup-candidate-inventory.md](../archive/phase3/phase3-cleanup-candidate-inventory.md) — Phase3 CLOSED, D01–D03·Claim 정책 ACCEPTED·push 성공, D04–D06 보류.

- [Phase3 수용·게시 §12](../archive/phase3/phase3-cleanup-candidate-inventory.md#12-phase-3-수용안전-게시) — 현재 게시 장부. §11의 감사 전 실행·미게시 이력 보존, Phase4 별도 승인 필요.
- [폐기된 Claim 제거 계획](../archive/phase3/claim-removal-plan-superseded.md) — 역사 원문 보존용, 현행 유지 정책·실행 지침이 아님.

# 최적화·개선·감사 작업 기록

현재 작업은 아래 로드맵을 기준으로 진행한다. 장기 유지 문서는 [상위 문서 안내](../README.md)에 있다.

## 현재 로드맵·P1 결과

- [money-note-final-optimization-and-closure-roadmap.md](money-note-final-optimization-and-closure-roadmap.md)
- [phase1-mitigation-plan.md](phase1-mitigation-plan.md) — 현재 공유 계획·구현/감사 장부, Planning Audit PASS·owner 구현 승인
- [p1-r-mobile-refresh-performance-results.md](p1-r-mobile-refresh-performance-results.md)
- [p1-04-backend-sql-presenter-performance-results.md](p1-04-backend-sql-presenter-performance-results.md)

## 이전 P1 결과·보류 후보

- [p1-01-monthly-expense-lazy-widget-results.md](../p1-01-monthly-expense-lazy-widget-results.md) — 원래 경로 보존
- [p1-02-flutter-rebuild-derived-state-results.md](../p1-02-flutter-rebuild-derived-state-results.md) — 원래 경로 보존
- [p1-03-snapshot-save-validation-performance-results.md](../p1-03-snapshot-save-validation-performance-results.md) — 원래 경로 보존

P1-R-01과 P1-S는 계획 감사 PASS·owner scoped 구현 승인을 수령했으며 baseline 조건에 따라 순차 실행한다. P1-U는 보류, P1-05는 소유자 결정으로 제외했다. 실제 구현·감사 지적은 위 공유 장부를 갱신하며 Phase1 종료나 다음 단계 진입은 자동이 아니다.

## 기존 단계별 설계·구현 기록

- [T6.5](../t65/README.md)
- [T6.6 설계·구현](../t66/)
- [측정·감사 근거](../benchmarks/)

## 원래 경로를 유지한 기록

다음102개는 기존 코드·도구·동결 근거에서 원래 경로를 직접 참조한다. 이번 정리에서는 원본 위치·내용을 보존하고 이 목차에서 한 번에 찾도록 했다. 이는 영구 이동 금지를 새로 정한 것이 아니며, 해당 경로의 이관은 별도 의존성 정리 범위다. 원시 근거는 기존 benchmarks 경로를 유지한다. 로컬에만 있는 미추적 대용량 실험 근거는 문서 커밋에 일괄 추가하지 않는다.

### 이전 P1·위생 조사

- [money-note-disk-cleanup-audit.md](../money-note-disk-cleanup-audit.md)
- [p1-01-monthly-expense-lazy-widget-results.md](../p1-01-monthly-expense-lazy-widget-results.md)
- [p1-02-flutter-rebuild-derived-state-results.md](../p1-02-flutter-rebuild-derived-state-results.md)
- [p1-03-snapshot-save-validation-performance-results.md](../p1-03-snapshot-save-validation-performance-results.md)

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
- [real-device-gate-g1-r01-independent-contract-review.md](../real-device-gate-g1-r01-independent-contract-review.md)
- [real-device-gate-g1-r02-independent-contract-rereview.md](../real-device-gate-g1-r02-independent-contract-rereview.md)
- [real-device-gate-g1-r03-independent-f02-closure.md](../real-device-gate-g1-r03-independent-f02-closure.md)
- [real-device-gate-g1-safety-contract-proposal.md](../real-device-gate-g1-safety-contract-proposal.md)
- [real-device-gate-g1-safety-contract.md](../real-device-gate-g1-safety-contract.md)
- [real-device-gate-g1-status-annotation-correction.md](../real-device-gate-g1-status-annotation-correction.md)
- [real-device-gate-g1-status-annotation-independent-review.md](../real-device-gate-g1-status-annotation-independent-review.md)
- [real-device-gate-g1-supplementary-amendment-proposal.md](../real-device-gate-g1-supplementary-amendment-proposal.md)
- [real-device-gate-g2-n01-exception-amendment-proposal.md](../real-device-gate-g2-n01-exception-amendment-proposal.md)
- [real-device-gate-g2-n02-independent-exception-review.md](../real-device-gate-g2-n02-independent-exception-review.md)
- [real-device-gate-g2-p01-restricted-campaign-proposal.md](../real-device-gate-g2-p01-restricted-campaign-proposal.md)
- [real-device-gate-g2-r01-independent-safety-review.md](../real-device-gate-g2-r01-independent-safety-review.md)
- [real-device-gate-g2-r02-independent-sc10-review.md](../real-device-gate-g2-r02-independent-sc10-review.md)
- [real-device-gate-g2-sc10-clarification.md](../real-device-gate-g2-sc10-clarification.md)
- [real-device-gate-prep01-headless-emulator-foundation.md](../real-device-gate-prep01-headless-emulator-foundation.md)
- [real-device-gate-prep02-isolated-android-smoke.md](../real-device-gate-prep02-isolated-android-smoke.md)
- [real-device-gate-prep03-independent-isolation-audit.md](../real-device-gate-prep03-independent-isolation-audit.md)
- [real-device-gate-prep04-isolation-remediation.md](../real-device-gate-prep04-isolation-remediation.md)
- [real-device-gate-prep05-independent-remediation-reaudit.md](../real-device-gate-prep05-independent-remediation-reaudit.md)
- [real-device-gate-prep06-adb-lifecycle-remediation.md](../real-device-gate-prep06-adb-lifecycle-remediation.md)
- [real-device-gate-prep07-independent-fail-closed-review.md](../real-device-gate-prep07-independent-fail-closed-review.md)
- [real-device-gate-prep08-adb-dispatch-boundary-remediation.md](../real-device-gate-prep08-adb-dispatch-boundary-remediation.md)
- [real-device-gate-prep09-independent-dispatch-audit.md](../real-device-gate-prep09-independent-dispatch-audit.md)
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

- [t66f-b01-backend-concurrency-investigation.md](../t66f-b01-backend-concurrency-investigation.md)
- [t66f-b01-independent-validation.md](../t66f-b01-independent-validation.md)
- [t66f-b02-a01-cold-acquisition-investigation.md](../t66f-b02-a01-cold-acquisition-investigation.md)
- [t66f-b02-a01-targeted-correction.md](../t66f-b02-a01-targeted-correction.md)
- [t66f-b02-a02-100k-acquisition-investigation.md](../t66f-b02-a02-100k-acquisition-investigation.md)
- [t66f-b02-a02-targeted-correction.md](../t66f-b02-a02-targeted-correction.md)
- [t66f-b02-e2-object-budget-investigation.md](../t66f-b02-e2-object-budget-investigation.md)
- [t66f-b02-independent-targeted-audit.md](../t66f-b02-independent-targeted-audit.md)
- [t66f-b02-large-profile-implementation.md](../t66f-b02-large-profile-implementation.md)
- [t66f-b03-ic01-p01-100k-lease-feasibility.md](../t66f-b03-ic01-p01-100k-lease-feasibility.md)
- [t66f-b03-ic01-p02-prepared-statement-reuse.md](../t66f-b03-ic01-p02-prepared-statement-reuse.md)
- [t66f-b03-ic01-p03-real-path-lease-verification.md](../t66f-b03-ic01-p03-real-path-lease-verification.md)
- [t66f-b03-ic01-p04-late-stage-differential-diagnosis.md](../t66f-b03-ic01-p04-late-stage-differential-diagnosis.md)
- [t66f-b03-ic01-p05-backend-artifact-handoff.md](../t66f-b03-ic01-p05-backend-artifact-handoff.md)
- [t66f-b03-ic01-targeted-correction.md](../t66f-b03-ic01-targeted-correction.md)
- [t66f-b03-ic02-ir03-n01-n02-correction.md](../t66f-b03-ic02-ir03-n01-n02-correction.md)
- [t66f-b03-ic03-installation-generation-correction.md](../t66f-b03-ic03-installation-generation-correction.md)
- [t66f-b03-ic04-exception-safe-lifecycle-correction.md](../t66f-b03-ic04-exception-safe-lifecycle-correction.md)
- [t66f-b03-ic05-ownership-entry-handoff-correction.md](../t66f-b03-ic05-ownership-entry-handoff-correction.md)
- [t66f-b03-ic06-pep669-monitoring-preflight-correction.md](../t66f-b03-ic06-pep669-monitoring-preflight-correction.md)
- [t66f-b03-independent-instrumentation-audit.md](../t66f-b03-independent-instrumentation-audit.md)
- [t66f-b03-ir01-independent-reaudit-scope.md](../t66f-b03-ir01-independent-reaudit-scope.md)
- [t66f-b03-ir02-audit-candidate-freeze.md](../t66f-b03-ir02-audit-candidate-freeze.md)
- [t66f-b03-ir03-independent-correctness-reaudit.md](../t66f-b03-ir03-independent-correctness-reaudit.md)
- [t66f-b03-ir04-independent-final-reaudit.md](../t66f-b03-ir04-independent-final-reaudit.md)
- [t66f-b03-ir05-independent-correctness-closure.md](../t66f-b03-ir05-independent-correctness-closure.md)
- [t66f-b03-ir06-independent-lifecycle-closure.md](../t66f-b03-ir06-independent-lifecycle-closure.md)
- [t66f-b03-ir07-independent-pep669-closure.md](../t66f-b03-ir07-independent-pep669-closure.md)
- [t66f-b03-logical-cost-instrumentation.md](../t66f-b03-logical-cost-instrumentation.md)
- [t66f-b04-phase-b-measurement-feasibility.md](../t66f-b04-phase-b-measurement-feasibility.md)
- [t66f-b05-lookup-hot-body-decode-optimization.md](../t66f-b05-lookup-hot-body-decode-optimization.md)
- [t66f-b05a-engine-admission-real-flutter-ab.md](../t66f-b05a-engine-admission-real-flutter-ab.md)
- [t66f-b05b-independent-5k-on-ab-replication.md](../t66f-b05b-independent-5k-on-ab-replication.md)
- [t66f-b06-cold-acquisition-critical-path-analysis.md](../t66f-b06-cold-acquisition-critical-path-analysis.md)
- [t66f-b07-bounded-connect-schema-attribution.md](../t66f-b07-bounded-connect-schema-attribution.md)
- [t66f-b08-expected-revision-contract-reuse.md](../t66f-b08-expected-revision-contract-reuse.md)
- [t66f-b09-engine-admission-real-flutter-cold-ab.md](../t66f-b09-engine-admission-real-flutter-cold-ab.md)
- [t66f-b10-independent-phase-b-closure-adjudication.md](../t66f-b10-independent-phase-b-closure-adjudication.md)
- [t66f-b11-applied-amendment-independent-consistency-review.md](../t66f-b11-applied-amendment-independent-consistency-review.md)
- [t66f-b11-approval-preflight.md](../t66f-b11-approval-preflight.md)
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

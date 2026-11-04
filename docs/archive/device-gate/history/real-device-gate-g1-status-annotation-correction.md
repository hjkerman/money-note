# G1 canonical 상태 주석 정정

**완료 — 승인된 한 줄 삽입, 독립 검증 PASS·차단 지적 0개.** [계약 문서](../../../real-device-gate-g1-safety-contract.md)의 기존 5행 바로 앞에 승인 문장과 LF 하나만 삽입했다. 삽입분은 348바이트·1행이고, 제거하면 원문 21,639바이트가 정확히 복원된다.

| 신원 | SHA-256 |
| --- | --- |
| 원본 | `967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e` |
| 수정본 | `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0` |

정확한 최소 diff는 다음과 같다. [diff 파일](../../../benchmarks/real-device-gate-g1-status-annotation/annotation.diff)과 [보존 원본](../../../benchmarks/real-device-gate-g1-status-annotation/original-before.md)도 남겼다.

```diff
--- a/docs/real-device-gate-g1-safety-contract.md
+++ b/docs/real-device-gate-g1-safety-contract.md
@@ -4,0 +5 @@
+규범 상태 주석: 제목·도입부, G1-12 마지막 문장 및 S6의 ‘현재 이 적용 승인은 없다’는 후보 작성 당시의 상태·결정을 기록한 것이며, 현행 보충 규범 효력은 docs/benchmarks/real-device-gate-g1-n3-application/completion-record.json의 G1-N3-N4-N5-DOCUMENT-APPLICATION-COMPLETE-01에 따른다.
```

참조한 완료 사건 `G1-N3-N4-N5-DOCUMENT-APPLICATION-COMPLETE-01`과 N3/N5 지원 기록·해시는 수정 전에 확인했고 그대로 보존했다. 이전 hash는 당시 문서의 역사 신원이며 현재 hash로 덮어쓰지 않았다. [현재 신원 연결](../../../benchmarks/real-device-gate-g1-status-annotation/current-canonical-identity.json)에 두 시점을 구별했다.

수정에 참여하지 않은 별도 `fork_turns=none` 검토 agent가 문서 검사 50개와 마무리 안정성 확인을 통과시켰다. 같은 orchestration 안의 비참여 검토이며 외부 인간 검토로 주장하지 않는다. [독립 보고서](real-device-gate-g1-status-annotation-independent-review.md)와 [판정 JSON](../../../benchmarks/real-device-gate-g1-status-annotation-review/result.json)을 확인한 뒤 [완료 기록](../../../benchmarks/real-device-gate-g1-status-annotation/correction-completion.json)을 발급했다. 원 저자의 PENDING 사건은 역사로 유지했다.

모든 규범 요구, 12개 조항·12개 증명 의무·14개 거부 기준·세 비면제 보호는 변경되지 않았다. 원 F01은 구속·미해결, 기술 증명 수용은 0/12, 운영 dispatch는 CLOSED/BLOCKED다. 기준선 8,110개 경로에서 승인된 대상 삽입 외의 원본·source locks·HEAD·Git index·staged 항목과 외부 sidecar 5개를 보존했다. 범위 밖 protocol·B03·제품·기기·ADB·빌드/시험·production 작업은 없고, 커밋·푸시·기존 자료 삭제도 없다.

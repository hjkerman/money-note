"""규범의 절·invariant·proof·negative 계획을 누락 없이 후속 증거에 연결한다."""

import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
protocol = (ROOT / "docs/t66/c/t66c-delta-sync-protocol.md").read_text()
initial = json.loads((HERE / "coverage-initial.json").read_text())
prior = "docs/t66f-phase-b-independent-verification.md"
new = "docs/t66f-phase-b-continuation.md"
labels = {
    "A": "INDEPENDENTLY VERIFIED — VALID EVIDENCE",
    "B": "INDEPENDENTLY VERIFIED — REGRESSION REQUIRED",
    "C": "UNVERIFIED — MANDATORY FOR CURRENT F",
    "D": "EXPLICITLY DEFERRED TO R1",
    "E": "ENVIRONMENT/DEVICE-DEPENDENT",
    "F": "CONTRACT AMBIGUITY OR CONFLICT",
}


def row(ident, text, status, evidence, limit="", owner="독립 F 감사"):
    old = (
        "INCONCLUSIVE"
        if ident in ["I25", "S30", "S34", "S35", "S38", "P8", "P9", "P10", "P11", "P12"]
        else "DEFERRED / 상위 exit INCONCLUSIVE"
        if ident in ["I23", "S31", "S33", "N31", "N32"]
        else "부분 PASS / 새 실제 HTTP 전수 coverage는 INCONCLUSIVE"
        if ident in ["I14", "S25", "S37"]
        else "해당 원 감사의 PASS 범위를 이월; 별도 새 주입은 미실행"
    )
    action = (
        "관찰한 범위에 새 필수 조치 없음; 유한 증거와 이전 감사 가정을 유지한다."
        if status == "A"
        else "필수 미완료 규모/metric proof를 독립 검증한다. 지원 한도나 규범을 감사 중 변경하지 않는다."
        if status == "C"
        else "명시 R1/transition 구현 및 독립 audit에서 검증한다."
        if status == "D"
        else "승인된 실제 Android/VFS/I/O/power-loss 환경에서 해당 proof를 확보한다."
        if status == "E"
        else "기록한 회귀 또는 규범 문제를 해결한 뒤 별도 판정한다."
    )
    return dict(
        id=ident,
        requirement=text,
        status=status,
        classification=labels[status],
        original_status=old,
        prior_evidence=prior,
        new_evidence=evidence,
        audited_product="af9525e20e6df1dd7dfc152d3db79c1eb07925d2",
        evidence_still_applicable=True,
        limitation=limit,
        owner=owner,
        remaining_action=action,
        final_acceptance="해당 규범 의무에 맞는 증거; 하위/기존 PASS를 전체 F PASS로 확장하지 않음",
    )


sections = []
for old in initial["sections"]:
    n = int(re.search(r"## (\d+)\.", old["section"]).group(1))
    status = (
        "D"
        if n in [31, 33]
        else "E"
        if n == 26
        else "C"
        if n in [30, 34, 35, 38]
        else "A"
    )
    reason = (
        "R1/transition 소유 부분은 미구현이며 기존 legacy 불변 증거와 구분한다."
        if status == "D"
        else "HOST pragmas/SIGKILL 증거가 actual Android VFS/I/O/power-loss proof를 대신하지 않는다."
        if status == "E"
        else "5개 backend grid/압축은 실행했으나 E2 hard cap으로 50k/100k 전체 D→E와 완전한 hash/write/resource accounting은 미완료다."
        if status == "C"
        else "원 독립 감사의 해당 범위 + product/history SHA 불변 + 최종 전체 회귀. 유한 사례를 모든 schedule/입력에 대한 증명으로 확대하지 않는다."
    )
    sections.append(row("S" + str(n), old["section"], status, new, reason))

invariants = []
for line in protocol.splitlines():
    m = re.match(r"\| (I\d+) (.*?) \|", line)
    if not m:
        continue
    ident, text = m.groups()
    status = "D" if ident == "I23" else "C" if ident == "I25" else "A"
    evidence = (
        "evidence/grid-summary.json; evidence/cost-summary.json; evidence/budget-50000.json"
        if ident == "I25"
        else "evidence/cases.json; evidence/checks-summary.json; " + prior
    )
    limit = (
        "지원 가능한 세 N에서 정상 반복의 독립 SQL/object 비용은 bounded다. 두 큰 N 및 전층 논리 bytes hashed/validated/written은 미검증이다. physical I/O/pure peak는 추가 관찰 한계이며 새 F 필수 threshold가 아니다."
        if ident == "I25"
        else "§31/R1 chunk/MW/apply/receipt의 소유와 전체 F dependency를 유지한다."
        if ident == "I23"
        else "기존 독립 oracle와 새 보완 사례를 구별한다. I17의 HOST crash와 Android proof는 별개 행이다."
    )
    invariants.append(
        row(
            ident,
            text,
            status,
            evidence,
            limit,
            "R1" if status == "D" else "독립 F 감사",
        )
    )

proofs = []
part = protocol.split("## 38.")[1].split("## 39.")[0]
for n, text in re.findall(r"^([0-9]+)\. (.+)$", part, re.M):
    status = (
        "E"
        if n == "8"
        else "D"
        if n == "10"
        else "C"
        if n in ["9", "11", "12"]
        else "A"
    )
    detail = {
        "8": "actual Android driver/VFS/I/O/power-loss 미확보; §26 rollout 차단",
        "9": "v7/v4/B/J 및 E4 materialization은 검증됨. migration/rollback은 R1 소유로 미완료",
        "10": "R1 별도 소유. 대형 chunk restore/MW 증명 미완료",
        "11": "기존 standalone backup 의미는 불변. 전체 R1 artifact/storage/exhaustion proof는 미완료",
        "12": "backend 전체 grid/오프라인 압축 완료. 전체 D→E 큰 N·일부 자원 계측과 실기기 post-T6.6 gate는 분리",
    }
    proofs.append(
        row(
            "P" + n,
            text,
            status,
            new,
            detail.get(n, "기존 독립 감사 및 최종 전체 회귀의 해당 범위를 이월한다."),
        )
    )

negative = []
part = protocol.split("## 37.")[1].split("## 38.")[0]
for line in part.splitlines():
    m = re.match(r"\| (\d+) \| (.*?) \| (.*?) \|", line)
    if not m:
        continue
    n, trigger, expect = m.groups()
    num = int(n)
    if num in [31, 32]:
        status = "D"
        evidence = "§31/33 R1/transition; 현재 legacy regression"
        limit = "R1 미구현을 F 제품 defect로 분류하지 않는다. 전체 F dependency에서는 미충족이다."
    else:
        status = "A"
        limit = "이 행은 새 독립 주입 횟수를 뜻하지 않는다. 기존 독립 oracle, 해당 기존 회귀 및 새 보완 증거의 범위를 이월한다."
        if num in [1, 2, 3, 4, 5, 6, 7, 18, 20, 21, 22, 33]:
            evidence = "evidence/cases.json; 원 Phase B integration/e2/backend evidence; E1/E2/E3 독립 audit"
        elif num in [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19]:
            evidence = "D1/D2 implementation 증거와 기존 E1/E3 독립 audit를 구분함; backend/tests/test_isolated_sync_segments·patricia·capture/finalization 및 mobile segmented_fetch/publication 전체 회귀"
        elif num in [23, 24, 25, 26, 27, 28, 29, 30]:
            evidence = "원 Phase B 실제 crash 7개 및 E3/E4 independent audit·A01/RA01; 최종 Flutter 회귀"
        else:
            evidence = (
                "legacy endpoint/full bundle 기존 독립 비교 및 backend full regression"
            )
    negative.append(
        row(
            "N" + n,
            trigger + " → " + expect,
            status,
            evidence,
            limit,
            "R1" if status == "D" else "독립 F 감사",
        )
    )

result = dict(
    starting_commit=initial["starting_commit"],
    categories=labels,
    sections=sections,
    invariants=invariants,
    implementation_proofs=proofs,
    negative_plan=negative,
    counts=dict(
        sections=len(sections),
        invariants=len(invariants),
        proofs=len(proofs),
        negative=len(negative),
    ),
    no_new_contract_threshold=True,
    phase_b_verdict="INCONCLUSIVE",
    full_t66f_complete=False,
    mandatory_unverified=[
        "50k 전체 backend→Flutter transfer/publication/read 및 I25/storage/resource grid",
        "100k 전체 backend→Flutter transfer/publication/read 및 I25/storage/resource grid",
        "전체 정상 경로 논리 bytes hashed/validated/written의 독립 accounting",
    ],
    device_unavailable=["actual Android VFS/pragmas/I/O/power-loss proof"],
    r1_deferred=[
        "Large Restore/MW",
        "chunk/hash/bounded staging",
        "backup/artifacts/retention",
        "atomic apply/receipt",
        "migration/rollback",
    ],
)
assert result["counts"] == dict(sections=39, invariants=25, proofs=12, negative=34)
(HERE / "coverage-final.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)

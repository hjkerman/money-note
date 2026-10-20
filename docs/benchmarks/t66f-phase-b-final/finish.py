"""실제 회귀 완료 자료를 읽고 최종 보고서를 갱신한다. Git commit은 수행하지 않는다."""

import gzip
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
REPORT = ROOT / "docs/t66f-phase-b-final-evidence-closure.md"


def load(path):
    return json.loads(path.read_text())


def main():
    modes = [
        "backend-full",
        "flutter-full",
        "frontend",
        "analyze",
        "build",
        "ruff",
        "compileall",
        "format",
    ]
    checks = {mode: load(OUT / (mode + ".json")) for mode in modes}
    checks["compileall"] = load(OUT / "compileall-final.json")
    assert all(
        r["status"] == "PASS" and r["exit"] == 0 and r["external_termination"] is None
        for r in checks.values()
    )
    backend_log = gzip.decompress((OUT / "backend-full.log.gz").read_bytes()).decode()
    tests = int(re.search(r"(\d+) passed", backend_log).group(1))
    subtests = int(re.search(r"(\d+) subtests passed", backend_log).group(1))
    backend_suite = ET.parse(OUT / "backend-full.xml").getroot().find("testsuite")
    assert int(backend_suite.attrib["tests"]) == tests + subtests
    assert all(
        int(backend_suite.attrib[k]) == 0 for k in ["failures", "errors", "skipped"]
    )
    flutter_log = gzip.decompress((OUT / "flutter-full.log.gz").read_bytes()).decode()
    events = []
    for line in flutter_log.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            events.append(value)
    completed = [
        e for e in events if e.get("type") == "testDone" and not e.get("hidden")
    ]
    passed = sum(e["result"] == "success" and not e["skipped"] for e in completed)
    failed = sum(e["result"] != "success" and not e["skipped"] for e in completed)
    skipped = sum(e["skipped"] for e in completed)
    assert failed == 0 and any(
        e.get("type") == "done" and e.get("success") for e in events
    )
    calibration = ET.parse(OUT / "calibration.xml").getroot().find("testsuite")
    assert all(
        int(calibration.attrib[k]) == 0 for k in ["failures", "errors", "skipped"]
    )
    calibration_count = int(calibration.attrib["tests"])
    definitions = {
        e["test"]["id"]: e["test"] for e in events if e.get("type") == "testStart"
    }
    suites = {
        e["suite"]["id"]: e["suite"]["path"] for e in events if e.get("type") == "suite"
    }
    by_file = {}
    for e in completed:
        path = suites[definitions[e["testID"]]["suiteID"]]
        record = by_file.setdefault(path, dict(passed=0, failed=0, skipped=0))
        key = (
            "skipped"
            if e["skipped"]
            else "passed"
            if e["result"] == "success"
            else "failed"
        )
        record[key] += 1
    (OUT / "flutter-by-file.json").write_text(json.dumps(by_file, indent=2) + "\n")
    inventory = load(HERE / "inventory.json")
    mismatches = [
        p
        for p, expected in inventory["files"].items()
        if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != expected
    ]
    assert not mismatches, mismatches
    summary = dict(
        full_backend=dict(tests=tests, subtests=subtests, failed=0),
        full_flutter=dict(passed=passed, failed=failed, skipped=skipped),
        calibration=dict(passed=calibration_count, failed=0),
        preserved_tracked_files=len(inventory["files"]),
        original_file_mismatches=mismatches,
        checks=checks,
        phase_b="INCONCLUSIVE",
        overall_f="NOT SATISFIED",
        newly_executed_large_cold_runs=0,
        independent_full_cost_grid_points=0,
    )
    (OUT / "checks-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    table = ["<!-- CHECKS -->", "|현재 실행|실제 결과|증거·경계|", "|---|---|---|"]
    table.append(
        f"|전체 backend|{tests} tests / {subtests} subtests PASS, exit 0|backend-full.xml·원문 log.gz; JUnit 합계를 main tests로 부풀리지 않음|"
    )
    table.append(
        f"|전체 Flutter|{passed} PASS / {failed} FAIL / {skipped} SKIP, done.success=true, exit 0|flutter-full.log.gz·flutter-by-file.json; hidden loading 제외|"
    )
    table.append(
        f"|새 calibration|{calibration_count} PASS / 0 FAIL|calibration.xml; §5의 subset만 보정|"
    )
    for mode, title in [
        ("frontend", "npm build"),
        ("analyze", "Flutter analyze"),
        ("build", "Flutter debug APK build"),
        ("ruff", "Ruff"),
        ("compileall", "compileall"),
        ("format", "새 Python formatting"),
    ]:
        table.append(f"|{title}|PASS / exit 0|evidence/{mode}.json 및 .log.gz|")
    table.extend(
        [
            "",
            "전체 suite는 E1/E2 cleanup·large profile/continuation, E3 I25/publication/crash, E4-A01/RA01,",
            "Frozen B/J·Snapshot v7·OfflineBaseline v4·AppState authority·source-SHA guards를 포함한다.",
            "각 file의 수는 flutter-by-file.json에 있고 전체 test 수에 다시 더하지 않는다. backend에는",
            "D1–D3c·prefix/C1·DB identity/permit 및 원 strict B01 test가 포함된다. 별도 audit calibration은",
            "backend full-suite count에 포함하지 않았다. debug APK는 build만 했으며 설치하지 않았다.",
            "최종 product/history SHA 2251개가 모두 같았다. git diff --check와 staged allowlist는 commit 직전",
            "별도 검사한다. 새 Dart source는 없어 changed-file Dart format 대상은 없다.",
            "<!-- END CHECKS -->",
        ]
    )
    text = REPORT.read_text()
    text = re.sub(
        r"<!-- CHECKS -->.*?<!-- END CHECKS -->", "\n".join(table), text, flags=re.S
    )
    footer = f"""<!-- FOOTER -->
아래 calibration PASS는 §5의 소형 Python 경계에 한정된다. 전층 byte 증거와 전체 비용은 PARTIAL/INCONCLUSIVE다.
기능 PASS는 해당 이월 fixture 범위이며 Android·matched cost grid PASS가 아니다. 새 cost grid tests와 별도
independent cost cases는 미실행 0건이다. 소형 Store 관찰은 calibration의 부분집합으로 중복 합산하지 않는다.

```text
T6.6F PHASE B FINAL EVIDENCE CLOSURE:
INCONCLUSIVE

STARTING B02 AUDIT COMMIT:
ae0f37250c8f54893cb2ac5eab1d3c9844a7d983

AUDITED B02 PRODUCT COMMIT:
1cabf319f0ac2c2069e804b47cb527b55e3374db

FINAL AUDIT-ONLY COMMIT:
? — 이 문서를 추가한 commit; 본문 Git 식별 명령·최종 응답 참조

REPOSITORY STATE:
VERIFIED

PRODUCT SOURCE MODIFIED:
NO

BINDING PROTOCOL:
UNCHANGED

PHASE A:
PASS

B01:
CLOSED

B02:
CLOSED

PRIOR PHASE B EVIDENCE:
PRESERVED

COMPLETE F COVERAGE MATRIX:
INCONCLUSIVE

H DEFINITION:
hot/참조 working set와 required control/policy descriptor 크기

D DEFINITION:
base 이후 changed rows

N DEFINITION:
전체 역사 row; 기존 fixture label은 현재+과거 ledger N행, 고정 참조 35행 별도

MANDATORY N POINTS:
1000 / 5000 / 10000 / 50000 / 100000

REQUIRED N GRID POINTS:
5

VERIFIED N GRID POINTS:
0 — 현재 matched 전층 비용; 서로 다른 범위의 기능 witness는 5개 label에 존재

FIXED H/D:
NOT VERIFIED

FULL D-E GRID:
INCONCLUSIVE

COLD ACQUISITION:
PASS

IDENTICAL GENERATION:
PASS

ONE-ROW DELTA:
PASS

FIXED-D DELTA:
INCONCLUSIVE

LOGICAL HASH BYTE DEFINITION:
VERIFIED

LOGICAL VALIDATE BYTE DEFINITION:
VERIFIED

LOGICAL WRITE BYTE DEFINITION:
VERIFIED

HASH COUNTER CALIBRATION:
PASS

VALIDATE COUNTER CALIBRATION:
PASS

WRITE COUNTER CALIBRATION:
PASS

INDEPENDENT HASH BYTES:
PARTIAL

INDEPENDENT VALIDATE BYTES:
PARTIAL

INDEPENDENT WRITE BYTES:
PARTIAL

COUNTER OVERLAP:
DOCUMENTED

BACKEND LOGICAL COST:
INCONCLUSIVE

D3 TRANSFER COST:
INCONCLUSIVE

E1 STORAGE COST:
INCONCLUSIVE

E2 VALIDATION COST:
INCONCLUSIVE

E3 PUBLICATION COST:
INCONCLUSIVE

E4 READ COST:
INCONCLUSIVE

E3 I25:
INCONCLUSIVE

END-TO-END INCREMENTAL TRANSFER:
INCONCLUSIVE

END-TO-END INCREMENTAL STORAGE:
INCONCLUSIVE

END-TO-END RESOURCE BOUNDEDNESS:
INCONCLUSIVE

N=50K LARGE D-E:
PASS

N=100K LARGE D-E:
PASS

N=50K DELTA:
PASS

N=100K DELTA:
PASS

COMPRESSION:
PASS

MEDIAN:
INCONCLUSIVE

P95:
INCONCLUSIVE

MEASUREMENT ENVIRONMENT:
DOCUMENTED

INDEPENDENT FINANCIAL EQUIVALENCE:
PASS

RAW MONETARY STRINGS:
PRESERVED

CANONICAL GRAPH:
PASS

CROSS-LAYER AUTHORITY:
PASS

PROTOCOL NEGATIVE:
PASS

BACKEND DATABASE IDENTITY:
PASS

CROSS-STORE CRASH CONSISTENCY:
PASS

FRESH-PROCESS RECOVERY:
PASS

FROZEN B/J:
PRESERVED

IMPLICIT B/J ACK:
NONE

AUTOMATIC B/J REBASE:
NONE

E4-A01:
CLOSED

E4-RA01:
CLOSED

SNAPSHOT V7:
PRESERVED

OFFLINE BASELINE V4:
PRESERVED

SYNC_ROOT / V7 FINGERPRINT:
SEPARATED

NEW COST CALIBRATION TESTS:
{calibration_count} PASS
0 FAIL

NEW COST GRID TESTS:
0 PASS
0 FAIL
0 INCONCLUSIVE — 계측 seam 부재로 새 grid test 미실행; 5개 의무 gate는 INCONCLUSIVE

NEW INDEPENDENT COST CASES:
0 PASS
0 FAIL
0 INCONCLUSIVE — 소형 관찰은 calibration 부분집합이며 별도 case로 재합산하지 않음

FULL BACKEND:
{tests} TESTS
{subtests} SUBTESTS
PASS

FULL FLUTTER:
{passed} PASS
{failed} FAIL
{skipped} SKIP

FLUTTER ANALYZE:
PASS

FLUTTER BUILD:
PASS

RUFF:
PASS

COMPILEALL:
PASS

CHANGED-FILE FORMATTING:
PASS

GIT DIFF CHECK:
PASS

MANDATORY F EVIDENCE MISSING:
현재 D1–E4 전층 hash/validation/logical-write bytes; 동일 H/D 5-point no-change/card/cash의
전체 I25·storage/resource 비용·median/p95. 상위 Android VFS/I/O·power proof와 §34 R1 dependency 별도 미충족.

PRODUCTION INSTRUMENTATION REQUIRED:
YES — 현재 확인한 지원 seam 기준; 이 감사에서는 미적용

INSTRUMENTATION CORRECTION SCOPE:
mobile/lib/src/segmented/c1.dart; mobile/lib/src/segmented/store.dart;
typed validation·허용 E4 legacy hash의 추가 경계는 별도 최소 설계 검토

ANDROID VFS/I-O:
REQUIRED BUT MISSING

HARDWARE POWER LOSS:
REQUIRED BUT MISSING

ANDROID MEMORY SAFETY:
NOT VERIFIED

DEVICE PERFORMANCE:
DEFERRED

R1 LARGE RESTORE:
DEFERRED

R1 MIGRATION/ROLLBACK:
DEFERRED

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
0

NEW LOW:
0

UNRESOLVED PHASE B BLOCKERS:
2 — 전층 논리 byte 계측; 현재 matched 전체 workload/비용 grid

PHASE B FINAL VERDICT:
INCONCLUSIVE

BINDING T6.6F EXIT CRITERIA:
NOT SATISFIED

SAFE TO DECLARE T6.6F COMPLETE:
NO

SAFE TO START R1:
NO — SUBJECT TO BINDING PREREQUISITES

R1 ACTIVATION GATE:
CLOSED

GENERAL-USER SEGMENTED OFFLINE:
NOT ACTIVATED

PRODUCTION SEGMENTED ACTIVATION:
NOT PERFORMED

SAFE TO DEPLOY:
NO

FINAL VERDICT:
INCONCLUSIVE — T6.6F PHASE B MANDATORY EVIDENCE STILL MISSING

NEXT ACTION:
별도 구현 세션에서 최소 hash/validation·SQLite 관측 seam을 검토한 뒤 독립 고정 H/D 비용 검증을 재개한다.
```
<!-- END FOOTER -->"""
    text = re.sub(
        r"<!-- FOOTER -->.*?<!-- END FOOTER -->", lambda _: footer, text, flags=re.S
    )
    REPORT.write_text(text)
    print(
        json.dumps(
            dict(
                backend_tests=tests,
                backend_subtests=subtests,
                flutter_passed=passed,
                flutter_skipped=skipped,
                original_mismatches=0,
                phase_b="INCONCLUSIVE",
            )
        )
    )


if __name__ == "__main__":
    main()

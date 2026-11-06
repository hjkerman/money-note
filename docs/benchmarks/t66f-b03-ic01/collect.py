"""최종 실제 exit/JUnit/machine과 aggregate를 합친다. 미완료를 PASS로 바꾸지 않는다."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
ROOT = HERE.parents[2]


def machine(path):
    counts = Counter()
    files = {}
    tests = {}
    suites = {}
    done = None
    errors = []
    lines = (
        gzip.open(path, "rt").read() if path.suffix == ".gz" else path.read_text()
    ).splitlines()
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        kind = e.get("type")
        if kind == "suite":
            suites[e["suite"]["id"]] = e["suite"]["path"]
        elif kind == "testStart":
            tests[e["test"]["id"]] = e["test"]
        elif kind == "done":
            done = e["success"]
        elif kind == "error":
            errors.append(e["error"])
        elif kind == "testDone" and not e.get("hidden"):
            status = (
                "SKIP"
                if e["skipped"]
                else ("PASS" if e["result"] == "success" else "FAIL")
            )
            counts[status] += 1
            test = tests.get(e["testID"], {})
            filename = suites.get(test.get("suiteID"), "unknown")
            files.setdefault(filename, Counter())[status] += 1
    return {"counts": dict(counts), "done": done, "errors": errors, "files": files}


def main():
    checks = {}
    for name in [
        "backend-sealed",
        "flutter-sealed",
        "independent-http",
        "authority",
        "overhead-flutter",
        "high-n-sample",
        "high-n-sample-final",
        "flutter-current-11",
        "historical-final",
        "analyze",
        "build",
    ]:
        path = OUT / (name + ".json")
        checks[name] = (
            json.loads(path.read_text()) if path.exists() else {"status": "NOT RUN"}
        )
        checks[name].pop("rss_samples", None)
    parts = []
    total = Counter()
    for i in range(3):
        # The original part-1 command used a Flutter-unsupported filter. Keep
        # its exit64 evidence; the equivalent corrected current-11 run follows
        # the identical sealed source. No historical assertion was relaxed.
        path = (
            OUT / "flutter-current-11.log.gz"
            if i == 1
            else (
                OUT / "historical-final.log.gz"
                if i == 2
                else OUT / f"sealed-flutter-full-part-{i}.jsonl"
            )
        )
        if path.exists():
            part = machine(path)
            part["evidence"] = path.name
            parts.append(part)
            total.update(part["counts"])
    reconciled = (
        len(parts) == 3
        and all(p["done"] is True and not p["errors"] for p in parts)
        and not total.get("FAIL")
        and checks["flutter-current-11"].get("exit") == 0
    )
    backend = {}
    path = OUT / "backend-sealed.xml"
    if path.exists():
        tree = ET.parse(path)
        backend = {
            tag: len(list(tree.iter(tag)))
            for tag in ["testcase", "failure", "error", "skipped"]
        }
        backend["classes"] = dict(
            Counter(x.get("classname") for x in tree.iter("testcase"))
        )
    archive = json.loads((HERE / "historical/manifest.json").read_text())
    historical_exact = {
        name: hashlib.sha256((HERE / "historical" / name).read_bytes()).hexdigest()
        == sha
        for name, sha in [(Path(p).name, v) for p, v in archive["files"].items()]
    }
    result = {
        "schema_version": 1,
        "instrumentation_version": "t66f-b03-ic01/1",
        "environment": {
            "host": platform.platform(),
            "python": sys.version,
            "sqlite": sqlite3.sqlite_version,
        },
        "original_findings": json.loads(
            (HERE.parent / "t66f-b03-independent/findings.json").read_text()
        ),
        "reproductions": json.loads((OUT / "reproductions.json").read_text()),
        "checks": checks,
        "backend": backend,
        "flutter": {
            "parts": parts,
            "counts": dict(total),
            "complete_unweakened_suite": "PASS" if reconciled else "INCOMPLETE",
            "runner_filter_error_preserved": "flutter-sealed.json exit1 / part-1 exit64",
        },
        "historical_exact": historical_exact,
        "new_tests": {
            "backend": 26,
            "flutter": 18,
            "high_n_e1_sample": 1,
            "note": "실제 JUnit/machine의 파일별 결과와 교차 확인. 재실행·역사 재현·원 probe를 신규로 합산하지 않음",
        },
        "original_test_accounting": {
            "b03_implementation": {"PASS": 75, "FAIL": 0},
            "independent_audit": {"PASS": 35, "FAIL": 0},
            "independent_current_behavior": 28,
            "independent_historical_defect_existence": 7,
            "note": "사용자 승인 분리. 역사 7 PASS는 현재 counter 정확성 proof가 아님",
        },
        "counter_overlap": "hash/validation/write는 별개 연산. 합쳐 unique data bytes라고 하지 않음",
        "measurement_coverage": {
            "supported": "실제 D→E의 고정 schema 및 명시 지원 SQL; native SHA/C1 span/TEXT-BLOB NEW row/file 입력",
            "exclusions": [
                "정확한 실패 parser 소비 prefix",
                "scalar SQLite record encoding",
                "physical I/O/WAL durability",
                "opaque TLS/PBKDF2 내부",
                "arbitrary raw cursor/executescript/native handle",
                "미지원 schema FAIL 및 Dart 다중 DML",
            ],
            "full_five_point_grid": "DEFERRED",
            "instrumented_100k_lease": "INCONCLUSIVE; 실제 high-N E1 표본에서 상당한 overhead. full HTTP/관측별 완료 검증 필요",
        },
        "verdict": "INCOMPLETE — 100k 활성 계측의 관측별 완료 가능성 미확정. 7개 교정의 구현 회귀와 독립 closure는 별개",
    }
    for name in [
        "overhead-independent-python-complete",
        "overhead-independent-flutter-complete",
        "high-n-sample-result",
        "independent-real-http",
        "independent-tls-concurrency",
    ]:
        p = OUT / (name + ".json")
        if p.exists():
            result[name] = json.loads(p.read_text())
    p = HERE / "sealed-overhead/evidence/overhead-independent-python-complete.json"
    if p.exists():
        result["sealed_python_overhead"] = json.loads(p.read_text())
    for name in ["performance-summary", "final-state"]:
        p = OUT / (name + ".json")
        if p.exists():
            result[name] = json.loads(p.read_text())
    (OUT / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    # Completed part traces remain independently reproducible but bounded in Git.
    for p in OUT.glob("sealed-flutter-full-part-*.jsonl"):
        part = machine(p)
        if part["done"] is not None:
            with gzip.open(str(p) + ".gz", "wb") as f:
                f.write(p.read_bytes())
    print(
        json.dumps(
            {
                "backend": {k: v for k, v in backend.items() if k != "classes"},
                "flutter": dict(total),
                "checks": {k: v["status"] for k, v in checks.items()},
            }
        )
    )


if __name__ == "__main__":
    main()

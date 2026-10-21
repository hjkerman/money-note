"""독립 machine/JUnit/primitive evidence로 최종 숫자를 재생성한다."""

from collections import Counter
import gzip
import json
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"


def read(name):
    return json.loads((OUT / name).read_text())


def flutter(name):
    text = gzip.decompress((OUT / (name + ".log.gz")).read_bytes()).decode()
    suites, tests, counts, files = {}, {}, Counter(), {}
    errors, skipped, done = [], [], None
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "suite":
            suites[event["suite"]["id"]] = event["suite"]["path"]
        if kind == "testStart":
            tests[event["test"]["id"]] = event["test"]
        if kind == "error":
            errors.append(event["error"])
        if kind == "done":
            done = event["success"]
        if kind != "testDone" or event.get("hidden"):
            continue
        status = (
            "SKIP"
            if event["skipped"]
            else "PASS"
            if event["result"] == "success"
            else "FAIL"
        )
        counts[status] += 1
        test = tests[event["testID"]]
        path = suites[test["suiteID"]]
        files.setdefault(path, Counter())[status] += 1
        if status == "SKIP":
            skipped.append(test["name"])
    return dict(
        counts=dict(counts), done=done, errors=errors, files=files, skipped=skipped
    )


def junit(name):
    tree = ET.parse(OUT / name)
    classes = Counter(case.get("classname") for case in tree.iter("testcase"))
    return dict(
        classes=dict(classes),
        **{
            tag: len(list(tree.iter(tag)))
            for tag in ["testcase", "failure", "error", "skipped"]
        },
    )


def main():
    modes = [
        "backend-calibration",
        "flutter-independent",
        "backend-full",
        "flutter-full",
        "flutter-calibration",
        "independent-http-serial",
        "authority",
        "analyze",
        "build",
        "frontend",
        "overhead-python-complete",
        "overhead-flutter-complete",
        "ruff-final",
        "compileall-final",
        "python-format",
        "dart-format",
        "probe-analyze",
        "diff-check",
    ]
    checks = {mode: read(mode + ".json") for mode in modes}
    assert all(
        v["status"] == "PASS" and v["exit"] == 0 and v["external_termination"] is None
        for v in checks.values()
    )
    runs = {
        mode: flutter(mode)
        for mode in [
            "flutter-independent",
            "flutter-full",
            "flutter-calibration",
            "independent-http-serial",
            "authority",
            "overhead-flutter-complete",
        ]
    }
    assert all(
        v["done"] and not v["errors"] and not v["counts"].get("FAIL")
        for v in runs.values()
    )
    backend = junit("backend-full.xml")
    assert backend["failure"] == backend["error"] == backend["skipped"] == 0
    overhead = read("overhead-independent-flutter-complete.json")
    for row in overhead["results"].values():
        row["summary"] = {}
        for enabled, values in row["samples"].items():
            row["summary"][enabled] = {
                key: dict(
                    median=statistics.median(v[key] for v in values),
                    p95=sorted(v[key] for v in values)[18],
                )
                for key in values[0]
            }
    costs = read("independent-real-http.json")
    frozen = read("fresh-frozen.json")
    findings = json.loads((HERE / "findings.json").read_text())
    original_backend = junit("backend-calibration.xml")["classes"]
    original_python = sum(
        v
        for k, v in original_backend.items()
        if k.endswith("test_logical_cost_instrumentation")
    )
    original_dart = sum(
        v.get("PASS", 0)
        for k, v in runs["flutter-full"]["files"].items()
        if "/segmented_logical_cost" in k and "independent_audit" not in k
    )
    original_authority = runs["authority"]["counts"]["PASS"]
    independent_python = sum(
        v
        for k, v in original_backend.items()
        if k.endswith("test_logical_cost_independent_audit")
    )
    independent_dart = runs["flutter-independent"]["counts"]["PASS"]
    independent_http = runs["independent-http-serial"]["counts"]["PASS"]
    independent_overhead = runs["overhead-flutter-complete"]["counts"]["PASS"]
    result = dict(
        verdict="FAIL — T6.6F-B03 INSTRUMENTATION CORRECTION REQUIRED",
        original_b03=dict(
            backend=original_python,
            flutter=original_dart,
            authority=original_authority,
            total=original_python + original_dart + original_authority,
        ),
        new_independent=dict(
            backend=independent_python,
            flutter=independent_dart,
            http=independent_http,
            overhead=independent_overhead,
            total=independent_python
            + independent_dart
            + independent_http
            + independent_overhead,
            note="결함 재현 시험의 PASS는 counter correctness PASS가 아니다. 직접 실험3종은 pytest 수에 더하지 않음",
        ),
        backend=backend,
        backend_calibration=junit("backend-calibration.xml"),
        flutter_runs=runs,
        checks={
            k: {a: b for a, b in v.items() if a not in {"rss_samples", "pid"}}
            for k, v in checks.items()
        },
        python_overhead=read("overhead-independent-python-complete.json"),
        flutter_overhead=overhead,
        real_http=dict(
            independent_bounds=costs["independent_bounds"],
            modes={
                mode: {
                    "cold_wall_us": costs[mode]["cold_wall_us"],
                    "root": costs[mode]["durable"]["root"],
                    "http_requests": len(costs[mode + "_http"]["records"]),
                    "request_entity_bytes": sum(
                        v["request_bytes"] for v in costs[mode + "_http"]["records"]
                    ),
                    "response_entity_bytes": sum(
                        v["response_bytes"] for v in costs[mode + "_http"]["records"]
                    ),
                }
                for mode in ["disabled", "enabled"]
            },
        ),
        frozen=dict(
            healthy_work=frozen["healthy_read_work"],
            lineage={
                k: v for k, v in frozen["primitive"].items() if "lineageHash" in k
            },
        ),
        findings_by_severity=dict(Counter(v["severity"] for v in findings)),
        blockers=len(findings),
        preserved_original_files=len(read("inventory.json")["original_files"]),
        limits=[
            "N grid 미실행",
            "100k enabled lease perturbation 미검증",
            "Flutter CPU는 coarse process ticks, VM allocations 미측정",
            "HOST RSS는 Android memory/VFS/power proof가 아님",
            "R1/activation/deployment 미수행",
        ],
        preserved_failed_attempts=[
            "independent-http: 동시 Flutter native-assets 충돌",
            "overhead-python: 독립 fixture의 kind 누락; benchmark fixture만 교정",
        ],
    )
    (OUT / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "original_b03",
                    "new_independent",
                    "findings_by_severity",
                    "blockers",
                ]
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

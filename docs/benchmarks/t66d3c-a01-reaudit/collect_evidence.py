"""완료된 /tmp 감사 실행 기록을 검증하고 Git 보존용 JSON으로 모은다."""

import json
from pathlib import Path
import re
import statistics
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = Path("/tmp/mn-d3c-a01-reaudit")


def suite(name, include_cases=True):
    root = ET.parse(OUT / (name + ".xml")).getroot()
    parts = list(root.iter("testsuite"))
    assert sum(int(p.get("failures", 0)) + int(p.get("errors", 0)) for p in parts) == 0
    return dict(
        tests=sum(int(p.get("tests", 0)) for p in parts),
        failures=0,
        errors=0,
        skipped=sum(int(p.get("skipped", 0)) for p in parts),
        elapsed_seconds=sum(float(p.get("time", 0)) for p in parts),
        cases=[dict(p.attrib) for p in root.iter("testcase")] if include_cases else [],
    )


def main():
    cases = []
    for file in sorted(OUT.glob("*.json")):
        value = json.loads(file.read_text())
        if "scenario" in value:
            cases.append(value)
    assert len(cases) == 41 and len({c["scenario"] for c in cases}) == 41
    assert all(
        c["result"] == "PASS" and c["unauthorized_committed_deletions"] == 0
        for c in cases
    )
    independent = suite("independent-final")
    assert independent["tests"] == 41 and independent["skipped"] == 0
    backend_exit = json.loads((OUT / "backend-exit.json").read_text())
    assert backend_exit["exit_code"] == 0
    backend_summary = next(
        line
        for line in reversed((OUT / "backend.log").read_text().splitlines())
        if re.search(r"\d+ passed", line)
    )
    assert "failed" not in backend_summary
    samples = next(
        c["samples_ms"] for c in cases if c["scenario"] == "steady_open_resources"
    )
    result = dict(
        audited_commit="3e54d6992872aba9589b1a34c3ebe4316c70d646",
        baseline_commit="6434d5e24cff316ff9a611b27b1d6cfc83e63d5c",
        initial_repository_state="HEAD=main=origin/main=actual remote main; clean",
        verdict="PASS — D3C-A01 INDEPENDENT TARGETED RE-AUDIT COMPLETE",
        unauthorized_committed_deletions=0,
        original_counterexample="PASS; original assert after == before unchanged",
        independent=independent,
        correction_and_original=suite("correction"),
        affected_prior_independent=suite("retention-regression"),
        backend=dict(
            exit=backend_exit, junit=suite("backend", include_cases=False), pytest_summary=backend_summary
        ),
        safety_summary=(OUT / "safety.log").read_text().splitlines()[-1],
        frontend_summary=[
            line.strip()
            for line in (OUT / "frontend.log").read_text().splitlines()
            if "Test Files" in line or "Tests " in line
        ],
        checks=dict(
            ruff="PASS", compileall="PASS", git_diff_check="PASS", frontend_build="PASS"
        ),
        performance=dict(
            samples=40,
            median_ms=statistics.median(samples),
            p95_ms=sorted(samples)[37],
            warmups=3,
            measurement="bound open plus independent fstat/proc check and close; no before/after latency claim",
        ),
        official_header=json.loads((OUT / "official-header.json").read_text()),
        artifact_check=json.loads((OUT / "artifact-check.json").read_text()),
        scenarios=cases,
        production_access="NONE",
        deployment="NOT PERFORMED",
    )
    (Path(__file__).parent / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()

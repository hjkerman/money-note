"""실제 실행·독립 관측·미해결 gate를 구분하여 감사 증거를 수집한다."""

from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def machine(path):
    if not path.exists():
        return {"state": "NOT_RUN"}
    names, suites, cases, errors = {}, {}, [], []
    files = defaultdict(Counter)
    done = None
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "suite":
            suites[event["suite"]["id"]] = event["suite"]["path"]
        elif kind == "testStart":
            names[event["test"]["id"]] = event["test"]
        elif kind == "testDone" and not event.get("hidden"):
            test = names.get(event["testID"], {})
            result = (
                "SKIP"
                if event.get("skipped")
                else "PASS"
                if event["result"] == "success"
                else "FAIL"
            )
            file = Path(suites.get(test.get("suiteID"), "?")).name
            cases.append({"name": test.get("name"), "file": file, "result": result})
            files[file][result] += 1
        elif kind == "error":
            errors.append(
                {
                    "name": names.get(event.get("testID"), {}).get("name"),
                    "error": str(event.get("error"))[:2400],
                }
            )
        elif kind == "done":
            done = event["success"]
    return {
        "counts": dict(Counter(c["result"] for c in cases)),
        "done_success": done,
        "files": dict(files),
        "cases": cases,
        "errors": errors,
        "log_sha256": sha(path),
    }


def junit(path):
    if not path.exists():
        return {"state": "NOT_RUN"}
    root = ET.parse(path).getroot()
    suites = list(root) if root.tag == "testsuites" else [root]
    cases = []
    failures = []
    for suite in suites:
        for test in suite.findall("testcase"):
            failure = test.find("failure")
            error = test.find("error")
            bad = failure if failure is not None else error
            result = (
                "FAIL"
                if bad is not None
                else "SKIP"
                if test.find("skipped") is not None
                else "PASS"
            )
            cases.append({"name": test.get("name"), "result": result})
            if bad is not None:
                failures.append(
                    {"name": test.get("name"), "evidence": (bad.text or "")[:8000]}
                )
    return {
        **{
            k: sum(int(s.get(k, 0)) for s in suites)
            for k in ["tests", "failures", "errors", "skipped"]
        },
        "seconds": sum(float(s.get("time", 0)) for s in suites),
        "cases": cases,
        "failure_evidence": failures,
        "xml_sha256": sha(path),
    }


EXPECTED = {
    "FB01": "실제 G1–G7의 complete graph/금융 bytes 일치, 동일 generation 객체 요청 0, delta 요청은 target closure에서 cache를 뺀 집합",
    "FB02": "backend v7 identity와 legacy 설치 lineage 일치, unknown pending 원문 보존, fresh process Frozen read 성공",
    "FB03": "G2 설치 이후 Frozen G1의 source/lineage/pins/값 보존",
    "FB04": "미설치 target의 필수 predecessor 누락을 거부하고 기존 유효 Frozen source/pins/B/pending 보존",
    "FB05": "취소된 A의 delayed recovery 이후 B의 source/B/pending/pins와 fresh read 보존",
    "FB06": "4개 durable object 뒤 취소·재개 시 missing objects만 실제 재전송",
    "FB07": "G1 snapshot은 혼합되지 않으며 competing COMMIT은 scope 종료까지 거부, 이후 G2 read는 G2와 일치",
    "FB08": "P0 raw 원문과 local input admission 분리, R1 recovery gate 차단",
    "FB09": "6번 stalled-body header 거부 뒤 TCP 소유권 누적 없음, limit=1 같은 client의 C1/hash 검증 정상 요청 성공",
    "FB10": "empty financial tables도 모든 필수 certified root를 실제 HTTP로 완전 취득",
    "FB11-false": "전송 중 lease 만료 후 fresh same-generation observation으로 complete closure 취득",
    "FB11-true": "전송 중 lease 만료와 generation churn 후 fresh target으로 complete closure 취득",
    "FB12": "E3 COMMIT 직후 credential 교체는 기존 Frozen source를 변경하는 E4 설치를 차단",
    "FB13": "실제 capabilities 404/no-store, R1 지원 허위 광고 없음",
    "FB14": "principal 2의 실제 인증된 Target을 principal 1 cache/설치에 사용하지 못함",
    "FB15": "mandatory trigger 손실 시 실제 cached refresh도 fail closed, 기존 Frozen source 보존",
    "FB16": "object quota 실패 시 기존 source/pins/objects/B/pending 보존",
    "FB17": "server와 유사한 거래가 있어도 Frozen J의 두 UUID/sequence/payload/lineage 원문 보존, implicit ACK/rebase 없음",
    "FB18": "잘린 실제 HTTP object를 bounded retry하고 완전한 C1 bytes만 저장",
    "FB19": "명시 epoch bootstrap의 old lease 409/EPOCH_CHANGED, context 혼용 설치 거부, old Frozen source 보존",
}


def main(folder):
    out = Path(folder).resolve()
    records = json.loads((out / "integration-campaign.json").read_text())
    assert len(records) == 33 and len({r["id"] for r in records}) == 33
    assert len(json.loads((out / "cost-final/cost.json").read_text())) == 2
    for directory, count in [
        ("backend-independent", 5),
        ("crash-final", 4),
        ("http-concurrency", 2),
        ("generation-cost-final", 2),
    ]:
        assert len(list((out / directory).glob("*.json"))) == count, directory
    summary, all_cases = {}, {}
    logs = {
        "integration": "integration-campaign.log",
        "independent_cost": "cost-final/cost.log",
        "flutter_first": "flutter-full.log",
        "flutter_final": "flutter-rerun.log",
        "previous_targeted": "previous-targeted-dart.log",
        "phase_a_dart": "previous-regressions/phase-a-dart.log",
        "a01_concurrent": "previous-regressions/a01-concurrent.log",
        "p0_integration": "previous-regressions/p0-integration.log",
        "original_phase_a_cost": "original-phase-a-cost/cost.log",
        "previous_ra01_cost": "previous-ra01-cost/cost.log",
    }
    for name, file in logs.items():
        row = machine(out / file)
        all_cases[name] = row.pop("cases", [])
        summary[name] = row
    xmls = {
        "new_backend": "new-backend.xml",
        "new_crash": "new-crash-final.xml",
        "new_http_concurrency": "new-http-concurrency.xml",
        "new_generation_cost": "generation-cost-final.xml",
        "backend_first": "backend-full.xml",
        "backend_focused": "backend-focused.xml",
        "backend_final": "backend-rerun.xml",
        "backend_identity_original": "backend-identity-original.xml",
        "e2_independent": "e2-independent.xml",
        "scripts": "scripts.xml",
        **{
            name: "previous-regressions/" + file + ".xml"
            for name, file in [
                ("phase_a_crash", "phase-a-crash"),
                ("a01_crash", "a01-crash"),
                ("ra01_crash", "ra01-crash"),
                ("e2_cleanup", "e2-cleanup"),
                ("p0_replay", "p0-replay"),
            ]
        },
    }
    for name, file in xmls.items():
        row = junit(out / file)
        all_cases[name] = row.pop("cases", [])
        summary[name] = row
        if name in ["backend_first", "backend_final"]:
            text = (out / file.replace(".xml", ".log")).read_text()
            match = re.search(
                r"(\d+) failed, (\d+) passed.*?(\d+) subtests passed", text
            )
            if match:
                row["main_tests"] = {"FAIL": int(match[1]), "PASS": int(match[2])}
                row["subtests_passed"] = int(match[3])
            # JUnit includes subtests; do not call all 2,855 entries main tests.

    independent = []
    for suite in [
        "integration",
        "independent_cost",
        "new_backend",
        "new_crash",
        "new_http_concurrency",
        "new_generation_cost",
    ]:
        for case in all_cases[suite]:
            name = case["name"]
            ident = (
                name.split()[0]
                if suite in ["integration", "independent_cost"]
                else name
            )
            if ident.startswith("FB-N-"):
                expected = "해당 wire/context 부정을 거부하며 accepted/installed를 만들지 않고 같은 client의 후속 유효 요청은 성공"
            elif ident.startswith("FB-A-"):
                expected = "취득 도중 authority 변경 시 E3/E4 무권한 COMMIT 없이 기존 durable state 보존"
            else:
                expected = EXPECTED.get(
                    ident,
                    {
                        "independent_cost": "실제 HTTP/SQL/object/pin 관측에서 identical 및 changed-frontier/frozen reuse 비용과 complete oracle 일치",
                        "new_backend": "완전한 backend root/capture/lease만 durable하며 SIGKILL 또는 잘못된 lifecycle에서 fail closed",
                        "new_crash": "실제 SIGKILL 후 fresh process에서 complete source/receipt/pins/lineage와 Frozen read 회복",
                        "new_http_concurrency": "실제 TLS 경쟁에서 bounded visible retry/lease budget/pins/release 일치",
                        "new_generation_cost": "실제 신규 immutable 집합·revision과 독립 complete F(raw)/Patricia oracle 일치",
                    }.get(suite, "별도 persisted-state oracle 일치"),
                )
            independent.append(
                {
                    "id": ident,
                    "suite": suite,
                    "test": name,
                    "expected": expected,
                    "actual": case["result"],
                    "oracle": "실제 실행 assertion과 evidence JSON의 HTTP/별도 SQLite/독립 graph 또는 fresh-process 결과",
                }
            )
    summary["new_independent_counts"] = dict(Counter(c["actual"] for c in independent))
    assert summary["new_independent_counts"] == {"PASS": 49}, summary[
        "new_independent_counts"
    ]
    assert summary["integration"]["done_success"] is True
    assert summary["independent_cost"]["done_success"] is True
    assert (out / "integration-campaign.exit").read_text().strip() == "0"
    assert summary["flutter_final"]["done_success"] is not None
    assert (out / "build.exit").exists()
    assert summary["backend_first"]["main_tests"] == {"FAIL": 1, "PASS": 1314}
    assert summary["backend_final"]["main_tests"] == {"FAIL": 1, "PASS": 1314}
    summary["actual_new_sigkill_cases"] = 7
    summary["exits"] = {
        p.stem: p.read_text().strip() for p in sorted(out.glob("*.exit"))
    }
    summary["all_recorded_sources_unchanged"] = all(
        sha(ROOT / row["path"]) == row["sha256"]
        for row in json.loads((HERE / "inventory.json").read_text())["files"]
    )
    summary["tracked_diff"] = subprocess.check_output(
        ["git", "diff", "--name-only"], cwd=ROOT, text=True
    ).strip()
    summary["product_diff_since_audited_product"] = subprocess.check_output(
        [
            "git",
            "diff",
            "--name-only",
            "af9525e",
            "--",
            "backend",
            "mobile/lib",
            "frontend",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    summary["phase_b_verdict"] = "INCONCLUSIVE"
    summary["reason"] = (
        "필수 backend 전체 회귀가 두 번 같은 concurrency assertion에서 실패했다. 단독 PASS와 허용된 503 semantics만으로 원인을 확정하거나 gate를 통과시킬 수 없다."
    )
    summary["confirmed_new_product_correctness_blockers"] = 0
    summary["binding_t66f_exit"] = "NOT SATISFIED"
    summary["remaining_upper_gates"] = [
        "R1",
        "§35 전체 scaling/compression grid",
        "§26 실제 Android durability 증명",
    ]
    summary["static_checks"] = json.loads((out / "final-checks.json").read_text())
    summary["format_baseline"] = {
        "reported_differences": 10,
        "paths": re.findall(
            r"^Changed (.+)$", (out / "format-repository.log").read_text(), re.MULTILINE
        ),
        "product_paths_modified": False,
        "explanation": "full-repository --output=none가 찾은 10개 기존 파일은 감사 diff 밖이며 실제 수정하지 않았다.",
    }
    summary["initial_harness_attempts"] = {
        name: {k: v for k, v in machine(out / file).items() if k != "cases"}
        for name, file in {
            "initial_http_binding": "first-flow.log",
            "initial_workspace_path": "first-flow-2.log",
            "initial_import": "integration-complete.log",
            "initial_installed_source_fixture": "integration-final-valid.log",
            "explicit_epoch_status_fixture": "real-epoch.log",
        }.items()
    }

    evidence = HERE / "evidence"
    evidence.mkdir(exist_ok=True)
    files = [
        "integration-campaign.json",
        "cost-final/cost.json",
        "history-preservation.json",
        "environment.json",
        "final-checks.json",
        *[
            str(p.relative_to(out))
            for d in [
                "backend-independent",
                "crash-final",
                "http-concurrency",
                "generation-cost-final",
                "e2-independent",
            ]
            for p in (out / d).glob("*.json")
        ],
        "original-phase-a-cost/cost.json",
        "previous-ra01-cost/cost.json",
        "previous-ra01-cost/cost.json.handoff.json",
    ]
    spec = importlib.util.spec_from_file_location(
        "prior_compact_only", HERE.parent / "t66e4-ra01-reaudit/collect.py"
    )
    compact_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compact_module)
    manifest = []
    for file in files:
        source = out / file
        if not source.exists():
            continue
        destination = evidence / file.replace("/", "__")
        value = json.loads(source.read_text())
        destination.write_text(
            json.dumps(
                compact_module.compact(value), ensure_ascii=False, separators=(",", ":")
            )
            + "\n"
        )
        manifest.append(
            {
                "file": str(destination.relative_to(HERE)),
                "original_bytes": source.stat().st_size,
                "original_sha256": sha(source),
                "persisted_sha256": sha(destination),
            }
        )
    # Preserve failure text; record exact original bytes separately.
    summary["text_log_preservation"] = []
    for file in ["backend-full.log", "backend-rerun.log", "format-repository.log"]:
        original = out / file
        destination = evidence / file
        destination.write_text(
            "\n".join(line.rstrip() for line in original.read_text().splitlines())
            + "\n"
        )
        summary["text_log_preservation"].append(
            {
                "file": str(destination.relative_to(HERE)),
                "original_sha256": sha(original),
                "persisted_sha256": sha(destination),
                "normalization": "행 끝 공백만 제거; 원문 SHA 보존, assertion과 실패 내용은 변경하지 않음",
            }
        )
    summary["evidence_manifest"] = manifest
    summary["completion"] = "EXECUTED_WITH_UNSATISFIED_GATES"
    write("summary.json", summary)
    write("cases.json", independent)
    write(
        "regression-cases.json",
        {
            k: v
            for k, v in all_cases.items()
            if k
            not in ["flutter_first", "flutter_final", "backend_first", "backend_final"]
        },
    )
    print(
        json.dumps(
            {
                "independent": summary["new_independent_counts"],
                "flutter": summary["flutter_final"].get("counts"),
                "backend": summary["backend_final"].get("main_tests"),
                "unchanged": summary["all_recorded_sources_unchanged"],
            }
        )
    )


if __name__ == "__main__":
    main(sys.argv[1])

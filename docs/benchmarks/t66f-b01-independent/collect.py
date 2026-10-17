"""실제 종료/JUnit/HTTP/native SQLite를 합쳐 B01 증거를 보존한다."""

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def junit(path):
    root = ET.parse(path).getroot()
    suites = list(root) if root.tag == "testsuites" else [root]
    cases = []
    for suite in suites:
        for test in suite.findall("testcase"):
            failure = test.find("failure")
            error = test.find("error")
            bad = failure if failure is not None else error
            cases.append(
                dict(
                    name=test.get("name"),
                    result="FAIL"
                    if bad is not None
                    else "SKIP"
                    if test.find("skipped") is not None
                    else "PASS",
                    **({"failure": bad.text} if bad is not None else {}),
                )
            )
    return {
        **{
            k: sum(int(s.get(k, 0)) for s in suites)
            for k in ["tests", "failures", "errors", "skipped"]
        },
        "cases": cases,
        "seconds": sum(float(s.get("time", 0)) for s in suites),
        "sha256": sha(path),
    }


def machine(path):
    names, cases, errors, done = {}, [], [], None
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "testStart":
            names[event["test"]["id"]] = event["test"]["name"]
        elif event.get("type") == "testDone" and not event.get("hidden"):
            cases.append(
                dict(
                    name=names.get(event["testID"]),
                    result="SKIP"
                    if event.get("skipped")
                    else "PASS"
                    if event["result"] == "success"
                    else "FAIL",
                )
            )
        elif event.get("type") == "error":
            errors.append(str(event.get("error")))
        elif event.get("type") == "done":
            done = event["success"]
    return dict(
        counts=dict(Counter(r["result"] for r in cases)),
        cases=cases,
        errors=errors,
        done=done,
        sha256=sha(path),
    )


EXPECTED = {
    "I01": "원 세 assert exact equality·bad status vector 거부·다른 helpers/제품 불변·기본1000/기존지원5000",
    "I02": "실제 writer 동안 short BEGIN이 BUSY/503, 해제 뒤 long 5개는 정확히 네201/한429·Available4/pins20·FD0",
    "I03": "writer wait 중 credential 폐기 후401/no mutation, 별도 유효 synthetic session으로201",
    "I04": "동일 nonce201/200 bytes 동일·한 observation, 다른 body409, quota4 초과429와 same-nonce200",
    "I05": "취소돼도 native 작업 동안 permit 유지/다음503, native exit 뒤 unchanged state와 정상201·capacity 복구",
    "I06": "COMMIT 전 SQL 오류는 rollback/다음201, COMMIT 후 오류는 complete lease/pins 유지/다음200",
    "I07": "A stale request는 B에 작용하지 못함, B own request201, A inode 복원 후 absent201/committed200",
    "I08": "5초/1초 fixture 실행 순서 양쪽에서 실제 PRAGMA·다른 repo 기본1000 보존·closed handles",
    "I09": "native admission100ms→해당 repo1000/5000만 적용→handle close, plain SQLite context와 close 구별",
    "I10": "실제 TLS quota429 세 번 후 같은 limit1 client가 release 뒤 E2 bytes/hash/closure 검증 성공·accepted는 null",
}


def artifact_id(name):
    ident = re.search(r"I\d+", name)[0]
    suffix = name.split("[")[-1].rstrip("]") if "[" in name else None
    if ident == "I08":
        suffix = "5000" if suffix == "ordering0" else "1000"
    return ident + ("-" + suffix if suffix else "")


def main(folder):
    out = Path(folder).resolve()
    summary, cases = {}, []
    for key, count in [
        ("independent-final", 14),
        ("correction", 4),
        ("related", 90),
        ("identity-independent", 6),
        ("real-http", 2),
        ("quota-first", 3),
        ("quota-last", 3),
    ]:
        row = junit(out / (key + ".xml"))
        row["exit"] = int((out / (key + ".exit")).read_text())
        assert (
            row["tests"] == count
            and row["failures"] == row["errors"] == row["skipped"] == row["exit"] == 0
        ), key
        summary[key] = row
    flutter = machine(out / "flutter-http.log")
    assert (
        flutter["counts"] == {"PASS": 4}
        and flutter["done"] is True
        and not flutter["errors"]
    )
    assert (out / "flutter-http.exit").read_text().strip() == "0"
    assert {c["name"].split()[0] for c in flutter["cases"]} == {
        "FB01",
        "FB13",
        "FB14",
        "I10",
    }
    summary["selected_flutter"] = flutter
    summary["full_flutter"] = "NOT RERUN IN B01 TARGETED VALIDATION"

    for index in [1, 2]:
        name = f"full-{index}"
        row = junit(out / (name + ".xml"))
        row.pop("cases")
        text = (out / (name + ".log")).read_text()
        counts = re.findall(r"(\d+) passed.*?(\d+) subtests passed", text)
        assert counts and tuple(map(int, counts[-1])) == (1315, 1540)
        row["main_tests"] = 1315
        row["subtests"] = 1540
        row["log_sha256"] = sha(out / (name + ".log"))
        row["process"] = json.loads((out / (name + "-process.json")).read_text())
        assert row["process"]["exit"] == 0 and row["process"]["timeout"] is False
        assert (
            row["tests"] == 2855
            and row["failures"] == row["errors"] == row["skipped"] == 0
        )
        warnings = re.findall(r"(\d+) warnings?", text)
        row["warning_count"] = int(warnings[-1]) if warnings else 0
        row["warnings"] = [
            line.strip() for line in text.splitlines() if "Warning:" in line
        ]
        summary[name] = row

    repetitions = []
    for directory in ["repetition", "teardown-repetition", "gc-repetition"]:
        for process in json.loads((out / directory / "processes.json").read_text()):
            raw_path = out / directory / process["record"]
            value = json.loads(raw_path.read_text())
            row = dict(
                process,
                statuses=sorted(r["status"] for r in value["responses"]),
                execute=value["execute_calls"],
                select=value["select_calls"],
                handles=len(value["handles"]),
                all_handles_closed=all(h["closed"] for h in value["handles"]),
                raw_sha256=sha(raw_path),
                source_sha256=value["source_sha256"],
                record_path=str(raw_path.relative_to(out)),
            )
            if process["cohort"] == "corrected":
                assert process["exit"] == 0 and row["statuses"] == [201] * 4 + [429]
                assert row["all_handles_closed"] and (
                    row["execute"],
                    row["select"],
                    row["handles"],
                ) == (4355, 1450, 14)
            repetitions.append(row)
    summary["repetitions"] = repetitions
    summary["corrected_repeated_counts"] = dict(
        Counter(
            "PASS" if r["exit"] == 0 else "FAIL"
            for r in repetitions
            if r["cohort"] == "corrected"
        )
    )
    summary["baseline_repeated_counts"] = dict(
        Counter(
            "PASS" if r["exit"] == 0 else "FAIL"
            for r in repetitions
            if r["cohort"] == "baseline"
        )
    )
    assert summary["corrected_repeated_counts"] == {"PASS": 17}
    assert summary["baseline_repeated_counts"] == {"PASS": 3, "FAIL": 1}
    gc = json.loads((out / "gc-repetition/corrected-1.json").read_text())
    assert (
        len(gc["native_fd_after_fixture_teardown"]) == 2
        and gc["native_fd_after_explicit_gc"] == []
    )

    for case in summary["independent-final"]["cases"]:
        ident = artifact_id(case["name"])
        observed = json.loads((out / "cases-final" / (ident + ".json")).read_text())
        actual = {
            "http_statuses": [r["status"] for r in observed.get("responses", [])],
            "sqlite_errors": [
                {
                    k: e.get(k)
                    for k in ["sql", "sqlite_code", "sqlite_name", "elapsed_us"]
                }
                for e in observed.get("events", [])
                if e["event"] == "execute_error"
            ],
            "all_observed_product_handles_closed": (
                all(h["closed"] for h in observed["handles"])
                if observed.get("handles")
                else None
            ),
            "durable_or_static_oracle": {
                k: v
                for k, v in observed.items()
                if k not in {"events", "responses", "handles", "statements"}
            },
        }
        cases.append(
            dict(
                id=ident,
                test=case["name"],
                result=case["result"],
                initial="원 transfer 합성 template의 새 disposable clone; static case는 Git source oracle",
                lock_budget_ms=[1000, 5000]
                if ident.startswith(("I02", "I08"))
                else int(ident.split("-")[-1])
                if ident.startswith("I09-")
                else 5000
                if not ident.startswith("I01")
                else None,
                expected=EXPECTED[ident.split("-")[0]],
                actual=actual,
                oracle="C SQLite return/trace·별도 raw connection·실제 permit 재획득·/proc FD 또는 exact Git AST",
                evidence="evidence/cases-final__" + ident + ".json",
            )
        )
    new_flutter = next(c for c in flutter["cases"] if c["name"].startswith("I10 "))
    cases.append(
        dict(
            id="I10",
            test=new_flutter["name"],
            result=new_flutter["result"],
            initial="새 실제 TLS backend/Flutter store",
            lock_budget_ms=1000,
            expected=EXPECTED["I10"],
            actual="4 leases201 +probe429 +E2 3×429 +release204 +verified acquisition",
            oracle="실제 HTTP observer와 별도 client SQLite/서버 bytes",
            evidence="evidence/flutter-quota.json",
        )
    )
    assert len(cases) == 15 and all(c["result"] == "PASS" for c in cases)
    summary["new_independent_counts"] = {"PASS": 15, "FAIL": 0, "INCONCLUSIVE": 0}
    summary["theme_coverage"] = {
        "01 exact assertion": ["I01", "corrected repetitions17"],
        "02/03/04 lock budgets and 503": ["I02", "baseline exact-copy failure"],
        "05 quota": ["I02", "I04", "I10"],
        "06 nonce": ["I04"],
        "07/08/09 permits and recovery": [
            "I02",
            "I03",
            "I05-authenticated",
            "I05-sqlite_wait",
            "I06-False",
            "I06-True",
            "I10",
        ],
        "10/11 scope/default": ["I01", "I08-5000", "I08-1000", "I09-1000", "I09-5000"],
        "12 identity": ["I07-authenticated", "I07-serialized", "existing actual-open6"],
        "13 cleanup": [
            "I02",
            "I09-1000",
            "I09-5000",
            "original fixture FD/GC observation",
        ],
        "14 ordering": ["I08-5000", "I08-1000", "related90", "full runs"],
        "15 product immutable": ["I01", "inventory hashes", "Git product diff"],
    }
    inventory = json.loads((HERE / "inventory.json").read_text())
    summary["all_recorded_files_preserved"] = all(
        sha(ROOT / r["path"]) == r["sha256"] for r in inventory["files"]
    )
    assert summary["all_recorded_files_preserved"]
    summary["product_diff_from_phase_b"] = subprocess.check_output(
        [
            "git",
            "diff",
            "c479a379",
            "--",
            "backend/app",
            "backend/isolated_sync",
            "mobile/lib",
            "frontend",
        ],
        cwd=ROOT,
        text=True,
    )
    assert summary["product_diff_from_phase_b"] == ""
    summary["checks"] = json.loads((out / "checks.json").read_text())
    assert all(row["exit"] == 0 for row in summary["checks"].values())
    summary.update(
        verdict="PASS",
        root_cause="TEST HARNESS",
        historical_individual_root_causes="NOT RETROSPECTIVELY PROVEN",
        phase_b="INCOMPLETE — CONTINUATION REQUIRED",
        phase_b_continuation="YES",
        r1="DEFERRED / CLOSED",
        new_findings={
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFORMATIONAL": 1,
        },
    )

    evidence = HERE / "evidence"
    evidence.mkdir(exist_ok=True)
    manifest = []
    files = [
        "flutter-quota.json",
        "checks.json",
        *[str(p.relative_to(out)) for p in (out / "cases-final").glob("*.json")],
        *[str(p.relative_to(out)) for p in (out / "correction").glob("*.json")],
        *[str(p.relative_to(out)) for p in (out / "real-http").glob("*.json")],
        "repetition/baseline-1.json",
        "repetition/baseline-2.json",
        "repetition/corrected-1.json",
        "gc-repetition/corrected-1.json",
    ]
    for file in files:
        source = out / file
        destination = evidence / file.replace("/", "__")
        shutil.copyfile(source, destination)
        manifest.append(
            dict(
                file=str(destination.relative_to(HERE)),
                sha256=sha(source),
                bytes=source.stat().st_size,
            )
        )
    # Existing large Flutter oracle is compacted only for bounded evidence storage.
    spec = importlib.util.spec_from_file_location(
        "compact_prior_evidence", HERE.parent / "t66e4-ra01-reaudit/collect.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw = out / "flutter-existing.json"
    destination = evidence / "flutter-existing-compact.json"
    destination.write_text(
        json.dumps(
            module.compact(json.loads(raw.read_text())),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
    )
    manifest.append(
        dict(
            file=str(destination.relative_to(HERE)),
            original_sha256=sha(raw),
            persisted_sha256=sha(destination),
            normalization="기존 oracle의 source/closure/B bytes를 count/digest로 보존; 원 assertions 변경 없음",
        )
    )
    for name in ["full-1", "full-2"]:
        for suffix in [".xml", "-process.json"]:
            shutil.copyfile(out / (name + suffix), evidence / (name + suffix))
    for source in sorted(Path("/tmp/mn-d3c-a01-reaudit").glob("swap_*.json")):
        destination = evidence / ("existing-identity__" + source.name)
        shutil.copyfile(source, destination)
        manifest.append(
            dict(
                file=str(destination.relative_to(HERE)),
                sha256=sha(source),
                bytes=source.stat().st_size,
            )
        )
    summary["fixture_gc_observation"] = {
        "product_handles": 14,
        "product_handles_closed": all(h["closed"] for h in gc["handles"]),
        "native_fd_before": len(gc["native_fd_before"]),
        "native_fd_after_call": len(gc["native_fd_after"]),
        "native_fd_after_fixture_teardown": len(gc["native_fd_after_fixture_teardown"]),
        "native_fd_after_explicit_gc": len(gc["native_fd_after_explicit_gc"]),
        "classification": "B01-IV01 INFORMATIONAL; 원 backup fixture context는 native close가 아님",
    }
    failed = junit(out / "repetition/baseline-1.xml")
    write("baseline-failure-signature.json", failed)
    summary["evidence_manifest"] = manifest
    write("cases.json", cases)
    write("summary.json", summary)
    print(
        json.dumps(
            {
                "new": summary["new_independent_counts"],
                "full_runs": [summary[f"full-{n}"]["process"]["exit"] for n in [1, 2]],
                "preserved": True,
                "verdict": "PASS",
            }
        )
    )


if __name__ == "__main__":
    main(sys.argv[1])

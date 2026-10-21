"""최종 lineage 승인 후 증거. 앞선 실패·승인 전 집계는 수정하지 않는다."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from collect import OUT, ROOT, flutter
from evidence_format import snapshot


def write(name, value):
    target = OUT / name
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    if target.exists() and target.read_bytes() != raw:
        raise RuntimeError(f"이전 최종 증거를 덮어쓰지 않는다: {name}")
    target.write_bytes(raw)


def main():
    runs = {}
    for name in [
        "lineage-targeted",
        "lineage-source-lock",
        "lineage-boundaries-final",
        "lineage-boundaries-approved",
        "lineage-http",
        "lineage-stale",
        "lineage-overhead-final",
        "lineage-backend-targeted",
        "lineage-analyze-initial",
        "lineage-authority-analyze",
        "lineage-authority-analyze-packages",
        "sealed-concurrent",
        "sealed-http",
        "sealed-stale",
    ]:
        for suffix in [".jsonl", ".err", ".log"]:
            source = Path("/tmp") / ("mn-b03-" + name + suffix)
            if not source.exists():
                continue
            raw = source.read_bytes()
            destination = OUT / (name + suffix + ".gz")
            compressed = gzip.compress(raw, mtime=0)
            if destination.exists() and destination.read_bytes() != compressed:
                raise RuntimeError("실행 중이거나 변경된 증거: " + name)
            destination.write_bytes(compressed)
            if suffix == ".jsonl":
                runs[name] = flutter(source)
    final_checks = {}
    for mode in [
        "backend-full",
        "flutter-full",
        "analyze",
        "build",
        "frontend",
        "ruff",
        "format",
        "compileall",
        "dart-format",
    ]:
        prefix = "lineage-" if mode == "backend-full" else "sealed-"
        source = OUT / (prefix + mode + ".json")
        if not source.exists():
            raise RuntimeError("최종 검사 미완료: " + mode)
        data = json.loads(source.read_text())
        if "exit" not in data:
            raise RuntimeError("아직 실행 중: " + mode)
        final_checks[mode] = {
            k: v for k, v in data.items() if k not in {"rss_samples", "pid"}
        }
    extra = json.loads((OUT / "sealed-authority-analyze.json").read_text())
    if extra.get("exit") is None:
        raise RuntimeError("별도 benchmark probe analyze 미완료")
    final_checks["authority-analyze"] = {
        k: v for k, v in extra.items() if k not in {"rss_samples", "pid"}
    }
    root = ET.parse(OUT / "lineage-backend-full.xml").getroot()
    cases = list(root.iter("testcase"))
    backend = {
        "tests": len(cases),
        "failures": len(list(root.iter("failure"))),
        "errors": len(list(root.iter("error"))),
        "skipped": len(list(root.iter("skipped"))),
    }
    calibration = ET.parse(OUT / "lineage-calibration.xml").getroot()
    calibration_result = {
        "tests": len(list(calibration.iter("testcase"))),
        "failures": len(list(calibration.iter("failure"))),
        "errors": len(list(calibration.iter("error"))),
        "scope": "신규 backend 24 + 역사 calibration 16, 원 assertion 보존",
    }
    # 원 machine stream를 임시 추출해 원 집계 로직을 그대로 사용한다.
    machine = Path("/tmp/mn-b03-lineage-full-machine.jsonl")
    machine.write_bytes(
        gzip.decompress((OUT / "sealed-flutter-full.log.gz").read_bytes())
    )
    final_flutter = flutter(machine)
    for n in [9, 260]:
        old = json.loads(Path(f"/tmp/mn-b03-lineage-http-n{n}.json").read_text())
        write(f"lineage-pre-seal-real-http-n{n}.json", old)
        data = json.loads(Path(f"/tmp/mn-b03-sealed-http-n{n}.json").read_text())
        write(f"sealed-real-http-n{n}.json", data)
        for phase, measured in data["phases"].items():
            for layer in ["primitive", "sqlite", "backend"]:
                if layer not in measured:
                    continue
                write(
                    f"sealed-n{n}-{phase}-{layer}.json",
                    snapshot(
                        data["run_id"] + ":" + data["phases"]["cold"]["generation"],
                        data["fixture"],
                        phase + "-cumulative",
                        layer,
                        measured[layer],
                        data["environment"],
                        {"scope": data["coverage"], "exclusions": data["exclusions"]},
                    ),
                )
    for name, path in {
        "lineage-frozen.json": "/tmp/mn-b03-lineage-boundaries-approved-frozen.json",
        "lineage-concurrent.json": "/tmp/mn-b03-lineage-http-concurrent.json",
        "sealed-concurrent.json": "/tmp/mn-b03-sealed-http-concurrent.json",
        "lineage-overhead-dart.json": "/tmp/mn-b03-lineage-overhead-final.json",
        "lineage-stale-cancelled.json": "/tmp/mn-b03-lineage-stale-cancelled.json",
        "lineage-stale-user.json": "/tmp/mn-b03-lineage-stale-stale-user.json",
        "sealed-stale-cancelled.json": "/tmp/mn-b03-sealed-stale-cancelled.json",
        "sealed-stale-user.json": "/tmp/mn-b03-sealed-stale-stale-user.json",
    }.items():
        write(name, json.loads(Path(path).read_text()))
    initial = json.loads((OUT / "initial.json").read_text())
    changed = {}
    for path, old in initial["sha256"].items():
        actual = ROOT / path
        if actual.exists():
            new = hashlib.sha256(actual.read_bytes()).hexdigest()
            if old != new:
                changed[path] = {"historical_sha256": old, "current_sha256": new}

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()

    write(
        "lineage-repository-before-commit.json",
        {
            "head": git("rev-parse", "HEAD"),
            "main": git("rev-parse", "main"),
            "origin_main": git("rev-parse", "origin/main"),
            "remote_main": git("ls-remote", "origin", "refs/heads/main"),
            "staged": git("diff", "--cached", "--name-status"),
            "initial_tracked_count": len(initial["sha256"]),
            "changed_tracked": changed,
            "missing": [p for p in initial["sha256"] if not (ROOT / p).exists()],
        },
    )
    write(
        "lineage-calibration-summary.json",
        {
            "schema_version": 1,
            "instrumentation_version": "t66f-b03/1",
            "source_lock_review": "../source-lock-review.json",
            "runs": runs,
            "full_backend": backend,
            "backend_calibration": calibration_result,
            "full_flutter": final_flutter,
            "checks": final_checks,
            "implementation_regression_gate": (
                "PASS"
                if final_flutter["done_success"] is True
                and final_flutter["counts"] == {"PASS": 1648, "SKIP": 2}
                and backend["tests"] == 1392
                and backend["failures"] == backend["errors"] == backend["skipped"] == 0
                and all(
                    c.get("exit") == 0
                    and c.get("status") == "PASS"
                    and c.get("external_termination") is None
                    for c in final_checks.values()
                )
                else "INCOMPLETE"
            ),
            "distinct_new_cases": {
                "backend": 24,
                "flutter": 49,
                "supplemental_real_authority_probe": 2,
                "total": 75,
                "note": "원 16 calibration·원 source guards·재실행·child probe는 신규 합계 제외. docs authority 2건은 기본 Flutter suite 밖에서 별도 실행",
            },
            "gate": "구현 결과만 집계. 독립 감사·5-point 비용 grid·Android/power/R1 판정 아님",
        },
    )
    print(json.dumps({"backend": backend, "flutter": final_flutter, "runs": runs}))


if __name__ == "__main__":
    main()

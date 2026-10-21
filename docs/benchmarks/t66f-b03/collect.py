"""명시 allow-list의 합성 결과만 보존하고 실제 exit/testDone/JUnit을 집계한다."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from evidence_format import snapshot

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def flutter(path):
    counts = Counter()
    names, failed = {}, []
    done = None
    for line in path.read_text().splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        if record.get("type") == "testStart":
            names[record["test"]["id"]] = record["test"]["name"]
        elif record.get("type") == "testDone" and not record.get("hidden"):
            if record["skipped"]:
                counts["SKIP"] += 1
            elif record["result"] == "success":
                counts["PASS"] += 1
            else:
                counts["FAIL"] += 1
                failed.append(names.get(record["testID"]))
        elif record.get("type") == "done":
            done = record["success"]
    return {"counts": dict(counts), "done_success": done, "failed": failed}


def main():
    OUT.mkdir(exist_ok=True)
    runs = {}
    for name in [
        "backend-calibration",
        "backend-calibration-2",
        "backend-calibration-3",
        "flutter-calibration",
        "flutter-calibration-2",
        "real-http",
        "real-http-2",
        "real-http-3",
        "real-http-4",
        "real-http-final-small",
        "overhead-dart",
        "unit-and-original-guards",
        "analyze-initial",
        "analyze-final",
    ]:
        for suffix in [".xml", ".log", ".jsonl", ".err"]:
            source = Path("/tmp") / ("mn-b03-" + name + suffix)
            if not source.is_file():
                continue
            raw = source.read_bytes()
            destination = OUT / (name + suffix + ("" if suffix == ".xml" else ".gz"))
            destination.write_bytes(
                raw if suffix == ".xml" else gzip.compress(raw, mtime=0)
            )
            if suffix == ".jsonl":
                runs[name] = flutter(source)
            elif suffix == ".xml":
                root = ET.fromstring(raw)
                cases = list(root.iter("testcase"))
                runs[name] = {
                    "tests": len(cases),
                    "failures": len(list(root.iter("failure"))),
                    "errors": len(list(root.iter("error"))),
                }
    for execution, n in [("4", 9), ("4", 260), ("final-small", 9)]:
        source = Path(f"/tmp/mn-b03-real-http-{execution}-n{n}.json")
        if not source.is_file():
            continue
        data = json.loads(source.read_text())
        label = f"n{n}" if execution == "4" else f"{execution}-n{n}"
        write(f"real-http-{label}.json", data)
        # 원 run_id는 보존하고, 재실행 evidence에는 실제 cold generation을 붙인다.
        evidence_run_id = data["run_id"] + ":" + data["phases"]["cold"]["generation"]
        for layer, key in [
            ("flutter-primitives", "primitive"),
            ("flutter-sqlite", "sqlite"),
            ("backend", "backend"),
        ]:
            write(
                f"logical-cost-{label}-{layer}.json",
                snapshot(
                    evidence_run_id,
                    data["fixture"],
                    "cold-identical-delta-legacy-read-fresh-process-cumulative",
                    layer,
                    data["phases"]["final"][key],
                    data["environment"],
                    {
                        "scope": data["coverage"],
                        "exclusions": data["exclusions"],
                        "final_grid": "DEFERRED",
                    },
                ),
            )
    overhead = Path("/tmp/mn-b03-overhead-dart.json")
    if overhead.is_file():
        write("overhead-dart.json", json.loads(overhead.read_text()))
    initial = json.loads((OUT / "initial.json").read_text())
    changed = {
        p: {"old": old, "new": hashlib.sha256((ROOT / p).read_bytes()).hexdigest()}
        for p, old in initial["sha256"].items()
        if (ROOT / p).is_file()
        and hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != old
    }
    missing = [p for p in initial["sha256"] if not (ROOT / p).is_file()]

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()

    write(
        "final-repository.json",
        {
            "head": git("rev-parse", "HEAD"),
            "main": git("rev-parse", "main"),
            "origin_main": git("rev-parse", "origin/main"),
            "remote_main": git("ls-remote", "origin", "refs/heads/main"),
            "status": git("status", "--short"),
            "staged": git("diff", "--cached", "--name-status"),
            "initial_tracked_count": len(initial["sha256"]),
            "changed_tracked_files": changed,
            "missing_tracked_files": missing,
            "commit": "NOT PERFORMED",
            "push": "NOT PERFORMED",
        },
    )
    write(
        "current-source-review.json",
        {
            "approval": "PENDING — source guards unchanged",
            "changed_tracked_files": changed,
            "missing_tracked_files": missing,
        },
    )
    write(
        "calibration-summary.json",
        {
            "schema_version": 1,
            "runs": runs,
            "distinct_new_cases": {
                "backend": 20,
                "flutter_unit": 25,
                "flutter_real_http": 2,
                "flutter_overhead": 1,
                "total": 48,
                "pass": 48,
                "fail": 0,
                "skip": 0,
                "note": "반복 실행·원 16 calibration·원 source guards는 신규 합계에서 제외",
            },
            "full_flutter": "NOT RUN — source-lock approval pending; original guards 21 PASS / 2 FAIL",
            "full_backend": json.loads((OUT / "backend-full.json").read_text()),
            "verdict": "BLOCKED — source-lock approval and remaining implementation gates pending",
        },
    )
    print(
        json.dumps({"runs": runs, "changed_tracked": list(changed)}, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()

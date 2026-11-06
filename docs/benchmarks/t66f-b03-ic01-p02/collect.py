"""P02 원자료를 재집계한다. 미실행100k를 PASS/zero로 바꾸지 않는다."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def machine(path):
    counts = Counter()
    done = None
    text = gzip.open(path, "rt").read() if path.suffix == ".gz" else path.read_text()
    for line in text.splitlines():
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if value.get("type") == "testDone" and not value.get("hidden"):
            counts[
                "SKIP"
                if value.get("skipped")
                else "PASS"
                if value.get("result") == "success"
                else "FAIL"
            ] += 1
        if value.get("type") == "done":
            done = value["success"]
    return {"counts": dict(counts), "done": done}


def main():
    commands = {}
    for file in OUT.glob("*.json"):
        value = json.loads(file.read_text())
        if isinstance(value, dict) and "mode" in value and "command" in value:
            commands[value["mode"]] = value
    full_flutter = [machine(OUT / f"flutter-full-part-{i}.jsonl") for i in range(3)]
    aggregate = Counter()
    for part in full_flutter:
        aggregate.update(part["counts"])
    log = OUT / "backend-full.log.gz"
    text = (
        gzip.open(log, "rt").read()
        if log.exists()
        else (OUT / "backend-full.log").read_text()
    )
    tests = re.search(r"(\d+) passed", text)
    subtests = re.search(r"(\d+) subtests passed", text)
    suite = ET.parse(OUT / "backend-full.xml").getroot()
    current = ROOT / "mobile/test/support/logical_cost_sqlite.dart"
    original = HERE / "original_sqlite.dart"
    new_cases = Counter()
    new_case_parts = {}
    for mode in [
        "new-tests-sealed",
        "components-final",
        "preparation-final",
        "cleanup-open-final",
        "cleanup-closed-final",
        "cached-busy-final",
    ]:
        assert commands[mode]["status"] == "PASS", mode
        path = OUT / (mode + ".log.gz")
        if not path.exists():
            path = OUT / (mode + ".log")
        part = machine(path)
        assert part["done"] and not part["counts"].get("FAIL"), (mode, part)
        new_cases.update(part["counts"])
        new_case_parts[mode] = part
    data = {
        "schema_version": 1,
        "instrumentation_version": "ic01-p02-cache32-v1",
        "instrumentation_scope": "explicit diagnostic wrapper only",
        "verdict": "INCOMPLETE — OBSERVER OVERHEAD OR LEASE EVIDENCE REMAINS",
        "full_100k_runs": 0,
        "full_100k_result": "NOT RUN",
        "preflight": "INCONCLUSIVE",
        "IC01": "INCOMPLETE",
        "independent_reaudit_ready": False,
        "commands": commands,
        "full_flutter": {"parts": full_flutter, "aggregate": dict(aggregate)},
        "full_backend": {
            "tests": int(tests[1]) if tests else None,
            "subtests": int(subtests[1]) if subtests else None,
            "junit": [s.attrib for s in suite],
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "python_sqlite": sqlite3.sqlite_version,
            "cpu_ticks_per_second": subprocess.check_output(["getconf", "CLK_TCK"])
            .decode()
            .strip(),
        },
        "source_sha256": {
            "before": hashlib.sha256(original.read_bytes()).hexdigest(),
            "after": hashlib.sha256(current.read_bytes()).hexdigest(),
        },
        "refs": {
            "branch": git("branch", "--show-current"),
            "local": git("rev-parse", "HEAD", "main", "origin/main"),
            "remote": git("ls-remote", "origin", "refs/heads/main"),
            "staged": git("diff", "--cached", "--name-only"),
            "status": git("status", "--short"),
        },
        "preservation": json.loads((OUT / "preservation.json").read_text()),
        "lease_model": json.loads((OUT / "lease-model.json").read_text()),
        "measurement_exclusions": [
            "Full instrumented100k closure/publication/read and terminal snapshots not run",
            "Five-point H/D/N and final I25 proof deferred to independent Phase B",
            "Android VFS/I/O/memory and hardware power loss not verified",
            "Unprofiled native/callback timers mean not measured, not zero work",
            "Statement metrics are diagnostic operations, separate from product logical bytes",
            "Cleanup-open PASS reproduces child exit1; cleanup-closed requires original child exit0",
        ],
        "commit": "NONE",
        "push": "NOT PERFORMED",
    }
    components = json.loads((OUT / "components-final-data.json").read_text())
    data["e1_input"] = {
        k: components[k]
        for k in [
            "objects",
            "bytes",
            "sample_kinds",
            "full_retained_store_kinds",
            "max_rss_bytes",
        ]
    }
    data["closed_caches"] = components["closed_caches"]
    data["bounded_actual_operation_counters"] = next(
        r
        for r in components["records"]
        if r["mode"] == "reuse" and not r["reuse"] and r["repeat"] == 1
    )
    for state in ["open", "closed"]:
        data[f"cleanup_{state}"] = json.loads(
            (OUT / f"cleanup-{state}-final/shutdown-state.json").read_text()
        )
    data["new_p02_unique_cases"] = {
        **{key: new_cases.get(key, 0) for key in ["PASS", "FAIL", "SKIP"]},
        "parts": new_case_parts,
        "scope": "10 unit + cached BUSY1 + cold/reuse/validation sample1 + prepared cohort1 + cleanup two parameterized cases; earlier attempts not double-counted",
    }
    data["historical_attempts_preserved"] = [
        "new-tests compile enum typo FAIL",
        "new-tests-final two new incorrect matchers FAIL",
        "dart-format-final copied adapter formatting FAIL",
    ]
    (OUT / "summary.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "backend": data["full_backend"],
                "flutter": data["full_flutter"],
                "preflight": data["preflight"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

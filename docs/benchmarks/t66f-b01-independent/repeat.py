"""원 assertion의 유한 독립 반복. baseline은 임시 exact copy로만 실행한다."""

import hashlib
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
TEST = "tests/test_isolated_sync_transfer.py::test_bounded_concurrent_quota_and_same_request_status"


def main(folder, corrected_only=False, runs=4):
    out = Path(folder).resolve()
    assert out.is_relative_to(Path("/tmp"))
    out.mkdir(parents=True, exist_ok=True)
    old = subprocess.check_output(
        ["git", "show", "c479a379:backend/tests/test_isolated_sync_transfer.py"],
        cwd=ROOT,
    )
    copy = out / "original_exact_test.py"
    copy.write_bytes(old)
    results = []
    cohorts = (
        [("corrected", runs)]
        if corrected_only
        else [("baseline", 4), ("corrected", 12)]
    )
    for cohort, repetitions in cohorts:
        for index in range(1, repetitions + 1):
            prefix = out / f"{cohort}-{index}"
            test = (
                str(copy) + "::" + TEST.split("::")[1] if cohort == "baseline" else TEST
            )
            cmd = [
                str(ROOT / ".venv/bin/python"),
                "-m",
                "pytest",
                "-q",
                "-p",
                "repeat_plugin",
                test,
                "--junitxml=" + str(prefix) + ".xml",
            ]
            start = time.monotonic()
            with Path(str(prefix) + ".log").open("w") as log:
                process = subprocess.run(
                    cmd,
                    cwd=ROOT / "backend",
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env=os.environ
                    | {
                        "PYTHONPATH": str(HERE) + os.pathsep + str(ROOT / "backend"),
                        "B01_REPEAT_RECORD": str(prefix) + ".json",
                    },
                    timeout=120,
                )
            results.append(
                dict(
                    cohort=cohort,
                    iteration=index,
                    command=cmd,
                    exit=process.returncode,
                    seconds=time.monotonic() - start,
                    record=prefix.name + ".json",
                )
            )
            (out / "processes.json").write_text(json.dumps(results, indent=2) + "\n")
            print(cohort, index, process.returncode, flush=True)
    (out / "baseline-copy-sha256").write_text(hashlib.sha256(old).hexdigest() + "\n")
    return int(any(row["exit"] for row in results if row["cohort"] == "corrected"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--corrected-only", action="store_true")
    parser.add_argument("--runs", type=int, default=4, choices=range(1, 17))
    args = parser.parse_args()
    raise SystemExit(main(args.folder, args.corrected_only, args.runs))

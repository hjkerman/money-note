"""Bounded runs of the unchanged test, preserving each response/lock trace."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TEST = "tests/test_isolated_sync_transfer.py::test_bounded_concurrent_quota_and_same_request_status"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--runs", type=int, default=8, choices=range(1, 17))
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--light", action="store_true")
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(Path("/tmp")):
        parser.error("Synthetic diagnostic outputs must be beneath /tmp")
    args.output.mkdir(parents=True, exist_ok=False)
    test = TEST
    if args.baseline:
        # Read the exact audit version without checkout/reset or editing the
        # current test. Product files are separately verified unchanged.
        source = subprocess.check_output(
            [
                "git",
                "show",
                "c479a379b54e196439c522c1fdf56eca713ca8ad:backend/tests/test_isolated_sync_transfer.py",
            ],
            cwd=ROOT,
        )
        source_path = args.output.resolve() / "original_test.py"
        source_path.write_bytes(source)
        test = str(source_path) + "::" + TEST.split("::")[1]
    else:
        source = (ROOT / "backend/tests/test_isolated_sync_transfer.py").read_bytes()
    result = []
    for index in range(args.runs):
        stem = args.output.resolve() / str(index + 1)
        command = [
            str(ROOT / ".venv/bin/python"),
            "-m",
            "pytest",
            "-q",
            "-p",
            "forensics",
            test,
            "--b01-output=" + str(stem) + ".json",
            "--junitxml=" + str(stem) + ".xml",
        ]
        if args.light:
            command.append("--b01-light")
        started = time.monotonic()
        with Path(str(stem) + ".log").open("w") as log:
            completed = subprocess.run(
                command,
                cwd=ROOT / "backend",
                env=dict(
                    os.environ,
                    PYTHONPATH=str(HERE) + os.pathsep + str(ROOT / "backend"),
                ),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=90,
            )
        suite = ET.parse(str(stem) + ".xml").getroot().find("testsuite")
        evidence = json.loads(Path(str(stem) + ".json").read_text())
        result.append(
            dict(
                iteration=index + 1,
                exit=completed.returncode,
                seconds=time.monotonic() - started,
                failures=int(suite.attrib["failures"]),
                errors=int(suite.attrib["errors"]),
                statuses=sorted(r["status"] for r in evidence["responses"]),
                command=command,
                baseline=args.baseline,
                light=args.light,
                test_source_sha256=hashlib.sha256(source).hexdigest(),
            )
        )
        print(
            index + 1, result[-1]["statuses"], "exit", completed.returncode, flush=True
        )
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0  # Diagnostic campaign records failures; it is not a PASS gate.


if __name__ == "__main__":
    raise SystemExit(main())

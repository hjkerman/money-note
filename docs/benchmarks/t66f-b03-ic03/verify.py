"""IC03 출력만 보관하는 bounded runner. 역사 source/assertion은 바꾸지 않는다."""

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"


def run(label, command, cwd):
    target = OUT / (label + ".log.gz")
    record = OUT / (label + ".json")
    if target.exists() or record.exists():
        raise FileExistsError(label)
    sources = [
        "docs/benchmarks/t66f-b03/counters.py",
        "mobile/test/support/logical_cost_sqlite.dart",
        "backend/tests/test_logical_cost_ic03.py",
    ]
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
    started = time.monotonic()
    with gzip.open(target, "wb") as log:
        process = subprocess.Popen(
            command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        with process.stdout:
            while chunk := process.stdout.read1(65536):
                log.write(chunk)
        exit_code = process.wait()
    result = {
        "command": command,
        "cwd": str(cwd),
        "exit_code": exit_code,
        "seconds": time.monotonic() - started,
        "source_sha256": hashes,
        "raw": target.name,
    }
    if "--machine" in command:
        counts, done = {"PASS": 0, "FAIL": 0, "SKIP": 0}, None
        for line in gzip.open(target, "rt"):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "testDone" and not event.get("hidden"):
                key = (
                    "SKIP"
                    if event.get("skipped")
                    else "PASS"
                    if event.get("result") == "success"
                    else "FAIL"
                )
                counts[key] += 1
            if event.get("type") == "done":
                done = event.get("success")
        result.update(counts=counts, done=done)
        if done is not True or counts["FAIL"]:
            exit_code = exit_code or 1
    record.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {"label": label, "exit_code": exit_code, "counts": result.get("counts")}
        ),
        flush=True,
    )
    if exit_code:
        print("".join(gzip.open(target, "rt").readlines()[-35:]), flush=True)
    return exit_code


def backend():
    # Reuse the explicitly approved historical/current split, but direct ALL
    # outputs here. Never invoke the older P02 runner which owns historical XML.
    import pytest

    spec = importlib.util.spec_from_file_location(
        "ic03_historical_backend", HERE.parent / "t66f-b03-ic01/original_backend.py"
    )
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)

    class Output(original.OutputOnly):
        def pytest_collection_modifyitems(self, items):
            for item in items:
                if item.module.__name__.endswith("test_logical_cost_independent_audit"):
                    item.module.OUT = OUT / "backend-original"
                    item.module.OUT.mkdir(exist_ok=True)

    sys.argv.append("--current")
    scratch = Path(os.environ["IC03_SCRATCH"])
    return pytest.main(
        [
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=" + str(scratch / "pytest-full"),
            "--junitxml=" + str(OUT / "backend-full.xml"),
        ],
        plugins=[Output()],
    )


if __name__ == "__main__":
    if sys.argv[1:] == ["backend-inner"]:
        raise SystemExit(backend())
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("--cwd", default=str(ROOT))
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    raise SystemExit(run(args.label, command, Path(args.cwd)))

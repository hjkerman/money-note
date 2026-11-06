"""IC04 출력만 보관하는 bounded runner. 역사 source/assertion은 바꾸지 않는다."""

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
        "backend/tests/test_logical_cost_ic04.py",
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
        "ic04_historical_backend", HERE.parent / "t66f-b03-ic01/original_backend.py"
    )
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)

    label = os.environ.get("IC04_BACKEND_LABEL", "backend-full")
    if not label.replace("-", "").isalnum():
        raise ValueError("invalid output label")
    xml = OUT / (label + ".xml")
    if xml.exists():
        raise FileExistsError(xml)

    class Output(original.OutputOnly):
        def pytest_collection_modifyitems(self, items):
            for item in items:
                if item.module.__name__.endswith("test_logical_cost_independent_audit"):
                    item.module.OUT = OUT / (label + "-original")
                    item.module.OUT.mkdir(exist_ok=True)

    sys.argv.append("--current")
    scratch = Path(os.environ["IC04_SCRATCH"])
    return pytest.main(
        [
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=" + str(scratch / ("pytest-" + label)),
            "--junitxml=" + str(xml),
        ],
        plugins=[Output()],
    )


def prepare_originals(destination):
    """Preserved assertions; only historical absolute root/import/output paths."""
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "candidate").symlink_to(ROOT, target_is_directory=True)
    (destination / "tests").mkdir()
    (destination / "evidence").mkdir()
    source = HERE.parent / "t66f-b03-ir05/tests"
    names = [
        "test_ir05_interrupt_final.py",
        "test_ir05_worker_interrupt.py",
        "test_ir05_interrupted_growth.py",
        "test_ir05_lifecycle.py",
        "test_ir04_rollover_native.py",
        "test_ir04_installation.py",
        "test_ir03_oracles.py",
        "test_ir03_installation.py",
        "test_ir03_tls.py",
        "test_ir03_triggers.py",
        "test_ir04_schema.py",
        "original_IA05.py",
        "original_IA06.py",
        "original_IA07.py",
        "ir03_oracles_test.dart",
        "ir04_schema_test.dart",
        "integration_original_test.dart",
        "ir03_delta_test.dart",
    ]
    records = []
    for name in names:
        original = (source / name).read_bytes()
        body = original
        changes = []
        for old in ["/tmp/money-note-ir05-20261024", "/tmp/money-note-ir03-20261023"]:
            count = body.count(old.encode())
            if count:
                changes.append({"from": old, "to": str(destination), "count": count})
                body = body.replace(old.encode(), str(destination).encode())
        (destination / "tests" / name).write_bytes(body)
        records.append(
            {
                "source": str((source / name).relative_to(ROOT)),
                "source_sha256": hashlib.sha256(original).hexdigest(),
                "adapter_sha256": hashlib.sha256(body).hexdigest(),
                "path_changes_only": changes,
                "assertions_unchanged": True,
            }
        )
    (destination / "adapters.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"adapters": len(records), "destination": str(destination)}))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "prepare-originals":
        prepare_originals(Path(sys.argv[2]))
        raise SystemExit(0)
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

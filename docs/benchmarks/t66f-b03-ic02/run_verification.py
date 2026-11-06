"""IC02 검증 출력만 새 경로에 보관한다. 원 assertion/역사 구현은 변경하지 않는다."""

import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"
SCRATCH = Path(os.environ["IC02_SCRATCH"])
LABEL = os.environ.get("IC02_RUN_LABEL", "final")
assert re.fullmatch(r"[a-z0-9-]+", LABEL), "invalid evidence run label"
SOURCES = [
    "docs/benchmarks/t66f-b03/counters.py",
    "mobile/test/support/logical_cost_sqlite.dart",
    "backend/tests/test_logical_cost_ic02.py",
    "mobile/test/segmented_logical_cost_ic02_test.dart",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, command, cwd):
    target = OUT / (name + ".log.gz")
    if target.exists() or (OUT / (name + ".json")).exists():
        raise FileExistsError(f"Choose a new run label; preserving {name}")
    started = time.monotonic()
    source_sha256 = {p: digest(ROOT / p) for p in SOURCES}
    with gzip.open(target, "wb") as log:
        # A child given gzip.fileno() would bypass compression. Drain a bounded
        # pipe through gzip.write instead, preserving real child bytes and exit.
        process = subprocess.Popen(
            command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        with process.stdout:
            last_flush = started
            while chunk := process.stdout.read1(65536):
                log.write(chunk)
                if time.monotonic() - last_flush >= 5:
                    log.flush()
                    last_flush = time.monotonic()
        exit_code = process.wait()
    record = {
        "command": command,
        "cwd": str(cwd),
        "exit_code": exit_code,
        "seconds": time.monotonic() - started,
        "source_sha256": source_sha256,
        "raw": target.name,
    }
    (OUT / (name + ".json")).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"run": name, "exit_code": exit_code}), flush=True)
    if exit_code:
        with gzip.open(target, "rt") as log:
            print("".join(log.readlines()[-35:]), flush=True)
    return record


def backend_pytest():
    import pytest

    spec = importlib.util.spec_from_file_location(
        "ic02_original_runner", HERE.parent / "t66f-b03-ic01/original_backend.py"
    )
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)

    class Output(original.OutputOnly):
        def pytest_collection_modifyitems(self, items):
            for item in items:
                if item.module.__name__.endswith("test_logical_cost_independent_audit"):
                    item.module.OUT = OUT / ("backend-original-" + LABEL)
                    item.module.OUT.mkdir(exist_ok=True)

    # The approved original plugin uses this flag only for the four historical
    # defect-existence tests. Current-behavior assertions use the live collector.
    sys.argv.append("--current")
    return pytest.main(
        [
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp=" + str(SCRATCH / ("pytest-" + LABEL)),
            "--junitxml=" + str(OUT / ("backend-" + LABEL + ".xml")),
        ],
        plugins=[Output()],
    )


def adapter(source, name, replacements):
    body = source.read_text()
    for before, after in replacements:
        assert body.count(before) == 1, (source, before)
        body = body.replace(before, after, 1)
    target = SCRATCH / (name + "_test.dart")
    target.write_text(body)
    return target, {
        "original": str(source.relative_to(ROOT)),
        "original_sha256": digest(source),
        "adapter_sha256": digest(target),
        "path_substitutions_only": replacements,
        "assertions_unchanged": True,
    }


def flutter_commands():
    original = ROOT / "mobile/test/segmented_logical_cost_independent_audit_test.dart"
    current, current_record = adapter(
        original,
        "ic02_" + LABEL.replace("-", "_") + "_current_independent",
        [
            (
                "import 'support/logical_cost_sqlite.dart';",
                f"import '{(ROOT / 'mobile/test/support/logical_cost_sqlite.dart').as_uri()}';",
            ),
            (
                "import 'support/offline_mode_fixtures.dart';",
                f"import '{(ROOT / 'mobile/test/support/offline_mode_fixtures.dart').as_uri()}';",
            ),
            (
                "docs/benchmarks/t66f-b03-independent/evidence",
                "docs/benchmarks/t66f-b03-ic02/evidence/flutter-original-current-"
                + LABEL,
            ),
            (
                "File('${auditOut.parent.path}/lineage-goldens.json')",
                "File('"
                + str(
                    ROOT / "docs/benchmarks/t66f-b03-independent/lineage-goldens.json"
                )
                + "')",
            ),
        ],
    )
    historical, historical_record = adapter(
        HERE.parent / "t66f-b03-ic01/historical_flutter_test.dart",
        "ic02_" + LABEL.replace("-", "_") + "_historical_independent",
        [
            (
                "import 'historical/logical_cost_sqlite.dart';",
                f"import '{(HERE.parent / 't66f-b03-ic01/historical/logical_cost_sqlite.dart').as_uri()}';",
            ),
            (
                "import '../../../mobile/test/support/offline_mode_fixtures.dart';",
                f"import '{(ROOT / 'mobile/test/support/offline_mode_fixtures.dart').as_uri()}';",
            ),
            (
                "docs/benchmarks/t66f-b03-ic01/evidence",
                "docs/benchmarks/t66f-b03-ic02/evidence/flutter-original-historical-"
                + LABEL,
            ),
            (
                "'${auditOut.parent.path}/../t66f-b03-independent/lineage-goldens.json'",
                "'"
                + str(
                    ROOT / "docs/benchmarks/t66f-b03-independent/lineage-goldens.json"
                )
                + "'",
            ),
        ],
    )
    (OUT / ("flutter-adapters-" + LABEL + ".json")).write_text(
        json.dumps([current_record, historical_record], indent=2) + "\n"
    )
    files = sorted(
        str(p.relative_to(ROOT / "mobile"))
        for p in (ROOT / "mobile/test").rglob("*_test.dart")
        if p != original
    )
    commands = [
        ["flutter", "test", "--no-pub", "--machine", "--concurrency=4", *files],
        [
            "flutter",
            "test",
            "--no-pub",
            "--machine",
            str(current),
            "--name",
            r"^(?!.*independent SQL defect reproducer).*$",
        ],
        [
            "flutter",
            "test",
            "--no-pub",
            "--machine",
            str(historical),
            "--plain-name",
            "independent SQL defect reproducer",
        ],
    ]
    return commands


def flutter_full():
    commands = flutter_commands()
    records = [
        run(f"flutter-{LABEL}-part-{i}", command, ROOT / "mobile")
        for i, command in enumerate(commands)
    ]
    for record in records:
        counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
        done = None
        for line in gzip.open(OUT / record["raw"], "rt"):
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
        record.update(counts=counts, done=done)
    (OUT / ("flutter-" + LABEL + ".json")).write_text(
        json.dumps(records, indent=2) + "\n"
    )
    return int(
        any(
            record["exit_code"]
            or record["done"] is not True
            or record["counts"]["FAIL"]
            for record in records
        )
    )


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    mode = sys.argv[1]
    if mode == "backend-pytest":
        raise SystemExit(backend_pytest())
    if mode == "backend-full":
        record = run(
            "backend-" + LABEL,
            [sys.executable, str(Path(__file__).resolve()), "backend-pytest"],
            ROOT / "backend",
        )
        raise SystemExit(record["exit_code"])
    if mode == "flutter-full":
        raise SystemExit(flutter_full())
    raise SystemExit("backend-full / flutter-full")

"""확인 cold 실행 종료를 기다린 뒤 작은 관련 회귀만 순차 실행한다."""

import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = Path(json.loads((HERE / "active-run.json").read_text())["out"])
while not (OUT / "execution.json").exists():
    time.sleep(5)
records = []


def run(name, args, cwd=ROOT, timeout=900):
    started = time.time()
    clock = time.monotonic()
    with (
        (OUT / (name + ".log")).open("w") as log,
        (OUT / (name + ".err")).open("w") as err,
    ):
        try:
            p = subprocess.run(args, cwd=cwd, stdout=log, stderr=err, timeout=timeout)
            record = dict(
                name=name,
                args=args,
                cwd=str(cwd),
                started_utc=started,
                elapsed_seconds=time.monotonic() - clock,
                exit_code=p.returncode,
                timeout=False,
            )
        except subprocess.TimeoutExpired:
            record = dict(
                name=name,
                args=args,
                cwd=str(cwd),
                started_utc=started,
                elapsed_seconds=time.monotonic() - clock,
                exit_code=None,
                timeout=True,
            )
    records.append(record)
    (OUT / "postchecks.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    )


run(
    "fresh-reopen",
    [
        "/home/hjkerman/.flutter/bin/dart",
        "--packages=" + str(ROOT / "mobile/.dart_tool/package_config.json"),
        str(ROOT / "docs/benchmarks/t66f-b02-implementation/reopen.dart"),
        str(OUT),
    ],
    timeout=900,
)
run(
    "targeted-flutter",
    [
        "/home/hjkerman/.flutter/bin/flutter",
        "test",
        "--no-pub",
        "--machine",
        "--concurrency=1",
        "test/segmented_large_profile_test.dart",
        "test/segmented_large_batch_test.dart",
        "test/segmented_large_profile_authority_test.dart",
        "test/segmented_large_profile_crash_test.dart",
        "test/segmented_adapter_isolation_test.dart",
        "test/segmented_fetch_test.dart",
        "test/segmented_response_cleanup_test.dart",
    ],
    ROOT / "mobile",
    timeout=1200,
)
run(
    "targeted-backend",
    [
        str(ROOT / ".venv/bin/python"),
        "-m",
        "pytest",
        "-q",
        "tests/test_isolated_sync_observation.py::test_repository_connections_close_on_success_and_failure",
        "tests/test_isolated_sync_observation.py::test_expiration_and_epoch_rotation",
        "tests/test_isolated_sync_observation.py::test_expired_observation_does_not_resurrect_on_clock_rollback",
        "tests/test_isolated_sync_observation.py::test_terminal_lease_expiry_is_sticky",
        "tests/test_isolated_sync_observation.py::test_terminal_before_expiry_remains_valid",
        "tests/test_isolated_sync_transfer.py::test_exact_expiry_and_rollback_persistence",
        "tests/test_isolated_sync_transfer.py::test_terminal_auth_expiry_cancellation_after_buffering",
        "tests/test_isolated_sync_transfer.py::test_bounded_concurrent_quota_and_same_request_status",
        "tests/test_isolated_sync_transfer.py::test_transfer_concurrency_budget_and_busy_retry",
        "--junitxml=" + str(OUT / "targeted-backend.xml"),
    ],
    ROOT / "backend",
    timeout=900,
)
run("frontend-build", ["npm", "run", "build"], ROOT / "frontend", timeout=300)
run(
    "ruff-backend",
    [str(ROOT / ".venv/bin/python"), "-m", "ruff", "check", "app", "tests"],
    ROOT / "backend",
    timeout=120,
)
run(
    "compileall",
    [
        str(ROOT / ".venv/bin/python"),
        "-m",
        "compileall",
        "-q",
        "backend/app",
        "backend/isolated_sync",
        "docs/benchmarks/t66f-b02-a01",
    ],
    timeout=120,
)
run("diff-check", ["git", "diff", "--check"], timeout=120)
(OUT / "postchecks-complete.json").write_text(
    json.dumps(dict(completed_utc=time.time(), checks=len(records))) + "\n"
)
print(json.dumps(dict(out=str(OUT), checks=records), ensure_ascii=False))

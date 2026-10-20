"""단일 bounded 실제 TLS D→E campaign. 기존 fixture/900초/3회 그대로다."""

import json
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def rss_tree(pid):
    nodes = {}
    for path in Path("/proc").glob("[0-9]*/status"):
        try:
            fields = dict(line.split(":", 1) for line in path.read_text().splitlines())
            nodes[int(path.parent.name)] = (
                int(fields["PPid"]),
                int(fields.get("VmRSS", "0 kB").split()[0]) * 1024,
            )
        except (OSError, ValueError, KeyError):
            continue
    owned = {pid}
    while True:
        extra = {p for p, (parent, _) in nodes.items() if parent in owned} - owned
        if not extra:
            return sum(nodes.get(p, (0, 0))[1] for p in owned)
        owned |= extra


def regression_pids():
    values = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            command = path.read_bytes()
        except OSError:
            continue
        if (
            b"\x00pytest\x00" in command
            or b"flutter_tools.snapshot\x00test\x00" in command
        ):
            values.append(int(path.parent.name))
    return values


def main():
    n = int(sys.argv[1])
    assert n in (1000, 50000, 100000)
    campaign = sys.argv[2] if len(sys.argv) > 2 else ""
    assert campaign in ("", "cursor-lifetime")
    if campaign:
        assert (HERE / "cursor-failure-source.json").exists()
    suffix = f"-{campaign}" if campaign else ""
    if shutil.disk_usage("/tmp").free < 8 * 1024**3:
        raise RuntimeError("합성 실행용 여유 디스크 8GiB 미만")
    out = Path(tempfile.mkdtemp(prefix=f"mn-a01-corrected-{n}{suffix}-"))
    args = [
        "/home/hjkerman/.flutter/bin/flutter",
        "test",
        "--no-pub",
        "--machine",
        f"--dart-define=B02_N={n}",
        f"--dart-define=B02_OUT={out}",
        "--dart-define=B02_COMPLETE_PLAN=true",
        "../docs/benchmarks/t66f-b02-a01-correction/full_http_test.dart",
    ]
    started = time.monotonic()
    record = {
        "n": n,
        "campaign": campaign,
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "mobile/lib/src/segmented/fetch.dart",
                "backend/isolated_sync/transfer.py",
            )
        },
        "out": str(out),
        "args": args,
        "started_utc": time.time(),
        "external_guard_seconds": 7200,
        "lease_seconds": 900,
        "observations": 3,
        "process_tree_rss_guard_bytes": 8 * 1024**3,
        "concurrent_synthetic_regression_pids": regression_pids(),
    }
    pointer = HERE / f"active-http-{n}{suffix}.json"
    assert not pointer.exists(), "동일 대형 campaign을 무근거 반복하지 않는다"
    pointer.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"started": str(out), "n": n}), flush=True)
    with (
        (out / "flutter.jsonl").open("w") as log,
        (out / "flutter.err").open("w") as err,
    ):
        proc = subprocess.Popen(
            args, cwd=ROOT / "mobile", stdout=log, stderr=err, start_new_session=True
        )
        record["pid"] = proc.pid
        (out / "command.json").write_text(json.dumps(record, indent=2) + "\n")
        reason, peak = None, 0
        while proc.poll() is None:
            peak = max(peak, rss_tree(proc.pid))
            if peak > 8 * 1024**3:
                reason = "process_tree_rss_guard"
            elif shutil.disk_usage("/tmp").free < 2 * 1024**3:
                reason = "free_disk_guard"
            elif time.monotonic() - started > 7200:
                reason = "wall_time_guard"
            if reason:
                break
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                pass
        if reason:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
        record.update(
            exit_code=proc.returncode,
            externally_terminated=reason is not None,
            guard_reason=reason,
            sampled_process_tree_rss_peak=peak,
        )
    record["elapsed_seconds"] = time.monotonic() - started
    (out / "execution.json").write_text(json.dumps(record, indent=2) + "\n")
    (HERE / f"http-{n}{suffix}-execution.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "out": str(out),
                "exit_code": record["exit_code"],
                "elapsed_seconds": record["elapsed_seconds"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

"""폐기용 실제 D→E 독립 실행. 50k/100k는 회귀 완료 뒤 순차로만 실행한다."""

from pathlib import Path
import gzip
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def process_tree(pid):
    nodes = {}
    for f in Path("/proc").glob("[0-9]*/status"):
        try:
            d = dict(x.split(":", 1) for x in f.read_text().splitlines())
            nodes[int(f.parent.name)] = (
                int(d["PPid"]),
                int(d.get("VmRSS", "0 kB").split()[0]) * 1024,
            )
        except (OSError, ValueError, KeyError):
            pass
    owned = {pid}
    while True:
        extra = {p for p, (parent, _) in nodes.items() if parent in owned} - owned
        if not extra:
            break
        owned |= extra
    return sum(nodes.get(p, (0, 0))[1] for p in owned)


def available():
    d = dict(x.split(":", 1) for x in Path("/proc/meminfo").read_text().splitlines())
    return int(d["MemAvailable"].split()[0]) * 1024


def collect(out, n):
    for f in out.rglob("*"):
        if not f.is_file() or f.suffix not in {".json", ".jsonl", ".err", ".stderr"}:
            continue
        target = (
            HERE
            / "evidence"
            / str(n)
            / (str(f.relative_to(out)).replace("/", "-") + ".gz")
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        with f.open("rb") as source, gzip.open(target, "wb") as dest:
            shutil.copyfileobj(source, dest)


def run(n):
    assert available() > 12 * 1024**3 and shutil.disk_usage("/tmp").free > 8 * 1024**3
    out = Path(tempfile.mkdtemp(prefix=f"mn-b02-independent-{n}-"))
    record = {
        "n": n,
        "out": str(out),
        "started_utc": time.time(),
        "available_memory_before": available(),
        "disk_free_before": shutil.disk_usage("/tmp").free,
        "ttl": 900,
        "max_observations": 3,
        "rss_tree_limit": 8 * 1024**3,
        "external_wall_guard_s": 600 if n == 1000 else 7200,
    }
    args = [
        "/home/hjkerman/.flutter/bin/flutter",
        "test",
        "--no-pub",
        "--machine",
        "--concurrency=1",
        f"--dart-define=B02_N={n}",
        f"--dart-define=B02_OUT={out}",
        "--dart-define=B02_COMPLETE_PLAN=true",
        "../docs/benchmarks/t66f-b02-independent/large_test.dart",
    ]
    start = time.monotonic()
    record["args"] = args
    with (
        (out / "flutter.jsonl").open("w") as log,
        (out / "flutter.err").open("w") as err,
    ):
        proc = subprocess.Popen(
            args, cwd=ROOT / "mobile", stdout=log, stderr=err, start_new_session=True
        )
        record["pid"] = proc.pid
        (HERE / f"active-{n}.json").write_text(json.dumps(record, indent=2) + "\n")
        peak = 0
        guard = None
        samples = []
        while proc.poll() is None:
            rss = process_tree(proc.pid)
            peak = max(peak, rss)
            samples.append(
                {
                    "elapsed_s": time.monotonic() - start,
                    "rss_tree": rss,
                    "memory_available": available(),
                }
            )
            if rss > 8 * 1024**3:
                guard = "process_tree_rss"
            if shutil.disk_usage("/tmp").free < 2 * 1024**3:
                guard = "free_disk"
            if time.monotonic() - start > record["external_wall_guard_s"]:
                guard = "external_wall"
            if guard:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                break
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                pass
        record.update(
            exit_code=proc.returncode,
            elapsed_s=time.monotonic() - start,
            peak_sampled_process_tree_rss=peak,
            external_termination=guard,
            resource_samples=samples,
        )
    (HERE / f"execution-{n}.json").write_text(json.dumps(record, indent=2) + "\n")
    collect(out, n)
    print(
        json.dumps(
            {"n": n, "exit": record["exit_code"], "out": str(out), "guard": guard}
        ),
        flush=True,
    )
    return record["exit_code"]


if __name__ == "__main__":
    if sys.argv[1] == "smoke":
        sys.exit(run(1000))
    assert sys.argv[1] == "large"
    for name in ["backend-full.exit", "flutter-full.exit", "smoke.exit"]:
        while not (HERE / name).exists():
            time.sleep(15)
        if (HERE / name).read_text().strip() != "0":
            raise SystemExit("선행 검사 실패: " + name)
    for n in [50000, 100000]:
        if run(n) != 0:
            raise SystemExit(1)

"""단일 실제50k cold 실행. 80분 외부 guard는 정상 expiry와 구분한다."""

import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = Path("/tmp") / f"mn-b02-a01-{time.strftime('%Y%m%d-%H%M%S')}"
OUT.mkdir()
(HERE / "active-run.json").write_text(
    json.dumps({"out": str(OUT), "started_utc": time.time()}) + "\n"
)


def command(args):
    value = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)
    return dict(
        command=args, exit=value.returncode, stdout=value.stdout, stderr=value.stderr
    )


cgroup = Path("/proc/self/cgroup").read_text()
relative = cgroup.split("::")[-1].strip()
cg = Path("/sys/fs/cgroup") / relative.lstrip("/")
environment = dict(
    os=platform.platform(),
    cpu=command(["lscpu"]),
    memory=command(["free", "-b"]),
    disk=command(["df", "-B1", "/tmp", str(ROOT)]),
    processes=command(["ps", "-eo", "pid,pcpu,pmem,args", "--sort=-pcpu"]),
    python=platform.python_version(),
    cgroup=cgroup,
    rlimits={
        str(n): resource.getrlimit(n)
        for n in [resource.RLIMIT_AS, resource.RLIMIT_NOFILE, resource.RLIMIT_CPU]
    },
    cgroup_limits={
        n: (cg / n).read_text() if (cg / n).exists() else None
        for n in ["cpu.max", "memory.max", "memory.high"]
    },
)
(OUT / "environment.json").write_text(json.dumps(environment, indent=2) + "\n")
args = [
    "/home/hjkerman/.flutter/bin/flutter",
    "test",
    "--no-pub",
    "--machine",
    "--dart-define=B02_N=50000",
    f"--dart-define=B02_OUT={OUT}",
    "../docs/benchmarks/t66f-b02-a01/cold_test.dart",
]
start = time.monotonic()
with (OUT / "flutter.jsonl").open("w") as log, (OUT / "flutter.err").open("w") as err:
    p = subprocess.Popen(
        args, cwd=ROOT / "mobile", stdout=log, stderr=err, start_new_session=True
    )
    (OUT / "command.json").write_text(
        json.dumps(
            dict(args=args, pid=p.pid, started_utc=time.time(), guard_seconds=4800),
            indent=2,
        )
        + "\n"
    )
    try:
        code = p.wait(timeout=4800)
        result = dict(
            exit_code=code,
            externally_terminated=False,
            elapsed_seconds=time.monotonic() - start,
        )
    except subprocess.TimeoutExpired:
        import signal

        os.killpg(p.pid, signal.SIGTERM)
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
        result = dict(
            exit_code=p.returncode,
            externally_terminated=True,
            elapsed_seconds=time.monotonic() - start,
        )
(OUT / "execution.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(dict(out=str(OUT), **result)))

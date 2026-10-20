"""합성 회귀의 실제 종료·자원 guard·원문 로그를 보존하는 감사 전용 runner."""

import gzip
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "evidence"
OUT.mkdir(exist_ok=True)
PYTHON = str(ROOT / ".venv/bin/python")
FLUTTER = "/home/hjkerman/.flutter/bin/flutter"
COMMANDS = {
    "backend-full": (
        "backend",
        [PYTHON, "-m", "pytest", "-q", "--junitxml=" + str(OUT / "backend-full.xml")],
    ),
    "flutter-full": (
        "mobile",
        [FLUTTER, "test", "--no-pub", "--machine", "--concurrency=4"],
    ),
    "analyze": ("mobile", [FLUTTER, "analyze", "--no-pub"]),
    "build": (
        "mobile",
        [
            FLUTTER,
            "build",
            "apk",
            "--debug",
            "--no-pub",
            "--dart-define=MONEY_NOTE_API_BASE_URL=https://audit.invalid",
        ],
    ),
    "frontend": ("frontend", ["npm", "run", "build"]),
    "ruff": (
        ".",
        [
            str(ROOT / ".venv/bin/ruff"),
            "check",
            "backend/app",
            "backend/isolated_sync",
            "backend/tests",
            "scripts",
            str(OUT.parent),
        ],
    ),
    "compileall": (
        ".",
        [
            PYTHON,
            "-m",
            "compileall",
            "-q",
            "backend/app",
            "backend/isolated_sync",
            "backend/tests",
            "scripts",
            str(OUT.parent),
        ],
    ),
    "format": (
        ".",
        [str(ROOT / ".venv/bin/ruff"), "format", "--check", str(OUT.parent)],
    ),
}
COMMANDS["compileall-final"] = COMMANDS["compileall"]


def tree_rss(pid):
    """표본 RSS 합이며 공유 page 중복·표본 사이 peak 누락이 가능하다."""
    parents, sizes = {}, {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
            parents[int(entry.name)] = int(fields[1])
            sizes[int(entry.name)] = int(fields[21]) * os.sysconf("SC_PAGE_SIZE")
        except (OSError, ValueError, IndexError):
            pass
    members = {pid}
    while True:
        expanded = members | {p for p, parent in parents.items() if parent in members}
        if expanded == members:
            break
        members = expanded
    return sum(sizes.get(p, 0) for p in members)


def run(mode):
    cwd, command = COMMANDS[mode]
    path = OUT / (mode + ".json")
    if path.exists():
        raise RuntimeError("기존 실행 증거를 덮어쓰지 않는다")
    env = {k: v for k, v in os.environ.items() if not k.startswith("MONEY_NOTE_")}
    record = dict(
        mode=mode,
        command=command,
        cwd=str(ROOT / cwd),
        start_unix=time.time(),
        status="RUNNING",
        timeout_seconds=7200,
        rss_guard_bytes=8 * 1024**3,
    )
    path.write_text(json.dumps(record, indent=2) + "\n")
    log_path = OUT / (mode + ".log")
    start = time.monotonic()
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT / cwd,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        record["pid"] = process.pid
        samples = []
        termination = None
        while process.poll() is None:
            rss = tree_rss(process.pid)
            samples.append([round(time.monotonic() - start, 3), rss])
            if time.monotonic() - start > 7200:
                termination = "TIMEOUT"
            if rss > record["rss_guard_bytes"]:
                termination = "RSS_GUARD"
            if os.statvfs(OUT).f_bavail * os.statvfs(OUT).f_frsize < 2 * 1024**3:
                termination = "DISK_GUARD"
            if termination:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(10)
        code = process.wait()
    record.update(
        exit=code,
        end_unix=time.time(),
        elapsed_seconds=time.monotonic() - start,
        external_termination=termination,
        rss_samples=samples,
        status="PASS" if code == 0 and termination is None else "FAIL",
    )
    path.write_text(json.dumps(record, indent=2) + "\n")
    raw = log_path.read_bytes()
    with gzip.open(str(log_path) + ".gz", "wb") as stream:
        stream.write(raw)
    log_path.unlink()
    print(json.dumps({k: v for k, v in record.items() if k != "rss_samples"}))
    if code or termination:
        print("\n".join(raw.decode(errors="replace").splitlines()[-25:]))
    return code or (1 if termination else 0)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))

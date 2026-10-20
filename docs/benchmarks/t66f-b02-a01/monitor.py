"""현재 조사 프로세스 트리만 30초 간격으로 /proc에서 읽는다."""

import json
import os
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
OUT = Path(json.loads((HERE / "active-run.json").read_text())["out"])
while not (OUT / "command.json").exists():
    time.sleep(1)
root = json.loads((OUT / "command.json").read_text())["pid"]
ticks = os.sysconf("SC_CLK_TCK")
with (OUT / "resources.jsonl").open("a", buffering=1) as stream:
    while True:
        entries = {}
        for p in Path("/proc").glob("[0-9]*"):
            try:
                stat = (p / "stat").read_text().rsplit(")", 1)[1].split()
                entries[int(p.name)] = (int(stat[1]), p, stat)
            except (OSError, ValueError, IndexError):
                pass
        ids = {root}
        while True:
            more = {pid for pid, (ppid, _, _) in entries.items() if ppid in ids}
            if more <= ids:
                break
            ids |= more
        rows = []
        for pid in sorted(ids):
            if pid not in entries:
                continue
            _, p, stat = entries[pid]
            try:
                status = dict(
                    line.split(":", 1)
                    for line in (p / "status").read_text().splitlines()
                    if ":" in line
                )
                io = dict(
                    (k, int(v))
                    for k, v in (
                        line.split(":", 1)
                        for line in (p / "io").read_text().splitlines()
                    )
                )
                rows.append(
                    dict(
                        pid=pid,
                        name=status["Name"].strip(),
                        command=(p / "cmdline")
                        .read_bytes()
                        .replace(b"\0", b" ")
                        .decode(errors="replace"),
                        rss_kib=status.get("VmRSS", "").strip(),
                        peak_rss_kib=status.get("VmHWM", "").strip(),
                        thread_count=status.get("Threads", "").strip(),
                        open_fds=len(list((p / "fd").iterdir())),
                        user_cpu_seconds=int(stat[11]) / ticks,
                        system_cpu_seconds=int(stat[12]) / ticks,
                        io=io,
                    )
                )
            except (OSError, ValueError, IndexError):
                pass
        stream.write(
            json.dumps(
                dict(monotonic_ns=time.monotonic_ns(), utc=time.time(), processes=rows)
            )
            + "\n"
        )
        if (OUT / "execution.json").exists():
            break
        time.sleep(30)

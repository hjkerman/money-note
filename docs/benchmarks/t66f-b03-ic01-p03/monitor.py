"""자기 소유 실험의 유한 host resource/clock anchor 표본. byte 계수 sampling 아님."""

import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
pid = int(sys.argv[1])
duration = 7200
start = time.monotonic()
path = HERE / "evidence/host-clock-samples.jsonl"
with path.open("x", buffering=1) as out:
    for serial in range(1441):
        before = time.perf_counter_ns()
        utc = time.time_ns()
        after = time.perf_counter_ns()
        process = Path(f"/proc/{pid}")
        if not process.exists():
            break
        fields = (process / "stat").read_text().rsplit(")", 1)[1].split()
        rss = int(fields[21]) * os.sysconf("SC_PAGE_SIZE")
        parent = int(fields[1])
        parent_rss = None
        try:
            f = Path(f"/proc/{parent}/stat").read_text().rsplit(")", 1)[1].split()
            parent_rss = int(f[21]) * os.sysconf("SC_PAGE_SIZE")
        except OSError:
            pass
        out.write(
            json.dumps(
                {
                    "serial": serial,
                    "monotonic_before_ns": before,
                    "utc_ns": utc,
                    "monotonic_after_ns": after,
                    "server_pid": pid,
                    "server_rss_bytes": rss,
                    "flutter_pid": parent,
                    "flutter_rss_bytes": parent_rss,
                }
            )
            + "\n"
        )
        if time.monotonic() - start >= duration:
            break
        time.sleep(5)

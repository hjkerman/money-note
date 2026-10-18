"""독립 요약 보유 모델 + 실제 facts component를 같은 host process에서 관찰한다.

이 모델에는 E2 closure/CompleteGenerationProof/accepted publication 권한이 없다.
"""

import json
from pathlib import Path
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = Path("/tmp/mn-b02")


def cap():
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))


for n in [1000, 10000, 50000, 100000]:
    folder = BASE / str(n)
    deadline = time.monotonic() + 2400
    while not (
        (folder / "result.json").exists()
        and json.loads((folder / "result.json").read_text())["status"] == "PASS"
    ):
        if time.monotonic() > deadline:
            raise TimeoutError(str(folder))
        time.sleep(1)
    label = f"jit-simulation-{n}"
    command = [
        "/usr/bin/time",
        "-v",
        "-o",
        str(BASE / (label + "-time.txt")),
        "/home/hjkerman/.flutter/bin/dart",
        "--packages=mobile/.dart_tool/package_config.json",
        str(HERE / "probe.dart"),
        "simulation",
        str(folder),
        str(BASE / (label + ".json")),
    ]
    start = time.time()
    with (BASE / (label + ".log")).open("w") as log:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            preexec_fn=cap,
            timeout=1500,
        )
    record = dict(
        command=command,
        actual_exit=result.returncode,
        seconds=time.time() - start,
        memory_guard_bytes=8 * 1024**3,
    )
    (BASE / (label + "-process.json")).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(dict(n=n, **record)), flush=True)
    assert result.returncode == 0

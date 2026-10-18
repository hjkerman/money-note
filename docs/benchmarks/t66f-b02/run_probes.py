"""유한 host component 측정. 준비된 실제 export만 소비한다."""

import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = Path("/tmp/mn-b02")
HERE = Path(__file__).resolve().parent


def invoke(label, command):
    prior = BASE / (label + "-process.json")
    if prior.exists() and json.loads(prior.read_text()).get("actual_exit") == 0:
        return
    started = time.time()
    log = BASE / (label + ".log")
    timed = ["/usr/bin/time", "-v", "-o", str(BASE / (label + "-time.txt")), *command]
    with log.open("w") as stream:
        try:
            result = subprocess.run(
                timed, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=1500
            )
            record = dict(command=timed, actual_exit=result.returncode, timeout=False)
        except subprocess.TimeoutExpired:
            record = dict(command=timed, actual_exit=None, timeout=True)
    record.update(start_unix=started, seconds=time.time() - started)
    (BASE / (label + "-process.json")).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(dict(label=label, **record)), flush=True)
    if record["actual_exit"] != 0:
        raise RuntimeError(f"조사 측정 실패: {log}")


for n in [1000, 5000, 10000, 12000, 15000, 20000, 24900, 25000, 50000, 100000]:
    directory = BASE / str(n)
    deadline = time.monotonic() + 2400
    while True:
        if (directory / "result.json").exists() and json.loads(
            (directory / "result.json").read_text()
        )["status"] == "PASS":
            break
        if time.monotonic() > deadline:
            raise TimeoutError(str(directory))
        time.sleep(1)
    for mode in [
        "graph",
        "facts",
        *(["simulation"] if n in [1000, 10000, 50000, 100000] else []),
    ]:
        label = f"jit-{mode}-{n}"
        invoke(
            label,
            [
                "/home/hjkerman/.flutter/bin/dart",
                "--packages=mobile/.dart_tool/package_config.json",
                str(HERE / "probe.dart"),
                mode,
                str(directory),
                str(BASE / (label + ".json")),
            ],
        )
    if n in [1000, 15000, 50000, 100000]:
        invoke(
            f"layout-{n}",
            [str(ROOT / ".venv/bin/python"), str(HERE / "layout.py"), str(directory)],
        )

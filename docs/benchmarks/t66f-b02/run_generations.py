"""새 backend-only 합성 generation을 유한 시간·고정 크기로 실행한다."""

import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
sizes = [int(x) for x in sys.argv[2:]] or [
    5000,
    10000,
    12000,
    15000,
    20000,
    24900,
    25000,
    50000,
    100000,
]
for n in sizes:
    start = time.time()
    command = [sys.executable, str(HERE / "generate.py"), str(n), str(OUT / str(n))]
    with (OUT / f"{n}.log").open("w") as log:
        try:
            result = subprocess.run(
                command, stdout=log, stderr=subprocess.STDOUT, timeout=1200
            )
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = None
    record = dict(
        n=n,
        command=command,
        start_unix=start,
        seconds=time.time() - start,
        actual_exit=code,
        timeout=code is None,
    )
    (OUT / f"{n}-process.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record), flush=True)
    if code != 0:
        raise SystemExit(1)

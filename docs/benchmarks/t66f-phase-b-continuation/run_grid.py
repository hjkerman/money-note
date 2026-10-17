"""각 규모를 새 process로 격리하고 실제 exit를 보존한다."""

import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).parent
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
for n in list(map(int, sys.argv[2:])) or [5000, 10000, 50000, 100000]:
    started = time.time()
    with (out / f"grid-{n}.log").open("w") as log:
        result = subprocess.run(
            [
                sys.executable,
                str(HERE / "grid.py"),
                "--n",
                str(n),
                "--out",
                str(out / "grid"),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    value = dict(n=n, exit=result.returncode, seconds=time.time() - started)
    (out / f"grid-{n}-process.json").write_text(json.dumps(value))
    print(json.dumps(value), flush=True)
    if result.returncode:
        print("\n".join((out / f"grid-{n}.log").read_text().splitlines()[-12:]))
        sys.exit(result.returncode)

"""앞 cache 준비가 끝난 뒤 다음 독립 규모를 실행해 동시 fsync를 제한한다."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).parent
out = Path(sys.argv[1])
n = int(sys.argv[2])
wait = Path(sys.argv[3]) if len(sys.argv) > 3 else None
if wait:
    while not (wait / "cost.json.partial").exists():
        if (wait / "cost-exit.json").exists():
            status = json.loads((wait / "cost-exit.json").read_text())
            if status["exit"]:
                raise SystemExit(
                    "preceding measurement failed; dependent execution blocked"
                )
        time.sleep(2)
start = time.time()
env = dict(os.environ, COST_N=str(n))
out.mkdir(parents=True, exist_ok=True)
with (out / "runner.log").open("w") as log:
    result = subprocess.run(
        [sys.executable, str(HERE / "measure.py"), str(out)],
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
value = dict(n=n, exit=result.returncode, seconds=time.time() - start)
(out / "runner-process.json").write_text(json.dumps(value))
print(json.dumps(value))
sys.exit(result.returncode)

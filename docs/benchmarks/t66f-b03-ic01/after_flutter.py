"""공유 Flutter native-assets 생성은 전체 suite 종료 뒤 순차 실행한다."""

import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
started = time.monotonic()
while (
    json.loads((HERE / "evidence/flutter-sealed.json").read_text()).get("status")
    == "RUNNING"
):
    if time.monotonic() - started > 7200:
        raise RuntimeError("full Flutter did not finish")
    time.sleep(10)
failures = []
for mode in [
    "independent-http",
    "authority",
    "overhead-flutter",
    "high-n-sample",
    "analyze",
    "build",
]:
    result = subprocess.run(
        [sys.executable, str(HERE / "run.py"), mode], cwd=HERE.parents[2]
    )
    if result.returncode:
        failures.append(mode)
print(json.dumps({"failed": failures}), flush=True)
sys.exit(int(bool(failures)))

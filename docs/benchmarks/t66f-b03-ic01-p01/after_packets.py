"""공유 native-assets 생성 충돌을 피하는 유한 순차 preflight."""

import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
deadline = time.monotonic() + 1800
while time.monotonic() < deadline:
    try:
        r = json.loads((HERE / "evidence/packets.json").read_text())
        if r.get("mode") == "packets" and r.get("status") in ["PASS", "FAIL"]:
            break
    except (ValueError, FileNotFoundError):
        pass
    time.sleep(2)
else:
    raise RuntimeError("bounded packet test did not finish")
results = []
for mode in ["components-no-profile", "cost-parts", "historical-3"]:
    r = subprocess.run(
        [sys.executable, str(HERE / "run.py"), mode], cwd=HERE.parents[2]
    )
    results.append({"mode": mode, "exit": r.returncode})
(HERE / "evidence/followups.json").write_text(json.dumps(results, indent=2) + "\n")
raise SystemExit(int(any(r["exit"] for r in results)))

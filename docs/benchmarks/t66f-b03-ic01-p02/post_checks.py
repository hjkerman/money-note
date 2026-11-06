"""최종 전체 검증 후 유한 paired 측정. 병렬 Flutter 금지."""

import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
deadline = time.monotonic() + 7200
while time.monotonic() < deadline:
    try:
        checks = json.loads((HERE / "evidence/final-checks.json").read_text())
        backend = json.loads((HERE / "evidence/backend-full.json").read_text())
        if any(r["mode"] == "frontend" for r in checks) and backend["status"] in [
            "PASS",
            "FAIL",
        ]:
            break
    except (ValueError, FileNotFoundError):
        pass
    time.sleep(2)
else:
    raise RuntimeError("bounded regression wait exhausted")
results = []
for mode in [
    "components-final",
    "preparation-final",
    "cleanup-open-final",
    "cleanup-closed-final",
    "independent-overhead",
    "authority",
    "small-http-final",
]:
    r = subprocess.run(
        [sys.executable, str(HERE / "run.py"), mode], cwd=HERE.parents[2]
    )
    results.append({"mode": mode, "exit": r.returncode})
    (HERE / "evidence/post-checks.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )
raise SystemExit(int(any(r["exit"] for r in results)))

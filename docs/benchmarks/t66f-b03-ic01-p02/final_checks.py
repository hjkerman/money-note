"""최종 source의 Flutter 검증은 native assets 충돌 없이 순차 실행한다."""

import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
results = []
for mode in [
    "flutter-targeted",
    "current-independent",
    "small-http",
    "flutter-full",
    "analyze",
    "build",
    "frontend",
]:
    result = subprocess.run(
        [sys.executable, str(HERE / "run.py"), mode], cwd=HERE.parents[2]
    )
    results.append({"mode": mode, "exit": result.returncode})
    (HERE / "evidence/final-checks.json").write_text(
        json.dumps(results, indent=2) + "\n"
    )
raise SystemExit(int(any(r["exit"] for r in results)))

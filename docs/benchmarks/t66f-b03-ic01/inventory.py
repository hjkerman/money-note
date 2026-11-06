"""시작 commit과 현재 source/역사 증거의 exact 보존 검사."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = "ebcbd54d90eeee194a04b9eea6367f446ee2fd28"
OUT = Path(__file__).resolve().parent / "evidence"
paths = (
    subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE], cwd=ROOT)
    .decode()
    .splitlines()
)
records, changed = {}, []
for path in paths:
    if path.startswith(
        (
            "docs/benchmarks/t66f-b03",
            "backend/tests/test_logical_cost",
            "mobile/lib/src/diagnostics/",
            "mobile/test/segmented_logical_cost",
            "mobile/test/support/logical_cost",
        )
    ) or path in [
        "docs/t66/c/t66c-delta-sync-protocol.md",
        "mobile/lib/src/offline/offline_store.dart",
        "docs/t66f-b03-independent-instrumentation-audit.md",
    ]:
        old = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)
        new = (ROOT / path).read_bytes()
        records[path] = {
            "starting_sha256": hashlib.sha256(old).hexdigest(),
            "current_sha256": hashlib.sha256(new).hexdigest(),
            "unchanged": old == new,
        }
        if old != new:
            changed.append(path)
value = {
    "starting_head": BASE,
    "refs": subprocess.check_output(
        ["git", "rev-parse", "HEAD", "main", "origin/main"], cwd=ROOT
    )
    .decode()
    .splitlines(),
    "staged": subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"], cwd=ROOT
    )
    .decode()
    .splitlines(),
    "files": records,
    "changed_existing": changed,
}
OUT.mkdir(exist_ok=True)
(OUT / "preservation.json").write_text(
    json.dumps(value, ensure_ascii=False, indent=2) + "\n"
)
print(
    json.dumps(
        {
            "reviewed": len(records),
            "changed_existing": changed,
            "staged": value["staged"],
        }
    )
)

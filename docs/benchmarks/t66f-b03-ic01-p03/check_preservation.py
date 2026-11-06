"""시작 파일과 Git index를 읽기만 하여 보존 여부를 기록한다."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "evidence"
start = json.loads((OUT / "starting-state.json").read_text())
allowed = (
    {"docs/t66f-b03-ic01-targeted-correction.md"}
    if "--completion-report-authorized" in sys.argv
    else set()
)
changed = []
for name, expected in start["files"].items():
    path = ROOT / name
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if expected != actual:
        changed.append({"path": name, "before": expected, "after": actual})
index = hashlib.sha256((ROOT / ".git/index").read_bytes()).hexdigest()
entries = subprocess.check_output(
    ["git", "--no-optional-locks", "ls-files", "--stage", "-z"], cwd=ROOT
)
status = subprocess.check_output(
    ["git", "--no-optional-locks", "status", "--short"], cwd=ROOT, text=True
)
entry_sha = hashlib.sha256(entries).hexdigest()
historical_sha = json.loads((OUT / "source-preservation.json").read_text())[
    "index_entries_z_sha256"
]
result = {
    "original_files_checked": len(start["files"]),
    "original_file_changes": changed,
    "authorized_completion_report_changes": sorted(allowed),
    "unexpected_changes": [v for v in changed if v["path"] not in allowed],
    "index_file_sha256": index,
    "index_entries_z_sha256": entry_sha,
    "index_preserved": index == start["index_sha256"] and entry_sha == historical_sha,
    "status": status,
}
(OUT / "final-preservation.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
assert not result["unexpected_changes"]
assert result["index_preserved"]
print(
    json.dumps(
        {"checked": len(start["files"]), "unexpected": 0, "index_preserved": True}
    )
)

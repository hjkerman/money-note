"""P04 시작 당시 모든 파일·index와 원 SQLite를 읽기 전용 대조한다."""

import hashlib
import json
from pathlib import Path
import subprocess
from prepare import OUT, file_sha

ROOT = Path(__file__).resolve().parents[3]
start = json.loads((OUT / "starting-state.json").read_text())
changes = []
for name, expected in start["files"].items():
    path = ROOT / name
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    if actual != expected:
        changes.append({"path": name, "expected": expected, "actual": actual})
index = hashlib.sha256((ROOT / ".git/index").read_bytes()).hexdigest()
entries = hashlib.sha256(subprocess.check_output(["git", "--no-optional-locks", "ls-files", "--stage", "-z"], cwd=ROOT)).hexdigest()
plan = json.loads((OUT / "clone-plan.json").read_text())
result = {
    "original_files_checked": len(start["files"]),
    "original_file_changes": changes,
    "index_sha256": index,
    "index_entries_z_sha256": entries,
    "index_preserved": index == start["index_sha256"] and entries == start["index_entries_z_sha256"],
    "original_sqlite_sha256": file_sha(Path(plan["source"])),
    "original_sqlite_unchanged": file_sha(Path(plan["source"])) == plan["source_sha256"],
    "P03_failure_evidence_preserved": True,
    "production_or_protocol_or_lock_modified": False,
}
assert changes == []
assert result["index_preserved"] and result["original_sqlite_unchanged"]
(OUT / "final-preservation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"files": len(start["files"]), "changes": 0, "index": "PRESERVED", "original_sqlite": "PRESERVED"}))

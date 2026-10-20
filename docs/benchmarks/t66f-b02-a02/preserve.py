"""원 입력·logical index·binary diff를 읽기 전용 비교한다. stage/commit 없음."""

from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
initial = json.loads((HERE / "initial-state.json").read_text())


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


changed = []
missing = []
for name, expected in initial["files"].items():
    p = ROOT / name
    if not p.is_file():
        missing.append(name)
    elif hashlib.sha256(p.read_bytes()).hexdigest() != expected:
        changed.append(name)
files = [
    p
    for p in git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    .decode()
    .split("\0")
    if p and (ROOT / p).is_file()
]
new = sorted(set(files) - set(initial["files"]))


def allowed(p):
    return (
        p.startswith("docs/benchmarks/t66f-b02-a02/")
        or p == "docs/t66f-b02-a02-100k-acquisition-investigation.md"
    )


result = {
    "head": git("rev-parse", "HEAD").decode().strip(),
    "refs": git("rev-parse", "HEAD", "main", "origin/main").decode().splitlines(),
    "actual_remote_main": git("ls-remote", "origin", "refs/heads/main")
    .decode()
    .strip(),
    "original_files_checked": len(initial["files"]),
    "changed_original_files": changed,
    "missing_original_files": missing,
    "index_entries_equal": git("ls-files", "--stage", "-z").decode()
    == initial["index"],
    "staged_binary_diff_equal": hashlib.sha256(
        git("diff", "--cached", "--binary")
    ).hexdigest()
    == initial["staged_diff_sha256"],
    "unstaged_binary_diff_equal": hashlib.sha256(git("diff", "--binary")).hexdigest()
    == initial["unstaged_diff_sha256"],
    "new_files_only_investigation": all(allowed(p) for p in new),
    "new_files": new,
    "final_status": git("status", "--short").decode(),
    "final_diff_stat": git("diff", "--stat").decode(),
    "commit_performed": False,
    "push_performed": False,
    "index_mutation_performed": False,
    "ignored_generated_files": "검사 중 .pyc 및 Dart/npm build cache는 기존 ignore 범위; 생산 artifact 설치 없음",
}
assert (
    not changed
    and not missing
    and result["index_entries_equal"]
    and result["staged_binary_diff_equal"]
    and result["unstaged_binary_diff_equal"]
    and result["new_files_only_investigation"]
), result
(HERE / "final-preservation.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(
    json.dumps(
        {
            k: result[k]
            for k in [
                "head",
                "original_files_checked",
                "changed_original_files",
                "missing_original_files",
                "index_entries_equal",
                "staged_binary_diff_equal",
                "unstaged_binary_diff_equal",
                "new_files_only_investigation",
            ]
        },
        ensure_ascii=False,
    )
)

"""최초 파일 내용·논리 index와 최종을 비교한다. Git mutation 없음."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    initial = json.loads((HERE / "initial-state.json").read_text())
    mismatches = []
    for name, expected in initial["all_existing_hashes"].items():
        p = ROOT / name
        if not p.is_file() or sha(p.read_bytes()) != expected:
            mismatches.append(name)
    refs = {
        r: git("rev-parse", r).decode().strip() for r in ["HEAD", "main", "origin/main"]
    }
    refs["actual_remote_main"] = (
        git("ls-remote", "origin", "refs/heads/main").decode().split()[0]
    )
    index = sha(git("ls-files", "--stage", "-z"))
    staged = sha(git("diff", "--cached", "--binary"))
    raw_diff = git("diff", "--binary")
    untracked = [
        p
        for p in git("ls-files", "--others", "--exclude-standard", "-z")
        .decode()
        .split("\0")
        if p
    ]
    old = set(initial["original_untracked"])
    current = dict(
        refs=refs,
        status=git("status", "--short").decode(),
        diff_stat=git("diff", "--stat").decode(),
        original_files=len(initial["all_existing_hashes"]),
        mismatches=mismatches,
        original_products_unchanged=all(
            name not in mismatches for name in initial["product_hashes"]
        ),
        staged_preserved=staged == initial["staged_diff_sha256"],
        index_entries_preserved=index == initial["index_entries_sha256"],
        original_tracked_diff_preserved=raw_diff
        == gzip.decompress((HERE / "worktree.diff.gz").read_bytes()),
        new_nonignored_artifacts=[p for p in untracked if p not in old],
        new_commit=False,
        push_performed=False,
        expected_dirty=True,
    )
    (HERE / "preservation-final.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n"
    )
    assert not mismatches, mismatches
    assert (
        current["staged_preserved"]
        and current["index_entries_preserved"]
        and current["original_tracked_diff_preserved"]
    )
    assert refs == initial["refs"], refs
    print(
        json.dumps(
            {
                k: current[k]
                for k in [
                    "original_files",
                    "mismatches",
                    "original_products_unchanged",
                    "staged_preserved",
                    "index_entries_preserved",
                    "original_tracked_diff_preserved",
                ]
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

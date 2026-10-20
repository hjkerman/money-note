"""기존 dirty worktree와 index를 변경하지 않고 입력 SHA를 고정한다."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    expected = "6282c1c3577c42bba9382d786745d583a5d88236"
    refs = {
        r: git("rev-parse", r).decode().strip() for r in ["HEAD", "main", "origin/main"]
    }
    refs["actual_remote_main"] = (
        git("ls-remote", "origin", "refs/heads/main").decode().split()[0]
    )
    assert set(refs.values()) == {expected}, refs
    tracked = git("ls-files", "-z").decode().split("\0")
    untracked = (
        git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    )
    paths = sorted(
        set(
            p
            for p in tracked + untracked
            if p and not p.startswith("docs/benchmarks/t66f-b02-a01/")
        )
    )
    hashes = {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        for p in paths
        if (ROOT / p).is_file()
    }
    products = [
        "mobile/lib/src/app_state.dart",
        "mobile/lib/src/segmented/fetch.dart",
        "mobile/lib/src/segmented/store.dart",
    ]
    assert all(git("diff", "--numstat", "--", p) for p in products), (
        "예상 미커밋 제품 변경 누락"
    )
    for name, args in [
        ("worktree.diff.gz", ["diff", "--binary"]),
        ("index.diff.gz", ["diff", "--cached", "--binary"]),
    ]:
        with gzip.GzipFile(str(HERE / name), "wb", mtime=0) as stream:
            stream.write(git(*args))
    record = dict(
        refs=refs,
        branch=git("branch", "--show-current").decode().strip(),
        status=git("status", "--short").decode(),
        diff_stat=git("diff", "--stat").decode(),
        diff_name_status=git("diff", "--name-status").decode(),
        staged_name_status=git("diff", "--cached", "--name-status").decode(),
        staged_diff_sha256=hashlib.sha256(
            git("diff", "--cached", "--binary")
        ).hexdigest(),
        index_entries_sha256=hashlib.sha256(
            git("ls-files", "--stage", "-z")
        ).hexdigest(),
        original_untracked=[
            p
            for p in untracked
            if p and not p.startswith("docs/benchmarks/t66f-b02-a01/")
        ],
        product_hashes={p: hashes[p] for p in products},
        all_existing_hashes=hashes,
    )
    (HERE / "initial-state.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )
    print("기존 입력 보호:", len(hashes), "files; dirty 제품3개; index 변경 없음")


if __name__ == "__main__":
    main()

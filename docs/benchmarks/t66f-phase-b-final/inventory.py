"""시작 tracked tree와 역사 증거의 lineage를 읽기 전용으로 기록한다."""

import hashlib
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = "ae0f37250c8f54893cb2ac5eab1d3c9844a7d983"
ORIGINAL = "c479a379b54e196439c522c1fdf56eca713ca8ad"
PRODUCT = "1cabf319f0ac2c2069e804b47cb527b55e3374db"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = git("ls-tree", "-r", "--name-only", BASE).splitlines()
    files = {p: digest(ROOT / p) for p in paths}
    assert git("rev-parse", "HEAD") == BASE
    assert all(git("rev-parse", ref) == BASE for ref in ["main", "origin/main"])
    remote = git("ls-remote", "origin", "refs/heads/main")
    assert remote.split()[0] == BASE
    old = json.loads(
        (ROOT / "docs/benchmarks/t66f-b02-independent/inventory.json").read_text()
    )
    old_mismatches = [
        p for p, expected in old["files"].items() if digest(ROOT / p) != expected
    ]
    assert old_mismatches == []
    commits = git("rev-list", "--reverse", ORIGINAL + ".." + BASE).splitlines()
    changes = []
    for commit in commits:
        changed = git(
            "diff-tree", "--no-commit-id", "--name-only", "-r", commit
        ).splitlines()
        changes.append(
            dict(
                commit=commit,
                subject=git("show", "-s", "--format=%s", commit),
                files=changed,
            )
        )
    record = dict(
        starting_head=BASE,
        local_main=git("rev-parse", "main"),
        origin_main=git("rev-parse", "origin/main"),
        actual_remote_main=remote,
        starting_tree=git("rev-parse", BASE + "^{tree}"),
        initial_worktree="clean — 첫 read-only git status 출력으로 확인",
        observed_worktree=git("status", "--short"),
        files=files,
        prior_b02_inventory_files=len(old["files"]),
        prior_b02_mismatches=old_mismatches,
        audited_product=PRODUCT,
        product_delta_since_b02=git(
            "diff",
            "--name-only",
            PRODUCT,
            BASE,
            "--",
            "backend",
            "mobile/lib",
            "frontend",
            "scripts",
        ),
        changes_since_original=changes,
        environment=dict(
            python=sys.version,
            sqlite=sqlite3.sqlite_version,
            platform=platform.platform(),
            cpu=platform.processor(),
            affinity_cpus=len(os.sched_getaffinity(0)),
            page_size=os.sysconf("SC_PAGE_SIZE"),
        ),
    )
    (HERE / "inventory.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            dict(
                tracked=len(files),
                b02_compared=len(old["files"]),
                mismatches=len(old_mismatches),
                commits=len(changes),
            )
        )
    )


if __name__ == "__main__":
    main()

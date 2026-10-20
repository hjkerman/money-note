"""A02 교정 시작점·index·역사 증거의 byte 보존 기록."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    start = HERE / "initial-state.json"
    if len(sys.argv) == 1:
        assert not start.exists()
        paths = set(
            git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
            .decode()
            .split("\0")
        )
        files = {
            p: sha((ROOT / p).read_bytes())
            for p in sorted(paths)
            if p
            and (ROOT / p).is_file()
            and not p.startswith("docs/benchmarks/t66f-b02-a02-correction/")
        }
        for name in (
            "backend/isolated_sync/canonical.py",
            "mobile/lib/src/segmented/fetch.dart",
        ):
            (HERE / (Path(name).name + ".before.gz")).write_bytes(
                gzip.compress((ROOT / name).read_bytes(), mtime=0)
            )
        (HERE / "original-worktree.diff.gz").write_bytes(
            gzip.compress(git("diff", "--binary"), mtime=0)
        )
        value = dict(
            files=files,
            index=sha(git("ls-files", "--stage", "-z")),
            staged=sha(git("diff", "--cached", "--binary")),
            status=git("status", "--short").decode(),
            refs={
                r: git("rev-parse", r).decode().strip()
                for r in ("HEAD", "main", "origin/main")
            },
        )
        start.write_text(json.dumps(value, indent=2) + "\n")
        print("preserved", len(files), "files")
    else:
        old = json.loads(start.read_text())
        changed = {
            p: dict(
                old=h,
                new=sha((ROOT / p).read_bytes()) if (ROOT / p).is_file() else None,
            )
            for p, h in old["files"].items()
            if not (ROOT / p).is_file() or sha((ROOT / p).read_bytes()) != h
        }
        value = dict(
            changed=changed,
            index_preserved=old["index"] == sha(git("ls-files", "--stage", "-z")),
            staged_preserved=old["staged"] == sha(git("diff", "--cached", "--binary")),
            status=git("status", "--short").decode(),
        )
        (HERE / "preservation-final.json").write_text(
            json.dumps(value, indent=2) + "\n"
        )
        print(json.dumps(value))


if __name__ == "__main__":
    main()

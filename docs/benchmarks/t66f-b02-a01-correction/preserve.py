"""원 dirty B02·조사 파일과 index의 logical 상태를 고정/대조한다."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRODUCTS = {
    "mobile/lib/src/app_state.dart": "c1d65f36dbd09a5f33b4a5d8d0e8b7a67ea429b0811592fce32aaeb65f9c46c1",
    "mobile/lib/src/segmented/fetch.dart": "94a99947e4bdf408124e74aca43f7f4c6c3c2738ab9a76c0ffd77aaeb9285b37",
    "mobile/lib/src/segmented/store.dart": "f2b451238b868b865beda40cfb39054d9c4a3ff36b5e27c7796b2759ee07811a",
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    snapshot = HERE / "initial-state.json"
    if len(sys.argv) == 1:
        if snapshot.exists():
            raise ValueError("최초 evidence를 덮어쓰지 않는다")
        paths = set(
            p
            for p in git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
            .decode()
            .split("\0")
            if p and not p.startswith("docs/benchmarks/t66f-b02-a01-correction/")
        )
        hashes = {
            p: digest((ROOT / p).read_bytes())
            for p in sorted(paths)
            if (ROOT / p).is_file()
        }
        assert all(hashes[p] == h for p, h in PRODUCTS.items()), (
            "기존 B02 source 불일치"
        )
        refs = {
            p: git("rev-parse", p).decode().strip()
            for p in ("HEAD", "main", "origin/main")
        }
        assert set(refs.values()) == {"6282c1c3577c42bba9382d786745d583a5d88236"}
        value = dict(
            refs=refs,
            status=git("status", "--short").decode(),
            files=hashes,
            index=digest(git("ls-files", "--stage", "-z")),
            staged=digest(git("diff", "--cached", "--binary")),
        )
        for name, args in (
            ("original-worktree.diff.gz", ("diff", "--binary")),
            ("original-index.diff.gz", ("diff", "--cached", "--binary")),
        ):
            (HERE / name).write_bytes(gzip.compress(git(*args), mtime=0))
        # Exact old resolver/frontier for test-only differential comparison.
        for name in (
            "backend/isolated_sync/transfer.py",
            "mobile/lib/src/segmented/fetch.dart",
        ):
            (HERE / (Path(name).name + ".before.gz")).write_bytes(
                gzip.compress((ROOT / name).read_bytes(), mtime=0)
            )
        snapshot.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        print("최초 보존", len(hashes), "files; 예상 dirty B02 일치")
    else:
        old = json.loads(snapshot.read_text())
        changed = [
            p
            for p, h in old["files"].items()
            if not (ROOT / p).is_file() or digest((ROOT / p).read_bytes()) != h
        ]
        value = dict(
            changed=changed,
            current_refs={
                name: git("rev-parse", name).decode().strip()
                for name in ("HEAD", "main", "origin/main")
            },
            current_status=git("status", "--short").decode(),
            current_source_sha256={
                p: digest((ROOT / p).read_bytes())
                for p in sorted(set(changed) | set(PRODUCTS))
            },
            index_preserved=old["index"] == digest(git("ls-files", "--stage", "-z")),
            staged_preserved=old["staged"]
            == digest(git("diff", "--cached", "--binary")),
        )
        (HERE / "preservation-final.json").write_text(
            json.dumps(value, indent=2) + "\n"
        )
        print(json.dumps(value))


if __name__ == "__main__":
    main()

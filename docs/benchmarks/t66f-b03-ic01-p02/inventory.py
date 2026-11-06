"""P02 시작 파일/index와 전체 원 diff를 보존한다. Git 쓰기 없음."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "evidence"
OUT.mkdir(exist_ok=True)
ALLOWED = {"mobile/test/support/logical_cost_sqlite.dart"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    target = OUT / "starting-state.json"
    if "--check" in sys.argv:
        old = json.loads(target.read_text())
        changed = [
            p
            for p, h in old["files"].items()
            if not (ROOT / p).is_file() or sha((ROOT / p).read_bytes()) != h
        ]
        result = {
            "changed_preexisting": changed,
            "unauthorized_changes": sorted(set(changed) - ALLOWED),
            "index_preserved": old["index_sha256"]
            == sha(git("ls-files", "--stage", "-z")),
        }
        (OUT / "preservation.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        assert not result["unauthorized_changes"] and result["index_preserved"]
        return
    assert not target.exists()
    names = sorted(
        set(
            git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
            .decode()
            .split("\0")
        )
    )
    value = {
        "refs": git("rev-parse", "HEAD", "main", "origin/main").decode().splitlines(),
        "remote": git("ls-remote", "origin", "refs/heads/main").decode().strip(),
        "status": git("status", "--short").decode(),
        "staged": git("diff", "--cached", "--name-only").decode(),
        "unstaged": git("diff", "--name-only").decode(),
        "untracked": git("ls-files", "--others", "--exclude-standard").decode(),
        "index_sha256": sha(git("ls-files", "--stage", "-z")),
        "files": {
            p: sha((ROOT / p).read_bytes())
            for p in names
            if p
            and (ROOT / p).is_file()
            and not p.startswith("docs/benchmarks/t66f-b03-ic01-p02/")
        },
    }
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    (OUT / "starting-unstaged.patch").write_bytes(git("diff", "--binary"))
    (OUT / "starting-staged.patch").write_bytes(git("diff", "--cached", "--binary"))
    (OUT / "original-logical-cost-sqlite.dart.txt").write_bytes(
        (ROOT / "mobile/test/support/logical_cost_sqlite.dart").read_bytes()
    )
    print(
        json.dumps(
            {
                "files": len(value["files"]),
                "refs": value["refs"],
                "staged": value["staged"],
            }
        )
    )


if __name__ == "__main__":
    main()

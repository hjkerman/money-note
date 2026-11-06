"""P01 이전 tracked/미추적 파일과 index를 보존한다. Git 쓰기 없음."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"
OUT.mkdir(exist_ok=True)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    target = OUT / "starting-state.json"
    if "--check" in sys.argv:
        old = json.loads(target.read_text())
        changed = [
            p
            for p, sha in old["files"].items()
            if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != sha
        ]
        index_same = (
            hashlib.sha256(git("ls-files", "--stage", "-z")).hexdigest()
            == old["index_sha256"]
        )
        result = {"changed_preexisting": changed, "index_preserved": index_same}
        (OUT / "preservation.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        assert not changed and index_same
        return
    assert not target.exists(), "시작 증거를 덮어쓰지 않음"
    names = (
        git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
        .decode()
        .split("\0")
    )
    names = sorted(
        p
        for p in set(names)
        if p and not p.startswith(str(HERE.relative_to(ROOT)) + "/")
    )
    value = {
        "refs": git("rev-parse", "HEAD", "main", "origin/main").decode().splitlines(),
        "actual_remote": git("ls-remote", "origin", "refs/heads/main").decode().strip(),
        "status": git("status", "--short").decode().splitlines(),
        "staged": git("diff", "--cached", "--name-only").decode().splitlines(),
        "unstaged": git("diff", "--name-only").decode().splitlines(),
        "untracked": git("ls-files", "--others", "--exclude-standard")
        .decode()
        .splitlines(),
        "index_sha256": hashlib.sha256(git("ls-files", "--stage", "-z")).hexdigest(),
        "files": {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in names
            if (ROOT / p).is_file()
        },
    }
    (OUT / "starting-unstaged.patch").write_bytes(git("diff", "--binary"))
    (OUT / "starting-staged.patch").write_bytes(git("diff", "--cached", "--binary"))
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "files": len(value["files"]),
                "staged": value["staged"],
                "unstaged": value["unstaged"],
            }
        )
    )


if __name__ == "__main__":
    main()

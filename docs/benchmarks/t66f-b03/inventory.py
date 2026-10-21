"""B03 clean 기준선과 합성 계측 대상의 SHA를 보존한다."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "evidence"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode()


def main():
    OUT.mkdir(exist_ok=True)
    destination = OUT / "initial.json"
    if destination.exists():
        raise RuntimeError("시작 증거는 덮어쓰지 않는다")
    files = git("ls-files", "-z").split("\0")
    result = {
        "head": git("rev-parse", "HEAD").strip(),
        "main": git("rev-parse", "main").strip(),
        "origin_main": git("rev-parse", "origin/main").strip(),
        "remote_main": git("ls-remote", "origin", "refs/heads/main").strip(),
        "status": git("status", "--short"),
        "staged": git("diff", "--cached", "--name-status"),
        "sha256": {
            p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in files
            if p and (ROOT / p).is_file()
        },
    }
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "sha256"}))


if __name__ == "__main__":
    main()

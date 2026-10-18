"""B02 시작 identity와 기존 모든 tracked bytes를 보호한다."""

import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


refs = {r: git("rev-parse", r) for r in ["HEAD", "main", "origin/main"]}
refs["actual_remote_main"] = git("ls-remote", "origin", "refs/heads/main").split()[0]
assert set(refs.values()) == {"c591a7a0d10b208ed0c0e7efd239576f91052c66"}
paths = git("ls-files").splitlines()
hashes = {
    p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
    for p in paths
    if (ROOT / p).is_file()
}
(HERE / "protected-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
(HERE / "repository.json").write_text(
    json.dumps(
        dict(
            refs=refs,
            branch=git("branch", "--show-current"),
            tree=git("rev-parse", "HEAD^{tree}"),
            initial_clean_verified_before_artifact_creation=True,
            status_after_own_script=git("status", "--short"),
        ),
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
print("시작 refs와 기존 tracked SHA 기록:", len(hashes))

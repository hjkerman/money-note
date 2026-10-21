"""시작 commit 원본·전체 B03 diff·raw evidence의 독립 무결성 inventory."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "da818648031e013e83dd6a680b1b1bde0fb6e0a1"
HEAD = "ea2c32ce75a5f6894f52dc1b8fb4e2b1ae6df478"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    changed = (
        git("diff", "--name-only", BASE, HEAD, "-z").decode().strip("\0").split("\0")
    )
    evidence = {}
    for name in changed:
        path = ROOT / name
        raw = path.read_bytes()
        record = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        if path.suffix == ".json":
            value = json.loads(raw)
            record["json_valid"] = True
            if isinstance(value, dict):
                record["keys"] = list(value)[:30]
        if path.suffix == ".gz":
            contents = gzip.decompress(raw)
            record.update(
                gzip_valid=True,
                decoded_bytes=len(contents),
                decoded_sha256=hashlib.sha256(contents).hexdigest(),
            )
            if path.name.endswith("jsonl.gz"):
                counts = {}
                errors = []
                for line in contents.splitlines():
                    try:
                        event = json.loads(line)
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if not isinstance(event, dict):
                        continue
                    if event.get("type") == "testDone" and not event.get(
                        "hidden", False
                    ):
                        status = "SKIP" if event.get("skipped") else event.get("result")
                        counts[status] = counts.get(status, 0) + 1
                    if event.get("type") == "error":
                        errors.append(event.get("error"))
                record.update(machine_counts=counts, errors=errors)
        if path.suffix == ".xml":
            tree = ET.fromstring(raw)
            record["junit"] = {
                tag: len(list(tree.iter(tag)))
                for tag in ["testcase", "failure", "error", "skipped"]
            }
        evidence[name] = record
    tracked = {}
    mismatches = []
    for row in git("ls-tree", "-rz", HEAD).split(b"\0"):
        if not row:
            continue
        metadata, name = row.split(b"\t", 1)
        path = name.decode()
        blob = metadata.split()[2].decode()
        original = git("cat-file", "blob", blob)
        actual = (ROOT / path).read_bytes()
        tracked[path] = dict(blob=blob, sha256=hashlib.sha256(original).hexdigest())
        if actual != original:
            mismatches.append(path)
    source_review = json.loads(
        (HERE.parent / "t66f-b03/source-lock-review.json").read_text()
    )
    locks = {}
    for path, info in source_review["files"].items():
        current = (ROOT / path).read_text()
        restored = current
        for replacement in info.get("exact_replacements", []):
            assert restored.count(replacement["reviewed"]) == 1
            restored = restored.replace(
                replacement["reviewed"], replacement["historical"]
            )
        sha = hashlib.sha256(current.encode()).hexdigest()
        historical = hashlib.sha256(restored.encode()).hexdigest()
        assert sha == info["reviewed_sha256"]
        if info.get("historical_sha256"):
            assert historical == info["historical_sha256"]
            assert restored.encode() == git("show", BASE + ":" + path)
        locks[path] = dict(current=sha, restored=historical, exact_match=True)
    result = dict(
        baseline=BASE,
        starting_head=HEAD,
        refs=git("rev-parse", "HEAD", "main", "origin/main").decode().splitlines(),
        actual_remote=git("ls-remote", "origin", "refs/heads/main").decode().strip(),
        original_tracked_count=len(tracked),
        original_files=tracked,
        original_worktree_mismatches=mismatches,
        changed_count=len(changed),
        b03_changed=evidence,
        exact_locks=locks,
        receipt_diff=git("diff", "--name-status", "a96e130", HEAD).decode(),
        status=git("status", "--short").decode(),
    )
    (HERE / "evidence/inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            dict(
                changed_count=len(changed),
                original_tracked_count=len(tracked),
                mismatches=mismatches,
                source_locks=len(locks),
            )
        )
    )


if __name__ == "__main__":
    main()

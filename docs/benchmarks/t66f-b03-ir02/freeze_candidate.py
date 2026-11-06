"""IR01 승인 inventory만 동결한다. 기존 source/index 및 과거 증거를 쓰지 않는다."""

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
import time

from verify_snapshot import BASE, PAYLOAD, check_source_tree, digest, file_digest

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
IR01 = ROOT / "docs/benchmarks/t66f-b03-ir01"


class CandidateChanged(RuntimeError):
    pass


def git(*args):
    return subprocess.check_output(["git", "--no-optional-locks", *args], cwd=ROOT)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def exclusive(path, data, mode=0o600):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def signature(value):
    return [
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
        value.st_mode & 0o777,
    ]


def safe_read(relative, expected_signature=None):
    parts = Path(relative).parts
    if Path(relative).is_absolute() or ".." in parts:
        raise CandidateChanged("unsafe source path: " + relative)
    fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            next_fd = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
            )
            os.close(fd)
            fd = next_fd
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        with os.fdopen(leaf, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or (
                expected_signature and signature(before) != expected_signature
            ):
                raise CandidateChanged(relative)
            data = stream.read()
            if signature(os.fstat(stream.fileno())) != signature(before):
                raise CandidateChanged(relative)
        return data
    finally:
        os.close(fd)


def check_live(manifest, preflight):
    differences = []
    for entry in manifest["entries"]:
        try:
            raw = safe_read(entry["path"], preflight["signatures"][entry["path"]])
            if digest(raw) != entry["worktree"]["sha256"]:
                differences.append(entry["path"])
        except (OSError, CandidateChanged):
            differences.append(entry["path"])
    if file_digest(ROOT / ".git/index") != preflight["index_sha256"]:
        differences.append("GIT_INDEX")
    if git("rev-parse", "HEAD").decode().strip() != BASE:
        differences.append("HEAD")
    if (
        git("diff", "--name-status").decode() != preflight["unstaged"]
        or git("diff", "--cached", "--name-status").decode() != preflight["staged"]
    ):
        differences.append("TRACKED_STATUS")
    untracked = set(
        git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    ) - {""}
    added = untracked - set(preflight["untracked_paths"])
    unexpected = [
        p
        for p in added
        if not p.startswith("docs/benchmarks/t66f-b03-ir02/")
        and p != "docs/t66f-b03-ir02-audit-candidate-freeze.md"
    ]
    differences.extend(unexpected)
    if differences:
        (OUT / "blocked-differences.json").write_bytes(
            encoded(dict(status="BLOCKED", differences=differences))
        )
        raise CandidateChanged("candidate changed; see blocked-differences.json")


def cleanup_owned(directory):
    """이 실행이 배타적으로 생성한 scratch의 정확한 leaf만 지운다."""
    directory = Path(directory)
    assert directory.name.startswith("ir02-verify-") and not directory.is_symlink()
    files = sorted(p for p in directory.rglob("*") if p.is_file() or p.is_symlink())
    directories = sorted(
        [p for p in directory.rglob("*") if p.is_dir()],
        key=lambda p: len(p.parts),
        reverse=True,
    )
    # verifier child/Git batch는 이미 종료됐으며 payload code/SQLite는 실행하지 않았다.
    active = []
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            descriptors = list((process / "fd").iterdir())
        except OSError:
            continue
        for descriptor in descriptors:
            try:
                target = os.readlink(descriptor)
            except OSError:
                continue
            if target.startswith(str(directory) + "/"):
                active.append(dict(pid=int(process.name), path=target))
    assert not active, "scratch still in use"
    rows = []
    for path in files:
        before = path.lstat()
        assert (
            not path.is_symlink()
            and path.is_relative_to(directory)
            and before.st_nlink == 1
        )
        row = dict(
            path=str(path),
            bytes=before.st_size,
            allocated=before.st_blocks * 512,
            device=before.st_dev,
            inode=before.st_ino,
            ownership="IR02 새 private verification root의 추출/base-overlay 중복 사본",
            no_active_use="verifier/Git 종료·open descriptor 검사0·제품 code/SQLite 미실행",
        )
        now = path.lstat()
        assert signature(now) == signature(before)
        path.unlink()
        row["deleted"] = not path.exists()
        rows.append(row)
    for path in directories:
        path.rmdir()
    directory.rmdir()
    return dict(
        status="COMPLETE",
        files=rows,
        file_count=len(rows),
        allocated=sum(r["allocated"] for r in rows),
        verification_root=str(directory),
        root_removed=not directory.exists(),
        pre_existing_files_deleted=0,
        recursive_delete_used=False,
    )


def main(destination):
    manifest_raw = safe_read(
        "docs/benchmarks/t66f-b03-ir01/candidate-source-manifest.json"
    )
    manifest = json.loads(manifest_raw)
    preflight = json.loads((OUT / "preflight.json").read_text())
    assert (
        preflight["status"] == "PASS"
        and manifest["candidate_payload_sha256"] == PAYLOAD
    )
    assert digest(manifest_raw) == preflight["ir01_manifest_sha256"]
    check_live(manifest, preflight)
    destination = Path(destination).absolute()
    assert not destination.is_relative_to(ROOT) and not destination.exists()
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert destination.parent.resolve() == destination.parent, "symlink storage parent"
    destination.mkdir(mode=0o700, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="ir02-verify-", dir=destination.parent))
    (OUT / "task-ownership.json").write_bytes(
        encoded(
            dict(
                snapshot_directory=str(destination),
                verification_root=str(scratch),
                created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                exclusive_creation=True,
            )
        )
    )
    metadata = {}
    support = [
        "candidate-source-manifest.json",
        "candidate-identity.json",
        "candidate-consistency.json",
        "read-only-checks.json",
        "finding-readiness.json",
        "requirement-ownership.json",
        "four-propositions.json",
        "reaudit-plan.json",
        "evidence-review.json",
        "summary.json",
    ]
    support_signatures = {}
    for name in support:
        relative = "docs/benchmarks/t66f-b03-ir01/" + name
        raw = safe_read(relative)
        metadata["metadata/ir01/" + name] = raw
        support_signatures[relative] = digest(raw)
    scope_path = "docs/t66f-b03-ir01-independent-reaudit-scope.md"
    metadata["metadata/ir01/scope.md"] = safe_read(scope_path)
    support_signatures[scope_path] = digest(metadata["metadata/ir01/scope.md"])
    metadata["metadata/base-commit.txt"] = git("cat-file", "commit", BASE)
    metadata["metadata/verify_snapshot.py"] = (
        Path(__file__).with_name("verify_snapshot.py").read_bytes()
    )
    metadata["metadata/freeze_candidate.py"] = Path(__file__).read_bytes()
    changes = [
        e["path"]
        for e in manifest["entries"]
        if e["base"]
        and (
            e["worktree"]["sha256"] != e["base"]["sha256"]
            or int(e["worktree"]["mode"], 8) != int(e["base"]["mode"], 8) & 0o777
        )
    ]
    untracked = [e["path"] for e in manifest["entries"] if e["index"] is None]
    freeze = dict(
        schema_version=1,
        HEAD=BASE,
        base_tree=manifest["committed_base_tree"],
        candidate_payload_sha256=PAYLOAD,
        candidate_files=819,
        candidate_bytes=9085052,
        index_sha256=preflight["index_sha256"],
        staged=preflight["staged"],
        unstaged=preflight["unstaged"],
        tracked_deletions=preflight["tracked_deletions"],
        tracked_worktree_overrides=changes,
        untracked_source_files=untracked,
        staged_deletions=[],
        unstaged_deletions=[],
        inventory_verification_self_contained=True,
        full_checkout_requires_base_commit=True,
        mutable_worktree_content_required=False,
        archive_symlinks_or_hardlinks=False,
        source_locks=preflight["source_locks"],
        creation_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        authorization="IR02 사용자의 source-only snapshot 및 IR01 scoped B03 audit 경계 채택 승인",
        scoped_audit="다음 구현 비관여 Codex XHigh 세션. full instrumented100k cold를 B03-only 추가 선행조건으로 요구하지 않되 새 binding 증거는 검토",
        still_unverified=[
            "five-point fixed-H/D N grid",
            "E3 I25 scaling",
            "full-scale measurement feasibility",
            "runtime perturbation",
            "Android",
            "hardware power-loss",
            "R1",
        ],
        B03_independent_audit="OPEN",
        commit="NONE",
        push="NOT PERFORMED",
    )
    metadata["metadata/freeze.json"] = encoded(freeze)
    archive = destination / "candidate.tar.gz"
    partial = destination / "candidate.tar.gz.partial"
    members = []
    with open(partial, "xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(
                mode="w|", fileobj=compressed, format=tarfile.PAX_FORMAT
            ) as tar:

                def add(name, data, mode):
                    info = tarfile.TarInfo(name)
                    info.size, info.mode, info.mtime = len(data), mode, 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    tar.addfile(info, io.BytesIO(data))
                    members.append(
                        dict(
                            path=name,
                            bytes=len(data),
                            mode=oct(mode),
                            sha256=digest(data),
                        )
                    )

                for entry in manifest["entries"]:
                    relative = entry["path"]
                    data = safe_read(relative, preflight["signatures"][relative])
                    assert digest(data) == entry["worktree"]["sha256"]
                    add("source/" + relative, data, int(entry["worktree"]["mode"], 8))
                for name, data in sorted(metadata.items()):
                    add(name, data, 0o444)
        raw.flush()
        os.fsync(raw.fileno())
    check_live(manifest, preflight)
    for relative, expected in support_signatures.items():
        if digest(safe_read(relative)) != expected:
            raise CandidateChanged(relative)
    partial.rename(archive)
    archive_sha = file_digest(archive)
    integrity = dict(
        schema_version=1,
        archive_sha256=archive_sha,
        archive_bytes=archive.stat().st_size,
        candidate_payload_sha256=PAYLOAD,
        source_manifest_sha256=digest(manifest_raw),
        baseline_commit=BASE,
        candidate_files=819,
        metadata_files=len(metadata),
        source_bytes=9085052,
        members=members,
        inventory_verification_self_contained=True,
        full_checkout_requires_base_commit=True,
        source_locks="PASS — static integrity only",
    )
    exclusive(destination / "snapshot-integrity.json", encoded(integrity))
    verifier = destination / "verify_snapshot.py"
    exclusive(verifier, metadata["metadata/verify_snapshot.py"])
    command = [
        sys.executable,
        "-B",
        str(verifier),
        "--archive",
        str(archive),
        "--sha256",
        archive_sha,
        "--integrity",
        str(destination / "snapshot-integrity.json"),
        "--extract",
        str(scratch / "extracted"),
        "--result",
        str(OUT / "archive-reconstruction.json"),
    ]
    clean_environment = os.environ.copy()
    clean_environment.pop("PYTHONPATH", None)
    clean_environment.pop("PYTHONHOME", None)
    clean_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    done = subprocess.run(
        command, cwd=scratch, capture_output=True, text=True, env=clean_environment
    )
    (OUT / "standalone-verifier.log").write_text(done.stdout + done.stderr)
    assert done.returncode == 0, "standalone archive verifier failed"
    # 원 worktree 대신 immutable Git blob + archive 내용만으로 subset을 재구성한다.
    base_tree = scratch / "from-base"
    base_tree.mkdir()
    base_entries = [e for e in manifest["entries"] if e["base"]]
    oids = sorted({e["base"]["git_oid"] for e in base_entries})
    result = subprocess.run(
        ["git", "cat-file", "--batch"],
        input=("\n".join(oids) + "\n").encode(),
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    blobs, offset = {}, 0
    for oid in oids:
        end = result.stdout.index(b"\n", offset)
        size = int(result.stdout[offset:end].split()[2])
        blob = result.stdout[end + 1 : end + 1 + size]
        assert (
            hashlib.sha1(b"blob " + str(size).encode() + b"\0" + blob).hexdigest()
            == oid
        )
        blobs[oid] = blob
        offset = end + size + 2
    for entry in base_entries:
        target = base_tree / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        data = blobs[entry["base"]["git_oid"]]
        assert digest(data) == entry["base"]["sha256"]
        exclusive(target, data, int(entry["base"]["mode"], 8) & 0o777)
    for relative in changes + untracked:
        source = scratch / "extracted/source" / relative
        target = base_tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as stream:
            stream.write(source.read_bytes())
        os.chmod(target, source.stat().st_mode & 0o777)
    reconstructed = check_source_tree(base_tree, manifest)
    reconstructed.update(
        status="PASS",
        tracked_baseline_files=len(base_entries),
        tracked_overrides=len(changes),
        untracked_overlay=len(untracked),
        tracked_deletions=0,
        original_index_modified=False,
        verification_uses_mutable_worktree_content=False,
    )
    (OUT / "base-overlay-reconstruction.json").write_bytes(encoded(reconstructed))
    check_live(manifest, preflight)
    retained_sha = file_digest(archive)
    assert retained_sha == archive_sha
    before = os.statvfs(destination).f_bavail * os.statvfs(destination).f_frsize
    cleanup = cleanup_owned(scratch)
    cleanup["observed_available_delta"] = (
        os.statvfs(destination).f_bavail * os.statvfs(destination).f_frsize - before
    )
    cleanup["retained_archive_sha256"] = retained_sha
    (OUT / "cleanup-manifest.json").write_bytes(encoded(cleanup))
    (OUT / "snapshot-location.json").write_bytes(
        encoded(
            dict(
                directory=str(destination),
                archive=str(archive),
                archive_sha256=archive_sha,
                integrity=str(destination / "snapshot-integrity.json"),
                verifier=str(verifier),
            )
        )
    )
    check_live(manifest, preflight)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    try:
        output = main(args.destination)
    except CandidateChanged:
        raise SystemExit("BLOCKED — approved candidate changed; no baseline update")
    print(json.dumps(dict(status="VERIFIED_PENDING_SEAL", directory=str(output))))

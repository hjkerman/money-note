"""IR02 source archive를 live worktree/Git 없이 검증하고 새 빈 경로에 푼다."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile

BASE = "ebcbd54d90eeee194a04b9eea6367f446ee2fd28"
PAYLOAD = "645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def payload_digest(entries):
    return digest(
        json.dumps(
            entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )


def check_source_tree(directory, manifest):
    directory = Path(directory)
    expected = {e["path"] for e in manifest["entries"]}
    actual = {
        p.relative_to(directory).as_posix()
        for p in directory.rglob("*")
        if p.is_file() or p.is_symlink()
    }
    assert actual == expected, "SOURCE_INVENTORY_MISMATCH"
    reconstructed = json.loads(json.dumps(manifest["entries"]))
    for entry in reconstructed:
        path = directory / entry["path"]
        assert not path.is_symlink() and path.stat().st_nlink == 1, "LINK_NOT_ALLOWED"
        values = dict(
            sha256=file_digest(path),
            bytes=path.stat().st_size,
            mode=oct(path.stat().st_mode & 0o777),
        )
        assert all(values[k] == entry["worktree"][k] for k in values), entry["path"]
        entry["worktree"].update(values)
    assert payload_digest(reconstructed) == PAYLOAD, "RECONSTRUCTED_PAYLOAD_MISMATCH"
    return dict(
        files=len(actual),
        bytes=sum(e["worktree"]["bytes"] for e in reconstructed),
        payload_sha256=PAYLOAD,
    )


def verify(archive, expected_sha256, integrity, extract=None):
    archive, integrity = Path(archive), Path(integrity)
    assert not archive.is_symlink() and archive.stat().st_nlink == 1
    assert file_digest(archive) == expected_sha256, "ARCHIVE_SHA_MISMATCH"
    index = json.loads(integrity.read_text())
    assert (
        index["archive_sha256"] == expected_sha256
        and index["candidate_payload_sha256"] == PAYLOAD
    )
    expected = {r["path"]: r for r in index["members"]}
    assert len(expected) == len(index["members"]), "DUPLICATE_INDEX_PATH"
    if extract is not None:
        extract = Path(extract)
        extract.mkdir(mode=0o700, parents=False, exist_ok=False)
    contents = {}
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        assert len(members) == len(expected) < 4096
        assert sum(m.size for m in members) < 64 * 1024**2
        seen = set()
        for member in members:
            name = member.name
            parts = PurePosixPath(name)
            assert (
                not parts.is_absolute() and ".." not in parts.parts and "\\" not in name
            )
            assert member.isfile() and name not in seen and name in expected, (
                "UNSAFE_OR_DUPLICATE_MEMBER"
            )
            seen.add(name)
            stream = tar.extractfile(member)
            assert stream is not None
            with stream:
                data = stream.read()
            actual = dict(
                path=name,
                bytes=len(data),
                mode=oct(member.mode & 0o777),
                sha256=digest(data),
            )
            assert actual == expected[name], name
            contents[name] = data
            if extract is not None:
                target = extract.joinpath(*parts.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                assert target.parent.resolve().is_relative_to(extract.resolve())
                with open(target, "xb") as output:
                    output.write(data)
                os.chmod(target, member.mode & 0o777)
        assert seen == set(expected)
    manifest = json.loads(contents["metadata/ir01/candidate-source-manifest.json"])
    assert (
        manifest["committed_base"] == BASE
        and manifest["candidate_payload_sha256"] == PAYLOAD
    )
    assert (
        len(manifest["entries"]) == 819
        and sum(e["worktree"]["bytes"] for e in manifest["entries"]) == 9085052
    )
    assert payload_digest(manifest["entries"]) == PAYLOAD
    assert {"source/" + e["path"] for e in manifest["entries"]} == {
        n for n in seen if n.startswith("source/")
    }
    for entry in manifest["entries"]:
        name = "source/" + entry["path"]
        assert digest(contents[name]) == entry["worktree"]["sha256"]
        assert expected[name]["mode"] == entry["worktree"]["mode"]
    commit = contents["metadata/base-commit.txt"]
    assert (
        hashlib.sha1(
            b"commit " + str(len(commit)).encode() + b"\0" + commit
        ).hexdigest()
        == BASE
    )
    assert commit.splitlines()[0] == b"tree " + manifest["committed_base_tree"].encode()
    state = json.loads(contents["metadata/freeze.json"])
    assert state["tracked_deletions"] == [] and state["staged"] == ""
    assert state["HEAD"] == BASE and state["candidate_payload_sha256"] == PAYLOAD
    review = json.loads(
        contents["source/docs/benchmarks/t66f-b03/source-lock-review.json"]
    )
    locks = {}
    for path, reviewed in review["files"].items():
        raw = contents["source/" + path]
        assert digest(raw) == reviewed["reviewed_sha256"], path
        if reviewed.get("historical_sha256"):
            original = raw.decode()
            for replacement in reviewed["exact_replacements"]:
                assert original.count(replacement["reviewed"]) == 1
                original = original.replace(
                    replacement["reviewed"], replacement["historical"], 1
                )
            assert digest(original.encode()) == reviewed["historical_sha256"], path
        locks[path] = "PASS"
    result = dict(
        status="PASS",
        archive_sha256=expected_sha256,
        member_files=len(seen),
        source_files=819,
        source_bytes=9085052,
        payload_sha256=PAYLOAD,
        source_locks=locks,
        baseline_commit=BASE,
        tracked_deletions=0,
        worktree_content_dependency=False,
        full_checkout_requires_base_commit=True,
    )
    if extract is not None:
        result["extracted_source"] = check_source_tree(extract / "source", manifest)
    assert file_digest(archive) == expected_sha256, (
        "ARCHIVE_CHANGED_DURING_VERIFICATION"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--integrity", required=True)
    parser.add_argument("--extract")
    parser.add_argument("--result")
    args = parser.parse_args()
    result = verify(args.archive, args.sha256, args.integrity, args.extract)
    if args.result:
        with open(args.result, "x") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(
        json.dumps({k: result[k] for k in ("status", "source_files", "payload_sha256")})
    )

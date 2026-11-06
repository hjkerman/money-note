"""IC03 source-only 동결·재구성. 제품 source나 Git index를 수정하지 않는다."""

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = Path(os.environ.get("IC03_BASE_REPOSITORY", str(ROOT)))
HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
BASE = "ebcbd54d90eeee194a04b9eea6367f446ee2fd28"
PARENT = "27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3"
DESTINATION = Path("/home/hjkerman/codex/audit-candidates/money-note/t66f-b03")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(entries):
    return json.dumps(
        entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def git(*args):
    return subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(REPOSITORY), *args],
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )


def describe(relative):
    p = ROOT / relative
    assert p.is_file() and not p.is_symlink(), relative
    body = p.read_bytes()
    return {
        "path": relative,
        "bytes": len(body),
        "mode": oct(stat.S_IMODE(p.stat().st_mode)),
        "sha256": sha(body),
    }


def source_paths():
    parent = json.loads(
        (HERE.parent / "t66f-b03-ic02/corrected-candidate-manifest.json").read_text()
    )
    paths = {e["path"] for e in parent["entries"]}
    paths.update(
        {
            "backend/tests/test_logical_cost_ic03.py",
            str((HERE / "verify.py").relative_to(ROOT)),
            str((HERE / "freeze.py").relative_to(ROOT)),
        }
    )
    # Immutable independent reproducer sources, not generated audit outputs.
    for name in [
        "test_ir04_rollover_native.py",
        "test_ir04_installation.py",
        "test_ir04_schema.py",
        "test_ir03_oracles.py",
        "test_ir03_installation.py",
        "test_ir03_tls.py",
        "test_ir03_triggers.py",
        "original_IA05.py",
        "original_IA06.py",
        "original_IA07.py",
        "ir03_oracles_test.dart",
        "ir04_schema_test.dart",
        "integration_original_test.dart",
        "ir03_delta_test.dart",
    ]:
        paths.add("docs/benchmarks/t66f-b03-ir04/tests/" + name)
    for name in [
        "test_ir03_oracles.py",
        "test_ir03_installation.py",
        "test_ir03_tls.py",
        "test_ir03_triggers.py",
        "ir03_oracles_test.dart",
        "original-IA05.py",
        "original-IA06.py",
        "original-IA07.py",
    ]:
        paths.add("docs/benchmarks/t66f-b03-ir03/" + name)
    return sorted(paths)


def context_paths():
    return [
        "docs/t66f-b03-ic02-ir03-n01-n02-correction.md",
        "docs/t66f-b03-ir03-independent-correctness-reaudit.md",
        "docs/t66f-b03-ir04-independent-final-reaudit.md",
        "docs/benchmarks/t66f-b03-ir03/findings.json",
        "docs/benchmarks/t66f-b03-ir04/findings.json",
        "docs/benchmarks/t66f-b03-ir04/xml-incident-adjudication.json",
        "docs/benchmarks/t66f-b03-ir04/index-adjudication.json",
        "docs/benchmarks/t66f-b03-ic03/evidence/summary.json",
    ]


def handoff(digest):
    return f"""# IC03 교정 후보 — 다음 작업은 실제 독립 재감사

이 동결은 구현 측 동결이며 독립 감사 PASS가 아니다. N01/N02·IC03 구현에 참여하지 않은 새 Codex XHigh auditor가 아래를 한 작업에서 검증한다. source payload `{digest}`, base `{BASE}`. archive SHA는 SHA256SUMS를 따른다.

1. archive SHA와 source-manifest의 entries(bytes/mode/SHA)를 대조한다. canonical entries JSON은 path 정렬, UTF8, ensure_ascii=False, sort_keys=True, separators=(',',':')이며 SHA-256이다. payload와 archive hash는 다르다.
2. 고정 base의 Git archive에 frozen source/만 overlay하고 freeze.json의 deletion을 적용한다. `IC03_BASE_REPOSITORY=/home/hjkerman/codex/money-note python freeze.py verify SNAPSHOT NEW_EMPTY_WORKSPACE`가 이를 검증한다. Git 저장소에서는 고정 commit/object만 읽고 live working-tree source를 실행 대상으로 참조하지 않는다. Python/Flutter 외부 의존성은 별도로 준비하되 frozen package source를 root로 사용한다.
3. 원 `docs/benchmarks/t66f-b03-ir04/tests/test_ir04_rollover_native.py`와 `test_ir04_installation.py`를 실행한다. 원문을 보존하고 /tmp root/import/output 경로만 소유 scratch로 치환한다. source·adapter hash와 치환 목록을 보존하고 assertion은 바꾸지 않는다.
4. 설치 teardown/새 activation을 실제 barrier/trace로 강제한다. 실제 native parser 호출수·UTF8 bytes, delegate의 __wrapped__ identity, reference 소유권과 복원 상태를 독립 검증한다. parse 1회/2B와 Unicode, 같은 bytes의 별개 두 호출을 포함한다. workers에도 같은 소유권 교정을 적용했으므로 accepted/rejected dispatch의 hold 반환을 확인한다.
5. 원 IR03 N02와 IA04를 실행한다: `docs/benchmarks/t66f-b03-ir03/test_ir03_installation.py`, `test_ir03_oracles.py`. IR04/tests에는 이미 경로만 분리한 원 oracle도 보존한다. 최초 설치 대기와 nested 계수가 generation 교대 교정 후에도 정확해야 한다.
6. 원 IA01–IA07, Python/Dart schema DDL·savepoint·SQL payload와 external DDL incomplete 경계를 검증한다. IA07 원 스크립트는 관측 출력 프로그램이므로 두 oracle SELECT가 setup이고 generation은0인지 별도 엄격 assertion을 수행한다.
7. `backend/tests/test_logical_cost_ic03.py`는 구현 측 회귀14개다. 독립 기대값을 대신하지 않는다. 기존 IC01/IC02, counter/scope/native/resource, source-lock/P0, 실제 소형 authenticated HTTP D→E/E3/E4를 검증한다. IR04/tests의 `integration_original_test.dart`, `ir03_delta_test.dart`는 OFF/ON cold·identical·card/cash delta·거부 및 native byte oracle을 제공한다.
8. 모든 scoped correctness가 통과하면 B03 correctness에 한해 PASS/CLOSED, 결함이면 FAIL을 판정한다. 교정과 자기 인증을 결합하지 않는다. scope 재검토·XML recovery·후보 동결을 다시 준비 단계로 요청하지 않는다.

이전 IR02·IR04 실패 후보와 원 finding은 불변이다. XML exact bytes 손실은 IR04가 evidentiary substitute로 판정했다. index는 역사 stat incident와 staged 내용 보존을 구분한다. 새100k cold, 비용 grid, full-scale feasibility, I25 large-N, Android/VFS/power-loss, R1, 배포는 미검증/미승인이다. 계측 correctness를 Phase B PASS로 확대하지 않는다.

snapshot은0444/0555와 digest로 보호한다. owner/root에 대한 hardware WORM은 아니다. 실패 후보를 덮어쓰지 않는다.
"""


def verify(snapshot, workspace):
    assert not workspace.exists(), "use a new empty task-owned workspace"
    manifest = json.loads((snapshot / "source-manifest.json").read_text())
    frozen = json.loads((snapshot / "freeze.json").read_text())
    for e in manifest["entries"] + frozen["context"]:
        relative = Path(e["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
    digest = sha(canonical(manifest["entries"]))
    assert digest == manifest["candidate_source_digest_sha256"] == snapshot.name
    archive_hash = sha((snapshot / "candidate.tar.gz").read_bytes())
    assert (snapshot / "SHA256SUMS").read_text().split()[0] == archive_hash
    assert git("rev-parse", BASE).decode().strip() == frozen["base_commit"] == BASE
    workspace.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(git("archive", BASE))) as t:
        t.extractall(workspace, filter="data")
    for relative in frozen["tracked_deletions"]:
        (workspace / relative).unlink()
    with tarfile.open(snapshot / "candidate.tar.gz") as t:
        assert (
            len(t.getmembers()) == len(manifest["entries"]) + len(frozen["context"]) + 2
        )
        assert (
            json.loads(t.extractfile("metadata/source-manifest.json").read())
            == manifest
        )
        assert json.loads(t.extractfile("metadata/freeze.json").read()) == frozen
        for e in manifest["entries"]:
            h = t.getmember("source/" + e["path"])
            assert h.isfile() and h.mode == int(e["mode"], 8)
            body = t.extractfile(h).read()
            assert len(body) == e["bytes"] and sha(body) == e["sha256"]
            p = workspace / e["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
            p.chmod(h.mode)
        for e in frozen["context"]:
            assert sha(t.extractfile("context/" + e["path"]).read()) == e["sha256"]
    selected = {e["path"] for e in manifest["entries"]}
    untouched = 0
    for record in git("ls-tree", "-r", "-z", BASE).split(b"\0"):
        if not record:
            continue
        meta, relative = record.split(b"\t")
        mode, _, oid = meta.split()
        name = relative.decode()
        if name in selected or name in frozen["tracked_deletions"]:
            continue
        p = workspace / name
        assert p.read_bytes() == git("cat-file", "blob", oid.decode())
        assert bool(p.stat().st_mode & 0o111) == (mode == b"100755")
        untouched += 1
    for e in manifest["entries"]:
        p = workspace / e["path"]
        assert (
            sha(p.read_bytes()) == e["sha256"]
            and oct(stat.S_IMODE(p.stat().st_mode)) == e["mode"]
        )
    return {
        "payload_sha256": digest,
        "archive_sha256": archive_hash,
        "snapshot": str(snapshot),
        "workspace": str(workspace),
        "files": manifest["files"],
        "bytes": manifest["source_bytes"],
        "baseline_other_files_verified": untouched,
        "reconstruction": "PASS",
    }


def freeze(workspace):
    summary = json.loads((OUT / "summary.json").read_text())
    assert summary["implementation_verdict"] == "PASS", (
        "verification must finish before freeze"
    )
    assert git("rev-parse", "HEAD").decode().strip() == BASE
    entries = [describe(p) for p in source_paths()]
    digest = sha(canonical(entries))
    assert digest != PARENT
    destination = DESTINATION / digest
    assert not destination.exists(), "never overwrite an existing frozen candidate"
    tracked = set(git("ls-files", "-z").decode().split("\0")) - {""}
    modifications = sorted(
        set(git("diff", "--name-only", "-z").decode().split("\0")) - {""}
    )
    assert set(modifications) <= set(source_paths()), "unlisted tracked modification"
    assert not git("diff", "--cached", "--name-only"), (
        "staged content differs from baseline"
    )
    deletions = sorted(p for p in tracked if not (ROOT / p).exists())
    assert not deletions, "unexpected tracked deletion requires explicit review"
    manifest = {
        "schema_version": 1,
        "kind": "IC03 implementation-side frozen source; independent audit pending",
        "base_commit": BASE,
        "parent_ir04_payload_sha256": PARENT,
        "candidate_source_digest_sha256": digest,
        "digest_definition": "SHA256 UTF8 JSON(entries), path sorted, ensure_ascii=False, sort_keys=True, separators=(comma,colon)",
        "files": len(entries),
        "source_bytes": sum(e["bytes"] for e in entries),
        "entries": entries,
    }
    frozen = {
        "base_commit": BASE,
        "payload_sha256": digest,
        "tracked_deletions": deletions,
        "tracked_modifications": modifications,
        "staged_content_equals_head": True,
        "base_tree": git("rev-parse", BASE + "^{tree}").decode().strip(),
        "required_untracked": sorted(set(source_paths()) - tracked),
        "staged_logical_sha256": sha(git("ls-files", "--stage")),
        "context": [describe(p) for p in context_paths()],
        "independence": "IMPLEMENTATION FREEZE; NOT INDEPENDENT AUDIT",
        "immutability": "read-only plus checksums; not hardware WORM",
    }
    stage = Path(tempfile.mkdtemp(prefix=".ic03-", dir=DESTINATION))
    archive = stage / "candidate.tar.gz"
    with (
        archive.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as gz,
        tarfile.open(fileobj=gz, mode="w") as t,
    ):

        def add(name, body, mode=0o444):
            h = tarfile.TarInfo(name)
            h.size, h.mode, h.mtime = len(body), mode, 0
            t.addfile(h, io.BytesIO(body))

        for e in entries:
            p = ROOT / e["path"]
            assert describe(e["path"]) == e, "source changed during freeze"
            add("source/" + e["path"], p.read_bytes(), int(e["mode"], 8))
        for e in frozen["context"]:
            body = (ROOT / e["path"]).read_bytes()
            assert sha(body) == e["sha256"]
            add("context/" + e["path"], body)
        add(
            "metadata/source-manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2).encode(),
        )
        add(
            "metadata/freeze.json",
            json.dumps(frozen, ensure_ascii=False, indent=2).encode(),
        )
    for e in entries:
        assert describe(e["path"]) == e, "source changed before finalization"
    (stage / "source-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    (stage / "freeze.json").write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2) + "\n"
    )
    (stage / "SHA256SUMS").write_text(
        sha(archive.read_bytes()) + "  candidate.tar.gz\n"
    )
    (stage / "HANDOFF.md").write_text(handoff(digest))
    # Verify every immutable source member before atomic publication.
    with tarfile.open(archive) as t:
        for e in entries:
            assert sha(t.extractfile("source/" + e["path"]).read()) == e["sha256"]
    for p in stage.iterdir():
        p.chmod(0o444)
    stage.chmod(0o555)
    stage.rename(destination)
    record = verify(destination, workspace)
    (OUT / "freeze-reconstruction.json").write_text(json.dumps(record, indent=2) + "\n")
    (HERE / "corrected-candidate-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(record))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["create", "verify"])
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    if args.mode == "create":
        assert len(args.paths) == 1
        freeze(Path(args.paths[0]))
    else:
        assert len(args.paths) == 2
        print(json.dumps(verify(Path(args.paths[0]), Path(args.paths[1]))))

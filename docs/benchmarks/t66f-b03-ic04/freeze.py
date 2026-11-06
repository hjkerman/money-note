"""IC04 source-only 동결·재구성. 제품 source나 Git index를 수정하지 않는다."""

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
REPOSITORY = Path(os.environ.get("IC04_BASE_REPOSITORY", str(ROOT)))
HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
BASE = "ebcbd54d90eeee194a04b9eea6367f446ee2fd28"
PARENT = "dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370"
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
        (HERE.parent / "t66f-b03-ic03/corrected-candidate-manifest.json").read_text()
    )
    paths = {e["path"] for e in parent["entries"]}
    paths.update(
        {
            "backend/tests/test_logical_cost_ic04.py",
            str((HERE / "verify.py").relative_to(ROOT)),
            str((HERE / "matrix.py").relative_to(ROOT)),
            str((HERE / "freeze.py").relative_to(ROOT)),
        }
    )
    for name in [
        "test_ir05_interrupt_final.py",
        "test_ir05_worker_interrupt.py",
        "test_ir05_interrupted_growth.py",
        "test_ir05_lifecycle.py",
        "test_ir04_rollover_native.py",
        "test_ir04_installation.py",
        "test_ir03_oracles.py",
        "test_ir03_installation.py",
        "test_ir03_tls.py",
        "test_ir03_triggers.py",
        "test_ir04_schema.py",
        "original_IA05.py",
        "original_IA06.py",
        "original_IA07.py",
        "ir03_oracles_test.dart",
        "ir04_schema_test.dart",
        "integration_original_test.dart",
        "ir03_delta_test.dart",
    ]:
        paths.add("docs/benchmarks/t66f-b03-ir05/tests/" + name)
    return sorted(paths)


def context_paths():
    return [
        "docs/t66f-b03-ir05-independent-correctness-closure.md",
        "docs/benchmarks/t66f-b03-ir05/findings.json",
        "docs/t66f-b03-ic03-installation-generation-correction.md",
        "docs/benchmarks/t66f-b03-ic04/evidence/lifecycle-model.json",
        "docs/benchmarks/t66f-b03-ic04/evidence/lifecycle-model-final.json",
        "docs/benchmarks/t66f-b03-ic04/evidence/interruption-matrix.json",
        "docs/benchmarks/t66f-b03-ic04/evidence/protected-source-check.json",
        "docs/benchmarks/t66f-b03-ic04/evidence/summary.json",
    ]


def handoff(digest, archive_digest):
    return f"""# IC04 교정 동결본 — 다음 작업은 실제 독립 정확성 재감사

이 snapshot은 구현 측 교정·검증·동결이며 독립 PASS가 아니다. 구현에 참여하지 않은 새 Codex XHigh auditor가 이 후보로 실제 B03 정확성 감사를 수행한다. 별도 readiness·freeze·역사 XML 복구 작업을 요구하지 않는다.

- 후보: `{DESTINATION / digest}`
- payload SHA-256: `{digest}`
- archive SHA-256: `{archive_digest}`
- 고정 base: `{BASE}`
- canonical entries: path 정렬, UTF8 JSON ensure_ascii=False, sort_keys=True, separators=(',',':')의 SHA-256; archive hash와 다르다.

## 바로 실행할 검증

1. SHA256SUMS·manifest bytes/mode를 확인하고 고정 Git base에 frozen source/만 overlay한다. `IC04_BASE_REPOSITORY=/home/hjkerman/codex/money-note python freeze.py verify SNAPSHOT NEW_EMPTY_WORKSPACE`가 Git 고정 객체만 읽어 재구성한다. live source를 실행 root로 사용하지 않는다. 외부 venv/Flutter runtime만 재사용하고 package root는 재구성본으로 잡는다.
2. 원 IR05 source 네 개는 `docs/benchmarks/t66f-b03-ir05/tests/test_ir05_interrupt_final.py`, `test_ir05_worker_interrupt.py`, `test_ir05_interrupted_growth.py`, `test_ir05_lifecycle.py`다. `/tmp/money-note-ir05-20261024` root/import/output만 자기 scratch로 치환하고 원문·adapter SHA·치환 목록을 보존한다. 원 assertion을 바꾸지 않는다. 중간 frame-router는 cross-thread 종료에서 handler를 남겨 폐기했으며 최종 후보에 없다. 원 SIGINT 두 seam은 실제 patch 적용 뒤 callback commit과 마지막 restore 직전이며 현재도 그대로 실행된다.
3. 새 `backend/tests/test_logical_cost_ic04.py`의 169개는 구현 회귀다. 이를 독립 oracle의 대용으로 삼지 말고 전체 취소 수명을 검토한다. matrix source는 `docs/benchmarks/t66f-b03-ic04/matrix.py`, 고정 machine matrix는 archive context의 `interruption-matrix.json`이다. 예: `PYTHONPATH=RECON/backend VENV/bin/python -m pytest -q -p no:cacheprovider RECON/backend/tests/test_logical_cost_ic04.py`.
4. 상태 모델은 UNINSTALLED→INSTALLING→ACTIVE→RESTORING→UNINSTALLED이며 실패 복원은 RECOVERING 한 세대를 유지한다. ref/callback/patch는 먼저 복구 의무를 예약한다. callback은 성공 뒤에만 pop한다. `OwnershipContext`가 각 동기 generator enter/exit/close resume만 보호한다. enter 뒤 취소되면 획득한 generator를 닫고 재전파한다. 사용자 본문·await 동안 process handler는 원래 값이며 worker에서 종료해도 main handler를 남기지 않는다. 대기 frame은 취소 가능하고, 소유권이 확정된 checkpoint에서 publication 전에 원 취소를 전달한다. dispatch cleanup도 별도 동기 context가 소유한다. 소유권 일관성 회복 뒤 원 handler를 호출하고, cleanup 오류는 복구 후에도 원 예외를 전파한다. 지속 오류는 새 세대 활성화를 거부해야 한다.
5. 모든 acquisition/publication/teardown에 ordinary exception·실제 SIGINT와 가능한 동시 activation을 독립 주입한다. matrix의 before/after ref·reserve·patch·ready·restore·retire, native constructor/instance finish/hold flag/count, ContextVar set/reset·prior binding identity, generator resume/반환/퇴역·cross-thread 종료·대기 취소, 거부 dispatch, 완료 callback handoff를 포함한다. Task.cancel은 실제 await에서, SIGINT Python handler는 main thread에서 전달됨을 구분한다. 고정 seed4104/907의 400-step 상태 모델은 native frame/literal ledger와 ownership을 대조한다.
6. patch/registry/native 실제 상태를 따로 확인한다. parse1회/ASCII2B와 Unicode, 같은 bytes의 두 실제 호출, per-scope/stage가 정확해야 한다. native budget0 뒤 hold0/completion1이어야 한다. 세션 worker class patch 종료 뒤에도 live job의 instance finish가 실제 hold를 반환해야 한다. 관측하려는 hash/parse 비용은 명시적으로 선택한 primitive observer의 유효 수명 안에서만 complete라고 주장한다.
7. 기본 journal256/257 거부, suspended user body의 잔류 signal handler0·전역 signal owner registry0, 세 registry 종류, job/dispatch1, 기존 owner32·cache32를 source·경계 oracle로 확인한다. 같은 실패를 반복해 callback/handle/wrapper가 쌓이지 않아야 한다. 외부 임의 report callback은 지연/재실행하지 않으며 completion_error가 있으면 complete snapshot PASS로 수용하지 않는다. SIGKILL·physical power loss는 이 Python cleanup 계약 밖이다.
8. 원 IA01–IA07·IR03/IR04 원 oracle은 frozen `docs/benchmarks/t66f-b03-ir04/tests/`와 `t66f-b03-ir03/`에 보존한다. IA07은 `original_IA07.py`의 실제 출력에서 oracle SELECT가 setup2개/generation0인지 별도 엄격 assertion한다. 원 historical defect-existence4개는 승인된 `t66f-b03-ic01/original_backend.py`로만 분리 실행하고 현재 동작은 현재 oracle로 검증한다.
9. IR03-N01 Python/Dart schema·savepoint·cache를 유지한다. 외부 concurrent DDL은 기존 명시적 incomplete 거부이며 성공 계수로 간주하지 않는다. `test_ir04_schema.py`, `ir04_schema_test.dart`, IC01/IC02/P02 회귀가 진입점이다.
10. 실제 인증 HTTP는 IR05/tests의 `integration_original_test.dart`, `ir03_delta_test.dart`와 `mobile/test/segmented_logical_cost_http_test.dart`를 사용한다. cold·identical·card/cash delta·거부·native SHA/parser witness·durable E1·E3/E4와 OFF/ON 동등성, source-lock/P0, backend TLS/native 취소를 검증한다. B03_OUTPUT은 새 audit evidence 경로로 지정한다.
11. 완료된 fresh 결과는 context summary와 저장소 `docs/benchmarks/t66f-b03-ic04/evidence/`에 보존한다. Git index/staged·기존 파일·역사 archive를 훼손하지 않는다. runtime 의존성만 별도 준비하고 source나 fixture를 mutable live bytes로 바꾸지 않는다.

## 실행 경로와 원 finding 대응

아래 변수는 auditor가 생성한 새 경로다. `audit_tree`는 검증 재구성본, `audit_scratch`는 존재하지 않는 새 oracle 출력 경로, `audit_venv`는 source를 포함하지 않는 기존 runtime이다.

```bash
"${{audit_venv}}/bin/python" "${{audit_tree}}/docs/benchmarks/t66f-b03-ic04/verify.py" prepare-originals "${{audit_scratch}}"
PYTHONPATH="${{audit_tree}}/backend" "${{audit_venv}}/bin/python" -m pytest -q -p no:cacheprovider "${{audit_tree}}/backend/tests/test_logical_cost_ic04.py" "${{audit_scratch}}/tests" --junitxml="${{audit_scratch}}/evidence/python.xml"
```

- IA01/02/03/04/05/06: `test_ir03_oracles.py::test_ia01_nearest_savepoint`, `test_ia02_conflicts_and_prefix`, `test_ia03_first_comment`, `test_ia04_nested_install`, `test_ia05_rejected_dispatch`, `test_ia06_owner32_before_execution_and_release`.
- IA07: 재구성 root에서 `original_IA07.py`를 실행하고 출력 stage가 두 setup/zero generation인지 독립 assert한다. 이 원 script는 관측만 출력하므로 exit0 자체로 PASS를 판정하지 않는다.
- IR03-N01: `test_ir03_oracles.py::test_ddl_observer_reinstallation`, `test_ir04_schema.py` 및 `ir04_schema_test.dart`/IC02.
- IR03-N02: `test_ir03_installation.py::test_concurrent_first_install_is_ready_before_second_scope_returns`, `test_ir04_installation.py`.
- IR04-N01: `test_ir04_rollover_native.py::test_unmodified_installation_generation_rollover_native_parse_once`.
- IR05-N01/N02: `test_ir05_interrupt_final.py`, `test_ir05_worker_interrupt.py`, `test_ir05_interrupted_growth.py`; 실제 SIGINT와 native frame/lease snapshot oracle를 유지한다.
- 구현 stateful/new fault169개와 위 독립 originals의 결과를 분리 보고한다. history-only4개는 원 approved historical runner를 사용하며 새 구현 기대값을 완화하지 않는다.
- Flutter는 재구성 mobile에서 package/runtime만 준비한 뒤 `flutter test --no-pub --machine --concurrency=1`로 `ir03_oracles_test.dart`, `ir04_schema_test.dart`, 실제 `ir03_delta_test.dart`, `integration_original_test.dart`, `mobile/test/segmented_logical_cost_http_test.dart`를 실행한다. B03_OUTPUT은 audit 고유 경로로 설정한다. 재구성된 backend가 실행되도록 server path를 확인한다.

`test_cancelled_outer_enter_return_transfers_no_unowned_reference_or_stage`의 세 resource handoff도 반드시 독립 검증한다. 구현 시 발견한 원 handoff 실패는 final-return-handoff-counterexamples 및 outer-enter-return JSON에 보존된다.

모든 scoped correctness·수명·독립 oracle·실제 경로가 통과하면 B03 정확성에 한해 독립 PASS/CLOSED, 새 결함이면 FAIL을 판정한다. 구현을 수정하고 자기 인증하지 않는다. 새100k cold·five-point 비용 grid·I25 large-N·full-scale feasibility·Android/VFS/power-loss·R1·배포는 미검증/미승인이다. 역사 P03 실패397146/400532는 유지한다. 이전 XML/index 사고를 다시 조사하거나 실패 증거를 바꾸지 않는다. read-only0444/0555는 owner/root에 대한 WORM이 아니다.
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
    for path, expected in summary["final_source_sha256"].items():
        assert describe(path)["sha256"] == expected, "untested source after final gate"
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
        "kind": "IC04 implementation-side frozen source; independent audit pending",
        "base_commit": BASE,
        "parent_ic03_payload_sha256": PARENT,
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
    stage = Path(tempfile.mkdtemp(prefix=".ic04-", dir=DESTINATION))
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
    (stage / "HANDOFF.md").write_text(handoff(digest, sha(archive.read_bytes())))
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

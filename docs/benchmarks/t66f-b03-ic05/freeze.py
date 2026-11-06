"""IC05 source-only 동결·재구성. 제품 source나 Git index를 수정하지 않는다."""

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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2] if len(HERE.parents) > 2 else HERE
REPOSITORY = Path(os.environ.get("IC05_BASE_REPOSITORY", str(ROOT)))
OUT = HERE / "evidence"
BASE = "ebcbd54d90eeee194a04b9eea6367f446ee2fd28"
PARENT = "821d64e5e9e530cbda3f54f08fef32072a91c36e829f928a75b534da8b03f709"
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
        (HERE.parent / "t66f-b03-ic04/failed-working-source-manifest.json").read_text()
    )
    paths = {e["path"] for e in parent["entries"]}
    paths.update(
        {
            "backend/tests/test_logical_cost_ic05.py",
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
        "docs/t66f-b03-ic04-exception-safe-lifecycle-correction.md",
        "docs/benchmarks/t66f-b03-ic04/evidence/open-finding.json",
        "docs/benchmarks/t66f-b03-ic04/failed-working-source-manifest.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/ownership-protocol-before-edit.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/handoff-transition-matrix.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/call-sites.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/entry-bytecode.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/protected-source-check.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/source-ast-comparison.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/original-three-final-ledger.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/preservation-before-freeze.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/baseline-counters.py.gz",
        "docs/benchmarks/t66f-b03-ic05/evidence/baseline-server.py.gz",
        "docs/benchmarks/t66f-b03-ic05/evidence/source-change.diff.gz",
        "docs/benchmarks/t66f-b03-ic05/evidence/summary.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/backend-complete.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/backend-complete.xml",
        "docs/benchmarks/t66f-b03-ic05/evidence/backend-complete.log.gz",
        "docs/benchmarks/t66f-b03-ic05/evidence/handoff-complete.xml",
        "docs/benchmarks/t66f-b03-ic05/evidence/handoff-complete.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/preserved-original-complete.xml",
        "docs/benchmarks/t66f-b03-ic05/evidence/preserved-original-complete.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/flutter-http-complete.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/flutter-http-complete.log.gz",
        "docs/benchmarks/t66f-b03-ic05/evidence/http-complete-n9.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/http-complete-n260.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/http-complete-concurrent.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/http-complete-frozen.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/ia07-complete-oracle.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/original-three-before.json",
        "docs/benchmarks/t66f-b03-ic05/evidence/original-three-before.xml",
        "docs/benchmarks/t66f-b03-ic05/evidence/original-three-before.log.gz",
    ]


def handoff(digest, archive_digest):
    return f"""# IC05 동결본 — 다음 작업은 실제 독립 B03 정확성 재감사

구현·교정에 참여하지 않은 새 Codex XHigh auditor가 이 source로 직접 검증한다. 본 기록은 구현 측 PASS이며 독립 closure가 아니다. 별도 readiness·범위검토·freeze·역사 XML 복구를 다시 요구하지 않는다.

- snapshot: `{DESTINATION / digest}`
- payload SHA-256: `{digest}`
- archive SHA-256: `{archive_digest}`
- base commit: `{BASE}`
- starting IC04 working digest: `{PARENT}`
- canonical payload: path 순 entries를 UTF8 JSON ensure_ascii=False, sort_keys=True, separators=(',',':')로 인코딩한 SHA-256이다. archive hash와 구분한다.

## 재구성과 바로 실행할 명령

1. SHA256SUMS와 manifest를 검증한다. archive의 `source/docs/benchmarks/t66f-b03-ic05/freeze.py`를 자기 scratch에 추출·hash 대조한 뒤 실행한다. 예: `IC05_BASE_REPOSITORY=/home/hjkerman/codex/money-note VENV/bin/python FROZEN_HELPER verify SNAPSHOT NEW_EMPTY_TREE`. 고정 Git object만 읽으며 mutable live source로 시험하지 않는다. 파일 bytes/mode·base2010개 이상·deletion을 전부 확인한다.
2. 아래 변수 audit_tree는 검증한 재구성본, audit_scratch는 존재하지 않는 새 출력 경로, audit_venv는 runtime 전용이다.

```bash
"${{audit_venv}}/bin/python" "${{audit_tree}}/docs/benchmarks/t66f-b03-ic05/verify.py" prepare-originals "${{audit_scratch}}"
PYTHONPATH="${{audit_tree}}/backend" "${{audit_venv}}/bin/python" -m pytest -q -p no:cacheprovider "${{audit_tree}}/backend/tests/test_logical_cost_ic04.py" "${{audit_tree}}/backend/tests/test_logical_cost_ic05.py" "${{audit_scratch}}/tests" --junitxml="${{audit_scratch}}/evidence/independent.xml"
```

원 IC04 세 실패는 `backend/tests/test_logical_cost_ic04.py::test_cancelled_outer_enter_return_transfers_no_unowned_reference_or_stage`의 instrument/instrument_workers/stage다. 원 bytes/assertion을 수정하지 않는다. IC04 output은 재구성본의 disposable docs/evidence에 기록되므로 historical live 증거를 덮어쓰지 않는다. 먼저 이3개를 독립 실행하고 실제 callback SIGINT·native parser1회/2B·A0/B 정확 귀속을 확인한다.

## 소유권 계약을 독립 평가할 핵심

- acquire 이전의 한 context 객체가 유일한 release gate다. 동기 generator resume/복원과 실제 native job hold는 서로 다른 수명이다.
- trace/profile 반환 callback은 Python 본문 finally 뒤에도 반환을 실패시킬 수 있다. EntryHandoff가 원 observer를 모두 전달하고 그 실패를 rollback한 후 원 예외를 재전파하는지 독립 확인한다. 주어진 2바이트나 duplicate payload의 계수 보정은 없어야 한다.
- 일반 structured with는 enter가 오류 없이 반환한 뒤 exit를 보장한다. 수동 entry caller는 먼저 finally를 확립한다. 현재 benchmark의 네 ExitStack scope는 `context.enter(stack)`으로 cleanup을 획득 전에 예약한다. `RecoveryStack.enter_context`의 동일 경계도 검증한다.
- return observer phase가 끝나면 frame/profile hook이 원래대로 돌아가야 한다. 사용자 본문·await·cross-thread exit에 persistent signal router가 없어야 한다. 내부 rollback은 GC나 __del__에 의존하면 안 된다. GC 비활성48회 뒤 ref/stage/wrapper/hold/weak metadata baseline0을 독립 확인한다.
- legacy local/opcode trace, profile, 양쪽 동시 callback·ordinary error·실제 SIGINT·복원 API 오류를 별도로 검사한다. CPython3.12 opcode는 기존 frame의 f_trace_opcodes를 settrace 전에 활성화해야 실제 emit된다.
- Task.cancel 요청과 전달을 구분한다. 반환 hook이 task.cancel만 요청하면 실제 await 전의 유효 parse1회/2B는 정상 계수되고, await에서 취소돼 cleanup해야 한다. SIGINT return callback이 예외를 내는 취소 진입은 A0/0B여야 한다.
- 현재 PEP669 custom monitoring on entry code는 획득 전 explicit incomplete 거부이며 조용한0B가 아니다. 해당 제한이 mandatory measurement path와 양립하는지 독립 판정한다. benchmark는 이를 사용하지 않는다. observer를 획득 도중 바꾸는 경우도 silent success가 없어야 한다.
- 새76개 구현 테스트를 독립 oracle의 대용으로 삼지 않는다. native parser frame/raw input, ContextVar 이전 binding identity, actual NativeBudget, registry/ref와 callable identity를 따로 대조한다. matrix는 archive context `handoff-transition-matrix.json`, call-site 목록은 `call-sites.json`이다.

## 반드시 유지할 원 재현 경로

모두 frozen `docs/benchmarks/t66f-b03-ir05/tests/`에 있다. prepare-originals는 root/import/output만 바꾸고 원/adapter SHA를 남긴다.

- IR05-N01/N02: `test_ir05_interrupt_final.py`, `test_ir05_worker_interrupt.py`, `test_ir05_interrupted_growth.py`; 설치 patch 뒤 callback commit과 last close seam, native hold0/completion1을 검증한다.
- IR04-N01: `test_ir04_rollover_native.py::test_unmodified_installation_generation_rollover_native_parse_once`.
- IR03-N02: `test_ir03_installation.py::test_concurrent_first_install_is_ready_before_second_scope_returns`, `test_ir04_installation.py`.
- IR03-N01: `test_ir03_oracles.py::test_ddl_observer_reinstallation`, `test_ir04_schema.py`, Dart `ir04_schema_test.dart`.
- IA01–06: `test_ir03_oracles.py`의 `test_ia01_nearest_savepoint`, `test_ia02_conflicts_and_prefix`, `test_ia03_first_comment`, `test_ia04_nested_install`, `test_ia05_rejected_dispatch`, `test_ia06_owner32_before_execution_and_release`.
- IA07: 재구성 root에서 `original_IA07.py` 실행; 출력 setup2회/176·185행, generation0을 별도 strict assert한다. 원 script exit0만으로 PASS라 하지 않는다.
- 과거 결함존재4개 backend/3개 Dart는 승인된 historical wrapper에서 원 assertion 그대로 보존한다. 현재 strict oracle와 혼동하지 않는다.

## 실제 경로와 회귀

재구성 mobile에서 runtime/package 의존성만 준비한다. source는 live tree에서 복사하지 않는다. `flutter test --no-pub --machine --concurrency=1`로 원 `ir03_oracles_test.dart`, `ir04_schema_test.dart`, `ir03_delta_test.dart`, `integration_original_test.dart`와 `mobile/test/segmented_logical_cost_http_test.dart`를 실행한다. B03_OUTPUT은 auditor 고유 경로로 지정한다. 실제 backend가 재구성 source에서 실행되는지 확인한다. cold/no-change/card/cash delta/corrupt reject·E1 durable canonical bytes·E3/E4·native hash/parser witness·OFF/ON 동등성을 검증한다.

full backend·Flutter affected110·exact source-lock6·hash/SQL AST 보존 및 원 before/after 증거는 context summary/XML/gzip에 고정했다. SQL schema·savepoint·partial batch·cache32·owner32/33·closed scope·native job hold/late tail·B01 strict201×4/429를 유지해야 한다.

새 material defect면 원 재현과 expected/actual을 보존하고 FAIL한다. 모든 scoped correctness/ownership/counter/resource/실제 경로가 독립 PASS이면 B03 instrumentation correctness만 CLOSED로 판정한다. 구현을 고치고 스스로 독립 인증하지 않는다.

새100k cold·five-point grid·I25 large-N·full-scale feasibility/perturbation·Android memory/VFS/power-loss·R1·배포는 별도다. 역사 P03 실패397146/400532와 B01/B02 CLOSED를 유지한다. 과거 XML/index 사고를 재조사하지 않는다. read-only0444/0555는 owner/root에 대한 WORM이 아니다.
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
        "kind": "IC05 implementation-side frozen source; independent audit pending",
        "base_commit": BASE,
        "starting_ic04_working_payload_sha256": PARENT,
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
    stage = Path(tempfile.mkdtemp(prefix=".ic05-", dir=DESTINATION))
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

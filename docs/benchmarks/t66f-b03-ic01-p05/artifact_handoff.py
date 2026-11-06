"""명시적으로 요청한 synthetic benchmark만 보존한다. 제품 backup API가 아니다.

manifest.json은 마지막에 게시하는 완료 표식이다. 부분 SQLite 파일만으로 성공을
판정하지 않는다. 복원 파일은 offline 증거이며 live epoch/observation 권한이 아니다.
"""

from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time


class ArtifactError(RuntimeError):
    pass


def source_identity():
    root = Path(__file__).resolve().parents[3]
    paths = [
        "scripts/benchmarks/t66d2b_writers.py",
        "backend/tests/test_isolated_sync_capture.py",
        "docs/benchmarks/t66f-b02-implementation/server.py",
        "docs/benchmarks/t66f-b03-ic01-p05/artifact_handoff.py",
        "docs/benchmarks/t66f-b03-ic01-p05/test_handoff.py",
    ]
    paths.extend(
        str(p.relative_to(root))
        for p in sorted((root / "backend/isolated_sync").glob("*.py"))
    )
    return {path: digest(root / path) for path in paths}


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def c1(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def inspect_snapshot(path):
    """읽기 전용 독립 oracle. product counter/PathResolver를 사용하지 않는다."""
    with closing(
        sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    ) as conn:
        integrity = conn.execute("PRAGMA integrity_check").fetchall()
        foreign = conn.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != [("ok",)] or foreign:
            raise ArtifactError("SQLITE_INTEGRITY_FAILED")
        row = conn.execute(
            "SELECT namespace,revision,raw_hash,index_hash,tx_id FROM sync_current WHERE id=1"
        ).fetchone()
        if row is None:
            raise ArtifactError("CURRENT_GENERATION_MISSING")
        namespace, revision, raw_hash, index_hash, tx_id = row
        latest = conn.execute(
            "SELECT target FROM sync_observations WHERE namespace=? ORDER BY rowid DESC LIMIT 1",
            (namespace,),
        ).fetchone()
        if latest is None:
            raise ArtifactError("TARGET_EVIDENCE_MISSING")
        target = json.loads(latest[0])
        if (
            target["ns"] != json.loads(namespace)
            or target["revision"] != str(revision)
            or target["raw_ref"]["hash"] != raw_hash
            or target["index_ref"]["hash"] != index_hash
        ):
            raise ArtifactError("TARGET_CURRENT_MISMATCH")
        view = {k: v for k, v in target.items() if k != "sync_root"}
        if (
            hashlib.sha256(b"money-note.sync.v1/view\0" + c1(view)).hexdigest()
            != target["sync_root"]
        ):
            raise ArtifactError("TARGET_ROOT_MISMATCH")
        pending = [target[k + "_ref"] for k in ("raw", "index", "hot", "control")]
        seen = set()
        byte_count = 0
        while pending:
            ref = pending.pop()
            if ref["hash"] in seen:
                continue
            found = conn.execute(
                "SELECT kind,body FROM sync_objects WHERE hash=?", (ref["hash"],)
            ).fetchone()
            if found is None:
                raise ArtifactError("MISSING_OBJECT")
            kind, raw = found
            obj = json.loads(raw)
            if (
                len(raw) != int(ref["bytes"])
                or obj["kind"] != kind
                or obj["ns"] != target["ns"]
                or c1(obj) != raw
                or hashlib.sha256(
                    b"money-note.sync.v1/" + kind.encode() + b"\0" + raw
                ).hexdigest()
                != ref["hash"]
            ):
                raise ArtifactError("OBJECT_IDENTITY_MISMATCH")
            if kind == "raw-root":
                pending.extend(t["root"]["ref"] for t in obj["tables"])
            elif kind == "snapshot-node":
                pending.extend(t["ref"] for t in obj["children"])
            elif kind == "index-root":
                pending.append(obj["facts"])
            elif kind == "index-node":
                pending.extend((obj["left"], obj["right"]))
            seen.add(ref["hash"])
            byte_count += len(raw)
        return dict(
            target=target,
            namespace=target["ns"],
            principal_id=target["principal_id"],
            generation=dict(revision=str(revision), tx_id=tx_id),
            reachable_objects=len(seen),
            canonical_bytes=byte_count,
            backend_objects=conn.execute(
                "SELECT count(*) FROM sync_objects"
            ).fetchone()[0],
            sqlite_user_version=conn.execute("PRAGMA user_version").fetchone()[0],
            schema_sha256=hashlib.sha256(
                c1(
                    conn.execute(
                        "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
                    ).fetchall()
                )
            ).hexdigest(),
            integrity="ok",
            foreign_key_errors=0,
        )


def _json_file(path, value):
    with open(path, "x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def verify_artifact(directory):
    """완료 표식·파일 digest·실제 SQL/graph identity를 독립 대조한다."""
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    if (
        manifest["backup_status"] != "COMPLETE"
        or not manifest["cleanup"]["source_removed"]
    ):
        raise ArtifactError("INCOMPLETE_ARTIFACT")
    path = directory / "backend.sqlite3"
    if path.is_symlink() or digest(path) != manifest["snapshot_sha256"]:
        raise ArtifactError("ARTIFACT_DIGEST_MISMATCH")
    if inspect_snapshot(path) != manifest["identity"]:
        raise ArtifactError("ARTIFACT_IDENTITY_MISMATCH")
    return manifest


@contextmanager
def retained_backend(
    factory,
    *,
    destination=None,
    fixture_name="synthetic",
    n=None,
    expected_reachable_objects=None,
):
    """서버/worker 종료 후 이 scope를 벗어난다. 기본값은 기존 정리 그대로다.

    실패·취소도 finally에서 backup한 뒤 원 sandbox를 정리한다. SIGKILL/host crash의
    사전 실행은 보장하지 않는다. 활성 observation이나 inode authority를 복원하지 않는다.
    """
    if destination is None:
        with factory() as db:
            yield db
        return
    destination = Path(destination)
    # 과거 evidence와 partial도 덮어쓰지 않는다. sandbox 생성 전 예약한다.
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    manifest = dict(
        schema_version=1,
        run_id=destination.name,
        fixture=dict(name=fixture_name, n=n, synthetic=True),
        artifact_class="ORIGINAL_SYNTHETIC_SNAPSHOT",
        backup_status="INCOMPLETE",
        limitations=[
            "offline 증거이며 재시작 후 old Target 권한이 아님",
            "synthetic DB의 세션 해시는 포함하나 credential 원문은 저장하지 않음",
            "SIGKILL·재부팅 전 backup 실행은 보장하지 않음",
        ],
    )
    manifest["expected_reachable_objects"] = expected_reachable_objects
    manifest["source_sha256"] = source_identity()
    manifest["snapshot_file"] = "backend.sqlite3"
    original_error = backup_error = None
    db = None
    try:
        db = factory()
        stat = db.path.stat()
        manifest["source"] = dict(
            path=str(db.path), device=stat.st_dev, inode=stat.st_ino
        )
        try:
            yield db
        except BaseException as exc:
            original_error = exc
            manifest["termination"] = type(exc).__name__
        else:
            manifest["termination"] = "NORMAL"
        try:
            db.assert_owned()
            partial = destination / "backend.partial.sqlite3"
            fd = os.open(partial, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            deadline = time.monotonic() + 60

            def progress(status, remaining, total):
                if time.monotonic() > deadline:
                    raise ArtifactError("BACKUP_DEADLINE")

            with (
                closing(db.connect()) as source,
                closing(sqlite3.connect(partial)) as saved,
            ):
                manifest["source_journal_mode"] = source.execute(
                    "PRAGMA journal_mode"
                ).fetchone()[0]
                source.backup(saved, pages=256, progress=progress, sleep=0.01)
                # 하나의 self-contained 파일. live WAL 파일을 복사하지 않는다.
                saved.execute("PRAGMA journal_mode=DELETE")
            manifest["identity"] = inspect_snapshot(partial)
            if (
                expected_reachable_objects is not None
                and manifest["identity"]["reachable_objects"]
                != expected_reachable_objects
            ):
                raise ArtifactError("EXPECTED_OBJECT_COUNT_MISMATCH")
            manifest["snapshot_sha256"] = digest(partial)
            manifest["snapshot_bytes"] = partial.stat().st_size
            with open(partial, "rb") as stream:
                os.fsync(stream.fileno())
            partial.rename(destination / "backend.sqlite3")
            manifest["backup_status"] = "COMPLETE"
            manifest["created_at"] = datetime.now(timezone.utc).isoformat()
        except BaseException as exc:
            backup_error = exc
            manifest["backup_error_type"] = type(exc).__name__
    except BaseException as exc:
        backup_error = exc
        manifest["backup_error_type"] = type(exc).__name__
    finally:
        if db is not None:
            try:
                db.__exit__(None, None, None)
            except BaseException as exc:
                backup_error = exc
                manifest["cleanup_error_type"] = type(exc).__name__
            manifest["cleanup"] = dict(
                source_removed=not db.path.exists(),
                directory_removed=not db.path.parent.exists(),
            )
            if not manifest["cleanup"]["source_removed"] and backup_error is None:
                backup_error = ArtifactError("SOURCE_CLEANUP_FAILED")
        else:
            manifest["cleanup"] = dict(source_removed=False, directory_removed=False)
        # manifest 하나만으로 complete를 오인하지 않도록 실패 표식을 분리한다.
        success = backup_error is None and manifest["cleanup"]["source_removed"]
        temp = destination / "manifest.partial.json"
        _json_file(temp, manifest)
        temp.rename(destination / ("manifest.json" if success else "failure.json"))
        fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    if original_error is not None:
        if backup_error is not None:
            original_error.add_note("test-only backend artifact preservation failed")
        raise original_error
    if backup_error is not None:
        raise ArtifactError("BACKEND_ARTIFACT_PRESERVATION_FAILED") from backup_error

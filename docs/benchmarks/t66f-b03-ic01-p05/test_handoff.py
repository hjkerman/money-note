"""P05 작은 합성 DB만 사용. 원 P03/P04 파일에 접근하거나 재생성하지 않는다."""

import asyncio
import base64
from contextlib import closing
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx
import pytest

from app import auth
from isolated_sync.canonical import CanonicalError
from isolated_sync.http import create_app
from isolated_sync.retention import RetentionRepository
from isolated_sync.retention_schema import RetentionSandbox
from isolated_sync.raw import MONEY_SETTINGS, TABLES
from tests.test_isolated_sync_capture import ROWS, insert
from tests.test_isolated_sync_observation import EVAL, NOW
from tests.test_isolated_sync_transfer import graph

import artifact_handoff as handoff

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
CASE = EVIDENCE / os.environ.get("P05_CASE_ROOT", "run-final")
ARTIFACTS = CASE / "artifacts"
URL = "/api/sync/v1/observations"


def write(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


@pytest.fixture
def token():
    return secrets.token_urlsafe(32)


def seeded(token):
    db = RetentionSandbox()
    try:
        with db.connect() as conn:
            for table, row in ROWS.items():
                value = dict(row)
                if table == "cash_flows":
                    value["amount_value"] = -50
                insert(conn, table, value)
            for key in MONEY_SETTINGS:
                conn.execute(
                    "INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')",
                    (key,),
                )
            conn.execute(
                "INSERT INTO users(id,username,password_hash) VALUES (1,'p05-synthetic','unused')"
            )
            conn.execute(
                "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",
                (auth._hash_session_token(token),),
            )
        db.install()
        db.bootstrap()
        return db
    except BaseException:
        db.__exit__(None, None, None)
        raise


def headers(token):
    return {"Authorization": "Bearer " + token}


def observe(client, token, base=None):
    return client.post(
        URL,
        json=dict(protocol=1, request_id=str(uuid4()), base=base, inline_bytes=0),
        headers=headers(token),
    )


def download(client, token, manifest):
    ref = manifest["target"]["raw_ref"]
    return client.post(
        URL + "/" + manifest["observation_id"] + "/objects",
        json=dict(
            protocol=1,
            request_id=str(uuid4()),
            items=[dict(path=[ref["hash"]], offset="0", length=int(ref["bytes"]))],
        ),
        headers=headers(token),
    )


@pytest.mark.parametrize(
    "ending",
    [
        "normal",
        "request_failure",
        "acquisition_failure",
        "expiry",
        "exception",
        "cancel",
    ],
)
def test_termination_preserves_authentic_target(token, ending):
    destination = ARTIFACTS / ending
    failure = asyncio.CancelledError if ending == "cancel" else RuntimeError
    caught = None
    now = [NOW]
    try:
        with handoff.retained_backend(
            lambda: seeded(token), destination=destination, fixture_name="ROWS-small"
        ) as db:
            source = db.path
            app = create_app(
                RetentionRepository(db, clock=lambda: now[0], evaluation=lambda: EVAL)
            )
            with TestClient(app) as client:
                response = observe(client, token)
                assert response.status_code == 201
                manifest = response.json()
                independent = graph(db, manifest)
                assert download(client, token, manifest).status_code == 200
                if ending == "request_failure":
                    assert (
                        observe(client, "unrecognized-synthetic-token").status_code
                        == 401
                    )
                elif ending == "acquisition_failure":
                    bad = client.post(
                        URL + "/" + manifest["observation_id"] + "/objects",
                        json={},
                        headers=headers(token),
                    )
                    assert bad.status_code == 422
                elif ending == "expiry":
                    now[0] += timedelta(seconds=901)
                    assert (
                        download(client, token, manifest).json()["error"]["code"]
                        == "OBSERVATION_EXPIRED"
                    )
            # 실제 ASGI lifespan/worker 종료 후, finally 경계를 검증한다.
            if ending in ("exception", "cancel"):
                raise failure("P05 controlled termination")
    except (RuntimeError, asyncio.CancelledError) as exc:
        caught = exc
    assert (caught is not None) == (ending in ("exception", "cancel"))
    assert not source.exists() and not source.parent.exists()
    saved = handoff.verify_artifact(destination)
    assert saved["identity"]["target"] == manifest["target"]
    assert saved["identity"]["reachable_objects"] == len(independent)
    assert saved["source_journal_mode"] == "wal"
    assert token not in (destination / "manifest.json").read_text()
    assert os.stat(destination / "backend.sqlite3").st_mode & 0o777 == 0o600


def test_backup_failure_and_partial_artifact_explicit(token):
    for label, corrupt_after_backup in (
        ("backup-failure", False),
        ("verification-failure", True),
    ):
        destination = ARTIFACTS / label
        with pytest.raises(handoff.ArtifactError, match="PRESERVATION_FAILED"):
            with handoff.retained_backend(
                lambda: seeded(token), destination=destination
            ) as db:
                source = db.path
                with TestClient(
                    create_app(
                        RetentionRepository(
                            db, clock=lambda: NOW, evaluation=lambda: EVAL
                        )
                    )
                ) as c:
                    assert observe(c, token).status_code == 201
                manager = (
                    patch.object(
                        handoff,
                        "inspect_snapshot",
                        side_effect=RuntimeError("injected"),
                    )
                    if corrupt_after_backup
                    else patch.object(
                        db, "connect", side_effect=sqlite3.OperationalError("injected")
                    )
                )
                manager.start()
        manager.stop()
        assert not source.exists()
        assert not (destination / "manifest.json").exists()
        assert (
            json.loads((destination / "failure.json").read_text())["backup_status"]
            == "INCOMPLETE"
        )
        assert (destination / "backend.partial.sqlite3").exists()


def test_original_exception_not_lost_on_backup_failure(token):
    destination = ARTIFACTS / "double-failure"
    manager = None
    try:
        with pytest.raises(ValueError, match="body failure") as caught:
            with handoff.retained_backend(
                lambda: seeded(token), destination=destination
            ) as db:
                source = db.path
                manager = patch.object(
                    db,
                    "connect",
                    side_effect=sqlite3.OperationalError("backup failure"),
                )
                manager.start()
                raise ValueError("body failure")
    finally:
        if manager:
            manager.stop()
    assert not source.exists()
    assert any("preservation failed" in note for note in caught.value.__notes__)
    assert (destination / "failure.json").exists()


def test_existing_destination_never_touched():
    destination = ARTIFACTS / "normal"
    before = {str(p): handoff.digest(p) for p in destination.iterdir() if p.is_file()}
    with pytest.raises(FileExistsError):
        with handoff.retained_backend(
            lambda: pytest.fail("must not create server"), destination=destination
        ):
            pytest.fail("must not enter")
    assert before == {
        str(p): handoff.digest(p) for p in destination.iterdir() if p.is_file()
    }


def test_default_cleanup_has_no_artifact(token):
    with handoff.retained_backend(lambda: seeded(token)) as db:
        path = db.path
    assert not path.exists() and not path.parent.exists()


def test_live_wal_and_uncommitted_writes(token):
    destination = ARTIFACTS / "wal"
    with handoff.retained_backend(lambda: seeded(token), destination=destination) as db:
        with TestClient(
            create_app(
                RetentionRepository(db, clock=lambda: NOW, evaluation=lambda: EVAL)
            )
        ) as c:
            manifest = observe(c, token).json()
        reader = sqlite3.connect(db.path)
        reader.execute("BEGIN")
        reader.execute("SELECT * FROM users").fetchall()
        writer = sqlite3.connect(db.path)
        original_exit = db.__exit__

        def exit_after_snapshot(*args):
            writer.rollback()
            writer.close()
            reader.close()
            return original_exit(*args)

        db.__exit__ = exit_after_snapshot
        writer.execute("UPDATE users SET username='committed-wal-value' WHERE id=1")
        writer.commit()
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE users SET username='must-not-be-backed-up' WHERE id=1")
        assert Path(str(db.path) + "-wal").stat().st_size > 0
    saved = handoff.verify_artifact(destination)
    assert saved["identity"]["target"] == manifest["target"]
    with closing(sqlite3.connect(destination / "backend.sqlite3")) as conn:
        assert (
            conn.execute("SELECT username FROM users WHERE id=1").fetchone()[0]
            == "committed-wal-value"
        )
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert not Path(saved["source"]["path"]).exists()


def test_restore_uses_new_epoch_and_rejects_old_authority(token):
    destination = ARTIFACTS / "restore-source"
    with handoff.retained_backend(lambda: seeded(token), destination=destination) as db:
        with TestClient(
            create_app(
                RetentionRepository(db, clock=lambda: NOW, evaluation=lambda: EVAL)
            )
        ) as c:
            old = observe(c, token).json()
    saved = handoff.verify_artifact(destination)
    source_digest = handoff.digest(destination / "backend.sqlite3")
    with RetentionSandbox() as restored:
        # 기존 synthetic test의 backup-into-new-owned-inode 패턴. marker를 authority로 채택하지 않는다.
        with (
            closing(
                sqlite3.connect(
                    (destination / "backend.sqlite3").as_uri() + "?mode=ro", uri=True
                )
            ) as source,
            closing(sqlite3.connect(restored.path)) as target,
        ):
            source.backup(target)
            # 보존본은 DELETE의 단일 파일, 실제 retention runtime은 WAL이다.
            target.execute("PRAGMA journal_mode=WAL")
        # 해제된 inode 번호는 재사용될 수 있다. 지금 살아 있는 artifact와의
        # 구분 및 새 sandbox의 실제 descriptor fence를 검사한다.
        artifact_stat = (destination / "backend.sqlite3").stat()
        assert restored._owned_file == (
            restored.path.stat().st_dev,
            restored.path.stat().st_ino,
        )
        assert restored._owned_file != (artifact_stat.st_dev, artifact_stat.st_ino)
        assert str(restored.path) != saved["source"]["path"]
        restored.install()
        with closing(sqlite3.connect(restored.path)) as conn:
            before = {t: conn.execute("SELECT * FROM " + t).fetchall() for t in TABLES}
        # §5의 새 bootstrap을 반드시 실행한다. old Target을 복원 서버에 광고하지 않는다.
        restored.bootstrap()
        with TestClient(
            create_app(
                RetentionRepository(
                    restored, clock=lambda: NOW, evaluation=lambda: EVAL
                )
            )
        ) as c:
            assert observe(c, "invalid").status_code == 401
            first = observe(c, token)
            assert first.status_code == 201
            fresh = first.json()
            assert (
                fresh["target"]["ns"]["server_id"] == old["target"]["ns"]["server_id"]
            )
            assert (
                fresh["target"]["ns"]["dataset_id"] == old["target"]["ns"]["dataset_id"]
            )
            assert fresh["target"]["ns"]["epoch"] != old["target"]["ns"]["epoch"]
            assert fresh["target"]["sync_root"] != old["target"]["sync_root"]
            old_response = download(c, token, old)
            assert old_response.status_code != 200
            response = download(c, token, fresh)
            assert response.status_code == 200
            body = base64.b64decode(
                response.json()["chunks"][0]["data_base64"], validate=True
            )
            assert (
                hashlib.sha256(b"money-note.sync.v1/raw-root\0" + body).hexdigest()
                == fresh["target"]["raw_ref"]["hash"]
            )
            wrong = json.loads(json.dumps(old["target"]))
            wrong["ns"]["dataset_id"] = str(uuid4())
            assert observe(c, token, wrong).status_code == 409
        with closing(sqlite3.connect(restored.path)) as conn:
            assert before == {
                t: conn.execute("SELECT * FROM " + t).fetchall() for t in TABLES
            }
        write(
            "restored-d3.json",
            dict(
                old_target=old["target"],
                fresh_target=fresh["target"],
                old_observation_status=old_response.status_code,
                authenticated_new_D3=response.status_code,
                financial_rows_equal=True,
                new_private_ownership_verified=True,
            ),
        )
    assert source_digest == handoff.digest(destination / "backend.sqlite3")


@pytest.mark.parametrize("ending", ["normal", "exception"])
def test_real_tls_server_lifecycle(ending):
    out = CASE / ("tls-" + ending)
    destination = ARTIFACTS / ("tls-" + ending)
    with open(CASE / ("tls-" + ending + ".stderr.log"), "x") as errors:
        process = subprocess.Popen(
            [
                str(HERE.parents[2] / ".venv/bin/python"),
                str(HERE / "server.py"),
                "1000",
                str(out),
                str(destination),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
        )
        try:
            initial = json.loads(process.stdout.readline())
            with httpx.Client(verify=False, timeout=30) as c:
                response = c.post(
                    initial["origin"] + URL,
                    headers=headers(initial["token"]),
                    json=dict(
                        protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0
                    ),
                )
                assert response.status_code == 201
                manifest = response.json()
                ref = manifest["target"]["raw_ref"]
                downloaded = c.post(
                    initial["origin"]
                    + URL
                    + "/"
                    + manifest["observation_id"]
                    + "/objects",
                    headers=headers(initial["token"]),
                    json=dict(
                        protocol=1,
                        request_id=str(uuid4()),
                        items=[
                            dict(
                                path=[ref["hash"]], offset="0", length=int(ref["bytes"])
                            )
                        ],
                    ),
                )
                assert downloaded.status_code == 200
            process.stdin.write(
                json.dumps(
                    dict(
                        command="exit"
                        if ending == "normal"
                        else "p05-controlled-exception"
                    )
                )
                + "\n"
            )
            process.stdin.flush()
            if ending == "normal":
                assert json.loads(process.stdout.readline()) == {"ok": True}
            code = process.wait(timeout=60)
            assert code == (0 if ending == "normal" else 1)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=30)
            process.stdin.close()
            process.stdout.close()
    saved = handoff.verify_artifact(destination)
    assert saved["identity"]["reachable_objects"] == 4132
    assert saved["identity"]["target"] == manifest["target"]
    assert saved["termination"] == ("NORMAL" if ending == "normal" else "ValueError")


def test_manifest_tampering_is_rejected():
    source = ARTIFACTS / "normal"
    destination = ARTIFACTS / "manifest-tamper"
    destination.mkdir()
    # 작은 소유 disposable 사본만 변경한다. canonical artifact는 불변이다.
    with (
        closing(
            sqlite3.connect(
                (source / "backend.sqlite3").as_uri() + "?mode=ro", uri=True
            )
        ) as conn,
        closing(sqlite3.connect(destination / "backend.sqlite3")) as copy,
    ):
        conn.backup(copy)
    value = json.loads((source / "manifest.json").read_text())
    value["snapshot_sha256"] = handoff.digest(destination / "backend.sqlite3")
    value["identity"]["target"]["ns"]["epoch"] = str(uuid4())
    (destination / "manifest.json").write_text(json.dumps(value))
    with pytest.raises(handoff.ArtifactError, match="IDENTITY_MISMATCH"):
        handoff.verify_artifact(destination)
    with open(destination / "backend.sqlite3", "ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(handoff.ArtifactError, match="DIGEST_MISMATCH"):
        handoff.verify_artifact(destination)


def test_declared_expected_graph_count_is_checked(token):
    destination = ARTIFACTS / "wrong-object-count"
    with pytest.raises(handoff.ArtifactError, match="PRESERVATION_FAILED"):
        with handoff.retained_backend(
            lambda: seeded(token), destination=destination, expected_reachable_objects=1
        ) as db:
            with TestClient(
                create_app(
                    RetentionRepository(db, clock=lambda: NOW, evaluation=lambda: EVAL)
                )
            ) as c:
                assert observe(c, token).status_code == 201
    assert not (destination / "manifest.json").exists()
    assert (destination / "failure.json").exists()


def test_live_database_replacement_rejected(token):
    with RetentionSandbox() as db, RetentionSandbox() as other:
        path = db.path
        saved = path.with_name("p05-owned-held.sqlite3")
        path.rename(saved)
        path.symlink_to(other.path)
        try:
            with pytest.raises(CanonicalError, match="OWNERSHIP"):
                db.connect()
        finally:
            path.unlink()
            saved.rename(path)


def test_actual_async_task_cancellation(token):
    destination = ARTIFACTS / "async-cancel"

    async def scenario():
        ready = asyncio.Event()

        async def work():
            with handoff.retained_backend(
                lambda: seeded(token), destination=destination
            ) as db:
                with TestClient(
                    create_app(
                        RetentionRepository(
                            db, clock=lambda: NOW, evaluation=lambda: EVAL
                        )
                    )
                ) as c:
                    assert observe(c, token).status_code == 201
                ready.set()
                await asyncio.Future()

        task = asyncio.create_task(work())
        await ready.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert handoff.verify_artifact(destination)["termination"] == "CancelledError"


def test_factory_failure_is_not_a_complete_artifact():
    destination = ARTIFACTS / "setup-failure"

    def failed_factory():
        raise RuntimeError("controlled setup failure")

    with pytest.raises(handoff.ArtifactError, match="PRESERVATION_FAILED"):
        with handoff.retained_backend(failed_factory, destination=destination):
            pytest.fail("must not enter")
    assert (destination / "failure.json").exists()
    assert not (destination / "manifest.json").exists()

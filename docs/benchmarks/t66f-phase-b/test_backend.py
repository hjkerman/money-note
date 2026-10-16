"""독립 합성 D1–D3c durable fence와 실제 process 종료 검사."""

from datetime import timedelta
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import signal
import sqlite3
import sys
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from isolated_sync.observation import ObservationError  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionSandbox  # noqa: E402
from isolated_sync.transfer import TransferRepository  # noqa: E402
from tests.test_isolated_sync_capture import ROWS, insert  # noqa: E402
from tests.test_isolated_sync_observation import CREDENTIAL, EVAL, NOW, auth_seed  # noqa: E402
from tests.test_isolated_sync_finalization import verify  # noqa: E402

OUT = Path(
    os.environ.get("F_BACKEND_OUTPUT", "/tmp/mn-t66f-phase-b/backend-independent")
)


@pytest.fixture
def owned():
    with RetentionSandbox() as db:
        with db.connect() as conn:
            for table, row in ROWS.items():
                value = dict(row)
                if table == "cash_flows":
                    value["amount_value"] = -50
                insert(conn, table, value)
            from isolated_sync.raw import MONEY_SETTINGS

            for key in MONEY_SETTINGS:
                conn.execute(
                    "INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')",
                    (key,),
                )
            auth_seed(conn)
        db.install()
        db.bootstrap()
        yield db


def persisted(db):
    with sqlite3.connect(db.path) as conn:
        conn.row_factory = sqlite3.Row
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        return dict(
            title=conn.execute(
                "SELECT title FROM ledger_entries WHERE id=100"
            ).fetchone()[0],
            current=dict(conn.execute("SELECT * FROM sync_current").fetchone()),
            raw_revision=conn.execute(
                "SELECT revision FROM authoritative_state_revision"
            ).fetchone()[0],
            context=conn.execute("SELECT count(*) FROM sync_tx_context").fetchone()[0],
        )


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)

    def encode(v):
        return (
            {"sha256": hashlib.sha256(v).hexdigest()}
            if isinstance(v, bytes)
            else str(v)
        )

    (OUT / (name + ".json")).write_text(json.dumps(value, default=encode, indent=2))


@pytest.mark.parametrize(
    "boundary", ["before_finalize", "after_finalize", "after_commit"]
)
def test_true_backend_kill_preserves_complete_roots(owned, boundary):
    before = persisted(owned)
    context = multiprocessing.get_context("fork")
    parent, child = context.Pipe()

    def run():
        conn = owned.connect()
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='독립 crash 변경' WHERE id=100")
        if boundary != "before_finalize":
            conn.finalize()
        if boundary == "after_commit":
            conn.commit()
        child.send(dict(pid=os.getpid(), boundary=boundary))
        signal.pause()

    p = context.Process(target=run)
    p.start()
    try:
        assert parent.poll(60), "backend child barrier not reached"
        marker = parent.recv()
        os.kill(p.pid, signal.SIGKILL)
        p.join(timeout=15)
        assert p.exitcode == -signal.SIGKILL
        after = persisted(owned)
        if boundary == "after_commit":
            assert after["title"] == "독립 crash 변경"
            assert after["current"]["raw_hash"] != before["current"]["raw_hash"]
        else:
            assert after == before
        with owned.connect() as conn:
            roots = verify(conn)  # 별도 radix/F(raw)/SQL row oracle도 함께 대조한다.
        assert after["context"] == 0
        assert after["current"]["revision"] == after["raw_revision"]
        save(
            "backend-kill-" + boundary,
            dict(
                marker=marker,
                signal="SIGKILL",
                before=before,
                after=after,
                verified_roots=roots,
            ),
        )
    finally:
        if p.is_alive():
            p.kill()
            p.join()


def test_unfinalized_native_commit_rejected_without_source_change(owned):
    before = persisted(owned)
    conn = owned.connect()
    try:
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='미확정 변경' WHERE id=100")
        with pytest.raises(sqlite3.IntegrityError):
            conn.commit()
        conn.rollback()
    finally:
        conn.close()
    assert persisted(owned) == before


def test_old_observation_cannot_transfer_a_new_generation_root(owned):
    repo = RetentionRepository(owned, clock=lambda: NOW, evaluation=lambda: EVAL)
    old = repo.create(CREDENTIAL, request_id=str(uuid4()), guard=lambda: CREDENTIAL)
    with owned.connect() as conn:
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='새 generation' WHERE id=100")
        conn.finalize()
    new = repo.create(CREDENTIAL, request_id=str(uuid4()), guard=lambda: CREDENTIAL)
    assert old["target"]["raw_ref"] != new["target"]["raw_ref"]
    request = dict(
        protocol=1,
        request_id=str(uuid4()),
        items=[dict(path=[new["target"]["raw_ref"]["hash"]], offset="0", length=1)],
    )
    with pytest.raises(ObservationError):
        TransferRepository(repo).acquire(
            old["observation_id"], CREDENTIAL, guard=lambda: CREDENTIAL, request=request
        )
    save(
        "old-new-root",
        dict(old=old["target"], new=new["target"], state=persisted(owned)),
    )


def test_expired_observation_remains_retired_after_clock_reversal(owned):
    clock = [NOW]
    repo = RetentionRepository(owned, clock=lambda: clock[0], evaluation=lambda: EVAL)
    old = repo.create(CREDENTIAL, request_id=str(uuid4()), guard=lambda: CREDENTIAL)
    clock[0] += timedelta(seconds=901)
    with pytest.raises(ObservationError):
        repo.lookup(old["observation_id"], CREDENTIAL, guard=lambda: CREDENTIAL)
    clock[0] = NOW
    with pytest.raises(ObservationError):
        repo.lookup(old["observation_id"], CREDENTIAL, guard=lambda: CREDENTIAL)
    with sqlite3.connect(owned.path) as conn:
        status = conn.execute(
            "SELECT status FROM sync_observations WHERE id=?", (old["observation_id"],)
        ).fetchone()[0]
        assert status == "retired"
    save("expiry", dict(status=status, state=persisted(owned)))

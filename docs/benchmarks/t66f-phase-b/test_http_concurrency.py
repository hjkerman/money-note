"""실제 TLS handler 경쟁·SQL busy·동일 nonce retry의 독립 저장 oracle."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = Path(os.environ.get("F_HTTP_OUTPUT", "/tmp/mn-t66f-phase-b/http-concurrency"))


@pytest.fixture
def service():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "server.log").open("w") as log:
        p = subprocess.Popen(
            [str(ROOT / ".venv/bin/python"), str(HERE / "server.py"), "3"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
        )
        try:
            init = json.loads(p.stdout.readline())
            yield init
        finally:
            if p.poll() is None:
                p.stdin.write('{"command":"exit"}\n')
                p.stdin.flush()
                p.communicate(timeout=30)


def payload():
    return dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)


def test_real_sql_writer_conflict_has_bounded_retry_and_no_false_lease(service):
    base = service["origin"] + "/api/sync/v1/observations"
    headers = {"Authorization": "Bearer " + service["token"]}
    body = payload()
    with (
        httpx.Client(verify=False, timeout=15) as client,
        sqlite3.connect(service["owned_db_path"]) as db,
    ):
        before = db.execute(
            "SELECT count(*) FROM sync_observations WHERE status='available'"
        ).fetchone()[0]
        db.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        blocked = client.post(base, json=body, headers=headers)
        elapsed = time.monotonic() - started
        db.rollback()
        assert blocked.status_code == 503, blocked.text
        assert blocked.json()["error"]["action"] == "retry_same"
        assert elapsed < 5
        assert (
            db.execute(
                "SELECT count(*) FROM sync_observations WHERE status='available'"
            ).fetchone()[0]
            == before
        )
        retry = client.post(base, json=body, headers=headers)
        assert retry.status_code == 201, retry.text
        duplicate = client.post(base, json=body, headers=headers)
        assert duplicate.status_code == 200 and duplicate.content == retry.content
        lease = retry.json()["observation_id"]
        assert client.delete(base + "/" + lease, headers=headers).status_code == 204
        assert (
            db.execute(
                "SELECT count(*) FROM sync_observations WHERE status='available'"
            ).fetchone()[0]
            == before
        )
        (OUT / "busy.json").write_text(
            json.dumps(
                dict(
                    first_status=blocked.status_code,
                    error=blocked.json(),
                    seconds=elapsed,
                    retry_status=retry.status_code,
                    duplicate_status=duplicate.status_code,
                    active_before=before,
                    active_after=before,
                ),
                indent=2,
            )
        )


def test_real_five_authenticated_requests_obey_worker_and_lease_budgets(service):
    url = service["origin"] + "/api/sync/v1/observations"
    headers = {"Authorization": "Bearer " + service["token"]}
    barrier = threading.Barrier(5)

    def run(_):
        body = payload()
        history = []
        with httpx.Client(verify=False, timeout=15) as client:
            barrier.wait(15)
            for delay in [0, 0.1, 0.25]:
                time.sleep(delay)
                r = client.post(url, json=body, headers=headers)
                history.append(
                    dict(
                        status=r.status_code, code=r.json().get("error", {}).get("code")
                    )
                )
                if r.status_code != 503:
                    break
            return dict(history=history, response=r.json(), status=r.status_code)

    with ThreadPoolExecutor(5) as pool:
        results = list(pool.map(run, range(5)))
    assert all(r["status"] in (201, 429, 503) for r in results)
    available = [r for r in results if r["status"] == 201]
    assert 1 <= len(available) <= 4
    with (
        sqlite3.connect(service["owned_db_path"]) as db,
        httpx.Client(verify=False, timeout=15) as client,
    ):
        rows = db.execute(
            "SELECT id FROM sync_observations WHERE status='available'"
        ).fetchall()
        assert {r[0] for r in rows} == {
            r["response"]["observation_id"] for r in available
        }
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        pins = db.execute(
            "SELECT count(*) FROM sync_observation_pins WHERE active=1"
        ).fetchone()[0]
        assert pins == len(available) * 5
        for r in available:
            assert (
                client.delete(
                    url + "/" + r["response"]["observation_id"], headers=headers
                ).status_code
                == 204
            )
        assert (
            db.execute(
                "SELECT count(*) FROM sync_observations WHERE status='available'"
            ).fetchone()[0]
            == 0
        )
        subsequent = client.post(url, json=payload(), headers=headers)
        assert subsequent.status_code == 201, subsequent.text
    (OUT / "concurrent.json").write_text(
        json.dumps(
            dict(
                results=results,
                active=len(available),
                pin_rows=pins,
                followup_status=201,
            ),
            indent=2,
        )
    )

"""새 D3b/D3c 경계의 실제 owned-inode 교체와 lease coherence 검증."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
from threading import Event
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    str(ROOT / "backend"),
    str(ROOT / "docs/benchmarks/t66f-b01-independent"),
]
spec = importlib.util.spec_from_file_location(
    "b01_validated_helpers",
    ROOT / "docs/benchmarks/t66f-b01-independent/test_independent.py",
)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
from observer import Observer  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from tests.test_isolated_sync_transfer import URL, headers  # noqa: E402

pytest_plugins = ["tests.test_isolated_sync_transfer"]
OUT = Path(os.environ.get("C_IDENTITY_OUTPUT", "/tmp/mn-f-continuation/identity"))


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2))


@pytest.mark.parametrize(
    ("operation", "boundary"),
    [
        ("manifest_retry", "authenticated"),
        ("manifest_retry", "serialized"),
        ("object", "authenticated"),
        ("object", "serialized"),
        ("release", "authenticated"),
        ("release", "terminal"),
    ],
)
def test_C_DB_stale_transfer_release_cannot_operate_on_replacement(
    template, operation, boundary
):
    with prior.cloned(template, True) as a, prior.cloned(template, True) as b:
        armed = False
        entered, release = Event(), Event()

        def fault(stage, ticket):
            if armed and stage == boundary:
                entered.set()
                assert release.wait(20)

        repo_a = RetentionRepository(
            a, clock=lambda: prior.original.NOW, evaluation=lambda: prior.original.EVAL
        )
        repo_b = RetentionRepository(
            b, clock=lambda: prior.original.NOW, evaluation=lambda: prior.original.EVAL
        )
        with (
            Observer() as observer,
            prior.client(a, repo=repo_a, fault=fault) as ca,
            prior.client(b, repo=repo_b) as cb,
        ):
            nonce = prior.request()
            manifest = ca.post(URL, json=nonce, headers=headers()).json()
            lease = manifest["observation_id"]
            b_before = prior.snapshot(b)
            a_before = prior.snapshot(a)
            armed = True

            def request():
                if operation == "manifest_retry":
                    return ca.post(URL, json=nonce, headers=headers())
                if operation == "release":
                    return ca.delete(URL + "/" + lease, headers=headers())
                ref = manifest["target"]["raw_ref"]
                return ca.post(
                    URL + "/" + lease + "/objects",
                    json=dict(
                        protocol=1,
                        request_id=str(uuid4()),
                        items=[
                            dict(
                                path=[ref["hash"]], offset="0", length=int(ref["bytes"])
                            )
                        ],
                    ),
                    headers=headers(),
                )

            with ThreadPoolExecutor(1) as pool:
                f = pool.submit(request)
                assert entered.wait(15)
                saved = a.path.with_name("continuation-owned-A.sqlite3")
                a.path.rename(saved)
                a.path.symlink_to(b.path)
                try:
                    release.set()
                    response = f.result(20)
                    assert response.status_code == 500, response.text
                    assert response.json()["error"]["code"] == "STORAGE_FAILED"
                    assert prior.snapshot(b) == b_before
                    assert (
                        cb.post(
                            URL, json=prior.request(), headers=headers()
                        ).status_code
                        == 201
                    )
                finally:
                    a.path.unlink()
                    saved.rename(a.path)
            armed = False
            a_after = prior.snapshot(a)
            assert a_after["financial_sha256"] == a_before["financial_sha256"]
            assert a_after["foreign_keys"] == []
            # 경로 원상 회복 후 새 유효 요청과 원 lease cleanup이 모두 가능해야 한다.
            assert (
                ca.post(URL, json=prior.request(), headers=headers()).status_code == 201
            )
            assert ca.delete(URL + "/" + lease, headers=headers()).status_code == 204
            observer.permits_free(8)
            save(
                f"C-DB-{operation}-{boundary}",
                dict(
                    status=response.status_code,
                    body=response.json(),
                    A_before=prior.compact(a_before),
                    A_after=prior.compact(a_after),
                    B_before=prior.compact(b_before),
                    B_after=prior.compact(prior.snapshot(b)),
                    observer=observer.result(),
                ),
            )


def test_C_DB_pinned_old_manifest_remains_exact_during_new_generation(template):
    with (
        prior.cloned(template, True) as db,
        prior.client(
            db,
            repo=RetentionRepository(
                db,
                clock=lambda: prior.original.NOW,
                evaluation=lambda: prior.original.EVAL,
            ),
        ) as c,
    ):
        first = c.post(URL, json=prior.request(), headers=headers())
        assert first.status_code == 201
        old = first.json()
        old_ref = old["target"]["raw_ref"]
        with closing(sqlite3.connect(db.path)) as inspect:
            original = inspect.execute(
                "SELECT body FROM sync_objects WHERE hash=?", (old_ref["hash"],)
            ).fetchone()[0]
        with db.connect() as writer:
            writer.begin_capture()
            writer.execute(
                "UPDATE ledger_entries SET title='independent identity churn' WHERE id=1000"
            )
            writer.finalize()
            writer.commit()
        newer = c.post(URL, json=prior.request(), headers=headers())
        assert newer.status_code == 201
        assert newer.json()["target"]["raw_ref"] != old_ref
        transferred = c.post(
            URL + "/" + old["observation_id"] + "/objects",
            json=dict(
                protocol=1,
                request_id=str(uuid4()),
                items=[
                    dict(
                        path=[old_ref["hash"]], offset="0", length=int(old_ref["bytes"])
                    )
                ],
            ),
            headers=headers(),
        )
        import base64

        assert transferred.status_code == 200
        assert (
            base64.b64decode(
                transferred.json()["chunks"][0]["data_base64"], validate=True
            )
            == original
        )
        assert (
            c.delete(URL + "/" + old["observation_id"], headers=headers()).status_code
            == 204
        )
        state = prior.snapshot(db)
        assert len(state["sync_observation_pins"]) == 10
        assert sum(row[-1] == 1 for row in state["sync_observation_pins"]) == 5
        assert sum(row[-1] == 0 for row in state["sync_observation_pins"]) == 5
        save(
            "C-DB-pinned-churn",
            dict(
                old=old["target"],
                new=newer.json()["target"],
                transfer=transferred.json(),
                state=prior.compact(state),
            ),
        )

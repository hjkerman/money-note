"""독립 감사: 새 synthetic DB의 실제 ASGI와 직접 SQLite graph oracle."""

import base64
from contextlib import closing
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import sys
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient  # noqa: E402
from app import auth  # noqa: E402
from isolated_sync.http import create_app  # noqa: E402
from isolated_sync.observation import Limits as ObservationLimits  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionSandbox  # noqa: E402
from tests.test_isolated_sync_capture import ROWS, insert  # noqa: E402
from tests.test_isolated_sync_observation import NOW, EVAL  # noqa: E402

TABLES = (
    "ledger_entries",
    "monthly_panels",
    "cash_flows",
    "card_payment_batches",
    "card_payment_batch_items",
    "card_payment_events",
    "card_payment_allocations",
    "card_payment_deferrals",
    "notification_candidate_registrations",
    "app_settings",
    "app_labels",
)
ROLES = {"raw": "raw-root", "index": "index-root", "hot": "hot", "control": "control"}


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def identity(kind, raw):
    return hashlib.sha256(
        b"money-note.sync.v1/" + kind.encode() + b"\0" + raw
    ).hexdigest()


def edge_fields(body):
    kind = body["kind"]
    if kind == "raw-root":
        assert [t["name"] for t in body["tables"]] == list(TABLES)
        return [
            (
                t["root"]["ref"],
                {"snapshot-node" if t["root"]["height"] else "snapshot-leaf"},
                t["name"],
                t["root"],
            )
            for t in body["tables"]
        ]
    if kind == "snapshot-node":
        return [
            (
                d["ref"],
                {"snapshot-node" if d["height"] else "snapshot-leaf"},
                body["table"],
                d,
            )
            for d in body["children"]
        ]
    if kind == "index-root":
        return [
            (body["facts"], {"index-empty", "index-node", "index-leaf"}, None, None)
        ]
    if kind == "index-node":
        return [
            (body[k], {"index-node", "index-leaf"}, None, None)
            for k in ["left", "right"]
        ]
    assert kind in {"snapshot-leaf", "index-empty", "index-leaf", "hot", "control"}
    return []


def oracle(path, manifest):
    objects = {}
    rows = {}
    facts = []
    edges = 0
    with closing(sqlite3.connect(path)) as conn:

        def visit(ref, kinds, table=None, descriptor=None):
            nonlocal edges
            row = conn.execute(
                "SELECT body FROM sync_objects WHERE hash=?", (ref["hash"],)
            ).fetchone()
            assert row is not None
            raw = bytes(row[0])
            body = json.loads(raw)
            assert canonical(body) == raw
            assert identity(body["kind"], raw) == ref["hash"] and len(raw) == int(
                ref["bytes"]
            )
            assert body["kind"] in kinds and body["ns"] == manifest["target"]["ns"]
            if table is not None:
                assert body["table"] == table
                assert all(
                    body[f] == descriptor[f] for f in ["height", "count", "min", "max"]
                )
            if ref["hash"] in objects:
                return
            objects[ref["hash"]] = dict(
                ref=ref, data_base64=base64.b64encode(raw).decode(), kind=body["kind"]
            )
            if body["kind"] == "snapshot-leaf":
                rows.setdefault(body["table"], []).extend(body["rows"])
            if body["kind"] == "index-leaf":
                facts.extend(body["facts"])
            children = edge_fields(body)
            edges += len(children)
            for child in children:
                visit(*child)

        for role, kind in ROLES.items():
            visit(manifest["target"][role + "_ref"], {kind})
        conn.row_factory = sqlite3.Row
        source = {
            table: [dict(r) for r in conn.execute("SELECT * FROM " + table)]
            for table in TABLES
        }
        source["app_settings"] = [
            r
            for r in source["app_settings"]
            if r["key"] not in {"share_pin_hash", "share_pin_is_default"}
        ]
        revision = conn.execute(
            "SELECT revision FROM authoritative_state_revision"
        ).fetchone()[0]
    # 빈 leaf에도 table key를 남겨야 한다.
    assert set(rows) == set(TABLES)
    for table, items in rows.items():
        column = (
            "entry_payment_key"
            if table == "card_payment_deferrals"
            else "registration_key"
            if table == "notification_candidate_registrations"
            else "key"
            if table in {"app_settings", "app_labels"}
            else "id"
        )
        got = {str(r["key"][1]): r["value"] for r in items}
        assert len(got) == len(items) and got == {
            str(r[column]): r for r in source[table]
        }
    # Fetched facts로부터 독립 canonical Patricia를 재구성한다. Production builder 미사용.
    common = {
        k: json.loads(
            base64.b64decode(
                objects[manifest["target"]["index_ref"]["hash"]]["data_base64"]
            )
        )[k]
        for k in ["ns", "canon", "raw_schema", "structural"]
    }
    groups = {}
    for fact in facts:
        groups.setdefault(identity("fact-key", canonical(fact["key"])), []).append(fact)

    def make(kind, **values):
        raw = canonical(dict(kind=kind, **common, **values))
        return dict(hash=identity(kind, raw), bytes=str(len(raw)))

    def build(keys):
        if not keys:
            return make("index-empty", count="0")
        if len(keys) == 1:
            group = sorted(groups[keys[0]], key=lambda f: canonical(f["key"]))
            return make(
                "index-leaf", digest=keys[0], count=str(len(group)), facts=group
            )
        low = bin(int(keys[0], 16))[2:].zfill(256)
        high = bin(int(keys[-1], 16))[2:].zfill(256)
        n = next(i for i in range(256) if low[i] != high[i])
        left = [k for k in keys if bin(int(k, 16))[2:].zfill(256)[n] == "0"]
        right = [k for k in keys if k not in left]
        return make(
            "index-node",
            prefix=low[:n],
            left=build(left),
            right=build(right),
            count=str(sum(len(groups[k]) for k in keys)),
        )

    assert (
        make("index-root", count=str(len(facts)), facts=build(sorted(groups)))
        == manifest["target"]["index_ref"]
    )
    return dict(
        manifest=manifest,
        objects=list(objects.values()),
        source=source,
        rows=rows,
        edges=edges,
        revision=revision,
        patricia="PASS",
        tables=len(rows),
    )


def main():
    empty = "--empty" in sys.argv
    clock = [NOW]
    token = secrets.token_urlsafe(24)
    with RetentionSandbox() as db:
        with db.connect() as conn:
            if empty:
                for table in reversed(TABLES):
                    conn.execute("DELETE FROM " + table)
            for table, row in [] if empty else ROWS.items():
                value = dict(row)
                if table == "cash_flows":
                    value["amount_value"] = -50
                insert(conn, table, value)
            for n in range(0 if empty else 12):
                insert(
                    conn,
                    "ledger_entries",
                    dict(
                        id=1000 + n,
                        book_section="archive",
                        entry_kind="expense",
                        entry_date="2026-07-03",
                        title="독립 합성 😀 e\u0301 " + str(n),
                        amount_value=1000,
                        sort_order=n,
                        payment_key="audit-" + str(n),
                    ),
                )
            for key in (
                ["scheduled_income", "cash_flow_balance", "card_limit"]
                if empty
                else [
                    "scheduled_income",
                    "cash_flow_balance",
                    "card_limit",
                    "base_next_month_liquidity",
                    "liquidity_status",
                ]
            ):
                conn.execute(
                    "INSERT OR REPLACE INTO app_settings(key,value) VALUES (?,?)",
                    (key, "0"),
                )
            conn.execute(
                "INSERT INTO users(id,username,password_hash) VALUES(1,'independent-synthetic','unused')"
            )
            conn.execute(
                "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES(1,?,'2026-12-31T00:00:00Z')",
                (auth._hash_session_token(token),),
            )
        db.install()
        db.bootstrap()
        repo = RetentionRepository(
            db,
            clock=lambda: clock[0],
            evaluation=lambda: EVAL,
            limits=ObservationLimits(lease_seconds=900),
        )
        with (
            patch(
                "app.services.judgment.common._MESSAGE_RANDOM.randrange", return_value=0
            ),
            TestClient(create_app(repo)) as client,
        ):
            headers = {"Authorization": "Bearer " + token}

            def observe():
                r = client.post(
                    "/api/sync/v1/observations",
                    headers=headers,
                    json=dict(
                        protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0
                    ),
                )
                assert r.status_code == 201, r.text
                return r.json()

            manifest = observe()
            initial = oracle(db.path, manifest)
            client.delete(
                "/api/sync/v1/observations/" + manifest["observation_id"],
                headers=headers,
            )
            print(json.dumps(dict(token=token, fixture=initial)), flush=True)
            for line in sys.stdin:
                value = json.loads(line)
                command = value["command"]
                if command == "http":
                    r = client.request(
                        value["method"],
                        value["path"],
                        headers=value["headers"],
                        content=base64.b64decode(value["body_base64"]),
                    )
                    if (
                        value["method"] == "POST"
                        and value["path"].endswith("/observations")
                        and r.status_code in [200, 201]
                    ):
                        manifest = r.json()
                    result = dict(
                        status=r.status_code,
                        body_base64=base64.b64encode(r.content).decode(),
                        headers=dict(r.headers),
                    )
                elif command == "oracle":
                    result = oracle(db.path, manifest)
                elif command == "mutate":
                    with db.connect() as conn:
                        conn.begin_capture()
                        conn.execute(
                            "UPDATE ledger_entries SET title=? WHERE id=100",
                            ("독립 변경 " + str(uuid4()),),
                        )
                        conn.finalize()
                    result = dict(ok=True)
                elif command == "advance":
                    clock[0] += timedelta(seconds=value["seconds"])
                    result = dict(ok=True)
                elif command == "revoke":
                    with db.connect() as conn:
                        conn.execute("DELETE FROM auth_sessions")
                    result = dict(ok=True)
                elif command == "exit":
                    print('{"ok":true}', flush=True)
                    break
                else:
                    raise AssertionError(command)
                print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()

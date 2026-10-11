"""독립 D3c 감사: 합성 SQLite만 사용하며 구현 helper로 기대 reachability를 만들지 않는다."""

import asyncio
import base64
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import signal
import sqlite3
import sys
from threading import Event, Lock
from unittest.mock import patch
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.authoritative_state import BundleCredential  # noqa: E402
from isolated_sync import http  # noqa: E402
from isolated_sync.canonical import CanonicalError  # noqa: E402
from isolated_sync.observation import Evaluation, Limits, ObservationError  # noqa: E402
from isolated_sync.retention import Collector, RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionConnection, RetentionSandbox  # noqa: E402

OUT = Path("/tmp/mn-d3c-audit")
OUT.mkdir(exist_ok=True)
NOW = datetime(2026, 10, 11, 4, tzinfo=timezone.utc)
TOKEN = "independent-d3c-audit-principal-one"
OTHER = "independent-d3c-audit-principal-two"
CRED = BundleCredential(hashlib.sha256(TOKEN.encode()).hexdigest(), 1)
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
PRIMARY = {
    t: (
        "entry_payment_key"
        if t == "card_payment_deferrals"
        else "registration_key"
        if t == "notification_candidate_registrations"
        else "key"
        if t in ("app_settings", "app_labels")
        else "id"
    )
    for t in TABLES
}
ROLES = ("raw", "index", "input", "hot", "control")
URL = "/api/sync/v1/observations"
EVIDENCE = []


def c1(value):
    # Python scalar ordering and integral REAL spelling are the binding C1 rules.
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def digest(kind, raw):
    return hashlib.sha256(
        b"money-note.sync.v1/" + kind.encode("ascii") + b"\0" + raw
    ).hexdigest()


def key(value):
    return ["i", str(value)] if type(value) is int else ["t", value]


def ref(body):
    raw = c1(body)
    return {"hash": digest(body["kind"], raw), "bytes": str(len(raw))}


def record(name, **value):
    item = {"scenario": name, "result": "PASS", **value}
    EVIDENCE.append(item)
    (OUT / (name + ".json")).write_text(json.dumps(item, ensure_ascii=False, indent=2))


def insert(conn, table, row):
    conn.execute(
        "INSERT INTO "
        + table
        + "("
        + ",".join(row)
        + ") VALUES ("
        + ",".join("?" for _ in row)
        + ")",
        tuple(row.values()),
    )


def seed(conn, history=24):
    rows = {
        "ledger_entries": dict(
            id=41,
            book_section="current",
            entry_kind="expense",
            entry_date="2026-10-11",
            title="독립 카드 😀",
            usage_place="감사 합성",
            amount_value=2300,
            sort_order=1,
            payment_key="audit-payment",
            spending_category="general",
        ),
        "monthly_panels": dict(
            id=9,
            month="2026-10",
            panel_type="claim",
            title="독립 청구",
            amount_value=127,
            sort_order=1,
        ),
        "cash_flows": dict(
            id=7,
            occurred_on="2026-10-11",
            title="합성 출금",
            amount_value=-37,
            sort_order=1,
        ),
        "card_payment_batches": dict(id=11, usage_month="2026-09"),
        "card_payment_batch_items": dict(
            id=12, batch_id=11, entry_id=41, entry_payment_key="audit-payment"
        ),
        "card_payment_events": dict(
            id=13,
            batch_id=11,
            event_date="2026-10-11",
            event_type="immediate",
            total_amount=37,
            cash_flow_id=7,
        ),
        "card_payment_allocations": dict(
            id=14,
            payment_event_id=13,
            entry_payment_key="audit-payment",
            amount_value=37,
        ),
        "card_payment_deferrals": dict(
            entry_payment_key="audit-payment",
            from_payment_month="2026-10",
            target_payment_month="2026-11",
        ),
        "notification_candidate_registrations": dict(
            registration_key="audit-registration",
            target="ledger",
            target_id=41,
            request_fingerprint="independent-synthetic",
        ),
        "app_settings": dict(key="audit-setting", value="보존된 설정"),
        "app_labels": dict(key="audit-label", value="세대 0"),
    }
    for table, row in rows.items():
        insert(conn, table, row)
    for n in range(history):
        insert(
            conn,
            "ledger_entries",
            dict(
                id=1000 + n,
                book_section="archive",
                entry_kind="expense",
                entry_date="2026-08-17",
                title="합성 과거 " + str(n),
                amount_value=n + 1,
                sort_order=n + 2,
                payment_key="audit-history-" + str(n),
            ),
        )
    for k in ("scheduled_income", "cash_flow_balance", "card_limit"):
        conn.execute(
            "INSERT OR REPLACE INTO app_settings(key,value) VALUES (?,'0')", (k,)
        )
    for k in ("share_pin_hash", "share_pin_is_default"):
        conn.execute(
            "INSERT INTO app_settings(key,value) VALUES (?,'audit-sensitive-must-stay-private')",
            (k,),
        )
    for uid, token in ((1, TOKEN), (2, OTHER)):
        conn.execute(
            "INSERT INTO users(id,username,password_hash) VALUES (?,?,'synthetic-only')",
            (uid, "independent-" + str(uid)),
        )
        conn.execute(
            "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (?,?,'2027-01-01T00:00:00Z')",
            (uid, hashlib.sha256(token.encode()).hexdigest()),
        )


@pytest.fixture(scope="module")
def template():
    with RetentionSandbox() as db:
        with db.connect() as conn:
            seed(conn)
        db.install()
        db.bootstrap()
        yield db


@pytest.fixture
def db(template):
    with RetentionSandbox() as value:
        with (
            sqlite3.connect(template.path) as source,
            sqlite3.connect(value.path) as target,
        ):
            source.backup(target)
        value.install()
        yield value


def repository(db, clock=None, **kwargs):
    return RetentionRepository(
        db,
        clock=clock or (lambda: NOW),
        evaluation=lambda: Evaluation(date(2026, 10, 11), 540),
        **kwargs,
    )


def create(repo, credential=CRED, request_id=None):
    return repo.create(
        credential,
        guard=lambda: credential,
        request_id=request_id or str(uuid4()),
        protocol=1,
        base=None,
        inline_bytes=0,
    )


def mutate(db, n=1):
    with db.connect() as conn:
        conn.begin_capture()
        conn.execute(
            "UPDATE app_labels SET value=? WHERE key='audit-label'",
            ("독립 세대 " + str(n),),
        )
        metrics = conn.finalize()
        conn.commit()
        return metrics


def financial(db):
    with sqlite3.connect(db.path, timeout=2) as conn:
        conn.execute("BEGIN IMMEDIATE")
        result = {
            t: conn.execute("SELECT * FROM " + t + " ORDER BY " + PRIMARY[t]).fetchall()
            for t in TABLES
        }
        result["revision"] = conn.execute(
            "SELECT * FROM authoritative_state_revision"
        ).fetchall()
        conn.rollback()
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        return result


def raw_state(db):
    with sqlite3.connect(db.path) as conn:
        conn.row_factory = sqlite3.Row
        return {
            t: [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM "
                    + t
                    + (
                        " WHERE key NOT IN ('share_pin_hash','share_pin_is_default')"
                        if t == "app_settings"
                        else ""
                    )
                    + " ORDER BY "
                    + PRIMARY[t]
                )
            ]
            for t in TABLES
        }


def certificates(db):
    with sqlite3.connect(db.path) as conn:
        return {
            t: conn.execute("SELECT * FROM " + t + " ORDER BY 1").fetchall()
            for t in (
                "sync_commits",
                "sync_capture_commits",
                "sync_tx_fence",
                "sync_authority_fence",
            )
        }


def load(db):
    with sqlite3.connect(db.path) as conn:
        return {
            h: (kind, bytes(raw), json.loads(raw))
            for h, kind, raw in conn.execute("SELECT hash,kind,body FROM sync_objects")
        }


def typed_children(body):
    kind = body["kind"]
    if kind == "raw-root":
        assert [x["name"] for x in body["tables"]] == list(TABLES)
        return [
            (
                x["root"]["ref"],
                "snapshot-node" if x["root"]["height"] else "snapshot-leaf",
                x["name"],
                x["root"],
            )
            for x in body["tables"]
        ]
    if kind == "snapshot-node":
        return [
            (
                x["ref"],
                "snapshot-node" if x["height"] else "snapshot-leaf",
                body["table"],
                x,
            )
            for x in body["children"]
        ]
    if kind == "index-root":
        return [
            (
                body["facts"],
                "index-empty"
                if int(body["count"]) == 0
                else ("index-leaf", "index-node"),
                None,
                None,
            )
        ]
    if kind == "index-node":
        return [
            (body[s], ("index-leaf", "index-node"), None, None)
            for s in ("left", "right")
        ]
    assert kind in ("snapshot-leaf", "index-leaf", "index-empty", "hot", "control")
    return []


def oracle(db):
    """SQLite roots와 JSON/hash/typed graph를 직접 검증하며 production GC helper는 사용하지 않는다."""
    stored = load(db)
    with sqlite3.connect(db.path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM sync_current WHERE id=1").fetchone()
        cert = conn.execute(
            "SELECT * FROM sync_commits WHERE tx_id=?", (cur["tx_id"],)
        ).fetchone()
        assert (
            cert
            and cert["status"] == "complete"
            and cert["target_revision"] == cur["revision"]
        )
        assert (
            cur["raw_hash"] == cert["raw_hash"]
            and cur["index_hash"] == cert["index_hash"]
        )
        roots = [cur["raw_hash"], cur["index_hash"], cert["input_hash"]]
        for row in conn.execute("SELECT * FROM sync_observations"):
            target = json.loads(row["target"])
            lifecycle = conn.execute(
                "SELECT released FROM sync_observation_lifecycle WHERE id=?",
                (row["id"],),
            ).fetchone()
            assert lifecycle is not None
            pins = list(
                conn.execute(
                    "SELECT role,hash,active FROM sync_observation_pins WHERE observation_id=?",
                    (row["id"],),
                )
            )
            expected = {
                r: target[r + "_ref"]["hash"]
                for r in ("raw", "index", "hot", "control")
            }
            expected["input"] = row["input_hash"]
            assert {r[0]: r[1] for r in pins} == expected and len(pins) == 5
            assert all(r[2] == 1 - lifecycle[0] for r in pins)
            if not lifecycle[0]:
                roots += list(expected.values())
        roots += [
            r[0]
            for r in conn.execute(
                "SELECT hash FROM sync_retention_roots WHERE scope='explicit'"
            )
        ]
        recorded = set(conn.execute("SELECT parent,child FROM sync_object_edges"))
        recorded = {tuple(r) for r in recorded}
    edges = set()
    for h, (kind, raw, b) in stored.items():
        assert (
            b["kind"] == kind
            and c1(b) == raw
            and digest(kind, raw) == h
            and type(b["canon"]) is int
            and b["canon"] == 1
        )
        for field in ("server_id", "dataset_id", "epoch"):
            from uuid import UUID

            assert str(UUID(b["ns"][field], version=4)) == b["ns"][field]
        for child, kinds, table, desc in typed_children(b):
            ch, ck, cb = stored[child["hash"]]
            assert ch == cb["kind"] and len(ck) == int(child["bytes"])
            assert ch in kinds if isinstance(kinds, tuple) else ch == kinds
            assert cb["ns"] == b["ns"]
            if table:
                assert cb["table"] == table
                assert all(cb[k] == desc[k] for k in ("height", "count", "min", "max"))
            if kind == "index-node":
                prefix = b["prefix"] + ("0" if child == b["left"] else "1")
                cp = cb.get(
                    "prefix",
                    "".join(f"{x:08b}" for x in bytes.fromhex(cb.get("digest", ""))),
                )
                assert cp.startswith(prefix) and 0 < int(cb["count"]) < int(b["count"])
            edges.add((h, child["hash"]))
    assert recorded == edges
    reachable, todo = set(), list(roots)
    while todo:
        h = todo.pop()
        if h in reachable:
            continue
        assert h in stored
        reachable.add(h)
        todo.extend(child["hash"] for child, *_ in typed_children(stored[h][2]))
    row_retained = set()
    for h in reachable:
        b = stored[h][2]
        if b["kind"] == "snapshot-leaf":
            for row in b["rows"]:
                row_retained.add(
                    digest(
                        "row",
                        c1(
                            dict(
                                ns=b["ns"],
                                raw_schema=b["raw_schema"],
                                table=b["table"],
                                key=row["key"],
                                value=row["value"],
                            )
                        ),
                    )
                )
    with sqlite3.connect(db.path) as conn:
        cached = {
            h: bytes(raw) for h, raw in conn.execute("SELECT hash,body FROM sync_rows")
        }
    for h, raw in cached.items():
        assert c1(json.loads(raw)) == raw and digest("row", raw) == h
    return dict(
        stored=stored,
        roots=set(roots),
        reachable=reachable,
        candidates=set(stored) - reachable,
        row_candidates=set(cached) - row_retained,
        cache=cached,
        edges=edges,
    )


def assert_plan(db, gc=None):
    gc = gc or Collector(repository(db))
    expected = oracle(db)
    mark = gc.mark()
    assert mark.reachable == expected["reachable"]
    assert set(dict(mark.candidates)) == expected["candidates"]
    assert set(dict(mark.row_candidates)) == expected["row_candidates"]
    return gc, mark, expected


def facts_from_rows(ns, schema, data):
    out = {}
    refs = {
        "ledger_entries": [("source_planned_entry_id", "ledger_entries")],
        "monthly_panels": [("confirmed_cash_flow_id", "cash_flows")],
        "card_payment_events": [
            ("batch_id", "card_payment_batches"),
            ("cash_flow_id", "cash_flows"),
        ],
        "card_payment_batch_items": [
            ("batch_id", "card_payment_batches"),
            ("entry_id", "ledger_entries"),
        ],
        "card_payment_allocations": [
            ("payment_event_id", "card_payment_events"),
            ("entry_payment_key", "@ledger_payment_key"),
        ],
    }

    def add(k, v):
        raw = c1(k)
        assert raw not in out
        out[raw] = v

    for t, rows in data.items():
        for v in rows:
            k = key(v[PRIMARY[t]])
            rh = digest(
                "row", c1(dict(ns=ns, raw_schema=schema, table=t, key=k, value=v))
            )
            owner = [t, k]
            add(["pk", t, k], rh)

            def unique(domain, parts):
                add(["unique", domain, parts], owner)

            if t == "ledger_entries":
                if v["payment_key"] is not None:
                    unique("ledger_payment_key", [v["payment_key"]])
                if (
                    v["entry_kind"] == "expense"
                    and v["source_planned_entry_id"] is not None
                ):
                    unique(
                        "recurring_child",
                        [
                            key(v["source_planned_entry_id"]),
                            v["confirmed_month"],
                            v["confirmed_at"],
                        ],
                    )
                if v["entry_kind"] == "planned" or any(
                    v[f] is not None
                    for f in (
                        "source_planned_entry_id",
                        "confirmed_month",
                        "confirmed_at",
                    )
                ):
                    add(["context_reverse", "last_closed_month", t, k], rh)
            elif t == "monthly_panels" and v["panel_type"] == "fixed":
                add(["context_reverse", "last_closed_month", t, k], rh)
                if v["confirmed_cash_flow_id"] is not None:
                    unique("cash_owner", [key(v["confirmed_cash_flow_id"])])
            elif t == "card_payment_batch_items":
                unique("batch_pair", [key(v["batch_id"]), v["entry_payment_key"]])
                unique("batch_key", [v["entry_payment_key"]])
                unique("batch_entry", [key(v["entry_id"])])
            elif t == "card_payment_events":
                if v["idempotency_key"] is not None:
                    unique("event_idempotency", [v["idempotency_key"]])
                if v["cash_flow_id"] is not None:
                    unique("cash_owner", [key(v["cash_flow_id"])])
            elif t == "card_payment_allocations":
                unique(
                    "allocation_pair",
                    [key(v["payment_event_id"]), v["entry_payment_key"]],
                )
                add(
                    [
                        "allocation",
                        key(v["payment_event_id"]),
                        v["entry_payment_key"],
                        k,
                    ],
                    str(int(v["amount_value"])),
                )
            for field, target in refs.get(t, ()):
                if v[field] is not None:
                    add(["ref", t, k, field], [target, key(v[field])])
                    add(["reverse", target, key(v[field]), t, k, field], rh)
    for event in data["card_payment_events"]:
        allocations = [
            x
            for x in data["card_payment_allocations"]
            if x["payment_event_id"] == event["id"]
        ]
        add(
            ["aggregate", "event", key(event["id"])],
            [
                str(len(allocations)),
                str(sum(int(x["amount_value"]) for x in allocations)),
            ],
        )
    add(
        ["aggregate", "active_batch"],
        str(sum(v["status"] == "active" for v in data["card_payment_batches"])),
    )
    add(
        ["context", "last_closed_month"],
        next(
            (
                x["value"]
                for x in data["app_settings"]
                if x["key"] == "last_closed_month"
            ),
            None,
        ),
    )
    return out


def patricia(ns, schema, facts):
    common = dict(ns=ns, raw_schema=schema, canon=1, structural=1)
    groups = defaultdict(list)
    for k, v in facts.items():
        groups[digest("fact-key", k)].append(dict(key=json.loads(k), value=v))

    def build(items):
        if not items:
            return ref(dict(kind="index-empty", **common, count="0")), 0
        if len(items) == 1:
            h, values = items[0]
            return ref(
                dict(
                    kind="index-leaf",
                    **common,
                    digest=h,
                    count=str(len(values)),
                    facts=sorted(values, key=lambda x: c1(x["key"])),
                )
            ), len(values)
        bits = [f"{int(h, 16):0256b}" for h, _ in items]
        split = next(i for i in range(256) if bits[0][i] != bits[-1][i])
        pivot = next(i for i, b in enumerate(bits) if b[split] == "1")
        left, nl = build(items[:pivot])
        right, nr = build(items[pivot:])
        return ref(
            dict(
                kind="index-node",
                **common,
                prefix=bits[0][:split],
                left=left,
                right=right,
                count=str(nl + nr),
            )
        ), nl + nr

    top, count = build(sorted(groups.items()))
    return ref(dict(kind="index-root", **common, facts=top, count=str(count)))


def input_facts(data):
    totals = Counter()
    fenwick = defaultdict(int)
    for row in data["cash_flows"]:
        i = date.fromisoformat(row["occurred_on"]).toordinal()
        while i <= date.max.toordinal():
            fenwick[i] += int(row["amount_value"])
            i += i & -i
    for t in ("ledger_entries", "monthly_panels", "card_payment_batches"):
        field = {
            "ledger_entries": "entry_date",
            "monthly_panels": "month",
            "card_payment_batches": "usage_month",
        }[t]
        for v in data[t]:
            if v[field]:
                totals["policy_horizon", v[field][:7]] += 1
            if (
                t == "ledger_entries"
                and v["book_section"] == "archive"
                and v["entry_kind"] == "expense"
                and v["entry_date"]
            ):
                totals["closed_count", v["entry_date"][:7]] += 1
    result = {
        c1(["local-maintained-input", "cash_prefix", str(k)]): str(v)
        for k, v in fenwick.items()
    }
    result.update(
        {
            c1(["local-maintained-input", domain, k]): str(v)
            for (domain, k), v in totals.items()
        }
    )
    return result


def check_current(db):
    expected = oracle(db)
    data = raw_state(db)
    with sqlite3.connect(db.path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM sync_current WHERE id=1").fetchone()
        cert = conn.execute(
            "SELECT * FROM sync_commits WHERE tx_id=?", (cur["tx_id"],)
        ).fetchone()
        ns = json.loads(cur["namespace"])
        actual = {t: [] for t in TABLES}
        todo = [cur["raw_hash"]]
        while todo:
            b = expected["stored"][todo.pop()][2]
            if b["kind"] == "snapshot-leaf":
                actual[b["table"]] += [r["value"] for r in b["rows"]]
            else:
                todo += [r["hash"] for r, *_ in typed_children(b)]
        assert {t: sorted(map(c1, v)) for t, v in actual.items()} == {
            t: sorted(map(c1, v)) for t, v in data.items()
        }
        assert (
            patricia(
                ns, cur["raw_schema"], facts_from_rows(ns, cur["raw_schema"], data)
            )["hash"]
            == cur["index_hash"]
        )
        assert (
            patricia(ns, cur["raw_schema"], input_facts(data))["hash"]
            == cert["input_hash"]
        )
        assert (
            cur["revision"]
            == conn.execute(
                "SELECT revision FROM authoritative_state_revision"
            ).fetchone()[0]
        )
    return expected


def test_independent_oracle_and_historical_reclamation(db):
    repo = repository(db)
    old = create(repo)
    for n in range(1, 4):
        mutate(db, n)
    repo.release(old["observation_id"], CRED, guard=lambda: CRED)
    repo.maintain()
    before = financial(db)
    evidence = certificates(db)
    gc, mark, expected = assert_plan(db)
    assert expected["candidates"]
    result = gc.collect(apply=True, batch=7, max_batches=128)
    assert set(load(db)) == expected["reachable"]
    assert result["objects_deleted"] == len(expected["candidates"])
    assert result["rows_deleted"] == len(expected["row_candidates"])
    assert financial(db) == before and certificates(db) == evidence
    check_current(db)
    assert gc.collect(apply=True)["objects_deleted"] == 0
    mutate(db, 4)
    check_current(db)
    record(
        "historical_reclamation",
        candidates=len(expected["candidates"]),
        objects_deleted=result["objects_deleted"],
        cache_deleted=result["rows_deleted"],
        logical_bytes=result["logical_bytes_reclaimed"],
        certificate_rows=len(evidence["sync_commits"]),
        maximum_lock_ms=max(x["lock_ms"] for x in result["batches"]),
    )


@pytest.mark.parametrize("scenario", ["three_mutations", "epoch_bootstrap"])
def test_original_historical_certificate_root_blocker(db, scenario):
    for n in range(1, 4):
        mutate(db, n)
    if scenario == "epoch_bootstrap":
        db.bootstrap()
    expected = oracle(db)
    evidence = certificates(db)
    historical = set()
    # Certificate digest를 직접 읽어 historical-root 가정의 결과를 별도로 계산한다.
    with sqlite3.connect(db.path) as conn:
        pending = [
            h
            for row in conn.execute(
                "SELECT raw_hash,index_hash,input_hash FROM sync_commits"
            )
            for h in row
        ]
    while pending:
        h = pending.pop()
        if h not in historical:
            historical.add(h)
            pending.extend(
                edge[0]["hash"] for edge in typed_children(expected["stored"][h][2])
            )
    only_historical = historical - expected["reachable"]
    assert only_historical and only_historical <= expected["candidates"]
    before = financial(db)
    result = Collector(repository(db)).collect(apply=True, batch=1024, max_batches=64)
    assert not only_historical.intersection(load(db))
    assert certificates(db) == evidence and financial(db) == before
    check_current(db)
    record(
        "original_blocker_" + scenario,
        current_live_reachable=len(expected["reachable"]),
        all_certificate_reachable=len(historical),
        historical_only_reclaimed=len(only_historical),
        objects_deleted=result["objects_deleted"],
        certificate_evidence_unchanged=True,
    )


def request_body(paths, sizes=None):
    return dict(
        protocol=1,
        request_id=str(uuid4()),
        items=[
            dict(path=p, offset="0", length=(sizes[p[-1]] if sizes else 1))
            for p in paths
        ],
    )


async def asgi(
    app, path, body=None, token=TOKEN, method="POST", messages=None, send_hook=None
):
    messages = messages if messages is not None else []
    raw = c1(body) if body is not None else b""
    first = True

    async def receive():
        nonlocal first
        if first:
            first = False
            return dict(type="http.request", body=raw, more_body=False)
        await asyncio.Future()

    async def send(message):
        if send_hook:
            await send_hook(message)
        messages.append(dict(message))

    scope = dict(
        type="http",
        asgi={"version": "3.0"},
        http_version="1.1",
        method=method,
        scheme="http",
        path=path,
        raw_path=path.encode(),
        query_string=b"",
        root_path="",
        headers=[
            (b"content-type", b"application/json"),
            (b"authorization", ("Bearer " + token).encode()),
        ],
        client=("127.0.0.1", 1),
        server=("synthetic-audit", 80),
    )
    await app(scope, receive, send)
    return messages


def status(events):
    return next(m["status"] for m in events if m["type"] == "http.response.start")


def payload(events):
    return b"".join(
        m.get("body", b"") for m in events if m["type"] == "http.response.body"
    )


async def http_graph(app, manifest, expected):
    target = manifest["target"]
    without = {k: v for k, v in target.items() if k != "sync_root"}
    assert digest("view", c1(without)) == target["sync_root"]
    pending = [[target[r + "_ref"]["hash"]] for r in ("raw", "index", "hot", "control")]
    refs = {
        target[r + "_ref"]["hash"]: target[r + "_ref"]
        for r in ("raw", "index", "hot", "control")
    }
    received = {}
    queries = 0
    while pending:
        paths, pending = pending[:24], pending[24:]
        events = await asgi(
            app,
            URL + "/" + manifest["observation_id"] + "/objects",
            request_body(paths, {h: int(r["bytes"]) for h, r in refs.items()}),
        )
        assert status(events) == 200, payload(events)[:150]
        response = json.loads(payload(events))
        queries += 1
        assert response["observation_id"] == manifest["observation_id"]
        for path, chunk in zip(paths, response["chunks"]):
            raw = base64.b64decode(chunk["data_base64"], validate=True)
            b = json.loads(raw)
            h = path[-1]
            assert (
                c1(b) == raw
                and digest(b["kind"], raw) == h
                and len(raw) == int(refs[h]["bytes"])
            )
            assert "audit-sensitive-must-stay-private" not in raw.decode()
            if h in received:
                assert received[h] == b
                continue
            received[h] = b
            for child, *_ in typed_children(b):
                refs[child["hash"]] = child
                pending.append(path + [child["hash"]])
    rows = {t: [] for t in TABLES}
    facts = {}
    for b in received.values():
        if b["kind"] == "snapshot-leaf":
            rows[b["table"]] += [r["value"] for r in b["rows"]]
        elif b["kind"] == "index-leaf":
            for f in b["facts"]:
                assert c1(f["key"]) not in facts
                facts[c1(f["key"])] = f["value"]
    assert {t: sorted(map(c1, v)) for t, v in rows.items()} == {
        t: sorted(map(c1, v)) for t, v in expected.items()
    }
    direct = facts_from_rows(target["ns"], target["versions"]["raw_schema"], expected)
    assert facts == direct
    assert (
        patricia(target["ns"], target["versions"]["raw_schema"], facts)
        == target["index_ref"]
    )
    assert len(received[target["hot_ref"]["hash"]]["state"]) == 12
    return {
        "http_queries": queries,
        "received_objects": len(received),
        "tables": len(rows),
        "facts": len(facts),
        "patricia": "PASS",
    }


def test_post_gc_http_eleven_tables_old_and_current(db):
    repo = repository(db)
    old = create(repo)
    old_rows = raw_state(db)
    for n in (1, 2, 3):
        mutate(db, n)
    new = create(repo)
    new_rows = raw_state(db)
    before = financial(db)
    certs = certificates(db)
    gc, _, expected = assert_plan(db)
    assert expected["candidates"]
    result = gc.collect(apply=True, batch=1024)
    assert financial(db) == before and certificates(db) == certs
    assert set(load(db)) == expected["reachable"]
    app = http.create_app(repo)

    async def run():
        a = await http_graph(app, old, old_rows)
        b = await http_graph(app, new, new_rows)
        retry = await asgi(
            app,
            URL,
            dict(protocol=1, request_id=old["request_id"], base=None, inline_bytes=0),
        )
        assert status(retry) == 200 and payload(retry) == c1(old)
        with sqlite3.connect(db.path) as conn:
            internal = conn.execute(
                "SELECT input_hash FROM sync_observations WHERE id=?",
                (old["observation_id"],),
            ).fetchone()[0]
        invalid = await asgi(
            app,
            URL + "/" + old["observation_id"] + "/objects",
            request_body([[internal]]),
        )
        assert status(invalid) == 422
        wrong = await asgi(
            app,
            URL + "/" + old["observation_id"] + "/objects",
            request_body([[old["target"]["raw_ref"]["hash"]]]),
            token=OTHER,
        )
        assert status(wrong) == 403
        return a, b

    a, b = asyncio.run(run(), debug=True)
    check_current(db)
    assert (
        patricia(
            old["target"]["ns"],
            old["target"]["versions"]["raw_schema"],
            input_facts(old_rows),
        )["hash"]
        in oracle(db)["reachable"]
    )
    record(
        "post_gc_http",
        old=a,
        current=b,
        objects_deleted=result["objects_deleted"],
        all_eleven_tables=True,
        internal_proof_not_downloadable=True,
        cross_principal_rejected=True,
    )


@pytest.mark.parametrize(
    "stage",
    [
        "retired",
        "release_raw",
        "release_index",
        "release_input",
        "release_hot",
        "release_control",
        "before_commit",
        "after_commit",
    ],
)
def test_release_atomicity(db, stage):
    repo = repository(db)
    m = create(repo)
    before = financial(db)

    def fault(at, conn):
        if at == stage:
            raise RuntimeError("independent release fault")

    with pytest.raises(RuntimeError):
        repo.release(m["observation_id"], CRED, guard=lambda: CRED, fault=fault)
    with sqlite3.connect(db.path) as conn:
        observed = conn.execute(
            "SELECT status FROM sync_observations WHERE id=?", (m["observation_id"],)
        ).fetchone()[0]
        pins = [
            x[0]
            for x in conn.execute(
                "SELECT active FROM sync_observation_pins WHERE observation_id=?",
                (m["observation_id"],),
            )
        ]
        assert observed == "retired" and pins == (
            [0] * 5 if stage == "after_commit" else [1] * 5
        )
    assert_plan(db)
    assert financial(db) == before
    repo.release(m["observation_id"], CRED, guard=lambda: CRED)
    repo.release(m["observation_id"], CRED, guard=lambda: CRED)
    assert_plan(db)
    record(
        "release_" + stage,
        status=observed,
        pins_after_fault=pins,
        idempotent_retry=True,
    )


def test_release_concurrent_and_wrong_principal(db):
    repo = repository(db)
    m = create(repo)
    other = BundleCredential(hashlib.sha256(OTHER.encode()).hexdigest(), 2)
    with pytest.raises(ObservationError):
        repo.release(m["observation_id"], other, guard=lambda: other)
    with ThreadPoolExecutor(4) as pool:
        list(
            pool.map(
                lambda _: repo.release(m["observation_id"], CRED, guard=lambda: CRED),
                range(4),
            )
        )
    with sqlite3.connect(db.path) as conn:
        assert (
            conn.execute("SELECT sum(active) FROM sync_observation_pins").fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM sync_retention_roots WHERE scope='observation'"
            ).fetchone()[0]
            == 0
        )
        assert min(x[0] for x in conn.execute("SELECT pins FROM sync_gc_counts")) == 0
    assert_plan(db)
    record("concurrent_release", release_calls=4, active_pins=0, underflow=False)


@pytest.mark.parametrize("invalidation", ["expiry", "revoke", "inactive", "epoch"])
def test_retire_reclaim_replay_and_rollback(db, invalidation):
    clock = [NOW]
    repo = repository(db, clock=lambda: clock[0])
    m = create(repo)
    if invalidation == "expiry":
        clock[0] += timedelta(seconds=900)
    elif invalidation == "revoke":
        with sqlite3.connect(db.path) as conn:
            conn.execute(
                "DELETE FROM auth_sessions WHERE session_token_hash=?",
                (CRED.token_hash,),
            )
    elif invalidation == "inactive":
        with sqlite3.connect(db.path) as conn:
            conn.execute("UPDATE users SET is_active=0 WHERE id=1")
    else:
        db.bootstrap()
    result = repo.maintain()
    clock[0] = NOW
    if invalidation == "inactive":
        with sqlite3.connect(db.path) as conn:
            conn.execute("UPDATE users SET is_active=1 WHERE id=1")
    with sqlite3.connect(db.path) as conn:
        assert (
            conn.execute(
                "SELECT 1 FROM sync_observations WHERE id=?", (m["observation_id"],)
            ).fetchone()
            is None
        )
        replay = conn.execute(
            "SELECT count(*) FROM sync_observation_replays"
        ).fetchone()[0]
        assert replay == (1 if invalidation in ("expiry", "inactive") else 0)
    with pytest.raises(ObservationError):
        repo.lookup(m["observation_id"], CRED, guard=lambda: CRED)
    if invalidation in ("expiry", "inactive"):
        with pytest.raises(ObservationError, match="OBSERVATION_EXPIRED"):
            create(repo, request_id=m["request_id"])
    assert_plan(db)
    check_current(db)
    record(
        "retirement_" + invalidation,
        maintenance=result,
        replay_records=replay,
        resurrected=False,
    )


def test_quota_and_byte_budget_recovery(db):
    clock = [NOW]
    repo = repository(
        db,
        clock=lambda: clock[0],
        limits=Limits(
            observations_per_principal=2, total_records=2, total_metadata_bytes=120000
        ),
    )
    counts = []
    for wave in range(5):
        for _ in range(2):
            create(repo)
        with pytest.raises(ObservationError, match="LEASE_LIMIT"):
            create(repo)
        clock[0] += timedelta(seconds=900)
        result = repo.maintain(limit=2)
        with sqlite3.connect(db.path) as conn:
            used = conn.execute(
                "SELECT used_bytes FROM sync_observation_budget"
            ).fetchone()[0]
            rows = conn.execute("SELECT count(*) FROM sync_observations").fetchone()[0]
            replay = conn.execute(
                "SELECT count(*) FROM sync_observation_replays"
            ).fetchone()[0]
            assert rows == 0 and replay == 2 * (wave + 1) and used == 512 * replay
            counts.append(
                dict(
                    wave=wave,
                    used_bytes=used,
                    replay=replay,
                    reclaimed=result["metadata_reclaimed"],
                )
            )
        assert_plan(db)
    record(
        "quota_budget_cycles",
        cycles=counts,
        default_limits=dict(
            lease_seconds=Limits().lease_seconds,
            per_principal=Limits().observations_per_principal,
            records=Limits().total_records,
            bytes=Limits().total_metadata_bytes,
        ),
    )


@pytest.mark.parametrize(
    "change", ["writer", "observation", "release", "epoch", "explicit"]
)
def test_stale_mark_rejects_every_publication(db, change):
    repo = repository(db)
    m = create(repo)
    mutate(db)
    gc, mark, _ = assert_plan(db)
    if change == "writer":
        mutate(db, 2)
    elif change == "observation":
        create(repo)
    elif change == "release":
        repo.release(m["observation_id"], CRED, guard=lambda: CRED)
    elif change == "epoch":
        db.bootstrap()
    else:
        gc.protect(str(uuid4()), {"raw": m["target"]["raw_ref"]})
    before = load(db)
    with pytest.raises(CanonicalError, match="STALE_MARK"):
        gc.sweep(mark)
    assert load(db) == before
    check_current(db)
    record("stale_" + change, deleted=0, stale_rejected=True)


def test_two_collectors_and_batch_publication(db):
    repo = repository(db)
    for n in (1, 2, 3):
        mutate(db, n)
    one, two = Collector(repo), Collector(repo)
    plan1, plan2 = one.mark(), two.mark()
    result, following = one.sweep(plan1, batch=1)
    assert result["objects_deleted"] == 1
    with pytest.raises(CanonicalError, match="STALE_MARK"):
        two.sweep(plan2)
    mutate(db, 4)
    before = load(db)
    with pytest.raises(CanonicalError, match="STALE_MARK"):
        one.sweep(following)
    assert load(db) == before
    check_current(db)
    record(
        "two_gc_and_between_batch_writer",
        first_batch_deleted=1,
        second_gc_stale=True,
        between_batch_writer_stale=True,
    )


def test_uncommitted_writer_serializes_sweep(db):
    repo = repository(db)
    mutate(db)
    gc = Collector(repo)
    plan = gc.mark()
    with db.connect() as writer:
        writer.begin_capture()
        writer.execute(
            "UPDATE app_labels SET value='uncommitted' WHERE key='audit-label'"
        )
        writer.finalize()
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            gc.sweep(plan)
        writer.commit()
    with pytest.raises(CanonicalError, match="STALE_MARK"):
        gc.sweep(plan)
    check_current(db)
    record("uncommitted_writer", blocked_before_commit=True, stale_after_commit=True)


@pytest.mark.parametrize("what", ["writer", "observation", "epoch"])
def test_mark_snapshot_can_overlap_publication(db, what):
    repo = repository(db)
    mutate(db)
    gc = Collector(repo)
    done = []

    def fault(stage, conn):
        if stage == "marked":

            def publish():
                if what == "writer":
                    mutate(db, 2)
                elif what == "observation":
                    create(repo)
                else:
                    db.bootstrap()
                done.append(True)

            with ThreadPoolExecutor(1) as pool:
                pool.submit(publish).result(timeout=15)

    mark = gc.mark(fault=fault)
    assert done == [True]
    before = load(db)
    with pytest.raises(CanonicalError, match="STALE_MARK"):
        gc.sweep(mark)
    assert load(db) == before
    check_current(db)
    record(
        "snapshot_overlap_" + what,
        publication_committed_during_mark=True,
        stale_rejected=True,
    )


CRASHES = [
    "retire_before",
    "retire_after",
    "release_before",
    "release_after",
    "marked",
    "batch_before",
    "batch_after",
    "metadata_before",
    "metadata_after",
    "epoch_before",
    "epoch_after",
]


@pytest.mark.parametrize("boundary", CRASHES)
def test_independent_sigkill_boundaries(db, boundary):
    repo = repository(db)
    m = create(repo)
    mutate(db)
    before = financial(db)
    evidence = certificates(db)
    before_objects = set(load(db))
    if (
        boundary.startswith("metadata")
        or boundary.startswith("batch")
        or boundary == "marked"
    ):
        repo.release(m["observation_id"], CRED, guard=lambda: CRED)

    def child():
        r = repository(db)

        def kill():
            os.kill(os.getpid(), signal.SIGKILL)

        if boundary.startswith("release"):
            at = "before_commit" if boundary.endswith("before") else "after_commit"
            r.release(
                m["observation_id"],
                CRED,
                guard=lambda: CRED,
                fault=lambda stage, conn: kill() if stage == at else None,
            )
        elif boundary.startswith("retire"):
            real = RetentionConnection.commit

            def commit(conn):
                if boundary.endswith("before"):
                    kill()
                real(conn)
                kill()

            with patch.object(RetentionConnection, "commit", commit):
                if boundary.startswith("retire"):
                    r = repository(db, clock=lambda: NOW + timedelta(seconds=900))
                    r.lookup(m["observation_id"], CRED, guard=lambda: CRED)
                else:
                    r.release(m["observation_id"], CRED, guard=lambda: CRED)
        elif boundary == "marked":
            Collector(r).mark(
                fault=lambda stage, conn: kill() if stage == "marked" else None
            )
        elif boundary.startswith("batch"):
            gc = Collector(r)
            plan = gc.mark()
            at = "before_commit" if boundary.endswith("before") else "after_commit"
            gc.sweep(
                plan, batch=2, fault=lambda stage, conn: kill() if stage == at else None
            )
        elif boundary.startswith("metadata"):
            at = "reclaimed" if boundary.endswith("before") else "after_commit"
            r.maintain(fault=lambda stage, conn: kill() if stage == at else None)
        else:
            if boundary.endswith("before"):
                real = RetentionConnection._epoch_bootstrapped

                def boot(conn, namespace):
                    real(conn, namespace)
                    kill()

                with patch.object(RetentionConnection, "_epoch_bootstrapped", boot):
                    db.bootstrap()
            else:
                db.bootstrap()
                kill()
        os._exit(99)

    process = multiprocessing.get_context("fork").Process(target=child)
    process.start()
    process.join(30)
    if process.is_alive():
        process.kill()
        process.join()
        pytest.fail("bounded synthetic crash child timeout")
    assert process.exitcode == -signal.SIGKILL
    assert financial(db) == before
    after_evidence = certificates(db)
    if boundary == "epoch_after":
        assert len(after_evidence["sync_commits"]) == len(evidence["sync_commits"]) + 1
        assert all(
            r in after_evidence["sync_commits"] for r in evidence["sync_commits"]
        )
    else:
        assert after_evidence == evidence
    with sqlite3.connect(db.path) as conn:
        row = conn.execute(
            "SELECT status FROM sync_observations WHERE id=?", (m["observation_id"],)
        ).fetchone()
        pins = conn.execute(
            "SELECT coalesce(sum(active),0) FROM sync_observation_pins WHERE observation_id=?",
            (m["observation_id"],),
        ).fetchone()[0]
        if boundary == "retire_before":
            assert row[0] == "available" and pins == 5
        elif boundary == "retire_after":
            assert row[0] == "retired" and pins == 5
        elif boundary == "release_before":
            assert row[0] == "available" and pins == 5
        elif boundary in ("release_after", "epoch_after"):
            assert row[0] == "retired" and pins == 0
        elif boundary == "metadata_before":
            assert row[0] == "retired" and pins == 0
        elif boundary == "metadata_after":
            assert row is None and pins == 0
    after_objects = set(load(db))
    assert after_objects <= before_objects if boundary != "epoch_after" else True
    check_current(db)
    assert_plan(db)
    if boundary.startswith("batch"):
        assert len(before_objects - after_objects) == (
            0 if boundary.endswith("before") else 2
        )
    # 별도 fresh process가 실제 persisted current를 독립 재구성한다.
    reopened = multiprocessing.get_context("fork").Process(
        target=lambda: check_current(db)
    )
    reopened.start()
    reopened.join(30)
    assert reopened.exitcode == 0
    Collector(repo).collect(apply=True, batch=1024)
    check_current(db)
    record(
        "sigkill_" + boundary,
        signal="SIGKILL",
        current_complete=True,
        financial_unchanged=True,
        pins_after_restart=pins,
        objects_removed=len(before_objects - after_objects),
        new_process_reconstruction=True,
    )


@pytest.mark.parametrize("when", ["before", "after"])
def test_historical_fk_retirement_sigkill(when):
    from isolated_sync.observation_schema import ObservationSandbox

    with RetentionSandbox() as db:
        with db.connect() as conn:
            seed(conn, history=3)
        ObservationSandbox.install(db)
        db.bootstrap()
        before = financial(db)
        certs = certificates(db)

        def child():
            def fault(stage, conn):
                if stage == "migration" and when == "before":
                    os.kill(os.getpid(), signal.SIGKILL)

            db.install(fault=fault)
            os.kill(os.getpid(), signal.SIGKILL)

        process = multiprocessing.get_context("fork").Process(target=child)
        process.start()
        process.join(30)
        assert process.exitcode == -signal.SIGKILL
        with sqlite3.connect(db.path) as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            assert version == (1000004 if when == "before" else 1000005)
            has_object_fk = any(
                r[2] == "sync_objects"
                for r in conn.execute("PRAGMA foreign_key_list(sync_commits)")
            )
            assert has_object_fk == (when == "before")
        assert financial(db) == before and certificates(db) == certs
        db.install()
        check_current(db)
        assert_plan(db)
        record(
            "sigkill_historical_fk_" + when,
            persisted_version=version,
            certificate_evidence_unchanged=True,
            current_complete=True,
        )


@pytest.mark.parametrize(
    "corruption",
    [
        "object_body",
        "canon",
        "raw_schema",
        "namespace",
        "kind",
        "edge",
        "incoming",
        "pins_count",
        "budget",
        "pin_hash",
        "lifecycle",
        "current_certificate",
        "root_missing",
        "schema_unknown",
        "row_cache",
    ],
)
def test_independent_corruption_fail_closed(db, corruption):
    repo = repository(db)
    create(repo)
    mutate(db)
    with sqlite3.connect(db.path) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        if corruption in ("object_body", "canon", "raw_schema", "namespace", "kind"):
            h, raw = conn.execute(
                "SELECT hash,body FROM sync_objects WHERE kind='index-leaf' LIMIT 1"
            ).fetchone()
            b = json.loads(raw)
            if corruption == "object_body":
                changed = b"{}"
            else:
                if corruption == "namespace":
                    b["ns"]["dataset_id"] = str(uuid4())
                else:
                    b[
                        {"canon": "canon", "raw_schema": "raw_schema", "kind": "kind"}[
                            corruption
                        ]
                    ] = {"canon": 2, "raw_schema": "f" * 64, "kind": "index-empty"}[
                        corruption
                    ]
                changed = c1(b)
            conn.execute("UPDATE sync_objects SET body=? WHERE hash=?", (changed, h))
        elif corruption == "edge":
            conn.execute(
                "UPDATE sync_object_edges SET child=? WHERE rowid=(SELECT min(rowid) FROM sync_object_edges)",
                ("d" * 64,),
            )
        elif corruption in ("incoming", "pins_count"):
            field = "incoming" if corruption == "incoming" else "pins"
            conn.execute(
                "UPDATE sync_gc_counts SET "
                + field
                + "="
                + field
                + "+1 WHERE rowid=(SELECT min(rowid) FROM sync_gc_counts)"
            )
        elif corruption == "budget":
            conn.execute("UPDATE sync_observation_budget SET used_bytes=used_bytes+1")
        elif corruption == "pin_hash":
            conn.execute(
                "UPDATE sync_observation_pins SET hash=? WHERE role='input'",
                ("d" * 64,),
            )
        elif corruption == "lifecycle":
            conn.execute("UPDATE sync_observation_lifecycle SET released=1")
        elif corruption == "current_certificate":
            conn.execute(
                "UPDATE sync_commits SET input_hash=? WHERE tx_id=(SELECT tx_id FROM sync_current)",
                ("d" * 64,),
            )
        elif corruption == "root_missing":
            conn.execute(
                "DELETE FROM sync_retention_roots WHERE scope='current' AND role='input'"
            )
        elif corruption == "schema_unknown":
            conn.execute("CREATE TABLE sync_unapproved(id INTEGER)")
        else:
            conn.execute(
                "UPDATE sync_rows SET body=? WHERE rowid=(SELECT min(rowid) FROM sync_rows)",
                (b"{}",),
            )
    before = load(db)
    with pytest.raises(
        (CanonicalError, ObservationError, sqlite3.DatabaseError, KeyError, TypeError)
    ) as error:
        Collector(repo).collect(apply=True)
    assert load(db) == before
    record(
        "corruption_" + corruption,
        deletion_count=0,
        error_type=type(error.value).__name__,
        error_code=str(error.value),
    )


@pytest.mark.parametrize(
    "mode",
    [
        "wrong_path",
        "symlink",
        "replaced_inode",
        "ownership_marker",
        "attached_database",
        "old_version",
    ],
)
def test_gc_admission_rejections(db, mode, tmp_path):
    repo = repository(db)
    gc = Collector(repo)
    original = db.path
    if mode == "attached_database":
        with db.connect() as conn:
            with pytest.raises(sqlite3.DatabaseError):
                conn.execute(
                    "ATTACH DATABASE ? AS foreign_db",
                    (str(tmp_path / "attached.sqlite"),),
                )
        record("admission_" + mode, rejected=True)
        return
    if mode == "old_version":
        with sqlite3.connect(db.path) as conn:
            conn.execute("PRAGMA user_version=1000004")
        with pytest.raises(CanonicalError):
            gc.collect(apply=True)
        record("admission_" + mode, rejected=True)
        return
    if mode == "ownership_marker":
        with patch.object(db, "_owned_file", (-1, -1)):
            with pytest.raises(CanonicalError, match="OWNERSHIP"):
                gc.collect(apply=True)
    elif mode == "wrong_path":
        dest = tmp_path / "external.sqlite"
        with sqlite3.connect(original) as source, sqlite3.connect(dest) as target:
            source.backup(target)
        with patch.object(type(db), "path", property(lambda self: dest)):
            with pytest.raises(CanonicalError, match="OWNERSHIP"):
                gc.collect(apply=True)
    else:
        saved = original.with_name("saved.sqlite")
        original.rename(saved)
        try:
            if mode == "symlink":
                original.symlink_to(saved)
            else:
                with (
                    sqlite3.connect(saved) as source,
                    sqlite3.connect(original) as target,
                ):
                    source.backup(target)
            with pytest.raises(CanonicalError, match="OWNERSHIP"):
                gc.collect(apply=True)
        finally:
            original.unlink()
            saved.rename(original)
    record("admission_" + mode, rejected=True)


def test_writer_reuses_stale_candidate_hash(db):
    mutate(db, 1)
    with sqlite3.connect(db.path) as conn:
        old = conn.execute("SELECT raw_hash FROM sync_current").fetchone()[0]
    mutate(db, 2)
    gc, plan, _ = assert_plan(db)
    assert old in dict(plan.candidates)
    mutate(db, 1)
    with sqlite3.connect(db.path) as conn:
        assert conn.execute("SELECT raw_hash FROM sync_current").fetchone()[0] == old
    with pytest.raises(CanonicalError, match="STALE_MARK"):
        gc.sweep(plan)
    assert old in load(db)
    check_current(db)
    record(
        "writer_reused_candidate_hash",
        stale_rejected=True,
        reused_current_preserved=True,
    )


def test_shared_principal_and_explicit_old_roots(db):
    repo = repository(db)
    one = create(repo)
    other = BundleCredential(hashlib.sha256(OTHER.encode()).hexdigest(), 2)
    two = create(repo, credential=other)
    assert one["target"]["raw_ref"] == two["target"]["raw_ref"]
    mutate(db, 1)
    gc = Collector(repo)
    pid = str(uuid4())
    gc.protect(pid, {"raw": one["target"]["raw_ref"]})
    repo.release(one["observation_id"], CRED, guard=lambda: CRED)
    gc.collect(apply=True, batch=1024)
    assert repo.lookup(two["observation_id"], other, guard=lambda: other) == two
    app = http.create_app(repo)
    path = URL + "/" + two["observation_id"] + "/objects"
    body = request_body([[two["target"]["raw_ref"]["hash"]]])
    assert status(asyncio.run(asgi(app, path, body, token=OTHER))) == 200
    assert status(asyncio.run(asgi(app, path, body))) == 403
    repo.release(two["observation_id"], other, guard=lambda: other)
    repo.maintain()
    gc.collect(apply=True, batch=1024)
    assert one["target"]["raw_ref"]["hash"] in load(db)
    gc.unprotect(pid)
    gc.collect(apply=True, batch=1024)
    assert one["target"]["raw_ref"]["hash"] not in load(db)
    check_current(db)
    record(
        "shared_principal_explicit",
        cross_principal_transfer_rejected=True,
        explicit_root_preserved=True,
        deleted_only_after_unprotect=True,
    )


class NativeCounter:
    def __init__(self):
        self.lock = Lock()
        self.running = self.maximum = self.started = self.exited = 0
        self.entered = Event()

    def wrap(self, fn):
        def call(*args, **kwargs):
            with self.lock:
                self.running += 1
                self.started += 1
                self.maximum = max(self.maximum, self.running)
                assert self.running <= 2
                self.entered.set()
            try:
                return fn(*args, **kwargs)
            finally:
                with self.lock:
                    self.running -= 1
                    self.exited += 1

        return call


async def drain(adapter, counter):
    while adapter.workers._tasks:
        await asyncio.gather(*list(adapter.workers._tasks), return_exceptions=True)
        await asyncio.sleep(0)
    assert counter.running == 0 and counter.started == counter.exited
    assert adapter.workers.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)
    slots = adapter.workers.slots
    available = [slots.acquire(False) for _ in range(3)]
    assert available == [True, True, False]
    for value in available:
        if value:
            slots.release()


@pytest.mark.parametrize(
    "stage", ["authenticated", "objects_prepared", "serialized", "terminal"]
)
def test_native_cancel_transfer_gc_boundary(db, stage):
    repo = repository(db)
    m = create(repo)
    mutate(db)
    before = financial(db)
    gc = Collector(repo)
    plan = gc.mark()

    async def run():
        loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        release = Event()
        tickets = []
        counter = NativeCounter()
        adapter = http.Adapter(repo, http.TransferLimits())
        adapter.prepare = counter.wrap(adapter.prepare)
        adapter.terminal = counter.wrap(adapter.terminal)

        def fault(at, ticket):
            if at == stage:
                tickets.append(ticket)
                loop.call_soon_threadsafe(entered.set)
                assert release.wait(20)

        adapter.fault = fault
        with patch.object(http, "Adapter", return_value=adapter):
            app = http.create_app(repo)
        events = []
        path = URL + "/" + m["observation_id"] + "/objects"
        body = request_body([[m["target"]["raw_ref"]["hash"]]])
        task = asyncio.create_task(asgi(app, path, body, messages=events))
        try:
            async with asyncio.timeout(20):
                await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert counter.running == 1 and adapter.workers.snapshot()["leases"] == 1
            assert tickets[0].cancelled.is_set()
            if stage == "objects_prepared":
                with pytest.raises(sqlite3.OperationalError, match="locked"):
                    await asyncio.to_thread(gc.sweep, plan)
                assert plan.reachable <= set(load(db))
            else:
                # 준비 전후의 무 DB 의존 구간에는 GC가 안전하게 진행될 수 있다.
                await asyncio.to_thread(gc.collect, apply=True, batch=1024)
        finally:
            release.set()
            await drain(adapter, counter)
        assert events == []
        good = await asgi(app, path, body)
        assert status(good) == 200
        await drain(adapter, counter)
        return counter.maximum

    maximum = asyncio.run(run(), debug=True)
    assert financial(db) == before
    check_current(db)
    record(
        "transfer_cancel_" + stage,
        maximum_native=maximum,
        protected_asgi_events=0,
        permit_available=2,
        current_complete=True,
    )


def test_cancelled_two_natives_do_not_admit_third_during_gc(db):
    repo = repository(db)
    m = create(repo)
    mutate(db)
    gc = Collector(repo)

    async def run():
        loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        release = Event()
        tickets = []
        counter = NativeCounter()
        adapter = http.Adapter(repo, http.TransferLimits())
        adapter.prepare = counter.wrap(adapter.prepare)
        adapter.terminal = counter.wrap(adapter.terminal)

        def fault(stage, ticket):
            if stage == "authenticated":
                tickets.append(ticket)
                if len(tickets) == 2:
                    loop.call_soon_threadsafe(entered.set)
                assert release.wait(20)

        adapter.fault = fault
        with patch.object(http, "Adapter", return_value=adapter):
            app = http.create_app(repo)
        path = URL + "/" + m["observation_id"] + "/objects"
        body = request_body([[m["target"]["raw_ref"]["hash"]]])
        events = [[], []]
        tasks = [asyncio.create_task(asgi(app, path, body, messages=e)) for e in events]
        try:
            async with asyncio.timeout(20):
                await entered.wait()
            for t in tasks:
                t.cancel()
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            assert counter.running == 2 and adapter.workers.snapshot()["leases"] == 2
            over = await asyncio.gather(*(asgi(app, path, body) for _ in range(6)))
            assert all(status(e) == 503 for e in over)
            await asyncio.to_thread(gc.collect, apply=True, batch=1024)
            assert counter.running == 2 and all(t.cancelled.is_set() for t in tickets)
        finally:
            release.set()
            await drain(adapter, counter)
        assert events == [[], []]
        adapter.fault = None
        assert status(await asgi(app, path, body)) == 200
        await drain(adapter, counter)
        return counter.maximum

    maximum = asyncio.run(run(), debug=True)
    check_current(db)
    record(
        "two_cancelled_natives_gc",
        maximum_native=maximum,
        overflow_requests=6,
        overflow_status=503,
        protected_asgi_events=0,
        permits_restored=2,
    )


def test_materialized_network_cancel_needs_no_source_lock(db):
    repo = repository(db)
    old = create(repo)
    mutate(db)
    gc = Collector(repo)
    before = financial(db)

    async def run():
        app = http.create_app(repo)
        entered = asyncio.Event()
        hold = asyncio.Event()
        events = []

        async def sending(message):
            if message["type"] == "http.response.body":
                entered.set()
                await hold.wait()

        task = asyncio.create_task(
            asgi(
                app,
                URL + "/" + old["observation_id"] + "/objects",
                request_body([[old["target"]["raw_ref"]["hash"]]]),
                messages=events,
                send_hook=sending,
            )
        )
        async with asyncio.timeout(20):
            await entered.wait()
        await asyncio.to_thread(
            repo.release, old["observation_id"], CRED, guard=lambda: CRED
        )
        result = await asyncio.to_thread(gc.collect, apply=True, batch=1024)
        assert old["target"]["raw_ref"]["hash"] not in load(db)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert [e["type"] for e in events] == ["http.response.start"]
        return result

    result = asyncio.run(run(), debug=True)
    assert financial(db) == before
    check_current(db)
    record(
        "network_materialized_cancel",
        objects_deleted=result["objects_deleted"],
        response_start_before_cancel=1,
        protected_body_after_cancel=0,
        source_object_reclaimed_after_materialization=True,
    )


def test_queued_request_cancel_then_gc_cannot_start_late(db):
    import anyio.to_thread

    repo = repository(db)
    m = create(repo)
    mutate(db)
    gc = Collector(repo)

    async def run():
        adapter = http.Adapter(repo, http.TransferLimits())
        counter = NativeCounter()
        adapter.prepare = counter.wrap(adapter.prepare)
        with patch.object(http, "Adapter", return_value=adapter):
            app = http.create_app(repo)
        limiter = anyio.to_thread.current_default_thread_limiter()
        original = limiter.total_tokens
        limiter.total_tokens = 1
        await limiter.acquire()
        events = []
        task = asyncio.create_task(
            asgi(
                app,
                URL + "/" + m["observation_id"] + "/objects",
                request_body([[m["target"]["raw_ref"]["hash"]]]),
                messages=events,
            )
        )
        try:
            async with asyncio.timeout(20):
                while limiter.statistics().tasks_waiting != 1:
                    await asyncio.sleep(0)
            assert adapter.workers.snapshot()["leases"] == 1 and counter.started == 0
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            await drain(adapter, counter)
            await asyncio.to_thread(gc.collect, apply=True, batch=1024)
        finally:
            limiter.release()
            limiter.total_tokens = original
        await asyncio.sleep(0)
        assert counter.started == 0 and events == []
        assert (
            status(
                await asgi(
                    app,
                    URL + "/" + m["observation_id"] + "/objects",
                    request_body([[m["target"]["raw_ref"]["hash"]]]),
                )
            )
            == 200
        )
        await drain(adapter, counter)

    asyncio.run(run(), debug=True)
    check_current(db)
    record(
        "queued_cancel_gc",
        queued_native_starts=0,
        permits_restored=2,
        protected_asgi_events=0,
    )


def test_native_exception_releases_database_and_gc_capacity(db):
    repo = repository(db)
    m = create(repo)
    mutate(db)

    async def run():
        adapter = http.Adapter(repo, http.TransferLimits())
        counter = NativeCounter()
        adapter.prepare = counter.wrap(adapter.prepare)

        def fault(stage, ticket):
            if stage == "objects_prepared":
                raise RuntimeError("independent synthetic materialization fault")

        adapter.fault = fault
        with patch.object(http, "Adapter", return_value=adapter):
            app = http.create_app(repo)
        events = []
        await asgi(
            app,
            URL + "/" + m["observation_id"] + "/objects",
            request_body([[m["target"]["raw_ref"]["hash"]]]),
            messages=events,
        )
        await drain(adapter, counter)
        assert status(events) == 500 and b"STORAGE_FAILED" in b"".join(
            e.get("body", b"") for e in events
        )
        await asyncio.to_thread(Collector(repo).collect, apply=True, batch=1024)
        adapter.fault = None
        assert (
            status(
                await asgi(
                    app,
                    URL + "/" + m["observation_id"] + "/objects",
                    request_body([[m["target"]["raw_ref"]["hash"]]]),
                )
            )
            == 200
        )
        await drain(adapter, counter)

    before = financial(db)
    asyncio.run(run(), debug=True)
    assert financial(db) == before
    check_current(db)
    record(
        "native_exception_gc",
        permits_restored=2,
        write_lock_leaked=False,
        protected_asgi_events=0,
    )


def test_shutdown_active_native_still_owns_permit_during_gc(db):
    repo = repository(db)
    m = create(repo)
    mutate(db)

    async def run():
        loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        release = Event()
        counter = NativeCounter()
        adapter = http.Adapter(repo, http.TransferLimits())
        adapter.prepare = counter.wrap(adapter.prepare)
        tickets = []

        def fault(stage, ticket):
            if stage == "authenticated":
                tickets.append(ticket)
                loop.call_soon_threadsafe(entered.set)
                assert release.wait(20)

        adapter.fault = fault
        with patch.object(http, "Adapter", return_value=adapter):
            app = http.create_app(repo)
        path = URL + "/" + m["observation_id"] + "/objects"
        body = request_body([[m["target"]["raw_ref"]["hash"]]])
        events = []
        task = asyncio.create_task(asgi(app, path, body, messages=events))
        try:
            async with asyncio.timeout(20):
                await entered.wait()
            adapter.workers.shutdown()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert (
                counter.running == 1
                and adapter.workers.snapshot()["leases"] == 1
                and tickets[0].cancelled.is_set()
            )
            assert status(await asgi(app, path, body)) == 503
            await asyncio.to_thread(Collector(repo).collect, apply=True, batch=1024)
        finally:
            release.set()
            await drain(adapter, counter)
        assert events == [] and adapter.workers.acquire() is None

    asyncio.run(run(), debug=True)
    check_current(db)
    record(
        "shutdown_native_gc",
        maximum_native=1,
        admission_closed=True,
        permits_restored=2,
        protected_asgi_events=0,
    )


def test_D3C_A01_open_inode_race_must_not_delete_other_database(db):
    """회귀 기대값은 안전 거부다. 감사 대상 revision에서는 실제로 실패해야 한다."""
    from isolated_sync import retention_schema

    for n in (1, 2, 3):
        mutate(db, n)
    gc = Collector(repository(db))
    plan = gc.mark()
    original = db.path
    saved = original.with_name("audit-original-held.sqlite")
    real_connect = sqlite3.connect
    armed = [True]
    with RetentionSandbox() as other:
        with real_connect(original) as source, real_connect(other.path) as target:
            source.backup(target)
        other.install()
        before = load(other)

        def interleaving(path, *args, **kwargs):
            if Path(path) == original and armed[0]:
                armed[0] = False
                # 마지막 검사 뒤 실제 SQLite open 직전 파일 교체를 확정한다.
                original.rename(saved)
                original.symlink_to(other.path)
            return real_connect(path, *args, **kwargs)

        try:
            with patch.object(retention_schema.sqlite3, "connect", interleaving):
                with pytest.raises(CanonicalError, match="OWNERSHIP"):
                    gc.sweep(plan, batch=1)
            after = load(other)
            evidence = dict(
                finding="D3C-A01",
                result="CONFIRMED FAILURE",
                unowned_objects_deleted=sorted(set(before) - set(after)),
                deletion_committed_before_ownership_error=True,
                production_access="NONE",
            )
            (OUT / "D3C-A01.json").write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2)
            )
            assert after == before, (
                "D3C-A01: 다른 inode의 synthetic DB 객체가 ownership 거부 전에 COMMIT 삭제됨"
            )
        finally:
            if original.is_symlink():
                original.unlink()
            if saved.exists():
                saved.rename(original)

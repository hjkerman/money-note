"""제품 graph/facts helper를 호출하지 않는 C1, typed closure, F(raw), Patricia oracle."""

import base64
from collections import defaultdict
from contextlib import closing
import hashlib
import json
import sqlite3

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


def c1(v):
    return json.dumps(
        v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def h(kind, raw):
    return hashlib.sha256(
        b"money-note.sync.v1/" + kind.encode() + b"\0" + raw
    ).hexdigest()


def key(v):
    return ["t" if isinstance(v, str) else "i", str(v)]


def edges(body):
    kind = body["kind"]
    if kind == "raw-root":
        assert [t["name"] for t in body["tables"]] == list(TABLES)
        return [
            (
                t["root"]["ref"],
                {"snapshot-leaf" if t["root"]["height"] == 0 else "snapshot-node"},
                t["name"],
                t["root"],
            )
            for t in body["tables"]
        ]
    if kind == "snapshot-node":
        return [
            (
                d["ref"],
                {"snapshot-leaf" if d["height"] == 0 else "snapshot-node"},
                body["table"],
                d,
            )
            for d in body["children"]
        ]
    if kind == "index-root":
        return [
            (body["facts"], {"index-empty", "index-leaf", "index-node"}, None, None)
        ]
    if kind == "index-node":
        return [
            (body[s], {"index-leaf", "index-node"}, None, None)
            for s in ("left", "right")
        ]
    assert kind in {"snapshot-leaf", "index-empty", "index-leaf", "hot", "control"}
    return []


def graph(fixture):
    objects = {
        o["ref"]["hash"]: base64.b64decode(o["data_base64"]) for o in fixture["objects"]
    }
    target = fixture["manifest"]["target"]
    unhashed = {k: v for k, v in target.items() if k != "sync_root"}
    assert h("view", c1(unhashed)) == target["sync_root"]
    seen = set()
    rows = {t: [] for t in TABLES}
    total_edges = 0

    def visit(ref, kinds, table=None, descriptor=None):
        nonlocal total_edges
        raw = objects[ref["hash"]]
        b = json.loads(raw)
        assert (
            c1(b) == raw
            and h(b["kind"], raw) == ref["hash"]
            and len(raw) == int(ref["bytes"])
        )
        assert b["ns"] == target["ns"] and b["kind"] in kinds
        if table is not None:
            assert b["table"] == table
            assert all(b[f] == descriptor[f] for f in ("height", "count", "min", "max"))
        assert ref["hash"] not in seen
        seen.add(ref["hash"])
        if b["kind"] == "snapshot-leaf":
            rows[b["table"]].extend(b["rows"])
        children = edges(b)
        total_edges += len(children)
        for child in children:
            visit(*child)

    for role, kind in [
        ("raw", "raw-root"),
        ("index", "index-root"),
        ("hot", "hot"),
        ("control", "control"),
    ]:
        visit(target[role + "_ref"], {kind})
    assert seen == set(objects)
    for table in TABLES:
        pk = (
            "entry_payment_key"
            if table == "card_payment_deferrals"
            else "registration_key"
            if table == "notification_candidate_registrations"
            else "key"
            if table in ("app_settings", "app_labels")
            else "id"
        )
        assert {str(r["key"][1]): r["value"] for r in rows[table]} == {
            str(r[pk]): r for r in fixture["source"][table]
        }
    return seen, rows, total_edges


def facts(target, rows):
    result = {}
    sums = defaultdict(int)
    counts = defaultdict(int)
    refs = {
        "ledger_entries": {"source_planned_entry_id": "ledger_entries"},
        "monthly_panels": {"confirmed_cash_flow_id": "cash_flows"},
        "card_payment_events": {
            "batch_id": "card_payment_batches",
            "cash_flow_id": "cash_flows",
        },
        "card_payment_batch_items": {
            "batch_id": "card_payment_batches",
            "entry_id": "ledger_entries",
        },
        "card_payment_allocations": {
            "payment_event_id": "card_payment_events",
            "entry_payment_key": "@ledger_payment_key",
        },
    }

    def add(k, v):
        ident = c1(k)
        assert ident not in result
        result[ident] = {"key": k, "value": v}

    for table in TABLES:
        for item in rows[table]:
            k, r = item["key"], item["value"]
            owner = [table, k]
            digest = h(
                "row",
                c1(
                    dict(
                        ns=target["ns"],
                        raw_schema=target["versions"]["raw_schema"],
                        table=table,
                        key=k,
                        value=r,
                    )
                ),
            )
            add(["pk", table, k], digest)

            def unique(domain, components):
                add(["unique", domain, components], owner)

            if table == "ledger_entries":
                if r["payment_key"] is not None:
                    unique("ledger_payment_key", [r["payment_key"]])
                if (
                    r["entry_kind"] == "expense"
                    and r["source_planned_entry_id"] is not None
                ):
                    unique(
                        "recurring_child",
                        [
                            key(r["source_planned_entry_id"]),
                            r["confirmed_month"],
                            r["confirmed_at"],
                        ],
                    )
                if r["entry_kind"] == "planned" or any(
                    r[f] is not None
                    for f in (
                        "source_planned_entry_id",
                        "confirmed_month",
                        "confirmed_at",
                    )
                ):
                    add(["context_reverse", "last_closed_month", table, k], digest)
            elif table == "monthly_panels" and r["panel_type"] == "fixed":
                add(["context_reverse", "last_closed_month", table, k], digest)
                if r["confirmed_cash_flow_id"] is not None:
                    unique("cash_owner", [key(r["confirmed_cash_flow_id"])])
            elif table == "card_payment_batch_items":
                unique("batch_pair", [key(r["batch_id"]), r["entry_payment_key"]])
                unique("batch_key", [r["entry_payment_key"]])
                unique("batch_entry", [key(r["entry_id"])])
            elif table == "card_payment_events":
                if r["idempotency_key"] is not None:
                    unique("event_idempotency", [r["idempotency_key"]])
                if r["cash_flow_id"] is not None:
                    unique("cash_owner", [key(r["cash_flow_id"])])
            elif table == "card_payment_allocations":
                unique(
                    "allocation_pair",
                    [key(r["payment_event_id"]), r["entry_payment_key"]],
                )
                add(
                    [
                        "allocation",
                        key(r["payment_event_id"]),
                        r["entry_payment_key"],
                        k,
                    ],
                    str(int(r["amount_value"])),
                )
                sums[r["payment_event_id"]] += int(r["amount_value"])
                counts[r["payment_event_id"]] += 1
            for field, destination in refs.get(table, {}).items():
                if r[field] is not None:
                    d = key(r[field])
                    add(["ref", table, k, field], [destination, d])
                    add(["reverse", destination, d, table, k, field], digest)
    for item in rows["card_payment_events"]:
        ident = item["value"]["id"]
        add(["aggregate", "event", item["key"]], [str(counts[ident]), str(sums[ident])])
    add(
        ["aggregate", "active_batch"],
        str(
            sum(i["value"]["status"] == "active" for i in rows["card_payment_batches"])
        ),
    )
    closed = next(
        (
            i["value"]["value"]
            for i in rows["app_settings"]
            if i["value"]["key"] == "last_closed_month"
        ),
        None,
    )
    add(["context", "last_closed_month"], closed)
    return list(result.values())


def patricia(target, fs):
    common = dict(
        ns=target["ns"],
        canon=1,
        structural=1,
        raw_schema=target["versions"]["raw_schema"],
    )
    buckets = defaultdict(list)
    for f in fs:
        buckets[h("fact-key", c1(f["key"]))].append(f)

    def make(kind, **fields):
        raw = c1(dict(kind=kind, **common, **fields))
        return dict(hash=h(kind, raw), bytes=str(len(raw)))

    def build(keys):
        if not keys:
            return make("index-empty", count="0"), 0
        if len(keys) == 1:
            values = sorted(buckets[keys[0]], key=lambda f: c1(f["key"]))
            return make(
                "index-leaf", digest=keys[0], count=str(len(values)), facts=values
            ), len(values)
        first, last = (bin(int(k, 16))[2:].zfill(256) for k in (keys[0], keys[-1]))
        n = 0
        while first[n] == last[n]:
            n += 1
        split = next(
            i for i, k in enumerate(keys) if bin(int(k, 16))[2:].zfill(256)[n] == "1"
        )
        left, a = build(keys[:split])
        right, b = build(keys[split:])
        return make(
            "index-node", prefix=first[:n], left=left, right=right, count=str(a + b)
        ), a + b

    root, count = build(sorted(buckets))
    return make("index-root", facts=root, count=str(count))


def persisted(path, fixtures):
    with closing(sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        has_roots = (
            db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='generation_roots'"
            ).fetchone()
            is not None
        )
        pointer = dict(db.execute("SELECT * FROM accepted").fetchone())
        namespace = db.execute("SELECT namespace FROM profile").fetchone()[0]
        expected_checksum = hashlib.sha256(
            c1(
                dict(
                    namespace=namespace,
                    current=pointer["current_id"],
                    previous=pointer["previous_id"],
                    sequence=str(pointer["sequence"]),
                )
            )
        ).hexdigest()
        assert pointer["checksum"] == expected_checksum
        result = dict(pointer=pointer, generations=[])
        assert (
            db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            and not db.execute("PRAGMA foreign_key_check").fetchall()
        )
        for ident in (pointer["current_id"], pointer["previous_id"]):
            if ident is None:
                continue
            generation = db.execute(
                "SELECT * FROM generations WHERE id=?", (ident,)
            ).fetchone()
            manifest = json.loads(generation["manifest"])
            target = manifest["target"]
            assert (
                hashlib.sha256(generation["manifest"]).hexdigest()
                == generation["manifest_checksum"]
            )
            assert (
                hashlib.sha256(generation["receipt"]).hexdigest()
                == generation["receipt_checksum"]
            )
            fixture = next(
                f
                for f in fixtures
                if f["manifest"]["target"]["sync_root"] == target["sync_root"]
            )
            expected, raw_rows, edge_count = graph(fixture)
            roots = {
                r[0]
                for r in db.execute(
                    "SELECT hash FROM generation_roots WHERE generation_id=? UNION SELECT hash FROM generation_objects WHERE generation_id=?"
                    if has_roots
                    else "SELECT hash FROM generation_objects WHERE generation_id=?",
                    (ident, ident) if has_roots else (ident,),
                )
            }
            seen = set()
            pending = list(roots)
            while pending:
                hash_ = pending.pop()
                if hash_ in seen:
                    continue
                seen.add(hash_)
                row = db.execute(
                    "SELECT body FROM objects WHERE hash=?", (hash_,)
                ).fetchone()
                assert row is not None
                raw = bytes(row[0])
                body = json.loads(raw)
                assert c1(body) == raw and h(body["kind"], raw) == hash_
                child_hashes = {e[0]["hash"] for e in edges(body)}
                stored = {
                    r[0]
                    for r in db.execute(
                        "SELECT child FROM edges WHERE parent=?", (hash_,)
                    )
                }
                assert stored == child_hashes
                pending.extend(child_hashes)
            assert seen == expected
            receipt = json.loads(generation["receipt"])
            assert receipt["target"] == target and receipt["objects"] == len(expected)
            assert receipt["edges"] == edge_count and int(receipt["facts"]) == len(
                facts(target, raw_rows)
            )
            assert receipt["authority_history"]["owner"] == target["principal_id"]
            if receipt["validator"] == "segmented-e3/2":
                association = dict(
                    roots={
                        role: target[role + "_ref"]
                        for role in ("raw", "index", "hot", "control")
                    },
                    objects=len(expected),
                    edges=edge_count,
                )
                assert (
                    receipt["object_set"] == hashlib.sha256(c1(association)).hexdigest()
                )
            else:
                refs = sorted(
                    [o["ref"] for o in fixture["objects"]], key=lambda r: r["hash"]
                )
                assert receipt["object_set"] == hashlib.sha256(c1(refs)).hexdigest()
            result["generations"].append(
                dict(
                    id=ident,
                    target=target["sync_root"],
                    objects=len(seen),
                    roots=len(roots),
                    receipt_validator=receipt["validator"],
                )
            )
        result["root_pin_rows"] = (
            db.execute("SELECT count(*) FROM generation_roots").fetchone()[0]
            if has_roots
            else 0
        )
        return result

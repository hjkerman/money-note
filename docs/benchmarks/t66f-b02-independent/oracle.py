"""독립 C1/hash/도달성/SQL-row oracle. 제품 graph/row decoder를 호출하지 않는다."""

from collections import Counter
import hashlib
import json

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
        if t in {"app_settings", "app_labels"}
        else "id"
    )
    for t in TABLES
}
_LAST = None


def encode(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest_set(hashes):
    digest = hashlib.sha256()
    for h in sorted(hashes):
        digest.update(h.encode() + b"\n")
    return digest.hexdigest()


def walk(conn, target, *, client=False, sql_values=True):
    global _LAST
    table = "objects" if client else "sync_objects"

    def read(ref):
        row = conn.execute(
            f"SELECT kind,body FROM {table} WHERE hash=?", (ref["hash"],)
        ).fetchone()
        assert row is not None, ("missing", ref)
        kind, raw = row
        raw = bytes(raw)
        assert len(raw) == int(ref["bytes"])
        assert (
            hashlib.sha256(
                b"money-note.sync.v1/" + kind.encode() + b"\0" + raw
            ).hexdigest()
            == ref["hash"]
        )
        value = json.loads(raw)
        assert value["kind"] == kind and encode(value) == raw, ("C1", kind)
        assert value["ns"] == target["ns"]
        return kind, value, raw

    pending = [
        (target[r + "_ref"], 0, {k})
        for r, k in [
            ("raw", "raw-root"),
            ("index", "index-root"),
            ("hot", "hot"),
            ("control", "control"),
        ]
    ]
    seen = set()
    kinds = Counter()
    sizes = Counter()
    raw_rows = Counter()
    facts = Counter()
    edges = 0
    depth = 0
    fanout = 0
    largest = 0
    while pending:
        ref, d, allowed = pending.pop()
        if ref["hash"] in seen:
            continue
        kind, obj, raw = read(ref)
        assert kind in allowed
        seen.add(ref["hash"])
        kinds[kind] += 1
        sizes[kind] += len(raw)
        depth = max(depth, d)
        largest = max(largest, len(raw))
        children = []
        if kind == "raw-root":
            assert [x["name"] for x in obj["tables"]] == list(TABLES)
            for entry in obj["tables"]:
                desc = entry["root"]
                assert desc["count"] == entry["count"]
                children.append(
                    (
                        desc["ref"],
                        {"snapshot-node"} if desc["height"] else {"snapshot-leaf"},
                    )
                )
        elif kind == "snapshot-node":
            children = [
                (x["ref"], {"snapshot-node"} if x["height"] else {"snapshot-leaf"})
                for x in obj["children"]
            ]
        elif kind == "snapshot-leaf":
            assert len(obj["rows"]) == int(obj["count"])
            raw_rows[obj["table"]] += len(obj["rows"])
            assert all(
                x["key"]
                == [
                    "i" if isinstance(x["value"][PRIMARY[obj["table"]]], int) else "t",
                    str(x["value"][PRIMARY[obj["table"]]]),
                ]
                for x in obj["rows"]
            )
        elif kind == "index-root":
            children = [
                (
                    obj["facts"],
                    {"index-empty"}
                    if obj["count"] == "0"
                    else {"index-node", "index-leaf"},
                )
            ]
        elif kind == "index-node":
            children = [
                (obj[x], {"index-node", "index-leaf"}) for x in ["left", "right"]
            ]
        elif kind == "index-leaf":
            for f in obj["facts"]:
                facts[f["key"][0]] += 1
        edges += len(children)
        fanout = max(fanout, len(children))
        pending.extend((r, d + 1, k) for r, k in children)

    def values(ref):
        kind, b, _ = read(ref)
        if kind == "snapshot-node":
            for child in b["children"]:
                yield from values(child["ref"])
        else:
            assert kind == "snapshot-leaf"
            yield from (row["value"] for row in b["rows"])

    rawroot = read(target["raw_ref"])[1]
    digests = {}
    sql_compared = 0
    for entry in rawroot["tables"]:
        name = entry["name"]
        vals = values(entry["root"]["ref"])
        digest = hashlib.sha256()
        count = 0
        cursor = None
        if sql_values:
            where = (
                " WHERE key NOT IN ('share_pin_hash','share_pin_is_default')"
                if name == "app_settings"
                else ""
            )
            cursor = conn.execute(
                f"SELECT * FROM {name}{where} ORDER BY {PRIMARY[name]}"
            )
            columns = [x[0] for x in cursor.description]
        for value in vals:
            if cursor is not None:
                row = cursor.fetchone()
                assert row is not None
                expected = dict(zip(columns, row))
                assert encode(value) == encode(expected), (
                    name,
                    value.get(PRIMARY[name]),
                )
                sql_compared += 1
            digest.update(hashlib.sha256(encode(value)).hexdigest().encode() + b"\n")
            count += 1
        if cursor is not None:
            assert cursor.fetchone() is None
        assert count == int(entry["count"])
        digests[name] = {"count": count, "sha256": digest.hexdigest()}
    new = None if _LAST is None else sorted(seen - _LAST)
    if not client:
        _LAST = seen
    graph = {
        "objects": len(seen),
        "canonical_bytes": sum(sizes.values()),
        "kinds": dict(kinds),
        "kind_bytes": dict(sizes),
        "edges": edges,
        "max_depth": depth,
        "max_fanout": fanout,
        "largest_object": largest,
        "raw_rows": dict(raw_rows),
        "fact_domains": dict(facts),
        "raw_value_sha256": digests,
        "audit_reachable_hash_set_sha256": digest_set(seen),
        "audit_sql_rows_compared": sql_compared,
        "audit_new_hashes": new if new is not None and len(new) <= 100 else None,
    }
    return seen, graph

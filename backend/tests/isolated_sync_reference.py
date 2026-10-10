"""Independent O(N) test oracles. Never imported by product or isolated library."""

import hashlib
import json


def c1(value):
    # Valid admitted inputs only; committed vectors independently test admission.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8", errors="strict")


def ref(kind, body):
    raw = c1(body)
    return {"hash": hashlib.sha256(b"money-note.sync.v1/" + kind.encode() + b"\0" + raw).hexdigest(),
            "bytes": str(len(raw))}


def patricia_root(context, facts, digest=None):
    fields = dict(ns=context.ns.wire(), canon=1, structural=1, raw_schema=context.raw_schema)
    groups = {}
    for fact in facts:
        h = digest(fact.key) if digest else hashlib.sha256(b"money-note.sync.v1/fact-key\0" + fact.key).hexdigest()
        groups.setdefault(h, []).append(fact)

    def construct(groups, depth=0):
        if not groups:
            return ref("index-empty", dict(kind="index-empty", **fields, count="0"))
        if len(groups) == 1:
            h, bucket = next(iter(groups.items()))
            body = dict(kind="index-leaf", **fields, digest=h, count=str(len(bucket)), facts=[
                {"key": json.loads(f.key), "value": json.loads(f.value)} for f in sorted(bucket, key=lambda f: f.key)])
            return ref("index-leaf", body)
        # Bit-at-a-time radix reference, not the implementation's sorted-leaf split.
        paths = {h: format(int(h, 16), "0256b") for h in groups}
        while len({path[depth] for path in paths.values()}) == 1:
            depth += 1
        left = {h: v for h, v in groups.items() if paths[h][depth] == "0"}
        right = {h: v for h, v in groups.items() if paths[h][depth] == "1"}
        return ref("index-node", dict(kind="index-node", **fields,
                   prefix=next(iter(paths.values()))[:depth], count=str(sum(map(len, groups.values()))),
                   left=construct(left, depth+1), right=construct(right, depth+1)))
    return ref("index-root", dict(kind="index-root", **fields, facts=construct(groups),
                                  count=str(len(facts))))


def audit_tree(tree):
    """Validate serialized reachable graph independently of Node/Tree validators."""
    objects = {o.hash: o.raw for o in tree.objects()}
    seen = set()

    def visit(descriptor, root=False):
        address = descriptor["ref"]
        assert address["hash"] not in seen
        seen.add(address["hash"])
        raw = objects[address["hash"]]
        body = json.loads(raw)
        assert raw == c1(body)
        assert ref(body["kind"], body) == address
        assert body["table"] == tree.table and body["ns"] == tree.context.ns.wire()
        if body["height"] == 0:
            records = body["rows"]
            assert len(records) <= 256
            assert body["oversized"] == (len(records) == 1 and len(raw) + (1 if body["oversized"] else 0) > 262144)
            assert body["oversized"] or len(raw) <= 262144
        else:
            assert (2 if root else 16) <= len(body["children"]) <= 32
            records = []
            for child in body["children"]:
                assert child["height"] == body["height"]-1
                records.extend(visit(child))
        keys = [r["key"] for r in records]
        order = [int(k[1]) if k[0] == "i" else k[1].encode() for k in keys]
        assert all(a < b for a, b in zip(order, order[1:]))
        assert body["min"] == (keys[0] if keys else None)
        assert body["max"] == (keys[-1] if keys else None)
        assert body["count"] == str(len(records))
        assert all(descriptor[k] == body[k] for k in ("min", "max", "count", "height"))
        return records
    rows = visit(tree.root.descriptor(), True)
    assert seen == set(objects)
    return rows


def facts_from_raw(context, data):
    """Independent complete catalog oracle for VALID states; no production extractor.

    Identity rules are spelled out here, not imported from isolated_sync.facts.
    Constraint rejection additionally uses actual SQLite and legacy validators.
    """
    result, sums, counts = {}, {}, {}
    links = [("ledger_entries", "source_planned_entry_id", "ledger_entries"),
             ("monthly_panels", "confirmed_cash_flow_id", "cash_flows"),
             ("card_payment_events", "batch_id", "card_payment_batches"),
             ("card_payment_events", "cash_flow_id", "cash_flows"),
             ("card_payment_batch_items", "batch_id", "card_payment_batches"),
             ("card_payment_batch_items", "entry_id", "ledger_entries"),
             ("card_payment_allocations", "payment_event_id", "card_payment_events"),
             ("card_payment_allocations", "entry_payment_key", "@ledger_payment_key")]

    def key(value):
        return ["i", str(value)] if type(value) is int else ["t", value]

    def add(k, v):
        raw = c1(k)
        assert raw not in result
        result[raw] = c1(v)

    for table, rows in data.items():
        pk = {"app_settings": "key", "app_labels": "key", "card_payment_deferrals": "entry_payment_key",
              "notification_candidate_registrations": "registration_key"}.get(table, "id")
        for row in rows:
            identity = key(row[pk])
            owner = [table, identity]
            digest = ref("row", dict(ns=context.ns.wire(), raw_schema=context.raw_schema,
                                     table=table, key=identity, value=row))["hash"]
            add(["pk", table, identity], digest)
            domains = []
            if table == "ledger_entries":
                if row["payment_key"] is not None:
                    domains.append(("ledger_payment_key", [row["payment_key"]]))
                if row["entry_kind"] == "expense" and row["source_planned_entry_id"] is not None:
                    domains.append(("recurring_child", [key(row["source_planned_entry_id"]), row["confirmed_month"], row["confirmed_at"]]))
                if row["entry_kind"] == "planned" or any(row[k] is not None for k in ("source_planned_entry_id", "confirmed_month", "confirmed_at")):
                    add(["context_reverse", "last_closed_month", table, identity], digest)
            if table == "monthly_panels" and row["panel_type"] == "fixed":
                add(["context_reverse", "last_closed_month", table, identity], digest)
                if row["confirmed_cash_flow_id"] is not None:
                    domains.append(("cash_owner", [key(row["confirmed_cash_flow_id"])]))
            if table == "card_payment_batch_items":
                domains += [("batch_pair", [key(row["batch_id"]), row["entry_payment_key"]]),
                            ("batch_key", [row["entry_payment_key"]]), ("batch_entry", [key(row["entry_id"])])]
            if table == "card_payment_events":
                if row["cash_flow_id"] is not None:
                    domains.append(("cash_owner", [key(row["cash_flow_id"])]))
                if row["idempotency_key"] is not None:
                    domains.append(("event_idempotency", [row["idempotency_key"]]))
            if table == "card_payment_allocations":
                event = key(row["payment_event_id"])
                domains.append(("allocation_pair", [event, row["entry_payment_key"]]))
                add(["allocation", event, row["entry_payment_key"], identity], str(int(row["amount_value"])))
                sums[row["payment_event_id"]] = sums.get(row["payment_event_id"], 0) + int(row["amount_value"])
                counts[row["payment_event_id"]] = counts.get(row["payment_event_id"], 0) + 1
            for domain, components in domains:
                add(["unique", domain, components], owner)
            for source, field, destination in links:
                if source == table and row[field] is not None:
                    dst = [destination, key(row[field])]
                    add(["ref", table, identity, field], dst)
                    add(["reverse", *dst, table, identity, field], digest)
    for event in data["card_payment_events"]:
        add(["aggregate", "event", key(event["id"])], [str(counts.get(event["id"], 0)), str(sums.get(event["id"], 0))])
    add(["aggregate", "active_batch"], str(len([r for r in data["card_payment_batches"] if r["status"] == "active"])))
    add(["context", "last_closed_month"], next((r["value"] for r in data["app_settings"] if r["key"] == "last_closed_month"), None))
    return result

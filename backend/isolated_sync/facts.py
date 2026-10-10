"""Complete structural=1 raw facts, T6.6C §§10–11, not financial formulas.

SQLite PK/UNIQUE/FKs and the already approved raw recovery predicates are
distinct obligations. Registration/deferral targets intentionally are NOT FKs.
"""

import calendar
from datetime import date

from isolated_sync.canonical import Key, fail, money
from isolated_sync.patricia import Fact, Index
from isolated_sync.raw import MONEY_SETTINGS, PRIMARY, TABLES, Row, valid_stamp


REFERENCES = {
    "ledger_entries": (("source_planned_entry_id", "ledger_entries"),),
    "monthly_panels": (("confirmed_cash_flow_id", "cash_flows"),),
    "card_payment_events": (("batch_id", "card_payment_batches"), ("cash_flow_id", "cash_flows")),
    "card_payment_batch_items": (("batch_id", "card_payment_batches"), ("entry_id", "ledger_entries")),
    "card_payment_allocations": (("payment_event_id", "card_payment_events"),
                                 ("entry_payment_key", "@ledger_payment_key")),
}


def row_facts(context, row):
    """Local facts only, O(one row width). D2b must update closure/aggregates too."""
    value, table, key = row.value(), row.table, row.key.wire()
    digest = row.hash(context)
    owner = [table, key]
    result = [Fact.make(["pk", table, key], digest)]

    def unique(domain, components):
        result.append(Fact.make(["unique", domain, components], owner))

    if table == "ledger_entries":
        if value["payment_key"] is not None:
            unique("ledger_payment_key", [value["payment_key"]])
        if value["entry_kind"] == "expense" and value["source_planned_entry_id"] is not None:
            unique("recurring_child", [Key(value["source_planned_entry_id"]).wire(),
                                       value["confirmed_month"], value["confirmed_at"]])
        if (value["entry_kind"] == "planned" or value["source_planned_entry_id"] is not None or
                value["confirmed_month"] is not None or value["confirmed_at"] is not None):
            result.append(Fact.make(["context_reverse", "last_closed_month", table, key], digest))
    elif table == "monthly_panels":
        if value["panel_type"] == "fixed":
            result.append(Fact.make(["context_reverse", "last_closed_month", table, key], digest))
            if value["confirmed_cash_flow_id"] is not None:
                unique("cash_owner", [Key(value["confirmed_cash_flow_id"]).wire()])
    elif table == "card_payment_batch_items":
        unique("batch_pair", [Key(value["batch_id"]).wire(), value["entry_payment_key"]])
        unique("batch_key", [value["entry_payment_key"]])
        unique("batch_entry", [Key(value["entry_id"]).wire()])
    elif table == "card_payment_events":
        if value["idempotency_key"] is not None:
            unique("event_idempotency", [value["idempotency_key"]])
        if value["cash_flow_id"] is not None:
            unique("cash_owner", [Key(value["cash_flow_id"]).wire()])
    elif table == "card_payment_allocations":
        event = Key(value["payment_event_id"]).wire()
        unique("allocation_pair", [event, value["entry_payment_key"]])
        result.append(Fact.make(["allocation", event, value["entry_payment_key"], key],
                                str(money(value["amount_value"]))))
    for field, target_table in REFERENCES.get(table, ()):
        if value[field] is not None:
            target_key = Key(value[field]).wire()
            result.extend((Fact.make(["ref", table, key, field], [target_table, target_key]),
                           Fact.make(["reverse", target_table, target_key, table, key, field], digest)))
    return tuple(result)


def _epoch(row):
    month, stamp = row["confirmed_month"], row["confirmed_at"]
    if (month is None) != (stamp is None) or (stamp is not None and not valid_stamp(stamp)):
        fail("REJECT_RECURRING_EPOCH")


def _fixed_period(day, month, closed):
    current = day[:7]
    if month == current:
        return True
    parsed = date.fromisoformat(day)
    if parsed.year == 9999 and parsed.month == 12:
        return False
    next_month = date(parsed.year + (parsed.month == 12), parsed.month % 12 + 1, 1).isoformat()[:7]
    return (parsed.day == calendar.monthrange(parsed.year, parsed.month)[1] and
            closed == current and month == next_month)


def validate_state(data):
    """O(N) complete-state structural oracle, no mutation, coercion or repair."""
    if type(data) is not dict or set(data) != set(TABLES):
        fail("REJECT_TABLE_COVERAGE")
    indexed = {}
    for table in TABLES:
        indexed[table] = {}
        for value in data[table]:
            row = Row.make(table, value)
            if row.key.value in indexed[table]:
                fail("REJECT_DUPLICATE_PK")
            indexed[table][row.key.value] = value
    entries, flows = indexed["ledger_entries"], indexed["cash_flows"]
    panels, batches = indexed["monthly_panels"], indexed["card_payment_batches"]
    events, settings = indexed["card_payment_events"], indexed["app_settings"]
    if not MONEY_SETTINGS <= set(settings):
        fail("REJECT_REQUIRED_SETTING")
    closed = settings.get("last_closed_month", {}).get("value")
    keys, epochs = {}, {}
    for row in entries.values():
        payment = row["payment_key"]
        if payment is not None:
            if payment in keys:
                fail("REJECT_LEDGER_PAYMENT_UNIQUE")
            keys[payment] = row
        source = row["source_planned_entry_id"]
        if row["entry_kind"] == "planned":
            _epoch(row)
            if source is not None or (row["entry_date"] is not None and row["confirmed_month"] is None):
                fail("REJECT_RECURRING_SOURCE")
        elif source is not None or (row["entry_kind"] == "expense" and
                                    (row["confirmed_month"] is not None or row["confirmed_at"] is not None)):
            _epoch(row)
            parent = entries.get(source)
            if (row["entry_kind"] != "expense" or parent is None or parent["entry_kind"] != "planned" or
                    row["confirmed_month"] is None or row["amount_value"] is None or money(row["amount_value"]) < 0):
                fail("REJECT_RECURRING_CHILD")
            epoch = (source, row["confirmed_month"], row["confirmed_at"])
            if epoch in epochs:
                fail("REJECT_RECURRING_UNIQUE")
            epochs[epoch] = row
            if row["confirmed_month"] > (closed or "0000-00") and (
                    parent["confirmed_month"], parent["confirmed_at"]) != epoch[1:]:
                fail("REJECT_RECURRING_ACTIVE")
    for source in entries.values():
        if source["entry_kind"] == "planned" and source["confirmed_month"] is not None and (
                source["id"], source["confirmed_month"], source["confirmed_at"]) not in epochs:
            fail("REJECT_RECURRING_MISSING")
    if sum(row["status"] == "active" for row in batches.values()) > 1:
        fail("REJECT_ACTIVE_BATCH")
    owners, item_entries, pairs = {}, set(), set()
    for item in indexed["card_payment_batch_items"].values():
        entry = entries.get(item["entry_id"])
        key, batch = item["entry_payment_key"], item["batch_id"]
        if (batch not in batches or entry is None or entry["entry_kind"] == "planned" or not key or
                entry["payment_key"] != key or entry["amount_value"] is None or money(entry["amount_value"]) < 0):
            fail("REJECT_BATCH_REFERENCE")
        if (batch, key) in pairs or key in owners or entry["id"] in item_entries:
            fail("REJECT_BATCH_UNIQUE")
        pairs.add((batch, key))
        owners[key] = batch
        item_entries.add(entry["id"])
    totals, counts, pairs = {}, {}, set()
    for part in indexed["card_payment_allocations"].values():
        event_id, key = part["payment_event_id"], part["entry_payment_key"]
        event, entry = events.get(event_id), keys.get(key)
        if event is None or entry is None or entry["entry_kind"] == "planned":
            fail("REJECT_ALLOCATION_REFERENCE")
        if (event_id, key) in pairs:
            fail("REJECT_ALLOCATION_UNIQUE")
        pairs.add((event_id, key))
        if event["batch_id"] is not None and owners.get(key) != event["batch_id"]:
            fail("REJECT_ALLOCATION_BATCH")
        totals[event_id] = totals.get(event_id, 0) + money(part["amount_value"])
        counts[event_id] = counts.get(event_id, 0) + 1
    event_flows, idempotency = set(), set()
    for event in events.values():
        key, flow_id = event["idempotency_key"], event["cash_flow_id"]
        if key is not None:
            if key in idempotency:
                fail("REJECT_N4_UNIQUE")
            idempotency.add(key)
        total = money(event["total_amount"])
        if event["batch_id"] is not None and event["batch_id"] not in batches:
            fail("REJECT_EVENT_BATCH")
        if total != totals.get(event["id"], 0):
            fail("REJECT_EVENT_TOTAL")
        if flow_id is not None:
            if flow_id in event_flows or flow_id not in flows:
                fail("REJECT_EVENT_CASH")
            event_flows.add(flow_id)
        if event["event_type"] == "immediate" and ((total > 0 and flow_id is None) or
                (flow_id is not None and money(flows[flow_id]["amount_value"]) != -total)):
            fail("REJECT_EVENT_OUTFLOW")
    fixed_flows = set()
    for panel in panels.values():
        flow_id = panel["confirmed_cash_flow_id"]
        if panel["panel_type"] != "fixed" and flow_id is None:
            continue
        if flow_id is None:
            if panel["confirmed_at"] is not None or panel["confirmed_month"] is not None:
                fail("REJECT_FIXED_MISSING")
            continue
        flow = flows.get(flow_id)
        if (panel["panel_type"] != "fixed" or flow is None or flow_id in fixed_flows or
                flow_id in event_flows or panel["spent_on"] != flow["occurred_on"] or
                money(flow["amount_value"]) > 0 or flow["is_primary_income"] != 0 or
                not valid_stamp(panel["confirmed_at"]) or
                not _fixed_period(panel["spent_on"], panel["confirmed_month"], closed)):
            fail("REJECT_FIXED_RELATIONSHIP")
        fixed_flows.add(flow_id)
    return indexed, totals, counts


def build_facts(context, data):
    """Complete F(data); duplicate identities are errors, never last-writer wins."""
    indexed, totals, counts = validate_state(data)
    facts = {}

    def add(fact):
        if fact.key in facts:
            fail("REJECT_FACT_DUPLICATE")
        facts[fact.key] = fact

    for table in TABLES:
        for value in data[table]:
            for fact in row_facts(context, Row.make(table, value)):
                add(fact)
    for event_id in indexed["card_payment_events"]:
        add(Fact.make(["aggregate", "event", Key(event_id).wire()],
                      [str(counts.get(event_id, 0)), str(totals.get(event_id, 0))]))
    add(Fact.make(["aggregate", "active_batch"],
                  str(sum(r["status"] == "active" for r in indexed["card_payment_batches"].values()))))
    add(Fact.make(["context", "last_closed_month"],
                  indexed["app_settings"].get("last_closed_month", {}).get("value")))
    return tuple(facts[key] for key in sorted(facts))


def validate_index(context, data, index):
    """Explicit full-state F(raw) completeness check; not an incremental finalizer.

    Index.validate alone proves representation, NOT global constraint coverage.
    Reconstructing the complete expected index is deliberately O(full state).
    """
    if index.context != context:
        fail("REJECT_INDEX_CONTEXT")
    index.validate()
    expected = Index.build(context, build_facts(context, data))
    if index.object() != expected.object():
        fail("REJECT_FACT_COMPLETENESS")
    return index.root.count


def read_state(conn):
    """Read-only explicit borrowed synthetic connection. Caller fixes read view.

    Requires sqlite3.Row row_factory. No configured database/path is opened here.
    Sensitive values never leave SQL.
    """
    result = {}
    for table in TABLES:
        where = " WHERE key NOT IN ('share_pin_hash','share_pin_is_default')" if table == "app_settings" else ""
        result[table] = [dict(row) for row in conn.execute(f"SELECT * FROM {table}{where} ORDER BY {PRIMARY[table]}")]
    return result

"""Transaction-local coalescing, adjacency and exact maintained inputs.

These are backend raw-state inputs, not a second financial projection engine.
The complete-state validator is invoked only on a proven relationship closure.
"""

from collections import deque
from datetime import date

from isolated_sync.canonical import Key, decode_c1, encode, fail, money
from isolated_sync.facts import REFERENCES, row_facts, validate_state
from isolated_sync.raw import MONEY_SETTINGS, PRIMARY, SENSITIVE, TABLES, Row


def coalesce(changes, trees, conn):
    """Replay ordered capture against accepted rows, retaining first OLD/final NEW.

    Membership, not an invented persistent entity ID, is the output. Deletion
    followed by key reuse is checked against absence before accepting the INSERT.
    """
    first, live = {}, {}

    def accepted(table, key):
        identity = (table, key)
        if identity not in live:
            first[identity] = live[identity] = trees[table].lookup(Key(key))
        return identity

    for change in changes:
        table, op = change["table_name"], change["operation"]
        for side, present in (("old", op != "INSERT"), ("new", op != "DELETE")):
            key, visible, value = change[f"{side}_key"], change[f"{side}_visible"], change[side]
            expected = present and not (table == "app_settings" and key in SENSITIVE)
            if bool(visible) != expected or (value is None) != (not expected):
                fail("REJECT_CAPTURE_VISIBILITY")
            if not present:
                if key is not None:
                    fail("REJECT_CAPTURE_KEY")
                continue
            if not expected:
                continue  # value-free sensitive marker; R coverage checked separately
            row = Row.make(table, value)
            if row.key != Key(key):
                fail("REJECT_CAPTURE_KEY")
            identity = accepted(table, key)
            if side == "old":
                if live[identity] != row:
                    fail("REJECT_CAPTURE_OLD")
                live[identity] = None
            else:
                if live[identity] is not None:
                    fail("REJECT_CAPTURE_INSERT")
                live[identity] = row
    result = []
    for (table, key), final in sorted(live.items(), key=lambda item: (TABLES.index(item[0][0]), Key(item[0][1]).order())):
        # Final payload is independently compared with the current SQL row, by PK.
        record = conn.execute(f"SELECT * FROM {table} WHERE {PRIMARY[table]}=?", (key,)).fetchone()
        current = Row.make(table, dict(record)) if record is not None else None
        if current != final:
            fail("REJECT_CAPTURE_NEW")
        old = first[(table, key)]
        if old != final:
            result.append((old, final))
    return result


def adjacency(row):
    """Local lookup edges include both actual refs and logical payment membership."""
    if row is None:
        return []
    value, result = row.value(), []
    for field, target in REFERENCES.get(row.table, ()):
        if value[field] is not None:
            result.append((target, encode(Key(value[field]).wire()), field))
    if row.table == "card_payment_batch_items":
        result.append(("@ledger_payment_key", encode(Key(value["entry_payment_key"]).wire()), "entry_payment_key"))
    return result


def update_adjacency(conn, old, new):
    if old:
        conn.execute("DELETE FROM sync_reverse WHERE src_table=? AND src_key=?", (old.table, encode(old.key.wire())))
        conn.execute("DELETE FROM sync_context_reverse WHERE src_table=? AND src_key=?", (old.table, encode(old.key.wire())))
    if new:
        for table, key, field in adjacency(new):
            conn.execute("INSERT INTO sync_reverse VALUES (?,?,?,?,?)",
                         (table, key, new.table, encode(new.key.wire()), field))
        value = new.value()
        if ((new.table == "ledger_entries" and (value["entry_kind"] == "planned" or
                any(value[f] is not None for f in ("source_planned_entry_id", "confirmed_at", "confirmed_month")))) or
                (new.table == "monthly_panels" and value["panel_type"] == "fixed")):
            conn.execute("INSERT INTO sync_context_reverse VALUES (?,?)", (new.table, encode(new.key.wire())))


def incoming(conn, table, key):
    """Affected structural closure, excluding proven-stable CLOSED epochs.

    All changed children are separately seeded by capture. For an unchanged
    closed child, a valid planned parent still exists; its new active epoch
    cannot invalidate that child's closed epoch. UNIQUE facts remain global.
    Parent deletion/kind changes and backwards close-context changes do NOT use
    that reduction. Work may then scale with the genuinely affected closure.
    """
    result = []
    domains = {(source, field) for source, refs in REFERENCES.items() for field, target in refs if target == table}
    if table == "@ledger_payment_key":
        domains.add(("card_payment_batch_items", "entry_payment_key"))
    for source, field in sorted(domains):
        if (source, field) == ("ledger_entries", "source_planned_entry_id"):
            parent = conn.execute("SELECT entry_kind,confirmed_month,confirmed_at FROM ledger_entries WHERE id=?", (key.value,)).fetchone()
            closed = conn.execute("SELECT value FROM app_settings WHERE key='last_closed_month'").fetchone()
            if parent and parent[0] == "planned":
                rows = list(conn.execute("SELECT id FROM ledger_entries WHERE source_planned_entry_id=? AND confirmed_month>?",
                                         (key.value, str(closed[0]) if closed else "0000-00")))
                rows.extend(conn.execute("SELECT id FROM ledger_entries WHERE source_planned_entry_id=? AND confirmed_month=? AND confirmed_at=?",
                                         (key.value, parent[1], parent[2])))
            else:
                rows = conn.execute("SELECT id FROM ledger_entries WHERE source_planned_entry_id=?", (key.value,))
            result.extend(("ledger_entries", Key(r[0])) for r in rows)
        else:
            result.extend((r[0], Key.parse(decode_c1(r[1]))) for r in conn.execute(
                "SELECT src_table,src_key FROM sync_reverse WHERE dst_table=? AND dst_key=? AND field=? AND src_table=?",
                (table, encode(key.wire()), field, source)))
    return result


def context_seeds(conn, changes):
    boundaries = [row.value()["value"] if row else "0000-00" for pair in changes
                  if any(r and r.table == "app_settings" and r.key.value == "last_closed_month" for r in pair)
                  for row in pair]
    if not boundaries:
        return []
    # Reopening old periods can genuinely affect many old epochs (allowed R).
    result = [("ledger_entries", Key(r[0])) for r in conn.execute(
        "SELECT id FROM ledger_entries WHERE confirmed_month>?", (min(boundaries),))]
    result.extend(("ledger_entries", Key(r[0])) for r in conn.execute(
        "SELECT id FROM ledger_entries WHERE entry_kind='planned'"))
    result.extend(("monthly_panels", Key(r[0])) for r in conn.execute(
        "SELECT id FROM monthly_panels WHERE panel_type='fixed'"))
    return result


def closure(conn, trees, changes, index):
    """Enumerate actual incoming/outgoing R, never scan all facts to find one ref."""
    pending = deque()
    for old, new in changes:
        for row in (old, new):
            if row:
                pending.append((row.table, row.key))
                pending.extend((t, Key.parse(decode_c1(k))) for t, k, _ in adjacency(row))
                if row.table == "ledger_entries" and row.value()["payment_key"] is not None:
                    pending.append(("@ledger_payment_key", Key(row.value()["payment_key"])))
    pending.extend(context_seeds(conn, changes))
    pending.extend(("app_settings", Key(k)) for k in MONEY_SETTINGS | {"last_closed_month"})
    seen, data = set(), {table: [] for table in TABLES}
    while pending:
        table, key = pending.popleft()
        identity = (table, encode(key.wire()))
        if identity in seen:
            continue
        seen.add(identity)
        references = incoming(conn, table, key)
        pending.extend(references)
        if table == "@ledger_payment_key":
            fact = index.lookup(["unique", "ledger_payment_key", [key.value]])
            if fact:
                owner = decode_c1(fact.value)
                pending.append((owner[0], Key.parse(owner[1])))
            continue
        row = trees[table].lookup(key)
        if row is not None:
            data[table].append(row.value())
            pending.extend((t, Key.parse(decode_c1(k))) for t, k, _ in adjacency(row))
            if table == "ledger_entries" and row.value()["payment_key"] is not None:
                pending.append(("@ledger_payment_key", Key(row.value()["payment_key"])))
        elif references:
            fail("REJECT_DANGLING_REFERENCE")
    validate_state(data)
    return len(seen)


DAY_LIMIT = date.max.toordinal()


def aggregate_keys(row):
    """Exact cache cells affected by this row; independent of ledger size."""
    if row is None:
        return set()
    value, result = row.value(), set()
    if row.table == "cash_flows":
        ordinal = date.fromisoformat(value["occurred_on"]).toordinal()
        while ordinal <= DAY_LIMIT:
            result.add(("cash_prefix", str(ordinal)))
            ordinal += ordinal & -ordinal
    if row.table == "ledger_entries" and value["book_section"] == "archive" and value["entry_kind"] == "expense" and value["entry_date"]:
        result.add(("closed_count", value["entry_date"][:7]))
    field = {"ledger_entries": "entry_date", "monthly_panels": "month", "card_payment_batches": "usage_month"}.get(row.table)
    if field and value[field]:
        result.add(("policy_horizon", value[field][:7]))
    return result


def cash_prefix(conn, day):
    """Exact Fenwick prefix; <=22 PK lookups over the fixed calendar domain."""
    ordinal, total = date.fromisoformat(day).toordinal(), 0
    while ordinal:
        row = conn.execute("SELECT total FROM sync_cash_prefix WHERE ordinal=?", (ordinal,)).fetchone()
        total += int(row[0]) if row else 0
        ordinal -= ordinal & -ordinal
    return total


def closed_counts(conn, limit=3):
    if type(limit) is not int or not 1 <= limit <= 120000:
        fail("REJECT_COUNT_LIMIT")
    return [int(row[0]) for row in conn.execute(
        "SELECT total FROM sync_totals WHERE domain='closed_count' ORDER BY key DESC LIMIT ?", (limit,))]


def policy_horizon(conn, evaluation_month):
    row = conn.execute("SELECT key FROM sync_totals WHERE domain='policy_horizon' ORDER BY key DESC LIMIT 1").fetchone()
    return max(evaluation_month, row[0]) if row else evaluation_month


def _counter(conn, domain, key, delta):
    found = conn.execute("SELECT total FROM sync_totals WHERE domain=? AND key=?", (domain, key)).fetchone()
    value = (int(found[0]) if found else 0) + delta
    if value < 0:
        fail("REJECT_AGGREGATE_COUNT")
    if value:
        conn.execute("INSERT INTO sync_totals VALUES (?,?,?) ON CONFLICT(domain,key) DO UPDATE SET total=excluded.total",
                     (domain, key, str(value)))
    else:
        conn.execute("DELETE FROM sync_totals WHERE domain=? AND key=?", (domain, key))


def aggregates(conn, row, sign):
    if row is None:
        return
    value, table = row.value(), row.table
    if table == "cash_flows":
        ordinal, delta = date.fromisoformat(value["occurred_on"]).toordinal(), sign * money(value["amount_value"])
        while ordinal <= DAY_LIMIT:
            found = conn.execute("SELECT total FROM sync_cash_prefix WHERE ordinal=?", (ordinal,)).fetchone()
            total = (int(found[0]) if found else 0) + delta
            conn.execute("INSERT INTO sync_cash_prefix VALUES (?,?) ON CONFLICT(ordinal) DO UPDATE SET total=excluded.total",
                         (ordinal, str(total)))
            ordinal += ordinal & -ordinal
    if table == "ledger_entries" and value["book_section"] == "archive" and value["entry_kind"] == "expense" and value["entry_date"]:
        _counter(conn, "closed_count", value["entry_date"][:7], sign)
    field = {"ledger_entries": "entry_date", "monthly_panels": "month", "card_payment_batches": "usage_month"}.get(table)
    if field and value[field]:
        _counter(conn, "policy_horizon", value[field][:7], sign)


def update_row_facts(context, index, changes):
    """Remove all OLD before inserting NEW (identity swaps/UNIQUE reuse)."""
    for old, _ in changes:
        if old:
            for fact in row_facts(context, old):
                if index.lookup(decode_c1(fact.key)) != fact:
                    fail("REJECT_OLD_FACT")
                index = index.delete(decode_c1(fact.key))
    for _, new in changes:
        if new:
            for fact in row_facts(context, new):
                index = index.put(fact)
    return index

"""Explicit isolated financial inputs, over a complete accepted generation.

No financial formula copy: existing validators/presenters remain the oracle.
The base is immutable under D1's writer lock. Every read overlays *all* current
capture events, not just the last command; rollback/savepoint ABA is not cached.
"""

from collections import defaultdict, deque
from datetime import date

from app.money import exact_money, query_money_sum
from app.services.financial_inputs import FinancialInputScope
from app.services.financial_relationships import validate_card_payment_ownership
from app.services.legacy_recurring import validate_recurring_ownership
from isolated_sync import capture
from isolated_sync.canonical import Key, decode_c1, encode, fail
from isolated_sync.maintenance import adjacency, coalesce, context_seeds, incoming
from isolated_sync.raw import PRIMARY, TABLES


def input_key(domain, key):
    # Local cache proof, NOT the protocol global structural facts root.
    return ["local-maintained-input", domain, str(key)]


def input_index(conn, store, tx_id):
    row = conn.execute("SELECT input_hash FROM sync_commits WHERE tx_id=?", (tx_id,)).fetchone()
    size = conn.execute("SELECT length(body) FROM sync_objects WHERE hash=?", (row[0],)).fetchone() if row else None
    if size is None:
        fail("REJECT_INPUT_ROOT")
    return store.index(dict(hash=row[0], bytes=str(size[0])))


def checked_total(conn, index, domain, key):
    if domain == "cash_prefix":
        row = conn.execute("SELECT total FROM sync_cash_prefix WHERE ordinal=?", (int(key),)).fetchone()
    else:
        row = conn.execute("SELECT total FROM sync_totals WHERE domain=? AND key=?", (domain, str(key))).fetchone()
    fact = index.lookup(input_key(domain, key))
    if (row is None) != (fact is None) or (row is not None and decode_c1(fact.value) != row[0]):
        fail("REJECT_STALE_MAINTAINED_INPUT")
    return int(row[0]) if row else 0


class BoundedInputs(FinancialInputScope):
    """A borrowed D2b connection, never a fake CardOwnershipReadView receipt.

    Construct explicitly AFTER begin_capture. Never use on legacy databases,
    another transaction, or after finalize. execute forwards unchanged SQL.
    """

    def __init__(self, conn):
        from isolated_sync.finalization import FinalizationConnection, generation
        if not isinstance(conn, FinalizationConnection):
            fail("REJECT_INPUT_CONNECTION")
        self.conn = conn
        self.base, self.context, self.store, self.trees, _ = generation(conn)
        self.tx_id = self._context()[0]
        self.proof = input_index(conn, self.store, self.base["tx_id"])
        self.relationship_rows = 0

    def __getattr__(self, name):
        return getattr(self.conn, name)

    def execute(self, sql, parameters=()):
        self._check()
        return self.conn.execute(sql, parameters)

    def _context(self):
        rows = self.conn.execute("SELECT tx_id,base_revision FROM sync_tx_context").fetchall()
        if len(rows) != 1 or rows[0][1] != self.base["revision"]:
            fail("REJECT_INPUT_CONTEXT")
        return rows[0]

    def _check(self):
        if not self.conn.in_transaction or self._context()[0] != self.tx_id:
            fail("REJECT_INPUT_CONTEXT")
        current = self.conn.execute("SELECT tx_id FROM sync_current WHERE id=1").fetchone()
        if current is None or current[0] != self.base["tx_id"]:
            fail("REJECT_INPUT_BASE")

    def financial_inputs(self):
        self._check()
        return self

    def net(self):
        self._check()
        changes = capture.read_changes(self.conn, self.tx_id)
        target = self.conn.execute("SELECT revision FROM authoritative_state_revision WHERE id=1").fetchone()[0]
        if len(changes) != target-self.base["revision"] or any(
                c["revision"] != self.base["revision"]+n for n, c in enumerate(changes, 1)):
            fail("REJECT_INPUT_CAPTURE_COVERAGE")
        return coalesce(changes, self.trees, self.conn)

    def related(self, seeds=()):
        """Union of OLD-base and NEW-current adjacency, so removals stay covered.

        Extra OLD edges can only include more rows. Actual current row values
        are always read by PK; stale edge presence is not treated as an FK.
        No metadata writes: safe inside existing query_only Summary scope too.
        """
        net = self.net()
        pending, added = deque(seeds), defaultdict(list)
        for pair in net:
            for row in pair:
                if row:
                    pending.append((row.table, row.key))
                    for table, key, _ in adjacency(row):
                        pending.append((table, Key.parse(decode_c1(key))))
                        added[(table, key)].append((row.table, row.key))
                    if row.table == "ledger_entries" and row.value()["payment_key"] is not None:
                        pending.append(("@ledger_payment_key", Key(row.value()["payment_key"])))
        pending.extend(context_seeds(self.conn, net))
        data, seen = {t: [] for t in TABLES}, set()
        while pending:
            table, key = pending.popleft()
            identity = (table, encode(key.wire()))
            if identity in seen:
                continue
            seen.add(identity)
            pending.extend(added[identity])
            pending.extend(incoming(self.conn, table, key))
            if table == "@ledger_payment_key":
                row = self.conn.execute("SELECT id FROM ledger_entries WHERE payment_key=?", (key.value,)).fetchone()
                if row:
                    pending.append(("ledger_entries", Key(row[0])))
                continue
            found = self.conn.execute(f"SELECT * FROM {table} WHERE {PRIMARY[table]}=?", (key.value,)).fetchone()
            if found:
                value = dict(found)
                data[table].append(value)
                # Raw SQL values (including transient invalid values) reach the
                # EXISTING validators; don't normalize financial input here.
                from isolated_sync.raw import Row
                row = Row.make(table, value)
                pending.extend((t, Key.parse(decode_c1(k))) for t, k, _ in adjacency(row))
                if table == "ledger_entries" and value["payment_key"] is not None:
                    pending.append(("@ledger_payment_key", Key(value["payment_key"])))
        self.relationship_rows += sum(map(len, data.values()))
        return data

    def validate_card_ownership(self):
        active = [("card_payment_batches", Key(r[0])) for r in self.conn.execute(
            "SELECT id FROM card_payment_batches WHERE status='active'")]
        validate_card_payment_ownership(self.related(active))

    def validate_recurring_ownership(self):
        data = self.related()
        closed = self.conn.execute("SELECT value FROM app_settings WHERE key='last_closed_month'").fetchone()
        validate_recurring_ownership(data["ledger_entries"], str(closed[0]) if closed else "0000-00",
                                     require_execution_epoch=False)

    def recurring_candidates(self, sources):
        # Only requested sources and their complete affected closure. A child
        # in archive or with NULL/date edits is included by identity, not date.
        self.validate_recurring_ownership()
        return self.related(("ledger_entries", Key(r["id"])) for r in sources)["ledger_entries"]

    def recurring_source_rows(self, source_id, entry_id=None):
        ids = (source_id,) if entry_id is None else (source_id, entry_id)
        return self.related(("ledger_entries", Key(value)) for value in ids)["ledger_entries"]

    def cash_total(self, cutoff):
        self._check()
        ordinal, total = date.fromisoformat(cutoff).toordinal(), 0
        while ordinal:
            total += checked_total(self.conn, self.proof, "cash_prefix", ordinal)
            ordinal -= ordinal & -ordinal
        for old, new in self.net():
            for row, sign in ((old, -1), (new, 1)):
                if row and row.table == "cash_flows" and row.value()["occurred_on"] <= cutoff:
                    total += sign * exact_money(row.value()["amount_value"])
        # Same wide intermediate semantics as query_money_sum, not an exposed
        # named API amount. Existing Summary applies exact_money at its boundary.
        return total

    def closed_counts(self, limit):
        return [r[1] for r in self._counter_view("closed_count", limit)]

    def policy_horizon(self, evaluation_month):
        values = self._counter_view("policy_horizon", 1)
        if values:
            checked_total(self.conn, self.proof, "policy_horizon", values[0][0])
        return max(evaluation_month, values[0][0]) if values else evaluation_month

    def _counter_view(self, domain, limit):
        """Indexed top-k plus changed keys; at most limit+D base keys examined."""
        deltas = defaultdict(int)
        for pair in self.net():
            for row, sign in zip(pair, (-1, 1)):
                if row:
                    value = row.value()
                    if domain == "closed_count":
                        field = "entry_date" if row.table == "ledger_entries" and value["book_section"] == "archive" and value["entry_kind"] == "expense" else None
                    else:
                        field = {"ledger_entries": "entry_date", "monthly_panels": "month", "card_payment_batches": "usage_month"}.get(row.table)
                    if field and value[field]:
                        deltas[value[field][:7]] += sign
        keys = {r[0] for r in self.conn.execute(
            "SELECT key FROM sync_totals WHERE domain=? ORDER BY key DESC LIMIT ?", (domain, limit+len(deltas)))} | deltas.keys()
        totals = {key: checked_total(self.conn, self.proof, domain, key)+deltas.get(key, 0) for key in keys}
        if any(n < 0 for n in totals.values()):
            fail("REJECT_STALE_MAINTAINED_INPUT")
        return [(key, totals[key]) for key in sorted(keys, reverse=True) if totals[key]][:limit]

    def discount_totals(self, keys):
        self._check()
        result = {}
        for key in set(keys):
            total = query_money_sum(self.conn, """SELECT a.amount_value FROM card_payment_allocations a
                JOIN card_payment_events e ON e.id=a.payment_event_id
                WHERE a.entry_payment_key=? AND e.event_type='discount'""", (key,))
            result[key] = exact_money(total, 'allocated total')
        return result

    def primary_income_total(self, month):
        self._check()
        return exact_money(query_money_sum(self.conn, """SELECT amount_value FROM cash_flows
            WHERE substr(occurred_on,1,7)=? AND is_primary_income=1 AND amount_value>0""", (month,)), 'primary_income_total')

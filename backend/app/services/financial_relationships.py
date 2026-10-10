"""Small persistent ownership contracts shared by reads and Snapshot boundaries.

Never repair data or derive identity from dates, amounts, or book location.
Historical unbatched events are not guessed into a payment workbench.
"""

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from app.services.legacy_recurring import validate_recurring_ownership, valid_nonnegative_money
from app.services.financial_inputs import FinancialInputScope, inputs_for


CARD_RELATIONSHIP_TABLES = (
    "ledger_entries", "card_payment_batches", "card_payment_batch_items",
    "card_payment_events", "card_payment_allocations", "cash_flows",
)


class CardOwnershipReadView(FinancialInputScope):
    """One connection/transaction's read-only card ownership validation scope.

    Only a successful, date/policy-independent canonical ownership check is
    remembered, not rows or projections. query_only prevents writes through
    aliases; a private savepoint proves that the original transaction survives
    (in_transaction/revision alone cannot detect commit/BEGIN or rollback ABA).
    Consumers receive only SELECT access. Nothing survives scope exit.
    """

    def __init__(self, conn: Any):
        if not conn.in_transaction:
            raise ValueError("card ownership read view requires an active transaction")
        self._conn = conn
        self._changes = conn.total_changes
        self._schema = conn.execute("PRAGMA schema_version").fetchone()[0]
        # TEMP can shadow an unqualified financial table without main DDL or
        # a changed total_changes counter, so it is part of the read identity.
        self._temp_schema = conn.execute("PRAGMA temp.schema_version").fetchone()[0]
        self._query_only = conn.execute("PRAGMA query_only").fetchone()[0]
        self._savepoint = f"card_read_{uuid4().hex}"
        self._active = False
        self._validated = False

    def _check(self) -> None:
        if (not self._active or not self._conn.in_transaction
                or self._changes != self._conn.total_changes):
            raise ValueError("card ownership read view ended or changed")

    def execute(self, sql: str, parameters: Any = ()) -> Any:
        self._check()
        if not sql.lstrip().upper().startswith("SELECT"):
            raise ValueError("card ownership read view only permits SELECT")
        return self._conn.execute(sql, parameters)

    def _check_metadata(self) -> None:
        self._check()
        if (self._conn.execute("PRAGMA query_only").fetchone()[0] != 1
                or self._conn.execute("PRAGMA schema_version").fetchone()[0] != self._schema
                or self._conn.execute("PRAGMA temp.schema_version").fetchone()[0] != self._temp_schema):
            raise ValueError("card ownership read view is no longer immutable")

    def validate_card_ownership(self) -> None:
        self._check_metadata()
        # RELEASE fails if an alias ended the original transaction, even when
        # it has already started a new transaction with identical rows/revision.
        self._conn.execute(f"RELEASE {self._savepoint}")
        self._conn.execute(f"SAVEPOINT {self._savepoint}")
        if not self._validated:
            _validate_card_payment_rows(self._conn)
            self._validated = True

    def financial_inputs(self):
        if not isinstance(self._conn, FinancialInputScope):
            return None  # default runtime: no extra metadata SQL for this hook
        self._check_metadata()
        return inputs_for(self._conn)


@contextmanager
def card_ownership_read_view(conn: Any):
    """Borrow, never commit/rollback, an existing transaction's immutable read.

    A borrowed write transaction may resume writing after this scope. Existing
    query_only/authorizer settings are preserved; no authorizer is replaced.
    """
    view = CardOwnershipReadView(conn)
    conn.execute(f"SAVEPOINT {view._savepoint}")
    try:
        conn.execute("PRAGMA query_only=ON")
        view._active = True
        yield view
        view._check_metadata()
    finally:
        try:
            conn.execute(f"RELEASE {view._savepoint}")
        finally:
            view._active = False
            view._validated = False
            conn.execute(f"PRAGMA query_only={view._query_only}")


def _by_id(rows: Sequence[Mapping[str, Any]], label: str) -> dict[Any, Mapping[str, Any]]:
    indexed = {row.get("id"): row for row in rows}
    if None in indexed or len(indexed) != len(rows):
        raise ValueError(f"duplicate or missing {label} identity")
    return indexed


def validate_card_payment_ownership(data: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    """Each ledger key has one batch owner; each allocation has one event.

    Distinct payments may allocate to the same ledger row, and one payment may
    allocate to several rows. Each (event, payment key) pair occurs once and
    belongs to that event's batch. A cash outflow cannot fund two events.
    """
    entries = _by_id(data.get("ledger_entries", ()), "ledger")
    batches = _by_id(data.get("card_payment_batches", ()), "card batch")
    events = _by_id(data.get("card_payment_events", ()), "card payment event")
    flows = _by_id(data.get("cash_flows", ()), "cash flow")
    if sum(row.get("status") == "active" for row in batches.values()) > 1:
        raise ValueError("multiple active card payment batches")
    keys = {row["payment_key"]: row for row in entries.values() if row.get("payment_key") is not None}
    if len(keys) != sum(row.get("payment_key") is not None for row in entries.values()):
        raise ValueError("duplicate ledger payment_key")
    items = _by_id(data.get("card_payment_batch_items", ()), "card batch item")
    owners: dict[str, Any] = {}
    owned_entries: set[Any] = set()
    for item in items.values():
        entry = entries.get(item.get("entry_id"))
        key, batch_id = item.get("entry_payment_key"), item.get("batch_id")
        if batch_id not in batches or entry is None or entry.get("entry_kind") == "planned":
            raise ValueError("card batch item has no valid batch or ledger entry")
        if not valid_nonnegative_money(entry.get("amount_value")):
            raise ValueError("card batch owned entry requires a nonnegative integer principal")
        if not key or key != entry.get("payment_key"):
            raise ValueError("card batch item payment key does not identify its ledger entry")
        if key in owners or entry["id"] in owned_entries:
            raise ValueError("duplicate card batch ownership")
        owners[key] = batch_id
        owned_entries.add(entry["id"])
    allocations = _by_id(data.get("card_payment_allocations", ()), "card payment allocation")
    pairs: set[tuple[Any, Any]] = set()
    totals: dict[Any, int] = {}
    for allocation in allocations.values():
        event_id, key = allocation.get("payment_event_id"), allocation.get("entry_payment_key")
        event, entry = events.get(event_id), keys.get(key)
        if event is None or entry is None or entry.get("entry_kind") == "planned":
            raise ValueError("card payment allocation has no valid event or ledger entry")
        pair = (event_id, key)
        if pair in pairs:
            raise ValueError("duplicate card payment allocation ownership")
        pairs.add(pair)
        if event.get("batch_id") is not None and owners.get(key) != event["batch_id"]:
            raise ValueError("card payment allocation does not belong to its event batch")
        amount = allocation.get("amount_value")
        if not valid_nonnegative_money(amount):
            raise ValueError("card payment allocation requires a nonnegative integer amount")
        totals[event_id] = totals.get(event_id, 0) + int(amount)
    cash_owners: set[Any] = set()
    for event_id, event in events.items():
        if event.get("batch_id") is not None and event["batch_id"] not in batches:
            raise ValueError("card payment event has no owning batch")
        if event.get("total_amount") != totals.get(event_id, 0):
            raise ValueError("card payment event total does not match allocations")
        flow_id = event.get("cash_flow_id")
        if flow_id is not None:
            if flow_id in cash_owners or flow_id not in flows:
                raise ValueError("card payment cash flow has no unique owning event")
            cash_owners.add(flow_id)
        if event.get("event_type") == "immediate":
            if event.get("total_amount", 0) > 0 and flow_id is None:
                raise ValueError("immediate card payment has no linked cash flow")
            if flow_id is not None and flows[flow_id].get("amount_value") != -event["total_amount"]:
                raise ValueError("immediate card payment does not match linked cash flow")


def validate_runtime_card_payment_ownership(conn: Any) -> None:
    if isinstance(conn, CardOwnershipReadView):
        conn.validate_card_ownership()
        return
    _validate_card_payment_rows(conn)


def _validate_card_payment_rows(conn: Any) -> None:
    inputs = inputs_for(conn)
    if inputs is not None:
        inputs.validate_card_ownership()
        return
    validate_card_payment_ownership({table: [dict(row) for row in conn.execute(f"SELECT * FROM {table}")]
                                     for table in CARD_RELATIONSHIP_TABLES})


def validate_runtime_recurring_ownership(conn: Any) -> None:
    inputs = inputs_for(conn)
    if inputs is not None:
        inputs.validate_recurring_ownership()
        return
    closed = conn.execute("SELECT value FROM app_settings WHERE key='last_closed_month'").fetchone()
    validate_recurring_ownership([dict(row) for row in conn.execute("SELECT * FROM ledger_entries")],
                                str(closed["value"]) if closed else "0000-00",
                                require_execution_epoch=False)
    # An unconfirmed historical template may carry a scheduled entry_date.
    # It still reserves its principal; it is not an active confirmation. v7
    # Snapshot admission retains the stricter execution-date/epoch contract.

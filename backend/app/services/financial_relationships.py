"""Small persistent ownership contracts shared by reads and Snapshot boundaries.

Never repair data or derive identity from dates, amounts, or book location.
Historical unbatched events are not guessed into a payment workbench.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from app.services.legacy_recurring import validate_recurring_ownership, valid_nonnegative_money


CARD_RELATIONSHIP_TABLES = (
    "ledger_entries", "card_payment_batches", "card_payment_batch_items",
    "card_payment_events", "card_payment_allocations", "cash_flows",
)


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
    validate_card_payment_ownership({table: [dict(row) for row in conn.execute(f"SELECT * FROM {table}")]
                                     for table in CARD_RELATIONSHIP_TABLES})


def validate_runtime_recurring_ownership(conn: Any) -> None:
    closed = conn.execute("SELECT value FROM app_settings WHERE key='last_closed_month'").fetchone()
    validate_recurring_ownership([dict(row) for row in conn.execute("SELECT * FROM ledger_entries")],
                                str(closed["value"]) if closed else "0000-00",
                                require_execution_epoch=False)
    # An unconfirmed historical template may carry a scheduled entry_date.
    # It still reserves its principal; it is not an active confirmation. v7
    # Snapshot admission retains the stricter execution-date/epoch contract.

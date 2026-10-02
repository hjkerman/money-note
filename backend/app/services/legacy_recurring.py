"""Conservative identity recovery for confirmed pre-v7 card recurring rows.

Historical Snapshots omitted the generated expense's source ID. Resolve the
relationship only while the original confirmation evidence is still present,
then persist the existing source_planned_entry_id. Mutable display fields must
never be consulted again to identify a relationship after that binding.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from math import isfinite
from typing import Any
from app.money import MAX_MONEY


def validate_source_epoch(source: Mapping[str, Any]) -> None:
    """An active source confirmation is a pair, never a truthy half-pair."""
    if (source.get("confirmed_month") is None) != (source.get("confirmed_at") is None):
        raise ValueError("partial recurring confirmation epoch is not a valid relationship")


def validate_recurring_ownership(
    entries: Sequence[Mapping[str, Any]], last_closed_month: str = "0000-00",
    *, require_execution_epoch: bool = True,
) -> None:
    """Validate canonical ownership without deriving identity from editable data.

    A closed epoch may survive on its generated expense after the template is
    reset or confirmed again. An unclosed epoch must still own the active
    confirmation. Legacy materialization, where provable, precedes this check.
    """
    sources = {row["id"]: row for row in entries if row.get("entry_kind") == "planned"}
    if len({row["id"] for row in entries}) != len(entries):
        raise ValueError("duplicate recurring ledger identity")
    owned: dict[tuple[Any, Any, Any], int] = {}
    for source in sources.values():
        validate_source_epoch(source)
        if require_execution_epoch and source.get("confirmed_month") is None and source.get("entry_date") is not None:
            raise ValueError("recurring confirmation has an execution date but no epoch")
    for row in entries:
        source_id = row.get("source_planned_entry_id")
        marked = source_id is not None or (row.get("entry_kind") == "expense" and (
            row.get("confirmed_month") is not None or row.get("confirmed_at") is not None
        ))
        if not marked:
            continue
        source = sources.get(source_id)
        if source is None or row.get("entry_kind") != "expense":
            raise ValueError("recurring confirmation generated expense has no valid source")
        principal = row.get("amount_value")
        if not valid_nonnegative_money(principal):
            raise ValueError("recurring generated expense requires a nonnegative integer principal")
        validate_source_epoch(row)
        period, timestamp = row.get("confirmed_month"), row.get("confirmed_at")
        if not isinstance(period, str) or not period or not isinstance(timestamp, str) or not timestamp:
            raise ValueError("recurring confirmation generated expense has no complete epoch")
        identity = (source_id, period, timestamp)
        owned[identity] = owned.get(identity, 0) + 1
        if owned[identity] != 1:
            raise ValueError("ambiguous recurring confirmation: duplicate generated ownership")
        if period > last_closed_month and (
            source.get("confirmed_month"), source.get("confirmed_at")
        ) != (period, timestamp):
            raise ValueError("recurring confirmation generated expense does not own the active source epoch")
    for source_id, source in sources.items():
        if source.get("confirmed_month") is not None and owned.get((
            source_id, source["confirmed_month"], source["confirmed_at"],
        ), 0) != 1:
            raise ValueError("recurring confirmation must own exactly one generated expense")


def valid_nonnegative_money(value: Any) -> bool:
    # Supported historical DBs retain REAL affinity even after integer-money
    # migration. 5000.0 is an integer principal; NULL, NaN and 5000.5 are not.
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and isfinite(value) and 0 <= value <= MAX_MONEY and value == int(value))


def near_confirmation_creation(created_at: Any, confirmed_at: Any) -> bool:
    """Historical INSERT and confirmation UPDATE occurred in one transaction.

    SQLite timestamps have second precision; allow a short statement boundary
    interval without treating a later edited display field as identity.
    """
    if not isinstance(created_at, str) or not isinstance(confirmed_at, str):
        return False
    try:
        return abs((datetime.fromisoformat(created_at) - datetime.fromisoformat(confirmed_at)).total_seconds()) <= 60
    except (TypeError, ValueError):
        return False


def infer_legacy_recurring_sources(entries: Sequence[Mapping[str, Any]]) -> dict[int, int]:
    """Return expense -> planned IDs supported by one unambiguous confirmation.

    A same-day second expense makes an older source-less relationship
    ambiguous, even if just one row still has the original title. Confirmation
    time is historical evidence that an expense was not edited after creation.
    """
    planned = [row for row in entries if row.get("book_section") == "current"
               and row.get("entry_kind") == "planned" and row.get("confirmed_month")
               and row.get("confirmed_at")]
    expenses = [row for row in entries if row.get("book_section") == "current"
                and row.get("entry_kind") == "expense" and row.get("entry_date")]
    explicit = {row.get("source_planned_entry_id") for row in expenses
                if row.get("source_planned_entry_id") is not None}
    unresolved = [row for row in expenses if row.get("source_planned_entry_id") is None]
    proposed: dict[int, list[int]] = {}
    for source in planned:
        if source["id"] in explicit:
            continue
        month = str(source["confirmed_month"])
        source_date = source.get("entry_date")
        # Historical generated rows were inserted in the same transaction as
        # confirmation. A later-edited generated row may have moved to a new
        # entry_date; do not bind a same-second manual row left in the old
        # month merely because that manual row still matches display fields.
        contemporaneous = [row for row in unresolved if near_confirmation_creation(
            row.get("created_at"), source.get("confirmed_at")
        )]
        if len(contemporaneous) > 1:
            continue
        same_period = [
            row for row in unresolved
            if str(row["entry_date"]).startswith(month)
            and (
                source_date is None or row["entry_date"] == source_date
                or (row.get("amount_value") == source.get("amount_value") and all(
                    (row.get(field) or "") == (source.get(field) or "")
                    for field in ("title", "usage_place", "usage_item")
                ))
            )
        ]
        if len(same_period) != 1:
            continue
        expense = same_period[0]
        if contemporaneous and contemporaneous[0]["id"] != expense["id"]:
            continue
        if not all((expense.get(field) or "") == (source.get(field) or "")
                   for field in ("title", "usage_place", "usage_item")):
            continue
        same_amount = expense.get("amount_value") == source.get("amount_value")
        explicit_actual_amount = (
            expense.get("amount_value") is not None
            and expense.get("amount_expr") == str(expense["amount_value"])
        )
        if not (same_amount or explicit_actual_amount):
            continue
        if expense.get("updated_at") != source.get("confirmed_at"):
            continue
        proposed.setdefault(int(expense["id"]), []).append(int(source["id"]))
    return {expense_id: sources[0] for expense_id, sources in proposed.items()
            if len(sources) == 1}


def materialize_recurring_confirmation_epochs(entries: Sequence[dict[str, Any]]) -> None:
    """Bind the original confirmation period/time before mutable edits.

    Existing epoch fields are immutable evidence, not recomputed from today's
    template. Older explicit source rows can be bound only while their original
    period still agrees and there is exactly one current generated expense.
    """
    by_id = {row.get("id"): row for row in entries}
    generated = [row for row in entries if row.get("book_section") == "current"
                 and row.get("entry_kind") == "expense" and row.get("source_planned_entry_id")]
    for row in generated:
        if row.get("confirmed_month") is not None or row.get("confirmed_at") is not None:
            continue
        source_id = row["source_planned_entry_id"]
        source = by_id.get(source_id)
        if (source and source.get("entry_kind") == "planned"
                and source.get("confirmed_month") and source.get("confirmed_at")
                and str(row.get("entry_date") or "").startswith(str(source["confirmed_month"]))
                and sum(other["source_planned_entry_id"] == source_id for other in generated) == 1):
            row["confirmed_month"] = source["confirmed_month"]
            row["confirmed_at"] = source["confirmed_at"]

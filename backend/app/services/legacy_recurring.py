"""Conservative identity recovery for confirmed pre-v7 card recurring rows.

Historical Snapshots omitted the generated expense's source ID. Resolve the
relationship only while the original confirmation evidence is still present,
then persist the existing source_planned_entry_id. Mutable display fields must
never be consulted again to identify a relationship after that binding.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any


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

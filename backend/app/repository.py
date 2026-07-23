"""Compatibility re-export layer for older imports.

New code should import from app.repositories.<domain> directly.
"""

from app.repositories.cash_flows import create_cash_flow, delete_cash_flow, list_cash_flows
from app.repositories.entries import (
    append_planned_entry,
    confirm_planned_entry,
    create_entry,
    delete_entry,
    delete_planned_entry,
    list_confirmed_planned_entries,
    list_entries,
    list_recent_closed_month_expense_counts,
    planned_entry_payment_date,
    reorder_current_entries,
    update_entry,
)
from app.repositories.labels import list_labels, upsert_label
from app.repositories.panels import (
    create_panel,
    delete_panel,
    delete_panels_by_type,
    list_panels,
    update_panel,
)
from app.repositories.settings import list_settings
from app.services.panels import complete_panels_by_type

__all__ = [
    "append_planned_entry",
    "complete_panels_by_type",
    "confirm_planned_entry",
    "create_cash_flow",
    "create_entry",
    "create_panel",
    "delete_cash_flow",
    "delete_entry",
    "delete_panel",
    "delete_panels_by_type",
    "delete_planned_entry",
    "list_cash_flows",
    "list_confirmed_planned_entries",
    "list_entries",
    "list_recent_closed_month_expense_counts",
    "list_labels",
    "list_panels",
    "list_settings",
    "planned_entry_payment_date",
    "reorder_current_entries",
    "update_entry",
    "update_panel",
    "upsert_label",
]

"""Synthetic comparison inputs only; not a new endpoint or formula engine."""

from calendar import monthrange
from datetime import date
import random
from unittest.mock import patch

from app.repositories.cash_flows import list_cash_flows
from app.repositories.entries import list_entries, list_confirmed_planned_entries, list_recent_closed_month_expense_counts
from app.repositories.panels import list_panels
from app.repositories.settings import list_settings
from app.services.card_charge.profiles import transit_discount_profile_status
from app.services.card_payments import current_payment_status, discount_month_status
from app.services.financial_relationships import card_ownership_read_view
from app.services.judgment import app_judgment
from app.services.month import month_close_status
from app.services.presentation import present_ledger_entries, present_monthly_panels
from app.services.summary import _summary_values_from_read_view


def projections(conn, today=date(2026, 10, 5)):
    """Same 12 financial projections, no Snapshot or full-bundle construction.

    Existing functions compute every value. Legacy conn = full-state oracle;
    explicit BoundedInputs = isolated measured path. No new client protocol.
    """
    month = today.strftime("%Y-%m")
    settings = list_settings(conn)
    start, end = date(today.year, today.month, 1), date(today.year, today.month, monthrange(today.year, today.month)[1])
    recent = date(today.year-1, 12, 1) if today.month == 1 else date(today.year, today.month-1, 1)
    with patch("app.services.judgment.common._MESSAGE_RANDOM", random.Random(662602)), card_ownership_read_view(conn) as view:
        entries = list_entries("current", today=today, conn=view)
        panels = list_panels(month, include_confirmed_fixed=True, conn=view)
        summary = _summary_values_from_read_view(view, today=today, visible_current_entries=entries)
        payment = current_payment_status(today, conn=view)
        return dict(entries=present_ledger_entries(entries, conn=view, today=today, settings=settings),
                    panels=present_monthly_panels(panels, conn=view, today=today, settings=settings),
                    summary=summary, card_payment_status=payment,
                    judgment=app_judgment(entries, list_panels(month, conn=view), list_cash_flows(start, end, conn=view),
                                          summary, payment, settings, list_recent_closed_month_expense_counts(conn=view), today=today),
                    confirmed_planned_entries=present_ledger_entries(list_confirmed_planned_entries(today, conn=view),
                                                                      conn=view, today=today, settings=settings),
                    cash_flows=list_cash_flows(recent, end, conn=view), settings=settings,
                    month_close_status=month_close_status(today, conn=view, timezone_offset_minutes=540),
                    owner_discount_month=discount_month_status(month, "owner", conn=view),
                    family_discount_month=discount_month_status(month, "family", conn=view),
                    transit_discount_profile=transit_discount_profile_status(month, conn=view))

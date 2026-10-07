from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Any
from app.money import exact_money, money_sum, query_money_sum, allocation_totals

from app.db import session
from app.repositories.entries import list_entries
from app.repositories.settings import list_settings
from app.services.card_charge import (
    DiscountCard,
    evaluate_stored_charge,
    normalize_discount_policy,
)
from app.services.card_payments import active_card_payment_unpaid_total
from app.services.clock import app_today
from app.services.financial_relationships import card_ownership_read_view


def current_summary_values() -> dict[str, int]:
    with session(transaction_mode="DEFERRED") as conn:
        return _current_summary_values(conn)


def _current_summary_values(conn: Any) -> dict[str, int]:
    # All downstream reads share the existing transaction, but only the pure
    # card ownership validator is reused. Date/policy-sensitive values are
    # still computed normally, and borrowed writers regain write access on exit.
    if not conn.in_transaction:
        # Existing diagnostic callers may borrow an autocommit connection.
        # No immutable snapshot is established there, so never reuse a PASS.
        return _summary_values_from_read_view(conn)
    with card_ownership_read_view(conn) as view:
        return _summary_values_from_read_view(view)


def _summary_values_from_read_view(conn: Any, *, today: date | None = None,
                                   visible_current_entries: list[dict[str, Any]] | None = None) -> dict[str, int]:
    if visible_current_entries is None:
        visible_current_entries = list_entries("current", today=today, conn=conn)
    current_entries = [
        entry for entry in visible_current_entries if entry.get("entry_kind") != "planned"
    ]
    planned_entries = [
        entry for entry in visible_current_entries if entry.get("entry_kind") == "planned"
    ]
    entry_card_total = money_sum(entry.get("amount_value") for entry in current_entries)
    planned_liquidity_total = money_sum(entry.get("amount_value") for entry in planned_entries)
    planned_recurring_total = planned_entry_total(conn)
    entry_discount_total = current_entry_discount_total(conn)
    card_total = max(0, entry_card_total - entry_discount_total)
    active_card_payment_unpaid = active_card_payment_unpaid_total(today=today, conn=conn)
    fixed_panel_total = panel_total("fixed", conn=conn)
    fixed_cash_processed_total = processed_fixed_cash_total(conn)
    pending_fixed_panel_total = panel_total("fixed", only_unconfirmed=True, conn=conn)
    transfer_or_deposit_total = fixed_panel_total + planned_recurring_total
    liquidity_fixed_total = pending_fixed_panel_total + planned_liquidity_total
    frozen_asset_total = panel_total("frozen", conn=conn)
    scheduled_income = setting_float("scheduled_income", conn)
    cash_flow_balance = setting_float("cash_flow_balance", conn) + cash_flow_total(conn, today=today)
    remaining_liquidity = (
        scheduled_income
        + cash_flow_balance
        - card_total
        - active_card_payment_unpaid
        - liquidity_fixed_total
        - frozen_asset_total
    )
    # remaining_liquidity reserves only unconfirmed cash-fixed templates. A
    # confirmed template has already produced its actual cash outflow, but its
    # next occurrence still needs the template reserve in the prefunded cycle.
    # Keep exactly one forward reserve per template; never re-subtract the
    # unconfirmed part already present in remaining_liquidity.
    # An early next-period transfer replaces that period's reserve with an
    # actual outflow. Reserve its following occurrence at the calendar boundary.
    early_fixed_total = query_money_sum(conn,
        """SELECT amount_value FROM monthly_panels
           WHERE panel_type = 'fixed' AND confirmed_at IS NOT NULL
             AND confirmed_cash_flow_id IS NOT NULL AND confirmed_month > ?""",
        ((today or app_today()).strftime("%Y-%m"),),
    )
    current_month_spendable = remaining_liquidity - (
        fixed_panel_total - pending_fixed_panel_total - int(early_fixed_total)
    )
    values = {
        "scheduled_income": int(scheduled_income),
        "cash_flow_balance": int(cash_flow_balance),
        "remaining_liquidity": int(remaining_liquidity),
        "current_month_spendable": int(current_month_spendable),
        "current_spending_total": int(entry_card_total),
        "current_discount_total": int(entry_discount_total),
        "card_total": int(card_total),
        "planned_recurring_total": int(planned_recurring_total),
        "fixed_cash_total": int(fixed_panel_total),
        "fixed_cash_processed_total": int(fixed_cash_processed_total),
        "transfer_or_deposit_total": int(transfer_or_deposit_total),
        "frozen_asset_total": int(frozen_asset_total),
        "claim_original_total": int(panel_total("claim", conn=conn)),
        "claim_net_total": int(panel_net_total("claim", conn)),
        "family_card_original_total": int(panel_total("family_card", conn=conn)),
        "family_card_net_total": int(panel_net_total("family_card", conn)),
        "visible_cash_flow_total": int(visible_cash_flow_total(conn, today=today)),
    }
    return {key: exact_money(value, key) for key, value in values.items()}


def planned_entry_total(conn: Any | None = None) -> int:
    """확인 여부와 무관한 월 반복 카드 정기결제 총액이다."""
    if conn is None:
        with session() as owned_conn:
            return planned_entry_total(owned_conn)
    return query_money_sum(conn,
        """
        SELECT amount_value
        FROM ledger_entries
        WHERE book_section = 'current'
          AND entry_kind = 'planned'
        """
    )


def panel_total(
    panel_type: str,
    *,
    only_unconfirmed: bool = False,
    conn: Any | None = None,
) -> int:
    confirmation_filter = (
        " AND (confirmed_at IS NULL OR confirmed_cash_flow_id IS NULL)"
        if only_unconfirmed
        else ""
    )
    if conn is None:
        with session() as owned_conn:
            return panel_total(panel_type, only_unconfirmed=only_unconfirmed, conn=owned_conn)
    return query_money_sum(conn,
        f"SELECT amount_value FROM monthly_panels WHERE panel_type = ?{confirmation_filter}",
        (panel_type,),
    )


def processed_fixed_cash_total(conn: Any) -> int:
    """Confirmed fixed expenses' actual cash outflow, not template reserve."""
    return -query_money_sum(conn,
        """
        SELECT cash_flows.amount_value
        FROM monthly_panels
        JOIN cash_flows ON cash_flows.id = monthly_panels.confirmed_cash_flow_id
        WHERE monthly_panels.panel_type = 'fixed'
          AND monthly_panels.confirmed_at IS NOT NULL
        """
    )


def panel_net_total(panel_type: str, conn: Any | None = None) -> int:
    if conn is None:
        with session() as owned_conn:
            return panel_net_total(panel_type, owned_conn)
    settings = list_settings(conn)
    rows = conn.execute(
        "SELECT month, title, amount_value, discount_amount, discount_override FROM monthly_panels WHERE panel_type = ?",
        (panel_type,),
    ).fetchall()
    return sum(
        _panel_effective_amount(row, panel_type, settings)
        for row in rows
    )


def current_entry_discount_total(conn: Any | None = None) -> int:
    if conn is None:
        with session() as owned_conn:
            return current_entry_discount_total(owned_conn)
    settings = list_settings(conn)
    rows = conn.execute(
        """
        SELECT ledger_entries.payment_key,
               ledger_entries.amount_value,
               ledger_entries.entry_date,
               ledger_entries.title,
               ledger_entries.usage_place,
               ledger_entries.spending_category,
               ledger_entries.discount_override,
               ledger_entries.aux_amount_value
        FROM ledger_entries
        WHERE ledger_entries.book_section = 'current'
          AND ledger_entries.entry_kind != 'planned'
          AND ledger_entries.payment_key IS NOT NULL
        """
    ).fetchall()
    discounts = allocation_totals(conn, 'discount')
    rows = [{**dict(row), 'override_discount_amount': discounts.get(row['payment_key'], 0)}
            for row in rows]
    return sum(
        evaluate_stored_charge(
            row["amount_value"],
            _manual_entry_discount(row),
            bool(row["discount_override"] or row["override_discount_amount"] or row["aux_amount_value"]),
            normalize_discount_policy(
                settings.get(
                    f"card_discount_policy:owner:{str(row['entry_date'] or '')[:7]}"
                ),
                "owner",
            ),
            str(row["entry_date"] or "")[:7],
            row["title"],
            DiscountCard.OWNER,
            merchant=row["usage_place"],
            spending_category=row["spending_category"],
            settings=settings,
        ).effective_discount_amount
        for row in rows
    )


def _panel_effective_amount(
    row: object,
    panel_type: str,
    settings: dict[str, str],
) -> int:
    if panel_type not in {"claim", "family_card"}:
        return max(0, exact_money(row["amount_value"] or 0))
    scope = "family" if panel_type == "family_card" else "owner"
    card = DiscountCard.FAMILY if panel_type == "family_card" else DiscountCard.OWNER
    policy = normalize_discount_policy(
        settings.get(f"card_discount_policy:{scope}:{row['month']}"),
        scope,
    )
    return evaluate_stored_charge(
        row["amount_value"],
        row["discount_amount"],
        bool(row["discount_override"] or row["discount_amount"]),
        policy,
        str(row["month"] or ""),
        row["title"],
        card,
        settings=settings,
    ).effective_amount


def _manual_entry_discount(row: object) -> int:
    if row["discount_override"] and row["aux_amount_value"] is not None:
        return exact_money(row["aux_amount_value"] or 0)
    return exact_money(row["override_discount_amount"] or 0)


def setting_float(key: str, conn: Any | None = None) -> int:
    # Retain the internal helper name for callers; its money result is exact.
    if conn is None:
        with session() as owned_conn:
            return setting_float(key, owned_conn)
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return 0
    return exact_money(row["value"], key)


def setting_text(key: str, fallback: str = "", conn: Any | None = None) -> str:
    if conn is None:
        with session() as owned_conn:
            return setting_text(key, fallback, owned_conn)
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row is not None else fallback


def cash_flow_total(conn: Any | None = None, *, today: date | None = None) -> int:
    cutoff = (today or app_today()).isoformat()
    if conn is None:
        with session() as owned_conn:
            return cash_flow_total(owned_conn, today=today)
    return query_money_sum(conn,
        """
        SELECT amount_value
        FROM cash_flows
        WHERE occurred_on <= ?
        """,
        (cutoff,),
    )


def visible_cash_flow_total(conn: Any | None = None, *, today: date | None = None) -> int:
    """웹/모바일 기본 목록과 같은 직전 월 1일부터 당월 말일까지의 현금흐름 합계다."""
    day = today or app_today()
    if day.month == 1:
        date_from = f"{day.year - 1}-12-01"
    else:
        date_from = f"{day.year}-{day.month - 1:02d}-01"
    date_to = f"{day.year}-{day.month:02d}-{monthrange(day.year, day.month)[1]:02d}"
    if conn is None:
        with session() as owned_conn:
            return visible_cash_flow_total(owned_conn, today=today)
    return query_money_sum(conn,
        """
        SELECT amount_value
        FROM cash_flows
        WHERE occurred_on BETWEEN ? AND ?
        """,
        (date_from, date_to),
    )

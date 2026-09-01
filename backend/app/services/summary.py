from __future__ import annotations

from calendar import monthrange
from typing import Any

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


def current_summary_values() -> dict[str, int]:
    with session(transaction_mode="DEFERRED") as conn:
        return _current_summary_values(conn)


def _current_summary_values(conn: Any) -> dict[str, int]:
    visible_current_entries = list_entries("current", conn=conn)
    current_entries = [
        entry for entry in visible_current_entries if entry.get("entry_kind") != "planned"
    ]
    planned_entries = [
        entry for entry in visible_current_entries if entry.get("entry_kind") == "planned"
    ]
    entry_card_total = sum(entry.get("amount_value") or 0 for entry in current_entries)
    planned_liquidity_total = sum(entry.get("amount_value") or 0 for entry in planned_entries)
    planned_recurring_total = planned_entry_total(conn)
    entry_discount_total = current_entry_discount_total(conn)
    card_total = max(0, entry_card_total - entry_discount_total)
    active_card_payment_unpaid = active_card_payment_unpaid_total(conn=conn)
    fixed_panel_total = panel_total("fixed", conn=conn)
    pending_fixed_panel_total = panel_total("fixed", only_unconfirmed=True, conn=conn)
    transfer_or_deposit_total = fixed_panel_total + planned_recurring_total
    liquidity_fixed_total = pending_fixed_panel_total + planned_liquidity_total
    frozen_asset_total = panel_total("frozen", conn=conn)
    scheduled_income = setting_float("scheduled_income", conn)
    cash_flow_balance = setting_float("cash_flow_balance", conn) + cash_flow_total(conn)
    remaining_liquidity = (
        scheduled_income
        + cash_flow_balance
        - card_total
        - active_card_payment_unpaid
        - liquidity_fixed_total
        - frozen_asset_total
    )
    return {
        "scheduled_income": int(scheduled_income),
        "cash_flow_balance": int(cash_flow_balance),
        "remaining_liquidity": int(remaining_liquidity),
        "current_spending_total": int(entry_card_total),
        "current_discount_total": int(entry_discount_total),
        "card_total": int(card_total),
        "planned_recurring_total": int(planned_recurring_total),
        "fixed_cash_total": int(fixed_panel_total),
        "transfer_or_deposit_total": int(transfer_or_deposit_total),
        "frozen_asset_total": int(frozen_asset_total),
        "claim_original_total": int(panel_total("claim", conn=conn)),
        "claim_net_total": int(panel_net_total("claim", conn)),
        "family_card_original_total": int(panel_total("family_card", conn=conn)),
        "family_card_net_total": int(panel_net_total("family_card", conn)),
        "visible_cash_flow_total": int(visible_cash_flow_total(conn)),
    }


def planned_entry_total(conn: Any | None = None) -> float:
    """확인 여부와 무관한 월 반복 카드 정기결제 총액이다."""
    if conn is None:
        with session() as owned_conn:
            return planned_entry_total(owned_conn)
    row = conn.execute(
        """
        SELECT COALESCE(SUM(amount_value), 0) AS total
        FROM ledger_entries
        WHERE book_section = 'current'
          AND entry_kind = 'planned'
        """
    ).fetchone()
    return float(row["total"])


def panel_total(
    panel_type: str,
    *,
    only_unconfirmed: bool = False,
    conn: Any | None = None,
) -> float:
    confirmation_filter = (
        " AND (confirmed_at IS NULL OR confirmed_cash_flow_id IS NULL)"
        if only_unconfirmed
        else ""
    )
    if conn is None:
        with session() as owned_conn:
            return panel_total(panel_type, only_unconfirmed=only_unconfirmed, conn=owned_conn)
    row = conn.execute(
        f"SELECT COALESCE(SUM(amount_value), 0) AS total FROM monthly_panels WHERE panel_type = ?{confirmation_filter}",
        (panel_type,),
    ).fetchone()
    return float(row["total"])


def panel_net_total(panel_type: str, conn: Any | None = None) -> float:
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


def current_entry_discount_total(conn: Any | None = None) -> float:
    if conn is None:
        with session() as owned_conn:
            return current_entry_discount_total(owned_conn)
    settings = list_settings(conn)
    rows = conn.execute(
        """
        SELECT ledger_entries.amount_value,
               ledger_entries.entry_date,
               ledger_entries.title,
               ledger_entries.usage_place,
               ledger_entries.spending_category,
               ledger_entries.discount_override,
               ledger_entries.aux_amount_value,
               COALESCE(SUM(CASE WHEN card_payment_events.event_type = 'discount'
                                 THEN card_payment_allocations.amount_value ELSE 0 END), 0) AS override_discount_amount
        FROM ledger_entries
        LEFT JOIN card_payment_allocations
          ON card_payment_allocations.entry_payment_key = ledger_entries.payment_key
        LEFT JOIN card_payment_events
          ON card_payment_events.id = card_payment_allocations.payment_event_id
        WHERE ledger_entries.book_section = 'current'
          AND ledger_entries.entry_kind != 'planned'
          AND ledger_entries.payment_key IS NOT NULL
        GROUP BY ledger_entries.id
        """
    ).fetchall()
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
        return max(0, int(row["amount_value"] or 0))
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


def _manual_entry_discount(row: object) -> float:
    if row["discount_override"] and row["aux_amount_value"] is not None:
        return float(row["aux_amount_value"] or 0)
    return float(row["override_discount_amount"] or 0)


def setting_float(key: str, conn: Any | None = None) -> float:
    if conn is None:
        with session() as owned_conn:
            return setting_float(key, owned_conn)
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return 0.0
    return float(row["value"])


def setting_text(key: str, fallback: str = "", conn: Any | None = None) -> str:
    if conn is None:
        with session() as owned_conn:
            return setting_text(key, fallback, owned_conn)
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row is not None else fallback


def cash_flow_total(conn: Any | None = None) -> float:
    today = app_today().isoformat()
    if conn is None:
        with session() as owned_conn:
            return cash_flow_total(owned_conn)
    row = conn.execute(
        """
        SELECT COALESCE(SUM(amount_value), 0) AS total
        FROM cash_flows
        WHERE occurred_on <= ?
        """,
        (today,),
    ).fetchone()
    return float(row["total"])


def visible_cash_flow_total(conn: Any | None = None) -> float:
    """웹/모바일 기본 목록과 같은 직전 월 1일부터 당월 말일까지의 현금흐름 합계다."""
    today = app_today()
    if today.month == 1:
        date_from = f"{today.year - 1}-12-01"
    else:
        date_from = f"{today.year}-{today.month - 1:02d}-01"
    date_to = f"{today.year}-{today.month:02d}-{monthrange(today.year, today.month)[1]:02d}"
    if conn is None:
        with session() as owned_conn:
            return visible_cash_flow_total(owned_conn)
    row = conn.execute(
        """
        SELECT COALESCE(SUM(amount_value), 0) AS total
        FROM cash_flows
        WHERE occurred_on BETWEEN ? AND ?
        """,
        (date_from, date_to),
    ).fetchone()
    return float(row["total"])

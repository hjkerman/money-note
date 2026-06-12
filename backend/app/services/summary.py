from __future__ import annotations

from app.db import session
from app.repository import list_entries, list_installments
from app.services.discounts import effective_card_discount, normalize_discount_policy


def current_summary_values() -> dict[str, float]:
    visible_current_entries = list_entries("current")
    current_entries = [entry for entry in visible_current_entries if entry.get("entry_kind") != "planned"]
    planned_entries = [entry for entry in visible_current_entries if entry.get("entry_kind") == "planned"]
    entry_card_total = sum(entry.get("amount_value") or 0 for entry in current_entries)
    planned_liquidity_total = sum(entry.get("amount_value") or 0 for entry in planned_entries)
    planned_recurring_total = planned_entry_total()
    entry_discount_total = current_entry_discount_total()
    installment_monthly_total = sum(row.get("monthly_amount") or 0 for row in list_installments())
    card_total = max(0.0, entry_card_total - entry_discount_total) + installment_monthly_total
    fixed_panel_total = panel_total("fixed")
    transfer_or_deposit_total = fixed_panel_total + planned_recurring_total
    liquidity_fixed_total = fixed_panel_total + planned_liquidity_total
    frozen_asset_total = panel_total("frozen")
    base_next_month_liquidity = setting_float("base_next_month_liquidity")
    interest_expense = setting_float("interest_expense")
    liquidity_status = setting_float("liquidity_status") + cash_flow_total()
    return {
        "base_next_month_liquidity": base_next_month_liquidity,
        "card_total": card_total,
        "installment_monthly_total": installment_monthly_total,
        "planned_recurring_total": planned_recurring_total,
        "transfer_or_deposit_total": transfer_or_deposit_total,
        "interest_expense": interest_expense,
        "frozen_asset_total": frozen_asset_total,
        "liquidity_status": liquidity_status,
        "next_month_liquidity": base_next_month_liquidity
        - card_total
        - liquidity_fixed_total
        - interest_expense
        - frozen_asset_total
        + liquidity_status,
    }


def planned_entry_total() -> float:
    """확인 여부와 무관한 월 반복 카드 정기결제 총액이다."""
    with session() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount_value), 0) AS total
            FROM ledger_entries
            WHERE book_section = 'current'
              AND entry_kind = 'planned'
            """
        ).fetchone()
    return float(row["total"])


def panel_total(panel_type: str) -> float:
    with session() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount_value), 0) AS total FROM monthly_panels WHERE panel_type = ?",
            (panel_type,),
        ).fetchone()
    return float(row["total"])


def panel_net_total(panel_type: str) -> float:
    with session() as conn:
        rows = conn.execute(
            "SELECT month, amount_value, discount_amount, discount_override FROM monthly_panels WHERE panel_type = ?",
            (panel_type,),
        ).fetchall()
    return sum(
        max(
            0.0,
            float(row["amount_value"] or 0)
            - (
                effective_card_discount(
                    row["amount_value"],
                    row["discount_amount"],
                    bool(row["discount_override"] or row["discount_amount"]),
                    normalize_discount_policy(
                        setting_text(
                            f"card_discount_policy:{'family' if panel_type == 'family_card' else 'owner'}:{row['month']}",
                            "disabled" if panel_type == "family_card" else "enabled",
                        ),
                        "family" if panel_type == "family_card" else "owner",
                    )
                    if panel_type in {"claim", "family_card"}
                    else "disabled",
                )
                if panel_type in {"claim", "family_card"}
                else 0.0
            ),
        )
        for row in rows
    )


def current_entry_discount_total() -> float:
    with session() as conn:
        rows = conn.execute(
            """
            SELECT ledger_entries.amount_value,
                   ledger_entries.entry_date,
                   ledger_entries.discount_override,
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
        effective_card_discount(
            row["amount_value"],
            row["override_discount_amount"],
            bool(row["discount_override"] or row["override_discount_amount"]),
            setting_text(f"card_discount_policy:owner:{str(row['entry_date'] or '')[:7]}", "enabled"),
        )
        for row in rows
    )


def setting_float(key: str) -> float:
    with session() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return 0.0
    return float(row["value"])


def setting_text(key: str, fallback: str = "") -> str:
    with session() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row is not None else fallback


def cash_flow_total() -> float:
    with session() as conn:
        row = conn.execute("SELECT COALESCE(SUM(amount_value), 0) AS total FROM cash_flows").fetchone()
    return float(row["total"])

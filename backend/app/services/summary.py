from __future__ import annotations

from app.db import session
from app.repository import list_entries, list_installments
from app.services.discounts import effective_card_discount


def current_summary_values() -> dict[str, float]:
    current_entries = [entry for entry in list_entries("current") if entry.get("entry_kind") != "planned"]
    entry_card_total = sum(entry.get("amount_value") or 0 for entry in current_entries)
    entry_discount_total = current_entry_discount_total()
    installment_monthly_total = sum(row.get("monthly_amount") or 0 for row in list_installments())
    card_total = max(0.0, entry_card_total - entry_discount_total) + installment_monthly_total
    transfer_or_deposit_total = panel_total("fixed")
    frozen_asset_total = panel_total("frozen")
    base_next_month_liquidity = setting_float("base_next_month_liquidity")
    interest_expense = setting_float("interest_expense")
    liquidity_status = setting_float("liquidity_status") + cash_flow_total()
    return {
        "base_next_month_liquidity": base_next_month_liquidity,
        "card_total": card_total,
        "installment_monthly_total": installment_monthly_total,
        "transfer_or_deposit_total": transfer_or_deposit_total,
        "interest_expense": interest_expense,
        "frozen_asset_total": frozen_asset_total,
        "liquidity_status": liquidity_status,
        "next_month_liquidity": base_next_month_liquidity
        - card_total
        - transfer_or_deposit_total
        - interest_expense
        - frozen_asset_total
        + liquidity_status,
    }


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
                    setting_text(
                        f"card_discount_policy:{'family' if panel_type == 'settlement' else 'owner'}:{row['month']}",
                        "undecided",
                    )
                    if panel_type in {"claim", "settlement"}
                    else "disabled",
                )
                if panel_type in {"claim", "settlement"}
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
            setting_text(f"card_discount_policy:owner:{str(row['entry_date'] or '')[:7]}", "undecided"),
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

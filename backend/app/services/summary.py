from __future__ import annotations

from app.db import session
from app.repository import list_entries


def current_summary_values() -> dict[str, float]:
    current_entries = list_entries("current")
    card_total = sum(entry.get("amount_value") or 0 for entry in current_entries)
    transfer_or_deposit_total = panel_total("fixed")
    frozen_asset_total = panel_total("frozen")
    base_next_month_liquidity = setting_float("base_next_month_liquidity")
    interest_expense = setting_float("interest_expense")
    liquidity_status = setting_float("liquidity_status") + cash_flow_total()
    return {
        "base_next_month_liquidity": base_next_month_liquidity,
        "card_total": card_total,
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


def setting_float(key: str) -> float:
    with session() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return 0.0
    return float(row["value"])


def cash_flow_total() -> float:
    with session() as conn:
        row = conn.execute("SELECT COALESCE(SUM(amount_value), 0) AS total FROM cash_flows").fetchone()
    return float(row["total"])

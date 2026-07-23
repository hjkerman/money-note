from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from app.db import session
from app.repositories.settings import list_settings
from app.services.clock import app_today
from app.services.discounts import (
    default_card_discount,
    discount_ineligible_title,
    effective_card_discount,
    normalize_discount_policy,
    toll_title,
    transport_title,
)


def present_ledger_entries(entries: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """원장 행에 서버가 확정한 할인/실결제 표시값을 덧붙인다."""
    rows = [dict(entry) for entry in entries]
    settings = list_settings()
    event_discounts = _legacy_entry_discount_events(rows)
    return [
        present_ledger_entry(entry, settings=settings, event_discounts=event_discounts)
        for entry in rows
    ]


def present_ledger_entry(
    entry: Mapping[str, Any],
    *,
    settings: Mapping[str, str] | None = None,
    event_discounts: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """단일 원장 행의 할인 정책과 최종 금액을 서버 기준으로 계산한다."""
    data = dict(entry)
    settings = settings or list_settings()
    event_discounts = event_discounts or {}
    month = str(data.get("entry_date") or app_today().isoformat())[:7]
    policy = normalize_discount_policy(
        settings.get(f"card_discount_policy:owner:{month}"),
        "owner",
    )
    payment_key = str(data.get("payment_key") or "")
    amount = int(data.get("amount_value") or 0)
    is_card_expense = data.get("entry_kind") != "planned" and bool(payment_key)
    automatic_eligible = is_card_expense and not discount_ineligible_title(data.get("title"))
    automatic_discount = default_card_discount(amount) if automatic_eligible else 0
    legacy_discount = int(event_discounts.get(payment_key, 0))
    override_enabled = bool(
        data.get("discount_override")
        or legacy_discount
        or data.get("aux_amount_value")
    )
    if data.get("discount_override") and data.get("aux_amount_value") is not None:
        override_discount = int(data.get("aux_amount_value") or 0)
    else:
        override_discount = legacy_discount
    effective_discount = (
        effective_card_discount(
            amount,
            override_discount,
            override_enabled,
            policy,
            data.get("title"),
        )
        if is_card_expense
        else 0
    )
    data.update(
        {
            "discount_policy": policy,
            "automatic_discount_eligible": automatic_eligible,
            "automatic_discount_amount": automatic_discount,
            "effective_discount_amount": effective_discount,
            "effective_amount_value": (
                max(0, amount - effective_discount)
                if data.get("amount_value") is not None
                else None
            ),
            "is_transport": transport_title(data.get("title")),
            "is_toll": toll_title(data.get("title")),
        }
    )
    return data


def present_monthly_panels(panels: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """월별 패널 행에 서버가 확정한 할인/실결제 표시값을 덧붙인다."""
    settings = list_settings()
    return [present_monthly_panel(panel, settings=settings) for panel in panels]


def present_monthly_panel(
    panel: Mapping[str, Any],
    *,
    settings: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """단일 패널 행의 할인 정책과 최종 금액을 서버 기준으로 계산한다."""
    data = dict(panel)
    settings = settings or list_settings()
    panel_type = str(data.get("panel_type") or "")
    scope = "family" if panel_type == "family_card" else "owner"
    month = str(data.get("month") or app_today().strftime("%Y-%m"))
    policy = normalize_discount_policy(
        settings.get(f"card_discount_policy:{scope}:{month}"),
        scope,
    )
    amount = int(data.get("amount_value") or 0)
    is_card_panel = panel_type in {"claim", "family_card"}
    automatic_eligible = is_card_panel and not discount_ineligible_title(data.get("title"))
    automatic_discount = default_card_discount(amount) if automatic_eligible else 0
    effective_discount = (
        effective_card_discount(
            amount,
            int(data.get("discount_amount") or 0),
            bool(data.get("discount_override") or data.get("discount_amount")),
            policy,
            data.get("title"),
        )
        if is_card_panel
        else 0
    )
    data.update(
        {
            "discount_policy": policy,
            "automatic_discount_eligible": automatic_eligible,
            "automatic_discount_amount": automatic_discount,
            "effective_discount_amount": effective_discount,
            "effective_amount_value": (
                max(0, amount - effective_discount)
                if data.get("amount_value") is not None
                else None
            ),
        }
    )
    return data


def _legacy_entry_discount_events(entries: list[dict[str, Any]]) -> dict[str, int]:
    payment_keys = {
        str(entry["payment_key"])
        for entry in entries
        if entry.get("payment_key")
    }
    if not payment_keys:
        return {}
    placeholders = ", ".join("?" for _ in payment_keys)
    with session() as conn:
        rows = conn.execute(
            f"""
            SELECT card_payment_allocations.entry_payment_key,
                   COALESCE(SUM(card_payment_allocations.amount_value), 0) AS amount
            FROM card_payment_allocations
            JOIN card_payment_events
              ON card_payment_events.id = card_payment_allocations.payment_event_id
            WHERE card_payment_events.event_type = 'discount'
              AND card_payment_allocations.entry_payment_key IN ({placeholders})
            GROUP BY card_payment_allocations.entry_payment_key
            """,
            tuple(payment_keys),
        ).fetchall()
    return {
        str(row["entry_payment_key"]): int(row["amount"] or 0)
        for row in rows
    }

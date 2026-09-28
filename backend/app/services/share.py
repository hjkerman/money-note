from __future__ import annotations

from collections.abc import Mapping

from app.repositories.cash_flows import list_cash_flows
from app.repositories.entries import list_entries
from app.repositories.labels import list_labels
from app.repositories.panels import list_panels
from app.repositories.settings import list_settings
from app.services.card_charge import DiscountCard, evaluate_stored_charge, normalize_discount_policy
from app.services.judgment import claim_ledger_note, shared_panel_subtitle
from app.services.month import calendar_month_label
from app.services.share_html import render_panel_row, render_shared_panel_html


PANEL_TITLES = {
    "claim": ("panel_claim_title", "청구"),
    "family_card": ("panel_family_card_title", "가족카드"),
}


def shared_panel(panel_type: str) -> dict:
    if panel_type not in PANEL_TITLES:
        raise ValueError("unknown shared panel type")
    month = calendar_month_label()
    rows = [
        panel
        for panel in list_panels(month)
        if panel.get("panel_type") == panel_type and panel.get("title")
    ]
    settings = list_settings()
    total = sum(_panel_net_amount(row, settings) for row in rows)
    discount_total = sum(_panel_discount_amount(row, settings) for row in rows)
    minimum_payment_month, minimum_rows = _minimum_payment_rows(rows, month)
    minimum_total = sum(_panel_net_amount(row, settings) for row in minimum_rows)
    minimum_discount_total = sum(
        _panel_discount_amount(row, settings) for row in minimum_rows
    )
    current_card_total = sum(row.get("amount_value") or 0 for row in list_entries("current"))
    card_limit = _float_setting(settings, "card_limit", 5_800_000)
    label_key, fallback = PANEL_TITLES[panel_type]
    title = list_labels().get(label_key, fallback)
    return {
        "month": month,
        "panel_type": panel_type,
        "title": title,
        "subtitle": shared_panel_subtitle(panel_type, rows, total, current_card_total, card_limit),
        "ledger_note": _ledger_note(panel_type, month),
        "rows": rows,
        "total": total,
        "discount_total": discount_total,
        "minimum_payment_month": minimum_payment_month,
        "minimum_total": minimum_total,
        "minimum_discount_total": minimum_discount_total,
    }


def shared_panel_html(panel_type: str) -> str:
    data = shared_panel(panel_type)
    settings = list_settings()
    rows_html = "\n".join(
        _row_html(
            row,
            data["minimum_payment_month"],
            data["month"],
            settings,
        )
        for row in data["rows"]
    )
    if not rows_html:
        rows_html = '<tr><td colspan="4" class="empty">표시할 항목이 없습니다.</td></tr>'
    net_total = sum(_panel_net_amount(row, settings) for row in data["rows"])
    discount_total = sum(
        _panel_discount_amount(row, settings) for row in data["rows"]
    )
    return render_shared_panel_html(
        data=data,
        rows_html=rows_html,
        minimum_payment_label=_korean_month_label(data["minimum_payment_month"]),
        net_total=net_total,
        discount_total=discount_total,
        minimum_total=data["minimum_total"],
        minimum_discount_total=data["minimum_discount_total"],
    )


def _row_html(
    row: dict,
    minimum_payment_month: str,
    current_month: str,
    settings: Mapping[str, str],
) -> str:
    discount = _panel_discount_amount(row, settings)
    original = float(row.get("amount_value") or 0)
    net = _panel_net_amount(row, settings)
    return render_panel_row(
        row=row,
        original=original,
        discount=discount,
        net=net,
        deferable=_payment_month(row, current_month) != minimum_payment_month,
    )


def _minimum_payment_rows(
    rows: list[dict],
    current_month: str,
) -> tuple[str, list[dict]]:
    payment_months = [_payment_month(row, current_month) for row in rows]
    minimum_payment_month = (
        min(payment_months) if payment_months else _next_month(current_month)
    )
    minimum_rows = [
        row
        for row in rows
        if _payment_month(row, current_month) == minimum_payment_month
    ]
    return minimum_payment_month, minimum_rows


def _payment_month(row: dict, current_month: str) -> str:
    spent_on = str(row.get("spent_on") or "")
    if not spent_on:
        # 구버전 날짜 누락 행은 가장 가까운 회차에 포함해 정산 누락을 막는다.
        return current_month
    spent_month = spent_on[:7]
    try:
        return _next_month(spent_month)
    except ValueError:
        return current_month


def _next_month(month: str) -> str:
    year_text, month_text = month.split("-", 1)
    year = int(year_text)
    month_number = int(month_text)
    if month_number < 1 or month_number > 12:
        raise ValueError("invalid month")
    if month_number == 12:
        return f"{year + 1:04d}-01"
    return f"{year:04d}-{month_number + 1:02d}"


def _korean_month_label(month: str) -> str:
    year_text, month_text = month.split("-", 1)
    return f"{int(year_text)}년 {int(month_text)}월"


def _panel_net_amount(
    row: dict,
    settings: Mapping[str, str] | None = None,
) -> float:
    return max(
        0,
        float(row.get("amount_value") or 0)
        - _panel_discount_amount(row, settings),
    )


def _panel_discount_amount(
    row: dict,
    settings: Mapping[str, str] | None = None,
) -> float:
    if row.get("panel_type") not in {"claim", "family_card"}:
        return 0.0
    settings = settings or list_settings()
    scope = "family" if row.get("panel_type") == "family_card" else "owner"
    policy = normalize_discount_policy(
        settings.get(f"card_discount_policy:{scope}:{row.get('month')}", "disabled" if scope == "family" else "enabled"),
        scope,
    )
    card = DiscountCard.FAMILY if scope == "family" else DiscountCard.OWNER
    return evaluate_stored_charge(
        row.get("amount_value"),
        row.get("discount_amount"),
        bool(row.get("discount_override") or row.get("discount_amount")),
        policy,
        str(row.get("month") or ""),
        row.get("title"),
        card,
        settings=settings,
    ).effective_discount_amount


def _ledger_note(panel_type: str, month: str) -> str | None:
    if panel_type != "claim":
        return None
    return claim_ledger_note(month, [*list_entries("archive"), *list_entries("current")], list_cash_flows())


def _float_setting(settings: dict[str, str], key: str, fallback: float) -> float:
    try:
        return float(settings.get(key, fallback))
    except (TypeError, ValueError):
        return fallback

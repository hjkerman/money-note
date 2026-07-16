from __future__ import annotations

from math import ceil
from statistics import median

from app.services.clock import app_today_iso
from app.services.discounts import normalize_discount_policy

from .categories import CATEGORY_LABELS, spending_stat_tones
from .common import days_between, judgment_message
from .features import panel_net_amount


DEFAULT_MANY_EXPENSE_THRESHOLD = 120


def app_judgment(
    entries: list[dict],
    panels: list[dict],
    cash_flows: list[dict],
    summary: dict,
    payment_status: dict,
    settings: dict[str, str],
    historical_expense_counts: list[int] | None = None,
) -> dict:
    """본체 웹앱에서 쓰는 모든 판단 문구를 한 번에 만든다."""
    expense_entries = [entry for entry in entries if entry.get("entry_kind") != "planned"]
    claim_rows = [
        {
            **panel,
            "discount_policy": normalize_discount_policy(
                settings.get(f"card_discount_policy:owner:{panel.get('month')}", "enabled"),
                "owner",
            ),
        }
        for panel in panels
        if panel.get("panel_type") == "claim"
    ]
    family_card_rows = [panel for panel in panels if panel.get("panel_type") == "family_card"]
    frozen_rows = [panel for panel in panels if panel.get("panel_type") == "frozen"]
    card_limit = float(settings.get("card_limit") or 5_800_000)
    family_card_total = sum(float(row.get("amount_value") or 0) for row in family_card_rows)
    owner_card_total = float(summary.get("card_total") or 0)
    today_iso = app_today_iso()
    days_until_due = days_between(today_iso, str(payment_status.get("due_date") or today_iso))
    reference_liquidity = float(payment_status.get("primary_income_total") or 0)
    if reference_liquidity <= 0:
        reference_liquidity = float(settings.get("base_next_month_liquidity") or 400_000)

    return {
        "category_labels": CATEGORY_LABELS,
        "stat_tones": spending_stat_tones(),
        "claim_categories": {},
        "budget": budget_committee_tone(
            {
                "expense_total": sum(float(entry.get("amount_value") or 0) for entry in expense_entries),
                "expense_count": len(expense_entries),
                "cash_flow_total": sum(float(flow.get("amount_value") or 0) for flow in cash_flows),
                "cash_flow_count": len(cash_flows),
                "claim_total": sum(panel_net_amount(row) for row in claim_rows),
                "claim_count": len(claim_rows),
                "family_card_total": family_card_total,
                "family_card_count": len(family_card_rows),
                "frozen_total": sum(float(row.get("amount_value") or 0) for row in frozen_rows),
                "frozen_count": len(frozen_rows),
                "next_month_liquidity": float(summary.get("next_month_liquidity") or 0),
                "historical_expense_counts": historical_expense_counts or [],
            }
        ),
        "credit": credit_usage_tone((owner_card_total + family_card_total) / card_limit if card_limit > 0 else 0),
        "payment": payment_pressure_tone(
            float(payment_status.get("recorded_remaining_total") or 0),
            days_until_due,
            reference_liquidity,
        ),
    }


def budget_committee_tone(input_data: dict) -> dict[str, str]:
    """장부 전체 변화에 반응하는 예산심사위원회 한 줄 평을 만든다."""
    activity_count = (
        input_data["expense_count"]
        + input_data["cash_flow_count"]
        + input_data["claim_count"]
        + input_data["family_card_count"]
        + input_data["frozen_count"]
    )

    def say(key: str) -> str:
        return judgment_message("insight", key, activity_count)

    if activity_count == 0:
        return {
            "level": "quiet",
            "message": say("budget.empty"),
        }
    if input_data.get("next_month_liquidity", 0) < 0:
        return {
            "level": "danger",
            "message": say("budget.liquidity_danger"),
        }
    if input_data["cash_flow_total"] < 0 and abs(input_data["cash_flow_total"]) > input_data["expense_total"]:
        return {
            "level": "warning",
            "message": say("budget.cash_outflow"),
        }
    if input_data["frozen_total"] > input_data["expense_total"] and input_data["frozen_count"] > 0:
        return {
            "level": "steady",
            "message": say("budget.frozen"),
        }
    if input_data["claim_total"] + input_data["family_card_total"] > input_data["expense_total"] and input_data["claim_count"] + input_data["family_card_count"] > 0:
        return {
            "level": "steady",
            "message": say("budget.family_presence"),
        }
    if input_data["expense_count"] >= many_expense_threshold(
        input_data.get("historical_expense_counts")
    ):
        return {
            "level": "steady",
            "message": say("budget.many_expenses"),
        }
    if input_data["cash_flow_total"] > input_data["expense_total"] and input_data["cash_flow_total"] > 0:
        return {
            "level": "quiet",
            "message": say("budget.cash_inflow"),
        }
    if input_data["expense_total"] >= 1_000_000:
        return {
            "level": "warning",
            "message": say("budget.high_expense"),
        }
    return {
        "level": "quiet",
        "message": say("budget.default"),
    }


def many_expense_threshold(historical_counts: list[int] | None) -> int:
    """최근 마감 월의 생활 패턴보다 확실히 건수가 많을 때만 판정한다."""
    counts = [int(count) for count in historical_counts or [] if int(count) >= 0]
    if not counts:
        return DEFAULT_MANY_EXPENSE_THRESHOLD
    baseline = median(counts[:3])
    margin = max(10, ceil(baseline * 0.15))
    return ceil(baseline) + margin


def credit_usage_tone(usage_rate: float) -> dict[str, str]:
    usage_percent = usage_rate * 100
    if usage_rate >= 0.8:
        return {
            "level": "danger",
            "message": judgment_message("insight", "credit.danger_80", round(usage_percent)),
        }
    if usage_rate >= 0.5:
        return {
            "level": "danger",
            "message": judgment_message("insight", "credit.danger_50", round(usage_percent)),
        }
    if usage_rate >= 0.3:
        return {
            "level": "warning",
            "message": judgment_message("insight", "credit.warning_30", round(usage_percent)),
        }
    if usage_rate >= 0.1:
        return {
            "level": "steady",
            "message": judgment_message("insight", "credit.steady_10", round(usage_percent)),
        }
    return {
        "level": "quiet",
        "message": judgment_message("insight", "credit.quiet", round(usage_percent)),
    }


def payment_pressure_tone(remaining_amount: float, days_until_due: int, reference_liquidity: float) -> dict[str, str]:
    liquidity_rate = remaining_amount / reference_liquidity if reference_liquidity > 0 else (2 if remaining_amount > 0 else 0)
    signals = (round(remaining_amount), days_until_due, round(liquidity_rate * 100))
    if remaining_amount <= 0:
        return {
            "level": "quiet",
            "message": judgment_message("insight", "payment.done", *signals),
        }
    if days_until_due < 0:
        return {
            "level": "danger",
            "message": judgment_message("insight", "payment.overdue", *signals),
        }
    if days_until_due == 0:
        return {
            "level": "danger",
            "message": judgment_message("insight", "payment.due_today", *signals),
        }
    if liquidity_rate >= 2 or (days_until_due <= 2 and liquidity_rate >= 1):
        return {
            "level": "danger",
            "message": judgment_message("insight", "payment.emergency", *signals),
        }
    if days_until_due <= 5 and liquidity_rate >= 0.75:
        return {
            "level": "warning",
            "message": judgment_message("insight", "payment.near_heavy", *signals),
        }
    if liquidity_rate >= 1:
        return {
            "level": "warning",
            "message": judgment_message("insight", "payment.over_income", *signals),
        }
    if days_until_due <= 5 or liquidity_rate >= 0.5:
        return {
            "level": "steady",
            "message": judgment_message("insight", "payment.watch", *signals),
        }
    return {
        "level": "quiet",
        "message": judgment_message("insight", "payment.quiet", *signals),
    }

from __future__ import annotations

# Judgment 문구와 판단 규칙은 이 패키지를 single source of truth로 둔다.
# 예산심사위원회, 공유 문구, 통계 톤을 다른 서비스나 UI에 흩뿌리지 않는다.

from .categories import CATEGORY_LABELS, category_label, spending_stat_tones
from .claim import claim_ledger_note, claim_subtitle, ledger_verdict
from .common import (
    choose_message,
    choose_seeded_message,
    days_between,
    format_won,
    get_messages,
    in_date_range,
    judgment_message,
    previous_to_current_range,
    ratio,
    safe_float,
    safe_int,
    stable_choice,
    text_contains,
    title_contains,
)
from .family_card import family_card_subtitle
from .features import (
    COLD_WORDS,
    DIGNITY_WORDS,
    ESSENTIAL_CLAIM_WORDS,
    MEDICAL_WORDS,
    PSYCHIATRY_WORDS,
    QUESTIONABLE_CLAIM_WORDS,
    SMALL_CLAIM_LIMIT,
    TRANSPORT_WORDS,
    claim_features,
    family_card_features,
    panel_net_amount,
    spending_category_counts,
    spending_category_totals,
)
from .insight import (
    app_judgment,
    budget_committee_tone,
    credit_usage_tone,
    many_expense_threshold,
    payment_pressure_tone,
)


def shared_panel_subtitle(
    panel_type: str,
    rows: list[dict],
    total: float,
    current_card_total: float,
    card_limit: float,
) -> str:
    """공유 화면 상단에 보여줄 패널별 평가 문구를 고른다."""
    if panel_type == "claim":
        return claim_subtitle(rows, total)
    return family_card_subtitle(rows, total, current_card_total, card_limit)


__all__ = [
    "CATEGORY_LABELS",
    "COLD_WORDS",
    "DIGNITY_WORDS",
    "ESSENTIAL_CLAIM_WORDS",
    "MEDICAL_WORDS",
    "PSYCHIATRY_WORDS",
    "QUESTIONABLE_CLAIM_WORDS",
    "SMALL_CLAIM_LIMIT",
    "TRANSPORT_WORDS",
    "app_judgment",
    "budget_committee_tone",
    "category_label",
    "choose_message",
    "choose_seeded_message",
    "claim_features",
    "claim_ledger_note",
    "claim_subtitle",
    "credit_usage_tone",
    "days_between",
    "family_card_features",
    "family_card_subtitle",
    "format_won",
    "get_messages",
    "in_date_range",
    "judgment_message",
    "ledger_verdict",
    "many_expense_threshold",
    "panel_net_amount",
    "payment_pressure_tone",
    "previous_to_current_range",
    "ratio",
    "safe_float",
    "safe_int",
    "shared_panel_subtitle",
    "spending_category_counts",
    "spending_category_totals",
    "spending_stat_tones",
    "stable_choice",
    "text_contains",
    "title_contains",
]

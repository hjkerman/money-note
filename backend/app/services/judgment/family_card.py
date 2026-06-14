from __future__ import annotations

from .common import judgment_message
from .features import family_card_features


def family_card_subtitle(rows: list[dict], total: float, current_card_total: float, card_limit: float) -> str:
    if not rows:
        return judgment_message("family_card", "subtitle.empty", round(current_card_total), round(card_limit))

    features = family_card_features(rows, total, current_card_total, card_limit)
    combined_usage_rate = float(features["usage_rate"])
    family_usage_rate = total / card_limit if card_limit > 0 else 0
    owner_usage_rate = current_card_total / card_limit if card_limit > 0 else 0
    family_share = total / (current_card_total + total) if current_card_total + total > 0 else 0
    largest_share = float(features["largest_share"])
    row_count = int(features["row_count"])
    signals = (
        row_count,
        round(total),
        round(current_card_total),
        round(combined_usage_rate * 1000),
        round(family_usage_rate * 1000),
        round(owner_usage_rate * 1000),
        round(family_share * 100),
        round(largest_share * 100),
    )

    if family_usage_rate >= 0.3 and owner_usage_rate >= 0.3:
        return judgment_message("family_card", "subtitle.joint_high", *signals)
    if owner_usage_rate >= 0.3 and family_usage_rate < 0.1:
        return judgment_message("family_card", "subtitle.owner_high_family_low", *signals)
    if family_usage_rate >= 0.3 or combined_usage_rate >= 0.5:
        return judgment_message("family_card", "subtitle.family_high", *signals)
    if combined_usage_rate >= 0.3:
        return judgment_message("family_card", "subtitle.combined_mid", *signals)
    if largest_share >= 0.7 and total >= 100_000:
        return judgment_message("family_card", "subtitle.largest", *signals)
    if family_usage_rate >= 0.1 or family_share >= 0.5:
        return judgment_message("family_card", "subtitle.moderate", *signals)
    return judgment_message("family_card", "subtitle.quiet", *signals)

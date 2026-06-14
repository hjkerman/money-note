from __future__ import annotations

from .common import in_date_range, judgment_message, previous_to_current_range, title_contains
from .features import COLD_WORDS, MEDICAL_WORDS, PSYCHIATRY_WORDS, TRANSPORT_WORDS, claim_features


def claim_subtitle(rows: list[dict], total: float) -> str:
    if not rows:
        return judgment_message("claim", "subtitle.empty", total)

    features = claim_features(rows, total)
    row_count = int(features["row_count"])
    medical_count = int(features["medical_count"])
    psychiatry_count = int(features["psychiatry_count"])
    transport_count = int(features["transport_count"])
    tiny_count = int(features["tiny_count"])
    largest = float(features["largest"])
    signals = features["signals"]

    if medical_count >= 4:
        return judgment_message("claim", "subtitle.medical_many", *signals)
    if medical_count == 3:
        return judgment_message("claim", "subtitle.medical_three", *signals)
    if psychiatry_count >= 2 and medical_count <= 2:
        return judgment_message("claim", "subtitle.psychiatry", *signals)
    if any("치과" in str(row.get("title") or "") for row in rows):
        return judgment_message("claim", "subtitle.dental", *signals)
    if tiny_count >= 3:
        return judgment_message("claim", "subtitle.tiny", *signals)
    if transport_count >= max(2, row_count / 2):
        return judgment_message("claim", "subtitle.transport", *signals)
    if total >= 300_000 or largest >= 200_000:
        return judgment_message("claim", "subtitle.large", *signals)
    if row_count >= 8:
        return judgment_message("claim", "subtitle.many_rows", *signals)
    return judgment_message("claim", "subtitle.default", *signals)


def claim_ledger_note(month: str, entries: list[dict], cash_flows: list[dict]) -> str:
    """어머니 청구서 하단에 붙일 전월~당월 가계부 한 줄 평가를 만든다."""
    start, end = previous_to_current_range(month)
    ranged_entries = [
        row
        for row in entries
        if row.get("entry_kind") != "planned" and in_date_range(str(row.get("entry_date") or ""), start, end)
    ]
    ranged_cash_flows = [
        row
        for row in cash_flows
        if in_date_range(str(row.get("occurred_on") or ""), start, end)
    ]
    card_total = sum(row.get("amount_value") or 0 for row in ranged_entries)
    cash_total = sum(row.get("amount_value") or 0 for row in ranged_cash_flows)
    questionable = sum(1 for row in ranged_entries if row.get("spending_category") == "questionable")
    verdict = ledger_verdict(card_total, cash_total, questionable, ranged_entries)
    return f"장부를 얼핏 보니, {verdict}"


def ledger_verdict(
    card_total: float,
    cash_total: float,
    questionable_count: int,
    entries: list[dict] | None = None,
) -> str:
    """카드/현금/성찰 항목 수를 바탕으로 짧은 평가 문장을 고른다."""
    entries = entries or []
    entry_count = len(entries)
    tiny_count = sum(1 for row in entries if 0 < float(row.get("amount_value") or 0) <= 5_000)
    medical_count = sum(1 for row in entries if title_contains(row, MEDICAL_WORDS))
    psychiatry_count = sum(1 for row in entries if title_contains(row, PSYCHIATRY_WORDS))
    cold_count = sum(1 for row in entries if title_contains(row, COLD_WORDS))
    largest = max((float(row.get("amount_value") or 0) for row in entries), default=0)
    largest_share = largest / card_total if card_total > 0 else 0
    signals = (
        round(card_total),
        round(cash_total),
        questionable_count,
        entry_count,
        tiny_count,
        medical_count,
        psychiatry_count,
        cold_count,
        round(largest_share * 100),
    )
    if medical_count >= 4:
        return judgment_message("claim", "ledger.medical_many", *signals)
    if psychiatry_count >= 2 and medical_count <= 3:
        return judgment_message("claim", "ledger.psychiatry", *signals)
    if medical_count >= 2 or cold_count >= 1:
        return judgment_message("claim", "ledger.medical_some", *signals)
    if entry_count >= 1 and tiny_count / entry_count >= 0.5:
        return judgment_message("claim", "ledger.tiny", *signals)
    if largest_share >= 0.5:
        return judgment_message("claim", "ledger.largest", *signals)
    if questionable_count >= 8:
        return judgment_message("claim", "ledger.enjoyable_many", *signals)
    if questionable_count >= 3:
        return judgment_message("claim", "ledger.enjoyable_some", *signals)
    if card_total >= 1_000_000:
        return judgment_message("claim", "ledger.card_very_active", *signals)
    if card_total >= 500_000:
        return judgment_message("claim", "ledger.card_active", *signals)
    if cash_total <= -300_000:
        return judgment_message("claim", "ledger.cash_large_out", *signals)
    if cash_total < 0:
        return judgment_message("claim", "ledger.cash_out", *signals)
    if cash_total > card_total and cash_total > 0:
        return judgment_message("claim", "ledger.cash_in", *signals)
    return judgment_message("claim", "ledger.default", *signals)

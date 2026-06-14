from __future__ import annotations

from app.services.discounts import effective_card_discount, normalize_discount_policy

from .common import title_contains


MEDICAL_WORDS = (
    "병원",
    "치과",
    "의원",
    "약국",
    "약제",
    "진료",
    "검사",
    "수술",
    "정신과",
    "정신건강",
    "감기",
    "내과",
    "이비인후과",
)
PSYCHIATRY_WORDS = ("정신과", "정신건강", "상담")
COLD_WORDS = ("감기", "내과", "이비인후과")
TRANSPORT_WORDS = ("교통", "하이패스", "주유", "유류", "lpg", "가스")
SMALL_CLAIM_LIMIT = 2_000
ESSENTIAL_CLAIM_WORDS = (
    "병원",
    "치과",
    "의원",
    "약국",
    "약제",
    "감기",
    "정신과",
    "정형외과",
    "진료",
    "검사",
    "수술",
    "이자",
    "대출",
    "통신",
    "보험",
    "관리비",
    "교통",
    "lpg",
    "가스",
    "유류",
    "주유",
    "하이패스",
    "통행",
)
QUESTIONABLE_CLAIM_WORDS = ("커피", "카페", "빽다방", "편지지", "간식", "술", "담배", "게임", "취미", "굿즈")
DIGNITY_WORDS = ("세탁", "의류", "옷", "미용", "이발", "헤어", "면도", "칫솔", "치약", "샴푸", "비누", "화장품")


def panel_net_amount(row: dict) -> float:
    if row.get("panel_type") != "claim":
        return max(0, float(row.get("amount_value") or 0))
    return max(
        0,
        float(row.get("amount_value") or 0)
        - effective_card_discount(
            row.get("amount_value"),
            row.get("discount_amount"),
            bool(row.get("discount_override") or row.get("discount_amount")),
            normalize_discount_policy(str(row.get("discount_policy") or "enabled"), "owner"),
            row.get("title"),
        ),
    )


def claim_features(rows: list[dict], total: float) -> dict[str, float | int | tuple[object, ...]]:
    row_count = len(rows)
    medical_count = sum(1 for row in rows if title_contains(row, MEDICAL_WORDS))
    psychiatry_count = sum(1 for row in rows if title_contains(row, PSYCHIATRY_WORDS))
    cold_count = sum(1 for row in rows if title_contains(row, COLD_WORDS))
    transport_count = sum(1 for row in rows if title_contains(row, TRANSPORT_WORDS))
    tiny_count = sum(1 for row in rows if 0 < float(row.get("amount_value") or 0) <= SMALL_CLAIM_LIMIT)
    largest = max(float(row.get("amount_value") or 0) for row in rows) if rows else 0
    signals = (
        row_count,
        round(total),
        medical_count,
        psychiatry_count,
        cold_count,
        transport_count,
        tiny_count,
        round(largest),
    )
    return {
        "row_count": row_count,
        "medical_count": medical_count,
        "psychiatry_count": psychiatry_count,
        "cold_count": cold_count,
        "transport_count": transport_count,
        "tiny_count": tiny_count,
        "largest": largest,
        "signals": signals,
    }


def family_card_features(
    rows: list[dict],
    total: float,
    current_card_total: float,
    card_limit: float,
) -> dict[str, float | int | tuple[object, ...]]:
    usage_rate = (current_card_total + total) / card_limit if card_limit > 0 else 0
    row_count = len(rows)
    largest = max(float(row.get("amount_value") or 0) for row in rows) if rows else 0
    largest_share = largest / total if total > 0 else 0
    signals = (row_count, round(total), round(current_card_total), round(usage_rate * 1000), round(largest_share * 100))
    return {
        "usage_rate": usage_rate,
        "row_count": row_count,
        "largest": largest,
        "largest_share": largest_share,
        "signals": signals,
    }


def spending_category_counts(entries: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        category = str(entry.get("spending_category") or "unclassified")
        counts[category] = counts.get(category, 0) + 1
    return counts


def spending_category_totals(entries: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for entry in entries:
        category = str(entry.get("spending_category") or "unclassified")
        totals[category] = totals.get(category, 0) + float(entry.get("amount_value") or 0)
    return totals

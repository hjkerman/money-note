from __future__ import annotations

from .models import DiscountCard


TRANSIT_WORDS = (
    "교통",
    "대중교통",
    "버스",
    "지하철",
)
TOLL_WORDS = (
    "통행",
    "통행료",
    "하이패스",
)
DISCOUNT_INELIGIBLE_WORDS = TRANSIT_WORDS + TOLL_WORDS


def toll_title(title: str | None) -> bool:
    """후불 하이패스 또는 통행료 카드 사용내역인지 판별한다."""
    text = str(title or "").lower()
    return "통행" in text or "하이패스" in text


def transport_title(title: str | None) -> bool:
    """통행료를 제외한 교통카드 사용내역인지 판별한다."""
    text = str(title or "").lower()
    return not toll_title(text) and any(
        word.lower() in text
        for word in TRANSIT_WORDS
    )


def discount_ineligible_title(title: str | None) -> bool:
    """기존 API 호환용으로 교통·통행 카드 제목을 판별한다."""
    return toll_title(title) or transport_title(title)


def classify_discount_card(
    title: str | None,
    default_card: DiscountCard,
    *,
    merchant: str | None = None,
) -> DiscountCard:
    """거래 제목을 우선하고 나머지는 호출 영역의 기본 카드로 분류한다.

    merchant는 미래의 가맹점별 정책을 위해 경계에서 받되 현재 분류에는 사용하지 않는다.
    """
    _ = merchant
    if toll_title(title):
        return DiscountCard.TOLL
    if transport_title(title):
        return DiscountCard.TRANSIT
    return default_card

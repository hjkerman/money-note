"""레거시 import를 위한 카드 실결제액 계산 호환층.

새 계산 코드는 ``app.services.card_charge``를 직접 사용한다. 이 모듈은 기존 public
함수와 테스트의 import 경로를 깨뜨리지 않기 위해 남겨 둔다.
"""

from __future__ import annotations

from app.services.card_charge import (
    DEFAULT_CARD_DISCOUNT_RATE as _DEFAULT_CARD_DISCOUNT_RATE,
    DISCOUNT_INELIGIBLE_WORDS,
    DiscountCard,
    default_discount_policy,
    discount_ineligible_title,
    evaluate_stored_charge,
    flat_statement_discount,
    normalize_discount_policy,
    toll_title,
    transport_title,
)

DEFAULT_CARD_DISCOUNT_RATE = float(_DEFAULT_CARD_DISCOUNT_RATE)


def default_card_discount(amount: float | int | None) -> int:
    """기존 1.2% 기본 자동 할인액을 반환한다."""
    return flat_statement_discount(int(amount or 0), _DEFAULT_CARD_DISCOUNT_RATE)


def effective_card_discount(
    amount: float | int | None,
    override_discount: float | int | None,
    override_enabled: bool,
    month_policy: str,
    title: str | None = None,
) -> int:
    """기존 호출 형식으로 본인 범용카드의 최종 할인액을 반환한다."""
    return evaluate_stored_charge(
        amount,
        override_discount,
        override_enabled,
        month_policy,
        "9999-12",
        title,
        DiscountCard.OWNER,
    ).effective_discount_amount


def net_card_amount(
    amount: float | int | None,
    override_discount: float | int | None,
    override_enabled: bool,
    month_policy: str,
    title: str | None = None,
) -> int:
    """기존 호출 형식으로 본인 범용카드의 실결제액을 반환한다."""
    return evaluate_stored_charge(
        amount,
        override_discount,
        override_enabled,
        month_policy,
        "9999-12",
        title,
        DiscountCard.OWNER,
    ).effective_amount


__all__ = [
    "DEFAULT_CARD_DISCOUNT_RATE",
    "DISCOUNT_INELIGIBLE_WORDS",
    "default_card_discount",
    "default_discount_policy",
    "discount_ineligible_title",
    "effective_card_discount",
    "net_card_amount",
    "normalize_discount_policy",
    "toll_title",
    "transport_title",
]

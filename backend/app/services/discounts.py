from __future__ import annotations

from math import floor


DEFAULT_CARD_DISCOUNT_RATE = 0.012


def default_card_discount(amount: float | int | None) -> float:
    """카드사가 별도 예외를 주지 않는다는 가정의 기본 할인액이다."""
    return float(floor(float(amount or 0) * DEFAULT_CARD_DISCOUNT_RATE))


def effective_card_discount(
    amount: float | int | None,
    manual_discount: float | int | None,
    manual_checked: bool,
    month_policy: str,
) -> float:
    """월 정책과 개별 할인 제외 상태를 합쳐 실제 계산에 쓸 할인액을 만든다."""
    if month_policy == "disabled":
        return 0.0
    if manual_checked:
        return max(0.0, float(manual_discount or 0))
    return default_card_discount(amount)


def net_card_amount(
    amount: float | int | None,
    manual_discount: float | int | None,
    manual_checked: bool,
    month_policy: str,
) -> float:
    """할인 반영 후 카드 청구 예상액이다."""
    return max(0.0, float(amount or 0) - effective_card_discount(amount, manual_discount, manual_checked, month_policy))

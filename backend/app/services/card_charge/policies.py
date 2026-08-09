from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Protocol

from .models import AutomaticDiscount, CardChargeInput


DEFAULT_CARD_DISCOUNT_RATE = Decimal("0.012")


def flat_statement_discount(
    amount: int,
    rate: Decimal = DEFAULT_CARD_DISCOUNT_RATE,
) -> int:
    """원금에 단일 청구할인율을 적용하고 원 미만을 버린다."""
    discount = (Decimal(amount) * rate).to_integral_value(rounding=ROUND_FLOOR)
    return max(0, int(discount))


class CardChargePolicy(Protocol):
    policy_id: str

    def automatic_discount(self, charge: CardChargeInput) -> AutomaticDiscount:
        """수동 override와 월 스위치를 제외한 카드 자체 혜택만 계산한다."""


@dataclass(frozen=True)
class FlatStatementDiscountPolicy:
    policy_id: str
    rate: Decimal = DEFAULT_CARD_DISCOUNT_RATE

    def automatic_discount(self, charge: CardChargeInput) -> AutomaticDiscount:
        """현재 범용카드처럼 원금에 단일 청구할인율을 적용한다."""
        return AutomaticDiscount(
            eligible=True,
            amount=flat_statement_discount(charge.original_amount, self.rate),
            reason=f"flat_statement:{self.rate}",
        )


@dataclass(frozen=True)
class NoAutomaticDiscountPolicy:
    policy_id: str

    def automatic_discount(self, charge: CardChargeInput) -> AutomaticDiscount:
        """통행료·교통카드처럼 자동으로 실결제액을 낮추지 않는다."""
        return AutomaticDiscount(
            eligible=False,
            amount=0,
            reason="no_automatic_discount",
        )

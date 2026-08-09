from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DiscountCard(str, Enum):
    """할인 계산에서 독립적으로 취급하는 네 카드."""

    OWNER = "owner"
    FAMILY = "family"
    TOLL = "toll"
    TRANSIT = "transit"


@dataclass(frozen=True)
class CardChargeInput:
    """실결제액 평가에 필요한 저장값과 미래 정책용 거래 문맥."""

    card: DiscountCard
    usage_month: str
    original_amount: int
    month_policy: str | None
    title: str | None = None
    merchant: str | None = None
    spending_category: str | None = None
    override_enabled: bool = False
    override_discount: int | None = None


@dataclass(frozen=True)
class AutomaticDiscount:
    eligible: bool
    amount: int
    reason: str


@dataclass(frozen=True)
class CardChargeResult:
    original_amount: int
    automatic_discount_eligible: bool
    automatic_discount_amount: int
    effective_discount_amount: int
    effective_amount: int
    policy_id: str
    reason: str

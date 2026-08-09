from __future__ import annotations

from dataclasses import dataclass

from .models import DiscountCard
from .policies import (
    CardChargePolicy,
    FlatStatementDiscountPolicy,
    NoAutomaticDiscountPolicy,
)


@dataclass(frozen=True)
class PolicyBinding:
    effective_from: str
    policy: CardChargePolicy


# 본인·가족은 현재 같은 계산식을 우연히 사용하지만 서로 독립된 정책 이력이다.
POLICY_TIMELINES: dict[DiscountCard, tuple[PolicyBinding, ...]] = {
    DiscountCard.OWNER: (
        PolicyBinding("0001-01", FlatStatementDiscountPolicy("owner-flat-statement-1.2")),
    ),
    DiscountCard.FAMILY: (
        PolicyBinding("0001-01", FlatStatementDiscountPolicy("family-flat-statement-1.2")),
    ),
    DiscountCard.TOLL: (
        PolicyBinding("0001-01", NoAutomaticDiscountPolicy("toll-no-automatic-discount")),
    ),
    DiscountCard.TRANSIT: (
        PolicyBinding("0001-01", NoAutomaticDiscountPolicy("transit-no-automatic-discount")),
    ),
}


def policy_for(card: DiscountCard, usage_month: str) -> CardChargePolicy:
    """사용월에 유효했던 카드 정책을 반환해 과거 재계산을 막는다."""
    month = usage_month if len(usage_month) == 7 else "9999-12"
    candidates = [
        binding
        for binding in POLICY_TIMELINES[card]
        if binding.effective_from <= month
    ]
    if not candidates:
        raise ValueError(f"{card.value} 카드의 {usage_month} 정책을 찾을 수 없습니다.")
    return max(candidates, key=lambda binding: binding.effective_from).policy

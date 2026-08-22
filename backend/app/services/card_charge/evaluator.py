from __future__ import annotations

from collections.abc import Mapping

from .activation import normalize_discount_policy
from .classifier import classify_discount_card
from .models import (
    CardChargeInput,
    CardChargeResult,
    DiscountCard,
    TransitDiscountProfile,
)
from .profiles import (
    TRANSIT_NO_DISCOUNT_POLICY,
    normalize_transit_discount_profile,
    policy_card_for,
    transit_discount_profile_for_month,
)
from .registry import policy_for


def evaluate_card_charge(charge: CardChargeInput) -> CardChargeResult:
    """카드 정책, 월 스위치, 수동 보정을 합쳐 최종 실결제액을 반환한다."""
    original = max(0, int(charge.original_amount))
    transit_profile = normalize_transit_discount_profile(charge.transit_profile)
    policy_card = policy_card_for(charge.card, transit_profile)
    if (
        charge.card == DiscountCard.TRANSIT
        and transit_profile == TransitDiscountProfile.NONE
    ):
        policy = TRANSIT_NO_DISCOUNT_POLICY
    else:
        policy = policy_for(policy_card, charge.usage_month)
    automatic = policy.automatic_discount(charge)
    raw_month_policy = charge.month_policy
    if charge.card == DiscountCard.TRANSIT and policy_card == DiscountCard.OWNER:
        raw_month_policy = charge.owner_month_policy or charge.month_policy
    month_policy = normalize_discount_policy(
        raw_month_policy,
        "family" if policy_card == DiscountCard.FAMILY else "owner",
    )

    if charge.override_enabled:
        effective_discount = max(0, int(charge.override_discount or 0))
        reason = "manual_override"
    elif month_policy == "disabled":
        effective_discount = 0
        reason = "month_disabled"
    else:
        effective_discount = automatic.amount
        reason = automatic.reason

    return CardChargeResult(
        original_amount=original,
        automatic_discount_eligible=automatic.eligible,
        automatic_discount_amount=automatic.amount,
        effective_discount_amount=effective_discount,
        effective_amount=max(0, original - effective_discount),
        policy_id=policy.policy_id,
        month_policy=month_policy,
        reason=reason,
    )


def evaluate_stored_charge(
    amount: float | int | None,
    override_discount: float | int | None,
    override_enabled: bool,
    month_policy: str | None,
    usage_month: str,
    title: str | None,
    default_card: DiscountCard,
    *,
    merchant: str | None = None,
    spending_category: str | None = None,
    settings: Mapping[str, str] | None = None,
) -> CardChargeResult:
    """저장 행의 문맥을 카드 분류와 실결제액 평가에 한 번에 전달한다."""
    card = classify_discount_card(title, default_card, merchant=merchant)
    policy_settings = settings or {}
    transit_profile = (
        transit_discount_profile_for_month(policy_settings, usage_month)
        if card == DiscountCard.TRANSIT
        else TransitDiscountProfile.NONE
    )
    return evaluate_card_charge(
        CardChargeInput(
            card=card,
            usage_month=usage_month,
            original_amount=int(amount or 0),
            month_policy=month_policy,
            title=title,
            merchant=merchant,
            spending_category=spending_category,
            override_enabled=override_enabled,
            override_discount=int(override_discount or 0),
            transit_profile=transit_profile,
            owner_month_policy=policy_settings.get(
                f"card_discount_policy:owner:{usage_month}"
            ),
        )
    )

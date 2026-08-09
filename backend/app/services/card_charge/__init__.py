"""카드 종류별 자동 할인과 실결제액 계산의 단일 진실 원천."""

from .activation import default_discount_policy, normalize_discount_policy
from .classifier import (
    DISCOUNT_INELIGIBLE_WORDS,
    classify_discount_card,
    discount_ineligible_title,
    toll_title,
    transport_title,
)
from .evaluator import evaluate_card_charge, evaluate_stored_charge
from .models import CardChargeInput, CardChargeResult, DiscountCard
from .policies import DEFAULT_CARD_DISCOUNT_RATE, flat_statement_discount
from .registry import policy_for

__all__ = [
    "CardChargeInput",
    "CardChargeResult",
    "DEFAULT_CARD_DISCOUNT_RATE",
    "DISCOUNT_INELIGIBLE_WORDS",
    "DiscountCard",
    "classify_discount_card",
    "default_discount_policy",
    "discount_ineligible_title",
    "evaluate_card_charge",
    "evaluate_stored_charge",
    "flat_statement_discount",
    "normalize_discount_policy",
    "policy_for",
    "toll_title",
    "transport_title",
]

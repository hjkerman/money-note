from __future__ import annotations

from math import floor


DEFAULT_CARD_DISCOUNT_RATE = 0.012
DISCOUNT_INELIGIBLE_WORDS = ("교통", "대중교통", "버스", "지하철", "통행", "통행료", "하이패스")


def default_discount_policy(scope: str = "owner") -> str:
    """설정이 없는 달의 카드 할인 기본 정책이다."""
    return "disabled" if scope == "family" else "enabled"


def normalize_discount_policy(policy: str | None, scope: str = "owner") -> str:
    """레거시/누락 정책값을 실제 계산에 쓰는 두 상태로 정규화한다."""
    if policy in {"enabled", "disabled"}:
        return policy
    return default_discount_policy(scope)


def default_card_discount(amount: float | int | None) -> float:
    """카드사가 별도 예외를 주지 않는다는 가정의 기본 할인액이다."""
    return float(floor(float(amount or 0) * DEFAULT_CARD_DISCOUNT_RATE))


def discount_ineligible_title(title: str | None) -> bool:
    """카드 할인 가능성이 없는 사용처/세부내역을 판별한다."""
    text = str(title or "").lower()
    return any(word.lower() in text for word in DISCOUNT_INELIGIBLE_WORDS)


def effective_card_discount(
    amount: float | int | None,
    override_discount: float | int | None,
    override_enabled: bool,
    month_policy: str,
    title: str | None = None,
) -> float:
    """월 정책과 개별 할인 제외 상태를 합쳐 실제 계산에 쓸 할인액을 만든다."""
    month_policy = normalize_discount_policy(month_policy)
    if override_enabled:
        return max(0.0, float(override_discount or 0))
    if month_policy == "disabled" or discount_ineligible_title(title):
        return 0.0
    return default_card_discount(amount)


def net_card_amount(
    amount: float | int | None,
    override_discount: float | int | None,
    override_enabled: bool,
    month_policy: str,
    title: str | None = None,
) -> float:
    """할인 반영 후 카드 청구 예상액이다."""
    return max(0.0, float(amount or 0) - effective_card_discount(amount, override_discount, override_enabled, month_policy, title))

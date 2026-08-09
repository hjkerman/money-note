"""본인카드와 가족카드가 독립적으로 갖는 월별 혜택 스위치."""


def default_discount_policy(scope: str = "owner") -> str:
    """설정이 없는 달의 할인 혜택 기본 상태를 반환한다."""
    return "disabled" if scope == "family" else "enabled"


def normalize_discount_policy(policy: str | None, scope: str = "owner") -> str:
    """레거시 또는 누락된 월 정책을 enabled/disabled로 정규화한다."""
    if policy in {"enabled", "disabled"}:
        return policy
    return default_discount_policy(scope)

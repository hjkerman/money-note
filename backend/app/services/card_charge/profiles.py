from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.db import session
from app.repositories.settings import list_settings

from .models import DiscountCard, TransitDiscountProfile
from .policies import NoAutomaticDiscountPolicy


TRANSIT_PROFILE_SETTING_PREFIX = "card_charge_profile:transit:"
TRANSIT_PROFILE_SELECTOR_VERSION = 1
TRANSIT_NO_DISCOUNT_POLICY = NoAutomaticDiscountPolicy(
    "transit-no-automatic-discount"
)
_MONTH_RE = re.compile(r"\d{4}-(?:0[1-9]|1[0-2])")


def normalize_transit_discount_profile(
    value: str | TransitDiscountProfile | None,
) -> TransitDiscountProfile:
    """누락된 구버전 설정은 기존 동작인 자동 할인 없음으로 해석한다."""
    if value is None or value == "":
        return TransitDiscountProfile.NONE
    try:
        return TransitDiscountProfile(value)
    except ValueError:
        raise ValueError("알 수 없는 교통카드 할인 정책입니다.") from None


def transit_discount_profile_for_month(
    settings: Mapping[str, str],
    usage_month: str,
) -> TransitDiscountProfile:
    """사용월 이전의 가장 최근 설정을 골라 과거 거래 재계산을 막는다."""
    _validate_month(usage_month)
    candidates: list[tuple[str, TransitDiscountProfile]] = []
    for key, value in settings.items():
        if not key.startswith(TRANSIT_PROFILE_SETTING_PREFIX):
            continue
        effective_from = key.removeprefix(TRANSIT_PROFILE_SETTING_PREFIX)
        if not _MONTH_RE.fullmatch(effective_from):
            raise ValueError("교통카드 할인 정책의 적용 월이 올바르지 않습니다.")
        if effective_from <= usage_month:
            candidates.append(
                (effective_from, normalize_transit_discount_profile(value))
            )
    if not candidates:
        return TransitDiscountProfile.NONE
    return max(candidates, key=lambda item: item[0])[1]


def policy_card_for(
    card: DiscountCard,
    transit_profile: str | TransitDiscountProfile | None,
) -> DiscountCard:
    """카드 정체성은 유지하면서 교통카드의 정책 출처만 선택한다."""
    if card != DiscountCard.TRANSIT:
        return card
    profile = normalize_transit_discount_profile(transit_profile)
    return DiscountCard.OWNER if profile == TransitDiscountProfile.OWNER else card


def transit_discount_profile_status(month: str) -> dict[str, str]:
    _validate_month(month)
    profile = transit_discount_profile_for_month(list_settings(), month)
    return {
        "card": DiscountCard.TRANSIT.value,
        "month": month,
        "profile": profile.value,
    }


def set_transit_discount_profile(
    month: str,
    profile: str | TransitDiscountProfile,
) -> dict[str, str]:
    """교통카드 정책 변경을 해당 월부터 유효한 이력으로 저장한다."""
    _validate_month(month)
    normalized = normalize_transit_discount_profile(profile)
    with session() as conn:
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (f"{TRANSIT_PROFILE_SETTING_PREFIX}{month}", normalized.value),
        )
    return transit_discount_profile_status(month)


def transit_discount_profile_manifest() -> dict[str, Any]:
    """Snapshot이 교통카드 프로파일 선택 의미까지 검증하도록 명세한다."""
    return {
        "schema_version": TRANSIT_PROFILE_SELECTOR_VERSION,
        "card": DiscountCard.TRANSIT.value,
        "default": TransitDiscountProfile.NONE.value,
        "modes": [profile.value for profile in TransitDiscountProfile],
        "none_mode": {
            "policy": TRANSIT_NO_DISCOUNT_POLICY.snapshot_definition(),
        },
        "owner_mode": {
            "policy_source": DiscountCard.OWNER.value,
            "month_policy_source": DiscountCard.OWNER.value,
        },
        "selection": "latest_effective_month",
        "setting_prefix": TRANSIT_PROFILE_SETTING_PREFIX,
    }


def _validate_month(value: str) -> None:
    if not _MONTH_RE.fullmatch(value):
        raise ValueError("월 형식은 YYYY-MM이어야 합니다.")

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .classifier import card_classifier_manifest
from .models import DiscountCard
from .policies import (
    CardChargePolicy,
    FlatStatementDiscountPolicy,
    NoAutomaticDiscountPolicy,
)
from .profiles import transit_discount_profile_manifest


@dataclass(frozen=True)
class PolicyBinding:
    effective_from: str
    policy: CardChargePolicy


CARD_CHARGE_POLICY_MANIFEST_VERSION = 2
LEGACY_CARD_CHARGE_POLICY_MANIFEST_VERSION = 1


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


def card_charge_policy_manifest(covered_through: str | None = None) -> dict[str, Any]:
    """과거 Snapshot을 같은 카드 정책으로 복원할 수 있는지 검증할 명세를 만든다."""
    manifest = {
        "schema_version": CARD_CHARGE_POLICY_MANIFEST_VERSION,
        "classifier": card_classifier_manifest(),
        "profile_selectors": {
            "transit": transit_discount_profile_manifest(),
        },
        "cards": {
            card.value: [
                {
                    "effective_from": binding.effective_from,
                    **binding.policy.snapshot_definition(),
                }
                for binding in POLICY_TIMELINES[card]
            ]
            for card in DiscountCard
        },
    }
    if covered_through is not None:
        manifest["covered_through"] = covered_through
    return manifest


def card_charge_policy_manifest_compatible(
    snapshot_manifest: object,
) -> bool:
    """Snapshot 당시 정책은 보존하고 이후 시작하는 binding 추가만 허용한다."""
    if not isinstance(snapshot_manifest, dict):
        return False
    schema_version = snapshot_manifest.get("schema_version")
    expected_keys = {"schema_version", "covered_through", "classifier", "cards"}
    if schema_version == CARD_CHARGE_POLICY_MANIFEST_VERSION:
        expected_keys.add("profile_selectors")
    elif schema_version != LEGACY_CARD_CHARGE_POLICY_MANIFEST_VERSION:
        return False
    if set(snapshot_manifest) != expected_keys:
        return False
    snapshot_month = snapshot_manifest.get("covered_through")
    if not isinstance(snapshot_month, str) or not re.fullmatch(
        r"\d{4}-(?:0[1-9]|1[0-2])",
        snapshot_month,
    ):
        return False
    current = card_charge_policy_manifest()
    if snapshot_manifest.get("classifier") != current["classifier"]:
        return False
    if schema_version == CARD_CHARGE_POLICY_MANIFEST_VERSION:
        if snapshot_manifest.get("profile_selectors") != current["profile_selectors"]:
            return False
    snapshot_cards = snapshot_manifest.get("cards")
    current_cards = current["cards"]
    if not isinstance(snapshot_cards, dict) or set(snapshot_cards) != set(current_cards):
        return False
    for card, snapshot_bindings in snapshot_cards.items():
        current_bindings = current_cards[card]
        if not isinstance(snapshot_bindings, list) or not snapshot_bindings:
            return False
        if current_bindings[: len(snapshot_bindings)] != snapshot_bindings:
            return False
        for binding in current_bindings[len(snapshot_bindings) :]:
            if binding.get("effective_from", "") <= snapshot_month:
                return False
    return True

"""The mobile admission registry must be generated from this backend build."""

from copy import deepcopy
import importlib.util
from pathlib import Path
from unittest.mock import patch

from app.services.card_charge import registry
from app.services.card_charge.models import DiscountCard


def test_mobile_policy_artifact_matches_entire_canonical_registry():
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "generate_bundle_policy", root / "scripts/generate_bundle_policy.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    assert generator.TARGET.read_text() == generator.generated_source()


def test_canonical_policy_exact_text_and_future_binding_prefix():
    original = registry.card_charge_policy_manifest("2026-10")
    assert registry.card_charge_policy_manifest_compatible(original)
    for rate in ("0.02", "0.0120"):
        changed = deepcopy(original)
        changed["cards"]["owner"][0]["parameters"]["rate"] = rate
        assert not registry.card_charge_policy_manifest_compatible(changed)
    timelines = dict(registry.POLICY_TIMELINES)
    timelines[DiscountCard.OWNER] += (
        registry.PolicyBinding("2026-11", timelines[DiscountCard.OWNER][0].policy),
    )
    with patch.object(registry, "POLICY_TIMELINES", timelines):
        assert registry.card_charge_policy_manifest_compatible(original)
        changed = deepcopy(original)
        changed["covered_through"] = "2026-11"
        assert not registry.card_charge_policy_manifest_compatible(changed)

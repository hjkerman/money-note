from decimal import Decimal
import unittest
from unittest.mock import patch

from app.services.card_charge import (
    CardChargeInput,
    DiscountCard,
    evaluate_card_charge,
    evaluate_stored_charge,
    policy_for,
)
from app.services.card_charge.policies import FlatStatementDiscountPolicy
from app.services.card_charge.registry import POLICY_TIMELINES, PolicyBinding
from app.services.discounts import DEFAULT_CARD_DISCOUNT_RATE, default_card_discount


class CardChargePolicyTest(unittest.TestCase):
    def test_legacy_default_discount_interface_is_preserved(self) -> None:
        self.assertIsInstance(DEFAULT_CARD_DISCOUNT_RATE, float)
        self.assertEqual(default_card_discount(10_099), 121)

    def test_four_cards_have_independent_policy_registrations(self) -> None:
        owner = policy_for(DiscountCard.OWNER, "2026-08")
        family = policy_for(DiscountCard.FAMILY, "2026-08")
        toll = policy_for(DiscountCard.TOLL, "2026-08")
        transit = policy_for(DiscountCard.TRANSIT, "2026-08")

        self.assertEqual(owner.policy_id, "owner-flat-statement-1.2")
        self.assertEqual(family.policy_id, "family-flat-statement-1.2")
        self.assertNotEqual(owner.policy_id, family.policy_id)
        self.assertEqual(toll.policy_id, "toll-no-automatic-discount")
        self.assertEqual(transit.policy_id, "transit-no-automatic-discount")

    def test_owner_and_family_share_formula_but_not_month_activation(self) -> None:
        owner = evaluate_card_charge(
            CardChargeInput(
                card=DiscountCard.OWNER,
                usage_month="2026-08",
                original_amount=10_000,
                month_policy="enabled",
            )
        )
        family = evaluate_card_charge(
            CardChargeInput(
                card=DiscountCard.FAMILY,
                usage_month="2026-08",
                original_amount=10_000,
                month_policy="disabled",
            )
        )

        self.assertEqual(owner.effective_discount_amount, 120)
        self.assertEqual(family.automatic_discount_amount, 120)
        self.assertEqual(family.effective_discount_amount, 0)

    def test_toll_and_transit_are_separate_no_discount_cards(self) -> None:
        toll = evaluate_stored_charge(
            10_000,
            None,
            False,
            "enabled",
            "2026-08",
            "고속도로 하이패스",
            DiscountCard.OWNER,
        )
        transit = evaluate_stored_charge(
            10_000,
            None,
            False,
            "enabled",
            "2026-08",
            "대중교통",
            DiscountCard.OWNER,
        )

        self.assertEqual(toll.policy_id, "toll-no-automatic-discount")
        self.assertFalse(toll.automatic_discount_eligible)
        self.assertEqual(toll.effective_discount_amount, 0)
        self.assertEqual(transit.policy_id, "transit-no-automatic-discount")
        self.assertFalse(transit.automatic_discount_eligible)

    def test_manual_override_wins_for_every_card(self) -> None:
        for card in DiscountCard:
            with self.subTest(card=card):
                result = evaluate_card_charge(
                    CardChargeInput(
                        card=card,
                        usage_month="2026-08",
                        original_amount=10_000,
                        month_policy="disabled",
                        override_enabled=True,
                        override_discount=3_000,
                    )
                )
                self.assertEqual(result.effective_discount_amount, 3_000)
                self.assertEqual(result.effective_amount, 7_000)
                self.assertEqual(result.reason, "manual_override")

    def test_flat_policy_accepts_future_context_without_changing_current_rate(self) -> None:
        result = evaluate_stored_charge(
            10_099,
            None,
            False,
            "enabled",
            "2026-08",
            "[의료] 정기 진료",
            DiscountCard.OWNER,
            merchant="동네의원",
            spending_category="essential",
        )

        self.assertEqual(result.automatic_discount_amount, 121)
        self.assertEqual(result.effective_amount, 9_978)

    def test_policy_timeline_uses_usage_month(self) -> None:
        timeline = (
            PolicyBinding(
                "0001-01",
                FlatStatementDiscountPolicy("old-rate", Decimal("0.010")),
            ),
            PolicyBinding(
                "2027-01",
                FlatStatementDiscountPolicy("new-rate", Decimal("0.020")),
            ),
        )
        with patch.dict(POLICY_TIMELINES, {DiscountCard.OWNER: timeline}):
            old = evaluate_card_charge(
                CardChargeInput(
                    card=DiscountCard.OWNER,
                    usage_month="2026-12",
                    original_amount=10_000,
                    month_policy="enabled",
                )
            )
            new = evaluate_card_charge(
                CardChargeInput(
                    card=DiscountCard.OWNER,
                    usage_month="2027-01",
                    original_amount=10_000,
                    month_policy="enabled",
                )
            )

        self.assertEqual(old.effective_discount_amount, 100)
        self.assertEqual(new.effective_discount_amount, 200)


if __name__ == "__main__":
    unittest.main()

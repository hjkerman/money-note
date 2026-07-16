import unittest

from app.services.judgment import (
    app_judgment,
    choose_message,
    claim_ledger_note,
    claim_subtitle,
    get_messages,
    ledger_verdict,
    family_card_subtitle,
    many_expense_threshold,
    stable_choice,
)


class JudgmentTest(unittest.TestCase):
    @staticmethod
    def _budget_input(expense_count: int, historical_counts: list[int]) -> dict:
        return {
            "expense_total": 100_000,
            "expense_count": expense_count,
            "cash_flow_total": 0,
            "cash_flow_count": 0,
            "claim_total": 0,
            "claim_count": 0,
            "family_card_total": 0,
            "family_card_count": 0,
            "frozen_total": 0,
            "frozen_count": 0,
            "next_month_liquidity": 400_000,
            "historical_expense_counts": historical_counts,
        }

    def test_stable_choice_keeps_same_verdict_for_same_state(self) -> None:
        messages = ("첫째", "둘째", "셋째")

        self.assertEqual(
            stable_choice(messages, 10, 20, "상태"),
            stable_choice(messages, 10, 20, "상태"),
        )

    def test_choose_message_can_be_seeded_but_varies_by_seed(self) -> None:
        messages = ("첫째", "둘째", "셋째", "넷째")

        self.assertEqual(
            choose_message(messages, "상태", seed="fixed"),
            choose_message(messages, "상태", seed="fixed"),
        )
        self.assertGreater(
            len({choose_message(messages, "상태", seed=index) for index in range(20)}),
            1,
        )

    def test_many_expense_threshold_uses_recent_month_median_and_margin(self) -> None:
        self.assertEqual(many_expense_threshold([97]), 112)
        self.assertEqual(many_expense_threshold([80, 100, 140]), 115)
        self.assertEqual(many_expense_threshold([]), 120)

    def test_budget_marks_only_personally_high_expense_count_as_steady(self) -> None:
        from app.services.judgment import budget_committee_tone

        ordinary = budget_committee_tone(self._budget_input(111, [97]))
        many = budget_committee_tone(self._budget_input(112, [97]))

        self.assertEqual(ordinary["level"], "quiet")
        self.assertEqual(many["level"], "steady")
        self.assertNotEqual(ordinary["message"], many["message"])

    def test_claim_subtitle_distinguishes_medical_and_tiny_claims(self) -> None:
        medical_rows = [
            {"title": "병원 진료", "amount_value": 30_000},
            {"title": "약국", "amount_value": 12_000},
        ]
        tiny_rows = [
            {"title": "복사비", "amount_value": 1_000},
            {"title": "주차비", "amount_value": 2_000},
            {"title": "봉투", "amount_value": 500},
        ]

        self.assertNotEqual(claim_subtitle(medical_rows, 42_000), claim_subtitle(tiny_rows, 3_500))

    def test_claim_subtitle_distinguishes_routine_one_sick_day_and_family_worry(self) -> None:
        routine_rows = [
            {"title": "정신과 정기진료", "amount_value": 25_000},
            {"title": "정신과 정기진료", "amount_value": 25_000},
        ]
        one_sick_day_rows = [
            *routine_rows,
            {"title": "감기 내과", "amount_value": 18_000},
        ]
        family_worry_rows = [
            *one_sick_day_rows,
            {"title": "병원 추가진료", "amount_value": 35_000},
        ]

        routine = claim_subtitle(routine_rows, 50_000)
        one_sick_day = claim_subtitle(one_sick_day_rows, 68_000)
        family_worry = claim_subtitle(family_worry_rows, 103_000)

        self.assertNotEqual(routine, one_sick_day)
        self.assertNotEqual(one_sick_day, family_worry)
        self.assertTrue("정신" in routine or "마음" in routine or "건강" in routine)

    def test_family_card_subtitle_distinguishes_usage_pressure(self) -> None:
        rows = [{"title": "가족카드", "amount_value": 500_000}]

        quiet = family_card_subtitle(rows, 500_000, 0, 5_800_000)
        danger = family_card_subtitle(rows, 500_000, 4_300_000, 5_800_000)

        self.assertNotEqual(quiet, danger)

    def test_family_card_subtitle_avoids_private_family_blame_words(self) -> None:
        rows = [{"title": "가족카드", "amount_value": 300_000}]
        messages = [
            family_card_subtitle(rows, 300_000, 0, 5_800_000),
            family_card_subtitle(rows, 300_000, 2_000_000, 5_800_000),
            family_card_subtitle(rows, 2_000_000, 2_000_000, 5_800_000),
        ]

        for message in messages:
            self.assertNotIn("오빠", message)
            self.assertNotIn("안 갚", message)
            self.assertNotIn("먹튀", message)

    def test_shared_message_pools_stay_separated(self) -> None:
        claim_messages = set(get_messages("claim", "subtitle.empty"))
        family_card_messages = set(get_messages("family_card", "subtitle.empty"))
        insight_messages = set(get_messages("insight", "budget.empty"))

        self.assertFalse(claim_messages & family_card_messages)
        self.assertFalse(claim_messages & insight_messages)
        self.assertFalse(family_card_messages & insight_messages)

        all_family_card_messages: list[str] = []
        for key in (
            "subtitle.empty",
            "subtitle.joint_high",
            "subtitle.owner_high_family_low",
            "subtitle.family_high",
            "subtitle.combined_mid",
            "subtitle.largest",
            "subtitle.moderate",
            "subtitle.quiet",
        ):
            all_family_card_messages.extend(get_messages("family_card", key))
        for message in all_family_card_messages:
            self.assertNotIn("오빠", message)
            self.assertNotIn("안 갚", message)

    def test_ledger_verdict_distinguishes_questionable_spending(self) -> None:
        ordinary = ledger_verdict(200_000, 50_000, 0)
        hearing = ledger_verdict(200_000, 50_000, 8)

        self.assertNotEqual(ordinary, hearing)

    def test_claim_ledger_note_hides_private_exact_amounts(self) -> None:
        note = claim_ledger_note(
            "2026-06",
            [
                {
                    "entry_date": "2026-06-02",
                    "entry_kind": "expense",
                    "title": "정신건강의학과",
                    "amount_value": 123_456,
                    "spending_category": "questionable",
                },
                {
                    "entry_date": "2026-06-03",
                    "entry_kind": "expense",
                    "title": "커피",
                    "amount_value": 7_890,
                    "spending_category": "questionable",
                },
            ],
            [
                {
                    "occurred_on": "2026-06-03",
                    "amount_value": -234_567,
                },
            ],
        )

        self.assertNotIn("123,456", note)
        self.assertNotIn("234,567", note)
        self.assertNotIn("questionable", note)
        self.assertIn("장부를 얼핏 보니", note)

    def test_app_judgment_returns_frontend_tones(self) -> None:
        result = app_judgment(
            entries=[
                {"entry_kind": "expense", "amount_value": 10_000, "spending_category": "dignity"},
            ],
            panels=[
                {"id": 1, "panel_type": "claim", "title": "세탁비", "amount_value": 10_000, "discount_amount": 0},
                {"id": 2, "panel_type": "family_card", "title": "가족카드", "amount_value": 20_000},
            ],
            cash_flows=[],
            summary={},
            payment_status={
                "due_date": "2026-06-14",
                "recorded_remaining_total": 0,
                "primary_income_total": 400_000,
            },
            settings={"card_limit": "5800000", "base_next_month_liquidity": "400000"},
        )

        self.assertEqual(result["category_labels"]["dignity"], "최소한의 품위유지비")
        self.assertEqual(result["claim_categories"], {})
        self.assertIn("budget", result)
        self.assertIn("payment", result)


if __name__ == "__main__":
    unittest.main()

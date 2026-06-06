import unittest

from app.services.judgment import (
    app_judgment,
    claim_subtitle,
    ledger_verdict,
    settlement_subtitle,
    stable_choice,
)


class JudgmentTest(unittest.TestCase):
    def test_stable_choice_keeps_same_verdict_for_same_state(self) -> None:
        messages = ("첫째", "둘째", "셋째")

        self.assertEqual(
            stable_choice(messages, 10, 20, "상태"),
            stable_choice(messages, 10, 20, "상태"),
        )

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
        self.assertIn("평", routine)

    def test_settlement_subtitle_distinguishes_usage_pressure(self) -> None:
        rows = [{"title": "가족카드", "amount_value": 500_000}]

        quiet = settlement_subtitle(rows, 500_000, 0, 5_800_000)
        danger = settlement_subtitle(rows, 500_000, 4_300_000, 5_800_000)

        self.assertNotEqual(quiet, danger)

    def test_ledger_verdict_distinguishes_questionable_spending(self) -> None:
        ordinary = ledger_verdict(200_000, 50_000, 0)
        hearing = ledger_verdict(200_000, 50_000, 8)

        self.assertNotEqual(ordinary, hearing)

    def test_app_judgment_returns_frontend_tones(self) -> None:
        result = app_judgment(
            entries=[
                {"entry_kind": "expense", "amount_value": 10_000, "spending_category": "dignity"},
            ],
            panels=[
                {"id": 1, "panel_type": "claim", "title": "세탁비", "amount_value": 10_000, "discount_amount": 0},
                {"id": 2, "panel_type": "settlement", "title": "가족카드", "amount_value": 20_000},
            ],
            cash_flows=[],
            summary={"installment_monthly_total": 0},
            payment_status={
                "due_date": "2026-06-14",
                "recorded_remaining_total": 0,
                "primary_income_total": 400_000,
            },
            settings={"settlement_card_limit": "5800000", "base_next_month_liquidity": "400000"},
        )

        self.assertEqual(result["category_labels"]["dignity"], "최소한의 품위유지비")
        self.assertEqual(result["claim_categories"], {})
        self.assertIn("budget", result)
        self.assertIn("payment", result)


if __name__ == "__main__":
    unittest.main()

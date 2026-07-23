import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repository import confirm_planned_entry
from app.schemas import CardPaymentAllocationIn, CardPaymentEventIn
from app.services.card_payments import create_card_payment_event, create_month_close_card_payment_batch
from app.services.summary import current_summary_values, panel_net_total


class SummaryCalculationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "money-note.sqlite3"
        self.env = patch.dict(os.environ, {"MONEY_NOTE_DB_PATH": str(self.db_path)})
        self.env.start()
        get_settings.cache_clear()
        init_db()

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_claim_total_does_not_reduce_next_month_liquidity(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value, sort_order, payment_key
                )
                VALUES ('current', 'expense', '2026-06-05', '본인 카드', 100000, 1, 'owner-card')
                """
            )
            conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'claim', '가족 청구', 50000, 1)
                """
            )

        summary = current_summary_values()

        self.assertEqual(summary["card_total"], 98_800)
        self.assertEqual(summary["current_spending_total"], 100_000)
        self.assertEqual(summary["current_discount_total"], 1_200)
        self.assertEqual(summary["claim_original_total"], 50_000)
        self.assertEqual(summary["claim_net_total"], 49_400)
        self.assertEqual(panel_net_total("claim"), 49_400)
        self.assertEqual(summary["next_month_liquidity"], 301_200)

    def test_family_card_total_uses_family_discount_policy(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'family_card', '가족카드', 100000, 1)
                """
            )

        self.assertEqual(panel_net_total("family_card"), 100_000)

        with session() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO app_settings(key, value, updated_at)
                VALUES ('card_discount_policy:family:2026-06', 'enabled', CURRENT_TIMESTAMP)
                """
            )

        self.assertEqual(panel_net_total("family_card"), 98_800)

    def test_claim_and_family_card_do_not_affect_core_summary(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES
                    ('2026-06', 'claim', '집에 청구할 돈', 80000, 1),
                    ('2026-06', 'family_card', '가족카드 사용액', 90000, 2)
                """
            )

        summary = current_summary_values()

        self.assertEqual(summary["card_total"], 0)
        self.assertEqual(summary["transfer_or_deposit_total"], 0)
        self.assertEqual(summary["frozen_asset_total"], 0)
        self.assertEqual(summary["next_month_liquidity"], 400_000)
        self.assertEqual(summary["claim_original_total"], 80_000)
        self.assertEqual(summary["family_card_original_total"], 90_000)

    def test_planned_card_payment_counts_as_fixed_until_confirmed(self) -> None:
        with session() as conn:
            planned_id = conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, date_label, group_label, title,
                    usage_place, usage_item, amount_value, sort_order, due_day
                )
                VALUES (
                    'current', 'planned', '카드 정기결제', '카드 정기결제', '[구독] 학습지옥 이용권',
                    '구독', '학습지옥 이용권', 30000, 1, 14
                )
                """
            ).lastrowid

        before = current_summary_values()

        self.assertEqual(before["card_total"], 0)
        self.assertEqual(before["planned_recurring_total"], 30_000)
        self.assertEqual(before["transfer_or_deposit_total"], 30_000)
        self.assertEqual(before["next_month_liquidity"], 370_000)

        confirm_planned_entry(planned_id)
        after = current_summary_values()

        self.assertEqual(after["card_total"], 29_640)
        self.assertEqual(after["planned_recurring_total"], 30_000)
        self.assertEqual(after["transfer_or_deposit_total"], 30_000)
        self.assertEqual(after["next_month_liquidity"], 370_360)

    def test_immediate_card_payment_reduces_cash_liquidity(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value, sort_order, payment_key
                )
                VALUES ('archive', 'expense', '2026-05-05', '전월 카드 사용', 10000, 1, 'paid-key')
                """
            )
            create_month_close_card_payment_batch(conn, "2026-05")

        before = current_summary_values()
        create_card_payment_event(
            CardPaymentEventIn(
                event_date="2026-06-05",
                event_type="immediate",
                allocations=[CardPaymentAllocationIn(entry_payment_key="paid-key", amount_value=5000)],
            )
        )
        after = current_summary_values()

        self.assertEqual(before["liquidity_status"], 0)
        self.assertEqual(after["liquidity_status"], -5_000)
        self.assertEqual(after["next_month_liquidity"], before["next_month_liquidity"] - 5_000)


if __name__ == "__main__":
    unittest.main()

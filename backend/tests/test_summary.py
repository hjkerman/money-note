import os
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repository import confirm_planned_entry
from app.schemas import CardPaymentAllocationIn, CardPaymentEventIn
from app.services.card_payments import (
    acknowledge_liquidity_reset,
    create_card_payment_event,
    create_month_close_card_payment_batch,
    current_payment_status,
    defer_toll_payment,
)
from app.services.month import close_current_month
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

    def test_claim_total_does_not_reduce_remaining_liquidity(self) -> None:
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

        for legacy_key in ("base_next_month_liquidity", "liquidity_status", "next_month_liquidity"):
            self.assertNotIn(legacy_key, summary)
        self.assertEqual(summary["card_total"], 98_800)
        self.assertEqual(summary["current_spending_total"], 100_000)
        self.assertEqual(summary["current_discount_total"], 1_200)
        self.assertEqual(summary["claim_original_total"], 50_000)
        self.assertEqual(summary["claim_net_total"], 49_400)
        self.assertEqual(panel_net_total("claim"), 49_400)
        self.assertEqual(summary["remaining_liquidity"], -98_800)

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

    def test_transit_profile_changes_current_month_total_without_rewriting_past(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value,
                    sort_order, payment_key
                )
                VALUES
                    ('current', 'expense', '2026-07-31', '대중교통', 10000, 1, 'past-transit'),
                    ('current', 'expense', '2026-08-01', '대중교통', 10000, 2, 'current-transit')
                """
            )
            conn.executemany(
                """
                INSERT INTO app_settings(key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    ("card_charge_profile:transit:2026-08", "owner"),
                    ("card_discount_policy:owner:2026-08", "enabled"),
                ),
            )

        summary = current_summary_values()

        self.assertEqual(summary["current_spending_total"], 20_000)
        self.assertEqual(summary["current_discount_total"], 120)
        self.assertEqual(summary["card_total"], 19_880)

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

        self.assertNotIn("interest_expense", summary)
        self.assertEqual(summary["card_total"], 0)
        self.assertEqual(summary["transfer_or_deposit_total"], 0)
        self.assertEqual(summary["frozen_asset_total"], 0)
        self.assertEqual(summary["remaining_liquidity"], 0)
        self.assertEqual(summary["claim_original_total"], 80_000)
        self.assertEqual(summary["family_card_original_total"], 90_000)

    def test_retired_setting_does_not_affect_summary(self) -> None:
        with session() as conn:
            conn.execute("INSERT INTO app_settings(key, value) VALUES ('interest_expense', '50000')")

        summary = current_summary_values()

        self.assertNotIn("interest_expense", summary)
        self.assertEqual(summary["remaining_liquidity"], 0)

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
        self.assertEqual(before["remaining_liquidity"], -30_000)

        confirm_planned_entry(planned_id)
        after = current_summary_values()

        self.assertEqual(after["card_total"], 29_640)
        self.assertEqual(after["planned_recurring_total"], 30_000)
        self.assertEqual(after["transfer_or_deposit_total"], 30_000)
        self.assertEqual(after["remaining_liquidity"], -29_640)

    def test_month_close_and_immediate_payments_keep_card_liability_counted_once(self) -> None:
        with session() as conn:
            conn.execute(
                "UPDATE app_settings SET value = '0' WHERE key = 'scheduled_income'"
            )
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value,
                    aux_amount_value, discount_override, sort_order, payment_key
                )
                VALUES ('current', 'expense', '2026-08-20', '당월 카드 사용', 100000, 0, 1, 1, 'close-key')
                """
            )

        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-08-31"}):
            get_settings.cache_clear()
            before_close = current_summary_values()
            close_current_month(
                date(2026, 8, 31),
                allow_early_close=True,
                target_month="2026-08",
            )
            after_close = current_summary_values()
            after_close_status = current_payment_status(date(2026, 8, 31))

            create_card_payment_event(
                CardPaymentEventIn(
                    idempotency_key="summary-close-payment-0001",
                    event_date="2026-08-31",
                    event_type="immediate",
                    allocations=[
                        CardPaymentAllocationIn(entry_payment_key="close-key", amount_value=40_000)
                    ],
                )
            )
            after_partial_payment = current_summary_values()
            partial_status = current_payment_status(date(2026, 8, 31))

            create_card_payment_event(
                CardPaymentEventIn(
                    idempotency_key="summary-close-payment-0002",
                    event_date="2026-08-31",
                    event_type="immediate",
                    allocations=[
                        CardPaymentAllocationIn(entry_payment_key="close-key", amount_value=60_000)
                    ],
                )
            )
            after_full_payment = current_summary_values()
            full_status = current_payment_status(date(2026, 8, 31))
        get_settings.cache_clear()

        self.assertEqual(before_close["card_total"], 100_000)
        self.assertEqual(before_close["remaining_liquidity"], -100_000)
        self.assertEqual(after_close["card_total"], 0)
        self.assertEqual(after_close_status["recorded_remaining_total"], 100_000)
        self.assertEqual(after_close["remaining_liquidity"], before_close["remaining_liquidity"])

        self.assertEqual(after_partial_payment["cash_flow_balance"], -40_000)
        self.assertEqual(partial_status["recorded_remaining_total"], 60_000)
        self.assertEqual(after_partial_payment["remaining_liquidity"], after_close["remaining_liquidity"])

        self.assertEqual(after_full_payment["cash_flow_balance"], -100_000)
        self.assertEqual(full_status["recorded_remaining_total"], 0)
        self.assertEqual(after_full_payment["remaining_liquidity"], after_close["remaining_liquidity"])

    def test_immediate_card_payment_replaces_unpaid_liability_with_cash_outflow(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value,
                    aux_amount_value, discount_override, sort_order, payment_key
                )
                VALUES ('archive', 'expense', '2026-05-05', '전월 카드 사용', 10000, 0, 1, 1, 'paid-key')
                """
            )
            create_month_close_card_payment_batch(conn, "2026-05")

        before = current_summary_values()
        create_card_payment_event(
            CardPaymentEventIn(
                idempotency_key="summary-payment-0001",
                event_date="2026-06-05",
                event_type="immediate",
                allocations=[CardPaymentAllocationIn(entry_payment_key="paid-key", amount_value=5000)],
            )
        )
        after = current_summary_values()

        self.assertEqual(before["cash_flow_balance"], 0)
        self.assertEqual(before["remaining_liquidity"], -10_000)
        self.assertEqual(after["cash_flow_balance"], -5_000)
        self.assertEqual(current_payment_status()["recorded_remaining_total"], 5_000)
        self.assertEqual(after["remaining_liquidity"], before["remaining_liquidity"])

    def test_deferred_card_liability_moves_from_active_batch_to_current_ledger(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value,
                    aux_amount_value, discount_override, sort_order, payment_key
                )
                VALUES ('archive', 'expense', '2026-05-05', '이월할 카드 사용', 10000, 0, 1, 1, 'defer-key')
                """
            )
            create_month_close_card_payment_batch(conn, "2026-05")

        before = current_summary_values()
        defer_toll_payment("defer-key", date(2026, 6, 4))
        after = current_summary_values()
        status = current_payment_status(date(2026, 6, 4))

        self.assertEqual(before["card_total"], 0)
        self.assertEqual(status["recorded_remaining_total"], 0)
        self.assertEqual(after["card_total"], 10_000)
        self.assertEqual(after["remaining_liquidity"], before["remaining_liquidity"])

    def test_acknowledged_statement_payment_uses_reconciled_cash_balance_only(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value,
                    aux_amount_value, discount_override, sort_order, payment_key
                )
                VALUES ('archive', 'expense', '2026-05-05', '정기 카드 결제', 10000, 0, 1, 1, 'settled-key')
                """
            )
            create_month_close_card_payment_batch(conn, "2026-05")

        before_reconciliation = current_summary_values()
        with session() as conn:
            conn.execute(
                "UPDATE app_settings SET value = '-10000' WHERE key = 'cash_flow_balance'"
            )
        before_acknowledgment = current_summary_values()
        acknowledge_liquidity_reset(date(2026, 6, 15))
        after_acknowledgment = current_summary_values()

        self.assertEqual(before_reconciliation["remaining_liquidity"], -10_000)
        self.assertEqual(before_acknowledgment["remaining_liquidity"], -20_000)
        self.assertEqual(current_payment_status(date(2026, 6, 15))["recorded_remaining_total"], 10_000)
        self.assertEqual(after_acknowledgment["cash_flow_balance"], -10_000)
        self.assertEqual(after_acknowledgment["remaining_liquidity"], -10_000)

    def test_future_cash_flow_is_excluded_until_its_occurrence_date(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order, is_primary_income)
                VALUES
                    ('2026-07-26', '이미 발생한 입금', 1000, 1, 0),
                    ('2026-08-01', '미래 급여', 5000, 2, 1)
                """
            )

        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-07-27"}):
            get_settings.cache_clear()
            before_occurrence = current_summary_values()
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-08-01"}):
            get_settings.cache_clear()
            on_occurrence = current_summary_values()
        get_settings.cache_clear()

        self.assertEqual(before_occurrence["cash_flow_balance"], 1_000)
        self.assertEqual(before_occurrence["remaining_liquidity"], 1_000)
        self.assertEqual(on_occurrence["cash_flow_balance"], 6_000)
        self.assertEqual(on_occurrence["remaining_liquidity"], 6_000)


if __name__ == "__main__":
    unittest.main()

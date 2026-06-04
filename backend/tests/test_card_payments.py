from datetime import date
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.schemas import CardPaymentAllocationIn, CardPaymentEventIn, LateCardEntryIn
from app.services.card_payments import (
    cancel_toll_deferral,
    create_card_payment_event,
    current_payment_status,
    create_late_card_entry,
    defer_toll_payment,
    discount_month_status,
    set_discount_month_policy,
)


class CardPaymentDeferralTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "money-note.sqlite3"
        self.env = patch.dict(os.environ, {"MONEY_NOTE_DB_PATH": str(self.db_path)})
        self.env.start()
        get_settings.cache_clear()
        init_db()
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, date_label, title,
                    amount_value, sort_order, payment_key
                )
                VALUES
                    ('archive', 'expense', '2026-05-02', '2026.05.02.', '일반 사용', 10000, 1, 'normal-key'),
                    ('archive', 'expense', '2026-05-03', '2026.05.03.', '고속도로 하이패스', 5000, 2, 'toll-key')
                """
            )

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_deferral_excludes_current_total_and_carries_to_next_month_front(self) -> None:
        defer_toll_payment("toll-key", date(2026, 6, 4))

        june = current_payment_status(date(2026, 6, 4))
        deferred = next(row for row in june["rows"] if row["payment_key"] == "toll-key")
        self.assertTrue(deferred["is_deferred"])
        self.assertEqual(deferred["book_section"], "current")
        self.assertEqual(deferred["entry_date"], "2026-06-01")
        self.assertEqual(deferred["date_label"], "")
        self.assertTrue(deferred["title"].startswith("[이월]"))
        self.assertEqual(june["original_total"], 10_000)

        july = current_payment_status(date(2026, 7, 4))
        self.assertEqual(july["rows"][0]["payment_key"], "toll-key")
        self.assertTrue(july["rows"][0]["is_carried_over"])
        self.assertFalse(july["rows"][0]["is_deferred"])
        self.assertEqual(july["original_total"], 5_000)

    def test_current_month_processing_cancels_deferral(self) -> None:
        defer_toll_payment("toll-key", date(2026, 6, 4))

        self.assertTrue(cancel_toll_deferral("toll-key", date(2026, 6, 4)))
        row = next(
            row for row in current_payment_status(date(2026, 6, 4))["rows"]
            if row["payment_key"] == "toll-key"
        )
        self.assertFalse(row["is_deferred"])
        self.assertEqual(row["book_section"], "archive")
        self.assertEqual(row["entry_date"], "2026-05-03")
        self.assertEqual(row["date_label"], "2026.05.03.")
        self.assertEqual(row["title"], "고속도로 하이패스")

    def test_non_toll_or_fully_paid_entry_cannot_be_deferred(self) -> None:
        with self.assertRaisesRegex(ValueError, "통행료 또는 하이패스"):
            defer_toll_payment("normal-key", date(2026, 6, 4))

        create_card_payment_event(
            CardPaymentEventIn(
                event_date="2026-06-04",
                event_type="immediate",
                allocations=[
                    CardPaymentAllocationIn(entry_payment_key="toll-key", amount_value=5_000)
                ],
            ),
            date(2026, 6, 4),
        )
        with self.assertRaisesRegex(ValueError, "이미 일부결제"):
            defer_toll_payment("toll-key", date(2026, 6, 4))

    def test_toll_rejects_discount_and_partial_payment(self) -> None:
        with self.assertRaisesRegex(ValueError, "할인액"):
            create_card_payment_event(
                CardPaymentEventIn(
                    event_date="2026-06-04",
                    event_type="discount",
                    allocations=[
                        CardPaymentAllocationIn(entry_payment_key="toll-key", amount_value=5_000)
                    ],
                ),
                date(2026, 6, 4),
            )
        with self.assertRaisesRegex(ValueError, "전액만"):
            create_card_payment_event(
                CardPaymentEventIn(
                    event_date="2026-06-04",
                    event_type="immediate",
                    allocations=[
                        CardPaymentAllocationIn(entry_payment_key="toll-key", amount_value=1_000)
                    ],
                ),
                date(2026, 6, 4),
            )

    def test_discount_policy_is_separate_for_owner_and_family_cards(self) -> None:
        set_discount_month_policy("2026-05", "disabled", "owner")
        set_discount_month_policy("2026-05", "enabled", "family")

        self.assertEqual(discount_month_status("2026-05", "owner")["policy"], "disabled")
        self.assertEqual(discount_month_status("2026-05", "family")["policy"], "enabled")

    def test_current_entry_discount_is_recorded_and_blocked_only_when_policy_disabled(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, date_label, title,
                    amount_value, sort_order, payment_key
                )
                VALUES ('current', 'expense', '2026-06-20', '2026.06.20.', '당월 할인', 10000, 3, 'current-key')
                """
            )
        create_card_payment_event(
            CardPaymentEventIn(
                event_date="2026-06-20",
                event_type="discount",
                allocations=[CardPaymentAllocationIn(entry_payment_key="current-key", amount_value=120)],
            ),
            date(2026, 6, 20),
        )
        self.assertEqual(discount_month_status("2026-06", "owner")["discounts"]["current-key"], 120)

        set_discount_month_policy("2026-06", "disabled", "owner")
        with self.assertRaisesRegex(ValueError, "할인 혜택이 없는 달"):
            create_card_payment_event(
                CardPaymentEventIn(
                    event_date="2026-06-20",
                    event_type="discount",
                    allocations=[CardPaymentAllocationIn(entry_payment_key="current-key", amount_value=100)],
                ),
                date(2026, 6, 20),
            )

    def test_deferral_is_blocked_after_due_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "14일까지"):
            defer_toll_payment("toll-key", date(2026, 6, 15))

    def test_deferral_becomes_final_after_due_date(self) -> None:
        defer_toll_payment("toll-key", date(2026, 6, 14))

        with self.assertRaisesRegex(ValueError, "14일까지만"):
            cancel_toll_deferral("toll-key", date(2026, 6, 15))

    def test_late_previous_month_entry_joins_current_payment_targets(self) -> None:
        entry = create_late_card_entry(
            LateCardEntryIn(
                entry_date="2026-05-31",
                usage_place="카드사 지연매입",
                usage_item="월말 소비",
                amount_value=12_345,
            ),
            date(2026, 6, 4),
        )

        self.assertEqual(entry["book_section"], "archive")
        self.assertEqual(entry["entry_kind"], "late_expense")
        rows = current_payment_status(date(2026, 6, 4))["rows"]
        late = next(row for row in rows if row["id"] == entry["id"])
        self.assertEqual(late["amount_value"], 12_345)
        self.assertEqual(late["title"], "[카드사 지연매입] 월말 소비")

    def test_late_entry_rejects_non_previous_month_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "직전월 날짜"):
            create_late_card_entry(
                LateCardEntryIn(
                    entry_date="2026-06-01",
                    usage_place="카드사",
                    usage_item="날짜 오류",
                    amount_value=10_000,
                ),
                date(2026, 6, 4),
            )


if __name__ == "__main__":
    unittest.main()

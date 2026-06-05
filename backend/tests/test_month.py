from datetime import date
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repository import confirm_planned_entry, create_entry, list_entries
from app.schemas import LedgerEntryIn
from app.services.month import close_current_month, month_close_status


class MonthCloseTest(unittest.TestCase):
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
                    ('current', 'expense', '2026-06-30', '2026.06.30.', '말일 사용', 10000, 1, 'june-key'),
                    ('current', 'expense', '2026-07-01', '2026.07.01.', '새 달 사용', 20000, 2, 'july-key'),
                    ('current', 'planned', NULL, '카드 정기결제', '정기결제', 30000, 3, NULL)
                """
            )

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_status_warns_about_oldest_open_month(self) -> None:
        status = month_close_status(date(2026, 7, 1))

        self.assertTrue(status["needs_close"])
        self.assertEqual(status["oldest_open_month"], "2026-06")

    def test_close_archives_only_oldest_month(self) -> None:
        result = close_current_month(date(2026, 7, 1))

        self.assertEqual(result["closed_month"], "2026-06")
        self.assertEqual(result["archived"], 1)
        with session() as conn:
            june = conn.execute(
                "SELECT book_section FROM ledger_entries WHERE payment_key = 'june-key'"
            ).fetchone()
            july = conn.execute(
                "SELECT book_section FROM ledger_entries WHERE payment_key = 'july-key'"
            ).fetchone()
            planned = conn.execute(
                "SELECT COUNT(*) AS count FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["count"]
        self.assertEqual(june["book_section"], "archive")
        self.assertEqual(july["book_section"], "current")
        self.assertEqual(planned, 1)
        self.assertFalse(month_close_status(date(2026, 7, 1))["needs_close"])

    def test_current_calendar_month_cannot_be_closed_before_27th(self) -> None:
        close_current_month(date(2026, 7, 1))

        with self.assertRaisesRegex(ValueError, "27일부터"):
            close_current_month(date(2026, 7, 26), allow_early_close=True)

    def test_current_calendar_month_can_be_closed_early_with_explicit_confirmation(self) -> None:
        close_current_month(date(2026, 7, 1))

        with self.assertRaisesRegex(ValueError, "명시적인 확인"):
            close_current_month(date(2026, 7, 27))

        result = close_current_month(date(2026, 7, 27), allow_early_close=True)
        self.assertEqual(result["closed_month"], "2026-07")
        self.assertEqual(result["archived"], 1)

    def test_planned_confirmation_stays_hidden_after_early_close_until_next_month(self) -> None:
        close_current_month(date(2026, 7, 1))
        with session() as conn:
            planned_id = conn.execute(
                "SELECT id FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["id"]

        confirm_planned_entry(planned_id, date(2026, 7, 10))
        self.assertFalse(
            any(entry["id"] == planned_id for entry in list_entries("current", date(2026, 7, 10)))
        )

        close_current_month(date(2026, 7, 27), allow_early_close=True)
        self.assertFalse(
            any(entry["id"] == planned_id for entry in list_entries("current", date(2026, 7, 28)))
        )
        with self.assertRaisesRegex(ValueError, "already confirmed"):
            confirm_planned_entry(planned_id, date(2026, 7, 28))

        self.assertTrue(
            any(entry["id"] == planned_id for entry in list_entries("current", date(2026, 8, 1)))
        )

    def test_entry_for_closed_month_is_added_to_archive(self) -> None:
        close_current_month(date(2026, 7, 1))
        close_current_month(date(2026, 7, 27), allow_early_close=True)

        entry = create_entry(
            LedgerEntryIn(
                book_section="current",
                entry_kind="expense",
                entry_date="2026-07-31",
                date_label="2026.07.31.",
                title="[카드사] 마감 후 매입",
                usage_place="카드사",
                amount_value=12_345,
                sort_order=99,
            )
        )

        self.assertEqual(entry["book_section"], "archive")
        self.assertEqual(entry["entry_date"], "2026-07-31")


if __name__ == "__main__":
    unittest.main()

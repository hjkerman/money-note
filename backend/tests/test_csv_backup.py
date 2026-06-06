import base64
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.services.csv_backup import export_csv_backup, import_csv_backup


class CsvBackupTest(unittest.TestCase):
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

    def test_single_csv_dump_preserves_discount_state(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value,
                    sort_order, payment_key, discount_override
                )
                VALUES ('current', 'expense', '2026-06-05', '할인 보존', 10000, 1, 'discount-key', 1)
                """
            )
            event_id = conn.execute(
                """
                INSERT INTO card_payment_events(event_date, event_type, total_amount, note)
                VALUES ('2026-06-05', 'discount', 120, '기존 할인')
                """
            ).lastrowid
            conn.execute(
                """
                INSERT INTO card_payment_allocations(payment_event_id, entry_payment_key, amount_value)
                VALUES (?, 'discount-key', 120)
                """,
                (event_id,),
            )

        filename, payload = export_csv_backup()
        self.assertTrue(filename.endswith(".csv"))
        self.assertIn(b"ledger_entries", payload)

        with session() as conn:
            conn.execute("DELETE FROM card_payment_allocations")
            conn.execute("DELETE FROM card_payment_events")
            conn.execute("DELETE FROM ledger_entries")

        result = import_csv_backup(base64.b64encode(payload).decode("ascii"))

        self.assertEqual(result["ledger_entries"], 1)
        with session() as conn:
            entry = conn.execute("SELECT * FROM ledger_entries WHERE payment_key = 'discount-key'").fetchone()
            allocation = conn.execute(
                "SELECT * FROM card_payment_allocations WHERE entry_payment_key = 'discount-key'"
            ).fetchone()
        self.assertEqual(entry["discount_override"], 1)
        self.assertEqual(allocation["amount_value"], 120)


if __name__ == "__main__":
    unittest.main()

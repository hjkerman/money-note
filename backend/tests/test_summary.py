import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
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
        self.assertEqual(panel_net_total("claim"), 49_400)
        self.assertEqual(summary["next_month_liquidity"], 301_200)


if __name__ == "__main__":
    unittest.main()

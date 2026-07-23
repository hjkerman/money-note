import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import list_entries
from app.repositories.panels import list_panels
from app.services.presentation import present_ledger_entries, present_monthly_panels


class ServerPresentationTest(unittest.TestCase):
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

    def test_ledger_discount_and_net_amount_are_computed_by_server(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value,
                    aux_amount_value, sort_order, payment_key, discount_override
                )
                VALUES
                    ('current', 'expense', '2026-07-01', '일반 사용', 10000, NULL, 1, 'normal', 0),
                    ('current', 'expense', '2026-07-02', '고속도로 하이패스', 5000, 1200, 2, 'toll', 1)
                """
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO app_settings(key, value, updated_at)
                VALUES ('card_discount_policy:owner:2026-07', 'enabled', CURRENT_TIMESTAMP)
                """
            )

        rows = {row["payment_key"]: row for row in present_ledger_entries(list_entries("current"))}

        self.assertTrue(rows["normal"]["automatic_discount_eligible"])
        self.assertEqual(rows["normal"]["automatic_discount_amount"], 120)
        self.assertEqual(rows["normal"]["effective_discount_amount"], 120)
        self.assertEqual(rows["normal"]["effective_amount_value"], 9_880)
        self.assertFalse(rows["toll"]["automatic_discount_eligible"])
        self.assertTrue(rows["toll"]["is_toll"])
        self.assertEqual(rows["toll"]["effective_discount_amount"], 1_200)
        self.assertEqual(rows["toll"]["effective_amount_value"], 3_800)

    def test_month_policy_and_panel_scope_are_reflected_in_response(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO monthly_panels(
                    month, panel_type, title, amount_value, discount_amount,
                    discount_override, sort_order
                )
                VALUES
                    ('2026-07', 'claim', '생활비', 10000, 0, 0, 1),
                    ('2026-07', 'family_card', '가족카드', 10000, 0, 0, 2)
                """
            )

        rows = {
            row["panel_type"]: row
            for row in present_monthly_panels(list_panels("2026-07"))
        }

        self.assertEqual(rows["claim"]["discount_policy"], "enabled")
        self.assertEqual(rows["claim"]["effective_discount_amount"], 120)
        self.assertEqual(rows["family_card"]["discount_policy"], "disabled")
        self.assertEqual(rows["family_card"]["effective_discount_amount"], 0)


if __name__ == "__main__":
    unittest.main()

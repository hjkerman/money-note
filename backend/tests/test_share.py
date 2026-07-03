import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.services.share import shared_panel, shared_panel_html


class SharePanelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "money-note.sqlite3"
        self.env = patch.dict(
            os.environ,
            {
                "MONEY_NOTE_DB_PATH": str(self.db_path),
                "MONEY_NOTE_TODAY": "2026-07-03",
            },
        )
        self.env.start()
        get_settings.cache_clear()
        init_db()
        with session() as conn:
            conn.execute(
                """
                INSERT INTO app_settings(key, value)
                VALUES
                    ('card_discount_policy:owner:2026-06', 'disabled'),
                    ('card_discount_policy:owner:2026-07', 'disabled')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )
            conn.execute(
                """
                INSERT INTO monthly_panels(
                    month, panel_type, title, spent_on, amount_value, discount_amount, discount_override, sort_order
                )
                VALUES
                    ('2026-06', 'claim', '지난달 병원비', '2026-06-22', 1000, 100, 1, 1),
                    ('2026-07', 'claim', '이번 달 커피', '2026-07-02', 2000, 200, 1, 2),
                    ('2026-07', 'claim', '전세대출이자', '2026-07-03', 300, 0, 0, 3)
                """
            )

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_shared_panel_reports_minimum_payment_total(self) -> None:
        data = shared_panel("claim")

        self.assertEqual(data["minimum_total"], 1200)
        self.assertEqual(data["minimum_discount_total"], 100)
        self.assertEqual(data["total"], 3000)
        self.assertEqual(data["discount_total"], 300)

    def test_shared_panel_html_dims_current_month_non_interest_rows(self) -> None:
        html = shared_panel_html("claim")

        self.assertIn("최소 결제", html)
        self.assertIn("전체 보기", html)
        self.assertIn("최소 결제 합계 1,200원", html)
        self.assertIn('data-full="-300원"', html)
        self.assertIn('data-minimum="-100원"', html)
        self.assertIn('data-full="3,000원"', html)
        self.assertIn('data-minimum="1,200원"', html)
        self.assertEqual(html.count('class="deferable-row"'), 1)
        self.assertIn("이번 달 커피", html)


if __name__ == "__main__":
    unittest.main()

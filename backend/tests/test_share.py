import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.share_auth import share_unlock_html
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

        self.assertEqual(data["minimum_payment_month"], "2026-07")
        self.assertEqual(data["minimum_total"], 1200)
        self.assertEqual(data["minimum_discount_total"], 100)
        self.assertEqual(data["total"], 3000)
        self.assertEqual(data["discount_total"], 300)

    def test_minimum_payment_advances_after_earliest_cycle_is_cleared(self) -> None:
        with session() as conn:
            conn.execute(
                """
                DELETE FROM monthly_panels
                WHERE panel_type = 'claim'
                  AND title IN ('지난달 병원비', '전세대출이자')
                """
            )

        data = shared_panel("claim")

        self.assertEqual(data["minimum_payment_month"], "2026-08")
        self.assertEqual(data["minimum_total"], 1800)
        self.assertEqual(data["minimum_discount_total"], 200)
        self.assertIn("2026년 8월 최소 결제 금액: 1,800원", shared_panel_html("claim"))

    def test_interest_exception_applies_only_to_claim(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO monthly_panels(
                    month, panel_type, title, spent_on, amount_value, sort_order
                )
                VALUES
                    ('2026-06', 'family_card', '지난달 가족카드', '2026-06-22', 1000, 1),
                    ('2026-07', 'family_card', '이자라는 단어', '2026-07-03', 300, 2)
                """
            )

        data = shared_panel("family_card")

        self.assertEqual(data["minimum_payment_month"], "2026-07")
        self.assertEqual(data["minimum_total"], 1000)

    def test_december_usage_moves_to_next_year_payment_cycle(self) -> None:
        with session() as conn:
            conn.execute("DELETE FROM monthly_panels WHERE panel_type = 'claim'")
            conn.execute(
                """
                INSERT INTO monthly_panels(
                    month, panel_type, title, spent_on, amount_value,
                    discount_amount, discount_override, sort_order
                )
                VALUES ('2026-12', 'claim', '연말 가족 장보기', '2026-12-28', 5000, 0, 1, 1)
                """
            )

        data = shared_panel("claim")

        self.assertEqual(data["minimum_payment_month"], "2027-01")
        self.assertEqual(data["minimum_total"], 5000)
        self.assertIn("2027년 1월 최소 결제 금액: 5,000원", shared_panel_html("claim"))

    def test_shared_panel_html_dims_current_month_non_interest_rows(self) -> None:
        html = shared_panel_html("claim")

        self.assertIn("최소 결제", html)
        self.assertIn("전체 보기", html)
        self.assertNotIn("<th>사용일</th>", html)
        self.assertIn('<th class="content">내용</th>', html)
        self.assertIn("[06/22] 지난달 병원비", html)
        self.assertIn('class="share-table-wrap"', html)
        self.assertIn("body.minimum-mode tr.deferable-row", html)
        self.assertIn("display: none", html)
        self.assertIn("2026년 7월 최소 결제 금액: 1,200원", html)
        self.assertIn('data-full="-300원"', html)
        self.assertIn('data-minimum="-100원"', html)
        self.assertIn('data-full="3,000원"', html)
        self.assertIn('data-minimum="1,200원"', html)
        self.assertIn('<td>합계</td>\n            <td class="money"></td>', html)
        self.assertEqual(html.count('class="deferable-row"'), 1)
        self.assertIn("이번 달 커피", html)

    def test_share_unlock_redirect_is_safe_inside_inline_script(self) -> None:
        html = share_unlock_html("/share/</script><script>alert(1)</script>")

        self.assertNotIn("</script><script>alert(1)</script>", html)
        self.assertIn(r"\u003c/script\u003e", html)


if __name__ == "__main__":
    unittest.main()

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repository import complete_panels_by_type, create_panel, list_panels, update_panel
from app.schemas import MonthlyPanelIn, MonthlyPanelPatch


class PanelCompletionTest(unittest.TestCase):
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
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES
                    ('2026-06', 'claim', '청구 하나', 1000, 1),
                    ('2026-06', 'claim', '청구 둘', 2000, 2),
                    ('2026-06', 'family_card', '가족카드 하나', 3000, 1),
                    ('2026-06', 'frozen', '동결 하나', 4000, 1)
                """
            )

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_bulk_completion_deletes_only_selected_delivery_queue(self) -> None:
        completed = complete_panels_by_type("2026-06", "claim")

        self.assertEqual(completed, 2)
        backups = list((self.db_path.parent / "snapshot-backups").glob("pre_restore-*.money-note-snapshot.json"))
        self.assertEqual(len(backups), 1)
        self.assertIn("청구 하나", backups[0].read_text(encoding="utf-8"))
        with session() as conn:
            remaining = conn.execute(
                "SELECT panel_type, COUNT(*) AS count FROM monthly_panels GROUP BY panel_type ORDER BY panel_type"
            ).fetchall()
        self.assertEqual([(row["panel_type"], row["count"]) for row in remaining], [("family_card", 1), ("frozen", 1)])

    def test_claim_discount_is_stored_separately_from_original_amount(self) -> None:
        updated = update_panel(1, MonthlyPanelPatch(discount_amount=120))

        self.assertEqual(updated["amount_value"], 1000)
        self.assertEqual(updated["discount_amount"], 120)

    def test_panel_special_characters_round_trip(self) -> None:
        title = "[병원] O'Reilly <진료> & 약값 / 괄호()"
        created = create_panel(
            MonthlyPanelIn(
                month="2026-06",
                panel_type="claim",
                title=title,
                spent_on="2026-06-11",
                amount_value=1234,
                sort_order=9,
            )
        )

        self.assertEqual(created["title"], title)
        listed = list_panels("2026-06")
        self.assertTrue(any(panel["title"] == title for panel in listed))

    def test_frozen_panel_requires_registration_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "등록일자"):
            create_panel(
                MonthlyPanelIn(
                    month="2026-06",
                    panel_type="frozen",
                    title="묶어둘 돈",
                    amount_value=5000,
                    sort_order=10,
                )
            )

    def test_frozen_panel_stores_registration_date(self) -> None:
        created = create_panel(
            MonthlyPanelIn(
                month="2026-06",
                panel_type="frozen",
                title="묶어둘 돈",
                spent_on="2026-06-18",
                amount_value=5000,
                sort_order=10,
            )
        )

        self.assertEqual(created["spent_on"], "2026-06-18")


if __name__ == "__main__":
    unittest.main()

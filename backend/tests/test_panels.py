import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repository import (
    complete_panels_by_type,
    confirm_fixed_panel,
    create_panel,
    delete_cash_flow,
    list_panels,
)
from app.repositories.panels import set_panel_discount
from app.schemas import MonthlyPanelIn, MonthlyPanelPatch
from app.services.summary import current_summary_values


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

    def test_persistent_panels_remain_visible_across_calendar_months(self) -> None:
        listed = list_panels("2026-07")

        titles = {panel["title"] for panel in listed}
        self.assertIn("청구 하나", titles)
        self.assertIn("청구 둘", titles)
        self.assertIn("가족카드 하나", titles)
        self.assertIn("동결 하나", titles)

    def test_bulk_completion_deletes_claim_queue_across_months(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-05', 'claim', '지난달 미처리 청구', 9000, 0)
                """
            )

        completed = complete_panels_by_type("2026-07", "claim")

        self.assertEqual(completed, 3)
        with session() as conn:
            remaining_claims = conn.execute(
                "SELECT COUNT(*) AS count FROM monthly_panels WHERE panel_type = 'claim'"
            ).fetchone()["count"]
            remaining_family_card = conn.execute(
                "SELECT COUNT(*) AS count FROM monthly_panels WHERE panel_type = 'family_card'"
            ).fetchone()["count"]
        self.assertEqual(remaining_claims, 0)
        self.assertEqual(remaining_family_card, 1)

    def test_claim_discount_is_stored_separately_from_original_amount(self) -> None:
        updated = set_panel_discount(1, 120, 1)

        self.assertEqual(updated["amount_value"], 1000)
        self.assertEqual(updated["discount_amount"], 120)

    def test_generic_panel_patch_rejects_state_transition_fields(self) -> None:
        with self.assertRaises(ValueError):
            MonthlyPanelPatch(panel_type="family_card")
        with self.assertRaises(ValueError):
            MonthlyPanelPatch(confirmed_at="2026-06-01T00:00:00Z")

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

    def test_fixed_confirmation_moves_pending_obligation_to_cash_flow_once(self) -> None:
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '월세', 100000, 20)
                """
            ).lastrowid

        before = current_summary_values()
        result = confirm_fixed_panel(panel_id, "2026-06-20")
        after = current_summary_values()

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["cash_flow"]["occurred_on"], "2026-06-20")
        self.assertEqual(result["cash_flow"]["amount_value"], -100000)
        self.assertEqual(result["panel"]["spent_on"], "2026-06-20")
        self.assertEqual(
            result["panel"]["confirmed_cash_flow_id"],
            result["cash_flow"]["id"],
        )
        self.assertEqual(before["remaining_liquidity"], after["remaining_liquidity"])
        self.assertEqual(before["fixed_cash_total"], after["fixed_cash_total"])
        self.assertEqual(
            after["cash_flow_balance"],
            before["cash_flow_balance"] - 100000,
        )
        self.assertFalse(any(row["id"] == panel_id for row in list_panels("2026-06")))
        self.assertTrue(
            any(
                row["id"] == panel_id
                for row in list_panels("2026-06", include_confirmed_fixed=True)
            )
        )

    def test_fixed_confirmation_releases_unused_reserve_without_changing_template(self) -> None:
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '공과금', 150000, 25)
                """
            ).lastrowid

        before = current_summary_values()
        result = confirm_fixed_panel(panel_id, "2026-06-20", actual_amount=112430)
        after = current_summary_values()

        assert result is not None
        self.assertEqual(result["panel"]["amount_value"], 150000)
        self.assertEqual(result["panel"]["confirmed_amount_value"], 112430)
        self.assertEqual(result["cash_flow"]["amount_value"], -112430)
        self.assertEqual(after["remaining_liquidity"], before["remaining_liquidity"] + 37570)
        listed = list_panels("2026-06", include_confirmed_fixed=True)
        confirmed = next(row for row in listed if row["id"] == panel_id)
        self.assertEqual(confirmed["amount_value"], 150000)
        self.assertEqual(confirmed["confirmed_amount_value"], 112430)

    def test_fixed_confirmation_charges_actual_amount_above_reserve(self) -> None:
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '변동 공과금', 150000, 26)
                """
            ).lastrowid

        before = current_summary_values()
        result = confirm_fixed_panel(panel_id, "2026-06-20", actual_amount=162000)
        after = current_summary_values()

        assert result is not None
        self.assertEqual(result["panel"]["amount_value"], 150000)
        self.assertEqual(result["cash_flow"]["amount_value"], -162000)
        self.assertEqual(after["remaining_liquidity"], before["remaining_liquidity"] - 12000)

    def test_zero_actual_fixed_expense_is_an_explicit_confirmation(self) -> None:
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '이번 달 미발생', 25000, 27)
                """
            ).lastrowid

        before = current_summary_values()
        result = confirm_fixed_panel(panel_id, "2026-06-20", actual_amount=0)
        after = current_summary_values()

        assert result is not None
        self.assertEqual(result["cash_flow"]["amount_value"], 0)
        self.assertEqual(after["remaining_liquidity"], before["remaining_liquidity"] + 25000)

    def test_deleting_actual_generated_cash_flow_restores_original_reserve(self) -> None:
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '실제액 취소', 150000, 28)
                """
            ).lastrowid
        before = current_summary_values()
        result = confirm_fixed_panel(panel_id, "2026-06-20", actual_amount=112430)
        assert result is not None

        self.assertTrue(delete_cash_flow(result["cash_flow"]["id"]))
        restored = current_summary_values()

        self.assertEqual(restored["remaining_liquidity"], before["remaining_liquidity"])
        with session() as conn:
            panel = conn.execute(
                "SELECT amount_value, confirmed_cash_flow_id FROM monthly_panels WHERE id = ?",
                (panel_id,),
            ).fetchone()
        self.assertEqual(panel["amount_value"], 150000)
        self.assertIsNone(panel["confirmed_cash_flow_id"])

    def test_deleting_generated_cash_flow_restores_pending_fixed_obligation(self) -> None:
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '관리비', 50000, 21)
                """
            ).lastrowid
        before = current_summary_values()
        result = confirm_fixed_panel(panel_id, "2026-06-21")
        assert result is not None

        self.assertTrue(delete_cash_flow(result["cash_flow"]["id"]))
        after_delete = current_summary_values()

        self.assertEqual(after_delete["remaining_liquidity"], before["remaining_liquidity"])
        with session() as conn:
            panel = conn.execute(
                """
                SELECT spent_on, confirmed_at, confirmed_cash_flow_id
                FROM monthly_panels WHERE id = ?
                """,
                (panel_id,),
            ).fetchone()
        self.assertIsNone(panel["spent_on"])
        self.assertIsNone(panel["confirmed_at"])
        self.assertIsNone(panel["confirmed_cash_flow_id"])

    def test_fixed_confirmation_rejects_duplicate_processing(self) -> None:
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '보험료', 30000, 22)
                """
            ).lastrowid
        confirm_fixed_panel(panel_id, "2026-06-22")

        with self.assertRaisesRegex(ValueError, "이미 확인 처리"):
            confirm_fixed_panel(panel_id, "2026-06-22")

    def test_fixed_confirmation_rejects_future_processing_date(self) -> None:
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '미래 보험료', 30000, 24)
                """
            ).lastrowid

        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-06-20"}):
            get_settings.cache_clear()
            with self.assertRaisesRegex(ValueError, "미래 날짜"):
                confirm_fixed_panel(panel_id, "2026-06-21")
        get_settings.cache_clear()

        with session() as conn:
            panel = conn.execute(
                "SELECT confirmed_cash_flow_id FROM monthly_panels WHERE id = ?",
                (panel_id,),
            ).fetchone()
            flow_count = conn.execute(
                "SELECT COUNT(*) AS count FROM cash_flows WHERE title = '미래 보험료'",
            ).fetchone()["count"]
        self.assertIsNone(panel["confirmed_cash_flow_id"])
        self.assertEqual(flow_count, 0)

    def test_unlinked_legacy_confirmation_remains_pending_and_can_be_confirmed(self) -> None:
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(
                    month, panel_type, title, amount_value, sort_order, confirmed_at
                )
                VALUES ('2026-06', 'fixed', '구형 고정지출', 12000, 23, '2026-06-01T00:00:00+00:00')
                """
            ).lastrowid

        before = current_summary_values()
        self.assertTrue(any(row["id"] == panel_id for row in list_panels("2026-06")))

        result = confirm_fixed_panel(panel_id, "2026-06-23")
        after = current_summary_values()

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["cash_flow"]["amount_value"], -12000)
        self.assertIsNotNone(result["panel"]["confirmed_cash_flow_id"])
        self.assertEqual(before["remaining_liquidity"], after["remaining_liquidity"])


if __name__ == "__main__":
    unittest.main()

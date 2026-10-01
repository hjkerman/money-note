import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import append_planned_entry, confirm_planned_entry, create_entry
from app.repositories.panels import create_panel
from app.services.card_payments import clear_entry_discount
from app.repositories.panels import set_panel_discount
from app.schemas import LedgerEntryIn, MonthlyPanelIn, PlannedEntryIn
from app.services.presentation import present_ledger_entry, present_monthly_panel, present_planned_charge_preview


class UtilityDiscountDefaultTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "MONEY_NOTE_DB_PATH": str(Path(self.temp_dir.name) / "test.sqlite3"),
            "MONEY_NOTE_TODAY": "2026-10-01",
        })
        self.env.start()
        get_settings.cache_clear()
        init_db()

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def _expense(self, place: str, item: str = "요금", enabled: bool | None = None):
        return present_ledger_entry(create_entry(LedgerEntryIn(
            book_section="current", entry_kind="expense", entry_date="2026-10-01",
            title=f"[{place}] {item}", usage_place=place, usage_item=item,
            amount_value=10_000, sort_order=0, discount_enabled=enabled,
        )))

    def test_place_and_item_keywords_default_to_exclusion(self) -> None:
        for word in ("도시가스", "가스요금", "전기", "전력", "수도"):
            for place, item in ((f"서울{word}요금", "청구"), ("가게", f"{word}요금")):
                with self.subTest(place=place, item=item):
                    row = self._expense(place, item)
                    self.assertEqual(row["effective_amount_value"], 10_000)
                    self.assertEqual(row["effective_discount_amount"], 0)
                    self.assertEqual(row["discount_override"], 1)

    def test_explicit_choice_beats_utility_default_but_not_toll_policy(self) -> None:
        normal = self._expense("서점", "책")
        utility_applied = self._expense("한국전력", enabled=True)
        utility_excluded = self._expense("한국전력", enabled=False)
        toll = self._expense("고속도로 통행료", enabled=True)
        self.assertEqual(normal["effective_amount_value"], 9_880)
        self.assertEqual(utility_applied["effective_amount_value"], 9_880)
        self.assertEqual(utility_applied["discount_override"], 0)
        self.assertEqual(utility_excluded["effective_amount_value"], 10_000)
        self.assertEqual(toll["effective_amount_value"], 10_000)
        with session() as conn:
            saved = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (utility_applied["id"],)).fetchone()
        self.assertEqual(present_ledger_entry(dict(saved))["effective_amount_value"], 9_880)

    def test_claim_and_family_use_original_card_month_policy(self) -> None:
        with session() as conn:
            conn.execute("INSERT INTO app_settings(key, value) VALUES ('card_discount_policy:family:2026-10', 'enabled')")
            conn.execute("INSERT INTO app_settings(key, value) VALUES ('card_discount_policy:owner:2026-09', 'disabled')")
        for panel_type in ("claim", "family_card"):
            with self.subTest(panel_type=panel_type):
                default = present_monthly_panel(create_panel(MonthlyPanelIn(
                    month="2026-10", panel_type=panel_type, title="한국전력 요금",
                    spent_on="2026-10-01", amount_value=10_000, sort_order=0,
                )))
                applied = present_monthly_panel(create_panel(MonthlyPanelIn(
                    month="2026-10", panel_type=panel_type, title="한국전력 요금",
                    spent_on="2026-10-01", amount_value=10_000, sort_order=0,
                    discount_enabled=True,
                )))
                self.assertEqual(default["effective_amount_value"], 10_000)
                self.assertEqual(applied["effective_amount_value"], 9_880)
                self.assertEqual(applied["discount_override"], 0)

    def test_notification_identity_and_edit_preserve_user_choice(self) -> None:
        payload = LedgerEntryIn(
            book_section="current", entry_kind="expense", entry_date="2026-10-01",
            title="[한국전력] 청구", usage_place="한국전력", usage_item="청구",
            amount_value=10_000, sort_order=0,
            candidate_registration_key="woori_card:utility-1",
        )
        first = create_entry(payload)
        self.assertEqual(create_entry(payload)["id"], first["id"])
        payload.discount_enabled = True
        with self.assertRaisesRegex(ValueError, "다른 내용"):
            create_entry(payload)
        self.assertTrue(clear_entry_discount(first["payment_key"]))
        with session() as conn:
            saved = dict(conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (first["id"],)).fetchone())
        self.assertEqual(present_ledger_entry(saved)["effective_amount_value"], 9_880)

        panel = create_panel(MonthlyPanelIn(
            month="2026-10", panel_type="claim", title="도시가스",
            spent_on="2026-10-01", amount_value=10_000, sort_order=0,
            candidate_registration_key="woori_card:utility-panel",
        ))
        self.assertEqual(present_monthly_panel(panel)["effective_amount_value"], 10_000)
        applied = set_panel_discount(panel["id"], 0, 0)
        self.assertEqual(present_monthly_panel(applied)["effective_amount_value"], 9_880)

    def test_transaction_month_policy_is_not_replaced_by_utility_heuristic(self) -> None:
        with session() as conn:
            conn.execute("INSERT INTO app_settings(key, value) VALUES ('card_discount_policy:owner:2026-09', 'disabled')")
        prior = present_ledger_entry(create_entry(LedgerEntryIn(
            book_section="current", entry_kind="expense", entry_date="2026-09-30",
            title="[한국전력] 요금", usage_place="한국전력", usage_item="요금",
            amount_value=10_000, sort_order=0, discount_enabled=True,
        )))
        current = self._expense("한국전력", enabled=True)
        self.assertEqual(prior["effective_amount_value"], 10_000)
        self.assertEqual(current["effective_amount_value"], 9_880)

    def test_recurring_utility_preview_matches_confirmed_card_use(self) -> None:
        planned = append_planned_entry(PlannedEntryIn(
            title="[한국전력] 청구", usage_place="한국전력", usage_item="청구",
            amount_value=10_000, due_day=1,
        ))
        preview = present_planned_charge_preview(planned, 10_000)
        generated = confirm_planned_entry(planned["id"])["entry"]
        self.assertEqual(preview["effective_amount_value"], 10_000)
        self.assertEqual(present_ledger_entry(generated)["effective_amount_value"], 10_000)
        self.assertEqual(generated["discount_override"], 1)


if __name__ == "__main__":
    unittest.main()

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repository import append_planned_entry, create_entry, delete_entry, list_entries, update_entry
from app.schemas import LedgerEntryIn, LedgerEntryPatch, PlannedEntryIn


class EntryConstraintTest(unittest.TestCase):
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

    def test_current_expense_allows_only_usage_item_to_be_missing(self) -> None:
        entry = create_entry(
            LedgerEntryIn(
                book_section="current",
                entry_kind="expense",
                entry_date="2026-06-04",
                usage_place="사용처",
                usage_item=None,
                amount_value=1000,
                sort_order=1,
            )
        )
        self.assertIsNone(entry["usage_item"])

        with self.assertRaisesRegex(ValueError, "usage_place"):
            create_entry(
                LedgerEntryIn(
                    book_section="current",
                    entry_kind="expense",
                    entry_date="2026-06-04",
                    amount_value=1000,
                    sort_order=2,
                )
            )

    def test_patch_cannot_remove_required_field(self) -> None:
        entry = create_entry(
            LedgerEntryIn(
                book_section="current",
                entry_kind="expense",
                entry_date="2026-06-04",
                usage_place="사용처",
                amount_value=1000,
                sort_order=1,
            )
        )
        with self.assertRaisesRegex(ValueError, "amount_value"):
            update_entry(entry["id"], LedgerEntryPatch(amount_value=None))
        with self.assertRaisesRegex(ValueError, "greater than or equal to zero"):
            update_entry(entry["id"], LedgerEntryPatch(amount_value=-1))

    def test_planned_schema_requires_due_day_place_and_amount(self) -> None:
        valid = PlannedEntryIn(
            title="[사용처]",
            usage_place="사용처",
            usage_item=None,
            amount_value=1000,
            due_day=14,
        )
        self.assertIsNone(valid.usage_item)

        with self.assertRaises(ValueError):
            PlannedEntryIn(title="", usage_place="", amount_value=1000, due_day=14)
        with self.assertRaises(ValueError):
            PlannedEntryIn(title="[사용처]", usage_place="사용처", amount_value=-1, due_day=14)

    def test_appended_planned_entry_is_visible_and_survives_init(self) -> None:
        created = append_planned_entry(
            PlannedEntryIn(
                title="[구독] 서버 유지비",
                usage_place="구독",
                usage_item="서버 유지비",
                amount_value=12000,
                due_day=14,
            )
        )

        self.assertEqual(created["book_section"], "current")
        self.assertEqual(created["entry_kind"], "planned")
        self.assertEqual(created["due_day"], 14)

        visible = list_entries("current")
        self.assertTrue(any(entry["id"] == created["id"] for entry in visible))

        init_db()
        visible_after_init = list_entries("current")
        self.assertTrue(any(entry["id"] == created["id"] for entry in visible_after_init))

    def test_delete_entry_cleans_card_payment_allocations_and_cash_flow(self) -> None:
        first = create_entry(
            LedgerEntryIn(
                book_section="archive",
                entry_kind="expense",
                entry_date="2026-05-04",
                usage_place="첫째",
                amount_value=1000,
                sort_order=1,
                payment_key="first-key",
            )
        )
        create_entry(
            LedgerEntryIn(
                book_section="archive",
                entry_kind="expense",
                entry_date="2026-05-04",
                usage_place="둘째",
                amount_value=2000,
                sort_order=2,
                payment_key="second-key",
            )
        )
        with session() as conn:
            cash_flow_id = conn.execute(
                "INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order) VALUES ('2026-06-05', '카드 즉시결제', -3000, 1)"
            ).lastrowid
            event_id = conn.execute(
                "INSERT INTO card_payment_events(event_date, event_type, total_amount, cash_flow_id) VALUES ('2026-06-05', 'immediate', 3000, ?)",
                (cash_flow_id,),
            ).lastrowid
            conn.execute(
                "INSERT INTO card_payment_allocations(payment_event_id, entry_payment_key, amount_value) VALUES (?, 'first-key', 1000)",
                (event_id,),
            )
            conn.execute(
                "INSERT INTO card_payment_allocations(payment_event_id, entry_payment_key, amount_value) VALUES (?, 'second-key', 2000)",
                (event_id,),
            )

        self.assertTrue(delete_entry(first["id"]))

        with session() as conn:
            event = conn.execute("SELECT total_amount FROM card_payment_events WHERE id = ?", (event_id,)).fetchone()
            cash_flow = conn.execute("SELECT amount_value FROM cash_flows WHERE id = ?", (cash_flow_id,)).fetchone()
            allocation_count = conn.execute(
                "SELECT COUNT(*) AS count FROM card_payment_allocations WHERE entry_payment_key = 'first-key'"
            ).fetchone()["count"]
        self.assertEqual(event["total_amount"], 2000)
        self.assertEqual(cash_flow["amount_value"], -2000)
        self.assertEqual(allocation_count, 0)


if __name__ == "__main__":
    unittest.main()

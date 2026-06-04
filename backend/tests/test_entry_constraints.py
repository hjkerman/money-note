import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db
from app.repository import create_entry, update_entry
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


if __name__ == "__main__":
    unittest.main()

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.services.reset import reset_ledger_data


class ResetTest(unittest.TestCase):
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

    def test_reset_writes_pre_restore_before_deleting_ledger_data(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, sort_order)
                VALUES ('current', 'expense', '2026-06-05', '초기화 직전 지출', 1000, 1)
                """
            )

        deleted = reset_ledger_data()

        self.assertEqual(deleted["ledger_entries"], 1)
        backups = list((self.db_path.parent / "snapshot-backups").glob("pre_restore-*.money-note-snapshot.json"))
        self.assertEqual(len(backups), 1)
        self.assertIn("초기화 직전 지출", backups[0].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

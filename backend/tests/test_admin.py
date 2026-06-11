import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.services.reset import reset_ledger_data


class AdminApiTest(unittest.TestCase):
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

    def test_reset_ledger_data_endpoint_is_registered(self) -> None:
        import app.main as main_module

        main_module = importlib.reload(main_module)
        paths = {route.path for route in main_module.app.routes}
        self.assertIn("/api/admin/reset-ledger-data", paths)
        self.assertIn("/api/admin/snapshot", paths)
        self.assertIn("/api/admin/snapshot/restore", paths)

    def test_reset_ledger_data_deletes_ledger_only(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO users(username, password_hash, display_name)
                VALUES ('tester', 'hash', '테스트')
                """
            )
            conn.execute(
                """
                INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, sort_order)
                VALUES ('current', 'expense', '2026-06-05', '초기화 대상', 1000, 1)
                """
            )

        reset_ledger_data()

        with session() as conn:
            entry_count = conn.execute("SELECT COUNT(*) AS count FROM ledger_entries").fetchone()["count"]
            user_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        self.assertEqual(entry_count, 0)
        self.assertEqual(user_count, 1)


if __name__ == "__main__":
    unittest.main()

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db
from app.services.audit import clear_audit_logs, list_audit_logs, record_audit_log


class AuditLogTest(unittest.TestCase):
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

    def test_log_list_and_clear(self) -> None:
        record_audit_log("owner", "POST", "/api/entries", 200)
        record_audit_log("owner", "DELETE", "/api/entries/1", 404)

        rows = list_audit_logs()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["method"], "DELETE")
        self.assertEqual(clear_audit_logs(), 2)
        self.assertEqual(list_audit_logs(), [])


if __name__ == "__main__":
    unittest.main()

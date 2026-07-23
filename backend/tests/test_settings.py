import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db
from app.routers.operations import get_settings_values
from app.share_auth import ensure_default_share_pin


class SettingsVisibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "money-note.sqlite3"
        self.env = patch.dict(os.environ, {"MONEY_NOTE_DB_PATH": str(self.db_path)})
        self.env.start()
        get_settings.cache_clear()
        init_db()
        ensure_default_share_pin()

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_settings_api_projection_excludes_share_pin_state(self) -> None:
        values = get_settings_values({})

        self.assertIn("card_limit", values)
        self.assertNotIn("share_pin_hash", values)
        self.assertNotIn("share_pin_is_default", values)


if __name__ == "__main__":
    unittest.main()

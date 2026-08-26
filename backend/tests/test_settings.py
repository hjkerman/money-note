import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.routers.operations import get_settings_values, patch_setting
from app.schemas import SettingPatch
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
        self.assertEqual(values["scheduled_income"], values["base_next_month_liquidity"])
        self.assertEqual(values["cash_flow_balance"], values["liquidity_status"])
        self.assertNotIn("share_pin_hash", values)
        self.assertNotIn("share_pin_is_default", values)

    def test_setting_alias_updates_compatibility_storage_key(self) -> None:
        income_response = patch_setting("scheduled_income", SettingPatch(value="550000"), {})
        balance_response = patch_setting("cash_flow_balance", SettingPatch(value="12000"), {})

        with session() as conn:
            stored_income = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'base_next_month_liquidity'"
            ).fetchone()
            stored_balance = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'liquidity_status'"
            ).fetchone()

        self.assertEqual(income_response, {"scheduled_income": "550000"})
        self.assertEqual(balance_response, {"cash_flow_balance": "12000"})
        self.assertEqual(stored_income["value"], "550000")
        self.assertEqual(stored_balance["value"], "12000")

    def test_default_liquidity_labels_are_normalized_without_overwriting_custom_label(self) -> None:
        with session() as conn:
            conn.execute(
                "UPDATE app_labels SET value = '익월 유동성' WHERE key = 'summary_next_month_liquidity_label'"
            )
            conn.execute(
                "UPDATE app_labels SET value = '내 통장 사정' WHERE key = 'summary_liquidity_status_label'"
            )

        init_db()

        with session() as conn:
            labels = {
                row["key"]: row["value"]
                for row in conn.execute(
                    "SELECT key, value FROM app_labels WHERE key LIKE 'summary_%liquidity%_label'"
                )
            }
        self.assertEqual(labels["summary_next_month_liquidity_label"], "잔여 유동성")
        self.assertEqual(labels["summary_liquidity_status_label"], "내 통장 사정")

        with session() as conn:
            conn.execute(
                "UPDATE app_labels SET value = '내가 정한 잔액' WHERE key = 'summary_next_month_liquidity_label'"
            )
        init_db()
        with session() as conn:
            custom = conn.execute(
                "SELECT value FROM app_labels WHERE key = 'summary_next_month_liquidity_label'"
            ).fetchone()
        self.assertEqual(custom["value"], "내가 정한 잔액")


if __name__ == "__main__":
    unittest.main()

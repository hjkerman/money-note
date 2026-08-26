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
from fastapi import HTTPException


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
        self.assertEqual(values["scheduled_income"], "400000")
        self.assertEqual(values["cash_flow_balance"], "0")
        self.assertNotIn("base_next_month_liquidity", values)
        self.assertNotIn("liquidity_status", values)
        self.assertNotIn("share_pin_hash", values)
        self.assertNotIn("share_pin_is_default", values)

    def test_standard_setting_names_update_standard_storage_keys(self) -> None:
        income_response = patch_setting("scheduled_income", SettingPatch(value="550000"), {})
        balance_response = patch_setting("cash_flow_balance", SettingPatch(value="12000"), {})

        with session() as conn:
            stored_income = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'scheduled_income'"
            ).fetchone()
            stored_balance = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'cash_flow_balance'"
            ).fetchone()

        self.assertEqual(income_response, {"scheduled_income": "550000"})
        self.assertEqual(balance_response, {"cash_flow_balance": "12000"})
        self.assertEqual(stored_income["value"], "550000")
        self.assertEqual(stored_balance["value"], "12000")

    def test_legacy_setting_and_label_keys_are_migrated_idempotently(self) -> None:
        with session() as conn:
            conn.execute("DELETE FROM app_settings WHERE key IN ('scheduled_income', 'cash_flow_balance')")
            conn.executemany(
                "INSERT INTO app_settings(key, value) VALUES (?, ?)",
                (
                    ("base_next_month_liquidity", "550000"),
                    ("liquidity_status", "12000"),
                ),
            )
            conn.execute(
                "DELETE FROM app_labels WHERE key IN ('summary_cash_flow_balance_label', 'summary_remaining_liquidity_label')"
            )
            conn.execute(
                "INSERT INTO app_labels(key, value) VALUES ('summary_next_month_liquidity_label', '익월 유동성')"
            )
            conn.execute(
                "INSERT INTO app_labels(key, value) VALUES ('summary_liquidity_status_label', '내 통장 사정')"
            )

        init_db()
        init_db()

        with session() as conn:
            settings = {
                row["key"]: row["value"]
                for row in conn.execute(
                    "SELECT key, value FROM app_settings WHERE key IN (?, ?, ?, ?)",
                    ("scheduled_income", "cash_flow_balance", "base_next_month_liquidity", "liquidity_status"),
                )
            }
            labels = {
                row["key"]: row["value"]
                for row in conn.execute(
                    "SELECT key, value FROM app_labels WHERE key LIKE 'summary_%_label'"
                )
            }
        self.assertEqual(settings["scheduled_income"], "550000")
        self.assertEqual(settings["cash_flow_balance"], "12000")
        self.assertNotIn("base_next_month_liquidity", settings)
        self.assertNotIn("liquidity_status", settings)
        self.assertEqual(labels["summary_remaining_liquidity_label"], "잔여 유동성")
        self.assertEqual(labels["summary_cash_flow_balance_label"], "내 통장 사정")
        self.assertNotIn("summary_next_month_liquidity_label", labels)
        self.assertNotIn("summary_liquidity_status_label", labels)

    def test_liquidity_key_migration_rejects_conflicting_values(self) -> None:
        with session() as conn:
            conn.execute(
                "INSERT INTO app_settings(key, value) VALUES ('base_next_month_liquidity', '999999')"
            )

        with self.assertRaisesRegex(RuntimeError, "conflicting app_settings values"):
            init_db()

        with session() as conn:
            values = {
                row["key"]: row["value"]
                for row in conn.execute(
                    "SELECT key, value FROM app_settings WHERE key IN ('scheduled_income', 'base_next_month_liquidity')"
                )
            }
        self.assertEqual(values["scheduled_income"], "400000")
        self.assertEqual(values["base_next_month_liquidity"], "999999")

    def test_liquidity_key_migration_removes_equal_legacy_value(self) -> None:
        with session() as conn:
            conn.execute(
                "INSERT INTO app_settings(key, value) VALUES ('base_next_month_liquidity', '400000')"
            )

        init_db()

        with session() as conn:
            keys = {
                row["key"]
                for row in conn.execute(
                    "SELECT key FROM app_settings WHERE key IN ('scheduled_income', 'base_next_month_liquidity')"
                )
            }
        self.assertEqual(keys, {"scheduled_income"})

    def test_legacy_setting_paths_are_removed(self) -> None:
        for key in ("base_next_month_liquidity", "liquidity_status"):
            with self.assertRaises(HTTPException) as context:
                patch_setting(key, SettingPatch(value="1"), {})
            self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()

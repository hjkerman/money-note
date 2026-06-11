import copy
from datetime import date
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.services.snapshot import export_snapshot, restore_snapshot


class SnapshotTest(unittest.TestCase):
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

    def test_export_contains_recent_data_and_excludes_sensitive_auth_state(self) -> None:
        self._seed_data()

        filename, snapshot = export_snapshot(date(2026, 6, 11))

        self.assertTrue(filename.endswith(".money-note-snapshot.json"))
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertEqual(snapshot["range"]["months"], ["2026-04", "2026-05", "2026-06"])
        titles = {row["title"] for row in snapshot["data"]["ledger_entries"]}
        self.assertIn("최근 지출", titles)
        self.assertIn("카드 정기결제", titles)
        self.assertNotIn("오래된 지출", titles)
        setting_keys = {row["key"] for row in snapshot["data"]["app_settings"]}
        self.assertIn("base_next_month_liquidity", setting_keys)
        self.assertNotIn("share_pin_hash", setting_keys)
        self.assertNotIn("share_pin_is_default", setting_keys)
        self.assertNotIn("users", snapshot["data"])
        self.assertNotIn("auth_sessions", snapshot["data"])
        self.assertNotIn("audit_logs", snapshot["data"])

    def test_restore_replaces_ledger_data_and_preserves_auth_share_and_audit(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        snapshot["data"]["ledger_entries"][0]["title"] = "복원된 최근 지출"

        with session() as conn:
            conn.execute("DELETE FROM ledger_entries")
            conn.execute(
                """
                INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, sort_order)
                VALUES ('current', 'expense', '2026-06-10', '복원 전 임시 지출', 777, 99)
                """
            )
            conn.execute(
                """
                UPDATE app_settings
                SET value = '999999'
                WHERE key = 'base_next_month_liquidity'
                """
            )

        restored = restore_snapshot(snapshot)

        self.assertGreater(restored["ledger_entries"], 0)
        with session() as conn:
            titles = {row["title"] for row in conn.execute("SELECT title FROM ledger_entries").fetchall()}
            self.assertIn("복원된 최근 지출", titles)
            self.assertNotIn("복원 전 임시 지출", titles)
            user_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
            auth_count = conn.execute("SELECT COUNT(*) AS count FROM auth_sessions").fetchone()["count"]
            share_count = conn.execute("SELECT COUNT(*) AS count FROM share_sessions").fetchone()["count"]
            audit_count = conn.execute("SELECT COUNT(*) AS count FROM audit_logs").fetchone()["count"]
            pin_hash = conn.execute("SELECT value FROM app_settings WHERE key = 'share_pin_hash'").fetchone()["value"]
            base_income = conn.execute("SELECT value FROM app_settings WHERE key = 'base_next_month_liquidity'").fetchone()["value"]
        self.assertEqual(user_count, 1)
        self.assertEqual(auth_count, 1)
        self.assertEqual(share_count, 1)
        self.assertEqual(audit_count, 1)
        self.assertEqual(pin_hash, "secret-pin-hash")
        self.assertEqual(base_income, "400000")

    def test_restore_rolls_back_on_invalid_snapshot(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        broken["data"]["ledger_entries"][0]["unknown_column"] = "boom"

        with self.assertRaises(ValueError):
            restore_snapshot(broken)

        with session() as conn:
            titles = {row["title"] for row in conn.execute("SELECT title FROM ledger_entries").fetchall()}
            user_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        self.assertIn("최근 지출", titles)
        self.assertIn("오래된 지출", titles)
        self.assertEqual(user_count, 1)

    def _seed_data(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO users(id, username, password_hash, display_name)
                VALUES (1, 'tester', 'hash', '테스트')
                """
            )
            conn.execute(
                """
                INSERT INTO auth_sessions(user_id, session_token_hash, expires_at)
                VALUES (1, 'auth-token', '2099-01-01 00:00:00')
                """
            )
            conn.execute(
                """
                INSERT INTO share_sessions(session_token_hash, expires_at)
                VALUES ('share-token', '2099-01-01 00:00:00')
                """
            )
            conn.execute(
                """
                INSERT INTO audit_logs(actor_username, method, path, status_code)
                VALUES ('tester', 'POST', '/api/example', 200)
                """
            )
            conn.execute(
                """
                INSERT INTO app_settings(key, value)
                VALUES ('share_pin_hash', 'secret-pin-hash')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )
            conn.execute(
                """
                INSERT INTO app_settings(key, value)
                VALUES ('share_pin_is_default', '0')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    id, book_section, entry_kind, entry_date, title, amount_value, sort_order, payment_key
                )
                VALUES
                    (1, 'current', 'expense', '2026-06-05', '최근 지출', 1000, 1, 'recent-key'),
                    (2, 'archive', 'expense', '2026-02-05', '오래된 지출', 2000, 2, 'old-key'),
                    (3, 'current', 'planned', NULL, '카드 정기결제', 3000, 3, NULL)
                """
            )
            conn.execute(
                """
                INSERT INTO monthly_panels(id, month, panel_type, title, amount_value, sort_order)
                VALUES (1, '2026-06', 'claim', '최근 청구', 1000, 1)
                """
            )
            conn.execute(
                """
                INSERT INTO cash_flows(id, occurred_on, title, amount_value, sort_order)
                VALUES (1, '2026-06-06', '최근 현금', 5000, 1)
                """
            )
            conn.execute(
                """
                INSERT INTO installments(id, title, principal_amount, fee_rate, fee_amount, months, remaining_months, start_month, sort_order, is_active)
                VALUES (1, '활성 할부', 120000, 0, 0, 12, 10, '2026-01', 1, 1)
                """
            )
            conn.execute(
                """
                INSERT INTO card_payment_events(id, event_date, event_type, total_amount, note, cash_flow_id)
                VALUES (1, '2026-06-07', 'immediate', 500, '최근 결제', 1)
                """
            )
            conn.execute(
                """
                INSERT INTO card_payment_allocations(id, payment_event_id, entry_payment_key, amount_value)
                VALUES (1, 1, 'recent-key', 500)
                """
            )
            conn.execute(
                """
                INSERT INTO card_payment_deferrals(entry_payment_key, from_payment_month, target_payment_month)
                VALUES ('recent-key', '2026-06', '2026-07')
                """
            )


if __name__ == "__main__":
    unittest.main()

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

    def test_export_contains_all_ledger_data_and_excludes_sensitive_auth_state(self) -> None:
        self._seed_data()

        filename, snapshot = export_snapshot(date(2026, 6, 11))

        self.assertTrue(filename.endswith(".money-note-snapshot.json"))
        self.assertEqual(snapshot["schema_version"], 3)
        self.assertEqual(snapshot["range"], {"scope": "all"})
        self.assertEqual(snapshot["manifest"]["algorithm"], "sha256")
        self.assertEqual(snapshot["manifest"]["tables"]["ledger_entries"]["row_count"], 3)
        titles = {row["title"] for row in snapshot["data"]["ledger_entries"]}
        self.assertIn("최근 지출", titles)
        self.assertIn("카드 정기결제", titles)
        self.assertIn("오래된 지출", titles)
        panel_titles = {row["title"] for row in snapshot["data"]["monthly_panels"]}
        self.assertIn("최근 청구", panel_titles)
        self.assertIn("오래된 청구", panel_titles)
        self.assertIn("오래된 가족카드", panel_titles)
        self.assertIn("오래된 고정지출", panel_titles)
        cash_flow_titles = {row["title"] for row in snapshot["data"]["cash_flows"]}
        self.assertIn("최근 현금", cash_flow_titles)
        self.assertIn("오래된 현금", cash_flow_titles)
        event_notes = {row["note"] for row in snapshot["data"]["card_payment_events"]}
        self.assertIn("최근 결제", event_notes)
        self.assertIn("오래된 결제", event_notes)
        allocation_keys = {row["entry_payment_key"] for row in snapshot["data"]["card_payment_allocations"]}
        self.assertIn("recent-key", allocation_keys)
        self.assertIn("old-key", allocation_keys)
        deferral_keys = {row["entry_payment_key"] for row in snapshot["data"]["card_payment_deferrals"]}
        self.assertIn("recent-key", deferral_keys)
        self.assertIn("old-key", deferral_keys)
        setting_keys = {row["key"] for row in snapshot["data"]["app_settings"]}
        self.assertIn("base_next_month_liquidity", setting_keys)
        self.assertNotIn("share_pin_hash", setting_keys)
        self.assertNotIn("share_pin_is_default", setting_keys)
        self.assertNotIn("users", snapshot["data"])
        self.assertNotIn("auth_sessions", snapshot["data"])
        self.assertNotIn("audit_logs", snapshot["data"])

    def test_new_database_uses_integer_money_columns(self) -> None:
        expected = {
            "ledger_entries": {"amount_value": "INTEGER", "aux_amount_value": "INTEGER"},
            "monthly_panels": {"amount_value": "INTEGER", "discount_amount": "INTEGER"},
            "cash_flows": {"amount_value": "INTEGER"},
            "card_payment_events": {"total_amount": "INTEGER"},
            "card_payment_allocations": {"amount_value": "INTEGER"},
        }

        with session() as conn:
            for table, columns in expected.items():
                info = {row["name"]: row["type"].upper() for row in conn.execute(f"PRAGMA table_info({table})")}
                for column, column_type in columns.items():
                    self.assertEqual(info[column], column_type)

    def test_restore_preserves_frozen_panel_registration_date(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO monthly_panels(id, month, panel_type, title, spent_on, amount_value, sort_order)
                VALUES (99, '2026-06', 'frozen', '등록일자 있는 동결', '2026-06-18', 12345, 1)
                """
            )
        _, snapshot = export_snapshot(date(2026, 6, 18))
        frozen = next(row for row in snapshot["data"]["monthly_panels"] if row["id"] == 99)
        self.assertEqual(frozen["spent_on"], "2026-06-18")

        with session() as conn:
            conn.execute("DELETE FROM monthly_panels WHERE id = 99")
        restore_snapshot(snapshot)

        with session() as conn:
            restored = conn.execute("SELECT spent_on FROM monthly_panels WHERE id = 99").fetchone()
        self.assertEqual(restored["spent_on"], "2026-06-18")

    def test_restore_truncates_float_money_values_from_legacy_snapshot(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 1)["amount_value"] = 1000.9
        next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 1)["aux_amount_value"] = 12.8
        next(row for row in snapshot["data"]["monthly_panels"] if row["id"] == 1)["amount_value"] = 2000.7
        next(row for row in snapshot["data"]["monthly_panels"] if row["id"] == 1)["discount_amount"] = 24.9
        next(row for row in snapshot["data"]["cash_flows"] if row["id"] == 1)["amount_value"] = -5000.6
        next(row for row in snapshot["data"]["card_payment_events"] if row["id"] == 1)["total_amount"] = 500.5
        next(row for row in snapshot["data"]["card_payment_allocations"] if row["id"] == 1)["amount_value"] = 300.4
        for setting in snapshot["data"]["app_settings"]:
            if setting["key"] == "base_next_month_liquidity":
                setting["value"] = "400000.9"
                break
        snapshot["manifest"] = self._rebuilt_manifest(snapshot["data"])
        snapshot["snapshot_id"] = snapshot["manifest"]["data_sha256"]

        restore_snapshot(snapshot)

        with session() as conn:
            ledger = conn.execute(
                "SELECT amount_value, aux_amount_value FROM ledger_entries WHERE id = 1",
            ).fetchone()
            panel = conn.execute(
                "SELECT amount_value, discount_amount FROM monthly_panels WHERE id = 1",
            ).fetchone()
            cash_flow = conn.execute("SELECT amount_value FROM cash_flows WHERE id = 1").fetchone()
            event = conn.execute("SELECT total_amount FROM card_payment_events WHERE id = 1").fetchone()
            allocation = conn.execute("SELECT amount_value FROM card_payment_allocations WHERE id = 1").fetchone()
            setting = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'base_next_month_liquidity'",
            ).fetchone()
        self.assertEqual(ledger["amount_value"], 1000)
        self.assertEqual(ledger["aux_amount_value"], 12)
        self.assertEqual(panel["amount_value"], 2000)
        self.assertEqual(panel["discount_amount"], 24)
        self.assertEqual(cash_flow["amount_value"], -5000)
        self.assertEqual(event["total_amount"], 500)
        self.assertEqual(allocation["amount_value"], 300)
        self.assertEqual(setting["value"], "400000")

    def test_export_omits_legacy_discount_checked_columns(self) -> None:
        self._seed_data()
        with session() as conn:
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN discount_checked INTEGER DEFAULT 1")
            conn.execute("ALTER TABLE monthly_panels ADD COLUMN discount_checked INTEGER DEFAULT 1")

        _, snapshot = export_snapshot(date(2026, 6, 11))

        self.assertNotIn("discount_checked", snapshot["manifest"]["tables"]["ledger_entries"]["columns"])
        self.assertNotIn("discount_checked", snapshot["manifest"]["tables"]["monthly_panels"]["columns"])
        self.assertTrue(all("discount_checked" not in row for row in snapshot["data"]["ledger_entries"]))
        self.assertTrue(all("discount_checked" not in row for row in snapshot["data"]["monthly_panels"]))

    def test_restore_accepts_legacy_discount_checked_columns_after_manifest_validation(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        for row in snapshot["data"]["ledger_entries"]:
            row["discount_checked"] = 0
        for row in snapshot["data"]["monthly_panels"]:
            row["discount_checked"] = 0
        snapshot["manifest"] = self._rebuilt_manifest(snapshot["data"])
        snapshot["snapshot_id"] = snapshot["manifest"]["data_sha256"]

        restored = restore_snapshot(snapshot)

        self.assertEqual(restored["ledger_entries"], 3)
        self.assertEqual(restored["monthly_panels"], 4)

    def test_restore_ignores_unknown_snapshot_columns_after_manifest_validation(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        for row in snapshot["data"]["ledger_entries"]:
            row["future_client_note"] = "나중에 생긴 컬럼"
        for row in snapshot["data"]["monthly_panels"]:
            row["future_panel_note"] = "나중에 생긴 패널 컬럼"
        snapshot["manifest"] = self._rebuilt_manifest(snapshot["data"])
        snapshot["snapshot_id"] = snapshot["manifest"]["data_sha256"]

        restored = restore_snapshot(snapshot)

        self.assertEqual(restored["ledger_entries"], 3)
        self.assertEqual(restored["monthly_panels"], 4)
        with session() as conn:
            ledger_columns = {row["name"] for row in conn.execute("PRAGMA table_info(ledger_entries)").fetchall()}
            panel_columns = {row["name"] for row in conn.execute("PRAGMA table_info(monthly_panels)").fetchall()}
        self.assertNotIn("future_client_note", ledger_columns)
        self.assertNotIn("future_panel_note", panel_columns)

    def test_restore_accepts_empty_table_manifest_from_older_column_set(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        snapshot["data"]["app_labels"] = []
        snapshot["manifest"] = self._rebuilt_manifest(snapshot["data"])
        snapshot["manifest"]["tables"]["app_labels"]["columns"] = ["key", "value"]
        snapshot["snapshot_id"] = snapshot["manifest"]["data_sha256"]

        restored = restore_snapshot(snapshot)

        self.assertEqual(restored["app_labels"], 0)

    def test_restore_replaces_ledger_data_and_preserves_auth_share_and_audit(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        snapshot["data"]["ledger_entries"][0]["title"] = "복원된 최근 지출"
        snapshot["manifest"] = self._rebuilt_manifest(snapshot["data"])

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
        backup_dir = self.db_path.parent / "snapshot-backups"
        backups = list(backup_dir.glob("pre_restore-*.money-note-snapshot.json"))
        self.assertEqual(len(backups), 1)
        pre_restore = backups[0].read_text(encoding="utf-8")
        self.assertIn("복원 전 임시 지출", pre_restore)
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

    def test_restore_rejects_missing_required_table_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        del broken["data"]["ledger_entries"]

        with self.assertRaises(ValueError):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def test_restore_rejects_wrong_schema_version_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        broken["schema_version"] = 999

        with self.assertRaises(ValueError):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def test_restore_rejects_empty_snapshot_without_touching_db(self) -> None:
        self._seed_data()

        with self.assertRaises(ValueError):
            restore_snapshot({})

        self._assert_seed_data_preserved()

    def test_restore_rejects_missing_column_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        del broken["data"]["ledger_entries"][0]["title"]
        broken["manifest"] = snapshot["manifest"]

        with self.assertRaises(ValueError):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def test_restore_rejects_manifest_mismatch_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        broken["data"]["ledger_entries"][0]["title"] = "해시 안 맞는 지출"

        with self.assertRaises(ValueError):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def test_restore_rejects_broken_foreign_key_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        broken["data"]["card_payment_allocations"][0]["payment_event_id"] = 99999
        broken["manifest"] = self._rebuilt_manifest(broken["data"])

        with self.assertRaises(ValueError):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def _rebuilt_manifest(self, data: dict) -> dict:
        import hashlib
        import json

        tables = {}
        for table, rows in data.items():
            columns = sorted(rows[0].keys()) if rows else []
            tables[table] = {
                "columns": columns,
                "row_count": len(rows),
                "sha256": hashlib.sha256(
                    json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
                ).hexdigest(),
            }
        return {
            "algorithm": "sha256",
            "tables": tables,
            "data_sha256": hashlib.sha256(
                json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            ).hexdigest(),
        }

    def _assert_seed_data_preserved(self) -> None:
        with session() as conn:
            titles = {row["title"] for row in conn.execute("SELECT title FROM ledger_entries").fetchall()}
            panels = {row["title"] for row in conn.execute("SELECT title FROM monthly_panels").fetchall()}
            user_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
            auth_count = conn.execute("SELECT COUNT(*) AS count FROM auth_sessions").fetchone()["count"]
        self.assertIn("최근 지출", titles)
        self.assertIn("오래된 지출", titles)
        self.assertIn("오래된 청구", panels)
        self.assertIn("오래된 가족카드", panels)
        self.assertEqual(user_count, 1)
        self.assertEqual(auth_count, 1)

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
                VALUES
                    (1, '2026-06', 'claim', '최근 청구', 1000, 1),
                    (2, '2026-02', 'claim', '오래된 청구', 2000, 2),
                    (3, '2026-02', 'family_card', '오래된 가족카드', 3000, 3),
                    (4, '2026-02', 'fixed', '오래된 고정지출', 4000, 4)
                """
            )
            conn.execute(
                """
                INSERT INTO cash_flows(id, occurred_on, title, amount_value, sort_order)
                VALUES
                    (1, '2026-06-06', '최근 현금', 5000, 1),
                    (2, '2026-02-06', '오래된 현금', 6000, 2)
                """
            )
            conn.execute(
                """
                INSERT INTO card_payment_events(id, event_date, event_type, total_amount, note, cash_flow_id)
                VALUES
                    (1, '2026-06-07', 'immediate', 500, '최근 결제', 1),
                    (2, '2026-02-07', 'immediate', 700, '오래된 결제', 2)
                """
            )
            conn.execute(
                """
                INSERT INTO card_payment_allocations(id, payment_event_id, entry_payment_key, amount_value)
                VALUES
                    (1, 1, 'recent-key', 500),
                    (2, 2, 'old-key', 700)
                """
            )
            conn.execute(
                """
                INSERT INTO card_payment_deferrals(entry_payment_key, from_payment_month, target_payment_month)
                VALUES
                    ('recent-key', '2026-06', '2026-07'),
                    ('old-key', '2026-02', '2026-03')
                """
            )


if __name__ == "__main__":
    unittest.main()

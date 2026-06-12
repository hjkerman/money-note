import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.auth import create_user
from app.config import get_settings
from app.db import init_db, session
from app.routers.admin import (
    get_pre_restore_backup,
    get_pre_restore_backups,
    post_pre_restore_backup_restore,
    post_snapshot_restore,
)
from app.schemas import PreRestoreRestoreIn, SnapshotRestoreIn
from app.services.reset import reset_ledger_data
from app.services.snapshot import export_snapshot, restore_snapshot
import app.services.snapshot as snapshot_service


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
        self.assertIn("/api/admin/snapshot/pre-restore", paths)
        self.assertIn("/api/admin/snapshot/pre-restore/{filename}", paths)
        self.assertIn("/api/admin/snapshot/pre-restore/{filename}/restore", paths)

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

    def test_pre_restore_list_download_and_restore_api(self) -> None:
        user = self._create_user()
        filename = self._create_pre_restore_backup()

        backups = get_pre_restore_backups(user)["backups"]
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0]["filename"], filename)
        self.assertGreater(backups[0]["size_bytes"], 0)
        self.assertTrue(backups[0]["snapshot_id"])
        self.assertTrue(backups[0]["exported_at"])

        download_response = get_pre_restore_backup(filename, user)
        self.assertEqual(download_response.media_type, "application/json")
        self.assertIn(filename, download_response.headers["content-disposition"])

        restore_response = post_pre_restore_backup_restore(
            filename,
            PreRestoreRestoreIn(password="secret"),
            user,
        )
        self.assertIn("restored", restore_response)
        with session() as conn:
            titles = {row["title"] for row in conn.execute("SELECT title FROM ledger_entries").fetchall()}
        self.assertIn("복원 직전 상태", titles)

    def test_pre_restore_api_rejects_bad_filename(self) -> None:
        user = self._create_user()

        with self.assertRaises(Exception):
            get_pre_restore_backup("not-a-backup.json", user)

    def test_pre_restore_restore_failure_preserves_current_db(self) -> None:
        user = self._create_user()
        self._seed_entry("현재 운영 상태")
        _, snapshot = export_snapshot()
        snapshot["data"]["card_payment_allocations"].append(
            {
                "id": 999,
                "payment_event_id": 999,
                "entry_payment_key": "broken",
                "amount_value": 100,
                "created_at": "2026-06-11 00:00:00",
            },
        )
        snapshot["manifest"] = snapshot_service._build_manifest(snapshot["data"])
        snapshot["snapshot_id"] = snapshot["manifest"]["data_sha256"]
        backup_dir = self.db_path.parent / "snapshot-backups"
        backup_dir.mkdir()
        filename = "pre_restore-20260611T010101Z.money-note-snapshot.json"
        (backup_dir / filename).write_text(snapshot_service.json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")

        with self.assertRaises(Exception):
            post_pre_restore_backup_restore(filename, PreRestoreRestoreIn(password="secret"), user)
        with session() as conn:
            titles = {row["title"] for row in conn.execute("SELECT title FROM ledger_entries").fetchall()}
        self.assertIn("현재 운영 상태", titles)

    def test_snapshot_restore_accepts_snapshot_text_payload(self) -> None:
        user = self._create_user()
        self._seed_entry("원문 snapshot 복원")
        _, snapshot = export_snapshot()
        snapshot_text = snapshot_service.json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        reset_ledger_data()

        response = post_snapshot_restore(SnapshotRestoreIn(password="secret", snapshot_text=snapshot_text), user)

        self.assertEqual(response["restored"]["ledger_entries"], 1)
        with session() as conn:
            title = conn.execute("SELECT title FROM ledger_entries").fetchone()["title"]
        self.assertEqual(title, "원문 snapshot 복원")

    def _create_user(self) -> dict:
        return create_user("tester", "secret", "테스트")

    def _create_pre_restore_backup(self) -> str:
        self._seed_entry("원래 상태")
        _, snapshot = export_snapshot()
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET title = '복원 직전 상태'")
        restore_snapshot(snapshot)
        backups = list((self.db_path.parent / "snapshot-backups").glob("pre_restore-*.money-note-snapshot.json"))
        self.assertEqual(len(backups), 1)
        return backups[0].name

    def _seed_entry(self, title: str) -> None:
        with session() as conn:
            conn.execute("DELETE FROM ledger_entries")
            conn.execute(
                """
                INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, sort_order)
                VALUES ('current', 'expense', '2026-06-05', ?, 1000, 1)
                """,
                (title,),
            )


if __name__ == "__main__":
    unittest.main()

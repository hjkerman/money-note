import threading
import unittest
from unittest.mock import patch

from tests.db_fixture import IsolatedDatabaseTestCase
from app.db import session
from app.services.reset import reset_ledger_data
from app.services.snapshot import create_pre_restore_backup


class ResetTest(IsolatedDatabaseTestCase):
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

    def test_reset_blocks_writes_between_pre_restore_and_delete(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value, sort_order
                )
                VALUES ('current', 'expense', '2026-06-05', '초기화 대상', 1000, 1)
                """
            )
        backup_started = threading.Event()
        writer_attempted = threading.Event()
        writer_finished = threading.Event()

        def guarded_backup(conn):
            backup_started.set()
            self.assertTrue(writer_attempted.wait(timeout=2))
            return create_pre_restore_backup(conn)

        def writer() -> None:
            self.assertTrue(backup_started.wait(timeout=2))
            writer_attempted.set()
            with session(transaction_mode="IMMEDIATE") as conn:
                conn.execute(
                    """
                    INSERT INTO ledger_entries(
                        book_section, entry_kind, entry_date, title,
                        amount_value, sort_order, payment_key
                    )
                    VALUES ('current', 'expense', '2026-06-06',
                            '초기화 뒤 동시 기록', 2000, 2, 'post-reset-write')
                    """
                )
            writer_finished.set()

        thread = threading.Thread(target=writer)
        thread.start()
        with patch("app.services.reset.create_pre_restore_backup", side_effect=guarded_backup):
            reset_ledger_data()
        thread.join(timeout=3)

        self.assertTrue(writer_finished.is_set())
        backups = list(
            (self.db_path.parent / "snapshot-backups").glob(
                "pre_restore-*.money-note-snapshot.json"
            )
        )
        self.assertEqual(len(backups), 1)
        backup_text = backups[0].read_text(encoding="utf-8")
        self.assertIn("초기화 대상", backup_text)
        self.assertNotIn("초기화 뒤 동시 기록", backup_text)
        with session() as conn:
            row = conn.execute(
                "SELECT title FROM ledger_entries WHERE payment_key = 'post-reset-write'"
            ).fetchone()
        self.assertEqual(row["title"], "초기화 뒤 동시 기록")


if __name__ == "__main__":
    unittest.main()

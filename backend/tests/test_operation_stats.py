import unittest

from tests.db_fixture import IsolatedDatabaseTestCase
from app.db import session
from app.services.operation_stats import operation_data_stats
from app.services.snapshot import create_pre_restore_backup


class OperationStatsTest(IsolatedDatabaseTestCase):
    def test_operation_stats_reports_table_counts_and_backup_sizes(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, sort_order)
                VALUES ('current', 'expense', '2026-06-05', '통계 대상 지출', 1000, 1)
                """
            )
        create_pre_restore_backup()

        stats = operation_data_stats()

        self.assertGreaterEqual(stats["db_file_size_bytes"], stats["empty_db_size_bytes"])
        self.assertGreaterEqual(stats["estimated_data_size_bytes"], 0)
        self.assertGreater(stats["pre_restore_total_size_bytes"], 0)
        self.assertEqual(stats["pre_restore_count"], 1)
        self.assertEqual(stats["table_row_counts"]["ledger_entries"], 1)
        self.assertIn("app_settings", stats["table_row_counts"])


if __name__ == "__main__":
    unittest.main()

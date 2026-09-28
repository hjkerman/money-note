"""Synthetic database shapes taken from committed historical SCHEMA definitions.

The fixture names map to Git commits in docs/database.md. Only the rows seeded
here are test data; no installed or production database is used.
"""

from pathlib import Path
import sqlite3

from app.db import init_db, session
from app.services.summary import current_summary_values
from tests.db_fixture import IsolatedDatabaseTestCase


FIXTURES = (
    "pre_batch",
    "card_batches",
    "fixed_expenses",
    "offline_phase2",
)
FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures"


def schema_shape(conn: sqlite3.Connection) -> dict[str, tuple[str, ...]]:
    tables = [
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    return {
        table: tuple(row[1] for row in conn.execute(f"PRAGMA table_info({table})"))
        for table in tables
    }


class MigrationCharacterizationTest(IsolatedDatabaseTestCase):
    def _seed_historical(self, era: str) -> None:
        self.db_path.unlink()
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript((FIXTURE_DIRECTORY / f"schema_{era}.sql").read_text())
            conn.execute(
                "INSERT INTO ledger_entries(id, book_section, entry_kind, entry_date, title, "
                "amount_value, sort_order, payment_key) "
                "VALUES (11, 'current', 'expense', '2026-06-11', 'Synthetic card', 10000, 1, 'card-11')"
            )
            conn.execute(
                "INSERT INTO ledger_entries(id, book_section, entry_kind, entry_date, title, "
                "amount_value, sort_order) "
                "VALUES (12, 'current', 'planned', '2026-06-12', '매월 12일 카드', 3000, 2)"
            )
            conn.execute(
                "INSERT INTO cash_flows(id, occurred_on, title, amount_value, sort_order) "
                "VALUES (21, '2026-06-11', 'Synthetic cash', -500, 1)"
            )
            conn.execute(
                "INSERT INTO monthly_panels(id, month, panel_type, title, amount_value, sort_order) "
                "VALUES (31, '2026-06', 'family_card', 'Synthetic family', 2000, 1)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO app_settings(key, value) "
                "VALUES ('card_limit', '5000000')"
            )

    def test_fresh_and_repeated_current_startup_preserve_schema_and_money(self) -> None:
        with session() as conn:
            first = schema_shape(conn)
            conn.execute(
                "INSERT INTO cash_flows(id, occurred_on, title, amount_value, sort_order) "
                "VALUES (21, '2026-06-11', 'Synthetic cash', -500, 1)"
            )
        init_db()
        init_db()
        with session() as conn:
            self.assertEqual(schema_shape(conn), first)
            self.assertEqual(conn.execute("SELECT amount_value FROM cash_flows WHERE id = 21").fetchone()[0], -500)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows").fetchone()[0], 1)

    def test_historical_eras_preserve_financial_rows_and_repeat_safely(self) -> None:
        for era in FIXTURES:
            with self.subTest(era=era):
                self._seed_historical(era)
                init_db()
                with session() as conn:
                    migrated_shape = schema_shape(conn)
                    first_rows = self._financial_rows(conn)
                    self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                    self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
                first_summary = current_summary_values()
                init_db()
                init_db()
                with session() as conn:
                    self.assertEqual(schema_shape(conn), migrated_shape)
                    self.assertEqual(self._financial_rows(conn), first_rows)
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0], 2)
                    self.assertEqual(conn.execute("SELECT due_day FROM ledger_entries WHERE id = 12").fetchone()[0], 12)
                    self.assertEqual(conn.execute("SELECT value FROM app_settings WHERE key = 'card_limit'").fetchone()[0], "5000000")
                self.assertEqual(current_summary_values(), first_summary)
                self.assertEqual(first_rows["ledger"], [(11, 10000), (12, 3000)])
                self.assertEqual(first_rows["cash"], [(21, -500)])
                self.assertEqual(first_rows["family"], [(31, 2000)])

    @staticmethod
    def _financial_rows(conn: sqlite3.Connection) -> dict[str, list[tuple[int, int]]]:
        return {
            "ledger": [tuple(row) for row in conn.execute("SELECT id, amount_value FROM ledger_entries ORDER BY id")],
            "cash": [tuple(row) for row in conn.execute("SELECT id, amount_value FROM cash_flows ORDER BY id")],
            "family": [tuple(row) for row in conn.execute("SELECT id, amount_value FROM monthly_panels ORDER BY id")],
        }

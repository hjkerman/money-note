"""Failure, restart and version-marker contracts for synthetic SQLite DBs."""

import sqlite3
from datetime import date
from unittest.mock import patch

from app.db import SCHEMA, connect, init_db, session
from app import db_migrations
from app.services.month import close_current_month
from app.services.summary import current_summary_values
from tests.db_fixture import IsolatedDatabaseTestCase
from tests.test_migration_characterization import MigrationCharacterizationTest as _FixtureBuilder, schema_shape


class VersionedMigrationTest(IsolatedDatabaseTestCase):
    _seed_historical = _FixtureBuilder._seed_historical

    def test_fresh_database_has_current_version_and_expected_schema(self) -> None:
        with session() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], db_migrations.CURRENT_SCHEMA_VERSION)
            self.assertEqual(
                {table: set(columns) for table, columns in schema_shape(conn).items()},
                db_migrations._expected_tables_and_columns(SCHEMA),
            )

    def test_current_version_skips_historical_data_and_schema_migrations(self) -> None:
        with session() as conn:
            conn.execute("INSERT INTO cash_flows(id, occurred_on, title, amount_value, sort_order) "
                         "VALUES (21, '2026-06-11', 'Synthetic cash', -500, 1)")
        conn = connect()
        statements: list[str] = []
        conn.set_trace_callback(statements.append)
        try:
            with patch("app.db.connect", return_value=conn):
                init_db()
            self.assertEqual(conn.execute("SELECT amount_value FROM cash_flows WHERE id = 21").fetchone()[0], -500)
        finally:
            conn.close()
        normalized = [statement.lstrip().upper() for statement in statements]
        self.assertFalse(any(statement.startswith(("UPDATE", "INSERT", "DELETE", "ALTER", "DROP", "CREATE"))
                             for statement in normalized))

    def test_unversioned_unknown_schema_fails_without_creating_tables(self) -> None:
        self.db_path.unlink()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE unexpected(id INTEGER PRIMARY KEY, amount INTEGER)")
            conn.execute("INSERT INTO unexpected VALUES (1, 12345)")
        with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
            init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT amount FROM unexpected").fetchone()[0], 12345)
            self.assertEqual(conn.execute("SELECT name FROM sqlite_master WHERE name = 'ledger_entries'").fetchone(), None)

    def test_unversioned_core_with_unknown_column_fails_closed(self) -> None:
        self._seed_historical("offline_phase2")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN foreign_unrecognized_value TEXT")
        with self.assertRaisesRegex(RuntimeError, "ledger_entries columns"):
            init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT amount_value FROM ledger_entries WHERE id = 11").fetchone()[0], 10000)

    def _assert_missing_financial_column_fails_closed(self, table: str, column: str) -> None:
        # Current SCHEMA without a marker represents the T4.5 unversioned shape.
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA user_version = 0")
            conn.execute(
                "INSERT INTO ledger_entries(id, book_section, entry_kind, title, amount_value, sort_order) "
                "VALUES (11, 'current', 'expense', 'Synthetic card', 10000, 1)"
            )
            conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
        with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
            init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT amount_value FROM ledger_entries WHERE id = 11").fetchone()[0], 10000)
            self.assertNotIn(column, {row[1] for row in conn.execute(f"PRAGMA table_info({table})")})

    def test_unversioned_missing_ledger_aux_amount_fails_closed(self) -> None:
        self._assert_missing_financial_column_fails_closed("ledger_entries", "aux_amount_value")

    def test_unversioned_missing_cash_title_fails_closed(self) -> None:
        self._assert_missing_financial_column_fails_closed("cash_flows", "title")

    def test_current_unversioned_shape_cannot_lose_confirmed_month(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA user_version = 0")
            conn.execute("ALTER TABLE monthly_panels DROP COLUMN confirmed_month")
        with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
            init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertNotIn(
                "confirmed_month",
                {row[1] for row in conn.execute("PRAGMA table_info(monthly_panels)")},
            )

    def test_current_unversioned_missing_required_tables_fails_before_recreation(self) -> None:
        for table in sorted(db_migrations._expected_tables_and_columns(SCHEMA)):
            with self.subTest(table=table):
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("PRAGMA user_version = 0")
                    conn.execute(f"DROP TABLE {table}")
                with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
                    init_db()
                with sqlite3.connect(self.db_path) as conn:
                    self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
                    self.assertIsNone(conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,),
                    ).fetchone())
                self.db_path.unlink()
                init_db()

    def test_missing_batch_members_cannot_erase_existing_obligation(self) -> None:
        with session() as conn:
            conn.execute("UPDATE app_settings SET value = '0' WHERE key = 'scheduled_income'")
            conn.execute("UPDATE app_settings SET value = '100000' WHERE key = 'cash_flow_balance'")
            conn.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES ('last_closed_month', '2026-05')")
            conn.execute(
                "INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, "
                "sort_order, payment_key) VALUES ('current', 'expense', '2026-06-11', 'Synthetic card', "
                "10000, 1, 'synthetic-card')"
            )
        close_current_month(date(2026, 7, 1), target_month="2026-06")
        with patch("app.services.summary.app_today", return_value=date(2026, 7, 1)):
            self.assertEqual(current_summary_values()["remaining_liquidity"], 90_120)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA user_version = 0")
            conn.execute("DROP TABLE card_payment_batch_items")
        with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
            init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_payment_batches").fetchone()[0], 1)
            self.assertIsNone(conn.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'card_payment_batch_items'"
            ).fetchone())

    def test_current_unversioned_requires_identity_and_unique_index_semantics(self) -> None:
        cases = ("cash_pk", "cash_pk_type", "event_pk", "idempotency_unique",
                 "idempotency_missing", "idempotency_wrong_predicate", "fixed_foreign_key")
        for case in cases:
            with self.subTest(case=case):
                self.db_path.unlink()
                if case in {"cash_pk", "cash_pk_type", "event_pk", "fixed_foreign_key"}:
                    old, new = {
                        "cash_pk": (
                            "CREATE TABLE IF NOT EXISTS cash_flows (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,",
                            "CREATE TABLE IF NOT EXISTS cash_flows (\n    id INTEGER,",
                        ),
                        "cash_pk_type": (
                            "CREATE TABLE IF NOT EXISTS cash_flows (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,",
                            "CREATE TABLE IF NOT EXISTS cash_flows (\n    id TEXT PRIMARY KEY,",
                        ),
                        "event_pk": (
                            "CREATE TABLE IF NOT EXISTS card_payment_events (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,",
                            "CREATE TABLE IF NOT EXISTS card_payment_events (\n    id INTEGER,",
                        ),
                        "fixed_foreign_key": (
                            "confirmed_cash_flow_id INTEGER REFERENCES cash_flows(id) ON DELETE SET NULL,",
                            "confirmed_cash_flow_id INTEGER,",
                        ),
                    }[case]
                    broken = SCHEMA.replace(old, new)
                    self.assertNotEqual(broken, SCHEMA)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.executescript(broken)
                else:
                    init_db()
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("DROP INDEX idx_card_payment_events_idempotency")
                        if case != "idempotency_missing":
                            unique = "UNIQUE " if case == "idempotency_wrong_predicate" else ""
                            predicate = (
                                "idempotency_key = 'only-one'" if case == "idempotency_wrong_predicate"
                                else "idempotency_key IS NOT NULL"
                            )
                            conn.execute(
                                f"CREATE {unique}INDEX idx_card_payment_events_idempotency "
                                f"ON card_payment_events(idempotency_key) WHERE {predicate}"
                            )
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("PRAGMA user_version = 0")
                with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
                    init_db()
                with sqlite3.connect(self.db_path) as conn:
                    self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)

    def test_interrupted_data_migration_rolls_back_and_restart_resumes(self) -> None:
        self._seed_historical("pre_batch")
        original = db_migrations.MIGRATIONS

        def fail_after_financial_write(conn: sqlite3.Connection, schema: str) -> None:
            conn.execute("UPDATE ledger_entries SET amount_value = 1 WHERE id = 11")
            raise RuntimeError("injected migration failure")

        with patch.object(db_migrations, "MIGRATIONS", (original[0], fail_after_financial_write, original[2])):
            with self.assertRaisesRegex(RuntimeError, "injected migration failure"):
                init_db()
        with session() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT amount_value FROM ledger_entries WHERE id = 11").fetchone()[0], 10000)
        init_db()
        init_db()
        with session() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], db_migrations.CURRENT_SCHEMA_VERSION)
            self.assertEqual(conn.execute("SELECT amount_value FROM ledger_entries WHERE id = 11").fetchone()[0], 10000)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger_entries WHERE id = 11").fetchone()[0], 1)

    def test_final_index_failure_keeps_previous_version_and_recovers(self) -> None:
        self._seed_historical("card_batches")
        original = db_migrations.MIGRATIONS

        def fail_after_index(conn: sqlite3.Connection, schema: str) -> None:
            original[2](conn, schema)
            raise RuntimeError("injected index failure")

        with patch.object(db_migrations, "MIGRATIONS", (original[0], original[1], fail_after_index)):
            with self.assertRaisesRegex(RuntimeError, "injected index failure"):
                init_db()
        with session() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertIsNone(conn.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'revision_cash_flows_update'"
            ).fetchone())
        init_db()
        with session() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], db_migrations.CURRENT_SCHEMA_VERSION)
            self.assertIsNotNone(conn.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'revision_cash_flows_update'"
            ).fetchone())

    def test_claimed_current_version_with_broken_schema_fails_closed(self) -> None:
        with session() as conn:
            conn.execute("DROP INDEX idx_card_payment_events_idempotency")
        with self.assertRaisesRegex(RuntimeError, "missing critical indexes"):
            init_db()

    def test_claimed_current_version_with_wrong_primary_key_fails_closed(self) -> None:
        self.db_path.unlink()
        broken = SCHEMA.replace(
            "CREATE TABLE IF NOT EXISTS cash_flows (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,",
            "CREATE TABLE IF NOT EXISTS cash_flows (\n    id TEXT PRIMARY KEY,",
        )
        self.assertNotEqual(broken, SCHEMA)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(broken)
            conn.execute("PRAGMA user_version = 3")
        with self.assertRaisesRegex(RuntimeError, "cash_flows primary key"):
            init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertEqual(
                next(row[2] for row in conn.execute("PRAGMA table_info(cash_flows)") if row[1] == "id"),
                "TEXT",
            )

    def test_claimed_current_version_with_missing_financial_columns_fails_closed(self) -> None:
        for table, column in (("ledger_entries", "aux_amount_value"), ("cash_flows", "title")):
            with self.subTest(table=table, column=column):
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
                with self.assertRaisesRegex(RuntimeError, f"missing {table} columns"):
                    init_db()
                with sqlite3.connect(self.db_path) as conn:
                    self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 3)
                    self.assertNotIn(column, {row[1] for row in conn.execute(f"PRAGMA table_info({table})")})
                self.db_path.unlink()
                init_db()

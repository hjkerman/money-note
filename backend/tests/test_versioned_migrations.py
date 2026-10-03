"""Failure, restart and version-marker contracts for synthetic SQLite DBs."""

import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app.db import SCHEMA, connect, init_db, session
from app import db_migrations
from app.services.month import close_current_month
from app.services.summary import current_summary_values
from tests.db_fixture import IsolatedDatabaseTestCase
from tests.test_migration_characterization import MigrationCharacterizationTest as _FixtureBuilder, schema_shape


class VersionedMigrationTest(IsolatedDatabaseTestCase):
    _seed_historical = _FixtureBuilder._seed_historical

    def test_historical_batch_relationship_column_cannot_be_guessed(self) -> None:
        self.db_path.unlink()
        fixture = Path(__file__).parent / "fixtures" / "schema_offline_phase2.sql"
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(fixture.read_text(encoding="utf-8"))
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES "
                         "('scheduled_income','0'),('cash_flow_balance','100000'),"
                         "('last_closed_month','2026-06')")
            conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,entry_date,"
                         "title,usage_place,amount_value,payment_key,sort_order) VALUES "
                         "(11,'archive','expense','2026-06-11','Purchase','Store',10000,'payment-11',1)")
            conn.execute("INSERT INTO card_payment_batches(id,usage_month,source,status) "
                         "VALUES (1,'2026-06','month_close','active')")
            conn.execute("INSERT INTO card_payment_batch_items(id,batch_id,entry_id,entry_payment_key) "
                         "VALUES (1,1,11,'payment-11')")
            conn.execute("INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order) "
                         "VALUES (21,'2026-07-01','Card payment',-500,1)")
            conn.execute("INSERT INTO card_payment_events(id,batch_id,event_date,event_type,"
                         "total_amount,cash_flow_id) VALUES (31,1,'2026-07-01','immediate',500,21)")
            conn.execute("INSERT INTO card_payment_allocations(id,payment_event_id,"
                         "entry_payment_key,amount_value) VALUES (41,31,'payment-11',500)")
        with patch("app.services.summary.app_today", return_value=date(2026, 7, 1)):
            self.assertEqual(current_summary_values()["remaining_liquidity"], 90_120)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("ALTER TABLE card_payment_events DROP COLUMN batch_id")
            before = list(conn.iterdump())
        with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
            init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(list(conn.iterdump()), before)

    def test_historical_explicit_discount_exclusion_cannot_be_guessed(self) -> None:
        self.db_path.unlink()
        fixture = Path(__file__).parent / "fixtures" / "schema_offline_phase2.sql"
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(fixture.read_text(encoding="utf-8"))
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES "
                         "('scheduled_income','0'),('cash_flow_balance','100000')")
            conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,entry_date,title,"
                         "usage_place,amount_value,aux_amount_value,discount_override,sort_order) "
                         "VALUES (11,'current','expense','2026-06-11','Purchase','Store',10000,0,1,1)")
        with patch("app.services.summary.app_today", return_value=date(2026, 6, 11)):
            self.assertEqual(current_summary_values()["remaining_liquidity"], 90_000)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("ALTER TABLE ledger_entries DROP COLUMN discount_override")
            before = list(conn.iterdump())
        with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
            init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(list(conn.iterdump()), before)

    def test_confirmed_fixed_relationship_cannot_masquerade_as_pre_fixed_era(self) -> None:
        self.db_path.unlink()
        fixture = Path(__file__).parent / "fixtures" / "schema_fixed_expenses.sql"
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(fixture.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order) "
                         "VALUES (21,'2026-06-11','Rent',-5000,1)")
            conn.execute("INSERT INTO monthly_panels(id,month,panel_type,title,spent_on,"
                         "amount_value,sort_order,confirmed_at,confirmed_cash_flow_id) "
                         "VALUES (31,'2026-06','fixed','Rent','2026-06-11',5000,1,"
                         "'2026-06-11T09:00:00+00:00',21)")
            conn.execute("ALTER TABLE monthly_panels DROP COLUMN confirmed_cash_flow_id")
            before = list(conn.iterdump())
        with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
            init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(list(conn.iterdump()), before)

    def test_supported_era_authoritative_columns_cannot_be_silently_recreated(self) -> None:
        # Independent list of fields carrying financial or relationship input.
        # Columns absent from an authentic historical fixture are future fields
        # and are exercised by the successful migration characterization test.
        authoritative = {
            "ledger_entries": (
                "book_section", "entry_kind", "entry_date", "date_label",
                "group_label", "title", "usage_place", "usage_item",
                "amount_value", "amount_expr", "aux_amount_value", "aux_amount_expr",
                "extra_value", "sort_order", "due_day", "confirmed_at",
                "confirmed_month", "source_planned_entry_id", "spending_category",
                "payment_key", "discount_override", "created_at", "updated_at",
            ),
            "monthly_panels": (
                "month", "panel_type", "title", "spent_on", "amount_value",
                "discount_amount", "discount_override", "amount_expr", "sort_order",
                "due_day", "confirmed_at", "confirmed_month", "confirmed_cash_flow_id",
                "created_at", "updated_at",
            ),
            "cash_flows": (
                "occurred_on", "title", "amount_value", "sort_order",
                "is_primary_income", "created_at", "updated_at",
            ),
            "card_payment_events": (
                "batch_id", "event_date", "event_type", "total_amount",
                "note", "cash_flow_id", "idempotency_key", "request_fingerprint",
                "created_at",
            ),
        }
        for era in (
            "pre_batch", "card_batches", "fixed_expenses", "pre_notification",
            "notification", "offline_phase2",
        ):
            for table, names in authoritative.items():
                for column in names:
                    with self.subTest(era=era, table=table, column=column):
                        self._seed_historical(era)
                        with sqlite3.connect(self.db_path) as conn:
                            present = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
                            if column not in present:
                                continue
                            # The confirmed fixed link is this era's sole schema
                            # marker. A confirmed row supplies separate evidence.
                            if era == "fixed_expenses" and column == "confirmed_cash_flow_id":
                                continue
                            try:
                                conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
                            except sqlite3.OperationalError:
                                # SQLite forbids dropping columns used by a
                                # historical index/constraint; those identities
                                # have dedicated structure corruption tests.
                                continue
                            before = list(conn.iterdump())
                        with self.assertRaisesRegex(RuntimeError, "unknown unversioned database schema"):
                            init_db()
                        with sqlite3.connect(self.db_path) as conn:
                            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
                            self.assertEqual(list(conn.iterdump()), before)

    def test_integer_primary_key_desc_is_not_an_auto_rowid_identity(self) -> None:
        for version in (0, 3):
            with self.subTest(version=version):
                self.db_path.unlink()
                init_db()
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("PRAGMA foreign_keys = OFF")
                    original = conn.execute(
                        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'cash_flows'"
                    ).fetchone()[0]
                    indexes = [row[0] for row in conn.execute(
                        "SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'cash_flows' "
                        "AND sql IS NOT NULL"
                    )]
                    triggers = [row[0] for row in conn.execute(
                        "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'cash_flows'"
                    )]
                    broken = original.replace(
                        "INTEGER PRIMARY KEY AUTOINCREMENT", "INTEGER PRIMARY KEY DESC"
                    )
                    self.assertNotEqual(broken, original)
                    conn.execute("DROP TABLE cash_flows")
                    conn.execute(broken)
                    for statement in indexes + triggers:
                        conn.execute(statement)
                    conn.execute(f"PRAGMA user_version = {version}")
                    before = list(conn.iterdump())
                with self.assertRaisesRegex(RuntimeError, "cash_flows primary key"):
                    init_db()
                with sqlite3.connect(self.db_path) as conn:
                    self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], version)
                    self.assertEqual(list(conn.iterdump()), before)

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
                    self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], db_migrations.CURRENT_SCHEMA_VERSION)
                    self.assertNotIn(column, {row[1] for row in conn.execute(f"PRAGMA table_info({table})")})
                self.db_path.unlink()
                init_db()

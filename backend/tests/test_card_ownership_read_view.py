"""Validation work counts are semantic: the canonical validator still runs."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
import sqlite3
from unittest.mock import patch

from app.db import connect, session
from app.repositories.entries import append_planned_entry, confirm_planned_entry
from app.schemas import PlannedEntryIn
from app.services import financial_relationships as relationships
from app.services import summary
from app.services.summary import current_summary_values, _current_summary_values
from tests.db_fixture import IsolatedDatabaseTestCase


class CardOwnershipReadViewTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        with session() as conn:
            self.entry = conn.execute(
                "INSERT INTO ledger_entries(book_section,entry_kind,title,amount_value,"
                "sort_order,payment_key,entry_date) VALUES('archive','expense','card',"
                "10000,1,'card-key','2026-09-01')"
            ).lastrowid
            batch = conn.execute("INSERT INTO card_payment_batches(usage_month,status) "
                                 "VALUES('2026-09','active')").lastrowid
            conn.execute("INSERT INTO card_payment_batch_items(batch_id,entry_id,entry_payment_key) "
                         "VALUES(?,?,'card-key')", (batch, self.entry))

    def counter(self):
        return patch.object(relationships, "validate_card_payment_ownership",
                            wraps=relationships.validate_card_payment_ownership)

    def validate(self, view):
        relationships.validate_runtime_card_payment_ownership(view)

    def test_summary_validates_card_ownership_once_per_read_view(self):
        with self.counter() as validate:
            first = current_summary_values()
            self.assertEqual(validate.call_count, 1)
            self.assertEqual(current_summary_values(), first)
            self.assertEqual(validate.call_count, 2)

    def test_summary_output_and_persistent_state_match_uncached_path(self):
        source = append_planned_entry(PlannedEntryIn(title="recurring", usage_place="shop",
                                                  amount_value=5000, due_day=5))["id"]
        confirm_planned_entry(source, today=date(2026, 10, 5))
        with session(transaction_mode="DEFERRED") as conn:
            before = tuple(conn.iterdump())
            expected = summary._summary_values_from_read_view(conn)
            actual = _current_summary_values(conn)
            self.assertEqual(actual, expected)
            self.assertEqual(tuple(conn.iterdump()), before)

    def test_same_view_does_not_repeat_the_six_table_scan(self):
        queries = []
        with session(transaction_mode="DEFERRED") as conn:
            conn.set_trace_callback(queries.append)
            with relationships.card_ownership_read_view(conn) as view, self.counter() as validate:
                for _ in range(3):
                    self.validate(view)
                self.assertEqual(validate.call_count, 1)
            for table in relationships.CARD_RELATIONSHIP_TABLES:
                self.assertEqual(queries.count(f"SELECT * FROM {table}"), 1)

    def test_new_transaction_same_connection_and_contents_recomputes(self):
        conn = connect()
        with self.counter() as validate:
            try:
                for _ in range(2):
                    conn.execute("BEGIN DEFERRED")
                    with relationships.card_ownership_read_view(conn) as view:
                        self.validate(view)
                    conn.commit()
                self.assertEqual(validate.call_count, 2)
            finally:
                conn.close()

    def test_autocommit_summary_keeps_independent_validation(self):
        with session() as conn, self.counter() as validate:
            _current_summary_values(conn)
            self.assertEqual(validate.call_count, 3)
            self.assertFalse(conn.in_transaction)
        with session() as conn:
            with self.assertRaisesRegex(ValueError, "active transaction"):
                with relationships.card_ownership_read_view(conn):
                    self.fail("autocommit view must not be admitted")

    def test_borrowed_writer_sees_prior_writes_and_can_write_after_scope(self):
        with session(transaction_mode="IMMEDIATE") as conn:
            conn.execute("UPDATE app_settings SET value='1234' WHERE key='cash_flow_balance'")
            self.assertEqual(_current_summary_values(conn)["cash_flow_balance"], 1234)
            self.assertTrue(conn.in_transaction)
            self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 0)
            conn.execute("UPDATE app_settings SET value='5678' WHERE key='cash_flow_balance'")
            self.assertEqual(_current_summary_values(conn)["cash_flow_balance"], 5678)
            conn.rollback()
        self.assertEqual(current_summary_values()["cash_flow_balance"], 0)

    def test_proxy_and_alias_writes_are_blocked(self):
        with session(transaction_mode="DEFERRED") as conn:
            before = tuple(conn.iterdump())
            with relationships.card_ownership_read_view(conn) as view:
                self.validate(view)
                for sql in ("UPDATE ledger_entries SET amount_value=0", "PRAGMA query_only=OFF",
                            "COMMIT", "ROLLBACK", "CREATE TABLE surprise(id)"):
                    with self.subTest(sql=sql), self.assertRaises(ValueError):
                        view.execute(sql)
                with self.assertRaises(sqlite3.OperationalError):
                    conn.execute("UPDATE ledger_entries SET amount_value=0")
                self.validate(view)
            self.assertEqual(tuple(conn.iterdump()), before)

    def test_read_guard_accepts_valid_select_whitespace(self):
        with session(transaction_mode="DEFERRED") as conn:
            with relationships.card_ownership_read_view(conn) as view:
                for sql in ("SELECT\n1", "SELECT(1)", " select\t1"):
                    self.assertEqual(view.execute(sql).fetchone()[0], 1)

    def test_ended_view_cannot_be_used_after_commit_or_rollback(self):
        for end in ("commit", "rollback"):
            with self.subTest(end=end), session(transaction_mode="DEFERRED") as conn:
                with relationships.card_ownership_read_view(conn) as view:
                    self.validate(view)
                getattr(conn, end)()
                conn.execute("BEGIN DEFERRED")
                with self.assertRaises(ValueError):
                    self.validate(view)
                with self.assertRaises(ValueError):
                    view.execute("SELECT * FROM ledger_entries")
                with relationships.card_ownership_read_view(conn) as fresh:
                    self.validate(fresh)

    def test_transaction_aba_through_raw_alias_cannot_reuse_pass(self):
        for end in ("COMMIT", "ROLLBACK"):
            with self.subTest(end=end), session(transaction_mode="DEFERRED") as conn:
                with self.assertRaises(sqlite3.OperationalError):
                    with relationships.card_ownership_read_view(conn) as view:
                        self.validate(view)
                        changes = conn.total_changes
                        conn.execute(end)
                        conn.execute("BEGIN DEFERRED")
                        self.assertEqual(conn.total_changes, changes)
                        self.validate(view)
                self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 0)

    def test_alias_disabling_read_only_or_mutating_cannot_reuse_pass(self):
        for mutate in (False, True):
            with self.subTest(mutate=mutate), session(transaction_mode="DEFERRED") as conn:
                with self.assertRaises(ValueError):
                    with relationships.card_ownership_read_view(conn) as view:
                        self.validate(view)
                        conn.execute("PRAGMA query_only=OFF")
                        if mutate:
                            conn.execute("UPDATE ledger_entries SET amount_value=0")
                            conn.execute("PRAGMA query_only=ON")
                        self.validate(view)
                self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 0)
                conn.rollback()

    def test_schema_change_cannot_reuse_pass_even_without_row_changes(self):
        with session(transaction_mode="DEFERRED") as conn:
            with self.assertRaises(ValueError):
                with relationships.card_ownership_read_view(conn) as view:
                    self.validate(view)
                    conn.execute("PRAGMA query_only=OFF")
                    conn.execute("ALTER TABLE ledger_entries ADD COLUMN surprise TEXT")
                    conn.execute("PRAGMA query_only=ON")
                    self.validate(view)
            conn.rollback()

    def test_temporary_table_shadow_cannot_reuse_pass_without_row_changes(self):
        with session(transaction_mode="DEFERRED") as conn:
            with self.assertRaises(ValueError):
                with relationships.card_ownership_read_view(conn) as view:
                    self.validate(view)
                    changes = conn.total_changes
                    conn.execute("PRAGMA query_only=OFF")
                    conn.execute("CREATE TEMP TABLE ledger_entries(id)")
                    conn.execute("PRAGMA query_only=ON")
                    self.assertEqual(conn.total_changes, changes)
                    self.validate(view)
            conn.rollback()

    def test_nested_views_do_not_share_success_or_remove_outer_read_guard(self):
        with session(transaction_mode="DEFERRED") as conn, self.counter() as validate:
            with relationships.card_ownership_read_view(conn) as outer:
                self.validate(outer)
                with relationships.card_ownership_read_view(conn) as inner:
                    self.validate(inner)
                self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 1)
                self.validate(outer)
            self.assertEqual(validate.call_count, 2)
            self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 0)

    def test_existing_read_only_and_authorizer_are_preserved(self):
        with session(transaction_mode="DEFERRED") as conn:
            conn.execute("PRAGMA query_only=ON")
            seen = []

            def authorizer(action, first, second, database, trigger):
                seen.append((action, first))
                return sqlite3.SQLITE_OK

            conn.set_authorizer(authorizer)
            with relationships.card_ownership_read_view(conn) as view:
                self.validate(view)
            self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 1)
            seen.clear()
            conn.execute("SELECT title FROM ledger_entries WHERE id=-99")
            self.assertTrue(seen)

    def test_different_connections_and_parallel_requests_recompute(self):
        with self.counter() as validate:
            with ThreadPoolExecutor(max_workers=2) as pool:
                values = list(pool.map(lambda _: current_summary_values(), range(2)))
            self.assertEqual(values[0], values[1])
            self.assertEqual(validate.call_count, 2)

    def test_wal_writer_cannot_change_an_existing_view_but_new_view_rejects(self):
        with session() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
        with session(transaction_mode="DEFERRED") as conn, self.counter() as validate:
            with relationships.card_ownership_read_view(conn) as view:
                self.validate(view)
                with session(transaction_mode="IMMEDIATE") as writer:
                    writer.execute("UPDATE ledger_entries SET amount_value=-0.5 WHERE id=?", (self.entry,))
                self.validate(view)
                self.assertEqual(view.execute("SELECT amount_value FROM ledger_entries WHERE id=?",
                                             (self.entry,)).fetchone()[0], 10000)
                self.assertEqual(validate.call_count, 1)
        with self.assertRaises(ValueError):
            current_summary_values()

    def test_failure_is_never_memoized_as_success(self):
        with session(transaction_mode="IMMEDIATE") as conn:
            conn.execute("UPDATE ledger_entries SET amount_value=NULL WHERE id=?", (self.entry,))
            with relationships.card_ownership_read_view(conn) as view, self.counter() as validate:
                for _ in range(2):
                    with self.assertRaises(ValueError):
                        self.validate(view)
                self.assertEqual(validate.call_count, 2)
            conn.rollback()
        current_summary_values()

    def test_policy_changes_between_views_recompute(self):
        with session() as conn:
            conn.execute("INSERT INTO ledger_entries(book_section,entry_kind,title,amount_value,"
                         "sort_order,payment_key,entry_date) VALUES('current','expense','shop',"
                         "10000,2,'current-card','2026-10-01')")
        with self.counter() as validate:
            self.assertEqual(current_summary_values()["current_discount_total"], 120)
            with session() as conn:
                conn.execute("INSERT OR REPLACE INTO app_settings(key,value) "
                             "VALUES('card_discount_policy:owner:2026-10','disabled')")
            self.assertEqual(current_summary_values()["current_discount_total"], 0)
            self.assertEqual(validate.call_count, 2)

    def test_same_rows_new_evaluation_date_do_not_cache_summary(self):
        with session() as conn:
            conn.execute("INSERT INTO cash_flows(occurred_on,title,amount_value,sort_order) "
                         "VALUES('2026-10-06','future',1,1)")
        with session(transaction_mode="DEFERRED") as conn, self.counter() as validate:
            with relationships.card_ownership_read_view(conn) as view:
                with patch.object(summary, "app_today", return_value=date(2026, 10, 5)):
                    first = summary._summary_values_from_read_view(view)
                with patch.object(summary, "app_today", return_value=date(2026, 10, 6)):
                    second = summary._summary_values_from_read_view(view)
            self.assertEqual(second["cash_flow_balance"] - first["cash_flow_balance"], 1)
            # Only the date-independent ownership result is reused.
            self.assertEqual(validate.call_count, 1)

    def test_malformed_recurring_state_is_not_hidden_by_card_pass(self):
        source = append_planned_entry(PlannedEntryIn(title="recurring", usage_place="shop",
                                                  amount_value=5000, due_day=5))["id"]
        child = confirm_planned_entry(source, today=date(2026, 10, 5))["entry"]["id"]
        current_summary_values()
        for column, value in (("confirmed_at", None), ("source_planned_entry_id", None),
                              ("amount_value", None), ("amount_value", -0.5)):
            with self.subTest(column=column, value=value), session(transaction_mode="IMMEDIATE") as conn:
                conn.execute(f"UPDATE ledger_entries SET {column}=? WHERE id=?", (value, child))
                with self.assertRaises(ValueError):
                    _current_summary_values(conn)
                self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 0)
                conn.rollback()

    def test_malformed_card_error_matches_uncached_validator_in_a_new_view(self):
        for amount in (None, -1, -0.5, 9007199254740992):
            with self.subTest(amount=amount), session(transaction_mode="IMMEDIATE") as conn:
                _current_summary_values(conn)  # PASS in a completed, different view.
                conn.execute("UPDATE ledger_entries SET amount_value=? WHERE id=?", (amount, self.entry))
                with self.assertRaises(ValueError) as uncached:
                    self.validate(conn)
                with self.assertRaises(ValueError) as reused:
                    _current_summary_values(conn)
                self.assertEqual(str(reused.exception), str(uncached.exception))
                conn.rollback()

    def test_read_guard_error_cleans_up_without_committing_borrowed_writes(self):
        with session(transaction_mode="IMMEDIATE") as conn:
            conn.execute("UPDATE app_settings SET value='1234' WHERE key='cash_flow_balance'")
            conn.execute("SAVEPOINT caller_owned")
            with self.assertRaises(ValueError):
                with relationships.card_ownership_read_view(conn) as view:
                    self.validate(view)
                    conn.execute("PRAGMA query_only=OFF")
                    conn.execute("UPDATE app_settings SET value='5678' WHERE key='cash_flow_balance'")
                    self.validate(view)
            self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 0)
            conn.execute("ROLLBACK TO caller_owned")
            conn.execute("RELEASE caller_owned")
            self.assertEqual(_current_summary_values(conn)["cash_flow_balance"], 1234)
            conn.rollback()
        self.assertEqual(current_summary_values()["cash_flow_balance"], 0)

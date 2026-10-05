"""Export-local metadata work counts and unchanged Snapshot contracts."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import json
import sqlite3
from unittest.mock import patch
import threading

from app.db import session
from app.repositories.entries import append_planned_entry, confirm_planned_entry
from app.schemas import PlannedEntryIn
from app.services import snapshot
from tests.db_fixture import IsolatedDatabaseTestCase


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 6, 11, 12, tzinfo=timezone.utc).astimezone(tz)


class SnapshotExportMetadataTest(IsolatedDatabaseTestCase):
    def seed(self):
        source = append_planned_entry(PlannedEntryIn(
            title="recurring", usage_place="shop", amount_value=5000, due_day=11,
        ))["id"]
        child = confirm_planned_entry(source, today=date(2026, 6, 11))["entry"]["id"]
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET book_section='archive', "
                         "entry_date=NULL, amount_value=7000 WHERE id=?", (child,))
            conn.execute("INSERT INTO cash_flows(occurred_on,title,amount_value,sort_order) "
                         "VALUES('2026-06-11','cash',1234,1)")
        return source, child

    def export(self, conn):
        with patch.object(snapshot, "datetime", FixedDatetime):
            return snapshot.export_snapshot_from_connection(conn, date(2026, 6, 11))

    def reference_export(self, conn):
        """Independent previous column/empty-manifest rules, including ordering."""
        original_manifest = snapshot._build_manifest

        def previous_rows(conn, table, order_by, where=None, params=(), **unused):
            canonical = snapshot._schema_columns(table)
            live = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            columns = [column for column in canonical if column in live]
            selected = ", ".join(f'"{column}"' for column in columns)
            predicate = f" WHERE {where}" if where else ""
            return [dict(row) for row in conn.execute(
                f"SELECT {selected} FROM {table}{predicate} ORDER BY {order_by}", params,
            )]

        def previous_manifest(data, **kwargs):
            kwargs.pop("empty_table_columns", None)
            return original_manifest(data, **kwargs)

        with patch.object(snapshot, "_snapshot_rows", side_effect=previous_rows), \
                patch.object(snapshot, "_build_manifest", side_effect=previous_manifest):
            return self.export(conn)

    def assert_parity(self, conn):
        expected = self.reference_export(conn)
        actual = self.export(conn)
        self.assertEqual(actual, expected)
        self.assertEqual(json.dumps(actual, ensure_ascii=False).encode(),
                         json.dumps(expected, ensure_ascii=False).encode())
        self.assertEqual(snapshot.snapshot_state_fingerprint(actual[1]),
                         snapshot.snapshot_state_fingerprint(expected[1]))
        return actual[1]

    def test_one_canonical_schema_build_per_export_including_empty_manifest(self):
        for populated in (False, True):
            with self.subTest(populated=populated):
                if populated:
                    self.seed()
                with session(transaction_mode="DEFERRED") as conn, \
                        patch.object(snapshot, "_schema_connection",
                                     wraps=snapshot._schema_connection) as schemas:
                    self.export(conn)
                self.assertEqual(schemas.call_count, 1)

    def test_actual_live_table_info_once_per_table_not_once_per_column(self):
        self.seed()
        with session(transaction_mode="DEFERRED") as conn:
            statements = []
            conn.set_trace_callback(statements.append)
            self.export(conn)
        actual = Counter(sql for sql in statements
                         if sql.upper().startswith("PRAGMA TABLE_INFO("))
        expected = Counter({f"PRAGMA table_info({table})": 1
                            for table in snapshot.SNAPSHOT_TABLES})
        self.assertEqual(actual, expected)

    def test_full_output_manifest_hash_and_order_parity(self):
        with session(transaction_mode="DEFERRED") as conn:
            self.assert_parity(conn)
        self.seed()
        with session(transaction_mode="DEFERRED") as conn:
            artifact = self.assert_parity(conn)
        snapshot.restore_snapshot(artifact)
        with session(transaction_mode="DEFERRED") as conn:
            self.assert_parity(conn)

    def test_missing_optional_live_column_and_unknown_column_parity(self):
        # Column intersection, not schema admission: keep the previous export
        # rule for historical connections, including canonical EMPTY columns.
        with session() as conn:
            conn.execute("ALTER TABLE ledger_entries DROP COLUMN usage_item")
            conn.execute("ALTER TABLE app_labels ADD COLUMN unknown_export_column TEXT")
        with session(transaction_mode="DEFERRED") as conn:
            empty = self.assert_parity(conn)
        self.assertIn("usage_item", empty["manifest"]["tables"]["ledger_entries"]["columns"])
        with session() as conn:
            conn.execute("INSERT INTO ledger_entries(book_section,entry_kind,title,amount_value,sort_order) "
                         "VALUES('current','planned','optional',123,1)")
        with session(transaction_mode="DEFERRED") as conn:
            populated = self.assert_parity(conn)
        self.assertNotIn("usage_item", populated["data"]["ledger_entries"][0])
        self.assertNotIn("unknown_export_column", populated["data"]["app_labels"][0])

    def test_later_operation_discovers_changed_live_schema(self):
        with session() as conn:
            conn.execute("ALTER TABLE ledger_entries DROP COLUMN usage_item")
            conn.execute("INSERT INTO ledger_entries(book_section,entry_kind,title,amount_value,sort_order) "
                         "VALUES('current','planned','optional',123,1)")
        with session(transaction_mode="DEFERRED") as conn:
            before = self.export(conn)[1]
        self.assertNotIn("usage_item", before["data"]["ledger_entries"][0])
        with session() as conn:
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN usage_item TEXT")
            conn.execute("UPDATE ledger_entries SET usage_item='new schema value'")
        with session(transaction_mode="DEFERRED") as conn:
            after = self.assert_parity(conn)
        self.assertEqual(after["data"]["ledger_entries"][0]["usage_item"], "new schema value")

    def test_invalid_money_and_recurring_ownership_rejection_parity(self):
        source, child = self.seed()
        for column, value in (("amount_value", -0.5), ("amount_value", None),
                              ("confirmed_month", None), ("source_planned_entry_id", None)):
            with self.subTest(column=column), session(transaction_mode="IMMEDIATE") as conn:
                before = list(conn.iterdump())
                conn.execute(f"UPDATE ledger_entries SET {column}=? WHERE id=?", (value, child))
                invalid = list(conn.iterdump())
                messages = []
                for exporter in (self.reference_export, self.export):
                    with self.assertRaises(ValueError) as error:
                        exporter(conn)
                    messages.append(str(error.exception))
                    self.assertEqual(list(conn.iterdump()), invalid)
                self.assertEqual(messages[0], messages[1])
                conn.rollback()
                self.assertEqual(list(conn.iterdump()), before)
        self.assertIsInstance(source, int)

    def test_parallel_exports_do_not_share_live_column_metadata(self):
        # Each connection has its own schema; content values do not infer it.
        with snapshot._schema_connection() as conn:
            canonical_script = "\n".join(conn.iterdump())

        def isolated_export(drop_column):
            with sqlite3.connect(":memory:") as conn:
                conn.row_factory = sqlite3.Row
                conn.executescript(canonical_script)
                if drop_column:
                    conn.execute("ALTER TABLE ledger_entries DROP COLUMN usage_item")
                conn.execute("INSERT INTO ledger_entries(book_section,entry_kind,title,amount_value,sort_order) "
                             "VALUES('current','planned','parallel',123,1)")
                conn.commit()
                conn.execute("BEGIN DEFERRED")
                return snapshot.export_snapshot_from_connection(conn, date(2026, 6, 11))[1]

        with ThreadPoolExecutor(max_workers=2) as executor:
            without, complete = list(executor.map(isolated_export, (True, False)))
        self.assertNotIn("usage_item", without["data"]["ledger_entries"][0])
        self.assertIn("usage_item", complete["data"]["ledger_entries"][0])

    def test_caller_write_transaction_sees_uncommitted_row_and_never_commits_it(self):
        with session(transaction_mode="IMMEDIATE") as conn:
            conn.execute("INSERT INTO cash_flows(occurred_on,title,amount_value,sort_order) "
                         "VALUES('2026-06-11','uncommitted',1234,1)")
            artifact = self.assert_parity(conn)
            self.assertEqual(artifact["data"]["cash_flows"][0]["amount_value"], 1234)
            self.assertTrue(conn.in_transaction)
            conn.rollback()
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows").fetchone()[0], 0)

    def test_concurrent_ddl_cannot_change_the_export_transaction_schema_view(self):
        with session() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("INSERT INTO ledger_entries(book_section,entry_kind,title,usage_item,amount_value,sort_order) "
                         "VALUES('current','planned','schema view','original item',123,1)")
        columns_read = threading.Event()
        writer_finished = threading.Event()
        failures = []
        original_rows = snapshot._snapshot_rows

        def observed_rows(*args, **kwargs):
            if args[1] == "ledger_entries":
                columns_read.set()
                self.assertTrue(writer_finished.wait(timeout=5))
            return original_rows(*args, **kwargs)

        def writer():
            try:
                if not columns_read.wait(timeout=5):
                    raise AssertionError("export never discovered its schema")
                with session(transaction_mode="IMMEDIATE") as conn:
                    conn.execute("ALTER TABLE ledger_entries DROP COLUMN usage_item")
            except BaseException as error:
                failures.append(error)
            finally:
                writer_finished.set()

        thread = threading.Thread(target=writer)
        thread.start()
        try:
            with patch.object(snapshot, "_snapshot_rows", side_effect=observed_rows), \
                    session(transaction_mode="DEFERRED") as conn:
                artifact = self.export(conn)[1]
        finally:
            columns_read.set()
            thread.join(timeout=6)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(artifact["data"]["ledger_entries"][0]["usage_item"], "original item")
        with session(transaction_mode="DEFERRED") as conn:
            later = self.export(conn)[1]
        self.assertNotIn("usage_item", later["data"]["ledger_entries"][0])

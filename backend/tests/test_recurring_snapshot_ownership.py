import copy
import os
import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tests.db_fixture import IsolatedDatabaseTestCase
from tests.recurring_witness import preserve_synthetic_witnesses
from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import (
    append_planned_entry, confirm_planned_entry, create_entry, delete_entry, delete_planned_entry,
    list_confirmed_planned_entries, update_entry,
)
from app.schemas import LedgerEntryIn, LedgerEntryPatch, PlannedEntryIn
from app.services import snapshot
from app.repositories.panels import create_panel
from app.services.month import close_current_month
from app.services.panels import confirm_fixed_panel
from app.schemas import MonthlyPanelIn
from app.services.summary import current_summary_values


class RecurringSnapshotOwnershipTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.clock = patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-06-11"})
        self.clock.start()
        get_settings.cache_clear()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='100000' WHERE key='cash_flow_balance'")
            conn.execute("UPDATE app_settings SET value='0' WHERE key='scheduled_income'")
        self.source = append_planned_entry(PlannedEntryIn(
            title="recurring", usage_place="shop", amount_value=5000, due_day=11,
        ))["id"]
        self.generated = confirm_planned_entry(self.source)["entry"]["id"]
        self.valid = snapshot.export_snapshot()[1]
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)

    def tearDown(self):
        self.clock.stop()
        super().tearDown()

    def durable_state(self):
        with sqlite3.connect(self.db_path) as conn:
            database = (conn.execute("PRAGMA user_version").fetchone()[0], tuple(conn.iterdump()))
        directory = Path(self.temp_dir.name) / "snapshot-backups"
        backups = {file.name: file.read_bytes() for file in directory.glob("*") if file.is_file()}
        return database, backups

    def row(self, artifact, row_id):
        return next(row for row in artifact["data"]["ledger_entries"] if row["id"] == row_id)

    def resign(self, artifact):
        artifact["manifest"] = snapshot._build_manifest(artifact["data"],
            policy_context=artifact["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(artifact))
        artifact["snapshot_id"] = artifact["manifest"]["content_sha256"]
        return artifact

    def assert_rejected_unchanged(self, artifact):
        before = self.durable_state()
        try:
            snapshot.restore_snapshot(self.resign(artifact))
        except ValueError:
            pass
        else:
            self.fail(f"invalid ownership restored; liquidity={current_summary_values()['remaining_liquidity']}")
        self.assertEqual(self.durable_state(), before)
        init_db()
        self.assertEqual(self.durable_state(), before)

    def test_exact_full_epoch_absence_rejected_before_90060(self):
        bad = copy.deepcopy(self.valid)
        for row_id in (self.source, self.generated):
            self.row(bad, row_id).update(confirmed_month=None, confirmed_at=None)
        self.assert_rejected_unchanged(bad)

    def test_exact_confirmed_source_without_generated_rejected_before_100000(self):
        bad = copy.deepcopy(self.valid)
        bad["data"]["ledger_entries"] = [row for row in bad["data"]["ledger_entries"] if row["id"] != self.generated]
        self.assert_rejected_unchanged(bad)

    def test_v7_ownership_matrix(self):
        cases = ["source_only", "expense_only", "source_partial", "expense_partial", "mismatched_month",
                 "mismatched_time", "duplicate", "missing_source", "missing_source_id", "wrong_kind", "second_source",
                 "unconfirmed_source", "points_elsewhere", "epoch_keys_missing"]
        for case in cases:
            with self.subTest(case=case):
                bad = copy.deepcopy(self.valid)
                source = self.row(bad, self.source)
                child = self.row(bad, self.generated)
                if case == "source_only":
                    child.update(confirmed_month=None, confirmed_at=None)
                elif case == "expense_only":
                    source.update(confirmed_month=None, confirmed_at=None)
                elif case == "source_partial":
                    source["confirmed_at"] = None
                elif case == "expense_partial":
                    child["confirmed_month"] = None
                elif case == "mismatched_month":
                    child["confirmed_month"] = "2026-07"
                elif case == "mismatched_time":
                    child["confirmed_at"] = "2026-06-11 01:00:00"
                elif case == "duplicate":
                    duplicate = {**child, "id": 999, "payment_key": "duplicate-owned-expense"}
                    bad["data"]["ledger_entries"].append(duplicate)
                elif case == "missing_source":
                    bad["data"]["ledger_entries"].remove(source)
                elif case == "missing_source_id":
                    child["source_planned_entry_id"] = None
                elif case == "wrong_kind":
                    child["entry_kind"] = "planned"
                elif case == "unconfirmed_source":
                    source.update(confirmed_month=None, confirmed_at=None, entry_date=None)
                elif case == "points_elsewhere":
                    bad["data"]["ledger_entries"].append({**source, "id": 999,
                        "confirmed_month": None, "confirmed_at": None, "entry_date": None})
                    child["source_planned_entry_id"] = 999
                elif case == "epoch_keys_missing":
                    for row in (source, child):
                        row.pop("confirmed_month")
                        row.pop("confirmed_at")
                else:
                    duplicate_source = {**source, "id": 999}
                    bad["data"]["ledger_entries"].append(duplicate_source)
                self.assert_rejected_unchanged(bad)

    def test_runtime_malformed_ownership_cannot_read_edit_delete_or_reconfirm(self):
        for corruption in ("missing_child", "full_absence", "child_absence", "mismatch", "duplicate"):
            for operation in ("read", "edit_source", "delete_source", "reconfirm", "edit_child", "delete_child"):
                if corruption == "missing_child" and operation.endswith("child"):
                    continue
                with self.subTest(corruption=corruption, operation=operation):
                    with session() as conn:
                        conn.execute("DELETE FROM ledger_entries")
                        for row in sorted(self.valid["data"]["ledger_entries"], key=lambda item: item["entry_kind"] != "planned"):
                            columns = list(row)
                            conn.execute(f"INSERT INTO ledger_entries({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
                                         tuple(row[column] for column in columns))
                        if corruption == "missing_child":
                            conn.execute("DELETE FROM ledger_entries WHERE id=?", (self.generated,))
                        elif corruption == "full_absence":
                            conn.execute("UPDATE ledger_entries SET confirmed_at=NULL,confirmed_month=NULL")
                        elif corruption == "child_absence":
                            conn.execute("UPDATE ledger_entries SET confirmed_at=NULL,confirmed_month=NULL WHERE id=?", (self.generated,))
                        elif corruption == "mismatch":
                            conn.execute("UPDATE ledger_entries SET confirmed_month='2026-07' WHERE id=?", (self.generated,))
                        else:
                            child = {**self.row(self.valid, self.generated), "id": 999, "payment_key": "runtime-duplicate"}
                            conn.execute(f"INSERT INTO ledger_entries({','.join(child)}) VALUES({','.join('?' for _ in child)})", tuple(child.values()))
                    before = self.durable_state()
                    command = {
                        "read": lambda: list_confirmed_planned_entries(date(2026, 6, 11)),
                        "edit_source": lambda: update_entry(self.source, LedgerEntryPatch(title="changed")),
                        "delete_source": lambda: delete_entry(self.source),
                        "reconfirm": lambda: confirm_planned_entry(self.source, today=date(2026, 7, 11)),
                        "edit_child": lambda: update_entry(self.generated, LedgerEntryPatch(title="changed")),
                        "delete_child": lambda: delete_entry(self.generated),
                    }[operation]
                    with self.assertRaises(ValueError):
                        command()
                    self.assertEqual(self.durable_state(), before)

    def test_exporter_refuses_invalid_ownership_instead_of_emitting_invalid_v7(self):
        for corruption in ("missing_child", "full_absence", "mismatch", "orphan"):
            with self.subTest(corruption=corruption):
                snapshot.restore_snapshot(self.valid)
                with session() as conn:
                    if corruption == "missing_child":
                        conn.execute("DELETE FROM ledger_entries WHERE id=?", (self.generated,))
                    elif corruption == "full_absence":
                        conn.execute("UPDATE ledger_entries SET confirmed_at=NULL,confirmed_month=NULL")
                    elif corruption == "mismatch":
                        conn.execute("UPDATE ledger_entries SET confirmed_month='2026-07' WHERE id=?", (self.generated,))
                    else:
                        conn.execute("UPDATE ledger_entries SET source_planned_entry_id=NULL WHERE id=?", (self.generated,))
                before = self.durable_state()
                with self.assertRaises(ValueError):
                    snapshot.export_snapshot()
                self.assertEqual(self.durable_state(), before)
                # Restore a valid runtime relation directly, not through a
                # recovery export of the intentionally malformed source DB.
                with session() as conn:
                    conn.execute("DELETE FROM ledger_entries")
                    for row in sorted(self.valid["data"]["ledger_entries"], key=lambda item: item["entry_kind"] != "planned"):
                        conn.execute(f"INSERT INTO ledger_entries({','.join(row)}) VALUES({','.join('?' for _ in row)})", tuple(row.values()))

    def test_write_producers_cannot_create_unowned_confirmation_metadata(self):
        for kind, period, timestamp in (("expense", "2026-06", "2026-06-11 00:00:00"),
                                        ("planned", "2026-06", "2026-06-11 00:00:00"),
                                        ("expense", None, "2026-06-11 00:00:00")):
            with self.subTest(kind=kind, period=period):
                before = self.durable_state()
                with self.assertRaises(ValueError):
                    create_entry(LedgerEntryIn(book_section="current", entry_kind=kind,
                        entry_date="2026-06-11", title="unowned", usage_place="shop", amount_value=5000,
                        sort_order=50, due_day=11, confirmed_month=period, confirmed_at=timestamp))
                self.assertEqual(self.durable_state(), before)

    def test_unconfirmed_template_edit_cannot_invent_execution_without_epoch(self):
        delete_entry(self.generated)
        before = self.durable_state()
        with self.assertRaises(ValueError):
            update_entry(self.source, LedgerEntryPatch(entry_date="2026-06-11"))
        self.assertEqual(self.durable_state(), before)

    def test_complete_edited_relation_roundtrip_cancel_and_reconfirm(self):
        update_entry(self.generated, LedgerEntryPatch(title="edited", amount_value=7000, entry_date="2026-07-01"))
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        init_db()
        self.assertEqual(list_confirmed_planned_entries(date(2026, 6, 11))[0]["_confirmed_expense"]["amount_value"], 7000)
        self.assertEqual(current_summary_values()["remaining_liquidity"], 93084)
        self.assertTrue(delete_entry(self.generated))
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)
        self.assertIsNotNone(confirm_planned_entry(self.source))
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])

    def test_active_epoch_archived_by_closing_edited_earlier_month_cancels_exact_source(self):
        with session() as conn:
            conn.execute("INSERT INTO app_settings(key,value) VALUES('last_closed_month','2026-04') "
                         "ON CONFLICT(key) DO UPDATE SET value=excluded.value")
        update_entry(self.generated, LedgerEntryPatch(entry_date="2026-05-11"))
        close_current_month(date(2026, 6, 11), target_month="2026-05")
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        init_db()
        linked = list_confirmed_planned_entries()[0]["_confirmed_expense"]
        self.assertEqual(linked["book_section"], "archive")
        self.assertEqual(linked["entry_date"], "2026-05-11")
        self.assertEqual(linked["confirmed_month"], "2026-06")
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
        manual = create_entry(LedgerEntryIn(book_section="current", entry_date="2026-06-11",
            title="recurring", usage_place="shop", amount_value=5000, sort_order=50))
        self.assertTrue(delete_entry(manual["id"]))
        self.assertEqual(list_confirmed_planned_entries()[0]["_confirmed_expense"]["id"], linked["id"])
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
        self.assertTrue(delete_entry(linked["id"]))
        with session() as conn:
            parent = conn.execute("SELECT confirmed_month,confirmed_at FROM ledger_entries WHERE id=?", (self.source,)).fetchone()
            self.assertEqual(tuple(parent), (None, None))
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)
        confirm_planned_entry(self.source)
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)

    def test_complete_v7_and_manual_lookalike_keep_distinct_ownership(self):
        manual = create_entry(LedgerEntryIn(book_section="current", entry_date="2026-06-11",
            title="recurring", usage_place="shop", amount_value=5000, sort_order=50))
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        init_db()
        self.assertTrue(delete_entry(manual["id"]))
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
        self.assertEqual(list_confirmed_planned_entries()[0]["_confirmed_expense"]["id"], self.generated)
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)

    def test_valid_template_deletion_retires_metadata_not_actual_financial_fact(self):
        for route in (delete_planned_entry, delete_entry):
            with self.subTest(route=route.__name__):
                snapshot.restore_snapshot(self.valid)
                self.assertTrue(route(self.source))
                with session() as conn:
                    expense = dict(conn.execute("SELECT * FROM ledger_entries WHERE id=?", (self.generated,)).fetchone())
                self.assertIsNone(expense["source_planned_entry_id"])
                self.assertIsNone(expense["confirmed_at"])
                self.assertIsNone(expense["confirmed_month"])
                self.assertEqual(expense["amount_value"], 5000)
                snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)

    def test_restore_failure_injection_preserves_destination_and_existing_recovery(self):
        def fail_after(function):
            def wrapper(*args, **kwargs):
                function(*args, **kwargs)
                raise ValueError("injected after validation")
            return wrapper

        original_replace = snapshot._replace_snapshot_tables
        def fail_replacement(stage):
            def wrapper(conn, data):
                durable = bool(conn.execute("PRAGMA database_list").fetchone()[2])
                if stage == "temporary" and not durable:
                    original_replace(conn, data)
                    raise ValueError("injected temporary population failure")
                if durable:
                    if stage == "during_destination":
                        conn.execute("DELETE FROM ledger_entries")
                    raise ValueError("injected destination replacement failure")
                return original_replace(conn, data)
            return wrapper

        for stage in ("normalization", "ownership", "temporary", "before_destination", "during_destination"):
            with self.subTest(stage=stage):
                before = self.durable_state()
                target = "_normalized_snapshot_data" if stage == "normalization" else (
                    "_validate_snapshot_recurring_ownership" if stage == "ownership" else "_replace_snapshot_tables")
                original = getattr(snapshot, target)
                failure = fail_after(original) if stage in ("normalization", "ownership") else fail_replacement(stage)
                with patch.object(snapshot, target, failure):
                    with self.assertRaises(ValueError):
                        snapshot.restore_snapshot(self.valid)
                after = self.durable_state()
                self.assertEqual(after[0], before[0])
                self.assertTrue(before[1].items() <= after[1].items())
                if stage in ("normalization", "ownership", "temporary"):
                    self.assertEqual(after[1], before[1])
                for filename in after[1].keys() - before[1].keys():
                    artifact = snapshot.read_pre_restore_backup(filename)[1]
                    self.assertEqual(snapshot.snapshot_state_fingerprint(artifact), snapshot.snapshot_state_fingerprint(self.valid))
                init_db()
                self.assertEqual(self.durable_state()[0], before[0])

    def test_legacy_to_v7_then_missing_child_is_rejected(self):
        preserve_synthetic_witnesses(self.db_path)
        import json
        for version in (4, 5, 6):
            with self.subTest(version=version):
                legacy = json.loads((Path(__file__).parent / "fixtures" / f"snapshot_v{version}_recurring.json").read_text())
                snapshot.restore_snapshot(legacy)
                init_db()
                self.assertEqual(list_confirmed_planned_entries()[0]["_confirmed_expense"]["id"], 42)
                update_entry(42, LedgerEntryPatch(title="edited", usage_place="shop", entry_date="2026-07-01", amount_value=7000))
                snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                self.assertTrue(delete_entry(42))
                self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)
                confirm_planned_entry(41)
                current = snapshot.export_snapshot()[1]
                child = next(row for row in current["data"]["ledger_entries"] if row.get("source_planned_entry_id") == 41)
                current["data"]["ledger_entries"].remove(child)
                self.assert_rejected_unchanged(current)

    def test_closed_epoch_early_fixed_and_new_recurring_roundtrip(self):
        delete_entry(self.generated)
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-09-30"}):
            get_settings.cache_clear()
            with session() as conn:
                conn.execute("UPDATE app_settings SET value='1459200' WHERE key='scheduled_income'")
                conn.execute("INSERT INTO app_settings(key,value) VALUES('last_closed_month','2026-08') "
                             "ON CONFLICT(key) DO UPDATE SET value=excluded.value")
            closed_expense = confirm_planned_entry(self.source)["entry"]
            fixed = create_panel(MonthlyPanelIn(month="2026-10", panel_type="fixed", title="transfer",
                amount_value=820000, sort_order=1))
            close_current_month(date(2026, 9, 30), target_month="2026-09", allow_early_close=True)
            before = current_summary_values()
            self.assertEqual(before["cash_flow_balance"], 1559200)
            self.assertEqual(before["current_month_spendable"], 2188460)
            actual = confirm_fixed_panel(fixed["id"], "2026-09-30")
            after = current_summary_values()
            self.assertEqual(after["cash_flow_balance"], 739200)
            self.assertEqual(after["current_month_spendable"], before["current_month_spendable"])
            snapshot.restore_snapshot(snapshot.export_snapshot()[1])
            init_db()
            self.assertEqual(current_summary_values(), after)
            self.assertEqual(actual["panel"]["confirmed_month"], "2026-10")
            self.assertEqual(actual["cash_flow"]["occurred_on"], "2026-09-30")
            with self.assertRaises(ValueError):
                confirm_planned_entry(self.source)
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-10-01"}):
            get_settings.cache_clear()
            new_expense = confirm_planned_entry(self.source)["entry"]["id"]
            expected = current_summary_values()
            snapshot.restore_snapshot(snapshot.export_snapshot()[1])
            init_db()
            self.assertEqual(current_summary_values(), expected)
            self.assertEqual(list_confirmed_planned_entries()[0]["_confirmed_expense"]["id"], new_expense)
            with session() as conn:
                old = conn.execute("SELECT confirmed_month FROM ledger_entries WHERE payment_key=?",
                                   (closed_expense["payment_key"],)).fetchone()
                self.assertEqual(old[0], "2026-09")
            delete_entry(new_expense)
            self.assertIsNotNone(confirm_planned_entry(self.source))
            snapshot.restore_snapshot(snapshot.export_snapshot()[1])

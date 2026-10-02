import copy
import threading
from datetime import date
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from tests.db_fixture import IsolatedDatabaseTestCase
from app.db import init_db, session
from app import db_migrations
from app.repositories.entries import (
    append_planned_entry, confirm_planned_entry, create_entry, delete_entry,
    update_entry,
)
from app.schemas import LedgerEntryIn, LedgerEntryPatch, PlannedEntryIn
from app.services.card_charge import DiscountCard
from app.services.card_charge.policies import NoAutomaticDiscountPolicy
from app.services.card_charge.registry import POLICY_TIMELINES, PolicyBinding
from app.services.month import close_current_month
from app.services.snapshot import SNAPSHOT_SCHEMA_VERSION, export_snapshot, restore_snapshot
import app.services.snapshot as snapshot_service
from app.services.summary import current_summary_values


class SnapshotTest(IsolatedDatabaseTestCase):
    def _assert_unprovable_ownership_restore_rejected(self, snapshot) -> None:
        with session() as conn:
            before = list(conn.iterdump())
        with self.assertRaisesRegex(ValueError, "recurring confirmation"):
            restore_snapshot(snapshot)
        with session() as conn:
            self.assertEqual(list(conn.iterdump()), before)

    def test_legacy_generated_edit_then_delete_releases_confirmation(self) -> None:
        for version in (4, 5, 6):
            with self.subTest(version=version):
                fixture = Path(__file__).parent / "fixtures" / f"snapshot_v{version}_recurring.json"
                snapshot = json.loads(fixture.read_text(encoding="utf-8"))
                for row in snapshot["data"]["ledger_entries"]:
                    row["usage_place"] = "Provider"
                    row["usage_item"] = "Subscription"
                self._refresh_manifest(snapshot)
                restore_snapshot(snapshot)
                init_db()
                update_entry(42, LedgerEntryPatch(title="Edited after restore"))
                init_db()
                with session() as conn:
                    self.assertEqual(conn.execute(
                        "SELECT source_planned_entry_id FROM ledger_entries WHERE id = 42"
                    ).fetchone()[0], 41)
                _, current = export_snapshot(date(2026, 6, 11))
                restore_snapshot(current)
                init_db()
                self.assertTrue(delete_entry(42))
                with session() as conn:
                    self.assertIsNone(conn.execute(
                        "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
                    ).fetchone()[0])
                with patch("app.services.summary.app_today", return_value=date(2026, 6, 11)):
                    self.assertEqual(current_summary_values()["remaining_liquidity"], 95_000)
                self.assertIsNotNone(confirm_planned_entry(41, today=date(2026, 6, 11)))
                _, current = export_snapshot(date(2026, 6, 11))
                restore_snapshot(current)
                init_db()
                with session() as conn:
                    self.assertEqual(conn.execute(
                        "SELECT COUNT(*) FROM ledger_entries WHERE source_planned_entry_id = 41"
                    ).fetchone()[0], 1)

    def test_legacy_edit_cannot_transfer_source_to_identical_manual_expense(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        for row in snapshot["data"]["ledger_entries"]:
            row["usage_place"] = "Provider"
            row["usage_item"] = "Subscription"
        self._refresh_manifest(snapshot)
        restore_snapshot(snapshot)
        update_entry(42, LedgerEntryPatch(title="Edited after restore"))
        manual = create_entry(LedgerEntryIn(
            book_section="current", entry_kind="expense", entry_date=date(2026, 6, 11),
            title="Audit recurring", usage_place="Provider", usage_item="Subscription",
            amount_value=5000, sort_order=50,
        ))
        self.assertTrue(delete_entry(manual["id"]))
        with session() as conn:
            self.assertEqual(conn.execute(
                "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
            ).fetchone()[0], "2026-06")
            self.assertIsNotNone(conn.execute("SELECT 1 FROM ledger_entries WHERE id = 42").fetchone())

    def test_ambiguous_legacy_snapshot_with_prior_edit_never_binds_manual(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        generated = next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 42)
        generated["title"] = "Edited before export"
        generated["updated_at"] = "2026-06-12 00:00:00"
        manual = copy.deepcopy(generated)
        manual["id"] = 43
        manual["title"] = "Audit recurring"
        manual["payment_key"] = "independent-manual-expense"
        snapshot["data"]["ledger_entries"].append(manual)
        self._refresh_manifest(snapshot)
        self._assert_unprovable_ownership_restore_rejected(snapshot)

    def test_legacy_source_moved_to_other_month_does_not_bind_same_second_manual(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        generated = next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 42)
        generated["created_at"] = "2026-06-11 00:00:00"  # historical INSERT timestamp
        generated["entry_date"] = "2026-07-01"
        generated["title"] = "Edited generated expense"
        generated["updated_at"] = "2026-06-12 00:00:00"
        manual = copy.deepcopy(generated)
        manual.update({
            "id": 43, "entry_date": "2026-06-11", "title": "Audit recurring",
            "updated_at": "2026-06-11 00:00:00", "payment_key": "same-second-manual",
        })
        snapshot["data"]["ledger_entries"].append(manual)
        self._refresh_manifest(snapshot)
        self._assert_unprovable_ownership_restore_rejected(snapshot)

    def test_legacy_source_moved_month_does_not_bind_older_manual_edited_at_confirmation(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        generated = next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 42)
        generated.update({
            "created_at": "2026-06-11 00:00:00", "entry_date": "2026-07-01",
            "title": "Edited generated expense", "updated_at": "2026-06-12 00:00:00",
        })
        manual = copy.deepcopy(generated)
        manual.update({
            "id": 43, "created_at": "2026-06-10 00:00:00",
            "entry_date": "2026-06-11", "title": "Audit recurring",
            "updated_at": "2026-06-11 00:00:00", "payment_key": "older-manual-edited-same-second",
        })
        snapshot["data"]["ledger_entries"].append(manual)
        self._refresh_manifest(snapshot)
        self._assert_unprovable_ownership_restore_rejected(snapshot)

    def test_preexisting_unbound_legacy_row_binds_before_edit_not_at_delete(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        for row in snapshot["data"]["ledger_entries"]:
            row["usage_place"] = "Provider"
            row["usage_item"] = "Subscription"
        self._refresh_manifest(snapshot)
        restore_snapshot(snapshot)
        # A DB already restored by an older application could still carry the
        # source-less historical rows. Cancellation must not infer a link.
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET source_planned_entry_id = NULL WHERE id = 42")
        with self.assertRaisesRegex(ValueError, "unresolved legacy recurring"):
            delete_entry(42)
        update_entry(42, LedgerEntryPatch(title="Edited after durable binding"))
        init_db()
        with session() as conn:
            self.assertEqual(conn.execute(
                "SELECT source_planned_entry_id FROM ledger_entries WHERE id = 42"
            ).fetchone()[0], 41)
        self.assertTrue(delete_entry(42))
        with session() as conn:
            self.assertIsNone(conn.execute(
                "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
            ).fetchone()[0])

    def test_preexisting_unbound_edited_date_cannot_silently_delete_generated_expense(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        restore_snapshot(json.loads(fixture.read_text(encoding="utf-8")))
        # Simulate a legacy DB restored and edited before stable binding was
        # available. Its original creation timestamp survives the date edit.
        with session() as conn:
            conn.execute(
                "UPDATE ledger_entries SET source_planned_entry_id = NULL, "
                "created_at = '2026-06-11 00:00:00', entry_date = '2026-07-01', "
                "title = 'Changed before upgrade', updated_at = '2026-06-12 00:00:00' "
                "WHERE id = 42"
            )
        with self.assertRaisesRegex(ValueError, "unresolved legacy recurring"):
            delete_entry(42)
        with session() as conn:
            self.assertIsNotNone(conn.execute(
                "SELECT 1 FROM ledger_entries WHERE id = 42"
            ).fetchone())
            self.assertEqual(conn.execute(
                "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
            ).fetchone()[0], "2026-06")

    def test_legacy_confirmed_actual_amount_can_bind_without_rewriting_reserve(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        generated = next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 42)
        generated["amount_value"] = 4000
        generated["amount_expr"] = "4000"  # historical explicit actual-amount input
        for row in snapshot["data"]["ledger_entries"]:
            row["usage_place"] = "Provider"
            row["usage_item"] = "Subscription"
        self._refresh_manifest(snapshot)
        restore_snapshot(snapshot)
        with session() as conn:
            self.assertEqual(conn.execute(
                "SELECT source_planned_entry_id FROM ledger_entries WHERE id = 42"
            ).fetchone()[0], 41)
            self.assertEqual(conn.execute(
                "SELECT amount_value FROM ledger_entries WHERE id = 41"
            ).fetchone()[0], 5000)
        update_entry(42, LedgerEntryPatch(title="Edited"))
        self.assertTrue(delete_entry(42))
        with patch("app.services.summary.app_today", return_value=date(2026, 6, 11)):
            self.assertEqual(current_summary_values()["remaining_liquidity"], 95_000)

    def test_current_explicit_recurring_does_not_block_identical_manual_delete(self) -> None:
        planned = append_planned_entry(PlannedEntryIn(
            title="Subscription", usage_place="Provider", usage_item="Subscription",
            amount_value=5000, due_day=11,
        ))
        generated = confirm_planned_entry(planned["id"], today=date(2026, 6, 11))["entry"]
        manual = create_entry(LedgerEntryIn(
            book_section="current", entry_kind="expense", entry_date=date(2026, 6, 11),
            title="Subscription", usage_place="Provider", usage_item="Subscription",
            amount_value=5000, sort_order=50,
        ))
        self.assertTrue(delete_entry(manual["id"]))
        with session() as conn:
            self.assertEqual(conn.execute(
                "SELECT confirmed_month FROM ledger_entries WHERE id = ?", (planned["id"],)
            ).fetchone()[0], "2026-06")
            self.assertIsNotNone(conn.execute(
                "SELECT 1 FROM ledger_entries WHERE id = ?", (generated["id"],)
            ).fetchone())
        self.assertTrue(delete_entry(generated["id"]))
        with session() as conn:
            self.assertIsNone(conn.execute(
                "SELECT confirmed_month FROM ledger_entries WHERE id = ?", (planned["id"],)
            ).fetchone()[0])

    def test_fixed_snapshot_rejects_invalid_confirmation_timestamps(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_confirmed_fixed.json"
        source = json.loads(fixture.read_text(encoding="utf-8"))
        for invalid_time in ("not-a-time", "", "2026-02-30T00:00:00"):
            for linked in (True, False):
                with self.subTest(value=invalid_time, linked=linked):
                    snapshot = copy.deepcopy(source)
                    panel = snapshot["data"]["monthly_panels"][0]
                    panel["confirmed_at"] = invalid_time
                    if not linked:
                        panel["confirmed_cash_flow_id"] = None
                    self._refresh_manifest(snapshot)
                    with session() as conn:
                        before = list(conn.iterdump())
                    with self.assertRaises(ValueError):
                        restore_snapshot(snapshot)
                    with session() as conn:
                        self.assertEqual(list(conn.iterdump()), before)

    def test_v6_confirmed_fixed_without_link_fails_closed(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_confirmed_fixed.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        snapshot["data"]["monthly_panels"][0]["confirmed_cash_flow_id"] = None
        self._refresh_manifest(snapshot)
        with session() as conn:
            before = list(conn.iterdump())
        with self.assertRaisesRegex(ValueError, "confirmed fixed expense has no cash-flow relationship"):
            restore_snapshot(snapshot)
        with session() as conn:
            self.assertEqual(list(conn.iterdump()), before)

    def test_v7_fixed_confirmation_month_without_link_fails_closed(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_confirmed_fixed.json"
        restore_snapshot(json.loads(fixture.read_text(encoding="utf-8")))
        _, snapshot = export_snapshot(date(2026, 6, 11))
        panel = next(row for row in snapshot["data"]["monthly_panels"] if row["panel_type"] == "fixed")
        panel["confirmed_cash_flow_id"] = None
        panel["confirmed_at"] = None
        self._refresh_manifest(snapshot)
        with session() as conn:
            before = list(conn.iterdump())
        with self.assertRaisesRegex(ValueError, "confirmed fixed expense has no cash-flow relationship"):
            restore_snapshot(snapshot)
        with session() as conn:
            self.assertEqual(list(conn.iterdump()), before)

    def test_failed_migration_restart_then_legacy_restore_and_recurring_cancel(self) -> None:
        from tests.test_migration_characterization import FIXTURE_DIRECTORY

        self.db_path.unlink()
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript((FIXTURE_DIRECTORY / "schema_pre_batch.sql").read_text())
            conn.execute(
                "INSERT INTO ledger_entries(id, book_section, entry_kind, title, amount_value, "
                "payment_key, sort_order) VALUES "
                "(11, 'current', 'expense', 'Before migration', 10000, 'before-11', 1)"
            )
        original = db_migrations.MIGRATIONS

        def fail_after_schema_work(conn: sqlite3.Connection, schema: str) -> None:
            original[0](conn, schema)
            raise OSError("injected migration write failure")

        with patch.object(db_migrations, "MIGRATIONS", (fail_after_schema_work, *original[1:])):
            with self.assertRaisesRegex(OSError, "injected migration write failure"):
                init_db()
        with sqlite3.connect(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(conn.execute(
                "SELECT amount_value FROM ledger_entries WHERE id = 11"
            ).fetchone()[0], 10000)
        init_db()
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        restore_snapshot(json.loads(fixture.read_text(encoding="utf-8")))
        init_db()
        self.assertTrue(delete_entry(42))
        with patch("app.services.summary.app_today", return_value=date(2026, 6, 11)):
            self.assertEqual(current_summary_values()["remaining_liquidity"], 95_000)

    def test_historical_recurring_cancellation_restores_reserve_and_roundtrips(self) -> None:
        # Actual legacy exporters require normalization. The pre-epoch v7
        # artifact below is deliberately retained as a current-format rejection
        # fixture; complete v7 lifecycle is covered by the ownership tests.
        for version in (4, 5, 6):
            with self.subTest(snapshot_version=version):
                fixture = Path(__file__).parent / "fixtures" / f"snapshot_v{version}_recurring.json"
                snapshot = json.loads(fixture.read_text(encoding="utf-8"))
                self.assertEqual(snapshot["schema_version"], version)
                restore_snapshot(snapshot)
                init_db()
                self.assertTrue(delete_entry(42))
                with session() as conn:
                    planned = conn.execute(
                        "SELECT confirmed_at, confirmed_month FROM ledger_entries WHERE id = 41"
                    ).fetchone()
                    self.assertIsNone(planned["confirmed_at"])
                    self.assertIsNone(planned["confirmed_month"])
                with patch("app.services.summary.app_today", return_value=date(2026, 6, 11)):
                    self.assertEqual(current_summary_values()["remaining_liquidity"], 95_000)
                confirmed = confirm_planned_entry(41, today=date(2026, 6, 11))
                self.assertIsNotNone(confirmed)
                self.assertEqual(confirmed["entry"]["source_planned_entry_id"], 41)
                _, current = export_snapshot(date(2026, 6, 11))
                self.assertEqual(current["schema_version"], 7)
                restore_snapshot(current)
                init_db()
                self.assertTrue(delete_entry(confirmed["entry"]["id"]))
                with session() as conn:
                    self.assertIsNone(conn.execute(
                        "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
                    ).fetchone()[0])

    def test_ambiguous_legacy_recurring_cancellation_rolls_back(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        original = json.loads(fixture.read_text(encoding="utf-8"))
        for duplicate_kind in ("planned", "expense"):
            with self.subTest(duplicate_kind=duplicate_kind):
                snapshot = copy.deepcopy(original)
                duplicate = copy.deepcopy(next(
                    row for row in snapshot["data"]["ledger_entries"]
                    if row["entry_kind"] == duplicate_kind
                ))
                duplicate["id"] = 43
                if duplicate_kind == "expense":
                    duplicate["payment_key"] = "duplicate-legacy-candidate"
                    duplicate["entry_date"] = "2026-06-12"
                snapshot["data"]["ledger_entries"].append(duplicate)
                self._refresh_manifest(snapshot)
                self._assert_unprovable_ownership_restore_rejected(snapshot)

    def test_pre_epoch_historical_v7_cannot_bypass_current_ownership_contract(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v7_recurring.json"
        self._assert_unprovable_ownership_restore_rejected(json.loads(fixture.read_text(encoding="utf-8")))

    def test_older_confirmed_row_without_planned_date_requires_unique_month_match(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v4_recurring.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        planned = next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 41)
        planned["entry_date"] = None  # possible pre-v4 confirmation carried into a v4 export
        self._refresh_manifest(snapshot)
        restore_snapshot(snapshot)
        self.assertTrue(delete_entry(42))
        with session() as conn:
            self.assertIsNone(conn.execute(
                "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
            ).fetchone()[0])
        with patch("app.services.summary.app_today", return_value=date(2026, 6, 11)):
            self.assertEqual(current_summary_values()["remaining_liquidity"], 95_000)

    def test_legacy_recurring_export_as_v7_then_cancel_keeps_legacy_meaning(self) -> None:
        for version in (4, 5, 6):
            with self.subTest(snapshot_version=version):
                fixture = Path(__file__).parent / "fixtures" / f"snapshot_v{version}_recurring.json"
                restore_snapshot(json.loads(fixture.read_text(encoding="utf-8")))
                _, current = export_snapshot(date(2026, 6, 11))
                self.assertEqual(current["schema_version"], 7)
                restore_snapshot(current)
                init_db()
                self.assertTrue(delete_entry(42))
                with session() as conn:
                    self.assertIsNone(conn.execute(
                        "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
                    ).fetchone()[0])
                with patch("app.services.summary.app_today", return_value=date(2026, 6, 11)):
                    self.assertEqual(current_summary_values()["remaining_liquidity"], 95_000)

    def test_unresolved_legacy_recurring_cancellation_fails_before_delete(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        generated = next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 42)
        generated["amount_value"] = 4000
        generated["updated_at"] = "2026-06-12 00:00:00"
        self._refresh_manifest(snapshot)
        self._assert_unprovable_ownership_restore_rejected(snapshot)
        # Independently retain the runtime cancellation guard for a DB which
        # was restored by an older release before import-time ownership checks.
        restore_snapshot(json.loads(fixture.read_text(encoding="utf-8")))
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET amount_value=4000,source_planned_entry_id=NULL, "
                         "confirmed_month=NULL,confirmed_at=NULL,updated_at='2026-06-12 00:00:00' WHERE id=42")
        with self.assertRaisesRegex(ValueError, "ambiguous legacy recurring"):
            delete_entry(42)
        with session() as conn:
            self.assertEqual(conn.execute(
                "SELECT amount_value FROM ledger_entries WHERE id = 42"
            ).fetchone()[0], 4000)
            self.assertEqual(conn.execute(
                "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
            ).fetchone()[0], "2026-06")

    def test_unrelated_expense_with_no_legacy_match_still_deletes(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        restore_snapshot(json.loads(fixture.read_text(encoding="utf-8")))
        with session() as conn:
            conn.execute(
                "INSERT INTO ledger_entries(id, book_section, entry_kind, entry_date, title, "
                "amount_value, sort_order, payment_key) VALUES "
                "(43, 'current', 'expense', '2026-06-12', 'Unrelated cash', 1000, 3, 'unrelated')"
            )
        self.assertTrue(delete_entry(43))
        with session() as conn:
            self.assertEqual(conn.execute(
                "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
            ).fetchone()[0], "2026-06")
            self.assertIsNotNone(conn.execute("SELECT 1 FROM ledger_entries WHERE id = 42").fetchone())

    def test_legacy_recurring_delete_and_confirmation_reset_are_one_transaction(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        restore_snapshot(json.loads(fixture.read_text(encoding="utf-8")))
        with session() as conn:
            conn.execute(
                "CREATE TRIGGER reject_recurring_reset BEFORE UPDATE OF confirmed_month "
                "ON ledger_entries WHEN OLD.id = 41 BEGIN SELECT RAISE(ABORT, 'injected reset failure'); END"
            )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "injected reset failure"):
            delete_entry(42)
        with session() as conn:
            self.assertIsNotNone(conn.execute("SELECT 1 FROM ledger_entries WHERE id = 42").fetchone())
            self.assertEqual(conn.execute(
                "SELECT confirmed_month FROM ledger_entries WHERE id = 41"
            ).fetchone()[0], "2026-06")

    def test_fixed_snapshot_relationships_reject_contradictions_without_restoring(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_confirmed_fixed.json"
        legacy = json.loads(fixture.read_text(encoding="utf-8"))
        restore_snapshot(legacy)
        _, current = export_snapshot(date(2026, 6, 11))
        with session() as conn:
            conn.execute(
                "INSERT INTO cash_flows(id, occurred_on, title, amount_value, sort_order) "
                "VALUES (91, '2026-06-11', 'Existing destination', -700, 91)"
            )
        for source in (legacy, current):
            for mutation in (
                "duplicate", "wrong_flow_date", "wrong_role", "missing_flow",
                "wrong_month", "payment_flow_reused",
            ):
                with self.subTest(version=source["schema_version"], mutation=mutation):
                    invalid = copy.deepcopy(source)
                    panel = invalid["data"]["monthly_panels"][0]
                    if mutation == "duplicate":
                        duplicate = copy.deepcopy(panel)
                        duplicate["id"] = 32
                        invalid["data"]["monthly_panels"].append(duplicate)
                    elif mutation == "wrong_flow_date":
                        invalid["data"]["cash_flows"][0]["occurred_on"] = "2026-07-01"
                    elif mutation == "wrong_role":
                        invalid["data"]["cash_flows"][0]["amount_value"] = 5000
                    elif mutation == "wrong_month":
                        panel["confirmed_month"] = "2026-05"
                    elif mutation == "payment_flow_reused":
                        flow_id = invalid["data"]["cash_flows"][0]["id"]
                        invalid["data"]["card_payment_events"].append({
                            "id": 91, "event_date": "2026-06-11", "event_type": "immediate",
                            "total_amount": 5000, "cash_flow_id": flow_id,
                        })
                        invalid["data"]["card_payment_allocations"].append({
                            "id": 91, "payment_event_id": 91,
                            "entry_payment_key": "synthetic-payment", "amount_value": 5000,
                        })
                    else:
                        panel["confirmed_cash_flow_id"] = 9999
                    self._refresh_manifest(invalid)
                    with self.assertRaises(ValueError):
                        restore_snapshot(invalid)
                    init_db()
                    with session() as conn:
                        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 3)
                        self.assertEqual(conn.execute(
                            "SELECT amount_value FROM cash_flows WHERE id = 91"
                        ).fetchone()[0], -700)

    def test_fixed_snapshot_allows_actual_amount_different_from_reserve(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_confirmed_fixed.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        snapshot["data"]["cash_flows"][0]["amount_value"] = -3000
        self._refresh_manifest(snapshot)
        restore_snapshot(snapshot)
        with session() as conn:
            self.assertEqual(conn.execute(
                "SELECT amount_value FROM monthly_panels WHERE id = 31"
            ).fetchone()[0], 5000)
            self.assertEqual(conn.execute(
                "SELECT amount_value FROM cash_flows WHERE id = 1"
            ).fetchone()[0], -3000)
        _, current = export_snapshot(date(2026, 6, 11))
        restore_snapshot(current)
        with session() as conn:
            self.assertEqual(conn.execute(
                "SELECT amount_value FROM cash_flows WHERE id = 1"
            ).fetchone()[0], -3000)

    def test_migrated_historical_db_then_legacy_snapshot_recurring_delete(self) -> None:
        from tests.test_migration_characterization import FIXTURE_DIRECTORY

        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_recurring.json"
        for era in ("pre_batch", "offline_phase2"):
            with self.subTest(era=era):
                self.db_path.unlink()
                with sqlite3.connect(self.db_path) as conn:
                    conn.executescript((FIXTURE_DIRECTORY / f"schema_{era}.sql").read_text())
                init_db()
                restore_snapshot(json.loads(fixture.read_text(encoding="utf-8")))
                init_db()
                self.assertTrue(delete_entry(42))
                with patch("app.services.summary.app_today", return_value=date(2026, 6, 11)):
                    self.assertEqual(current_summary_values()["remaining_liquidity"], 95_000)

    def test_supported_snapshot_versions_restore_then_restart_and_reexport(self) -> None:
        with session() as conn:
            conn.execute(
                "INSERT INTO ledger_entries(id, book_section, entry_kind, entry_date, title, "
                "amount_value, sort_order, payment_key) VALUES "
                "(11, 'current', 'expense', '2026-06-11', 'Versioned card', 10000, 1, 'snapshot-card-11')"
            )
            conn.execute(
                "INSERT INTO cash_flows(id, occurred_on, title, amount_value, sort_order) "
                "VALUES (21, '2026-06-11', 'Versioned cash', -500, 1)"
            )
        _, original = export_snapshot(date(2026, 6, 11))
        for version in (4, 5, 6, 7):
            with self.subTest(snapshot_version=version):
                snapshot = copy.deepcopy(original)
                if version == 4:
                    self._convert_to_v4_liquidity_keys(snapshot)
                    for panel in snapshot["data"]["monthly_panels"]:
                        panel.pop("confirmed_month", None)
                        panel.pop("confirmed_cash_flow_id", None)
                    for entry in snapshot["data"]["ledger_entries"]:
                        entry.pop("source_planned_entry_id", None)
                    for event in snapshot["data"]["card_payment_events"]:
                        event.pop("idempotency_key", None)
                        event.pop("request_fingerprint", None)
                    self._refresh_manifest(snapshot)
                else:
                    snapshot["schema_version"] = version
                    if version == 5:
                        for row in snapshot["data"]["monthly_panels"]:
                            row.pop("confirmed_cash_flow_id", None)
                    if version <= 6:
                        for row in snapshot["data"]["ledger_entries"]:
                            row.pop("source_planned_entry_id", None)
                        for row in snapshot["data"]["monthly_panels"]:
                            row.pop("confirmed_month", None)
                        for row in snapshot["data"]["card_payment_events"]:
                            row.pop("idempotency_key", None)
                            row.pop("request_fingerprint", None)
                    self._refresh_manifest(snapshot)
                restore_snapshot(snapshot)
                init_db()
                _, current = export_snapshot(date(2026, 6, 11))
                self.assertEqual(current["schema_version"], SNAPSHOT_SCHEMA_VERSION)
                self.assertEqual(
                    [(row["id"], row["amount_value"]) for row in current["data"]["ledger_entries"]],
                    [(11, 10000)],
                )
                self.assertEqual(
                    [(row["id"], row["amount_value"]) for row in current["data"]["cash_flows"]],
                    [(21, -500)],
                )

    def test_export_contains_all_ledger_data_and_excludes_sensitive_auth_state(self) -> None:
        self._seed_data()

        filename, snapshot = export_snapshot(date(2026, 6, 11))

        self.assertTrue(filename.endswith(".money-note-snapshot.json"))
        self.assertEqual(snapshot["schema_version"], SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(snapshot["range"], {"scope": "all"})
        self.assertEqual(snapshot["manifest"]["algorithm"], "sha256")
        self.assertEqual(
            snapshot["card_charge_policy"]["cards"]["owner"][0]["policy_id"],
            "owner-flat-statement-1.2",
        )
        self.assertEqual(
            snapshot["card_charge_policy"]["cards"]["owner"][0]["parameters"]["rate"],
            "0.012",
        )
        self.assertEqual(snapshot["card_charge_policy"]["covered_through"], "2026-06")
        self.assertEqual(
            snapshot["snapshot_id"],
            snapshot["manifest"]["content_sha256"],
        )
        self.assertTrue(snapshot["manifest"]["card_charge_policy_sha256"])
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
        self.assertEqual(snapshot["manifest"]["tables"]["card_payment_batches"]["row_count"], 2)
        self.assertEqual(snapshot["manifest"]["tables"]["card_payment_batch_items"]["row_count"], 2)
        allocation_keys = {row["entry_payment_key"] for row in snapshot["data"]["card_payment_allocations"]}
        self.assertIn("recent-key", allocation_keys)
        self.assertIn("old-key", allocation_keys)
        deferral_keys = {row["entry_payment_key"] for row in snapshot["data"]["card_payment_deferrals"]}
        self.assertIn("recent-key", deferral_keys)
        self.assertIn("old-key", deferral_keys)
        setting_keys = {row["key"] for row in snapshot["data"]["app_settings"]}
        self.assertIn("scheduled_income", setting_keys)
        self.assertIn("cash_flow_balance", setting_keys)
        self.assertNotIn("interest_expense", setting_keys)
        self.assertNotIn("base_next_month_liquidity", setting_keys)
        self.assertNotIn("liquidity_status", setting_keys)
        label_keys = {row["key"] for row in snapshot["data"]["app_labels"]}
        self.assertIn("summary_cash_flow_balance_label", label_keys)
        self.assertIn("summary_remaining_liquidity_label", label_keys)
        self.assertNotIn("summary_liquidity_status_label", label_keys)
        self.assertNotIn("summary_next_month_liquidity_label", label_keys)
        self.assertNotIn("summary_interest_expense_label", label_keys)
        self.assertNotIn("share_pin_hash", setting_keys)
        self.assertNotIn("share_pin_is_default", setting_keys)
        self.assertNotIn("users", snapshot["data"])
        self.assertNotIn("auth_sessions", snapshot["data"])
        self.assertNotIn("audit_logs", snapshot["data"])

    def test_snapshot_v7_contains_new_relation_and_idempotency_columns(self) -> None:
        self._seed_data()

        _, snapshot = export_snapshot(date(2026, 6, 11))

        self.assertIn(
            "source_planned_entry_id",
            snapshot["manifest"]["tables"]["ledger_entries"]["columns"],
        )
        self.assertIn(
            "confirmed_month",
            snapshot["manifest"]["tables"]["monthly_panels"]["columns"],
        )
        self.assertIn(
            "idempotency_key",
            snapshot["manifest"]["tables"]["card_payment_events"]["columns"],
        )
        self.assertIn(
            "request_fingerprint",
            snapshot["manifest"]["tables"]["card_payment_events"]["columns"],
        )
        event_keys = {
            row["idempotency_key"] for row in snapshot["data"]["card_payment_events"]
        }
        self.assertEqual(event_keys, {"snapshot-payment-recent", "snapshot-payment-old"})

    def test_export_reads_one_consistent_database_state_during_concurrent_write(self) -> None:
        self._seed_data()
        ledger_read = threading.Event()
        writer_inserted = threading.Event()
        writer_finished = threading.Event()
        original_snapshot_rows = snapshot_service._snapshot_rows

        def observed_snapshot_rows(conn, table, order_by, where=None, params=()):
            rows = original_snapshot_rows(conn, table, order_by, where, params)
            if table == "ledger_entries":
                ledger_read.set()
                self.assertTrue(writer_inserted.wait(timeout=2))
            return rows

        def writer() -> None:
            self.assertTrue(ledger_read.wait(timeout=2))
            with session(transaction_mode="IMMEDIATE") as conn:
                conn.execute(
                    """
                    INSERT INTO ledger_entries(
                        book_section, entry_kind, entry_date, title,
                        amount_value, sort_order, payment_key
                    )
                    VALUES ('current', 'expense', '2026-06-11',
                            '동시 기록', 7777, 99, 'concurrent-snapshot-key')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO monthly_panels(
                        month, panel_type, title, amount_value, sort_order
                    )
                    VALUES ('2026-06', 'claim', '동시 청구', 7777, 99)
                    """
                )
                writer_inserted.set()
            writer_finished.set()

        thread = threading.Thread(target=writer)
        thread.start()
        with patch.object(snapshot_service, "_snapshot_rows", side_effect=observed_snapshot_rows):
            _, snapshot = export_snapshot(date(2026, 6, 11))
        thread.join(timeout=3)

        self.assertTrue(writer_finished.is_set())
        self.assertFalse(
            any(row["title"] == "동시 기록" for row in snapshot["data"]["ledger_entries"])
        )
        self.assertFalse(
            any(row["title"] == "동시 청구" for row in snapshot["data"]["monthly_panels"])
        )
        with session() as conn:
            self.assertIsNotNone(
                conn.execute(
                    "SELECT id FROM ledger_entries WHERE payment_key = 'concurrent-snapshot-key'"
                ).fetchone()
            )
            self.assertIsNotNone(
                conn.execute(
                    "SELECT id FROM monthly_panels WHERE title = '동시 청구'"
                ).fetchone()
            )

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

    def test_startup_migrates_v6_database_with_additive_v7_columns(self) -> None:
        self.db_path.unlink()
        # The committed 53ff6e1 v6-era schema has no revision table. Removing
        # columns from today's SCHEMA would invent an impossible historical era.
        legacy_schema = (
            Path(__file__).parent / "fixtures" / "schema_fixed_expenses.sql"
        ).read_text(encoding="utf-8")
        legacy_conn = sqlite3.connect(self.db_path)
        try:
            legacy_conn.executescript(legacy_schema)
            legacy_conn.commit()
        finally:
            legacy_conn.close()

        init_db()

        with session() as conn:
            ledger_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(ledger_entries)")
            }
            panel_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(monthly_panels)")
            }
            event_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(card_payment_events)")
            }
        self.assertIn("source_planned_entry_id", ledger_columns)
        self.assertIn("confirmed_month", panel_columns)
        self.assertIn("idempotency_key", event_columns)
        self.assertIn("request_fingerprint", event_columns)

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

    def test_restore_preserves_fixed_confirmation_cash_flow_link(self) -> None:
        with session() as conn:
            flow_id = conn.execute(
                """
                INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order)
                VALUES ('2026-06-20', '변동 공과금', -112430, 1)
                """
            ).lastrowid
            conn.execute(
                """
                INSERT INTO monthly_panels(
                    id, month, panel_type, title, spent_on, amount_value,
                    sort_order, confirmed_at, confirmed_month, confirmed_cash_flow_id
                )
                VALUES (100, '2026-06', 'fixed', '변동 공과금', '2026-06-20', 150000,
                        1, '2026-06-20T00:00:00+00:00', '2026-06', ?)
                """,
                (flow_id,),
            )
        _, snapshot = export_snapshot(date(2026, 6, 20))

        restore_snapshot(snapshot)

        with session() as conn:
            panel = conn.execute(
                "SELECT amount_value, confirmed_cash_flow_id FROM monthly_panels WHERE id = 100",
            ).fetchone()
            flow = conn.execute(
                "SELECT amount_value FROM cash_flows WHERE id = ?",
                (flow_id,),
            ).fetchone()
        self.assertEqual(panel["amount_value"], 150000)
        self.assertEqual(panel["confirmed_cash_flow_id"], flow_id)
        self.assertEqual(flow["amount_value"], -112430)

    def test_restore_preserves_salary_created_by_month_close(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value, sort_order, payment_key
                )
                VALUES ('current', 'expense', '2026-06-30', '마감 대상', 1000, 1, 'salary-snapshot-key')
                """
            )
        close_current_month(date(2026, 7, 1))
        _, snapshot = export_snapshot(date(2026, 7, 1))

        with session() as conn:
            conn.execute("DELETE FROM cash_flows WHERE title = '급여'")
        restore_snapshot(snapshot)

        with session() as conn:
            salary = conn.execute(
                """
                SELECT occurred_on, amount_value, is_primary_income
                FROM cash_flows WHERE title = '급여'
                """
            ).fetchone()
        self.assertEqual(dict(salary), {
            "occurred_on": "2026-07-01",
            "amount_value": 400_000,
            "is_primary_income": 1,
        })

    def test_restore_accepts_v5_snapshot_without_fixed_cash_flow_link(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO monthly_panels(id, month, panel_type, title, amount_value, sort_order)
                VALUES (101, '2026-06', 'fixed', '구버전 고정지출', 50000, 1)
                """
            )
        _, snapshot = export_snapshot(date(2026, 6, 20))
        snapshot["schema_version"] = 5
        for row in snapshot["data"]["monthly_panels"]:
            row.pop("confirmed_cash_flow_id", None)
        self._refresh_manifest(snapshot)

        restore_snapshot(snapshot)

        with session() as conn:
            panel = conn.execute(
                "SELECT confirmed_cash_flow_id FROM monthly_panels WHERE id = 101",
            ).fetchone()
        self.assertIsNone(panel["confirmed_cash_flow_id"])

    def test_restore_accepts_v6_snapshot_without_v7_columns(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        snapshot["schema_version"] = 6
        for row in snapshot["data"]["ledger_entries"]:
            row.pop("source_planned_entry_id", None)
        for row in snapshot["data"]["monthly_panels"]:
            row.pop("confirmed_month", None)
        for row in snapshot["data"]["card_payment_events"]:
            row.pop("idempotency_key", None)
            row.pop("request_fingerprint", None)
        self._refresh_manifest(snapshot)

        restored = restore_snapshot(snapshot)

        self.assertEqual(restored["ledger_entries"], 3)
        self.assertEqual(restored["monthly_panels"], 4)
        with session() as conn:
            planned_sources = conn.execute(
                "SELECT source_planned_entry_id FROM ledger_entries"
            ).fetchall()
            event_keys = conn.execute(
                "SELECT idempotency_key, request_fingerprint FROM card_payment_events"
            ).fetchall()
        self.assertTrue(all(row["source_planned_entry_id"] is None for row in planned_sources))
        self.assertTrue(all(row["idempotency_key"] is None for row in event_keys))
        self.assertTrue(all(row["request_fingerprint"] is None for row in event_keys))

    def test_real_v6_confirmed_fixed_survives_restore_restart_and_month_close(self) -> None:
        # Exported by 53ff6e1 from synthetic cash=100000 and a confirmed fixed=5000.
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_confirmed_fixed.json"
        snapshot = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(snapshot["schema_version"], 6)
        self.assertNotIn("confirmed_month", snapshot["data"]["monthly_panels"][0])

        restore_snapshot(snapshot)
        init_db()  # A version-3 database must still preserve imported v6 meaning.
        with session() as conn:
            fixed = conn.execute(
                "SELECT confirmed_month, confirmed_cash_flow_id FROM monthly_panels WHERE id = 31"
            ).fetchone()
            self.assertEqual(fixed["confirmed_month"], "2026-06")
            self.assertIsNotNone(fixed["confirmed_cash_flow_id"])

        close_current_month(date(2026, 7, 1), target_month="2026-06")
        with session() as conn:
            fixed = conn.execute(
                "SELECT confirmed_at, confirmed_cash_flow_id FROM monthly_panels WHERE id = 31"
            ).fetchone()
            self.assertIsNone(fixed["confirmed_at"])
            self.assertIsNone(fixed["confirmed_cash_flow_id"])
        with patch("app.services.summary.app_today", return_value=date(2026, 7, 1)):
            summary = current_summary_values()
        self.assertEqual(summary["cash_flow_balance"], 95_000)
        self.assertEqual(summary["remaining_liquidity"], 90_000)

        _, current = export_snapshot(date(2026, 7, 1))
        self.assertEqual(current["schema_version"], 7)
        restore_snapshot(current)
        init_db()
        with patch("app.services.summary.app_today", return_value=date(2026, 7, 1)):
            self.assertEqual(current_summary_values()["remaining_liquidity"], 90_000)

    def test_unconfirmed_fixed_lifecycle_survives_each_supported_snapshot_version(self) -> None:
        with session() as conn:
            conn.execute("UPDATE app_settings SET value = '0' WHERE key = 'scheduled_income'")
            conn.execute("UPDATE app_settings SET value = '100000' WHERE key = 'cash_flow_balance'")
            conn.execute(
                "INSERT OR REPLACE INTO app_settings(key, value) VALUES('last_closed_month', '2026-05')"
            )
            conn.execute(
                "INSERT INTO monthly_panels(id, month, panel_type, title, amount_value, sort_order) "
                "VALUES (31, '2026-06', 'fixed', 'Synthetic reserve', 5000, 1)"
            )
        _, original = export_snapshot(date(2026, 6, 15))
        for version in (4, 5, 6, 7):
            with self.subTest(snapshot_version=version):
                snapshot = copy.deepcopy(original)
                if version == 4:
                    self._convert_to_v4_liquidity_keys(snapshot)
                    for panel in snapshot["data"]["monthly_panels"]:
                        panel.pop("confirmed_month", None)
                        panel.pop("confirmed_cash_flow_id", None)
                    self._refresh_manifest(snapshot)
                elif version < 7:
                    snapshot["schema_version"] = version
                    for panel in snapshot["data"]["monthly_panels"]:
                        panel.pop("confirmed_month", None)
                        if version == 5:
                            panel.pop("confirmed_cash_flow_id", None)
                    self._refresh_manifest(snapshot)
                restore_snapshot(snapshot)
                init_db()
                close_current_month(
                    date(2026, 7, 1), target_month="2026-06", allow_unconfirmed_recurring=True
                )
                with patch("app.services.summary.app_today", return_value=date(2026, 7, 1)):
                    summary = current_summary_values()
                self.assertEqual(summary["cash_flow_balance"], 100_000)
                self.assertEqual(summary["remaining_liquidity"], 95_000)
                _, current = export_snapshot(date(2026, 7, 1))
                restore_snapshot(current)
                init_db()
                with patch("app.services.summary.app_today", return_value=date(2026, 7, 1)):
                    self.assertEqual(current_summary_values()["remaining_liquidity"], 95_000)

    def test_ambiguous_v6_confirmation_is_rejected_before_restore(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_confirmed_fixed.json"
        original = json.loads(fixture.read_text(encoding="utf-8"))
        with session() as conn:
            conn.execute(
                "INSERT INTO cash_flows(id, occurred_on, title, amount_value, sort_order) "
                "VALUES (91, '2026-06-11', 'Existing state', -700, 1)"
            )
        for spent_on in ("unknown", "2026-02-30"):
            with self.subTest(spent_on=spent_on):
                invalid = copy.deepcopy(original)
                invalid["data"]["monthly_panels"][0]["spent_on"] = spent_on
                self._refresh_manifest(invalid)
                with self.assertRaisesRegex(ValueError, "valid spent_on"):
                    restore_snapshot(invalid)
                with session() as conn:
                    self.assertEqual(conn.execute("SELECT amount_value FROM cash_flows WHERE id = 91").fetchone()[0], -700)
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM monthly_panels").fetchone()[0], 0)

    def test_current_snapshot_does_not_reconstruct_missing_fixed_confirmation_month(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_confirmed_fixed.json"
        restore_snapshot(json.loads(fixture.read_text(encoding="utf-8")))
        _, current = export_snapshot(date(2026, 6, 15))
        self.assertEqual(current["schema_version"], 7)
        invalid = copy.deepcopy(current)
        invalid["data"]["monthly_panels"][0]["confirmed_month"] = None
        self._refresh_manifest(invalid)
        with self.assertRaisesRegex(ValueError, "inconsistent confirmed_month"):
            restore_snapshot(invalid)
        with session() as conn:
            self.assertEqual(conn.execute("SELECT confirmed_month FROM monthly_panels WHERE id = 31").fetchone()[0], "2026-06")

    def test_v5_snapshot_cannot_claim_a_v6_fixed_confirmation_link(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "snapshot_v6_confirmed_fixed.json"
        impossible = json.loads(fixture.read_text(encoding="utf-8"))
        impossible["schema_version"] = 5
        self._refresh_manifest(impossible)
        with self.assertRaisesRegex(ValueError, "cannot represent a fixed confirmation link"):
            restore_snapshot(impossible)
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM monthly_panels").fetchone()[0], 0)

    def test_restore_keeps_standard_summary_values(self) -> None:
        self._seed_data()
        before = current_summary_values()
        _, snapshot = export_snapshot(date(2026, 6, 11))

        restore_snapshot(snapshot)
        after = current_summary_values()

        for key in ("scheduled_income", "cash_flow_balance", "remaining_liquidity", "card_total"):
            self.assertEqual(after[key], before[key])

    def test_restore_discards_retired_setting_and_label_after_manifest_validation(self) -> None:
        self._seed_data()
        with session() as conn:
            conn.execute("INSERT INTO app_settings(key, value) VALUES ('interest_expense', '12345')")
            conn.execute(
                "INSERT INTO app_labels(key, value) VALUES ('summary_interest_expense_label', 'retired')"
            )
        _, snapshot = export_snapshot(date(2026, 6, 11))

        restore_snapshot(snapshot)

        with session() as conn:
            setting = conn.execute(
                "SELECT 1 FROM app_settings WHERE key = 'interest_expense'"
            ).fetchone()
            label = conn.execute(
                "SELECT 1 FROM app_labels WHERE key = 'summary_interest_expense_label'"
            ).fetchone()
        self.assertIsNone(setting)
        self.assertIsNone(label)

    def test_restore_normalizes_v4_liquidity_keys_after_manifest_validation(self) -> None:
        self._seed_data()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value = '550000' WHERE key = 'scheduled_income'")
            conn.execute(
                "UPDATE app_labels SET value = '내가 정한 잔액' WHERE key = 'summary_remaining_liquidity_label'"
            )
        _, snapshot = export_snapshot(date(2026, 6, 11))
        self._convert_to_v4_liquidity_keys(snapshot)

        restore_snapshot(snapshot)

        with session() as conn:
            settings = {
                row["key"]: row["value"]
                for row in conn.execute(
                    "SELECT key, value FROM app_settings WHERE key IN (?, ?, ?, ?)",
                    ("scheduled_income", "cash_flow_balance", "base_next_month_liquidity", "liquidity_status"),
                )
            }
            labels = {
                row["key"]: row["value"]
                for row in conn.execute(
                    "SELECT key, value FROM app_labels WHERE key LIKE 'summary_%_label'"
                )
            }
        self.assertEqual(settings["scheduled_income"], "550000")
        self.assertEqual(settings["cash_flow_balance"], "0")
        self.assertNotIn("base_next_month_liquidity", settings)
        self.assertNotIn("liquidity_status", settings)
        self.assertEqual(labels["summary_remaining_liquidity_label"], "내가 정한 잔액")
        self.assertNotIn("summary_next_month_liquidity_label", labels)

    def test_restore_verifies_v4_manifest_before_liquidity_key_normalization(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        self._convert_to_v4_liquidity_keys(snapshot)
        next(
            row
            for row in snapshot["data"]["app_settings"]
            if row["key"] == "base_next_month_liquidity"
        )["value"] = "999999"

        with self.assertRaisesRegex(ValueError, "snapshot manifest mismatch"):
            restore_snapshot(snapshot)

        self._assert_seed_data_preserved()

    def test_restore_rejects_conflicting_legacy_and_standard_liquidity_keys(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        snapshot["data"]["app_settings"].append(
            {
                "key": "base_next_month_liquidity",
                "value": "999999",
                "updated_at": "2026-06-11 00:00:00",
            }
        )
        self._refresh_manifest(snapshot)

        with self.assertRaisesRegex(ValueError, "conflicting values"):
            restore_snapshot(snapshot)

        self._assert_seed_data_preserved()

    def test_restore_deduplicates_equal_legacy_and_standard_liquidity_keys(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        current = next(
            row for row in snapshot["data"]["app_settings"] if row["key"] == "scheduled_income"
        )
        snapshot["data"]["app_settings"].append(
            {**current, "key": "base_next_month_liquidity"}
        )
        self._refresh_manifest(snapshot)

        restore_snapshot(snapshot)

        with session() as conn:
            keys = {
                row["key"]
                for row in conn.execute(
                    "SELECT key FROM app_settings WHERE key IN ('scheduled_income', 'base_next_month_liquidity')"
                )
            }
        self.assertEqual(keys, {"scheduled_income"})

    def test_restore_truncates_float_money_values_from_legacy_snapshot(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 1)["amount_value"] = 1000.9
        next(row for row in snapshot["data"]["ledger_entries"] if row["id"] == 1)["aux_amount_value"] = 12.8
        next(row for row in snapshot["data"]["monthly_panels"] if row["id"] == 1)["amount_value"] = 2000.7
        next(row for row in snapshot["data"]["monthly_panels"] if row["id"] == 1)["discount_amount"] = 24.9
        next(row for row in snapshot["data"]["cash_flows"] if row["id"] == 1)["amount_value"] = -500.6
        next(row for row in snapshot["data"]["card_payment_events"] if row["id"] == 1)["total_amount"] = 500.5
        next(row for row in snapshot["data"]["card_payment_allocations"] if row["id"] == 1)["amount_value"] = 500.4
        for setting in snapshot["data"]["app_settings"]:
            if setting["key"] == "scheduled_income":
                setting["value"] = "400000.9"
                break
        self._refresh_manifest(snapshot)

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
                "SELECT value FROM app_settings WHERE key = 'scheduled_income'",
            ).fetchone()
        self.assertEqual(ledger["amount_value"], 1000)
        self.assertEqual(ledger["aux_amount_value"], 12)
        self.assertEqual(panel["amount_value"], 2000)
        self.assertEqual(panel["discount_amount"], 24)
        self.assertEqual(cash_flow["amount_value"], -500)
        self.assertEqual(event["total_amount"], 500)
        self.assertEqual(allocation["amount_value"], 500)
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
        self._refresh_manifest(snapshot)

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
        self._refresh_manifest(snapshot)

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
        self._refresh_manifest(snapshot)
        snapshot["manifest"]["tables"]["app_labels"]["columns"] = ["key", "value"]

        restored = restore_snapshot(snapshot)

        self.assertEqual(restored["app_labels"], 0)

    def test_restore_accepts_legacy_snapshot_without_card_payment_batch_tables(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        del snapshot["data"]["card_payment_batches"]
        del snapshot["data"]["card_payment_batch_items"]
        for row in snapshot["data"]["card_payment_events"]:
            row.pop("batch_id", None)
        self._refresh_manifest(snapshot)

        restored = restore_snapshot(snapshot)

        self.assertEqual(restored["card_payment_batches"], 0)
        self.assertEqual(restored["card_payment_batch_items"], 0)
        self.assertEqual(restored["ledger_entries"], 3)

    def test_restore_replaces_ledger_data_and_preserves_auth_share_and_audit(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        snapshot["data"]["ledger_entries"][0]["title"] = "복원된 최근 지출"
        self._refresh_manifest(snapshot)

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
                WHERE key = 'scheduled_income'
                """
            )

        restored = restore_snapshot(snapshot)

        self.assertGreater(restored["ledger_entries"], 0)
        backup_dir = self.db_path.parent / "snapshot-backups"
        backups = list(backup_dir.glob("pre_restore-*.money-note-snapshot.json"))
        self.assertEqual(len(backups), 1)
        import json

        pre_restore = json.loads(backups[0].read_text(encoding="utf-8"))
        self.assertEqual(pre_restore["schema_version"], SNAPSHOT_SCHEMA_VERSION)
        self.assertIn("복원 전 임시 지출", str(pre_restore["data"]["ledger_entries"]))
        pre_restore_setting_keys = {row["key"] for row in pre_restore["data"]["app_settings"]}
        self.assertIn("scheduled_income", pre_restore_setting_keys)
        self.assertNotIn("base_next_month_liquidity", pre_restore_setting_keys)
        with session() as conn:
            titles = {row["title"] for row in conn.execute("SELECT title FROM ledger_entries").fetchall()}
            self.assertIn("복원된 최근 지출", titles)
            self.assertNotIn("복원 전 임시 지출", titles)
            user_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
            auth_count = conn.execute("SELECT COUNT(*) AS count FROM auth_sessions").fetchone()["count"]
            share_count = conn.execute("SELECT COUNT(*) AS count FROM share_sessions").fetchone()["count"]
            audit_count = conn.execute("SELECT COUNT(*) AS count FROM audit_logs").fetchone()["count"]
            pin_hash = conn.execute("SELECT value FROM app_settings WHERE key = 'share_pin_hash'").fetchone()["value"]
            base_income = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'scheduled_income'",
            ).fetchone()["value"]
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

    def test_restore_preserves_transit_profile_history(self) -> None:
        self._seed_data()
        with session() as conn:
            conn.executemany(
                """
                INSERT INTO app_settings(key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    ("card_charge_profile:transit:2026-08", "owner"),
                    ("card_charge_profile:transit:2027-01", "none"),
                ),
            )
        _, snapshot = export_snapshot(date(2027, 1, 1))

        with session() as conn:
            conn.execute(
                "DELETE FROM app_settings WHERE key LIKE 'card_charge_profile:transit:%'"
            )
        restore_snapshot(snapshot)

        with session() as conn:
            restored = {
                row["key"]: row["value"]
                for row in conn.execute(
                    """
                    SELECT key, value FROM app_settings
                    WHERE key LIKE 'card_charge_profile:transit:%'
                    ORDER BY key
                    """
                ).fetchall()
            }
        self.assertEqual(
            restored,
            {
                "card_charge_profile:transit:2026-08": "owner",
                "card_charge_profile:transit:2027-01": "none",
            },
        )

    def test_restore_rejects_policy_manifest_tampering_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        snapshot["card_charge_policy"]["cards"]["owner"][0]["parameters"]["rate"] = "0.999"

        with self.assertRaisesRegex(ValueError, "snapshot manifest mismatch"):
            restore_snapshot(snapshot)

        self._assert_seed_data_preserved()

    def test_restore_rejects_top_level_metadata_tampering(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        snapshot["exported_at"] = "2000-01-01T00:00:00Z"

        with self.assertRaisesRegex(ValueError, "snapshot manifest mismatch"):
            restore_snapshot(snapshot)

        self._assert_seed_data_preserved()

    def test_restore_rejects_valid_but_different_policy_manifest(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        snapshot["card_charge_policy"]["cards"]["owner"][0]["parameters"]["rate"] = "0.999"
        self._refresh_manifest(snapshot)

        with self.assertRaisesRegex(ValueError, "card charge policy does not match"):
            restore_snapshot(snapshot)

        self._assert_seed_data_preserved()

    def test_restore_accepts_policy_bindings_that_start_after_snapshot_month(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        future_binding = PolicyBinding(
            "2099-01",
            NoAutomaticDiscountPolicy("owner-no-automatic-discount-2099"),
        )

        with patch.dict(
            POLICY_TIMELINES,
            {DiscountCard.OWNER: POLICY_TIMELINES[DiscountCard.OWNER] + (future_binding,)},
        ):
            restored = restore_snapshot(snapshot)

        self.assertEqual(restored["ledger_entries"], 3)

    def test_restore_rejects_new_policy_binding_that_reinterprets_snapshot_month(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        retroactive_binding = PolicyBinding(
            "2000-01",
            NoAutomaticDiscountPolicy("owner-retroactive-no-discount"),
        )

        with patch.dict(
            POLICY_TIMELINES,
            {DiscountCard.OWNER: POLICY_TIMELINES[DiscountCard.OWNER] + (retroactive_binding,)},
        ):
            with self.assertRaisesRegex(ValueError, "card charge policy does not match"):
                restore_snapshot(snapshot)

        self._assert_seed_data_preserved()

    def test_restore_rejects_broken_foreign_key_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        broken["data"]["card_payment_allocations"][0]["payment_event_id"] = 99999
        self._refresh_manifest(broken)

        with self.assertRaises(ValueError):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def test_restore_rejects_duplicate_payment_key_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        next(row for row in broken["data"]["ledger_entries"] if row["id"] == 2)["payment_key"] = "recent-key"
        self._refresh_manifest(broken)

        with self.assertRaisesRegex(ValueError, "duplicate ledger payment_key"):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def test_restore_rejects_multiple_active_payment_batches_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        next(row for row in broken["data"]["card_payment_batches"] if row["id"] == 2)["status"] = "active"
        self._refresh_manifest(broken)

        with self.assertRaisesRegex(ValueError, "multiple active card payment batches"):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def test_restore_rejects_payment_allocation_mismatch_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        next(row for row in broken["data"]["card_payment_allocations"] if row["id"] == 1)["amount_value"] = 499
        self._refresh_manifest(broken)

        with self.assertRaisesRegex(ValueError, "event total does not match allocations"):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def test_restore_rejects_payment_cash_flow_mismatch_without_touching_db(self) -> None:
        self._seed_data()
        _, snapshot = export_snapshot(date(2026, 6, 11))
        broken = copy.deepcopy(snapshot)
        next(row for row in broken["data"]["cash_flows"] if row["id"] == 1)["amount_value"] = -499
        self._refresh_manifest(broken)

        with self.assertRaisesRegex(ValueError, "payment does not match linked cash flow"):
            restore_snapshot(broken)

        self._assert_seed_data_preserved()

    def _rebuilt_manifest(
        self,
        data: dict,
        policy_context: dict | None = None,
        snapshot_metadata: dict | None = None,
    ) -> dict:
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
        manifest = {
            "algorithm": "sha256",
            "tables": tables,
            "data_sha256": hashlib.sha256(
                json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            ).hexdigest(),
        }
        if policy_context is not None:
            manifest["card_charge_policy_sha256"] = hashlib.sha256(
                json.dumps(
                    policy_context,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8"),
            ).hexdigest()
            manifest["content_sha256"] = hashlib.sha256(
                json.dumps(
                    {
                        **(snapshot_metadata or {}),
                        "card_charge_policy": policy_context,
                        "data": data,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8"),
            ).hexdigest()
        return manifest

    def _refresh_manifest(self, snapshot: dict) -> None:
        snapshot["manifest"] = self._rebuilt_manifest(
            snapshot["data"],
            snapshot.get("card_charge_policy"),
            {
                "schema_version": snapshot.get("schema_version"),
                "exported_at": snapshot.get("exported_at"),
                "range": snapshot.get("range"),
            },
        )
        snapshot["snapshot_id"] = snapshot["manifest"].get(
            "content_sha256",
            snapshot["manifest"]["data_sha256"],
        )

    def _convert_to_v4_liquidity_keys(self, snapshot: dict) -> None:
        snapshot["schema_version"] = 4
        setting_keys = {
            "scheduled_income": "base_next_month_liquidity",
            "cash_flow_balance": "liquidity_status",
        }
        label_keys = {
            "summary_cash_flow_balance_label": "summary_liquidity_status_label",
            "summary_remaining_liquidity_label": "summary_next_month_liquidity_label",
        }
        for row in snapshot["data"]["app_settings"]:
            row["key"] = setting_keys.get(row["key"], row["key"])
        for row in snapshot["data"]["app_labels"]:
            row["key"] = label_keys.get(row["key"], row["key"])
        self._refresh_manifest(snapshot)

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
                    (1, '2026-06-06', '최근 현금', -500, 1),
                    (2, '2026-02-06', '오래된 현금', -700, 2)
                """
            )
            conn.execute(
                """
                INSERT INTO card_payment_batches(id, usage_month, source, status)
                VALUES
                    (1, '2026-05', 'month_close', 'active'),
                    (2, '2026-01', 'month_close', 'completed')
                """
            )
            conn.execute(
                """
                INSERT INTO card_payment_batch_items(id, batch_id, entry_id, entry_payment_key)
                VALUES
                    (1, 1, 1, 'recent-key'),
                    (2, 2, 2, 'old-key')
                """
            )
            conn.execute(
                """
                INSERT INTO card_payment_events(
                    id, batch_id, event_date, event_type, total_amount, note,
                    cash_flow_id, idempotency_key, request_fingerprint
                )
                VALUES
                    (1, 1, '2026-06-07', 'immediate', 500, '최근 결제', 1,
                     'snapshot-payment-recent', 'fingerprint-recent'),
                    (2, 2, '2026-02-07', 'immediate', 700, '오래된 결제', 2,
                     'snapshot-payment-old', 'fingerprint-old')
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

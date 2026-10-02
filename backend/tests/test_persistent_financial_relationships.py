import copy
import json
import os
import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.db_fixture import IsolatedDatabaseTestCase
from app.auth import require_user
from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import (
    append_planned_entry, confirm_planned_entry, delete_entry,
    list_confirmed_planned_entries, list_entries, update_entry,
)
from app.routers import entries
from app.schemas import CardPaymentAllocationIn, CardPaymentEventIn, LedgerEntryPatch, PlannedEntryIn
from app.services import snapshot
from app.services.card_payments import (
    _add_card_payment_batch_item,
    create_card_payment_event, create_month_close_card_payment_batch,
    current_payment_status, delete_card_payment_event, set_entry_discount,
)
from app.services.card_payment_reads import _active_payment_context, _payment_rows_for_batch
from app.services.month import close_current_month, month_close_status
from app.services.summary import current_summary_values


class PersistentFinancialRelationshipsTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.clock = patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-06-11"})
        self.clock.start()
        get_settings.cache_clear()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='100000' WHERE key='cash_flow_balance'")
            conn.execute("UPDATE app_settings SET value='0' WHERE key='scheduled_income'")

    def tearDown(self):
        self.clock.stop()
        super().tearDown()

    def durable(self):
        with sqlite3.connect(self.db_path) as conn:
            database = (conn.execute("PRAGMA user_version").fetchone()[0], tuple(conn.iterdump()))
        return database, {file.name: file.read_bytes() for file in
            (Path(self.temp_dir.name) / "snapshot-backups").glob("*") if file.is_file()}

    def resign(self, artifact):
        artifact["manifest"] = snapshot._build_manifest(artifact["data"],
            policy_context=artifact["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(artifact))
        artifact["snapshot_id"] = artifact["manifest"]["content_sha256"]
        return artifact

    def assert_invalid_restore(self, artifact):
        before = self.durable()
        with self.assertRaises(ValueError):
            snapshot.restore_snapshot(self.resign(artifact))
        self.assertEqual(self.durable(), before)
        init_db()
        self.assertEqual(self.durable(), before)

    def recurring(self):
        source = append_planned_entry(PlannedEntryIn(
            title="recurring", usage_place="shop", amount_value=5000, due_day=11,
        ))["id"]
        generated = confirm_planned_entry(source)["entry"]["id"]
        return source, generated

    def archived_active(self):
        source, child = self.recurring()
        with session() as conn:
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('last_closed_month','2026-04')")
        update_entry(child, LedgerEntryPatch(entry_date="2026-05-11"))
        close_current_month(date(2026, 6, 11), target_month="2026-05")
        with session() as conn:
            child = conn.execute("SELECT id FROM ledger_entries WHERE source_planned_entry_id=?", (source,)).fetchone()[0]
        return source, child

    def paid_card(self):
        with session() as conn:
            conn.execute("INSERT INTO ledger_entries(book_section,entry_kind,entry_date,title,amount_value,sort_order,payment_key) "
                "VALUES('archive','expense','2026-05-11','shop',10000,1,'card-key')")
            create_month_close_card_payment_batch(conn, "2026-05")
        event = create_card_payment_event(CardPaymentEventIn(
            idempotency_key="relationship-payment-1", event_date="2026-06-11", event_type="immediate",
            allocations=[CardPaymentAllocationIn(entry_payment_key="card-key", amount_value=1000)],
        ))
        return event

    def test_h1_exact_duplicate_membership_rejected_not_91120(self):
        self.paid_card()
        self.assertEqual(current_payment_status()["immediate_paid_total"], 1000)
        self.assertEqual(current_summary_values()["current_month_spendable"], 90120)
        bad = snapshot.export_snapshot()[1]
        bad["data"]["card_payment_batch_items"].append({**bad["data"]["card_payment_batch_items"][0],
            "id": 999, "entry_payment_key": "incompatible-alias"})
        self.assert_invalid_restore(bad)

    def test_h2_exact_archived_principal_null_patch_rejected_not_100000(self):
        source, child = self.archived_active()
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
        app = FastAPI()
        app.include_router(entries.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        before = self.durable()
        with TestClient(app, raise_server_exceptions=False) as client:
            result = client.patch(f"/api/entries/{child}", json={"amount_value": None})
        self.assertEqual(result.status_code, 422)
        self.assertEqual(self.durable(), before)
        self.assertEqual(list_confirmed_planned_entries()[0]["id"], source)
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)

    def test_m1_exact_old_current_active_archive_roundtrip_and_recovery(self):
        source, old = self.recurring()
        with session() as conn:
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('last_closed_month','2026-05')")
        update_entry(old, LedgerEntryPatch(entry_date="2026-09-11"))
        close_current_month(date(2026, 6, 30), allow_early_close=True, target_month="2026-06")
        os.environ["MONEY_NOTE_TODAY"] = "2026-08-11"
        get_settings.cache_clear()
        active = confirm_planned_entry(source)["entry"]["id"]
        update_entry(active, LedgerEntryPatch(entry_date="2026-07-11"))
        close_current_month(date(2026, 8, 11), target_month="2026-07", allow_unconfirmed_recurring=True)
        artifact = snapshot.export_snapshot()[1]
        owned = [row for row in artifact["data"]["ledger_entries"] if row["source_planned_entry_id"] == source]
        self.assertEqual({(row["book_section"], row["confirmed_month"]) for row in owned},
                         {("current", "2026-06"), ("archive", "2026-08")})
        before = current_summary_values()
        self.assertEqual(before["remaining_liquidity"], 90120)
        snapshot.restore_snapshot(artifact)
        init_db()
        self.assertEqual(current_summary_values(), before)
        for backup in (snapshot.create_pre_restore_backup, snapshot.create_pre_reconcile_server_backup):
            saved = json.loads(backup().read_text())
            snapshot.restore_snapshot(saved)
        self.assertEqual(current_summary_values(), before)
        active = list_confirmed_planned_entries()[0]["_confirmed_expense"]
        self.assertEqual(active["book_section"], "archive")
        self.assertTrue(delete_entry(active["id"]))
        self.assertEqual(current_summary_values()["remaining_liquidity"], 90060)
        confirm_planned_entry(source)
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])

    def test_card_relation_corruption_matrix(self):
        event = self.paid_card()
        valid = snapshot.export_snapshot()[1]
        for corruption in ("same_batch", "two_batches", "same_id", "missing_batch", "missing_entry",
                           "wrong_key", "missing_event", "wrong_event_batch", "duplicate_allocation",
                           "missing_allocation_entry", "shared_cash_flow"):
            with self.subTest(corruption=corruption):
                bad = copy.deepcopy(valid)
                item = bad["data"]["card_payment_batch_items"][0]
                allocation = bad["data"]["card_payment_allocations"][0]
                if corruption in ("same_batch", "two_batches", "same_id"):
                    duplicate = {**item, "id": 999}
                    if corruption == "two_batches":
                        bad["data"]["card_payment_batches"].append({**bad["data"]["card_payment_batches"][0],
                            "id": 999, "status": "completed"})
                        duplicate["batch_id"] = 999
                    elif corruption == "same_id":
                        duplicate["id"] = item["id"]
                    bad["data"]["card_payment_batch_items"].append(duplicate)
                elif corruption == "missing_batch":
                    item["batch_id"] = 999
                elif corruption == "missing_entry":
                    item["entry_id"] = 999
                elif corruption == "wrong_key":
                    item["entry_payment_key"] = "different-key"
                elif corruption == "missing_event":
                    bad["data"]["card_payment_events"] = []
                elif corruption == "wrong_event_batch":
                    bad["data"]["card_payment_batches"].append({**bad["data"]["card_payment_batches"][0],
                        "id": 999, "status": "completed"})
                    bad["data"]["card_payment_events"][0]["batch_id"] = 999
                elif corruption == "duplicate_allocation":
                    allocation["amount_value"] = 500
                    bad["data"]["card_payment_allocations"].append({**allocation, "id": 999})
                elif corruption == "missing_allocation_entry":
                    allocation["entry_payment_key"] = "missing"
                else:
                    bad["data"]["card_payment_events"].append({**event, "id": 999,
                        "idempotency_key": "second-payment", "request_fingerprint": "second"})
                    bad["data"]["card_payment_allocations"].append({**allocation, "id": 999, "payment_event_id": 999})
                self.assert_invalid_restore(bad)

    def test_recurring_snapshot_missing_principal_rejected(self):
        _, child = self.archived_active()
        valid = snapshot.export_snapshot()[1]
        for corruption in ("null", "missing", "negative"):
            with self.subTest(corruption=corruption):
                bad = copy.deepcopy(valid)
                expense = next(row for row in bad["data"]["ledger_entries"] if row["id"] == child)
                if corruption == "missing":
                    expense.pop("amount_value")
                else:
                    expense["amount_value"] = None if corruption == "null" else -1
                self.assert_invalid_restore(bad)

    def test_runtime_bad_card_cannot_read_export_cancel_or_rollover(self):
        event = self.paid_card()
        context = _active_payment_context(date(2026, 6, 11))
        with session() as conn:
            item = conn.execute("SELECT * FROM card_payment_batch_items").fetchone()
            conn.execute("INSERT INTO card_payment_batch_items(batch_id,entry_id,entry_payment_key) VALUES(?,?,'alias')",
                         (item["batch_id"], item["entry_id"]))
        for operation in (current_summary_values, current_payment_status, snapshot.export_snapshot,
                          lambda: _payment_rows_for_batch(context),
                          lambda: delete_card_payment_event(event["id"]),
                          lambda: close_current_month(date(2026, 6, 30), allow_early_close=True,
                                                     allow_unconfirmed_recurring=True)):
            with self.subTest(operation=operation):
                before = self.durable()
                with self.assertRaises(ValueError):
                    operation()
                self.assertEqual(self.durable(), before)

    def test_runtime_bad_recurring_cannot_disappear_in_summary_or_export(self):
        _, child = self.archived_active()
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET amount_value=NULL WHERE id=?", (child,))
        for operation in (current_summary_values, snapshot.export_snapshot, list_confirmed_planned_entries,
                          lambda: list_entries("archive"), lambda: update_entry(child, LedgerEntryPatch())):
            with self.subTest(operation=operation):
                before = self.durable()
                with self.assertRaises(ValueError):
                    operation()
                self.assertEqual(self.durable(), before)

    def test_month_close_confirmed_warning_uses_owned_epoch_not_mutable_date(self):
        source, child = self.archived_active()
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET created_at='2026-06-01 00:00:00' WHERE id=?", (source,))
        status = month_close_status(date(2026, 6, 30))
        self.assertEqual(status["unconfirmed_recurring_items"], [])
        result = close_current_month(date(2026, 6, 30), allow_early_close=True, target_month="2026-06")
        self.assertEqual(result["closed_month"], "2026-06")
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)

    def test_orphan_payment_destination_cannot_be_backed_up_or_replaced(self):
        self.paid_card()
        valid = snapshot.export_snapshot()[1]
        with session() as conn:
            conn.execute("DELETE FROM ledger_entries")
        before = self.durable()
        for operation in (snapshot.export_snapshot, snapshot.create_pre_restore_backup,
                          lambda: snapshot.restore_snapshot(valid)):
            with self.subTest(operation=operation):
                with self.assertRaises(ValueError):
                    operation()
                self.assertEqual(self.durable(), before)

    def test_card_valid_retry_partial_payments_cancellation_and_membership(self):
        event = self.paid_card()
        payload = CardPaymentEventIn(idempotency_key="relationship-payment-1", event_date="2026-06-11",
            event_type="immediate", allocations=[CardPaymentAllocationIn(entry_payment_key="card-key", amount_value=1000)])
        self.assertEqual(create_card_payment_event(payload)["id"], event["id"])
        payload.idempotency_key = "relationship-payment-2"
        second = create_card_payment_event(payload)
        self.assertEqual(current_payment_status()["immediate_paid_total"], 2000)
        self.assertEqual(current_summary_values()["remaining_liquidity"], 90120)
        with session() as conn:
            item = conn.execute("SELECT * FROM card_payment_batch_items").fetchone()
            _add_card_payment_batch_item(conn, item["batch_id"], item["entry_id"], item["entry_payment_key"])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_payment_batch_items").fetchone()[0], 1)
            with self.assertRaises(ValueError):
                _add_card_payment_batch_item(conn, item["batch_id"], item["entry_id"], "alias")
        for _ in range(2):
            snapshot.restore_snapshot(snapshot.export_snapshot()[1])
            init_db()
            self.assertEqual(current_payment_status()["immediate_paid_total"], 2000)
            self.assertEqual(current_summary_values()["current_month_spendable"], 90120)
        self.assertTrue(delete_card_payment_event(second["id"]))
        self.assertEqual(current_payment_status()["immediate_paid_total"], 1000)
        self.assertTrue(delete_card_payment_event(event["id"]))
        self.assertEqual(current_payment_status()["immediate_paid_total"], 0)
        self.assertEqual(current_summary_values()["remaining_liquidity"], 90120)

    def test_recurring_principal_patch_matrix_and_optional_discount(self):
        _, child = self.archived_active()
        app = FastAPI()
        app.include_router(entries.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        with TestClient(app, raise_server_exceptions=False) as client:
            for amount in (None, -1, "not-money", "NaN", 0.5, True):
                with self.subTest(amount=amount):
                    before = self.durable()
                    self.assertEqual(client.patch(f"/api/entries/{child}", json={"amount_value": amount}).status_code, 422)
                    self.assertEqual(self.durable(), before)
            self.assertEqual(client.patch(f"/api/entries/{child}", json={"title": "edited", "aux_amount_value": None}).status_code, 200)
            self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
            self.assertEqual(client.patch(f"/api/entries/{child}", json={"amount_value": 0}).status_code, 200)
            self.assertEqual(current_summary_values()["remaining_liquidity"], 100000)
            self.assertEqual(client.patch(f"/api/entries/{child}", json={"amount_value": 5000}).status_code, 200)
        with session() as conn:
            key = conn.execute("SELECT payment_key FROM ledger_entries WHERE id=?", (child,)).fetchone()[0]
        for discount in (0, 120, 500):
            with self.subTest(discount=discount):
                set_entry_discount(key, discount)
                self.assertEqual(current_summary_values()["remaining_liquidity"], 95000 + discount)
                snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                init_db()
                self.assertEqual(current_summary_values()["remaining_liquidity"], 95000 + discount)

    def test_archive_duplicate_epoch_and_logical_identity_rejected(self):
        _, child = self.archived_active()
        valid = snapshot.export_snapshot()[1]
        for corruption in ("duplicate_epoch", "duplicate_key", "rebound_closed_epoch"):
            with self.subTest(corruption=corruption):
                bad = copy.deepcopy(valid)
                expense = next(row for row in bad["data"]["ledger_entries"] if row["id"] == child)
                duplicate = {**expense, "id": 999, "book_section": "current", "payment_key": "other-key"}
                if corruption == "duplicate_key":
                    duplicate["payment_key"] = expense["payment_key"]
                    duplicate["confirmed_month"] = "2026-04"
                elif corruption == "rebound_closed_epoch":
                    duplicate["confirmed_month"] = "2026-07"
                bad["data"]["ledger_entries"].append(duplicate)
                self.assert_invalid_restore(bad)

    def test_validation_failures_rollback_patch_payment_restore_and_recovery(self):
        source, child = self.archived_active()
        valid = snapshot.export_snapshot()[1]
        from app.repositories import entries as entry_repository
        original = entry_repository._require_recurring_ownership

        def fail_after_update(conn, source_id):
            original(conn, source_id)
            if conn.execute("SELECT amount_value FROM ledger_entries WHERE id=?", (child,)).fetchone()[0] == 6000:
                raise RuntimeError("injected after principal update")

        before = self.durable()
        with patch.object(entry_repository, "_require_recurring_ownership", side_effect=fail_after_update):
            with self.assertRaises(RuntimeError):
                update_entry(child, LedgerEntryPatch(amount_value=6000))
        self.assertEqual(self.durable(), before)
        for boundary in ("_validate_financial_relationships", "_validate_snapshot_recurring_ownership"):
            with self.subTest(boundary=boundary):
                with patch.object(snapshot, boundary, side_effect=RuntimeError("validation failure")):
                    for operation in (snapshot.export_snapshot, snapshot.create_pre_restore_backup,
                                      lambda: snapshot.restore_snapshot(valid)):
                        with self.assertRaises(RuntimeError):
                            operation()
                        self.assertEqual(self.durable(), before)
        self.assertEqual(list_confirmed_planned_entries()[0]["id"], source)

    def test_month_close_mandatory_recovery_failure_does_not_change_finances(self):
        source, _ = self.recurring()
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET created_at='2026-06-01 00:00:00' WHERE id=?", (source,))
        before = self.durable()
        with patch("app.services.month.create_pre_restore_backup", side_effect=OSError("recovery unavailable")):
            with self.assertRaises(OSError):
                close_current_month(date(2026, 6, 30), allow_early_close=True, target_month="2026-06")
        self.assertEqual(self.durable(), before)

    def test_same_root_cause_batch_owned_principal_null_cannot_commit(self):
        self.paid_card()
        with session() as conn:
            child = conn.execute("SELECT entry_id FROM card_payment_batch_items").fetchone()[0]
        app = FastAPI()
        app.include_router(entries.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        before = self.durable()
        with TestClient(app, raise_server_exceptions=False) as client:
            self.assertEqual(client.patch(f"/api/entries/{child}", json={"amount_value": None}).status_code, 422)
        self.assertEqual(self.durable(), before)
        self.assertEqual(current_summary_values()["current_month_spendable"], 90120)

    def test_same_root_cause_batch_owned_principal_snapshot_and_runtime(self):
        self.paid_card()
        valid = snapshot.export_snapshot()[1]
        child = valid["data"]["card_payment_batch_items"][0]["entry_id"]
        bad = copy.deepcopy(valid)
        next(row for row in bad["data"]["ledger_entries"] if row["id"] == child)["amount_value"] = None
        self.assert_invalid_restore(bad)
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET amount_value=NULL WHERE id=?", (child,))
        before = self.durable()
        for operation in (current_summary_values, current_payment_status, snapshot.export_snapshot,
                          lambda: update_entry(child, LedgerEntryPatch(title="edit")),
                          lambda: update_entry(child, LedgerEntryPatch()), lambda: list_entries("archive")):
            with self.subTest(operation=operation):
                with self.assertRaises(ValueError):
                    operation()
                self.assertEqual(self.durable(), before)

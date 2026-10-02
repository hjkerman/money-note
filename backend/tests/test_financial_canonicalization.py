"""Lossless Snapshot money and stable actual recurring projection regressions."""

import copy
import json
import os
import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import require_user
from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import (
    append_planned_entry, confirm_planned_entry, delete_entry,
    list_confirmed_planned_entries, update_entry,
)
from app.routers import admin, entries, month, operations, offline_reconciliation
from app.routers.money_input import validate_financial_json_money
from app.schemas import CardPaymentAllocationIn, CardPaymentEventIn, LedgerEntryPatch, PlannedEntryIn, integer_money
from app.services import snapshot
from app.services.card_payments import create_card_payment_event, create_month_close_card_payment_batch
from app.services.month import close_current_month
from app.services.presentation import present_ledger_entries
from app.services.summary import current_summary_values
from tests.db_fixture import IsolatedDatabaseTestCase


class FinancialCanonicalizationTest(IsolatedDatabaseTestCase):
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
        return database, {path.name: path.read_bytes() for path in
            (Path(self.temp_dir.name) / "snapshot-backups").glob("*") if path.is_file()}

    def resign(self, artifact):
        artifact["manifest"] = snapshot._build_manifest(artifact["data"],
            table_names=list(artifact["data"]), empty_table_columns={
                table: meta["columns"] for table, meta in artifact["manifest"]["tables"].items()},
            policy_context=artifact["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(artifact))
        artifact["snapshot_id"] = artifact["manifest"]["content_sha256"]
        return artifact

    def recurring(self, archived=False):
        source = append_planned_entry(PlannedEntryIn(
            title="recurring", usage_place="shop", amount_value=5000, due_day=11,
        ))["id"]
        child = confirm_planned_entry(source)["entry"]["id"]
        if archived:
            with session() as conn:
                conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('last_closed_month','2026-04')")
            update_entry(child, LedgerEntryPatch(entry_date="2026-05-11"))
            close_current_month(date(2026, 6, 11), target_month="2026-05")
            with session() as conn:
                child = conn.execute("SELECT id FROM ledger_entries WHERE source_planned_entry_id=?", (source,)).fetchone()[0]
        return source, child

    def invalid_restore(self, artifact):
        before = self.durable()
        with self.assertRaises(ValueError):
            snapshot.restore_snapshot(self.resign(artifact))
        self.assertEqual(self.durable(), before)
        init_db()
        self.assertEqual(self.durable(), before)

    def test_h1_exact_negative_fraction_rejected_before_normalization(self):
        _, child = self.recurring()
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
        bad = snapshot.export_snapshot()[1]
        next(row for row in bad["data"]["ledger_entries"] if row["id"] == child)["amount_value"] = -0.5
        self.invalid_restore(bad)
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)

    def test_m1_exact_archived_null_date_projects_actual_after_restart_roundtrip(self):
        _, child = self.recurring(archived=True)
        update_entry(child, LedgerEntryPatch(amount_value=7000, entry_date=None))
        init_db()
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        init_db()
        app = FastAPI()
        app.include_router(month.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        with TestClient(app) as client:
            response = client.get("/api/month/current/planned/confirmed")
        self.assertEqual(response.status_code, 200)
        actual = response.json()[0]
        fixture = json.loads((Path(__file__).parent / "fixtures" / "confirmed_recurring_actual.json").read_text())
        self.assertEqual({key: actual[key] for key in fixture}, fixture)
        self.assertEqual(actual["amount_value"], 5000)
        self.assertEqual(actual["confirmed_amount_value"], 7000)
        self.assertEqual(actual["confirmed_effective_discount_amount"], 84)
        self.assertEqual(actual["confirmed_effective_amount_value"], 6916)

    def test_current_money_fraction_matrix(self):
        _, child = self.recurring()
        valid = snapshot.export_snapshot()[1]
        for column in ("amount_value", "aux_amount_value"):
            for value in (-0.5, 5000.5, "5000.5", "garbage", True, 2**63, -(2**63)-1):
                with self.subTest(column=column, value=value):
                    bad = copy.deepcopy(valid)
                    next(row for row in bad["data"]["ledger_entries"] if row["id"] == child)[column] = value
                    self.invalid_restore(bad)

    def test_current_export_rejects_fractional_financial_siblings(self):
        with session() as conn:
            conn.execute("INSERT INTO cash_flows(occurred_on,title,amount_value,sort_order) VALUES('2026-06-11','cash',500,1)")
        before = self.durable()
        with session() as conn:
            conn.execute("UPDATE cash_flows SET amount_value=-0.5")
        malformed = self.durable()
        with self.assertRaises(ValueError):
            snapshot.export_snapshot()
        self.assertEqual(self.durable(), malformed)
        self.assertNotEqual(malformed, before)

    def test_integer_valued_real_normalization_preserves_exact_value(self):
        # Integer-valued REAL remains compatible inside the explicit product
        # range; previously accepted int64-only values are now fail-closed.
        with self.assertRaises(ValueError):
            snapshot._normalize_snapshot_money(float(9223372036854774784), "cash")
        value = float(2**53 - 1)
        self.assertEqual(snapshot._normalize_snapshot_money(value, "cash"), int(value))
        artifact = snapshot.export_snapshot()[1]
        artifact["data"]["cash_flows"] = [{"id": 1, "occurred_on": "2026-06-11", "title": "real",
                                          "amount_value": value, "sort_order": 1}]
        snapshot.restore_snapshot(self.resign(artifact))
        with session() as conn:
            self.assertEqual(conn.execute("SELECT amount_value FROM cash_flows WHERE id=1").fetchone()[0], int(value))

    def test_api_integer_valued_real_preserves_principal_before_commit(self):
        with self.assertRaises(ValueError):
            integer_money(float(9223372036854774784))
        value = float(2**53 - 1)
        self.assertEqual(integer_money(value), int(value))
        app = FastAPI()
        app.include_router(operations.cash_router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        with TestClient(app) as client:
            result = client.post("/api/cash-flows", json={
                "occurred_on": "2026-06-11", "title": "exact REAL", "amount_value": int(value), "sort_order": 1,
            })
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["amount_value"], int(value))
        with session() as conn:
            self.assertEqual(conn.execute("SELECT amount_value FROM cash_flows WHERE id=?", (result.json()["id"],)).fetchone()[0], int(value))
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])

    def test_financial_http_raw_fraction_or_lossy_integer_rejected_before_commit(self):
        app = FastAPI()
        app.include_router(operations.cash_router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        with TestClient(app, raise_server_exceptions=False) as client:
            for literal in ("-1e-400", "5000.00000000000001", "9.223372036854775e18"):
                with self.subTest(literal=literal):
                    before = self.durable()
                    body = '{"occurred_on":"2026-06-11","sort_order":1,"amount_value":' + literal + '}'
                    result = client.post("/api/cash-flows", content=body, headers={"Content-Type": "application/json"})
                    self.assertEqual(result.status_code, 422)
                    self.assertEqual(self.durable(), before)

    def test_null_financial_setting_rejected_not_stringified(self):
        artifact = snapshot.export_snapshot()[1]
        next(row for row in artifact["data"]["app_settings"] if row["key"] == "scheduled_income")["value"] = None
        self.invalid_restore(artifact)

    def test_setting_input_validated_before_float_rounding(self):
        app = FastAPI()
        app.include_router(operations.settings_router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        with TestClient(app) as client:
            for value in ("5000.00000000000001", "-1e-400", "9223372036854775808", "9007199254740993"):
                with self.subTest(value=value):
                    before = self.durable()
                    result = client.patch("/api/settings/scheduled_income", json={"value": value})
                    self.assertEqual(result.status_code, 422)
                    self.assertEqual(self.durable(), before)
            result = client.patch("/api/settings/scheduled_income", json={"value": "9007199254740991"})
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json(), {"scheduled_income": "9007199254740991"})
            snapshot.restore_snapshot(snapshot.export_snapshot()[1])

    def test_api_sqlite_money_range_rejected_before_mutation(self):
        app = FastAPI()
        app.include_router(operations.cash_router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        with TestClient(app, raise_server_exceptions=False) as client:
            for value in (2**63, -(2**63)-1):
                with self.subTest(value=value):
                    before = self.durable()
                    result = client.post("/api/cash-flows", json={"occurred_on": "2026-06-11",
                        "amount_value": value, "sort_order": 1})
                    self.assertEqual(result.status_code, 422)
                    self.assertEqual(self.durable(), before)

    def test_snapshot_json_fraction_must_not_round_to_integer_before_validation(self):
        _, child = self.recurring()
        app = FastAPI()
        app.include_router(admin.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        for literal, decoded in (("-1e-400", -0.0), ("5000.00000000000001", 5000.0)):
            for representation in ("text", "object", "recovery-file"):
                with self.subTest(literal=literal, representation=representation):
                    artifact = snapshot.export_snapshot()[1]
                    next(row for row in artifact["data"]["ledger_entries"] if row["id"] == child)["amount_value"] = decoded
                    text = json.dumps(self.resign(artifact)).replace(f'"amount_value": {decoded}', f'"amount_value": {literal}')
                    before = self.durable()
                    if representation == "recovery-file":
                        path = Path(self.temp_dir.name) / "synthetic.money-note-snapshot.json"
                        path.write_text(text)
                        with self.assertRaises(ValueError):
                            snapshot._read_snapshot_file(path)
                    else:
                        with patch.object(admin, "verify_user_password", return_value=True), TestClient(app) as client:
                            body = json.dumps({"password": "synthetic", "snapshot_text": text}) if representation == "text" else (
                                '{"password":"synthetic","snapshot":' + text + '}')
                            response = client.post("/api/admin/snapshot/restore", content=body, headers={"Content-Type": "application/json"})
                        self.assertEqual(response.status_code, 400)
                    self.assertEqual(self.durable(), before)

    def test_raw_numeric_command_and_journal_field_matrix(self):
        fields = ("amount_value", "aux_amount_value", "actual_amount", "discount_amount", "discount_override_amount")
        for field in fields:
            for literal in ("-1e-400", "5000.00000000000001", "9.223372036854775e18", "NaN", "Infinity", "9223372036854775807", "-9223372036854775808"):
                for container in ("command", "allocation", "journal"):
                    with self.subTest(field=field, literal=literal, container=container):
                        row = '{"' + field + '":' + literal + '}'
                        body = row if container == "command" else '{"allocations":[' + row + ']}' if container == "allocation" else (
                            '{"operations":[{"payload":' + row + '}]}')
                        with self.assertRaises(ValueError):
                            validate_financial_json_money(body)
        for literal in ("0", "-500", "5000.0", "9007199254740991", "-9007199254740991", '"5000.0"'):
            with self.subTest(valid=literal):
                validate_financial_json_money('{"amount_value":' + literal + '}')

    def test_raw_mobile_wins_baseline_rejected_before_apply(self):
        _, child = self.recurring()
        artifact = snapshot.export_snapshot()[1]
        next(row for row in artifact["data"]["ledger_entries"] if row["id"] == child)["amount_value"] = -0.0
        self.resign(artifact)
        body = json.dumps({"schema_version": 1, "reconciliation_id": "canonical-raw-baseline",
            "baseline_fingerprint": "0" * 64, "baseline_snapshot": artifact,
            "operations": [], "mobile_artifact_sha256": "0" * 64,
            "expected_server_fingerprint": "0" * 64, "password": "synthetic"}).replace('"amount_value": -0.0', '"amount_value": -1e-400')
        app = FastAPI()
        app.include_router(offline_reconciliation.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        before = self.durable()
        with patch.object(offline_reconciliation, "verify_user_password", return_value=True), \
             patch.object(offline_reconciliation, "apply_mobile_wins") as apply, TestClient(app) as client:
            response = client.post("/api/offline-reconciliation/mobile-wins", content=body,
                headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 400)
        apply.assert_not_called()
        self.assertEqual(self.durable(), before)

    def test_real_affinity_export_json_is_lossless_without_ordinary_fingerprint_drift(self):
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("CREATE TABLE money(amount_value REAL)")
            for value in (5000.0, float(2**53 - 1), float(9223372036854774784)):
                with self.subTest(value=value):
                    conn.execute("DELETE FROM money")
                    conn.execute("INSERT INTO money VALUES(?)", (value,))
                    data = {"cash_flows": [dict(conn.execute("SELECT * FROM money").fetchone())]}
                    raw = copy.deepcopy(data)
                    if value > 2**53-1:
                        with self.assertRaises(ValueError):
                            snapshot._validate_snapshot_money(data)
                        self.assertEqual(data, raw)
                        continue
                    snapshot._validate_snapshot_money(data)
                    self.assertIsInstance(data["cash_flows"][0]["amount_value"], float)
                    self.assertEqual(snapshot._stable_hash(data), snapshot._stable_hash(raw))
                    snapshot.parse_snapshot_json(json.dumps({"schema_version": 7, "data": data}))

    def money_fixture(self):
        self.recurring()
        with session() as conn:
            conn.execute("INSERT INTO monthly_panels(month,panel_type,title,amount_value,discount_amount,sort_order) "
                         "VALUES('2026-06','claim','panel',1000,12,1)")
            conn.execute("INSERT INTO ledger_entries(book_section,entry_kind,entry_date,title,amount_value,sort_order,payment_key) "
                         "VALUES('archive','expense','2026-05-11','card',10000,1,'canonical-card')")
            create_month_close_card_payment_batch(conn, "2026-05")
        create_card_payment_event(CardPaymentEventIn(event_type="immediate", event_date="2026-06-11",
            idempotency_key="canonical-payment", allocations=[
                CardPaymentAllocationIn(entry_payment_key="canonical-card", amount_value=1000)]))
        return snapshot.export_snapshot()[1]

    def test_all_current_financial_numeric_columns_reject_before_dry_run(self):
        valid = self.money_fixture()
        for table, columns in snapshot.SNAPSHOT_MONEY_COLUMNS.items():
            for column in columns:
                for value in (-0.5, 5000.5, "invalid", True, float("nan"), float("inf"), 2**63, -(2**63)-1):
                    with self.subTest(table=table, column=column, value=value):
                        bad = copy.deepcopy(valid)
                        bad["data"][table][0][column] = value
                        with patch.object(snapshot, "_dry_run_restore", side_effect=AssertionError("too late")):
                            self.invalid_restore(bad)
        for key in ("cash_flow_balance", "scheduled_income", "card_limit"):
            for value in ("-0.5", "5000.5", "", "nan", "inf", "9223372036854775808", None):
                with self.subTest(key=key, value=value):
                    bad = copy.deepcopy(valid)
                    next(row for row in bad["data"]["app_settings"] if row["key"] == key)["value"] = value
                    self.invalid_restore(bad)

    def test_export_numeric_column_matrix_and_recovery_fail_closed(self):
        self.money_fixture()
        for table, columns in snapshot.SNAPSHOT_MONEY_COLUMNS.items():
            for column in columns:
                with self.subTest(table=table, column=column):
                    before = self.durable()
                    with session(transaction_mode="IMMEDIATE") as conn:
                        conn.execute("SAVEPOINT malformed")
                        conn.execute(f"UPDATE {table} SET {column}=0.5 WHERE id=(SELECT MIN(id) FROM {table})")
                        for exporter in (snapshot.export_snapshot_from_connection, snapshot.create_pre_restore_backup,
                                         snapshot.create_pre_reconcile_server_backup):
                            with self.assertRaises(ValueError):
                                exporter(conn)
                        conn.execute("ROLLBACK TO malformed")
                    self.assertEqual(self.durable(), before)
        for key in ("scheduled_income", "cash_flow_balance", "card_limit"):
            with self.subTest(key=key):
                with session(transaction_mode="IMMEDIATE") as conn:
                    conn.execute("SAVEPOINT malformed")
                    conn.execute("UPDATE app_settings SET value='0.5' WHERE key=?", (key,))
                    with self.assertRaises(ValueError):
                        snapshot.export_snapshot_from_connection(conn)
                    conn.execute("ROLLBACK TO malformed")

    def test_versioned_integer_real_and_legacy_fraction_contract(self):
        # v4-v6 REAL storage/truncation is retained; current v7 cannot enter it.
        for version in (4, 5, 6):
            legacy = json.loads((Path(__file__).parent / "fixtures" / f"snapshot_v{version}_recurring.json").read_text())
            for value in (5000, 5000.0, 5000.5):
                with self.subTest(version=version, value=value):
                    artifact = copy.deepcopy(legacy)
                    for row in artifact["data"]["ledger_entries"]:
                        row["amount_value"] = value
                    snapshot.restore_snapshot(self.resign(artifact))
                    init_db()
                    self.assertEqual(list_confirmed_planned_entries()[0]["_confirmed_expense"]["amount_value"], 5000)
                    snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        current = snapshot.export_snapshot()[1]
        for value in (5000, 5000.0, "5000", "5000.0"):
            with self.subTest(version=7, value=value):
                artifact = copy.deepcopy(current)
                for row in artifact["data"]["ledger_entries"]:
                    row["amount_value"] = value
                snapshot.restore_snapshot(self.resign(artifact))
                self.assertEqual(list_confirmed_planned_entries()[0]["_confirmed_expense"]["amount_value"], 5000)

    def test_restore_failure_boundaries_leave_destination_unchanged(self):
        self.recurring(archived=True)
        valid = snapshot.export_snapshot()[1]
        for boundary in ("_normalize_snapshot_row", "_validate_snapshot_recurring_ownership", "_insert_rows",
                         "_replace_snapshot_tables"):
            with self.subTest(boundary=boundary):
                before = self.durable()
                with patch.object(snapshot, boundary, side_effect=ValueError("injected")):
                    with self.assertRaises(ValueError):
                        snapshot.restore_snapshot(valid)
                self.assertEqual(self.durable(), before)
        # Force replacement failure only after successful dry-run and recovery
        # publication. The validated recovery artifact may remain, DB may not.
        before = self.durable()[0]
        original = snapshot._replace_snapshot_tables
        def fail_live(conn, data):
            if str(conn.execute("PRAGMA database_list").fetchone()[2]) == str(self.db_path):
                conn.execute("DELETE FROM ledger_entries")
                raise ValueError("live replacement failed")
            return original(conn, data)
        with patch.object(snapshot, "_replace_snapshot_tables", side_effect=fail_live):
            with self.assertRaises(ValueError):
                snapshot.restore_snapshot(valid)
        self.assertEqual(self.durable()[0], before)
        init_db()
        self.assertEqual(self.durable()[0], before)

    def test_current_null_date_patch_rejected_archive_null_date_preserved(self):
        _, child = self.recurring()
        app = FastAPI()
        app.include_router(entries.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        before = self.durable()
        with TestClient(app) as client:
            response = client.patch(f"/api/entries/{child}", json={"entry_date": None})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.durable(), before)

    def test_projection_mutable_fields_and_missing_child_fail_closed(self):
        _, child = self.recurring(archived=True)
        for change in ({"amount_value": 7000}, {"title": "edited"}, {"usage_place": None},
                       {"usage_item": None}, {"entry_date": "2026-05-20"},
                       {"entry_date": "2026-07-01"}, {"entry_date": None}):
            with self.subTest(change=change):
                update_entry(child, LedgerEntryPatch(**change))
                init_db()
                snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                projected = present_ledger_entries(list_confirmed_planned_entries())[0]
                self.assertEqual(projected["confirmed_amount_value"], 7000)
                self.assertEqual(projected["confirmed_effective_amount_value"], 6916)
        before = self.durable()
        with patch("app.repositories.entries.validate_recurring_ownership"):
            with session() as conn:
                conn.execute("DELETE FROM ledger_entries WHERE id=?", (child,))
            with self.assertRaisesRegex(ValueError, "recurring"):
                list_confirmed_planned_entries()
        self.assertNotEqual(self.durable(), before)

    def test_actual_projection_location_null_date_cancel_and_reconfirm(self):
        source, child = self.recurring(archived=True)
        update_entry(child, LedgerEntryPatch(amount_value=7000))
        for section in ("current", "archive", "current", "archive"):
            with self.subTest(section=section):
                with session() as conn:
                    conn.execute("UPDATE ledger_entries SET book_section=? WHERE id=?", (section, child))
                init_db()
                snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                self.assertEqual(present_ledger_entries(list_confirmed_planned_entries())[0]["confirmed_amount_value"], 7000)
        update_entry(child, LedgerEntryPatch(entry_date=None, title="changed", usage_place=None, usage_item=None))
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        self.assertEqual(present_ledger_entries(list_confirmed_planned_entries())[0]["confirmed_amount_value"], 7000)
        self.assertTrue(delete_entry(child))
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)
        confirm_planned_entry(source)
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)

    def test_actual_projection_failure_is_read_only(self):
        self.recurring(archived=True)
        before = self.durable()
        with patch("app.services.presentation.present_ledger_entry", side_effect=ValueError("injected")):
            with self.assertRaises(ValueError):
                present_ledger_entries(list_confirmed_planned_entries())
        self.assertEqual(self.durable(), before)

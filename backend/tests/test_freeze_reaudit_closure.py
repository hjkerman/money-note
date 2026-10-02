import copy
import json
import os
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from tests.db_fixture import IsolatedDatabaseTestCase
from app.auth import current_user_from_request, require_user
from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import append_planned_entry, confirm_planned_entry, create_entry, delete_entry, update_entry
from app.repositories.panels import create_panel
from app.routers import auth, entries, month, card_payments, operations
from app.schemas import CardDiscountPolicyPatch, LedgerEntryIn, LedgerEntryPatch, MonthlyPanelIn, PlannedEntryIn, TransitDiscountProfilePatch
from app.services import snapshot
from app.services.presentation import present_monthly_panel


def response_data(value):
    return json.loads(value.body) if isinstance(value, JSONResponse) else value


class FreezeReauditClosureTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.clock = patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-06-11"})
        self.clock.start()
        get_settings.cache_clear()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='100000' WHERE key='cash_flow_balance'")
            conn.execute("UPDATE app_settings SET value='0' WHERE key='scheduled_income'")
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('card_discount_policy:family:2026-06','enabled')")

    def tearDown(self):
        self.clock.stop()
        super().tearDown()

    def dump(self):
        with sqlite3.connect(self.db_path) as conn:
            return (conn.execute("PRAGMA user_version").fetchone()[0], tuple(conn.iterdump()))

    def recurring(self):
        source = append_planned_entry(PlannedEntryIn(title="subscription", usage_place="shop", amount_value=5000, due_day=11))
        expense = confirm_planned_entry(source["id"])["entry"]
        return source["id"], expense["id"]

    def client(self):
        app = FastAPI()
        app.include_router(entries.router)
        app.include_router(month.router)
        app.include_router(card_payments.discounts_router)
        app.include_router(operations.cash_router)
        app.include_router(operations.settings_router)
        app.include_router(card_payments.payments_router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        return TestClient(app, raise_server_exceptions=False)

    def test_auth_cli_actually_allows_two_distinct_principals(self):
        for username in ("synthetic-owner-a", "synthetic-owner-b"):
            subprocess.run([sys.executable, "scripts/create_user.py", username, "synthetic-password-123"],
                cwd=Path(__file__).resolve().parents[1], env={**os.environ, "PYTHONPATH": "."},
                capture_output=True, check=True)
        auth.login_limiter.reset()
        principals = []
        for username in ("synthetic-owner-a", "synthetic-owner-b"):
            from app.schemas import LoginIn
            request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 12345)})
            result = auth.mobile_login(LoginIn(username=username, password="synthetic-password-123"), request)
            authenticated = Request({"type": "http", "headers": [(b"authorization", f"Bearer {result['session_token']}".encode())]})
            principals.append(current_user_from_request(authenticated)["id"])
        self.assertNotEqual(*principals)

    def test_policy_status_failure_cannot_follow_durable_mutation(self):
        cases = [
            ("app.services.card_payments.discount_month_status", lambda: card_payments.patch_card_discount_month(
                "2026-06", CardDiscountPolicyPatch(policy="disabled"), "owner", {})),
            ("app.services.card_charge.profiles.transit_discount_profile_status", lambda: card_payments.patch_transit_discount_profile(
                "2026-06", TransitDiscountProfilePatch(profile="owner"), {})),
        ]
        for target, command in cases:
            with self.subTest(target=target):
                before = self.dump()
                with patch(target, side_effect=ValueError("required status failed")):
                    with self.assertRaises(HTTPException):
                        command()
                self.assertEqual(self.dump(), before)

    def test_fastapi_post_commit_serializer_is_bypassed_by_prebuilt_body(self):
        async def fail_serializer(**kwargs):
            raise ValueError("framework serializer after handler")
        with self.client() as client, patch("fastapi.routing.serialize_response", fail_serializer):
            response = client.post("/api/entries", json={"book_section": "current", "entry_date": "2026-06-11",
                "title": "shop", "usage_place": "shop", "amount_value": 10000, "sort_order": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["amount_value"], 10000)

    def test_final_body_preparation_failure_rolls_back_http_write(self):
        original = JSONResponse.render
        def fail_financial_body(response, content):
            if isinstance(content, dict) and "payment_key" in content:
                raise ValueError("final body failed")
            return original(response, content)
        before = self.dump()
        with self.client() as client, patch.object(JSONResponse, "render", fail_financial_body):
            response = client.post("/api/entries", json={"book_section": "current", "entry_date": "2026-06-11",
                "title": "shop", "usage_place": "shop", "amount_value": 10000, "sort_order": 1})
        self.assertGreaterEqual(response.status_code, 400)
        self.assertEqual(self.dump(), before)

    def test_snapshot_partial_source_epoch_is_rejected_without_change(self):
        source, _ = self.recurring()
        valid = snapshot.export_snapshot()[1]
        for field in ("confirmed_month", "confirmed_at"):
            with self.subTest(field=field):
                bad = copy.deepcopy(valid)
                next(row for row in bad["data"]["ledger_entries"] if row["id"] == source)[field] = None
                bad["manifest"] = snapshot._build_manifest(bad["data"], policy_context=bad["card_charge_policy"],
                    snapshot_metadata=snapshot._snapshot_metadata(bad))
                bad["snapshot_id"] = bad["manifest"]["content_sha256"]
                before = self.dump()
                with self.assertRaisesRegex(ValueError, "recurring confirmation"):
                    snapshot.restore_snapshot(bad)
                self.assertEqual(self.dump(), before)

    def test_runtime_partial_source_epoch_blocks_cancel_and_reconfirm(self):
        for field in ("confirmed_month", "confirmed_at"):
            for operation in ("cancel", "confirm"):
                with self.subTest(field=field, operation=operation):
                    source, expense = self.recurring()
                    with session() as conn:
                        conn.execute(f"UPDATE ledger_entries SET {field}=NULL WHERE id=?", (source,))
                    before = self.dump()
                    with self.assertRaises(ValueError):
                        delete_entry(expense) if operation == "cancel" else confirm_planned_entry(source)
                    self.assertEqual(self.dump(), before)

    def test_confirmed_projection_uses_epoch_not_mutable_date(self):
        _, expense = self.recurring()
        update_entry(expense, LedgerEntryPatch(entry_date=date(2026, 7, 1), amount_value=7000, title="changed"))
        row = month.get_confirmed_planned_entries({})[0]
        self.assertEqual(row["confirmed_amount_value"], 7000)
        self.assertEqual(row["entry_date"], "2026-07-01")

    def test_boolean_only_false_is_authoritative_exclusion(self):
        for panel_type in ("claim", "family_card"):
            with self.subTest(panel_type=panel_type):
                panel = create_panel(MonthlyPanelIn(month="2026-06", panel_type=panel_type, title="ordinary",
                    amount_value=10000, discount_enabled=False, sort_order=1))
                self.assertEqual(present_monthly_panel(panel)["effective_amount_value"], 10000)
                self.assertEqual(panel["discount_override"], 1)

    def test_partial_source_epoch_cannot_be_bypassed_by_archived_generated_child(self):
        for field in ("confirmed_month", "confirmed_at"):
            with self.subTest(field=field):
                source, generated = self.recurring()
                with session() as conn:
                    conn.execute("UPDATE ledger_entries SET book_section='archive' WHERE id=?", (generated,))
                    conn.execute(f"UPDATE ledger_entries SET {field}=NULL WHERE id=?", (source,))
                before = self.dump()
                with self.assertRaisesRegex(ValueError, "recurring confirmation"):
                    delete_entry(generated)
                self.assertEqual(self.dump(), before)

    def test_unretired_generated_epoch_cannot_have_unconfirmed_source(self):
        source, _ = self.recurring()
        invalid = snapshot.export_snapshot()[1]
        next(row for row in invalid["data"]["ledger_entries"] if row["id"] == source).update(
            confirmed_month=None, confirmed_at=None)
        invalid["manifest"] = snapshot._build_manifest(invalid["data"], policy_context=invalid["card_charge_policy"],
            snapshot_metadata=snapshot._snapshot_metadata(invalid))
        invalid["snapshot_id"] = invalid["manifest"]["content_sha256"]
        before = self.dump()
        with self.assertRaisesRegex(ValueError, "recurring confirmation"):
            snapshot.restore_snapshot(invalid)
        self.assertEqual(self.dump(), before)

    def test_runtime_unretired_epoch_blocks_both_cancel_and_reconfirm(self):
        for operation in ("cancel", "confirm"):
            with self.subTest(operation=operation):
                source, generated = self.recurring()
                with session() as conn:
                    conn.execute("UPDATE ledger_entries SET confirmed_month=NULL, confirmed_at=NULL WHERE id=?", (source,))
                before = self.dump()
                with self.assertRaises(ValueError):
                    delete_entry(generated) if operation == "cancel" else confirm_planned_entry(source)
                self.assertEqual(self.dump(), before)

    def test_profile_status_observes_uncommitted_new_policy_and_rollback_preserves_burden(self):
        from app.services.card_payments import set_discount_month_policy
        from app.services.summary import current_summary_values
        create_entry(LedgerEntryIn(book_section="current", entry_date="2026-06-11", title="ordinary",
            usage_place="shop", amount_value=10000, sort_order=1))
        set_discount_month_policy("2026-06", "disabled")
        self.assertEqual(current_summary_values()["card_total"], 10000)
        before = self.dump()
        with patch("app.services.card_payments.discount_month_status", side_effect=ValueError("status failed")):
            with self.assertRaises(HTTPException):
                card_payments.patch_card_discount_month("2026-06", CardDiscountPolicyPatch(policy="enabled"), "owner", {})
        self.assertEqual(self.dump(), before)
        self.assertEqual(current_summary_values()["card_total"], 10000)
        with session(transaction_mode="IMMEDIATE") as conn:
            result = set_discount_month_policy("2026-06", "enabled", conn=conn)
            self.assertEqual(result["policy"], "enabled")
            self.assertEqual(result["discount_total"], 120)
        self.assertEqual(current_summary_values()["card_total"], 9880)

    def test_final_body_preparation_rolls_back_all_financial_response_siblings(self):
        fixed = create_panel(MonthlyPanelIn(month="2026-06", panel_type="fixed", title="fixed", amount_value=5000, sort_order=1))
        planned = append_planned_entry(PlannedEntryIn(title="recurring", usage_place="shop", amount_value=5000, due_day=11))
        original = JSONResponse.render
        def fail_body(response, content):
            if isinstance(content, dict) and "detail" not in content:
                raise ValueError("required body cannot be encoded")
            return original(response, content)
        cases = [
            ("post", "/api/cash-flows", {"occurred_on": "2026-06-11", "title": "cash", "amount_value": -500, "sort_order": 1}),
            ("post", "/api/month/current/panels", {"month": "2026-06", "panel_type": "claim", "title": "claim", "amount_value": 10000, "sort_order": 1}),
            ("post", f"/api/month/current/planned/{planned['id']}/confirm", {}),
            ("post", f"/api/month/current/panels/{fixed['id']}/confirm-fixed", {"occurred_on": "2026-06-11"}),
            ("patch", "/api/card-discounts/months/2026-06", {"policy": "disabled"}),
            ("patch", "/api/card-discounts/profiles/transit/2026-06", {"profile": "owner"}),
            ("patch", "/api/settings/scheduled_income", {"value": "123456"}),
        ]
        with self.client() as client:
            for method, path, payload in cases:
                with self.subTest(path=path):
                    before = self.dump()
                    with patch.object(JSONResponse, "render", fail_body):
                        result = client.request(method, path, json=payload)
                    self.assertGreaterEqual(result.status_code, 400)
                    self.assertEqual(self.dump(), before)

    def test_definite_delete_contract_is_unmutated_404_or_409(self):
        from app.services.card_payments import create_card_payment_event, create_month_close_card_payment_batch
        from app.schemas import CardPaymentAllocationIn, CardPaymentEventIn
        paid = create_entry(LedgerEntryIn(book_section="archive", entry_date="2026-05-11",
            title="card", usage_place="shop", amount_value=10000, sort_order=1, discount_enabled=False))
        with session() as conn:
            create_month_close_card_payment_batch(conn, "2026-05")
        event = create_card_payment_event(CardPaymentEventIn(event_type="immediate", event_date="2026-06-11",
            idempotency_key="synthetic-rejected-delete-payment",
            allocations=[CardPaymentAllocationIn(entry_payment_key=paid["payment_key"], amount_value=500)]))
        with self.client() as client:
            for path, status in (("/api/entries/987654", 404), ("/api/cash-flows/987654", 404),
                                 (f"/api/entries/{paid['id']}", 409), (f"/api/cash-flows/{event['cash_flow_id']}", 409)):
                with self.subTest(path=path):
                    before = self.dump()
                    self.assertEqual(client.delete(path).status_code, status)
                    self.assertEqual(self.dump(), before)

    def test_stable_confirmed_projection_restart_roundtrip_and_new_epoch(self):
        source, generated = self.recurring()
        update_entry(generated, LedgerEntryPatch(entry_date="2026-07-01", title="edited", amount_value=7000))
        for checkpoint in ("restart", "roundtrip"):
            with self.subTest(checkpoint=checkpoint):
                init_db()
                if checkpoint == "roundtrip":
                    snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                row = month.get_confirmed_planned_entries({})[0]
                self.assertEqual(row["confirmed_amount_value"], 7000)
                self.assertEqual(row["entry_date"], "2026-07-01")
        self.assertTrue(delete_entry(generated))
        self.assertIsNotNone(confirm_planned_entry(source))

    def test_boolean_normalization_preserves_monetary_precedence_and_roundtrip(self):
        for kind in ("claim", "family_card"):
            for title in ("ordinary", "한국전력"):
                for enabled, override, amount, expected in ((False, 0, 0, 10000), (True, 0, 0, 9880),
                                                           (False, 1, 500, 9500), (None, 1, 120, 9880)):
                    with self.subTest(kind=kind, title=title, enabled=enabled, override=override):
                        panel = create_panel(MonthlyPanelIn(month="2026-06", panel_type=kind, title=title,
                            amount_value=10000, discount_enabled=enabled, discount_override=override,
                            discount_amount=amount, sort_order=1))
                        self.assertEqual(present_monthly_panel(panel)["effective_amount_value"], expected)
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        init_db()
        with session() as conn:
            rows = [dict(row) for row in conn.execute("SELECT * FROM monthly_panels ORDER BY id")]
        self.assertEqual([present_monthly_panel(row)["effective_amount_value"] for row in rows],
                         [10000, 9880, 9500, 9880] * 4)

    def test_boolean_exclusion_notification_identity_matches_redundant_representation(self):
        with self.client() as client:
            for kind in ("claim", "family_card"):
                with self.subTest(kind=kind):
                    payload = {"month": "2026-06", "panel_type": kind, "title": "ordinary",
                        "amount_value": 10000, "sort_order": 1, "discount_enabled": False,
                        "candidate_registration_key": f"synthetic-notification-{kind}"}
                    first = client.post("/api/month/current/panels", json=payload)
                    retry = client.post("/api/month/current/panels", json={**payload,
                        "discount_override": 1, "discount_amount": 0})
                    self.assertEqual(first.status_code, 200)
                    self.assertEqual(retry.status_code, 200)
                    self.assertEqual(first.json()["id"], retry.json()["id"])
                    self.assertEqual(retry.json()["effective_amount_value"], 10000)

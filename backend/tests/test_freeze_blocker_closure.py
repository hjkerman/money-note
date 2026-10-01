import copy
import json
import os
from datetime import date
from pathlib import Path
import sqlite3
from unittest.mock import patch

from fastapi import HTTPException

from tests.db_fixture import IsolatedDatabaseTestCase
from app.db import init_db, session
from app.repositories.entries import append_planned_entry, confirm_planned_entry, create_entry, delete_entry, update_entry
from app.repositories.panels import create_panel
from app.routers import entries as entry_routes, month as month_routes
from app.routers import operations as cash_routes
from app.routers import card_payments as discount_routes
from app.schemas import CashFlowIn, FixedPanelConfirmIn, LedgerEntryIn, LedgerEntryPatch, MonthlyPanelIn, MonthlyPanelPatch, PanelDiscountPatch, PlannedEntryIn
from app.services.panels import confirm_fixed_panel
from app.services.presentation import present_ledger_entry
from app.services import snapshot
from app.services.summary import current_summary_values


class FreezeBlockerClosureTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.today = patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-06-11"})
        self.today.start()
        from app.config import get_settings
        get_settings.cache_clear()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value = '100000' WHERE key = 'cash_flow_balance'")
            conn.execute("UPDATE app_settings SET value = '0' WHERE key = 'scheduled_income'")

    def tearDown(self):
        self.today.stop()
        super().tearDown()

    def dump(self):
        with sqlite3.connect(self.db_path) as conn:
            return tuple(conn.iterdump())

    def expense(self, **changes):
        return LedgerEntryIn(**{
            "book_section": "current", "entry_date": "2026-06-11",
            "title": "card", "usage_place": "shop", "amount_value": 10000,
            "sort_order": 1, **changes,
        })

    def test_recurring_cross_month_edit_restart_roundtrip_cancellation(self):
        planned = append_planned_entry(PlannedEntryIn(
            title="subscription", usage_place="Provider", usage_item="Service", amount_value=5000, due_day=11,
        ))
        generated = confirm_planned_entry(planned["id"])["entry"]
        update_entry(generated["id"], LedgerEntryPatch(entry_date="2026-07-01", title="edited", amount_value=7000))
        init_db()
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        self.assertTrue(delete_entry(generated["id"]))
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)
        self.assertEqual(current_summary_values()["current_month_spendable"], 95000)
        self.assertIsNotNone(confirm_planned_entry(planned["id"]))

    def test_legacy_cross_month_edit_uses_materialized_confirmation(self):
        for version in (4, 5, 6):
            with self.subTest(version=version):
                artifact = json.loads((Path(__file__).parent / "fixtures" / f"snapshot_v{version}_recurring.json").read_text())
                snapshot.restore_snapshot(artifact)
                update_entry(42, LedgerEntryPatch(entry_date="2026-07-01", usage_place="Provider"))
                init_db()
                snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                delete_entry(42)
                self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)
                self.assertIsNotNone(confirm_planned_entry(41))

    def test_utility_preserves_explicit_legacy_monetary_input(self):
        for place, amount in (("한국전력", 120), ("도시가스", 500), ("shop", 120)):
            with self.subTest(place=place):
                row = create_entry(self.expense(usage_place=place, discount_override=1, aux_amount_value=amount))
                self.assertEqual(row["aux_amount_value"], amount)
                self.assertEqual(present_ledger_entry(row)["effective_amount_value"], 10000 - amount)

    def test_utility_all_supported_explicit_representations_and_registration_retry(self):
        cases = [({}, 10000), ({"discount_enabled": True}, 9880),
                 ({"discount_enabled": False}, 10000), ({"discount_override_amount": 120}, 9880),
                 ({"discount_override": 1, "aux_amount_value": 500}, 9500),
                 ({"discount_override": 1, "aux_amount_value": 0}, 10000)]
        for index, (fields, expected) in enumerate(cases):
            with self.subTest(fields=fields):
                payload = self.expense(usage_place="한국전력", candidate_registration_key=f"utility-{index}", **fields)
                row = entry_routes.post_entry(payload, {})
                self.assertEqual(row["effective_amount_value"], expected)
                self.assertEqual(entry_routes.post_entry(payload, {})["id"], row["id"])
        for kind in ("claim", "family_card"):
            row = month_routes.post_panel(MonthlyPanelIn(month="2026-06", panel_type=kind,
                title="한국전력", amount_value=10000, discount_amount=500, discount_override=1, sort_order=1), {})
            self.assertEqual(row["effective_amount_value"], 9500)

    def test_old_generated_expense_does_not_release_new_confirmation(self):
        from app.services.month import close_current_month
        planned = append_planned_entry(PlannedEntryIn(title="card", usage_place="shop", amount_value=5000, due_day=11))
        old = confirm_planned_entry(planned["id"])["entry"]
        update_entry(old["id"], LedgerEntryPatch(entry_date="2026-07-02"))
        create_entry(self.expense(amount_value=0, discount_enabled=False))
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-06-30"}):
            close_current_month(date(2026, 6, 30), target_month="2026-06", allow_early_close=True, allow_unconfirmed_recurring=True)
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-07-11"}):
            new = confirm_planned_entry(planned["id"], today=date(2026, 7, 11))["entry"]
            snapshot.restore_snapshot(snapshot.export_snapshot()[1])
            delete_entry(old["id"])
            with session() as conn:
                self.assertEqual(conn.execute("SELECT confirmed_month FROM ledger_entries WHERE id=?", (planned["id"],)).fetchone()[0], "2026-07")
            delete_entry(new["id"])
            self.assertIsNotNone(confirm_planned_entry(planned["id"], today=date(2026, 7, 11)))

    def test_recurring_cancel_rollback_after_delete_and_before_release(self):
        from contextlib import contextmanager
        planned = append_planned_entry(PlannedEntryIn(title="card", usage_place="shop", amount_value=5000, due_day=11))
        generated = confirm_planned_entry(planned["id"])["entry"]
        before = self.dump()
        @contextmanager
        def failing_session(**kwargs):
            with session(**kwargs) as conn:
                conn.execute("CREATE TEMP TRIGGER fail_release BEFORE UPDATE OF confirmed_month ON ledger_entries "
                             "WHEN NEW.entry_kind='planned' AND NEW.confirmed_month IS NULL BEGIN SELECT RAISE(ABORT, 'injected release'); END")
                yield conn
        with patch("app.repositories.entries.session", failing_session):
            with self.assertRaisesRegex(sqlite3.IntegrityError, "injected release"):
                delete_entry(generated["id"])
        self.assertEqual(self.dump(), before)

    def test_cash_response_model_validation_and_serialization_roll_back(self):
        payload = CashFlowIn(occurred_on=date(2026, 6, 11), title="cash", amount_value=-500, sort_order=1)
        for stage in ("model_validate", "model_dump"):
            with self.subTest(stage=stage):
                before = self.dump()
                with patch.object(cash_routes.CashFlow, stage, side_effect=RuntimeError("cash response")):
                    with self.assertRaisesRegex(RuntimeError, "cash response"):
                        cash_routes.post_cash_flow(payload, {})
                self.assertEqual(self.dump(), before)
        cash_routes.post_cash_flow(payload, {})
        self.assertEqual(current_summary_values()["cash_flow_balance"], 99500)

    def test_discount_presenter_422_cannot_hide_a_durable_financial_change(self):
        row = entry_routes.post_entry(self.expense(discount_enabled=False), {})
        before = self.dump()
        with patch.object(discount_routes, "present_ledger_entry", side_effect=ValueError("discount response")):
            with self.assertRaises(HTTPException):
                discount_routes.patch_entry_discount(row["payment_key"], PanelDiscountPatch(discount_amount=500), {})
        self.assertEqual(self.dump(), before)
        self.assertEqual(current_summary_values()["card_total"], 10000)

    def test_update_presenter_failures_roll_back_identity_and_financial_values(self):
        entry = entry_routes.post_entry(self.expense(discount_enabled=False), {})
        panel = month_routes.post_panel(MonthlyPanelIn(month="2026-06", panel_type="claim",
            title="claim", amount_value=10000, sort_order=1), {})
        cases = [
            (entry_routes, "present_ledger_entry", lambda: entry_routes.patch_entry(
                entry["id"], LedgerEntryPatch(amount_value=20000), {})),
            (month_routes, "present_monthly_panel", lambda: month_routes.patch_panel(
                panel["id"], MonthlyPanelPatch(amount_value=20000), {})),
            (month_routes, "present_monthly_panel", lambda: month_routes.patch_panel_discount(
                panel["id"], PanelDiscountPatch(discount_amount=500), {})),
        ]
        for module, presenter, update in cases:
            with self.subTest(update=update):
                before = self.dump()
                with patch.object(module, presenter, side_effect=RuntimeError("update response")):
                    with self.assertRaisesRegex(RuntimeError, "update response"):
                        update()
                self.assertEqual(self.dump(), before)

    def test_named_revision_contract_accepts_layout_not_aba(self):
        with session() as conn:
            conn.execute("DROP TRIGGER revision_cash_flows_insert")
            conn.execute('CREATE TRIGGER "revision_cash_flows_insert" AFTER INSERT ON "cash_flows" BEGIN '
                         '/* equivalent layout */ UPDATE "authoritative_state_revision" SET "revision" = "revision" + 1 WHERE "id" = 1; END')
        init_db()
        init_db()
        with session() as conn:
            before = conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
        row = cash_routes.post_cash_flow(CashFlowIn(occurred_on=date(2026, 6, 11), title="ABA", amount_value=-500, sort_order=1), {})
        cash_routes.remove_cash_flow(row["id"], {})
        with session() as conn:
            self.assertEqual(conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0], before + 2)

    def test_extra_trigger_cannot_cancel_authoritative_revision_increment(self):
        with session() as conn:
            conn.execute("CREATE TRIGGER undo_revision AFTER INSERT ON cash_flows BEGIN "
                         "UPDATE authoritative_state_revision SET revision=revision-1 WHERE id=1; END")
            conn.execute("PRAGMA user_version=0")
        before = self.dump()
        with self.assertRaisesRegex(RuntimeError, "revision"):
            init_db()
        self.assertEqual(self.dump(), before)

    def test_router_presenter_failure_rolls_back_and_retry_creates_once(self):
        payload = self.expense(discount_enabled=False)
        with patch.object(entry_routes, "present_ledger_entry", side_effect=ValueError("response conversion failed")):
            with self.assertRaises(HTTPException):
                entry_routes.post_entry(payload, {})
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger_entries WHERE entry_kind='expense'").fetchone()[0], 0)
        entry_routes.post_entry(payload, {})
        self.assertEqual(current_summary_values()["card_total"], 10000)

    def test_api_pre_commit_failure_and_post_commit_identity_retry(self):
        from contextlib import contextmanager
        payload = self.expense(discount_enabled=False, candidate_registration_key="closure-transport-identity")
        @contextmanager
        def fail_before_commit(**kwargs):
            with session(**kwargs) as conn:
                yield conn
                raise RuntimeError("immediately before commit")
        before = self.dump()
        with patch.object(entry_routes, "session", fail_before_commit):
            with self.assertRaisesRegex(RuntimeError, "before commit"):
                entry_routes.post_entry(payload, {})
        self.assertEqual(self.dump(), before)
        committed = entry_routes.post_entry(payload, {})  # response may be lost after this commit
        self.assertEqual(entry_routes.post_entry(payload, {})["id"], committed["id"])
        self.assertEqual(current_summary_values()["card_total"], 10000)
        with self.assertRaises(HTTPException):
            entry_routes.post_entry(self.expense(amount_value=20000, discount_enabled=False,
                candidate_registration_key="closure-transport-identity"), {})
        self.assertEqual(current_summary_values()["card_total"], 10000)

    def test_utility_monetary_intent_survives_input_only_mobile_wins(self):
        from app.schemas import OfflineMobileWinsIn
        from app.services.offline_reconciliation import apply_mobile_wins, export_offline_baseline
        baseline = export_offline_baseline()
        payload = OfflineMobileWinsIn(schema_version=1, reconciliation_id="closure-utility-0001",
            baseline_fingerprint=baseline["state_fingerprint"], baseline_snapshot=baseline["snapshot"],
            mobile_artifact_sha256="a" * 64, expected_server_fingerprint=baseline["state_fingerprint"],
            password="synthetic-unused-password", operations=[{
                "schema_version": 1, "operation_id": "closure-utility-operation-1", "sequence": 1,
                "operation_type": "CREATE_CARD_EXPENSE", "status": "pending", "created_at": "2026-06-11T03:00:00Z",
                "payload": {"book_section": "current", "entry_kind": "expense", "entry_date": "2026-06-11",
                    "title": "한국전력", "usage_place": "한국전력", "amount_value": 10000,
                    "usage_item": None, "spending_category": None, "discount_enabled": True,
                    "discount_override_amount": 120},
            }])
        first = apply_mobile_wins(payload)
        self.assertEqual(apply_mobile_wins(payload), first)
        self.assertEqual(current_summary_values()["card_total"], 9880)
        self.assertEqual(current_summary_values()["remaining_liquidity"], 90120)

    def test_panel_presenter_failure_is_atomic_including_registration(self):
        for panel_type in ("claim", "family_card"):
            with self.subTest(panel_type=panel_type):
                before = self.dump()
                with patch.object(month_routes, "present_monthly_panel", side_effect=ValueError("response failed")):
                    with self.assertRaises(HTTPException):
                        month_routes.post_panel(MonthlyPanelIn(month="2026-06", panel_type=panel_type,
                            title="panel", amount_value=10000, sort_order=1,
                            candidate_registration_key=f"closure-{panel_type}"), {})
                self.assertEqual(self.dump(), before)

    def test_confirmation_presenter_failure_rolls_back(self):
        planned = append_planned_entry(PlannedEntryIn(title="card", usage_place="shop", amount_value=5000, due_day=11))
        before = self.dump()
        with patch.object(month_routes, "present_ledger_entry", side_effect=RuntimeError("response failed")):
            with self.assertRaises(RuntimeError):
                month_routes.post_confirm_planned_entry(planned["id"], None, {})
        self.assertEqual(self.dump(), before)
        fixed = create_panel(MonthlyPanelIn(month="2026-06", panel_type="fixed", title="fixed", amount_value=5000, sort_order=1))
        before = self.dump()
        with patch.object(month_routes, "present_monthly_panel", side_effect=RuntimeError("response failed")):
            with self.assertRaises(RuntimeError):
                month_routes.post_confirm_fixed_panel(fixed["id"], FixedPanelConfirmIn(occurred_on=date(2026, 6, 11)), {})
        self.assertEqual(self.dump(), before)

    def test_same_name_wrong_revision_trigger_is_rejected_without_mutation(self):
        for version in (0, 3):
            for case in ("noop", "event", "table", "decrement", "wrong_target"):
                with self.subTest(version=version, case=case):
                    init_db()
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("DROP TRIGGER revision_cash_flows_insert")
                        event = "DELETE" if case == "event" else "INSERT"
                        table = "app_labels" if case == "table" else "cash_flows"
                        body = {
                            "noop": "SELECT 1", "decrement": "UPDATE authoritative_state_revision SET revision=revision-1 WHERE id=1",
                            "wrong_target": "UPDATE authoritative_state_revision SET revision=revision+1 WHERE id=2",
                        }.get(case, "UPDATE authoritative_state_revision SET revision=revision+1 WHERE id=1")
                        conn.execute(f"CREATE TRIGGER revision_cash_flows_insert AFTER {event} ON {table} BEGIN {body}; END")
                        conn.execute(f"PRAGMA user_version={version}")
                    before = self.dump()
                    with self.assertRaisesRegex(RuntimeError, "revision"):
                        init_db()
                    self.assertEqual(self.dump(), before)
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("DROP TRIGGER revision_cash_flows_insert")
                        conn.execute("CREATE TRIGGER revision_cash_flows_insert AFTER INSERT ON cash_flows BEGIN UPDATE authoritative_state_revision SET revision=revision+1 WHERE id=1; END")

    def test_snapshot_invalid_offset_rejected_without_destination_change(self):
        fixed = create_panel(MonthlyPanelIn(month="2026-06", panel_type="fixed", title="fixed", amount_value=5000, sort_order=1))
        confirm_fixed_panel(fixed["id"], "2026-06-11")
        valid = snapshot.export_snapshot()[1]
        for offset in ("+00:99", "+24:00", "-01:60"):
            with self.subTest(offset=offset):
                bad = copy.deepcopy(valid)
                bad["data"]["monthly_panels"][0]["confirmed_at"] = "2026-06-11T00:00:00" + offset
                bad["manifest"] = snapshot._build_manifest(bad["data"], policy_context=bad["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(bad))
                bad["snapshot_id"] = bad["manifest"]["content_sha256"]
                before = self.dump()
                with self.assertRaisesRegex(ValueError, "timestamp"):
                    snapshot.restore_snapshot(bad)
                self.assertEqual(self.dump(), before)

    def test_snapshot_cannot_change_or_partially_drop_bound_recurring_epoch(self):
        planned = append_planned_entry(PlannedEntryIn(title="card", usage_place="shop", amount_value=5000, due_day=11))
        generated = confirm_planned_entry(planned["id"])["entry"]
        valid = snapshot.export_snapshot()[1]
        for fields in ({"confirmed_month": "2026-05"}, {"confirmed_at": None},
                       {"confirmed_at": "2026-06-11T00:00:00+00:99"}):
            with self.subTest(fields=fields):
                bad = copy.deepcopy(valid)
                next(row for row in bad["data"]["ledger_entries"] if row["id"] == generated["id"]).update(fields)
                bad["manifest"] = snapshot._build_manifest(bad["data"], policy_context=bad["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(bad))
                bad["snapshot_id"] = bad["manifest"]["content_sha256"]
                before = self.dump()
                with self.assertRaisesRegex(ValueError, "recurring confirmation"):
                    snapshot.restore_snapshot(bad)
                self.assertEqual(self.dump(), before)

import copy
from datetime import date
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import create_entry
from app.repositories.panels import create_panel
from app.schemas import CardPaymentAllocationIn, CardPaymentEventIn, LateCardEntryIn, LedgerEntry, LedgerEntryIn, MonthlyPanel, MonthlyPanelIn
from app.routers.entries import post_entry
from app.routers.month import post_panel
from app.services.card_payments import (
    active_card_payment_unpaid_total,
    cancel_toll_deferral,
    create_card_payment_event,
    create_month_close_card_payment_batch,
    create_late_card_entry,
    current_payment_status,
    defer_toll_payment,
)
from app.services.panels import confirm_fixed_panel
from app.services.month import close_current_month
from app.services.snapshot import export_snapshot, restore_snapshot
import app.services.snapshot as snapshot_service
from app.services.summary import current_summary_values


class FinancialStateGapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "money-note.sqlite3"
        self.env = patch.dict(os.environ, {
            "MONEY_NOTE_DB_PATH": str(self.db_path),
            "MONEY_NOTE_TODAY": "2026-09-01",
        })
        self.env.start()
        get_settings.cache_clear()
        init_db()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value = '0' WHERE key = 'scheduled_income'")
            conn.execute("INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order) VALUES ('2026-08-31', '잔액', 1000000, 1)")
            conn.execute("INSERT INTO app_settings(key, value) VALUES ('card_discount_policy:owner:2026-08', 'disabled')")

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def _entry(self, key: str | None = None, date_value: str = "2026-08-20", amount: int = 50000) -> LedgerEntryIn:
        return LedgerEntryIn(
            book_section="current", entry_kind="expense", entry_date=date_value,
            title="[가게] 지출", usage_place="가게", usage_item="지출",
            amount_value=amount, sort_order=0, candidate_registration_key=key,
        )

    def _close_august_batch(self, original: int = 100000) -> None:
        with session() as conn:
            if original:
                conn.execute(
                    "INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, sort_order, payment_key) "
                    "VALUES ('archive', 'expense', '2026-08-10', '기존 카드', ?, 1, 'existing-key')",
                    (original,),
                )
            create_month_close_card_payment_batch(conn, "2026-08")
            conn.execute("INSERT INTO app_settings(key, value) VALUES ('last_closed_month', '2026-08')")

    def _pay(self, key: str, amount: int, on: str = "2026-09-01") -> dict:
        return create_card_payment_event(
            CardPaymentEventIn(
                idempotency_key=f"payment-{key}-{on}-{amount}",
                event_date=on, event_type="immediate",
                allocations=[CardPaymentAllocationIn(entry_payment_key=key, amount_value=amount)],
            ),
            date(2026, 9, 1),
        )

    def _close_grouped_toll_batch(self) -> None:
        with session() as conn:
            for order, (key, title, amount) in enumerate(
                (("toll-a", "하이패스 A", 100000), ("toll-b", "통행료 B", 20000)), start=1
            ):
                conn.execute(
                    "INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, sort_order, payment_key) "
                    "VALUES ('archive', 'expense', '2026-08-10', ?, ?, ?, ?)",
                    (title, amount, order, key),
                )
            create_month_close_card_payment_batch(conn, "2026-08")
            conn.execute("INSERT INTO app_settings(key, value) VALUES ('last_closed_month', '2026-08')")

    def _assert_toll_finances(self, current: int, batch: int, cash: int = 1000000) -> None:
        summary = current_summary_values()
        self.assertEqual(summary["cash_flow_balance"], cash)
        self.assertEqual(summary["card_total"], current)
        self.assertEqual(active_card_payment_unpaid_total(date(2026, 9, 1)), batch)
        self.assertEqual(current_payment_status(date(2026, 9, 1))["recorded_remaining_total"], batch)
        self.assertEqual(summary["remaining_liquidity"], cash - current - batch)

    def test_grouped_toll_partial_defer_counts_each_obligation_once(self) -> None:
        self._close_grouped_toll_batch()
        self._assert_toll_finances(0, 120000)
        defer_toll_payment("toll-a", date(2026, 9, 1))
        self._assert_toll_finances(100000, 20000)
        rows = current_payment_status(date(2026, 9, 1))["rows"]
        self.assertEqual([row["payment_keys"] for row in rows], [["toll-b"], ["toll-a"]])
        self.assertEqual([row["is_deferred"] for row in rows], [False, True])

    def test_grouped_toll_full_defer_keeps_only_current_liability(self) -> None:
        self._close_grouped_toll_batch()
        defer_toll_payment("toll-a", date(2026, 9, 1))
        defer_toll_payment("toll-b", date(2026, 9, 1))
        self._assert_toll_finances(120000, 0)
        rows = current_payment_status(date(2026, 9, 1))["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]["payment_keys"]), {"toll-a", "toll-b"})
        self.assertTrue(rows[0]["is_deferred"])

    def test_grouped_toll_partial_retry_keeps_origin_and_liability(self) -> None:
        self._close_grouped_toll_batch()
        first = defer_toll_payment("toll-a", date(2026, 9, 1))
        self.assertEqual(defer_toll_payment("toll-a", date(2026, 9, 1)), first)
        self._assert_toll_finances(100000, 20000)
        with session() as conn:
            origin = conn.execute(
                "SELECT original_entry_date FROM card_payment_deferrals WHERE entry_payment_key = 'toll-a'"
            ).fetchone()[0]
        self.assertEqual(origin, "2026-08-10")

    def test_grouped_toll_partial_defer_then_cancel_restores_original(self) -> None:
        self._close_grouped_toll_batch()
        defer_toll_payment("toll-a", date(2026, 9, 1))
        self.assertTrue(cancel_toll_deferral("toll-a", date(2026, 9, 1)))
        self._assert_toll_finances(0, 120000)
        with session() as conn:
            row = conn.execute(
                "SELECT book_section, entry_date FROM ledger_entries WHERE payment_key = 'toll-a'"
            ).fetchone()
        self.assertEqual((row["book_section"], row["entry_date"]), ("archive", "2026-08-10"))

    def test_grouped_toll_full_defer_then_partial_cancel(self) -> None:
        self._close_grouped_toll_batch()
        defer_toll_payment("toll-a", date(2026, 9, 1))
        defer_toll_payment("toll-b", date(2026, 9, 1))
        self.assertTrue(cancel_toll_deferral("toll-a", date(2026, 9, 1)))
        self._assert_toll_finances(20000, 100000)
        rows = current_payment_status(date(2026, 9, 1))["rows"]
        self.assertEqual([row["is_deferred"] for row in rows], [False, True])

    def test_grouped_toll_paid_sibling_rejection_preserves_partial_defer(self) -> None:
        self._close_grouped_toll_batch()
        self._pay("toll-b", 5000)
        rows = current_payment_status(date(2026, 9, 1))["rows"]
        self.assertEqual([row["payment_keys"] for row in rows], [["toll-a"], ["toll-b"]])
        defer_toll_payment("toll-a", date(2026, 9, 1))
        with self.assertRaisesRegex(ValueError, "이미 일부결제"):
            defer_toll_payment("toll-b", date(2026, 9, 1))
        self._assert_toll_finances(100000, 15000, cash=995000)
        rows = current_payment_status(date(2026, 9, 1))["rows"]
        self.assertEqual([row["payment_keys"] for row in rows], [["toll-b"], ["toll-a"]])

    def test_grouped_toll_mixed_subgroups_keep_distinct_ui_identity(self) -> None:
        self._close_grouped_toll_batch()
        with session() as conn:
            batch_id = conn.execute("SELECT id FROM card_payment_batches WHERE status = 'active'").fetchone()[0]
            for order, (key, amount) in enumerate((("toll-c", 3000), ("toll-d", 4000)), start=3):
                entry_id = conn.execute(
                    "INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, sort_order, payment_key) "
                    "VALUES ('archive', 'expense', '2026-08-11', '통행료 추가', ?, ?, ?)",
                    (amount, order, key),
                ).lastrowid
                conn.execute(
                    "INSERT INTO card_payment_batch_items(batch_id, entry_id, entry_payment_key) VALUES (?, ?, ?)",
                    (batch_id, entry_id, key),
                )
        defer_toll_payment("toll-a", date(2026, 9, 1))
        defer_toll_payment("toll-b", date(2026, 9, 1))
        self._assert_toll_finances(120000, 7000)
        rows = current_payment_status(date(2026, 9, 1))["rows"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["is_group"] for row in rows))
        self.assertEqual([row["is_deferred"] for row in rows], [False, True])
        self.assertEqual([row["remaining_amount"] for row in rows], [7000, 120000])
        self.assertEqual(len({row["payment_key"] for row in rows}), 2)
        self.assertEqual(len({row["id"] for row in rows}), 2)

    def test_grouped_toll_settled_current_part_does_not_revive_closed_cycle(self) -> None:
        self._close_grouped_toll_batch()
        defer_toll_payment("toll-a", date(2026, 9, 1))
        self._pay("toll-b", 20000)
        self._assert_toll_finances(100000, 0, cash=980000)
        with self.assertRaisesRegex(ValueError, "완납"):
            create_entry(self._entry())
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0], 2)

    def test_grouped_toll_interrupted_second_operation_is_financially_valid(self) -> None:
        self._close_grouped_toll_batch()
        defer_toll_payment("toll-a", date(2026, 9, 1))
        with self.assertRaises(ConnectionError):
            raise ConnectionError("second request did not reach server")
        self._assert_toll_finances(100000, 20000)
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_payment_deferrals").fetchone()[0], 1)

    def test_non_toll_deferral_stays_ungrouped_and_exact_once(self) -> None:
        self._close_august_batch()
        self._assert_toll_finances(0, 100000)
        defer_toll_payment("existing-key", date(2026, 9, 1))
        self._assert_toll_finances(98800, 0)
        self.assertTrue(cancel_toll_deferral("existing-key", date(2026, 9, 1)))
        self._assert_toll_finances(0, 100000)

    def test_generic_closed_expense_joins_batch_exactly_once(self) -> None:
        self._close_august_batch()
        before = current_summary_values()
        created = create_entry(self._entry())
        after = current_summary_values()
        self.assertEqual((created["book_section"], created["entry_kind"]), ("archive", "late_expense"))
        self.assertEqual(before["remaining_liquidity"] - after["remaining_liquidity"], 50000)
        self.assertEqual(after["remaining_liquidity"], 850000)
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_payment_batch_items WHERE entry_id = ?", (created["id"],)).fetchone()[0], 1)

    def test_closed_expense_rejects_settled_and_wrong_cycle_without_insert(self) -> None:
        self._close_august_batch()
        self._pay("existing-key", 100000)
        with self.assertRaisesRegex(ValueError, "완납"):
            create_entry(self._entry())
        with self.assertRaisesRegex(ValueError, "안전하게 연결"):
            create_entry(self._entry(date_value="2026-07-25"))
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0], 1)

    def test_open_past_expense_keeps_current_semantics(self) -> None:
        created = create_entry(self._entry())
        self.assertEqual((created["book_section"], created["entry_kind"]), ("current", "expense"))

    def test_explicit_archive_cannot_bypass_closed_liability_guard(self) -> None:
        self._close_august_batch()
        archived = self._entry()
        archived.book_section = "archive"
        created = create_entry(archived)
        self.assertEqual(created["entry_kind"], "late_expense")
        self.assertEqual(current_summary_values()["remaining_liquidity"], 850000)

    def test_closed_expense_after_due_is_rejected(self) -> None:
        self._close_august_batch()
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-09-15"}):
            get_settings.cache_clear()
            with self.assertRaisesRegex(ValueError, "이미 정산"):
                create_entry(self._entry())
        get_settings.cache_clear()

    def test_dedicated_late_entry_cannot_revive_settled_cycle(self) -> None:
        self._close_august_batch()
        self._pay("existing-key", 100000)
        with self.assertRaisesRegex(ValueError, "완납"):
            create_late_card_entry(
                LateCardEntryIn(entry_date="2026-08-20", usage_place="지연매입", amount_value=5000),
                date(2026, 9, 1),
            )
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0], 1)

    def test_same_candidate_retry_and_distinct_similar_candidate(self) -> None:
        first = create_entry(self._entry("woori_card:candidate-a"))
        retry = create_entry(self._entry("woori_card:candidate-a"))
        other = create_entry(self._entry("woori_card:candidate-b"))
        self.assertEqual(first["id"], retry["id"])
        self.assertNotEqual(first["id"], other["id"])
        with self.assertRaisesRegex(ValueError, "다른 내용"):
            create_entry(self._entry("woori_card:candidate-a", amount=60000))
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0], 2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM notification_candidate_registrations").fetchone()[0], 2)

    def test_initial_actual_payment_override_is_atomic_and_authoritative(self) -> None:
        payload = self._entry("woori_card:initial-override", amount=10000)
        payload.discount_override_amount = 3000

        created = create_entry(payload)
        summary = current_summary_values()

        self.assertEqual(created["aux_amount_value"], 3000)
        self.assertEqual(created["discount_override"], 1)
        self.assertEqual(summary["card_total"], 7000)
        self.assertEqual(summary["remaining_liquidity"], 993000)
        retry = create_entry(payload)
        self.assertEqual(retry["id"], created["id"])

        changed = self._entry("woori_card:initial-override", amount=10000)
        changed.discount_override_amount = 2000
        with self.assertRaisesRegex(ValueError, "다른 내용"):
            create_entry(changed)

    def test_initial_discount_exclusion_is_part_of_create_transaction(self) -> None:
        payload = self._entry(amount=10000)
        payload.discount_enabled = False

        created = create_entry(payload)
        self.assertEqual(created["aux_amount_value"], 0)
        self.assertEqual(created["discount_override"], 1)
        self.assertEqual(current_summary_values()["card_total"], 10000)

    def test_initial_override_failure_rolls_back_entry_and_registration(self) -> None:
        payload = self._entry("woori_card:rollback-override", amount=10000)
        payload.discount_override_amount = 3000

        with patch(
            "app.repositories.entries.set_entry_discount",
            side_effect=ValueError("injected override failure"),
        ):
            with self.assertRaisesRegex(ValueError, "injected override failure"):
                create_entry(payload)

        with session() as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM notification_candidate_registrations"
                ).fetchone()[0],
                0,
            )
        self.assertEqual(current_summary_values()["card_total"], 0)

    def test_web_and_mobile_share_entry_api_and_key_is_request_only(self) -> None:
        self._close_august_batch()
        first = post_entry(self._entry("woori_card:api-shared"), _={})
        retry = post_entry(self._entry("woori_card:api-shared"), _={})
        self.assertEqual(first["id"], retry["id"])
        self.assertEqual(first["entry_kind"], "late_expense")
        self.assertNotIn("candidate_registration_key", LedgerEntry.model_validate(first).model_dump())

    def test_panel_registration_key_is_not_in_api_response(self) -> None:
        payload = MonthlyPanelIn(
            month="2026-09", panel_type="family_card", title="가게", spent_on="2026-09-01",
            amount_value=5000, sort_order=0, candidate_registration_key="woori_card:panel-api",
        )
        first = post_panel(payload, _={})
        retry = post_panel(payload, _={})
        self.assertEqual(first["id"], retry["id"])
        self.assertNotIn("candidate_registration_key", MonthlyPanel.model_validate(first).model_dump())

    def test_candidate_cannot_switch_between_claim_and_ledger_after_write(self) -> None:
        panel = MonthlyPanelIn(
            month="2026-09", panel_type="claim", title="가게: 지출", spent_on="2026-09-01",
            amount_value=50000, sort_order=0, candidate_registration_key="woori_card:candidate-x",
        )
        first = create_panel(panel)
        self.assertEqual(create_panel(panel)["id"], first["id"])
        with self.assertRaisesRegex(ValueError, "등록 대상"):
            create_entry(self._entry("woori_card:candidate-x", date_value="2026-09-01"))
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM monthly_panels").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0], 0)

    def test_candidate_registration_id_survives_month_close_copy(self) -> None:
        first = create_entry(self._entry("woori_card:close-copy"))
        close_current_month(date(2026, 9, 1), target_month="2026-08")
        retry = create_entry(self._entry("woori_card:close-copy"))
        self.assertNotEqual(first["id"], retry["id"])
        self.assertEqual(retry["book_section"], "archive")
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM ledger_entries WHERE payment_key = ?", (first["payment_key"],)).fetchone()[0], 1)

    def test_closed_fixed_confirmation_rejects_without_partial_change(self) -> None:
        self._close_august_batch(0)
        with session() as conn:
            panel_id = conn.execute(
                "INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order) VALUES ('2026-08', 'fixed', '월세', 100000, 1)"
            ).lastrowid
        with self.assertRaisesRegex(ValueError, "마감"):
            confirm_fixed_panel(panel_id, "2026-08-30")
        with session() as conn:
            self.assertIsNone(conn.execute("SELECT confirmed_month FROM monthly_panels WHERE id = ?", (panel_id,)).fetchone()[0])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows").fetchone()[0], 1)
        self.assertIsNotNone(confirm_fixed_panel(panel_id, "2026-09-01"))

    def test_future_actual_payment_rejects_without_cash_or_allocation(self) -> None:
        self._close_august_batch()
        before = current_summary_values()
        with self.assertRaisesRegex(ValueError, "오늘 이후"):
            self._pay("existing-key", 100000, "2026-09-02")
        self.assertEqual(current_summary_values()["remaining_liquidity"], before["remaining_liquidity"])
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_payment_events").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows").fetchone()[0], 1)
        self._pay("existing-key", 10000, "2026-08-31")
        self._pay("existing-key", 10000, "2026-09-01")

    def test_same_deferral_retry_preserves_first_origin_and_cancel(self) -> None:
        self._close_august_batch()
        before = current_summary_values()
        first = defer_toll_payment("existing-key", date(2026, 9, 1))
        retry = defer_toll_payment("existing-key", date(2026, 9, 1))
        self.assertEqual(first, retry)
        with session() as conn:
            self.assertEqual(conn.execute("SELECT original_entry_date FROM card_payment_deferrals WHERE entry_payment_key = 'existing-key'").fetchone()[0], "2026-08-10")
        self.assertTrue(cancel_toll_deferral("existing-key", date(2026, 9, 1)))
        self.assertEqual(current_summary_values()["remaining_liquidity"], before["remaining_liquidity"])
        with session() as conn:
            row = conn.execute("SELECT book_section, entry_date FROM ledger_entries WHERE payment_key = 'existing-key'").fetchone()
            self.assertEqual((row["book_section"], row["entry_date"]), ("archive", "2026-08-10"))

    def test_partial_other_item_then_deferral_retry_keeps_exact_obligation(self) -> None:
        self._close_august_batch()
        with session() as conn:
            added = conn.execute(
                "INSERT INTO ledger_entries(book_section, entry_kind, entry_date, title, amount_value, sort_order, payment_key) "
                "VALUES ('archive', 'expense', '2026-08-11', '다른 카드', 20000, 2, 'other-key')"
            ).lastrowid
            conn.execute("INSERT INTO card_payment_batch_items(batch_id, entry_id, entry_payment_key) VALUES (1, ?, 'other-key')", (added,))
        self._pay("other-key", 5000)
        before = current_summary_values()
        defer_toll_payment("existing-key", date(2026, 9, 1))
        defer_toll_payment("existing-key", date(2026, 9, 1))
        cancel_toll_deferral("existing-key", date(2026, 9, 1))
        self.assertEqual(current_summary_values()["remaining_liquidity"], before["remaining_liquidity"])

    def test_new_cycle_deferral_can_replace_previous_cycle_metadata(self) -> None:
        self._close_august_batch()
        defer_toll_payment("existing-key", date(2026, 9, 1))
        close_current_month(date(2026, 9, 30), allow_early_close=True, target_month="2026-09")
        before = current_summary_values()["remaining_liquidity"]
        second = defer_toll_payment("existing-key", date(2026, 10, 1))
        self.assertEqual((second["from_payment_month"], second["target_payment_month"]), ("2026-10", "2026-11"))
        with session() as conn:
            origin = conn.execute("SELECT original_entry_date FROM card_payment_deferrals WHERE entry_payment_key = 'existing-key'").fetchone()[0]
        self.assertEqual(origin, "2026-09-01")
        self.assertEqual(defer_toll_payment("existing-key", date(2026, 10, 1)), second)
        self.assertTrue(cancel_toll_deferral("existing-key", date(2026, 10, 1)))
        self.assertEqual(current_summary_values()["remaining_liquidity"], before)

    def test_snapshot_rejects_positive_payment_without_cash_relation(self) -> None:
        self._close_august_batch()
        self._pay("existing-key", 10000)
        _, good = export_snapshot(date(2026, 9, 1))
        bad = copy.deepcopy(good)
        bad["data"]["card_payment_events"][0]["cash_flow_id"] = None
        bad["manifest"] = snapshot_service._build_manifest(
            bad["data"], policy_context=bad["card_charge_policy"],
            snapshot_metadata=snapshot_service._snapshot_metadata(bad),
        )
        bad["snapshot_id"] = bad["manifest"]["content_sha256"]
        with self.assertRaisesRegex(ValueError, "no linked cash flow"):
            restore_snapshot(bad)
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_payment_events").fetchone()[0], 1)
        self.assertIn("card_payment_events", restore_snapshot(good))

    def test_snapshot_zero_value_immediate_without_cash_relation_is_still_valid(self) -> None:
        with session() as conn:
            conn.execute(
                "INSERT INTO card_payment_events(event_date, event_type, total_amount, note) VALUES ('2026-09-01', 'immediate', 0, '구버전 0원 기록')"
            )
        _, snapshot = export_snapshot(date(2026, 9, 1))
        self.assertEqual(restore_snapshot(snapshot)["card_payment_events"], 1)

    def test_snapshot_registry_survives_restore_and_legacy_optional_absence(self) -> None:
        created = create_entry(self._entry("woori_card:preserved"))
        _, snapshot = export_snapshot(date(2026, 9, 1))
        restore_snapshot(snapshot)
        self.assertEqual(create_entry(self._entry("woori_card:preserved"))["id"], created["id"])
        for version in (4, 5, 6, 7):
            with self.subTest(schema_version=version):
                legacy = copy.deepcopy(snapshot)
                legacy["schema_version"] = version
                legacy["data"].pop("notification_candidate_registrations")
                legacy["manifest"] = snapshot_service._build_manifest(
                    legacy["data"],
                    table_names=[table for table in snapshot_service.SNAPSHOT_TABLES if table in legacy["data"]],
                    policy_context=legacy["card_charge_policy"],
                    snapshot_metadata=snapshot_service._snapshot_metadata(legacy),
                )
                legacy["snapshot_id"] = legacy["manifest"]["content_sha256"]
                restore_snapshot(legacy)
                with session() as conn:
                    self.assertEqual(conn.execute("SELECT COUNT(*) FROM notification_candidate_registrations").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()

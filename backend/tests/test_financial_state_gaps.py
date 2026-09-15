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
    cancel_toll_deferral,
    create_card_payment_event,
    create_month_close_card_payment_batch,
    create_late_card_entry,
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

from datetime import date
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repository import (
    confirm_planned_entry,
    confirm_fixed_panel,
    create_entry,
    delete_planned_entry,
    delete_entry,
    list_confirmed_planned_entries,
    list_entries,
    list_recent_closed_month_expense_counts,
)
from app.schemas import LedgerEntryIn
from app.services.card_payments import current_payment_status
from app.services.month import close_current_month, month_close_status
from app.services.presentation import present_ledger_entries, present_planned_charge_preview
from app.services.summary import current_summary_values


class MonthCloseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "money-note.sqlite3"
        self.env = patch.dict(os.environ, {"MONEY_NOTE_DB_PATH": str(self.db_path)})
        self.env.start()
        get_settings.cache_clear()
        init_db()
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, date_label, title,
                    amount_value, sort_order, payment_key
                )
                VALUES
                    ('current', 'expense', '2026-06-30', '2026.06.30.', '말일 사용', 10000, 1, 'june-key'),
                    ('current', 'expense', '2026-07-01', '2026.07.01.', '새 달 사용', 20000, 2, 'july-key'),
                    ('current', 'planned', NULL, '카드 정기결제', '정기결제', 30000, 3, NULL)
                """
            )

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_status_warns_about_oldest_open_month(self) -> None:
        status = month_close_status(date(2026, 7, 1))

        self.assertEqual(status["calendar_date"], "2026-07-01")
        self.assertTrue(status["needs_close"])
        self.assertEqual(status["oldest_open_month"], "2026-06")

    def test_status_lists_unconfirmed_recurring_items_for_target_cycle(self) -> None:
        with session() as conn:
            conn.execute(
                "UPDATE ledger_entries SET created_at = '2026-06-01 00:00:00' WHERE entry_kind = 'planned'"
            )
            conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '관리비', 80000, 1)
                """
            )

        status = month_close_status(date(2026, 7, 1))

        self.assertEqual(
            [(item["kind"], item["title"], item["amount_value"]) for item in status["unconfirmed_recurring_items"]],
            [("fixed", "관리비", 80000), ("planned", "정기결제", 30000)],
        )

    def test_close_requires_explicit_override_for_unconfirmed_recurring_items(self) -> None:
        with session() as conn:
            conn.execute(
                "UPDATE ledger_entries SET created_at = '2026-06-01 00:00:00' WHERE entry_kind = 'planned'"
            )
            conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '관리비', 80000, 1)
                """
            )

        with self.assertRaisesRegex(ValueError, "미확인 정기지출"):
            close_current_month(date(2026, 7, 1), target_month="2026-06")
        with session() as conn:
            current = conn.execute(
                "SELECT book_section FROM ledger_entries WHERE payment_key = 'june-key'"
            ).fetchone()
        self.assertEqual(current["book_section"], "current")
        self.assertFalse((self.db_path.parent / "snapshot-backups").exists())

        result = close_current_month(
            date(2026, 7, 1),
            target_month="2026-06",
            allow_unconfirmed_recurring=True,
        )

        self.assertEqual(result["closed_month"], "2026-06")

    def test_confirmed_recurring_items_do_not_trigger_month_close_warning(self) -> None:
        with session() as conn:
            planned_id = conn.execute(
                "SELECT id FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["id"]
            conn.execute(
                "UPDATE ledger_entries SET created_at = '2026-06-01 00:00:00' WHERE id = ?",
                (planned_id,),
            )
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-06', 'fixed', '관리비', 80000, 1)
                """
            ).lastrowid
        confirm_planned_entry(planned_id, date(2026, 6, 20), entry_date="2026-06-15")
        confirm_fixed_panel(panel_id, "2026-06-20", actual_amount=75000)

        status = month_close_status(date(2026, 7, 1))

        self.assertEqual(status["unconfirmed_recurring_items"], [])
        result = close_current_month(date(2026, 7, 1), target_month="2026-06")
        self.assertEqual(result["closed_month"], "2026-06")

    def test_status_uses_app_today_override(self) -> None:
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-07-01"}):
            get_settings.cache_clear()
            status = month_close_status()

        self.assertEqual(status["calendar_date"], "2026-07-01")
        self.assertEqual(status["calendar_month"], "2026-07")
        self.assertTrue(status["needs_close"])

    def test_close_archives_only_oldest_month(self) -> None:
        result = close_current_month(date(2026, 7, 1), target_month="2026-06")

        self.assertEqual(result["closed_month"], "2026-06")
        self.assertEqual(result["archived"], 1)
        backups = list((self.db_path.parent / "snapshot-backups").glob("pre_restore-*.money-note-snapshot.json"))
        self.assertEqual(len(backups), 1)
        self.assertIn("말일 사용", backups[0].read_text(encoding="utf-8"))
        with session() as conn:
            june = conn.execute(
                "SELECT book_section FROM ledger_entries WHERE payment_key = 'june-key'"
            ).fetchone()
            july = conn.execute(
                "SELECT book_section FROM ledger_entries WHERE payment_key = 'july-key'"
            ).fetchone()
            planned = conn.execute(
                "SELECT COUNT(*) AS count FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["count"]
        self.assertEqual(june["book_section"], "archive")
        self.assertEqual(july["book_section"], "current")
        self.assertEqual(planned, 1)
        self.assertFalse(month_close_status(date(2026, 7, 1))["needs_close"])

    def test_same_target_month_replay_is_idempotent(self) -> None:
        first = close_current_month(date(2026, 7, 1), target_month="2026-06")
        replay = close_current_month(date(2026, 7, 1), target_month="2026-06")

        self.assertEqual(first["archived"], 1)
        self.assertTrue(replay["already_closed"])
        with session() as conn:
            archive_count = conn.execute(
                "SELECT COUNT(*) AS count FROM ledger_entries WHERE payment_key = 'june-key'",
            ).fetchone()["count"]
            salary_count = conn.execute(
                "SELECT COUNT(*) AS count FROM cash_flows WHERE title = '급여' AND occurred_on = '2026-07-01'",
            ).fetchone()["count"]
            batch_count = conn.execute(
                "SELECT COUNT(*) AS count FROM card_payment_batches WHERE usage_month = '2026-06'",
            ).fetchone()["count"]
        self.assertEqual(archive_count, 1)
        self.assertEqual(salary_count, 1)
        self.assertEqual(batch_count, 1)

    def test_concurrent_same_target_month_closes_once(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: close_current_month(
                        date(2026, 7, 1),
                        target_month="2026-06",
                    ),
                    range(2),
                )
            )

        self.assertEqual(sum(result.get("archived", 0) for result in results), 1)
        self.assertEqual(sum(bool(result.get("already_closed")) for result in results), 1)
        with session() as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) AS count FROM ledger_entries WHERE payment_key = 'june-key'",
                ).fetchone()["count"],
                1,
            )

    def test_close_records_scheduled_income_as_next_cycle_salary(self) -> None:
        before = current_summary_values()

        close_current_month(date(2026, 7, 1))

        with session() as conn:
            salary = conn.execute(
                """
                SELECT occurred_on, title, amount_value, is_primary_income
                FROM cash_flows
                WHERE title = '급여'
                """
            ).fetchone()
        after = current_summary_values()
        self.assertEqual(dict(salary), {
            "occurred_on": "2026-07-01",
            "title": "급여",
            "amount_value": 400_000,
            "is_primary_income": 1,
        })
        self.assertEqual(after["cash_flow_balance"], before["cash_flow_balance"] + 400_000)

    def test_each_close_records_the_current_scheduled_income_once(self) -> None:
        close_current_month(date(2026, 7, 1))
        with session() as conn:
            conn.execute(
                "UPDATE app_settings SET value = '550000' WHERE key = 'scheduled_income'",
            )

        close_current_month(date(2026, 7, 27), allow_early_close=True)

        with session() as conn:
            salaries = conn.execute(
                """
                SELECT occurred_on, amount_value
                FROM cash_flows
                WHERE title = '급여'
                ORDER BY occurred_on, id
                """
            ).fetchall()
        self.assertEqual(
            [dict(row) for row in salaries],
            [
                {"occurred_on": "2026-07-01", "amount_value": 400_000},
                {"occurred_on": "2026-08-01", "amount_value": 550_000},
            ],
        )

    def test_early_close_salary_affects_balance_only_from_next_cycle_date(self) -> None:
        close_current_month(date(2026, 7, 1))
        close_current_month(date(2026, 7, 27), allow_early_close=True)

        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-07-27"}):
            get_settings.cache_clear()
            before_next_cycle = current_summary_values()
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-08-01"}):
            get_settings.cache_clear()
            on_next_cycle = current_summary_values()
        get_settings.cache_clear()

        self.assertEqual(before_next_cycle["cash_flow_balance"], 400_000)
        self.assertEqual(on_next_cycle["cash_flow_balance"], 800_000)

    @patch("app.services.month.create_month_close_card_payment_batch", side_effect=RuntimeError("batch failed"))
    def test_close_failure_rolls_back_salary_and_ledger_changes(self, _: object) -> None:
        with self.assertRaisesRegex(RuntimeError, "batch failed"):
            close_current_month(date(2026, 7, 1))

        with session() as conn:
            salary_count = conn.execute(
                "SELECT COUNT(*) AS count FROM cash_flows WHERE title = '급여'",
            ).fetchone()["count"]
            june = conn.execute(
                "SELECT book_section FROM ledger_entries WHERE payment_key = 'june-key'",
            ).fetchone()
        self.assertEqual(salary_count, 0)
        self.assertEqual(june["book_section"], "current")

    def test_recent_closed_month_expense_counts_ignore_current_and_planned_entries(self) -> None:
        close_current_month(date(2026, 7, 1))

        self.assertEqual(list_recent_closed_month_expense_counts(), [1])

    def test_close_preserves_discount_override_for_payment_panel(self) -> None:
        with session() as conn:
            conn.execute(
                """
                UPDATE ledger_entries
                SET discount_override = 1
                WHERE payment_key = 'june-key'
                """
            )

        close_current_month(date(2026, 7, 1))
        status = current_payment_status(date(2026, 7, 1))
        row = next(row for row in status["rows"] if row["payment_key"] == "june-key")

        self.assertEqual(row["book_section"], "archive")
        self.assertEqual(row["discount_override"], 1)
        self.assertEqual(row["discount_amount"], 0)
        self.assertEqual(row["remaining_amount"], 10_000)

    def test_current_calendar_month_cannot_be_closed_before_27th(self) -> None:
        close_current_month(date(2026, 7, 1))

        with self.assertRaisesRegex(ValueError, "27일부터"):
            close_current_month(date(2026, 7, 26), allow_early_close=True)

    def test_current_calendar_month_can_be_closed_early_with_explicit_confirmation(self) -> None:
        close_current_month(date(2026, 7, 1))

        with self.assertRaisesRegex(ValueError, "명시적인 확인"):
            close_current_month(date(2026, 7, 27))

        result = close_current_month(date(2026, 7, 27), allow_early_close=True)
        self.assertEqual(result["closed_month"], "2026-07")
        self.assertEqual(result["archived"], 1)

    def test_month_close_resets_planned_confirmation_for_next_cycle(self) -> None:
        close_current_month(date(2026, 7, 1))
        with session() as conn:
            planned_id = conn.execute("SELECT id FROM ledger_entries WHERE entry_kind = 'planned'").fetchone()["id"]

        confirm_planned_entry(planned_id, date(2026, 7, 10))
        self.assertFalse(
            any(entry["id"] == planned_id for entry in list_entries("current", date(2026, 7, 10)))
        )

        close_current_month(date(2026, 7, 27), allow_early_close=True)
        self.assertTrue(
            any(entry["id"] == planned_id for entry in list_entries("current", date(2026, 7, 28)))
        )
        with session() as conn:
            planned = conn.execute(
                "SELECT entry_date, confirmed_at, confirmed_month FROM ledger_entries WHERE id = ?",
                (planned_id,),
            ).fetchone()
            archived_generated = conn.execute(
                """
                SELECT source_planned_entry_id
                FROM ledger_entries
                WHERE book_section = 'archive' AND source_planned_entry_id = ?
                """,
                (planned_id,),
            ).fetchone()
        self.assertIsNone(planned["entry_date"])
        self.assertIsNone(planned["confirmed_at"])
        self.assertIsNone(planned["confirmed_month"])
        self.assertEqual(archived_generated["source_planned_entry_id"], planned_id)

        self.assertTrue(
            any(entry["id"] == planned_id for entry in list_entries("current", date(2026, 8, 1)))
        )

    def test_month_close_reactivates_fixed_panel_without_deleting_cash_flow(self) -> None:
        close_current_month(date(2026, 7, 1))
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-07', 'fixed', '현금 보험료', 40000, 1)
                """
            ).lastrowid
        result = confirm_fixed_panel(panel_id, "2026-07-15")
        assert result is not None
        cash_flow_id = result["cash_flow"]["id"]

        close_current_month(date(2026, 7, 27), allow_early_close=True)

        with session() as conn:
            panel = conn.execute(
                """
                SELECT spent_on, confirmed_at, confirmed_cash_flow_id
                FROM monthly_panels WHERE id = ?
                """,
                (panel_id,),
            ).fetchone()
            cash_flow = conn.execute(
                "SELECT amount_value FROM cash_flows WHERE id = ?",
                (cash_flow_id,),
            ).fetchone()
        self.assertIsNone(panel["spent_on"])
        self.assertIsNone(panel["confirmed_at"])
        self.assertIsNone(panel["confirmed_cash_flow_id"])
        self.assertEqual(cash_flow["amount_value"], -40000)

    def test_delayed_close_does_not_reset_later_fixed_expense_confirmation(self) -> None:
        close_current_month(date(2026, 7, 1), target_month="2026-06")
        with session() as conn:
            panel_id = conn.execute(
                """
                INSERT INTO monthly_panels(month, panel_type, title, amount_value, sort_order)
                VALUES ('2026-08', 'fixed', '8월 관리비', 50000, 5)
                """
            ).lastrowid
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-08-05"}):
            get_settings.cache_clear()
            result = confirm_fixed_panel(panel_id, "2026-08-05")
            assert result is not None
            close_current_month(date(2026, 8, 5), target_month="2026-07")
        get_settings.cache_clear()

        with session() as conn:
            panel = conn.execute(
                """
                SELECT confirmed_month, confirmed_cash_flow_id
                FROM monthly_panels WHERE id = ?
                """,
                (panel_id,),
            ).fetchone()
        self.assertEqual(panel["confirmed_month"], "2026-08")
        self.assertEqual(panel["confirmed_cash_flow_id"], result["cash_flow"]["id"])

    def test_confirmed_planned_entry_keeps_actual_payment_date(self) -> None:
        close_current_month(date(2026, 7, 1))
        with session() as conn:
            planned_id = conn.execute(
                "SELECT id FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["id"]
            conn.execute("UPDATE ledger_entries SET due_day = 15 WHERE id = ?", (planned_id,))

        result = confirm_planned_entry(planned_id, date(2026, 7, 10), entry_date="2026-07-17")
        with session() as conn:
            conn.execute(
                "UPDATE ledger_entries SET entry_date = '2026-07-10' WHERE id = ?",
                (planned_id,),
            )
        confirmed = list_confirmed_planned_entries(date(2026, 7, 10))

        self.assertEqual(result["entry"]["entry_date"], "2026-07-17")
        self.assertEqual(confirmed[0]["entry_date"], "2026-07-17")
        self.assertEqual(confirmed[0]["due_day"], 15)
        self.assertEqual(result["entry"]["source_planned_entry_id"], planned_id)

    def test_confirmed_planned_entry_uses_actual_principal_and_keeps_template(self) -> None:
        close_current_month(date(2026, 7, 1))
        with session() as conn:
            planned_id = conn.execute(
                "SELECT id FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["id"]

        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-07-10"}):
            get_settings.cache_clear()
            preview = present_planned_charge_preview(
                {**next(row for row in list_entries("current") if row["id"] == planned_id)},
                32000,
            )
            result = confirm_planned_entry(
                planned_id,
                date(2026, 7, 10),
                entry_date="2026-07-17",
                actual_amount=32000,
            )
            confirmed = present_ledger_entries(
                list_confirmed_planned_entries(date(2026, 7, 10))
            )[0]
        get_settings.cache_clear()

        self.assertEqual(result["planned"]["amount_value"], 30000)
        self.assertEqual(result["entry"]["amount_value"], 32000)
        self.assertEqual(confirmed["amount_value"], 30000)
        self.assertEqual(confirmed["confirmed_amount_value"], 32000)
        self.assertEqual(
            confirmed["confirmed_effective_discount_amount"],
            preview["effective_discount_amount"],
        )
        self.assertEqual(
            confirmed["confirmed_effective_amount_value"],
            preview["effective_amount_value"],
        )

    def test_deleting_confirmed_planned_expense_reactivates_template(self) -> None:
        close_current_month(date(2026, 7, 1))
        with session() as conn:
            planned_id = conn.execute(
                "SELECT id FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["id"]
        result = confirm_planned_entry(
            planned_id,
            date(2026, 7, 10),
            entry_date="2026-07-17",
            actual_amount=28000,
        )

        self.assertTrue(delete_entry(result["entry"]["id"]))

        with session() as conn:
            planned = conn.execute(
                "SELECT amount_value, confirmed_at, confirmed_month FROM ledger_entries WHERE id = ?",
                (planned_id,),
            ).fetchone()
        self.assertEqual(planned["amount_value"], 30000)
        self.assertIsNone(planned["confirmed_at"])
        self.assertIsNone(planned["confirmed_month"])
        self.assertTrue(any(entry["id"] == planned_id for entry in list_entries("current")))

    def test_repeated_planned_confirmation_does_not_create_duplicate_expense(self) -> None:
        close_current_month(date(2026, 7, 1))
        with session() as conn:
            planned_id = conn.execute(
                "SELECT id FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["id"]

        first = confirm_planned_entry(
            planned_id,
            date(2026, 7, 10),
            entry_date="2026-07-17",
            actual_amount=28000,
        )
        with self.assertRaisesRegex(ValueError, "already confirmed"):
            confirm_planned_entry(
                planned_id,
                date(2026, 7, 10),
                entry_date="2026-07-17",
                actual_amount=29000,
            )

        with session() as conn:
            generated_count = conn.execute(
                "SELECT COUNT(*) AS count FROM ledger_entries WHERE source_planned_entry_id = ?",
                (planned_id,),
            ).fetchone()["count"]
        self.assertIsNotNone(first)
        self.assertEqual(generated_count, 1)

    def test_confirmed_planned_entry_ignores_identical_manual_expense(self) -> None:
        close_current_month(date(2026, 7, 1), target_month="2026-06")
        with session() as conn:
            planned_id = conn.execute(
                "SELECT id FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["id"]
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value,
                    sort_order, payment_key
                )
                VALUES ('current', 'expense', '2026-07-03', '정기결제', 30000,
                        4, 'manual-lookalike')
                """
            )

        confirm_planned_entry(
            planned_id,
            date(2026, 7, 10),
            entry_date="2026-07-17",
        )
        confirmed = list_confirmed_planned_entries(date(2026, 7, 10))

        self.assertEqual(confirmed[0]["entry_date"], "2026-07-17")

    def test_deleting_planned_template_keeps_generated_expense(self) -> None:
        close_current_month(date(2026, 7, 1), target_month="2026-06")
        with session() as conn:
            planned_id = conn.execute(
                "SELECT id FROM ledger_entries WHERE entry_kind = 'planned'"
            ).fetchone()["id"]
        result = confirm_planned_entry(
            planned_id,
            date(2026, 7, 10),
            entry_date="2026-07-17",
        )
        generated_id = result["entry"]["id"]

        self.assertTrue(delete_planned_entry(planned_id))

        with session() as conn:
            generated = conn.execute(
                "SELECT source_planned_entry_id FROM ledger_entries WHERE id = ?",
                (generated_id,),
            ).fetchone()
        self.assertIsNotNone(generated)
        self.assertIsNone(generated["source_planned_entry_id"])

    def test_entry_for_closed_month_is_added_to_archive(self) -> None:
        close_current_month(date(2026, 7, 1))
        close_current_month(date(2026, 7, 27), allow_early_close=True)

        entry = create_entry(
            LedgerEntryIn(
                book_section="current",
                entry_kind="expense",
                entry_date="2026-07-31",
                date_label="2026.07.31.",
                title="[카드사] 마감 후 매입",
                usage_place="카드사",
                amount_value=12_345,
                sort_order=99,
            )
        )

        self.assertEqual(entry["book_section"], "archive")
        self.assertEqual(entry["entry_date"], "2026-07-31")


if __name__ == "__main__":
    unittest.main()

from datetime import date
from concurrent.futures import ThreadPoolExecutor
import copy
import os
import signal
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repositories.cash_flows import delete_cash_flow
from app.repositories.entries import confirm_planned_entry
from app.services.month import close_current_month, month_close_status
from app.services.panels import confirm_fixed_panel
from app.services.snapshot import export_snapshot, restore_snapshot
from app.services.summary import current_summary_values
from app.services.presentation import present_monthly_panel
import app.services.snapshot as snapshot_service


class EarlyCashFixedTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {
            "MONEY_NOTE_DB_PATH": str(Path(self.temp.name) / "test.sqlite3"),
            "MONEY_NOTE_TODAY": "2026-09-30",
        })
        self.env.start()
        get_settings.cache_clear()
        init_db()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='1459200' WHERE key='scheduled_income'")
            conn.execute("INSERT INTO app_settings(key,value) VALUES ('last_closed_month','2026-08')")
            self.fixed = conn.execute(
                "INSERT INTO monthly_panels(month,panel_type,title,amount_value,sort_order) "
                "VALUES ('2026-10','fixed','October transfer',820000,1)"
            ).lastrowid
            self.planned = conn.execute(
                "INSERT INTO ledger_entries(book_section,entry_kind,title,amount_value,sort_order,due_day) "
                "VALUES ('current','planned','Card recurring',10000,1,1)"
            ).lastrowid

    def tearDown(self):
        get_settings.cache_clear()
        self.env.stop()
        self.temp.cleanup()

    def close(self):
        return close_current_month(date(2026, 9, 30), target_month="2026-09",
                                   allow_early_close=True, allow_unconfirmed_recurring=True)

    def test_calendar_month_end_matrix(self):
        for day, allowed in [("2026-09-29", False), ("2026-09-30", True),
                             ("2026-02-27", False), ("2026-02-28", True),
                             ("2028-02-28", False), ("2028-02-29", True),
                             ("2026-07-30", False), ("2026-07-31", True)]:
            with self.subTest(day=day):
                with session() as conn:
                    conn.execute("DELETE FROM app_settings WHERE key='last_closed_month'")
                status = month_close_status(date.fromisoformat(day))
                self.assertEqual(status["early_close_available"], allowed)
                if not allowed:
                    with self.assertRaises(ValueError):
                        close_current_month(date.fromisoformat(day), target_month=day[:7],
                                            allow_early_close=True, allow_unconfirmed_recurring=True)

    def test_future_fixed_is_denied_before_close(self):
        with session() as conn:
            panel = dict(conn.execute("SELECT * FROM monthly_panels WHERE id=?", (self.fixed,)).fetchone())
        self.assertFalse(present_monthly_panel(panel)["can_confirm_fixed"])
        with self.assertRaises(ValueError):
            confirm_fixed_panel(self.fixed, "2026-09-30")
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows").fetchone()[0], 0)

    def test_after_close_cash_opens_but_card_does_not_advance(self):
        self.close()
        self.assertFalse(month_close_status()["card_recurring_confirmation_available"])
        with session() as conn:
            panel = dict(conn.execute("SELECT * FROM monthly_panels WHERE id=?", (self.fixed,)).fetchone())
        projected = present_monthly_panel(panel)
        self.assertTrue(projected["can_confirm_fixed"])
        self.assertEqual(projected["fixed_execution_month"], "2026-10")
        with self.assertRaises(ValueError):
            confirm_planned_entry(self.planned, date(2026, 9, 30), entry_date="2026-10-01")
        with self.assertRaises(ValueError):
            confirm_planned_entry(self.planned, date(2026, 9, 30))
        result = confirm_fixed_panel(self.fixed, "2026-09-30")
        self.assertEqual(result["panel"]["confirmed_month"], "2026-10")
        self.assertEqual(result["cash_flow"]["occurred_on"], "2026-09-30")

    def test_early_outflow_replaces_reserve_once_and_roundtrips(self):
        self.close()
        before = current_summary_values()
        self.assertEqual(before["cash_flow_balance"], 1_459_200)
        self.assertEqual(before["remaining_liquidity"], 2_088_400)
        self.assertEqual(before["current_month_spendable"], 2_088_400)
        result = confirm_fixed_panel(self.fixed, "2026-09-30")
        after = current_summary_values()
        self.assertEqual(after["cash_flow_balance"], 639_200)
        self.assertEqual(after["remaining_liquidity"], 2_088_400)
        self.assertEqual(after["current_month_spendable"], before["current_month_spendable"])
        init_db()
        restore_snapshot(export_snapshot()[1])
        self.assertEqual(current_summary_values(), after)
        with self.assertRaises(ValueError):
            confirm_fixed_panel(self.fixed, "2026-09-30")
        self.assertTrue(self.close()["already_closed"])
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows").fetchone()[0], 2)
        delete_cash_flow(result["cash_flow"]["id"])
        self.assertEqual(current_summary_values(), before)

    def test_october_calendar_and_following_recurrence(self):
        self.close()
        result = confirm_fixed_panel(self.fixed, "2026-09-30")
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-10-01"}):
            get_settings.cache_clear()
            init_db()
            self.assertEqual(current_summary_values()["cash_flow_balance"], 639_200)
            # November's reserve now replaces the already-executed October reserve.
            self.assertEqual(current_summary_values()["current_month_spendable"], 1_268_400)
            with self.assertRaises(ValueError):
                confirm_fixed_panel(self.fixed, "2026-10-01")
            confirm_planned_entry(self.planned, date(2026, 10, 1))
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-10-31"}):
            get_settings.cache_clear()
            close_current_month(date(2026, 10, 31), target_month="2026-10", allow_early_close=True)
            before_next = current_summary_values()
            next_result = confirm_fixed_panel(self.fixed, "2026-10-31")
            self.assertEqual(next_result["panel"]["confirmed_month"], "2026-11")
            self.assertEqual(next_result["cash_flow"]["occurred_on"], "2026-10-31")
            after_next = current_summary_values()
            self.assertEqual(after_next["current_month_spendable"], before_next["current_month_spendable"])
            restore_snapshot(export_snapshot()[1])
            init_db()
            self.assertEqual(current_summary_values(), after_next)
            delete_cash_flow(next_result["cash_flow"]["id"])
            self.assertEqual(current_summary_values(), before_next)
        self.assertNotEqual(next_result["cash_flow"]["id"], result["cash_flow"]["id"])

    def test_october_unconfirmed_cash_and_card_are_calendar_eligible(self):
        self.close()
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-10-01"}):
            get_settings.cache_clear()
            self.assertTrue(month_close_status()["card_recurring_confirmation_available"])
            self.assertEqual(confirm_fixed_panel(self.fixed, "2026-10-01")["panel"]["confirmed_month"], "2026-10")
            self.assertEqual(confirm_planned_entry(self.planned)["entry"]["entry_date"], "2026-10-01")

    def test_differing_actual_amount_preserves_template_reserve(self):
        self.close()
        before = current_summary_values()
        confirm_fixed_panel(self.fixed, "2026-09-30", actual_amount=800_000)
        after = current_summary_values()
        self.assertEqual(after["cash_flow_balance"], 659_200)
        self.assertEqual(after["current_month_spendable"], before["current_month_spendable"] + 20_000)
        restore_snapshot(export_snapshot()[1])
        self.assertEqual(current_summary_values(), after)

    def test_response_loss_and_concurrent_confirmation_do_not_duplicate(self):
        self.close()
        def execute(_):
            try:
                return confirm_fixed_panel(self.fixed, "2026-09-30") is not None
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(sum(executor.map(execute, range(2))), 1)
        with self.assertRaises(ValueError):
            confirm_fixed_panel(self.fixed, "2026-09-30")  # committed response lost/retry
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows WHERE amount_value<0").fetchone()[0], 1)

    def test_fixed_write_failure_rolls_back_created_flow(self):
        self.close()
        before = current_summary_values()
        with session() as conn:
            conn.execute("CREATE TRIGGER fail_fixed BEFORE UPDATE ON monthly_panels "
                         "WHEN NEW.confirmed_cash_flow_id IS NOT NULL BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaisesRegex(Exception, "injected"):
            confirm_fixed_panel(self.fixed, "2026-09-30")
        self.assertEqual(current_summary_values(), before)
        with session() as conn:
            self.assertIsNone(conn.execute("SELECT confirmed_cash_flow_id FROM monthly_panels").fetchone()[0])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows").fetchone()[0], 1)

    def test_income_and_post_income_failure_roll_back_close(self):
        for failure_point in ("_record_scheduled_income", "create_month_close_card_payment_batch"):
            with self.subTest(failure_point=failure_point):
                before = export_snapshot()[1]["data"]
                with patch(f"app.services.month.{failure_point}", side_effect=RuntimeError("injected")):
                    with self.assertRaisesRegex(RuntimeError, "injected"):
                        self.close()
                self.assertEqual(export_snapshot()[1]["data"], before)
        self.close()

    def test_invalid_early_snapshot_rejected_without_destination_mutation(self):
        self.close()
        confirm_fixed_panel(self.fixed, "2026-09-30")
        valid = export_snapshot()[1]
        for mutation in ("missing_close", "wrong_period", "not_month_end"):
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(valid)
                panel = bad["data"]["monthly_panels"][0]
                if mutation == "missing_close":
                    bad["data"]["app_settings"] = [row for row in bad["data"]["app_settings"] if row["key"] != "last_closed_month"]
                elif mutation == "wrong_period":
                    panel["confirmed_month"] = "2026-11"
                else:
                    panel["spent_on"] = "2026-09-29"
                    bad["data"]["cash_flows"][-1]["occurred_on"] = "2026-09-29"
                bad["manifest"] = snapshot_service._build_manifest(
                    bad["data"], snapshot_service._manifest_table_columns(bad["manifest"]),
                    policy_context=bad["card_charge_policy"],
                    snapshot_metadata=snapshot_service._snapshot_metadata(bad),
                )
                with self.assertRaises(ValueError):
                    restore_snapshot(bad)
                self.assertEqual(export_snapshot()[1]["data"], valid["data"])

    def test_process_kill_preserves_close_and_fixed_checkpoints_in_delete_and_wal(self):
        for mode in ("DELETE", "WAL"):
            for operation in ("close", "fixed"):
                with self.subTest(mode=mode, operation=operation):
                    with session() as conn:
                        conn.execute("DELETE FROM cash_flows")
                        conn.execute("UPDATE monthly_panels SET spent_on=NULL, confirmed_at=NULL, "
                                     "confirmed_month=NULL, confirmed_cash_flow_id=NULL")
                        conn.execute("UPDATE app_settings SET value='2026-08' WHERE key='last_closed_month'")
                    # Journal mode is configured outside the write transaction.
                    with session() as conn:
                        conn.execute(f"PRAGMA journal_mode={mode}")
                    if operation == "fixed":
                        self.close()
                    before = export_snapshot()[1]["data"]
                    script = '''
import os, signal
from contextlib import contextmanager
from unittest.mock import patch
from app.db import session
from app.services.month import close_current_month
from app.services.panels import confirm_fixed_panel
from datetime import date
def trace(sql):
    if (os.environ['AUDIT_OPERATION'] == 'fixed' and 'UPDATE monthly_panels' in sql) or (
        os.environ['AUDIT_OPERATION'] == 'close' and 'INSERT INTO card_payment_batches' in sql):
        os.kill(os.getpid(), signal.SIGKILL)
@contextmanager
def traced_session(**kwargs):
    with session(**kwargs) as conn:
        conn.set_trace_callback(trace)
        yield conn
if os.environ['AUDIT_OPERATION'] == 'close':
    with patch('app.db.session', traced_session):
        close_current_month(date(2026,9,30), target_month='2026-09', allow_early_close=True, allow_unconfirmed_recurring=True)
else:
    with traced_session(transaction_mode='IMMEDIATE') as conn:
        confirm_fixed_panel(int(os.environ['AUDIT_PANEL']), '2026-09-30', conn=conn)
'''
                    result = subprocess.run(
                        [sys.executable, "-c", script], capture_output=True,
                        env={**os.environ, "AUDIT_OPERATION": operation, "AUDIT_PANEL": str(self.fixed)},
                        timeout=20,
                    )
                    self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr.decode())
                    init_db()
                    self.assertEqual(export_snapshot()[1]["data"], before)
                    with session() as conn:
                        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 3)

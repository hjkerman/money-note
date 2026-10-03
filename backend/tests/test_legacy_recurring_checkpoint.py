"""Synthetic historical rows only; no production data or content fixtures."""

import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.services import snapshot
from app.services.summary import current_summary_values
from app.services.recurring_compatibility import canonicalize_legacy_recurring
from tests.db_fixture import IsolatedDatabaseTestCase


class LegacyRecurringCheckpointTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.clock = patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-07-11"})
        self.clock.start()
        get_settings.cache_clear()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='100000' WHERE key='cash_flow_balance'")
            conn.execute("UPDATE app_settings SET value='0' WHERE key='scheduled_income'")
            conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,title,amount_value,"
                         "sort_order,confirmed_month,confirmed_at,entry_date,created_at) VALUES "
                         "(10,'current','planned','Synthetic subscription',5000,1,'2026-07',"
                         "'2026-07-11 00:00:00','2026-07-11','2026-01-01 00:00:00')")
            conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,title,amount_value,"
                         "sort_order,source_planned_entry_id,payment_key,entry_date,created_at,"
                         "confirmed_month,confirmed_at) VALUES "
                         "(21,'current','expense','Synthetic purchase',5000,2,10,'synthetic-active',"
                         "'2026-07-11','2026-07-11 00:00:00','2026-07','2026-07-11 00:00:00')")
        self.canonical = snapshot.export_snapshot()[1]
        # Compatibility needs a complete, previously preserved ownership
        # relation. Epoch-less/timestamp-only documents cannot supply it.
        directory = self.db_path.parent / "snapshot-backups"
        directory.mkdir(exist_ok=True)
        (directory / "pre_restore-20260711T000000Z.money-note-snapshot.json").write_text(json.dumps(self.canonical))

    def tearDown(self):
        self.clock.stop()
        super().tearDown()

    def historical(self, artifact=None):
        result = copy.deepcopy(artifact or self.canonical)
        result.pop("recurring_ownership_version", None)
        for row in result["data"]["ledger_entries"]:
            if row.get("source_planned_entry_id") is not None:
                row.update(confirmed_month=None, confirmed_at=None)
        return self.resign(result)

    def resign(self, artifact):
        artifact["manifest"] = snapshot._build_manifest(artifact["data"],
            policy_context=artifact["card_charge_policy"],
            snapshot_metadata=snapshot._snapshot_metadata(artifact))
        artifact["snapshot_id"] = artifact["manifest"]["content_sha256"]
        return artifact

    def state(self):
        with sqlite3.connect(self.db_path) as conn:
            return tuple(conn.iterdump()), conn.execute("PRAGMA user_version").fetchone()[0]

    def make_legacy_db(self):
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE id=21")
            conn.execute("PRAGMA user_version=3")

    def add_retired(self, *, active_location="current", old_location="archive"):
        old = copy.deepcopy(self.canonical)
        for row in old["data"]["ledger_entries"]:
            row.update(confirmed_month="2026-06", confirmed_at="2026-06-11 00:00:00")
            if row["id"] == 21:
                row.update(id=120, payment_key="synthetic-retired", created_at="2026-06-11 00:00:00")
        witness = self.resign(old)
        directory = self.db_path.parent / "snapshot-backups"
        directory.mkdir(exist_ok=True)
        (directory / "pre_restore-20260630T090000Z.money-note-snapshot.json").write_text(json.dumps(witness))
        with session() as conn:
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES ('last_closed_month','2026-06')")
            conn.execute("UPDATE ledger_entries SET book_section=? WHERE id=21", (active_location,))
            conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,title,amount_value,"
                         "sort_order,source_planned_entry_id,payment_key,entry_date,created_at) VALUES "
                         "(20,?,'expense','Different mutable text',7000,3,10,'synthetic-retired',"
                         "'2026-05-01','2026-06-30 09:00:00')", (old_location,))
        return witness

    def test_version3_active_checkpoint_preserves_money_and_is_one_time(self):
        expected = current_summary_values()
        self.make_legacy_db()
        init_db()
        self.assertEqual(current_summary_values(), expected)
        self.assertEqual(self.state()[1], 4)
        first = self.state()
        init_db()
        init_db()
        self.assertEqual(self.state(), first)

    def test_historical_v7_canonical_witness_then_canonical_round_trip(self):
        expected = current_summary_values()
        snapshot.restore_snapshot(self.historical())
        self.assertEqual(current_summary_values(), expected)
        init_db()
        current = snapshot.export_snapshot()[1]
        self.assertEqual(current["recurring_ownership_version"], 1)
        snapshot.restore_snapshot(current)
        self.assertEqual(current_summary_values(), expected)

    def test_retired_identity_uses_witness_key_not_row_id_content_or_location(self):
        self.add_retired()
        self.make_legacy_db()
        init_db()
        with session() as conn:
            row = conn.execute("SELECT * FROM ledger_entries WHERE id=20").fetchone()
            self.assertEqual((row["confirmed_month"], row["confirmed_at"]),
                             ("2026-06", "2026-06-11 00:00:00"))
            self.assertEqual(row["amount_value"], 7000)
            self.assertEqual(row["entry_date"], "2026-05-01")
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])

    def test_missing_or_conflicting_witness_preserves_checkpoint(self):
        witness = self.add_retired()
        self.make_legacy_db()
        directory = self.db_path.parent / "snapshot-backups"
        for case in ("missing", "conflicting", "tampered"):
            with self.subTest(case=case):
                original = directory / "pre_restore-20260630T090000Z.money-note-snapshot.json"
                original.write_text(json.dumps(witness))
                second = directory / "pre_restore-20260630T090001Z.money-note-snapshot.json"
                second.unlink(missing_ok=True)
                if case == "missing":
                    original.unlink()
                elif case == "tampered":
                    changed = copy.deepcopy(witness)
                    changed["data"]["ledger_entries"][0]["confirmed_at"] = "2026-06-12 00:00:00"
                    original.write_text(json.dumps(changed))
                else:
                    changed = copy.deepcopy(witness)
                    for row in changed["data"]["ledger_entries"]:
                        if row["entry_kind"] == "planned":
                            row["confirmed_at"] = "2026-06-12 00:00:00"
                        else:
                            row["created_at"] = "2026-06-12 00:00:00"
                    second.write_text(json.dumps(self.resign(changed)))
                before = self.state()
                with self.assertRaises(ValueError):
                    init_db()
                self.assertEqual(self.state(), before)

    def test_proven_retired_epoch_is_not_a_competing_new_confirmation(self):
        # Old month close copied the expense with a new creation timestamp.
        # An immediate next confirmation can therefore share that second.
        self.add_retired()
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET created_at='2026-07-11 00:00:00' WHERE id=20")
        self.make_legacy_db()
        init_db()
        with session() as conn:
            epochs = dict(conn.execute("SELECT id,confirmed_month FROM ledger_entries WHERE entry_kind='expense'"))
        self.assertEqual(epochs, {20: "2026-06", 21: "2026-07"})
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])

    def test_current_snapshot_missing_epoch_is_not_legacy(self):
        bad = copy.deepcopy(self.canonical)
        for row in bad["data"]["ledger_entries"]:
            if row["entry_kind"] == "expense":
                row.update(confirmed_month=None, confirmed_at=None)
        before = self.state()
        with self.assertRaises(ValueError):
            snapshot.restore_snapshot(self.resign(bad))
        self.assertEqual(self.state(), before)

    def test_current_db_corruption_cannot_repeat_legacy_checkpoint(self):
        self.make_legacy_db()
        init_db()
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE id=21")
        before = self.state()
        with self.assertRaises(ValueError):
            init_db()
        self.assertEqual(self.state(), before)

    def test_creation_timestamp_is_irrelevant_with_canonical_witness(self):
        # Even a nonadjacent creation timestamp cannot alter stable ownership.
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET created_at='2026-07-12 23:59:59' WHERE id=21")
        self.make_legacy_db()
        init_db()
        with session() as conn:
            row = conn.execute("SELECT confirmed_month,confirmed_at FROM ledger_entries WHERE id=21").fetchone()
        self.assertEqual(tuple(row), ("2026-07", "2026-07-11 00:00:00"))

    def test_ambiguity_matrix_never_changes_input_or_destination(self):
        for case in ("duplicate", "missing_source", "manual_lookalike", "partial_source",
                     "partial_child", "missing_key", "empty_key", "duplicate_key", "wrong_source"):
            with self.subTest(case=case):
                bad = self.historical()
                source = next(row for row in bad["data"]["ledger_entries"] if row["id"] == 10)
                child = next(row for row in bad["data"]["ledger_entries"] if row["id"] == 21)
                if case == "duplicate":
                    bad["data"]["ledger_entries"].append({**child, "id": 22, "payment_key": "second-candidate"})
                elif case == "missing_source":
                    bad["data"]["ledger_entries"].remove(source)
                elif case == "manual_lookalike":
                    child["source_planned_entry_id"] = None
                    child["payment_key"] = "unproven-manual-key"
                elif case == "partial_source":
                    source["confirmed_at"] = None
                elif case == "partial_child":
                    child["confirmed_month"] = "2026-07"
                elif case == "missing_key":
                    child["payment_key"] = None
                elif case == "empty_key":
                    child["payment_key"] = ""
                elif case == "duplicate_key":
                    bad["data"]["ledger_entries"].append({**child, "id": 22})
                elif case == "wrong_source":
                    child["source_planned_entry_id"] = 999
                original = copy.deepcopy(bad)
                before = self.state()
                with self.assertRaises(ValueError):
                    snapshot.restore_snapshot(self.resign(bad))
                self.assertEqual(bad["data"], original["data"])
                self.assertEqual(self.state(), before)

    def test_metadata_only_pure_transformation_and_no_text_or_date_evidence(self):
        bad = self.historical()
        child = next(row for row in bad["data"]["ledger_entries"] if row["id"] == 21)
        child.update(book_section="archive", entry_date=None, title="Changed", usage_place="Other",
                     usage_item="Edited", amount_value=7000, aux_amount_value=120, discount_override=1)
        original = copy.deepcopy(bad["data"])
        rows = canonicalize_legacy_recurring(bad["data"], [self.canonical["data"]])
        self.assertEqual(bad["data"], original)
        self.assertEqual(next(row for row in rows if row["id"] == 21)["amount_value"], 7000)
        snapshot.restore_snapshot(self.resign(bad))
        from app.repositories.entries import list_confirmed_planned_entries
        actual = list_confirmed_planned_entries()[0]["_confirmed_expense"]
        self.assertEqual((actual["id"], actual["amount_value"], actual["aux_amount_value"]), (21, 7000, 120))

    def test_upgrade_failure_before_after_writes_and_before_checkpoint_is_atomic(self):
        self.add_retired()
        self.make_legacy_db()
        from app.services import recurring_compatibility as compat
        from app import db_migrations as migrations
        for stage in ("before", "first", "second", "checkpoint"):
            with self.subTest(stage=stage):
                before = self.state()
                original_write, original_validate = compat._write_epoch, migrations._validate_current_schema
                count = 0
                validation_count = 0

                def write(conn, row):
                    nonlocal count
                    if stage == "before":
                        raise RuntimeError("before first backfill")
                    original_write(conn, row)
                    count += 1
                    if (stage == "first" and count == 1) or (stage == "second" and count == 2):
                        raise RuntimeError("after backfill")

                def validate(conn, schema):
                    nonlocal validation_count
                    validation_count += 1
                    if stage == "checkpoint" and validation_count == 3:
                        raise RuntimeError("before checkpoint")
                    original_validate(conn, schema)

                with patch.object(compat, "_write_epoch", write), patch.object(migrations, "_validate_current_schema", validate):
                    with self.assertRaises(RuntimeError):
                        init_db()
                self.assertEqual(self.state(), before)
        init_db()
        self.assertEqual(self.state()[1], 4)

    def test_unsupported_money_cannot_be_coerced_by_checkpoint(self):
        self.make_legacy_db()
        for amount in (-0.5, 2**53 + 1):
            with self.subTest(amount=amount):
                with session() as conn:
                    conn.execute("UPDATE ledger_entries SET amount_value=? WHERE id=21", (amount,))
                before = self.state()
                with self.assertRaises(ValueError):
                    init_db()
                self.assertEqual(self.state(), before)

    def test_capability_is_manifest_bound_and_invalid_generations_reject(self):
        bad = copy.deepcopy(self.canonical)
        bad.pop("recurring_ownership_version")
        before = self.state()
        with self.assertRaisesRegex(ValueError, "manifest mismatch"):
            snapshot.restore_snapshot(bad)
        for version in (True, 0, 2, None):
            bad = copy.deepcopy(self.canonical)
            bad["recurring_ownership_version"] = version
            with self.assertRaisesRegex(ValueError, "ownership contract"):
                snapshot.restore_snapshot(self.resign(bad))
        self.assertEqual(self.state(), before)

    def test_current_archive_combinations_and_old_cancel_do_not_release_active(self):
        from app.repositories.entries import delete_entry

        for active, old in (("current", "archive"), ("archive", "current")):
            with self.subTest(active=active, old=old):
                snapshot.restore_snapshot(self.canonical)
                self.add_retired(active_location=active, old_location=old)
                self.make_legacy_db()
                init_db()
                snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                self.assertTrue(delete_entry(20))
                with session() as conn:
                    owner = conn.execute("SELECT confirmed_month,confirmed_at FROM ledger_entries WHERE id=10").fetchone()
                self.assertEqual(tuple(owner), ("2026-07", "2026-07-11 00:00:00"))

    def test_retired_source_reset_then_new_confirmation(self):
        from app.repositories.entries import confirm_planned_entry

        self.add_retired()
        with session() as conn:
            conn.execute("DELETE FROM ledger_entries WHERE id=21")
            conn.execute("UPDATE ledger_entries SET confirmed_at=NULL,confirmed_month=NULL,entry_date=NULL WHERE id=10")
            conn.execute("PRAGMA user_version=3")
        init_db()
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)
        confirm_planned_entry(10)
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])

    def test_upgraded_actual_edit_archive_cancel_and_reconfirm(self):
        from app.repositories.entries import confirm_planned_entry, delete_entry, list_confirmed_planned_entries, update_entry
        from app.schemas import LedgerEntryPatch
        from datetime import date

        with session() as conn:
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES ('last_closed_month','2026-06')")
        self.make_legacy_db()
        init_db()
        update_entry(21, LedgerEntryPatch(amount_value=7000, entry_date=date(2026, 6, 12),
                                          title="Edited actual", usage_place="Synthetic shop"))
        init_db()
        actual = list_confirmed_planned_entries()[0]["_confirmed_expense"]
        self.assertEqual(actual["amount_value"], 7000)
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        self.assertTrue(delete_entry(21))
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)
        confirm_planned_entry(10)
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])

    def test_witness_owner_reuse_is_not_admitted(self):
        witness = self.add_retired()
        self.make_legacy_db()
        for row in witness["data"]["ledger_entries"]:
            if row["entry_kind"] == "planned":
                row["created_at"] = "2026-01-02 00:00:00"
        path = self.db_path.parent / "snapshot-backups/pre_restore-20260630T090000Z.money-note-snapshot.json"
        path.write_text(json.dumps(self.resign(witness)))
        before = self.state()
        with self.assertRaisesRegex(ValueError, "contradicts"):
            init_db()
        self.assertEqual(self.state(), before)

    def test_historical_baseline_mobile_wins_retry_preserves_request_identity(self):
        from app.schemas import OfflineMobileWinsIn
        from app.services.offline_reconciliation import apply_mobile_wins
        from app.services.snapshot import snapshot_state_fingerprint

        baseline = self.historical()
        original = copy.deepcopy(baseline)
        fingerprint = snapshot_state_fingerprint(baseline)
        current = snapshot_state_fingerprint(snapshot.export_snapshot()[1])
        payload = OfflineMobileWinsIn(schema_version=1, reconciliation_id="synthetic-legacy-reconcile",
            baseline_fingerprint=fingerprint, baseline_snapshot=baseline,
            operations=[{"schema_version": 1, "operation_id": "synthetic-cash-operation", "sequence": 1,
                         "operation_type": "CREATE_CASH_FLOW", "status": "pending",
                         "created_at": "2026-07-11T01:00:00Z",
                         "payload": {"occurred_on": "2026-07-11", "title": "Synthetic cash", "amount_value": -5000, "is_primary_income": 0}}],
            mobile_artifact_sha256="a" * 64, expected_server_fingerprint=current,
            confirm_server_changed=True, password="synthetic-only-password")
        before = current_summary_values()

        def fail(stage, sequence):
            if stage == "before_commit":
                raise RuntimeError("simulated replay rollback")

        with self.assertRaises(RuntimeError):
            apply_mobile_wins(payload, failure_injector=fail)
        self.assertEqual(current_summary_values(), before)
        first = apply_mobile_wins(payload)
        retried = apply_mobile_wins(payload)
        self.assertEqual(first, retried)
        self.assertEqual(baseline, original)
        self.assertEqual(current_summary_values()["cash_flow_balance"], 95000)
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows").fetchone()[0], 1)

    def test_process_kill_before_checkpoint_commit_delete_and_wal(self):
        for mode in ("DELETE", "WAL"):
            with self.subTest(mode=mode):
                self.make_legacy_db()
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(f"PRAGMA journal_mode={mode}")
                before = self.state()
                script = """
import sys
from app import db_migrations as m
from app.db import init_db
original=m.MIGRATIONS[3]
def stop(conn,schema):
    original(conn,schema)
    print('uncommitted',flush=True)
    sys.stdin.read()
m.MIGRATIONS=(*m.MIGRATIONS[:3],stop)
init_db()
"""
                process = subprocess.Popen([sys.executable, "-c", script], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    cwd=Path(__file__).resolve().parents[1])
                try:
                    self.assertEqual(process.stdout.readline().strip(), "uncommitted")
                finally:
                    process.kill()
                    process.communicate(timeout=10)
                self.assertEqual(self.state(), before)
                init_db()
                self.assertEqual(self.state()[1], 4)

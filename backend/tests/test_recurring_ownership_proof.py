"""Ownership proofs, not timestamps/content; all states are synthetic."""

import copy
import itertools
import json
import os
import sqlite3
from unittest.mock import patch

from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import confirm_planned_entry, delete_entry, list_confirmed_planned_entries, update_entry
from app.schemas import LedgerEntryPatch
from app.services import snapshot
from app.services.recurring_compatibility import canonicalize_legacy_recurring
from app.services.summary import current_summary_values
from tests.db_fixture import IsolatedDatabaseTestCase


class RecurringOwnershipProofTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.clock = patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-07-11"})
        self.clock.start()
        get_settings.cache_clear()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='100000' WHERE key='cash_flow_balance'")
            conn.execute("UPDATE app_settings SET value='0' WHERE key='scheduled_income'")
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES ('last_closed_month','2026-06')")
            conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,title,amount_value,sort_order,"
                         "confirmed_month,confirmed_at,entry_date,created_at) VALUES "
                         "(10,'current','planned','Synthetic source',5000,1,'2026-07',"
                         "'2026-07-11 00:00:00','2026-07-11','2026-01-01 00:00:00')")
            conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,title,amount_value,sort_order,"
                         "source_planned_entry_id,payment_key,entry_date,created_at,confirmed_month,confirmed_at) VALUES "
                         "(21,'current','expense','Synthetic actual',5000,2,10,'active-key','2026-07-11',"
                         "'2026-07-11 00:00:00','2026-07','2026-07-11 00:00:00'),"
                         "(20,'archive','expense','Synthetic old actual',5000,3,10,'retired-key','2026-06-11',"
                         "'2026-07-11 00:00:00','2026-06','2026-06-11 00:00:00')")
        self.canonical = snapshot.export_snapshot()[1]
        self.assertEqual(current_summary_values()["card_total"], 4940)

    def tearDown(self):
        self.clock.stop()
        super().tearDown()

    def state(self):
        with sqlite3.connect(self.db_path) as conn:
            return tuple(conn.iterdump()), conn.execute("PRAGMA user_version").fetchone()[0]

    def historical(self, *, missing_child=False):
        artifact = copy.deepcopy(self.canonical)
        artifact.pop("recurring_ownership_version")
        for row in artifact["data"]["ledger_entries"]:
            if row["entry_kind"] == "expense":
                row.update(confirmed_month=None, confirmed_at=None)
            if row["id"] == 21:
                row["source_planned_entry_id"] = None
        if missing_child:
            artifact["data"]["ledger_entries"] = [r for r in artifact["data"]["ledger_entries"] if r["id"] != 21]
        artifact["manifest"] = snapshot._build_manifest(artifact["data"],
            policy_context=artifact["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(artifact))
        artifact["snapshot_id"] = artifact["manifest"]["content_sha256"]
        return artifact

    def test_collision_with_source_less_new_child_restore_rejected_atomically(self):
        before = self.state()
        with self.assertRaises(ValueError):
            snapshot.restore_snapshot(self.historical())
        self.assertEqual(self.state(), before)

    def test_collision_with_missing_new_child_restore_rejected_atomically(self):
        before = self.state()
        with self.assertRaises(ValueError):
            snapshot.restore_snapshot(self.historical(missing_child=True))
        self.assertEqual(self.state(), before)

    def test_collision_startup_rejects_before_checkpoint_and_financial_mutation(self):
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE entry_kind='expense'")
            conn.execute("UPDATE ledger_entries SET source_planned_entry_id=NULL WHERE id=21")
            conn.execute("PRAGMA user_version=3")
        before = self.state()
        with self.assertRaises(ValueError):
            init_db()
        self.assertEqual(self.state(), before)

    def test_unversioned_collision_rejects_before_any_migration_checkpoint(self):
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE entry_kind='expense'")
            conn.execute("UPDATE ledger_entries SET source_planned_entry_id=NULL WHERE id=21")
            conn.execute("PRAGMA user_version=0")
        before = self.state()
        with self.assertRaises(ValueError):
            init_db()
        self.assertEqual(self.state(), before)

    def test_legacy_source_less_content_timestamp_collision_is_not_proof(self):
        for version in (4, 5, 6):
            with self.subTest(version=version):
                bad = self.historical()
                bad["schema_version"] = version
                for row in bad["data"]["ledger_entries"]:
                    if row["entry_kind"] == "expense":
                        row["source_planned_entry_id"] = None
                    if row["id"] == 20:
                        row.update(book_section="current", title="Synthetic source",
                                   entry_date="2026-07-11", amount_expr="5000",
                                   updated_at="2026-07-11 00:00:00")
                    if row["id"] == 21:
                        row["book_section"] = "archive"
                bad["manifest"] = snapshot._build_manifest(bad["data"],
                    policy_context=bad["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(bad))
                bad["snapshot_id"] = bad["manifest"]["content_sha256"]
                before = self.state()
                with self.assertRaises(ValueError):
                    snapshot.restore_snapshot(bad)
                self.assertEqual(self.state(), before)

    def test_incomplete_witness_cannot_hide_conflicting_stable_source_claim(self):
        target = self.historical()["data"]
        other = copy.deepcopy(self.canonical["data"])
        other["ledger_entries"] = [r for r in other["ledger_entries"] if r["id"] != 20]
        for row in other["ledger_entries"]:
            if row["id"] == 10:
                row["id"] = 99
            else:
                row.update(source_planned_entry_id=99, confirmed_month=None, confirmed_at=None)
        with self.assertRaises(ValueError):
            canonicalize_legacy_recurring(target, [self.canonical["data"], other])

    def test_existing_complete_child_cannot_hide_contradictory_epoch_witness(self):
        target = self.historical()["data"]
        old = next(r for r in target["ledger_entries"] if r["id"] == 20)
        old.update(confirmed_month="2026-06", confirmed_at="2026-06-11 00:00:00")
        other = copy.deepcopy(self.canonical["data"])
        next(r for r in other["ledger_entries"] if r["id"] == 20).update(
            confirmed_month="2026-05", confirmed_at="2026-05-11 00:00:00")
        with self.assertRaises(ValueError):
            canonicalize_legacy_recurring(target, [other])

    def preserve_witness(self):
        directory = self.db_path.parent / "snapshot-backups"
        directory.mkdir(exist_ok=True)
        (directory / "pre_restore-20260711T000000Z.money-note-snapshot.json").write_text(json.dumps(self.canonical))

    def test_timestamp_and_content_alone_never_prove_an_epoch(self):
        for location, seconds in itertools.product(("current", "archive"), (-1, 0, 1)):
            with self.subTest(location=location, seconds=seconds):
                data = self.historical()["data"]
                data["ledger_entries"] = [r for r in data["ledger_entries"] if r["id"] != 21]
                old = next(r for r in data["ledger_entries"] if r["id"] == 20)
                old.update(book_section=location, title="Synthetic source", entry_date="2026-07-11")
                old["created_at"] = { -1: "2026-07-10 23:59:59", 0: "2026-07-11 00:00:00",
                                      1: "2026-07-11 00:00:01"}[seconds]
                before = copy.deepcopy(data)
                with self.assertRaises(ValueError):
                    canonicalize_legacy_recurring(data, [copy.deepcopy(data)])
                self.assertEqual(data, before)

    def test_canonical_proof_is_independent_of_row_order_content_and_location(self):
        for active_location, old_location in itertools.product(("current", "archive"), repeat=2):
            for ordered in itertools.permutations(self.historical()["data"]["ledger_entries"]):
                data = copy.deepcopy(self.historical()["data"])
                data["ledger_entries"] = copy.deepcopy(list(ordered))
                for row in data["ledger_entries"]:
                    if row["entry_kind"] == "expense":
                        row.update(title="Same content", usage_place="Same shop", usage_item="Same item",
                                   entry_date=None, created_at="2026-07-11 00:00:00")
                        row["book_section"] = active_location if row["id"] == 21 else old_location
                before = copy.deepcopy(data)
                normalized = canonicalize_legacy_recurring(data, [self.canonical["data"]])
                self.assertEqual(data, before)
                expected = {"retired-key": (10, "2026-06", "2026-06-11 00:00:00"),
                            "active-key": (10, "2026-07", "2026-07-11 00:00:00")}
                self.assertEqual({r["payment_key"]: (r["source_planned_entry_id"], r["confirmed_month"], r["confirmed_at"])
                                  for r in normalized if r["entry_kind"] == "expense"}, expected)

    def test_historical_versions_with_immutable_key_proof_roundtrip_and_exact_cancel(self):
        self.preserve_witness()
        for version in (4, 5, 6, 7):
            with self.subTest(version=version):
                bad = self.historical()
                bad["schema_version"] = version
                bad["manifest"] = snapshot._build_manifest(bad["data"],
                    policy_context=bad["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(bad))
                bad["snapshot_id"] = bad["manifest"]["content_sha256"]
                snapshot.restore_snapshot(bad)
                self.assertEqual(current_summary_values()["card_total"], 4940)
                init_db()
                update_entry(21, LedgerEntryPatch(title="Edited", usage_place="Synthetic shop", amount_value=7000,
                                                entry_date="2026-08-01"))
                snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                init_db()
                self.assertEqual(list_confirmed_planned_entries()[0]["_confirmed_expense"]["amount_value"], 7000)
                self.assertTrue(delete_entry(20))
                with session() as conn:
                    self.assertEqual(conn.execute("SELECT confirmed_month FROM ledger_entries WHERE id=10").fetchone()[0], "2026-07")
                self.assertTrue(delete_entry(21))
                self.assertEqual(current_summary_values()["remaining_liquidity"], 95000)
                confirm_planned_entry(10)
                self.assertEqual(current_summary_values()["card_total"], 4940)
                snapshot.restore_snapshot(snapshot.export_snapshot()[1])

    def test_source_less_startup_uses_canonical_witness_only_and_is_one_time(self):
        self.preserve_witness()
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE entry_kind='expense'")
            conn.execute("UPDATE ledger_entries SET source_planned_entry_id=NULL WHERE id=21")
            conn.execute("PRAGMA user_version=3")
        init_db()
        first = self.state()
        self.assertEqual(first[1], 4)
        self.assertEqual(current_summary_values()["card_total"], 4940)
        init_db()
        self.assertEqual(self.state(), first)

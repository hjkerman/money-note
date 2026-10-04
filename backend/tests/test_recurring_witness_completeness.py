"""Complete evidence sets for synthetic historical recurring ownership."""

import copy
import itertools
import json
import os
import sqlite3
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import require_user
from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import append_planned_entry, confirm_planned_entry
from app.routers import admin
from app.schemas import PlannedEntryIn
from app.services import snapshot
from app.services.recurring_compatibility import canonicalize_legacy_recurring
from app.services.summary import current_summary_values
from tests.db_fixture import IsolatedDatabaseTestCase


class RecurringWitnessCompletenessTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.clock = patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-07-11"})
        self.clock.start()
        get_settings.cache_clear()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='100000' WHERE key='cash_flow_balance'")
            conn.execute("UPDATE app_settings SET value='0' WHERE key='scheduled_income'")
        source = append_planned_entry(PlannedEntryIn(title="Synthetic recurring", usage_place="Synthetic shop", amount_value=5000, due_day=11))
        self.source_id = source["id"]
        self.child_id = confirm_planned_entry(self.source_id)["entry"]["id"]
        self.canonical = snapshot.export_snapshot()[1]
        self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)
        self.directory = self.db_path.parent / "snapshot-backups"
        self.directory.mkdir(exist_ok=True)
        self.save_witness(self.canonical, "20260711T000000Z")

    def tearDown(self):
        self.clock.stop()
        super().tearDown()

    def state(self):
        with sqlite3.connect(self.db_path) as conn:
            return tuple(conn.iterdump()), conn.execute("PRAGMA user_version").fetchone()[0]

    def resign(self, document):
        document["manifest"] = snapshot._build_manifest(document["data"],
            policy_context=document["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(document))
        document["snapshot_id"] = document["manifest"]["content_sha256"]
        return document

    def child(self, document):
        return next(row for row in document["data"]["ledger_entries"] if row["id"] == self.child_id)

    def historical(self):
        document = copy.deepcopy(self.canonical)
        document.pop("recurring_ownership_version")
        self.child(document).update(confirmed_month=None, confirmed_at=None)
        return self.resign(document)

    def null_source(self, case):
        document = copy.deepcopy(self.canonical)
        document.pop("recurring_ownership_version")
        child = self.child(document)
        child["source_planned_entry_id"] = None
        if case == "partial":
            child["confirmed_at"] = None
        elif case == "partial_time":
            child["confirmed_month"] = None
        elif case == "conflicting":
            child.update(confirmed_month="2026-06", confirmed_at="2026-06-11 00:00:00")
        elif case == "conflicting_time":
            child["confirmed_at"] = "2026-07-11 00:00:00"
        elif case == "absent":
            child.update(confirmed_month=None, confirmed_at=None)
        elif case == "unrelated":
            child.update(payment_key="unrelated-manual-key", confirmed_month=None, confirmed_at=None)
        elif case == "wrong_kind":
            child["entry_kind"] = "planned"
        return self.resign(document)

    def save_witness(self, document, stamp):
        (self.directory / f"pre_restore-{stamp}.money-note-snapshot.json").write_text(json.dumps(document))

    def test_null_source_partial_or_conflicting_epoch_restore_http_rejects_unchanged(self):
        app = FastAPI()
        app.include_router(admin.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        with TestClient(app, raise_server_exceptions=False) as client, patch.object(admin, "verify_user_password", return_value=True):
            for case in ("partial", "conflicting"):
                with self.subTest(case=case):
                    self.save_witness(self.null_source(case), "20260711T000001Z")
                    before, files = self.state(), {path.name: path.read_bytes() for path in self.directory.iterdir()}
                    response = client.post("/api/admin/snapshot/restore", json={"password": "synthetic", "snapshot": self.historical()})
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(self.state(), before)
                    self.assertEqual({path.name: path.read_bytes() for path in self.directory.iterdir()}, files)

    def test_null_source_partial_or_conflicting_epoch_startup_rejects_before_checkpoint(self):
        for case in ("partial", "conflicting"):
            for version in (0, 3):
                with self.subTest(case=case, version=version):
                    self.save_witness(self.null_source(case), "20260711T000001Z")
                    with session() as conn:
                        conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE id=?", (self.child_id,))
                        conn.execute(f"PRAGMA user_version={version}")
                    before = self.state()
                    for _ in range(2):
                        with self.assertRaises(ValueError):
                            init_db()
                        self.assertEqual(self.state(), before)

    def test_same_key_null_source_cannot_hide_different_child_kind(self):
        with self.assertRaises(ValueError):
            canonicalize_legacy_recurring(self.historical()["data"],
                [self.canonical["data"], self.null_source("wrong_kind")["data"]])

    def test_null_source_evidence_matrix(self):
        target, canonical = self.historical()["data"], self.canonical["data"]
        expected = canonicalize_legacy_recurring(target, [canonical])
        for case in ("absent", "same", "unrelated"):
            with self.subTest(case=case):
                additional = self.null_source(case)["data"]
                self.assertEqual(canonicalize_legacy_recurring(target, [additional, canonical]), expected)
                # Missing owner never positively proves one, even if epoch matches.
                with self.assertRaises(ValueError):
                    canonicalize_legacy_recurring(target, [additional])
        for case in ("partial", "partial_time", "conflicting", "conflicting_time"):
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    canonicalize_legacy_recurring(target, [canonical, self.null_source(case)["data"]])

    def test_all_witness_orders_and_locations_have_identical_outcome(self):
        target, canonical = self.historical()["data"], self.canonical["data"]
        expected = canonicalize_legacy_recurring(target, [canonical])
        for case, location in itertools.product(("absent", "same", "partial", "conflicting"), ("current", "archive")):
            documents = [copy.deepcopy(canonical), self.null_source("absent")["data"], self.null_source(case)["data"]]
            for document in documents:
                next(row for row in document["ledger_entries"] if row["id"] == self.child_id)["book_section"] = location
            for ordered in itertools.permutations(documents):
                with self.subTest(case=case, location=location, order=[id(doc) for doc in ordered]):
                    before = copy.deepcopy((target, ordered))
                    if case in ("partial", "conflicting"):
                        with self.assertRaises(ValueError):
                            canonicalize_legacy_recurring(target, ordered)
                    else:
                        self.assertEqual(canonicalize_legacy_recurring(target, ordered), expected)
                    self.assertEqual((target, ordered), before)

    def test_duplicate_same_key_across_current_archive_cannot_hide_null_source(self):
        witness = self.null_source("absent")["data"]
        child = next(row for row in witness["ledger_entries"] if row["id"] == self.child_id)
        witness["ledger_entries"].append({**child, "id": 999, "book_section": "archive"})
        with self.assertRaises(ValueError):
            canonicalize_legacy_recurring(self.historical()["data"], [self.canonical["data"], witness])

    def test_snapshot_startup_share_complete_evidence_contract(self):
        expected = current_summary_values()
        app = FastAPI()
        app.include_router(admin.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        original = self.child(self.canonical)
        with TestClient(app, raise_server_exceptions=False) as client, patch.object(admin, "verify_user_password", return_value=True):
            for case in ("absent", "same", "unrelated", "partial", "partial_time", "conflicting", "conflicting_time", "wrong_kind"):
                with self.subTest(case=case):
                    accepts = case in ("absent", "same", "unrelated")
                    # New synthetic case; the preceding rejected startup was
                    # deliberately left untouched, not repaired by admission.
                    with session() as conn:
                        conn.execute("UPDATE ledger_entries SET confirmed_month=?,confirmed_at=? WHERE id=?",
                                     (original["confirmed_month"], original["confirmed_at"], self.child_id))
                        conn.execute("PRAGMA user_version=4")
                    self.save_witness(self.null_source(case), "20260711T000001Z")
                    before = self.state()
                    response = client.post("/api/admin/snapshot/restore", json={"password": "synthetic", "snapshot": self.historical()})
                    self.assertEqual(response.status_code, 200 if accepts else 400)
                    if accepts:
                        self.assertEqual(current_summary_values(), expected)
                    else:
                        self.assertEqual(self.state(), before)
                    with session() as conn:
                        conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE id=?", (self.child_id,))
                        conn.execute("PRAGMA user_version=3")
                    before = self.state()
                    if accepts:
                        init_db()
                        self.assertEqual(self.state()[1], 4)
                        self.assertEqual(current_summary_values(), expected)
                        once = self.state()
                        init_db()
                        self.assertEqual(self.state(), once)
                        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                        self.assertEqual(current_summary_values(), expected)
                    else:
                        with self.assertRaises(ValueError):
                            init_db()
                        self.assertEqual(self.state(), before)

    def test_interruptions_after_collection_proof_write_and_before_checkpoint_are_atomic(self):
        from app import db_migrations
        from app.services import recurring_compatibility as compat

        for stage in ("collection", "proof", "write", "checkpoint"):
            with self.subTest(stage=stage):
                with session() as conn:
                    conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE id=?", (self.child_id,))
                    conn.execute("PRAGMA user_version=3")
                before = self.state()
                owner, name = (compat, {"collection": "_collect_relevant_witnesses", "proof": "canonicalize_legacy_recurring",
                                        "write": "_write_epoch"}.get(stage, "")) if stage != "checkpoint" else (
                                            db_migrations, "_migration_004_recurring_identity_checkpoint")
                original = getattr(owner, name)

                def fail_after(*args, **kwargs):
                    original(*args, **kwargs)
                    raise RuntimeError("synthetic interruption")

                if stage == "checkpoint":
                    with patch.object(db_migrations, "MIGRATIONS", (*db_migrations.MIGRATIONS[:3], fail_after)):
                        with self.assertRaises(RuntimeError):
                            init_db()
                else:
                    with patch.object(owner, name, fail_after):
                        with self.assertRaises(RuntimeError):
                            init_db()
                self.assertEqual(self.state(), before)
                init_db()
                self.assertEqual(self.state()[1], 4)
                self.assertEqual(current_summary_values()["remaining_liquidity"], 95060)

    def test_supported_legacy_witness_cannot_hide_same_key_null_source_conflict(self):
        app = FastAPI()
        app.include_router(admin.router)
        app.dependency_overrides[require_user] = lambda: {"id": 1}
        original = self.child(self.canonical)
        with TestClient(app, raise_server_exceptions=False) as client, patch.object(admin, "verify_user_password", return_value=True):
            for version, case in itertools.product((4, 5, 6), ("partial", "conflicting")):
                with self.subTest(version=version, case=case):
                    with session() as conn:
                        conn.execute("UPDATE ledger_entries SET confirmed_month=?,confirmed_at=? WHERE id=?",
                                     (original["confirmed_month"], original["confirmed_at"], self.child_id))
                        conn.execute("PRAGMA user_version=4")
                    additional = self.null_source(case)
                    additional["schema_version"] = version
                    self.save_witness(self.resign(additional), "20260711T000001Z")
                    before = self.state()
                    response = client.post("/api/admin/snapshot/restore", json={"password": "synthetic", "snapshot": self.historical()})
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(self.state(), before)
                    with session() as conn:
                        conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE id=?", (self.child_id,))
                        conn.execute("PRAGMA user_version=3")
                    before = self.state()
                    with self.assertRaises(ValueError):
                        init_db()
                    self.assertEqual(self.state(), before)

    def test_legacy_witness_is_a_constraint_not_a_positive_epoch_proof(self):
        from app.services.recurring_compatibility import _proofs, legacy_recurring_witnesses

        for version in (4, 5, 6):
            with self.subTest(version=version):
                additional = self.null_source("absent")
                additional["schema_version"] = version
                self.save_witness(self.resign(additional), "20260711T000001Z")
                witnesses = legacy_recurring_witnesses()
                legacy = next(w for w in witnesses if w["_recurring_witness_schema_version"] == version)
                self.assertEqual(_proofs(legacy), {})
                self.assertEqual(canonicalize_legacy_recurring(self.historical()["data"], witnesses),
                                 self.canonical["data"]["ledger_entries"])
                with self.assertRaises(ValueError):
                    canonicalize_legacy_recurring(self.historical()["data"], [legacy])

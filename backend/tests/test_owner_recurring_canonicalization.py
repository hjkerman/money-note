"""Explicit owner decisions are not automatic historical ownership proof."""

import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from unittest.mock import patch

import pytest

from app.config import get_settings
from app.db import init_db, session
from app.services.summary import _current_summary_values
from app.repositories.entries import confirm_planned_entry, delete_entry, list_confirmed_planned_entries
from app.services.snapshot import export_snapshot, restore_snapshot
from tests.db_fixture import IsolatedDatabaseTestCase
from app.services.recurring_canonicalization import (
    build_manifest, encode_document, execute, persistent_state,
)


class OwnerCanonicalizationTests(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.today = patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-10-03"})
        self.today.start()
        get_settings.cache_clear()
        self.addCleanup(self.today.stop)
        self.root = Path(self.temp_dir.name)
        self.mappings = []
        with session() as conn:
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('cash_flow_balance','100000')")
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('last_closed_month','2026-09')")
            for source in range(1, 8):
                active = source in (1, 2, 3, 7)
                conn.execute("""INSERT INTO ledger_entries(id,book_section,entry_kind,title,amount_value,sort_order,
                    confirmed_month,confirmed_at) VALUES(?,'current','planned','synthetic',5000,0,?,?)""",
                    (source, '2026-10' if active else None, '2026-10-01 00:00:00' if active else None))
            pairs = [(s, 'archive', '2026-09') for s in range(1, 8)]
            pairs += [(s, 'current', '2026-10') for s in (1, 2, 3, 7)]
            for index, (source, location, month) in enumerate(pairs, 1):
                child, key = 100 + index, f'synthetic-owner-key-{index}'
                timestamp = f'{month}-01 00:00:00'
                conn.execute("""INSERT INTO ledger_entries(id,book_section,entry_kind,title,amount_value,sort_order,
                    entry_date,payment_key,source_planned_entry_id,confirmed_month,confirmed_at)
                    VALUES(?,?,'expense','synthetic',5000,0,?,?,?,?,?)""",
                    (child, location, f'{month}-01', key, source, month, timestamp))
                self.mappings.append(dict(review_id=f'R{index:02}', source_planned_id=source,
                    child_location=location, child_id=child, stable_key=key,
                    confirmed_month=month, confirmed_at=timestamp, owner_decision='YES'))
            self.baseline = _current_summary_values(conn)
            conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL WHERE entry_kind='expense'")
            conn.execute('PRAGMA user_version=3')
        with self.connect() as conn:
            self.manifest = build_manifest(conn, self.mappings, '2026-10-03', self.baseline)
        self.backup = self.root / 'verified-online-backup.sqlite3'
        with self.connect() as conn, sqlite3.connect(self.backup) as dest:
            conn.backup(dest)
        self.backup_sha = hashlib.sha256(self.backup.read_bytes()).hexdigest()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        return conn

    def state(self):
        with self.connect() as conn:
            return persistent_state(conn)

    def run_tool(self, manifest=None, *, apply=False, receipt=None, checkpoint=None):
        raw = encode_document(manifest or self.manifest)
        return execute(self.db_path, raw, hashlib.sha256(raw).hexdigest(), self.backup,
            self.backup_sha, apply=apply, receipt=receipt,
            receipt_sha256=hashlib.sha256(receipt).hexdigest() if receipt else None,
            checkpoint=checkpoint)

    def test_eleven_dry_run_atomic_apply_startup_and_repeat(self):
        before = self.state()
        file_hash = hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        dry = self.run_tool()
        assert dry['mode'] == 'dry-run'
        assert dry['mapping_count'] == 11
        assert all(value == 0 for value in dry['financial_difference'].values())
        assert self.state() == before
        assert hashlib.sha256(self.db_path.read_bytes()).hexdigest() == file_hash
        result = self.run_tool(apply=True, receipt=encode_document(dry))
        assert result['mode'] == 'applied'
        assert len(result['changed_rows']) == 11
        with self.connect() as conn:
            assert _current_summary_values(conn) == self.baseline
            assert conn.execute('PRAGMA user_version').fetchone()[0] == 3
        init_db()
        after = self.state()
        init_db()
        assert self.state() == after
        with pytest.raises(ValueError):
            self.run_tool(apply=True, receipt=encode_document(dry))
        assert self.state() == after

    def test_automatic_compatibility_still_rejects(self):
        before = self.state()
        with pytest.raises(ValueError):
            init_db()
        assert self.state() == before

    def test_wrong_manifest_matrix_is_all_or_nothing(self):
        mutations = [
            lambda m: m['mappings'][0].update(child_id=9999),
            lambda m: m['mappings'][0].update(source_planned_id=9999),
            lambda m: m['mappings'][0].update(stable_key='wrong'),
            lambda m: m['mappings'][0].update(child_location='current'),
            lambda m: m['mappings'][0].update(confirmed_month='2026-10'),
            lambda m: m['mappings'][0].update(confirmed_at='2026-09-01T00:00:00+00:99'),
            lambda m: m['mappings'][0].update(owner_decision='NO'),
            lambda m: m['mappings'][0].update(review_id='unknown'),
            lambda m: m['mappings'].append(copy.deepcopy(m['mappings'][0])),
            lambda m: m['mappings'][1].update(child_id=m['mappings'][0]['child_id']),
            lambda m: m.update(review_fingerprint='0' * 64),
            lambda m: m['financial_baseline'].update(card_total=999),
        ]
        before = self.state()
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                document = copy.deepcopy(self.manifest)
                mutate(document)
                with pytest.raises(ValueError):
                    self.run_tool(document)
                assert self.state() == before

    def test_stale_review_and_stale_backup_reject(self):
        with self.connect() as conn:
            conn.execute("UPDATE ledger_entries SET title='changed after review' WHERE id=101")
            conn.commit()
        before = self.state()
        with pytest.raises((ValueError, RuntimeError)):
            self.run_tool()
        assert self.state() == before

    def test_review_comparison_date_cannot_survive_calendar_advancement(self):
        before = self.state()
        with patch.dict(os.environ, {'MONEY_NOTE_TODAY': '2026-11-01'}):
            get_settings.cache_clear()
            with pytest.raises(ValueError, match='date'):
                self.run_tool()
        get_settings.cache_clear()
        assert self.state() == before

    def test_apply_requires_verified_backup_and_dry_run_receipt(self):
        before = self.state()
        with pytest.raises(ValueError):
            self.run_tool(apply=True)
        self.backup_sha = '0' * 64
        with pytest.raises(ValueError):
            self.run_tool()
        assert self.state() == before

    def test_incomplete_or_inconsistent_receipt_is_not_a_dry_run(self):
        dry = self.run_tool()
        before = self.state()
        for field, replacement in (('financial_difference', {}), ('mapping_count', 1),
                                   ('changed_rows', []), ('after_state_fingerprint', '0' * 64)):
            with self.subTest(field=field):
                bad = {**dry, field: replacement}
                with pytest.raises(ValueError):
                    self.run_tool(apply=True, receipt=encode_document(bad))
                assert self.state() == before

    def test_interruption_at_every_boundary_rolls_back(self):
        receipt = encode_document(self.run_tool())
        stages = ['before_transaction', 'collected', 'updated:1', 'updated:6', 'updated:11', 'validated', 'before_commit']
        before = self.state()
        for stage in stages:
            with self.subTest(stage=stage):
                def interrupt(current):
                    if current == stage:
                        raise RuntimeError('controlled interruption')
                with pytest.raises(RuntimeError):
                    self.run_tool(apply=True, receipt=receipt, checkpoint=interrupt)
                assert self.state() == before

    def test_unexpected_trigger_change_rolls_back(self):
        with self.connect() as conn:
            conn.execute("""CREATE TRIGGER malicious_metadata_effect AFTER UPDATE OF confirmed_at
                ON ledger_entries BEGIN UPDATE ledger_entries SET amount_value=1 WHERE id=NEW.id; END""")
            conn.commit()
        # Even a freshly reviewed, accurately backed-up state cannot authorize money changes.
        with self.connect() as conn:
            self.manifest = build_manifest(conn, self.mappings, '2026-10-03', self.baseline)
        self.backup.unlink()
        with self.connect() as conn, sqlite3.connect(self.backup) as dest:
            conn.backup(dest)
        self.backup_sha = hashlib.sha256(self.backup.read_bytes()).hexdigest()
        before = self.state()
        with pytest.raises((ValueError, RuntimeError)):
            self.run_tool()
        assert self.state() == before

    def test_raw_manifest_digest_and_no_unlisted_repair(self):
        raw = encode_document(self.manifest)
        tampered = json.loads(raw)
        tampered['mappings'][0]['confirmed_at'] = '2026-09-02 00:00:00'
        with pytest.raises(ValueError):
            execute(self.db_path, encode_document(tampered), hashlib.sha256(raw).hexdigest(),
                self.backup, self.backup_sha)

    def refresh_review_and_backup(self):
        with self.connect() as conn:
            self.manifest = build_manifest(conn, self.mappings, '2026-10-03', self.baseline)
        self.backup.unlink()
        with self.connect() as conn, sqlite3.connect(self.backup) as dest:
            conn.backup(dest)
        self.backup_sha = hashlib.sha256(self.backup.read_bytes()).hexdigest()

    def test_unlisted_lookalike_is_unchanged(self):
        with self.connect() as conn:
            conn.execute("""INSERT INTO ledger_entries(id,book_section,entry_kind,title,amount_value,
                sort_order,entry_date,payment_key) VALUES(999,'archive','expense','synthetic',5000,
                0,'2026-09-01','unlisted-similar-key')""")
            conn.commit()
        self.refresh_review_and_backup()
        before = self.state()
        receipt = encode_document(self.run_tool())
        self.run_tool(apply=True, receipt=receipt)
        assert next(r for r in self.state()['tables']['ledger_entries'] if r['id'] == 999) == next(
            r for r in before['tables']['ledger_entries'] if r['id'] == 999)

    def test_unlisted_unresolved_relationship_blocks_entire_manifest(self):
        with self.connect() as conn:
            conn.execute("""INSERT INTO ledger_entries(id,book_section,entry_kind,title,amount_value,
                sort_order,entry_date,payment_key,source_planned_entry_id)
                VALUES(999,'archive','expense','synthetic',5000,0,'2026-08-01','unlisted-key',1)""")
            conn.commit()
        self.refresh_review_and_backup()
        before = self.state()
        with pytest.raises(ValueError):
            self.run_tool()
        assert self.state() == before

    def test_pairs_archive_reset_cancel_reconfirm_and_current_round_trip(self):
        receipt = encode_document(self.run_tool())
        self.run_tool(apply=True, receipt=receipt)
        init_db()
        for source in (1, 2, 3, 7):
            historical = next(m for m in self.mappings if m['source_planned_id'] == source and m['child_location'] == 'archive')
            active = next(m for m in self.mappings if m['source_planned_id'] == source and m['child_location'] == 'current')
            assert next(r for r in list_confirmed_planned_entries() if r['id'] == source)['_confirmed_expense']['id'] == active['child_id']
            assert delete_entry(historical['child_id'])
            assert next(r for r in list_confirmed_planned_entries() if r['id'] == source)['_confirmed_expense']['id'] == active['child_id']
            assert delete_entry(active['child_id'])
            generated = confirm_planned_entry(source)['entry']
            with pytest.raises(ValueError):
                confirm_planned_entry(source)
            assert next(r for r in list_confirmed_planned_entries() if r['id'] == source)['_confirmed_expense']['id'] == generated['id']
        for source in (4, 5, 6):
            assert next(r for r in self.state()['tables']['ledger_entries'] if r['id'] == source)['confirmed_month'] is None
        snapshot = export_snapshot()[1]
        with session() as conn:
            expected = _current_summary_values(conn)
        target = self.root / 'fresh-round-trip.sqlite3'
        with patch.dict(os.environ, {'MONEY_NOTE_DB_PATH': str(target)}):
            get_settings.cache_clear()
            init_db()
            restore_snapshot(snapshot)
            init_db()
            with session() as conn:
                assert _current_summary_values(conn) == expected
            assert export_snapshot()[1]['data'] == snapshot['data']
        get_settings.cache_clear()

    def test_allowlist_detects_even_nonfinancial_unlisted_change(self):
        before = self.state()
        receipt = encode_document(self.run_tool())
        # Test-only hook changes a nonfinancial value on the same connection.
        # Ordinary concurrent writers are excluded by BEGIN IMMEDIATE.
        original = __import__('app.services.recurring_canonicalization', fromlist=['persistent_state']).persistent_state
        def changed_state(conn):
            if conn.execute('SELECT confirmed_at FROM ledger_entries WHERE id=101').fetchone()[0]:
                conn.execute("UPDATE ledger_entries SET title='unexpected' WHERE id=101")
            return original(conn)
        with patch('app.services.recurring_canonicalization.persistent_state', changed_state):
            with pytest.raises(ValueError):
                self.run_tool(apply=True, receipt=receipt)
        assert self.state() == before

    def test_real_process_exit_is_atomic_in_delete_and_wal(self):
        for journal in ('DELETE', 'WAL'):
            with self.connect() as conn:
                conn.execute(f'PRAGMA journal_mode={journal}')
            self.refresh_review_and_backup()
            receipt = encode_document(self.run_tool())
            manifest_path = self.root / 'approved.json'
            receipt_path = self.root / 'dry.json'
            manifest_path.write_bytes(encode_document(self.manifest))
            receipt_path.write_bytes(receipt)
            before = self.state()
            for stage in ('before_transaction', 'collected', 'updated:6', 'updated:11', 'validated', 'before_commit'):
                with self.subTest(journal=journal, stage=stage):
                    program = '''import hashlib, os, sys
from pathlib import Path
from app.services.recurring_canonicalization import execute
db,manifest,backup,backup_sha,receipt,stage=sys.argv[1:]
m=Path(manifest).read_bytes(); r=Path(receipt).read_bytes()
execute(Path(db),m,hashlib.sha256(m).hexdigest(),Path(backup),backup_sha,
    apply=True,receipt=r,receipt_sha256=hashlib.sha256(r).hexdigest(),
    checkpoint=lambda s: os._exit(77) if s==stage else None)
'''
                    process = subprocess.run([sys.executable, '-c', program, str(self.db_path),
                        str(manifest_path), str(self.backup), self.backup_sha, str(receipt_path), stage],
                        env={**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1])},
                        capture_output=True, timeout=20)
                    assert process.returncode == 77, process.stderr.decode()
                    assert self.state() == before

    def test_cli_defaults_to_dry_run_and_never_overwrites_artifacts(self):
        manifest_path = self.root / 'owner-approved.json'
        report = self.root / 'cli-dry-run.json'
        manifest_path.write_bytes(encode_document(self.manifest))
        cli = Path(__file__).resolve().parents[2] / 'scripts/canonicalize-recurring.py'
        arguments = [sys.executable, str(cli), '--db', str(self.db_path), '--manifest', str(manifest_path),
            '--approved-manifest-sha256', hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            '--verified-backup', str(self.backup), '--backup-sha256', self.backup_sha]
        before = self.state()
        result = subprocess.run([*arguments, '--report', str(report)], capture_output=True, env=os.environ, timeout=20)
        assert result.returncode == 0, result.stderr.decode()
        assert json.loads(report.read_bytes())['mode'] == 'dry-run'
        assert report.stat().st_mode & 0o777 == 0o600
        assert self.state() == before
        for path in (report, manifest_path, self.db_path, self.backup):
            original = path.read_bytes()
            result = subprocess.run([*arguments, '--apply', '--report', str(path)], capture_output=True, env=os.environ, timeout=20)
            assert result.returncode == 1
            assert path.read_bytes() == original
            assert self.state() == before

    def test_reapproved_structurally_wrong_inputs_still_reject(self):
        # Recomputing approval digests cannot bypass relational preconditions.
        for field, value in (('child_id', 9999), ('source_planned_id', 6),
                ('stable_key', 'wrong'), ('child_location', 'archive'),
                ('confirmed_month', '2026-11'), ('confirmed_at', '2026-10-02 00:00:00')):
            with self.subTest(field=field):
                mappings = copy.deepcopy(self.mappings)
                mappings[7][field] = value  # active October occurrence
                before = self.state()
                with self.connect() as conn:
                    manifest = build_manifest(conn, mappings, '2026-10-03', self.baseline)
                with pytest.raises(ValueError):
                    self.run_tool(manifest)
                assert self.state() == before

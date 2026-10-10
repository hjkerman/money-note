"""D3a real migrated synthetic SQLite, independent financial/state oracles."""

from datetime import date, datetime, timedelta, timezone
import hashlib
import random
import sqlite3
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.services.authoritative_state import BundleCredential
from isolated_sync.observation import Evaluation, ObservationError, ObservationRepository, accepted_generation, financial_scope, hot_projections
from isolated_sync.observation_schema import ObservationSandbox, validate_schema
from isolated_sync.raw import MONEY_SETTINGS
from tests.test_isolated_sync_capture import ROWS, insert
from tests.test_isolated_sync_finalization import verify

NOW = datetime(2026, 10, 5, 0, 0, 0, tzinfo=timezone.utc)
EVAL = Evaluation(date(2026, 10, 5), 540)
CREDENTIAL = BundleCredential(hashlib.sha256(b"synthetic-d3a-token").hexdigest(), 1)


def auth_seed(conn):
    conn.execute("INSERT INTO users(id,username,password_hash) VALUES (1,'synthetic-owner','not-a-real-hash')")
    conn.execute("INSERT INTO users(id,username,password_hash) VALUES (2,'synthetic-other','not-a-real-hash')")
    for cred in (CREDENTIAL, BundleCredential('b'*64, 1), BundleCredential('c'*64, 2)):
        conn.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (?,?,?)", (cred.user_id, cred.token_hash, '2026-12-31T00:00:00Z'))


@pytest.fixture
def sandbox():
    with ObservationSandbox() as db:
        with db.connect() as conn:
            for table, source in ROWS.items():
                value = dict(source)
                if table == 'cash_flows':
                    value['amount_value'] = -50
                insert(conn, table, value)
            for key in MONEY_SETTINGS:
                conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
            auth_seed(conn)
        db.install()
        db.bootstrap()
        yield db


def repository(db, **kwargs):
    return ObservationRepository(db, evaluation=kwargs.pop('evaluation', lambda: EVAL), clock=kwargs.pop('clock', lambda: NOW), **kwargs)


def create(repo, **kwargs):
    cred = kwargs.pop('credential', CREDENTIAL)
    return repo.create(cred, request_id=kwargs.pop('request_id', str(uuid4())), guard=kwargs.pop('guard', lambda: cred), **kwargs)


def raw_state(db):
    with db.connect() as conn:
        from isolated_sync.facts import read_state
        return read_state(conn), verify(conn), list(map(tuple, conn.execute('SELECT * FROM auth_sessions')))


def test_complete_pins_restart_and_financial_immutability(sandbox):
    before = raw_state(sandbox)
    repo = repository(sandbox)
    result = create(repo)
    assert repo.lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL) == result
    with sandbox.connect() as conn:
        current = conn.execute('SELECT * FROM sync_current').fetchone()
        cert = conn.execute('SELECT * FROM sync_commits WHERE tx_id=?', (current['tx_id'],)).fetchone()
        pins = dict(conn.execute('SELECT role,hash FROM sync_observation_pins WHERE observation_id=? AND active=1', (result['observation_id'],)))
        assert pins == dict(raw=current['raw_hash'], index=current['index_hash'], input=cert['input_hash'],
                            hot=result['target']['hot_ref']['hash'], control=result['target']['control_ref']['hash'])
        assert cert['status'] == 'complete'
        assert int(result['target']['revision']) == cert['target_revision']
        assert len(repo.roots(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)) == 4
    assert raw_state(sandbox) == before


def test_repository_connections_close_on_success_and_failure(sandbox):
    opened = []
    original = sandbox.connect
    def connect():
        conn = original()
        opened.append(conn)
        return conn
    with patch.object(sandbox, 'connect', connect):
        result = create(repository(sandbox))
        repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
        with pytest.raises(ObservationError):
            create(repository(sandbox), guard=lambda: None)
    assert len(opened) == 3
    for conn in opened:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            conn.execute('SELECT 1')


@pytest.mark.parametrize('day', [date(2026, 9, 30), date(2026, 10, 5), date(2026, 10, 31), date(2026, 11, 1)])
@pytest.mark.parametrize('state', ['base', 'recurring', 'fixed', 'policy', 'archive', 'cash'])
def test_all_twelve_legacy_projection_parity(sandbox, day, state):
    # Actual B-1 construction is the independent oracle, not D3a serialization.
    from app.services.authoritative_state import _construct, _prepare
    with sandbox.connect() as conn:
        if state != 'base':
            from isolated_sync.inputs import BoundedInputs
            conn.begin_capture()
            writer = BoundedInputs(conn)
            if state == 'recurring':
                from app.repositories.entries import append_planned_entry, confirm_planned_entry
                from app.schemas import PlannedEntryIn
                source = append_planned_entry(PlannedEntryIn(title='recurring', usage_place='service', amount_value=500, due_day=5), conn=writer)
                confirm_planned_entry(source['id'], today=EVAL.today, actual_amount=700, conn=writer)
            elif state == 'fixed':
                from app.services.panels import confirm_fixed_panel
                insert(writer, 'monthly_panels', dict(id=101, month='2026-10', panel_type='fixed', title='fixed', amount_value=500, sort_order=2, due_day=5))
                confirm_fixed_panel(101, '2026-10-05', actual_amount=400, today=EVAL.today, conn=writer)
            elif state == 'policy':
                from app.services.card_charge.profiles import set_transit_discount_profile
                set_transit_discount_profile('2026-10', 'owner', conn=writer)
            elif state == 'archive':
                conn.execute("UPDATE ledger_entries SET book_section='archive',entry_date=NULL WHERE id=100")
            else:
                from app.repositories.cash_flows import create_cash_flow
                from app.schemas import CashFlowIn
                create_cash_flow(CashFlowIn(occurred_on='2026-01-05', title='historical', amount_value=1000, sort_order=2), conn=writer)
                create_cash_flow(CashFlowIn(occurred_on='2026-10-05', title='income', amount_value=500, sort_order=3, is_primary_income=1), conn=writer)
            conn.finalize()
            conn.commit()
        conn.execute('BEGIN IMMEDIATE')
        accepted, _, _ = accepted_generation(conn)
        with patch('app.services.judgment.common._MESSAGE_RANDOM', random.Random(66301)), financial_scope(conn, accepted) as scope:
            actual = hot_projections(scope, Evaluation(day, 540))
        with patch('app.services.authoritative_state.CURRENT_SCHEMA_VERSION', conn.execute('PRAGMA user_version').fetchone()[0]), patch('app.services.authoritative_state._validate_revision_triggers'), patch('app.services.authoritative_state.app_today', return_value=day), patch('app.services.judgment.common._MESSAGE_RANDOM', random.Random(66301)):
            # Snapshot strict admission is unchanged; only isolated schema gate
            # differs. Full history construction runs ONLY in this test oracle.
            bundle, _, _ = _construct(conn, CREDENTIAL)
            import json
            expected = json.loads(_prepare(bundle).body)['state']
        assert len(actual) == 12
        assert actual == expected


def test_read_scope_lifetime_and_no_writes(sandbox):
    with sandbox.connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        accepted, _, _ = accepted_generation(conn)
        with financial_scope(conn, accepted) as scope:
            with pytest.raises(ObservationError):
                scope.execute("UPDATE app_settings SET value='wrong'")
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("UPDATE app_settings SET value='wrong'")
        with pytest.raises(ObservationError):
            scope.cash_total('2026-10-05')


@pytest.mark.parametrize('stage', ['validation', 'roots', 'pin_raw', 'pin_index', 'pin_hot', 'pin_control', 'pin_input', 'before_commit'])
def test_failure_rolls_back_all_metadata(sandbox, stage):
    before = raw_state(sandbox)
    def fault(current, conn):
        if current == stage:
            raise RuntimeError('synthetic failure')
    with pytest.raises(RuntimeError):
        create(repository(sandbox), fault=fault)
    with sandbox.connect() as conn:
        assert conn.execute('SELECT count(*) FROM sync_observations').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM sync_observation_pins').fetchone()[0] == 0
    assert raw_state(sandbox) == before


@pytest.mark.parametrize('defect', ['wrong_owner', 'different_token', 'missing_guard', 'changed_guard', 'expired_token', 'inactive_user', 'protocol'])
def test_auth_fail_closed(sandbox, defect):
    repo = repository(sandbox)
    result = create(repo)
    cred = CREDENTIAL
    def guard():
        return cred
    if defect == 'wrong_owner':
        cred = BundleCredential('c'*64, 2)
    elif defect == 'different_token':
        cred = BundleCredential('b'*64, 1)
    elif defect == 'missing_guard':
        guard = None
    elif defect == 'changed_guard':
        def guard():
            return BundleCredential('b'*64, 1)
    elif defect in ('expired_token', 'inactive_user'):
        with sandbox.connect() as conn:
            if defect == 'expired_token':
                conn.execute("UPDATE auth_sessions SET expires_at='2026-01-01T00:00:00Z'")
            else:
                conn.execute('UPDATE users SET is_active=0')
    if defect == 'protocol':
        with pytest.raises(ObservationError, match='UNSUPPORTED'):
            create(repo, protocol=2)
    else:
        with pytest.raises(ObservationError):
            repo.lookup(result['observation_id'], cred, guard=guard)


def test_idempotent_retry_request_conflict_and_quota(sandbox):
    repo = repository(sandbox)
    request = str(uuid4())
    result = create(repo, request_id=request)
    assert create(repo, request_id=request) == result
    with pytest.raises(ObservationError, match='REQUEST_CONFLICT'):
        create(repo, request_id=request, inline_bytes=1)
    for _ in range(3):
        create(repo)
    with pytest.raises(ObservationError, match='LEASE_LIMIT'):
        create(repo)


def test_expiration_and_epoch_rotation(sandbox):
    result = create(repository(sandbox))
    with pytest.raises(ObservationError, match='EXPIRED'):
        repository(sandbox, clock=lambda: NOW+timedelta(seconds=900)).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
    sandbox.bootstrap()
    with pytest.raises(ObservationError, match='EPOCH_CHANGED'):
        repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
    with sandbox.connect() as conn:
        assert conn.execute('SELECT count(*) FROM sync_observation_pins WHERE active=1').fetchone()[0] == 0
    fresh = create(repository(sandbox))
    assert fresh['target']['ns'] != result['target']['ns']


@pytest.mark.parametrize('defect', ['revision', 'capture_only', 'stale_cert', 'missing_root', 'corrupt_root', 'missing_input', 'stale_cash', 'schema'])
def test_invalid_accepted_generation(sandbox, defect):
    # Intentional privileged corruption only; ordinary SQL cannot do this.
    with sqlite3.connect(sandbox.path) as conn:
        if defect == 'revision':
            conn.execute('UPDATE authoritative_state_revision SET revision=revision+1')
        elif defect == 'capture_only':
            conn.execute('DELETE FROM sync_commits')
        elif defect == 'stale_cert':
            conn.execute('UPDATE sync_commits SET target_revision=target_revision+1')
        elif defect == 'missing_root':
            conn.execute('DELETE FROM sync_objects WHERE hash=(SELECT raw_hash FROM sync_current)')
        elif defect == 'corrupt_root':
            conn.execute("UPDATE sync_objects SET body=x'7b7d' WHERE hash=(SELECT raw_hash FROM sync_current)")
        elif defect == 'missing_input':
            conn.execute('UPDATE sync_commits SET input_hash=raw_hash')
        elif defect == 'stale_cash':
            conn.execute("UPDATE sync_cash_prefix SET total='999'")
        elif defect == 'schema':
            conn.execute('CREATE INDEX sync_unapproved ON sync_objects(kind)')
    with pytest.raises((ObservationError, ValueError)):
        create(repository(sandbox))


def test_changed_complete_generation_requires_capture_certificate(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        conn.execute("UPDATE app_labels SET value='changed'")
        conn.finalize()
        conn.commit()
    with sqlite3.connect(sandbox.path) as conn:
        conn.execute('DELETE FROM sync_capture_commits WHERE tx_id=(SELECT tx_id FROM sync_current)')
    with pytest.raises(ObservationError, match='ROOT_NOT_READY'):
        create(repository(sandbox))
    with sandbox.connect() as conn:
        assert not conn.execute('SELECT 1 FROM sync_observations').fetchone()


def test_date_context_and_raw_change_classification(sandbox):
    with patch('app.services.judgment.common._MESSAGE_RANDOM', random.Random(66301)):
        base = create(repository(sandbox))
    with patch('app.services.judgment.common._MESSAGE_RANDOM', random.Random(66301)):
        same = create(repository(sandbox), base=base['target'])
    assert same['change_kind'] == 'unchanged'
    later = create(repository(sandbox, evaluation=lambda: Evaluation(date(2026, 11, 1), 540)), base=base['target'])
    assert later['change_kind'] == 'context'
    assert later['target']['raw_ref'] == base['target']['raw_ref']
    with sandbox.connect() as conn:
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='new' WHERE id=100")
        conn.finalize()
        conn.commit()
    changed = create(repository(sandbox), base=base['target'])
    assert changed['change_kind'] == 'raw'
    assert repository(sandbox).lookup(base['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL) == base


def test_terminal_date_and_credential_change_rolls_back(sandbox):
    current = [EVAL]
    def fault(stage, conn):
        if stage == 'before_commit':
            current[0] = Evaluation(date(2026, 10, 6), 540)
    with pytest.raises(ObservationError, match='CONFLICT'):
        create(repository(sandbox, evaluation=lambda: current[0]), fault=fault)
    current[0] = EVAL
    def credential_fault(stage, conn):
        if stage == 'before_commit':
            conn.execute('DELETE FROM auth_sessions')
    with pytest.raises(ObservationError, match='AUTH_REQUIRED'):
        create(repository(sandbox), fault=credential_fault)
    assert raw_state(sandbox)[2]  # Auth mutation rolled back with failed pin.


def test_sensitive_setting_revision_only(sandbox):
    before = create(repository(sandbox))
    with sandbox.connect() as conn:
        conn.begin_capture()
        conn.execute("INSERT INTO app_settings(key,value) VALUES ('share_pin_hash','synthetic-never-transfer')")
        conn.finalize()
        conn.commit()
    after = create(repository(sandbox), base=before['target'])
    assert after['target']['raw_ref'] == before['target']['raw_ref']
    assert after['target']['revision'] != before['target']['revision']
    with sandbox.connect() as conn:
        assert all(b'synthetic-never-transfer' not in r[0] for r in conn.execute('SELECT body FROM sync_objects'))


def test_forbids_full_history_and_graph_rebuild(sandbox):
    from isolated_sync.segments import Tree
    from isolated_sync.patricia import Index
    with patch.object(Tree, 'rows', side_effect=AssertionError('full rows')), patch.object(Tree, 'objects', side_effect=AssertionError('full graph')), patch.object(Index, 'facts', side_effect=AssertionError('all facts')), patch.object(Index, 'build', side_effect=AssertionError('rebuild')):
        create(repository(sandbox))


def test_no_runtime_import_or_new_routes():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert all('isolated_sync' not in path.read_text() for path in (root/'app').rglob('*.py'))
    from app.main import app
    assert not any('/api/sync/' in getattr(route, 'path', '') for route in app.routes)


def test_pin_tamper_lookup_rejected(sandbox):
    result = create(repository(sandbox))
    with sqlite3.connect(sandbox.path) as conn:
        conn.execute("DELETE FROM sync_observation_pins WHERE role='input'")
    with pytest.raises(ObservationError, match='INCOMPLETE'):
        repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)


@pytest.mark.parametrize('field,value', [('target', []), ('target', {'principal_id': 1}), ('response', [])])
def test_corrupt_persisted_envelope_error_classification(sandbox, field, value):
    from isolated_sync.canonical import encode
    result = create(repository(sandbox))
    with sqlite3.connect(sandbox.path) as conn:
        conn.execute(f'UPDATE sync_observations SET {field}=?', (encode(value),))
    with pytest.raises(ObservationError, match='REQUIRED_METADATA_INVALID'):
        repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)


def test_install_idempotent_and_d2b_writer_still_valid(sandbox):
    before = raw_state(sandbox)
    sandbox.install()
    with sandbox.connect() as conn:
        validate_schema(conn)
        conn.begin_capture()
        conn.execute("UPDATE app_labels SET value='updated'")
        conn.finalize()
        conn.commit()
        assert verify(conn) != before[1]
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("UPDATE sync_observations SET status='retired'")


@pytest.mark.parametrize('stage', ['validation', 'roots', 'pin_raw', 'pin_input', 'before_commit', 'after_commit'])
def test_process_kill_atomic_observation(sandbox, stage):
    import multiprocessing
    import os
    import signal
    request_id = str(uuid4())
    before = raw_state(sandbox)
    def child():
        def fault(current, conn):
            if current == stage:
                os.kill(os.getpid(), signal.SIGKILL)
        create(repository(sandbox), request_id=request_id, fault=fault)
    process = multiprocessing.get_context('fork').Process(target=child)
    process.start()
    process.join(10)
    assert not process.is_alive()
    assert process.exitcode == -signal.SIGKILL
    with sandbox.connect() as conn:
        rows = conn.execute('SELECT id FROM sync_observations WHERE request_id=?', (request_id,)).fetchall()
        assert len(rows) == (stage == 'after_commit')
        if rows:
            result = repository(sandbox).lookup(rows[0][0], CREDENTIAL, guard=lambda: CREDENTIAL)
            assert result['request_id'] == request_id
    assert raw_state(sandbox) == before


@pytest.mark.parametrize('change', ['auth', 'revision', 'epoch', 'rollback'])
def test_writer_before_lock_acquisition(sandbox, change):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from isolated_sync.observation_schema import ObservationConnection
    before = create(repository(sandbox))
    lock_attempt = Event()
    original = ObservationConnection.execute
    def execute(conn, sql, parameters=()):
        if sql == 'BEGIN IMMEDIATE' and getattr(conn, 'observer_test', False):
            lock_attempt.set()
        return original(conn, sql, parameters)
    original_connect = sandbox.connect
    def observer_connect():
        conn = original_connect()
        conn.observer_test = True
        return conn
    with sandbox.connect() as writer:
        writer.begin_capture()
        if change == 'auth':
            writer.execute('DELETE FROM auth_sessions WHERE session_token_hash=?', (CREDENTIAL.token_hash,))
        else:
            writer.execute("UPDATE ledger_entries SET title='writer' WHERE id=100")
        with patch.object(ObservationConnection, 'execute', execute), patch.object(sandbox, 'connect', observer_connect), ThreadPoolExecutor(1) as pool:
            future = pool.submit(create, repository(sandbox))
            assert lock_attempt.wait(2)
            if change == 'rollback':
                writer.rollback()
            else:
                writer.finalize()
                writer.commit()
            if change == 'auth':
                with pytest.raises(ObservationError, match='AUTH_REQUIRED'):
                    future.result(3)
            else:
                result = future.result(3)
                assert result['target']['revision'] == (before['target']['revision'] if change == 'rollback' else str(int(before['target']['revision'])+1))
                assert result['target']['raw_ref'] == before['target']['raw_ref'] if change == 'rollback' else result['target']['raw_ref'] != before['target']['raw_ref']
    if change == 'epoch':
        # Cold bootstrap is exclusive, atomic, and invalidates existing pins.
        sandbox.bootstrap()
        with pytest.raises(ObservationError, match='EPOCH_CHANGED'):
            repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)


@pytest.mark.parametrize('change', ['epoch', 'cancel', 'principal'])
def test_terminal_identity_changes_before_lock_acquisition(sandbox, change):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, current_thread
    from isolated_sync.observation_schema import ObservationConnection
    base = create(repository(sandbox))
    attempted, release, ticket = Event(), Event(), [CREDENTIAL]
    original = ObservationConnection.execute
    def execute(conn, sql, parameters=()):
        if sql == 'BEGIN IMMEDIATE' and current_thread().name.startswith('d3a-guard'):
            attempted.set()
            assert release.wait(10)
        return original(conn, sql, parameters)
    with patch.object(ObservationConnection, 'execute', execute), ThreadPoolExecutor(1, thread_name_prefix='d3a-guard') as pool:
        future = pool.submit(create, repository(sandbox), base=base['target'], guard=lambda: ticket[0])
        try:
            assert attempted.wait(3)
            if change == 'epoch':
                sandbox.bootstrap()
            else:
                ticket[0] = None if change == 'cancel' else BundleCredential('c'*64, 2)
        finally:
            release.set()
        with pytest.raises(ObservationError, match='EPOCH_CHANGED' if change == 'epoch' else 'PRINCIPAL_OR_SESSION_CHANGED'):
            future.result(10)
    with sandbox.connect() as conn:
        assert conn.execute('SELECT count(*) FROM sync_observations').fetchone()[0] == 1


def test_observation_lock_prevents_mixed_writer_target(sandbox):
    from concurrent.futures import ThreadPoolExecutor
    def blocked_writer():
        with sandbox.connect() as conn:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                conn.begin_capture()
    def fault(stage, conn):
        if stage == 'roots':
            with ThreadPoolExecutor(1) as pool:
                pool.submit(blocked_writer).result(3)
    result = create(repository(sandbox), fault=fault)
    with sandbox.connect() as conn:
        assert result['target']['revision'] == str(conn.execute('SELECT revision FROM sync_current').fetchone()[0])
        verify(conn)


def test_concurrent_observers_same_target(sandbox):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: create(repository(sandbox)), range(2)))
    assert results[0]['observation_id'] != results[1]['observation_id']
    assert results[0]['target']['raw_ref'] == results[1]['target']['raw_ref']
    assert results[0]['target']['index_ref'] == results[1]['target']['index_ref']
    with sandbox.connect() as conn:
        assert conn.execute('SELECT count(*) FROM sync_observation_pins WHERE active=1').fetchone()[0] == 10


def test_uncommitted_authority_not_observable(sandbox):
    with sandbox.connect() as writer:
        writer.begin_capture()
        writer.execute("UPDATE ledger_entries SET title='uncommitted' WHERE id=100")
        writer.finalize()  # Complete but not COMMITTED.
        with pytest.raises(ObservationError, match='ROOT_NOT_READY'):
            create(repository(sandbox))
        writer.rollback()
    create(repository(sandbox))


def test_expired_observation_does_not_resurrect_on_clock_rollback(sandbox):
    result = create(repository(sandbox))
    with pytest.raises(ObservationError, match='EXPIRED'):
        repository(sandbox, clock=lambda: NOW+timedelta(seconds=901)).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
    with pytest.raises(ObservationError, match='EXPIRED'):
        repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)


@pytest.mark.parametrize('change', ['date', 'offset', 'engine', 'policy', 'cancel', 'principal'])
def test_terminal_context_counterexamples(sandbox, change):
    current = [EVAL]
    ticket = [CREDENTIAL]
    def guard():
        return ticket[0]
    def fault(stage, conn):
        if stage != 'roots':
            return
        if change == 'date':
            current[0] = Evaluation(date(2026, 10, 6), 540)
        elif change == 'offset':
            current[0] = Evaluation(EVAL.today, 0)
        elif change == 'engine':
            current[0] = Evaluation(EVAL.today, 540, 'f'*64)
        elif change == 'principal':
            ticket[0] = BundleCredential('c'*64, 2)
        elif change == 'cancel':
            ticket[0] = None
        else:
            from app.services.card_charge.registry import POLICY_TIMELINES
            from dataclasses import replace
            card = next(iter(POLICY_TIMELINES))
            POLICY_TIMELINES[card] += (replace(POLICY_TIMELINES[card][-1], effective_from='2027-01'),)
    from app.services.card_charge.registry import POLICY_TIMELINES
    with patch.dict(POLICY_TIMELINES, POLICY_TIMELINES.copy(), clear=True):
        with pytest.raises((ObservationError, ValueError)):
            create(repository(sandbox, evaluation=lambda: current[0]), guard=guard, fault=fault)
    with sandbox.connect() as conn:
        assert not conn.execute('SELECT 1 FROM sync_observations').fetchone()


@pytest.mark.parametrize('limit', ['lease', 'metadata', 'records', 'deadline', 'total_bytes'])
def test_resource_limits(sandbox, limit):
    from isolated_sync.observation import Limits
    if limit == 'lease':
        with pytest.raises(ObservationError):
            Limits(lease_seconds=901)
        return
    if limit == 'metadata':
        limits = Limits(metadata_bytes=1024)
    elif limit == 'deadline':
        limits = Limits(transaction_seconds=0.000001)
    elif limit == 'total_bytes':
        limits = Limits(total_metadata_bytes=1024)
    else:
        limits = Limits(total_records=4)
        repo = repository(sandbox, limits=limits)
        for _ in range(4):
            create(repo)
    with pytest.raises(ObservationError):
        create(repository(sandbox, limits=limits))
    if limit == 'total_bytes':
        with sandbox.connect() as conn:
            assert conn.execute('SELECT used_bytes FROM sync_observation_budget WHERE id=1').fetchone()[0] == 0
            assert not conn.execute('SELECT 1 FROM sync_observation_pins').fetchone()


@pytest.mark.parametrize('defect', ['raw', 'index', 'principal', 'versions', 'epoch', 'revision'])
def test_base_mismatch_rejected(sandbox, defect):
    from copy import deepcopy
    from isolated_sync.roots import sync_root
    target = deepcopy(create(repository(sandbox))['target'])
    if defect in ('raw', 'index'):
        target[defect+'_ref']['hash'] = 'f'*64
    elif defect == 'principal':
        target['principal_id'] = 2
    elif defect == 'versions':
        target['versions']['projection_schema'] = 'f'*64
    elif defect == 'epoch':
        target['ns']['epoch'] = str(uuid4())
    else:
        target['revision'] = str(int(target['revision'])+1)
    target.pop('sync_root')
    target['sync_root'] = sync_root(target)
    with pytest.raises(ObservationError):
        create(repository(sandbox), base=target)


def lease_state(db):
    """Independent fresh-connection evidence, not the serialized response."""
    with sqlite3.connect(db.path) as conn:
        return (dict(conn.execute('SELECT id,status FROM sync_observations')),
                list(conn.execute('SELECT observation_id,role,hash,active FROM sync_observation_pins ORDER BY observation_id,role')),
                conn.execute('SELECT used_bytes FROM sync_observation_budget').fetchone()[0])


@pytest.mark.parametrize('operation', ['lookup', 'roots', 'retry'])
@pytest.mark.parametrize('initial,terminal', [(900, 900), (899, 900), (899, 901)])
def test_terminal_lease_expiry_is_sticky(sandbox, operation, initial, terminal):
    result = create(repository(sandbox))
    before = raw_state(sandbox)
    pins = lease_state(sandbox)[1]
    # Retry has one extra create guard before the two shared lookup guards.
    times = iter(([initial] if operation == 'retry' else []) + [initial, terminal])
    repo = repository(sandbox, clock=lambda: NOW+timedelta(seconds=next(times)))
    with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED') as error:
        if operation == 'retry':
            create(repo, request_id=result['request_id'])
        else:
            getattr(repo, operation)(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
    assert error.value.action == 'new_observation'
    assert lease_state(sandbox)[0] == {result['observation_id']: 'retired'}
    assert lease_state(sandbox)[1] == pins
    # New repository/connection and a rolled-back clock cannot resurrect it.
    for _ in range(2):
        with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
            repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
    assert raw_state(sandbox) == before


def test_quota_replacement_clock_rollback(sandbox):
    old = [create(repository(sandbox)) for _ in range(4)]
    pins = lease_state(sandbox)[1]
    now = NOW+timedelta(seconds=901)
    fresh = [create(repository(sandbox, clock=lambda: now)) for _ in range(4)]
    states, current_pins, _ = lease_state(sandbox)
    assert all(states[r['observation_id']] == 'retired' for r in old)
    assert sum(s == 'available' for s in states.values()) == 4
    assert len(current_pins) == 40 and all(p[3] == 1 for p in current_pins)
    assert all(pin in current_pins for pin in pins)
    for result in old:
        with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
            repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
    for result in fresh:
        assert repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL) == result
    with pytest.raises(ObservationError, match='LEASE_LIMIT'):
        create(repository(sandbox))


@pytest.mark.parametrize('operation', ['lookup', 'roots', 'retry'])
def test_terminal_before_expiry_remains_valid(sandbox, operation):
    result = create(repository(sandbox))
    repo = repository(sandbox, clock=lambda: NOW+timedelta(seconds=899))
    if operation == 'retry':
        assert create(repo, request_id=result['request_id']) == result
    else:
        value = getattr(repo, operation)(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
        assert value == (result if operation == 'lookup' else {k: result['target'][k+'_ref'] for k in ('raw', 'index', 'hot', 'control')})
    assert lease_state(sandbox)[0] == {result['observation_id']: 'available'}


@pytest.mark.parametrize('failure', ['records', 'metadata', 'total_bytes', 'pin', 'before_commit', 'auth', 'context', 'new_expiry'])
def test_sticky_quota_retirement_survives_failed_publication(sandbox, failure):
    from isolated_sync.observation import Limits
    old = [create(repository(sandbox)) for _ in range(4)]
    before = raw_state(sandbox)
    _, pins, budget = lease_state(sandbox)
    with sqlite3.connect(sandbox.path) as conn:
        objects = list(conn.execute('SELECT * FROM sync_objects ORDER BY hash'))
        views = list(conn.execute('SELECT * FROM sync_observation_views ORDER BY identity'))
    limits = {'records': Limits(total_records=4), 'metadata': Limits(metadata_bytes=1024),
              'total_bytes': Limits(total_metadata_bytes=1024)}.get(failure, Limits())
    current = [EVAL]
    def fault(stage, conn):
        if failure == 'pin' and stage == 'pin_index':
            raise sqlite3.IntegrityError('synthetic pin failure')
        if stage == 'before_commit':
            if failure == 'before_commit':
                raise RuntimeError('synthetic publication failure')
            if failure == 'auth':
                conn.execute('DELETE FROM auth_sessions')
            if failure == 'context':
                current[0] = Evaluation(date(2026, 10, 6), 540)
    times = iter([901, 901, 1801])
    clock = (lambda: NOW+timedelta(seconds=next(times))) if failure == 'new_expiry' else lambda: NOW+timedelta(seconds=901)
    with pytest.raises((ObservationError, RuntimeError, sqlite3.IntegrityError)):
        create(repository(sandbox, clock=clock, limits=limits, evaluation=lambda: current[0]), fault=fault)
    # Fresh SQLite, not a cached object. ONLY retirement survived; candidate
    # hot/control/view/pins/budget and injected auth deletion were rolled back.
    states, after_pins, after_budget = lease_state(sandbox)
    assert states == {r['observation_id']: 'retired' for r in old}
    assert after_pins == pins and after_budget == budget
    with sqlite3.connect(sandbox.path) as conn:
        assert list(conn.execute('SELECT * FROM sync_objects ORDER BY hash')) == objects
        assert list(conn.execute('SELECT * FROM sync_observation_views ORDER BY identity')) == views
    assert raw_state(sandbox) == before


def test_quota_rejection_preserves_expired_and_live_memberships(sandbox):
    from isolated_sync.observation import Limits
    expired = [create(repository(sandbox, limits=Limits(lease_seconds=10))) for _ in range(3)]
    live = create(repository(sandbox))
    with pytest.raises(ObservationError, match='LEASE_LIMIT'):
        create(repository(sandbox, clock=lambda: NOW+timedelta(seconds=11), limits=Limits(observations_per_principal=1)))
    states, pins, _ = lease_state(sandbox)
    assert all(states[r['observation_id']] == 'retired' for r in expired)
    assert states[live['observation_id']] == 'available'
    assert len(pins) == 20 and all(pin[3] == 1 for pin in pins)


def test_retirement_scope_and_original_auth_guards(sandbox):
    other = BundleCredential('c'*64, 2)
    first = create(repository(sandbox), credential=other)
    old = create(repository(sandbox))
    create(repository(sandbox, clock=lambda: NOW+timedelta(seconds=901)), credential=BundleCredential('b'*64, 1))
    states = lease_state(sandbox)[0]
    assert states[old['observation_id']] == 'retired'
    assert states[first['observation_id']] == 'available'  # Other owner is not swept.
    for cred in (other, BundleCredential('b'*64, 1)):
        with pytest.raises(ObservationError, match='PRINCIPAL_OR_SESSION_CHANGED'):
            repository(sandbox).lookup(old['observation_id'], cred, guard=lambda: cred)
    with pytest.raises(ObservationError, match='PRINCIPAL_OR_SESSION_CHANGED'):
        repository(sandbox).lookup(old['observation_id'], CREDENTIAL, guard=lambda: None)
    for operation in ('lookup', 'roots'):
        for _ in range(2):
            with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
                getattr(repository(sandbox), operation)(old['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
    with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
        create(repository(sandbox), request_id=old['request_id'])


def test_concurrent_quota_replacement_is_atomic(sandbox):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from isolated_sync.observation import Limits
    old = [create(repository(sandbox)) for _ in range(4)]
    ready = Barrier(5)
    def replace(_):
        ready.wait(10)
        try:
            return create(repository(sandbox, clock=lambda: NOW+timedelta(seconds=901), limits=Limits(lock_wait_ms=5000)))
        except ObservationError as error:
            return error.code
    with ThreadPoolExecutor(5) as pool:
        results = list(pool.map(replace, range(5)))
    assert sum(type(r) is dict for r in results) == 4
    assert results.count('LEASE_LIMIT') == 1
    states, pins, _ = lease_state(sandbox)
    assert all(states[r['observation_id']] == 'retired' for r in old)
    assert sum(s == 'available' for s in states.values()) == 4
    assert len(pins) == 40 and all(pin[3] == 1 for pin in pins)


@pytest.mark.parametrize('path', ['lookup', 'quota_error'])
@pytest.mark.parametrize('boundary', ['before_commit', 'after_commit'])
def test_retirement_process_crash_boundary(sandbox, path, boundary):
    import multiprocessing
    import os
    import signal
    from isolated_sync.observation import Limits
    from isolated_sync.observation_schema import ObservationConnection
    result = create(repository(sandbox))
    if path == 'quota_error':
        for _ in range(3):
            create(repository(sandbox))
    before = raw_state(sandbox)
    pins = lease_state(sandbox)[1]
    original = ObservationConnection.commit
    def child():
        def commit(conn):
            if boundary == 'before_commit':
                os.kill(os.getpid(), signal.SIGKILL)
            original(conn)
            os.kill(os.getpid(), signal.SIGKILL)
        with patch.object(ObservationConnection, 'commit', commit):
            repo = repository(sandbox, clock=lambda: NOW+timedelta(seconds=901), limits=Limits(total_records=4))
            if path == 'lookup':
                repo.lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
            else:
                create(repo)
    process = multiprocessing.get_context('fork').Process(target=child)
    process.start()
    process.join(10)
    assert not process.is_alive() and process.exitcode == -signal.SIGKILL
    states, after_pins, _ = lease_state(sandbox)
    assert set(states.values()) == ({'retired'} if boundary == 'after_commit' else {'available'})
    assert after_pins == pins and raw_state(sandbox) == before
    if boundary == 'after_commit':
        # New process/repository with old wall clock still cannot authorize.
        with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
            repository(sandbox).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
    else:
        # No expiry response was delivered before the crash/rollback. A later
        # detection at the expired clock must commit retirement normally.
        with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
            repository(sandbox, clock=lambda: NOW+timedelta(seconds=901)).lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
        assert lease_state(sandbox)[0][result['observation_id']] == 'retired'


def test_retirement_queries_use_existing_quota_index(sandbox):
    from isolated_sync.canonical import encode
    result = create(repository(sandbox))
    with sqlite3.connect(sandbox.path) as conn:
        queries = [
            ("UPDATE sync_observations SET status='retired' WHERE principal_id=? AND status='available' AND expires_at<=? AND namespace=? RETURNING id",
             (1, '2026-10-05T00:15:01Z', encode(result['target']['ns']))),
            ("SELECT count(*) FROM sync_observations WHERE principal_id=? AND status='available'", (1,)),
        ]
        for sql, parameters in queries:
            plan = [r[3] for r in conn.execute('EXPLAIN QUERY PLAN '+sql, parameters)]
            assert any('SEARCH sync_observations USING' in p and 'sync_observation_quota' in p for p in plan)
            assert not any('SCAN sync_observations' in p for p in plan)


@pytest.mark.parametrize('path', ['lookup', 'quota_error'])
def test_retirement_commit_failure_is_not_reported_as_durable_expiry(sandbox, path):
    from isolated_sync.observation import Limits
    from isolated_sync.observation_schema import ObservationConnection
    result = create(repository(sandbox))
    if path == 'quota_error':
        for _ in range(3):
            create(repository(sandbox))
    before = lease_state(sandbox)
    repo = repository(sandbox, clock=lambda: NOW+timedelta(seconds=901), limits=Limits(total_records=4))
    with patch.object(ObservationConnection, 'commit', side_effect=sqlite3.OperationalError('synthetic commit failure')):
        with pytest.raises(ObservationError, match='ROOT_NOT_READY' if path == 'lookup' else 'PIN_TRANSACTION_FAILED'):
            if path == 'lookup':
                repo.lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
            else:
                create(repo)
    assert lease_state(sandbox) == before
    with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
        repo.lookup(result['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
    assert lease_state(sandbox)[0][result['observation_id']] == 'retired'


def test_retry_expiry_commits_only_retirement(sandbox):
    result = create(repository(sandbox))
    before = raw_state(sandbox)
    def fault(stage, conn):
        if stage == 'validation':
            conn.execute('DELETE FROM auth_sessions WHERE user_id=2')
    with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
        create(repository(sandbox, clock=lambda: NOW+timedelta(seconds=901)), request_id=result['request_id'], fault=fault)
    assert lease_state(sandbox)[0] == {result['observation_id']: 'retired'}
    assert raw_state(sandbox) == before

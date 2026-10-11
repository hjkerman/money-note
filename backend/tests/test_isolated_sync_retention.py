"""D3c: owned file-backed SQLite, independent graph and persisted-state oracles.

The oracle below parses actual C1 references, not production retention roots,
PathResolver, Store.edges or Collector.mark. Faults are synthetic only.
"""

import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import random
import signal
import sqlite3
from threading import Event
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app import auth
from app.services.authoritative_state import BundleCredential
from isolated_sync.canonical import CanonicalError, encode
from isolated_sync.facts import build_facts
from isolated_sync.http import create_app
from isolated_sync.observation import Limits, ObservationError, accepted_generation
from isolated_sync.patricia import Index
from isolated_sync.retention import Collector, RetentionRepository
from isolated_sync.retention_schema import RetentionSandbox, VERSION
from isolated_sync.raw import TABLES
from tests.test_isolated_sync_finalization import verify
from tests.test_isolated_sync_observation import EVAL, NOW
from tests.test_isolated_sync_transfer import TOKEN_A, TOKEN_B, URL, headers, observe, request, graph_child
from tests.test_isolated_sync_transfer_cancellation import Barrier, Rig, cancel

pytest_plugins = ('tests.test_isolated_sync_transfer',)
CRED = BundleCredential(auth._hash_session_token(TOKEN_A), 1)


@pytest.fixture
def db(template):
    with RetentionSandbox() as value:
        with sqlite3.connect(template.path) as source, sqlite3.connect(value.path) as target:
            source.backup(target)
        value.install()
        yield value


def repo(db, **kwargs):
    return RetentionRepository(db, clock=kwargs.pop('clock', lambda: NOW), evaluation=lambda: EVAL, **kwargs)


def create(repository, **kwargs):
    return repository.create(CRED, guard=lambda: CRED, request_id=kwargs.pop('request_id', str(uuid4())), **kwargs)


def mutate(db, value='next'):
    with db.connect() as conn:
        conn.begin_capture()
        conn.execute('UPDATE app_labels SET value=? WHERE key=?', (value, 'd1-label'))
        metrics = conn.finalize()
        conn.commit()
        return metrics


def state(db):
    with sqlite3.connect(db.path, timeout=1) as conn:
        # Fresh connection also proves no leaked worker/migration write lock.
        conn.execute('BEGIN IMMEDIATE')
        result = {t: conn.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall()
                  for t in (*TABLES, 'authoritative_state_revision', 'sync_current', 'sync_commits',
                            'sync_capture_commits', 'sync_tx_fence', 'sync_authority_fence')}
        conn.rollback()
        return result


def objects(db):
    with sqlite3.connect(db.path) as conn:
        return {r[0]: bytes(r[1]) for r in conn.execute('SELECT hash,body FROM sync_objects')}


def oracle(db):
    """Independent retained-root enumeration + exact domain SHA-256 traversal."""
    stored = objects(db)
    with sqlite3.connect(db.path) as conn:
        current = conn.execute('SELECT raw_hash,index_hash,tx_id FROM sync_current').fetchone()
        roots = list(current[:2])+[conn.execute('SELECT input_hash FROM sync_commits WHERE tx_id=?', (current[2],)).fetchone()[0]]
        roots += [r[0] for r in conn.execute('SELECT hash FROM sync_observation_pins WHERE active=1')]
        roots += [r[0] for r in conn.execute("SELECT hash FROM sync_retention_roots WHERE scope='explicit'")]
    reached, pending = set(), roots[:]
    while pending:
        digest = pending.pop()
        if digest in reached:
            continue
        raw = stored[digest]
        body = json.loads(raw)
        assert hashlib.sha256(b'money-note.sync.v1/'+body['kind'].encode()+b'\0'+raw).hexdigest() == digest
        assert encode(body) == raw
        reached.add(digest)
        for child in graph_child(body):
            assert len(stored[child['hash']]) == int(child['bytes'])
            pending.append(child['hash'])
    return reached, set(stored)-reached


def valid(db):
    with db.connect() as conn:
        accepted_generation(conn)
        verify(conn)
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    reached, _ = oracle(db)
    assert reached <= objects(db).keys()


def boom(stage):
    def fault(at, conn):
        if stage == at:
            raise RuntimeError('synthetic '+stage)
    return fault


def test_versioned_migration_preserves_evidence_and_raw_rows(template):
    from isolated_sync.observation import ObservationRepository
    with RetentionSandbox() as db:
        with sqlite3.connect(template.path) as source, sqlite3.connect(db.path) as target:
            source.backup(target)
        legacy = ObservationRepository(db, clock=lambda: NOW, evaluation=lambda: EVAL)
        terminal, active = create(legacy), create(legacy)
        expired = ObservationRepository(db, clock=lambda: NOW+timedelta(seconds=900), evaluation=lambda: EVAL)
        with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
            expired.lookup(terminal['observation_id'], CRED, guard=lambda: CRED)
        before = state(db)
        with pytest.raises(RuntimeError):
            db.install(fault=boom('migration'))
        assert state(db) == before
        with sqlite3.connect(db.path) as conn:
            assert conn.execute('PRAGMA user_version').fetchone()[0] == 1_000_004
        db.install()
        db.install()
        assert state(db) == before
        with db.connect() as conn:
            assert conn.execute('PRAGMA user_version').fetchone()[0] == VERSION
            for table in ('sync_commits', 'sync_observations', 'sync_observation_pins'):
                assert not any(r['table'] == 'sync_objects' for r in conn.execute('PRAGMA foreign_key_list('+table+')'))
            assert any(r['table'] == 'sync_commits' for r in conn.execute('PRAGMA foreign_key_list(sync_authority_fence)'))
            assert conn.execute('SELECT count(*) FROM sync_observation_lifecycle WHERE released=0').fetchone()[0] == 2
        assert repo(db).lookup(active['observation_id'], CRED, guard=lambda: CRED) == active
        with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
            repo(db).lookup(terminal['observation_id'], CRED, guard=lambda: CRED)
        valid(db)


def test_historical_certificate_only_objects_reclaimed_and_writer_restarts(db):
    baseline = state(db)
    for n in range(3):
        mutate(db, str(n))
    before = state(db)
    collector = Collector(repo(db))
    reached, expected = oracle(db)
    assert expected
    mark = collector.mark()
    assert mark.reachable == reached and set(dict(mark.candidates)) == expected
    dry = collector.collect()
    assert dry['objects_deleted'] == 0 and state(db) == before
    result = collector.collect(apply=True, batch=7, max_batches=100)
    assert result['objects_deleted'] == len(expected)
    assert objects(db).keys() == reached
    assert state(db) == before  # EVERY historical evidence/fence row survives.
    assert baseline['ledger_entries'] == before['ledger_entries']
    assert collector.collect(apply=True)['objects_deleted'] == 0
    valid(db)
    mutate(db, 'after-gc')
    valid(db)
    assert create(repo(db))['target']['revision'] != str(baseline['sync_current'][0][2])


def test_active_old_generation_and_shared_subtrees_survive(db):
    repository = repo(db)
    old = create(repository)
    old_objects = oracle(db)[0]
    mutate(db)
    new = create(repository)
    before = state(db)
    collector = Collector(repository)
    collector.collect(apply=True)
    assert old_objects <= objects(db).keys()
    repository.release(old['observation_id'], CRED, guard=lambda: CRED)
    reached, garbage = oracle(db)
    assert garbage
    collector.collect(apply=True)
    assert objects(db).keys() == reached
    assert old_objects & reached  # shared descendants, not newest-only sweep.
    assert repository.lookup(new['observation_id'], CRED, guard=lambda: CRED) == new
    assert state(db) == before
    valid(db)


@pytest.mark.parametrize('stage', ['retired', 'release_raw', 'release_index', 'release_input', 'release_hot', 'release_control', 'before_commit'])
def test_release_fault_rolls_back_all_pins_sticky_retirement(db, stage):
    repository = repo(db)
    m = create(repository)
    before = objects(db)
    with pytest.raises(RuntimeError):
        repository.release(m['observation_id'], CRED, guard=lambda: CRED, fault=boom(stage))
    with sqlite3.connect(db.path) as conn:
        assert conn.execute('SELECT status FROM sync_observations').fetchone()[0] == 'retired'
        assert conn.execute('SELECT sum(active) FROM sync_observation_pins').fetchone()[0] == 5
        assert conn.execute('SELECT released FROM sync_observation_lifecycle').fetchone()[0] == 0
    assert objects(db) == before
    assert oracle(db)[0] == Collector(repository).mark().reachable
    repository.release(m['observation_id'], CRED, guard=lambda: CRED)
    repository.release(m['observation_id'], CRED, guard=lambda: CRED)
    with sqlite3.connect(db.path) as conn:
        assert conn.execute('SELECT sum(active) FROM sync_observation_pins').fetchone()[0] == 0
        assert conn.execute('SELECT min(pins) FROM sync_gc_counts').fetchone()[0] >= 0


def test_concurrent_release_exact_once_and_wrong_original_credential(db):
    repository = repo(db)
    m = create(repository)
    with pytest.raises(ObservationError):
        repository.release(m['observation_id'], BundleCredential(auth._hash_session_token(TOKEN_B), 2), guard=lambda: CRED)
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda _: repository.release(m['observation_id'], CRED, guard=lambda: CRED), range(2)))
    valid(db)
    assert len(Collector(repository).mark().reachable) < len(objects(db))


def test_expiry_reclaim_nonce_replay_and_clock_rollback(db):
    clock = [NOW]
    repository = repo(db, clock=lambda: clock[0])
    nonce = str(uuid4())
    m = create(repository, request_id=nonce)
    clock[0] += timedelta(seconds=900)
    with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
        repository.lookup(m['observation_id'], CRED, guard=lambda: CRED)
    result = repository.maintain()
    assert result['released'] == result['metadata_reclaimed'] == 1
    clock[0] = NOW
    restarted = repo(db, clock=lambda: clock[0])
    for operation in (lambda: restarted.lookup(m['observation_id'], CRED, guard=lambda: CRED),
                      lambda: create(restarted, request_id=nonce)):
        with pytest.raises(ObservationError, match='OBSERVATION_(EXPIRED|INCOMPLETE)'):
            operation()
    with sqlite3.connect(db.path) as conn:
        assert conn.execute('SELECT count(*) FROM sync_observations').fetchone()[0] == 0
        assert conn.execute('SELECT used_bytes FROM sync_observation_budget').fetchone()[0] == 512
    assert create(restarted)['observation_id'] != m['observation_id']
    valid(db)


@pytest.mark.parametrize('invalidate', ['revoke', 'epoch'])
def test_replay_evidence_reclaimed_only_after_context_invalidated(db, invalidate):
    repository = repo(db)
    m = create(repository)
    repository.release(m['observation_id'], CRED, guard=lambda: CRED)
    repository.maintain()
    if invalidate == 'revoke':
        with db.connect() as conn:
            conn.execute('DELETE FROM auth_sessions WHERE session_token_hash=?', (CRED.token_hash,))
    else:
        db.bootstrap()
    repository.maintain()
    with sqlite3.connect(db.path) as conn:
        assert conn.execute('SELECT count(*) FROM sync_observation_replays').fetchone()[0] == 0
        assert conn.execute('SELECT used_bytes FROM sync_observation_budget').fetchone()[0] == 0
    with pytest.raises(ObservationError):
        repository.lookup(m['observation_id'], CRED, guard=lambda: CRED)
    Collector(repository).collect(apply=True)
    valid(db)


def test_sustained_quota_and_metadata_budget_recovery(db):
    clock = [NOW]
    repository = repo(db, clock=lambda: clock[0], limits=Limits(total_records=4, total_metadata_bytes=500_000))
    identities = set()
    for _ in range(5):
        current = [create(repository) for _ in range(4)]
        assert not identities & {m['observation_id'] for m in current}
        identities.update(m['observation_id'] for m in current)
        with pytest.raises(ObservationError, match='LEASE_LIMIT'):
            create(repository)
        clock[0] += timedelta(seconds=901)
        repository.maintain()
        with sqlite3.connect(db.path) as conn:
            assert conn.execute('SELECT count(*) FROM sync_observations').fetchone()[0] == 0
            assert conn.execute('SELECT count(*) FROM sync_observation_pins').fetchone()[0] == 0
    Collector(repository).collect(apply=True)
    assert all(len(h) == 36 for h in identities)
    valid(db)


@pytest.mark.parametrize('change', ['writer', 'observer', 'explicit', 'epoch', 'other_gc'])
def test_stale_mark_aborts_before_any_delete(db, change):
    repository = repo(db)
    collector = Collector(repository)
    mutate(db)
    plan = collector.mark()
    assert plan.candidates
    if change == 'writer':
        mutate(db, 'newer')
    elif change == 'observer':
        create(repository)
    elif change == 'explicit':
        # An explicit raw root obligation, not a new transfer credential.
        raw = next((h, b) for h, b in objects(db).items() if json.loads(b)['kind'] == 'raw-root')
        collector.protect(str(uuid4()), {'raw': dict(hash=raw[0], bytes=str(len(raw[1])))})
    elif change == 'epoch':
        db.bootstrap()
    else:
        Collector(repository).collect(apply=True)
    before = objects(db)
    with pytest.raises(CanonicalError, match='REJECT_GC_STALE_MARK'):
        collector.sweep(plan)
    assert objects(db) == before
    valid(db)


@pytest.mark.parametrize('stage', ['deleted', 'row_deleted', 'before_commit'])
def test_deletion_transaction_rollback_preserves_every_object(db, stage):
    mutate(db)
    collector = Collector(repo(db))
    plan = collector.mark()
    before = objects(db), state(db)
    with pytest.raises(RuntimeError):
        collector.sweep(plan, fault=boom(stage))
    assert (objects(db), state(db)) == before
    valid(db)


@pytest.mark.parametrize('table,column', [('sync_objects', 'body'), ('sync_gc_counts', 'incoming'),
                                        ('sync_object_edges', 'child'), ('sync_commits', 'raw_hash'),
                                        ('sync_observation_pins', 'hash'), ('sync_observation_lifecycle', 'released')])
def test_corrupt_retention_metadata_blocks_gc_without_deletion(db, table, column):
    create(repo(db))
    # Direct synthetic corruption is intentional; never through a normal DB.
    with sqlite3.connect(db.path) as conn:
        conn.execute('PRAGMA foreign_keys=OFF')
        if table == 'sync_objects':
            conn.execute("UPDATE sync_objects SET body=? WHERE rowid=(SELECT min(rowid) FROM sync_objects)", (b'{}',))
        elif table == 'sync_gc_counts':
            conn.execute('UPDATE sync_gc_counts SET incoming=incoming+1 WHERE rowid=(SELECT min(rowid) FROM sync_gc_counts)')
        elif table == 'sync_object_edges':
            conn.execute("UPDATE sync_object_edges SET child=? WHERE rowid=(SELECT min(rowid) FROM sync_object_edges)", ('a'*64,))
        elif table == 'sync_commits':
            conn.execute('UPDATE sync_commits SET raw_hash=?', ('a'*64,))
        elif table == 'sync_observation_pins':
            conn.execute('UPDATE sync_observation_pins SET hash=? WHERE role=?', ('a'*64, 'raw'))
        else:
            conn.execute('UPDATE sync_observation_lifecycle SET released=1')
    before = objects(db)
    with pytest.raises((CanonicalError, ObservationError, sqlite3.DatabaseError, KeyError)):
        Collector(repo(db)).collect(apply=True)
    assert objects(db) == before


def test_missing_required_descendant_and_unknown_schema_fail_closed(db):
    with sqlite3.connect(db.path) as conn:
        # Drop guard only in this deliberately corrupted disposable fixture.
        conn.execute('DROP TRIGGER sync_gc_object_delete')
        digest = conn.execute("SELECT hash FROM sync_objects WHERE kind='index-leaf' LIMIT 1").fetchone()[0]
        conn.execute('DELETE FROM sync_objects WHERE hash=?', (digest,))
    before = objects(db)
    with pytest.raises(CanonicalError):
        Collector(repo(db)).collect(apply=True)
    assert objects(db) == before


def test_positive_synthetic_ownership_and_default_runtime_isolation(db):
    repository = repo(db)
    with patch.object(db, '_owned_file', (-1, -1)):
        with pytest.raises(CanonicalError, match='REJECT_SYNTHETIC_OWNERSHIP'):
            Collector(repository).collect(apply=True)
    source = Path(__file__).resolve().parents[1]/'app'
    assert not any('isolated_sync' in p.read_text() for p in source.rglob('*.py'))
    with TestClient(create_app(repository)) as c:
        assert c.post('/api/sync/v1/gc', headers=headers()).status_code == 404


@pytest.mark.parametrize('operation,stage', [('release', 'release_index'), ('release', 'after_commit'),
                                          ('gc', 'marked'), ('gc', 'deleted'), ('gc', 'before_commit'),
                                          ('gc', 'after_commit'), ('maintain', 'reclaimed'), ('maintain', 'after_commit')])
def test_real_process_interruption_recovery(db, operation, stage):
    repository = repo(db)
    m = create(repository)
    mutate(db)
    before = state(db)
    # fork inherits ONLY this owned synthetic path; actual SIGKILL, not a mock.
    def child():
        worker = repo(db)
        def kill(at, conn):
            if at == stage:
                os.kill(os.getpid(), signal.SIGKILL)
        if operation == 'release':
            worker.release(m['observation_id'], CRED, guard=lambda: CRED, fault=kill)
        elif operation == 'maintain':
            worker.release(m['observation_id'], CRED, guard=lambda: CRED)
            worker.maintain(fault=kill)
        else:
            worker.release(m['observation_id'], CRED, guard=lambda: CRED)
            Collector(worker).collect(apply=True, fault=kill)
    process = multiprocessing.get_context('fork').Process(target=child)
    process.start()
    process.join(20)
    assert not process.is_alive() and process.exitcode == -signal.SIGKILL
    assert state(db) == before
    valid(db)
    repository.maintain()
    Collector(repository).collect(apply=True)
    valid(db)


@pytest.mark.parametrize('cancel_request', [False, True])
def test_actual_asgi_transfer_gc_serialization_and_native_cancel(db, cancel_request):
    clock = [NOW]
    repository = repo(db, clock=lambda: clock[0])
    with TestClient(create_app(repository)) as c:
        manifest = observe(c).json()
    mutate(db)
    before = state(db)
    collector = Collector(repository)
    planned = collector.mark()
    async def scenario():
        barrier = Barrier(asyncio.get_running_loop(), 'objects_prepared')
        rig = Rig(db, manifest)
        rig.adapter.repo = repository
        rig.adapter.transfer.observation = repository
        rig.adapter.fault = barrier.fault
        messages = []
        task = asyncio.create_task(rig.invoke(messages))
        try:
            await barrier.wait()
            clock[0] += timedelta(seconds=900)
            if cancel_request:
                await cancel(task)
                assert rig.adapter.workers.snapshot()['running'] == 1
                assert barrier.tickets[0].cancelled.is_set()
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                await asyncio.to_thread(collector.sweep, planned)
            assert planned.reachable <= objects(db).keys()
        finally:
            barrier.release.set()
            if not cancel_request:
                await task
            await rig.drain()
        if cancel_request:
            assert messages == []
        else:
            assert messages[0]['status'] == 410
            assert b'OBSERVATION_EXPIRED' in messages[1]['body']
    asyncio.run(scenario())
    collector.collect(apply=True)
    assert state(db) == before
    valid(db)


def http_reconstruct(c, manifest):
    """Walk ONLY HTTP-returned parents, independently decode/hash all chunks."""
    target = manifest['target']
    pending = [[target[r+'_ref']['hash']] for r in ('raw', 'index', 'hot', 'control')]
    result, refs = {}, {target[r+'_ref']['hash']: target[r+'_ref'] for r in ('raw', 'index', 'hot', 'control')}
    while pending:
        paths, pending = pending[:32], pending[32:]
        body = dict(protocol=1, request_id=str(uuid4()), items=[dict(path=p, offset='0', length=int(refs[p[-1]]['bytes'])) for p in paths])
        response = c.post(URL+'/'+manifest['observation_id']+'/objects', json=body, headers=headers())
        assert response.status_code == 200, response.text[:150]
        for path, chunk in zip(paths, response.json()['chunks']):
            raw = base64.b64decode(chunk['data_base64'], validate=True)
            value = json.loads(raw)
            digest = hashlib.sha256(b'money-note.sync.v1/'+value['kind'].encode()+b'\0'+raw).hexdigest()
            assert digest == path[-1] and len(raw) == int(refs[digest]['bytes']) and encode(value) == raw
            if digest in result:
                assert result[digest] == value
                continue
            result[digest] = value
            for child in graph_child(value):
                refs[child['hash']] = child
                pending.append(path+[child['hash']])
    rows = {t: [] for t in TABLES}
    facts = []
    for value in result.values():
        if value['kind'] == 'snapshot-leaf':
            rows[value['table']].extend(item['value'] for item in value['rows'])
        elif value['kind'] == 'index-leaf':
            facts.extend(value['facts'])
    return result, rows, facts


def test_post_gc_all_eleven_tables_patricia_and_immutable_old_target(db):
    repository = repo(db)
    with TestClient(create_app(repository)) as c:
        old = observe(c).json()
        old_bytes = encode(old)
        with db.connect() as conn:
            from isolated_sync.facts import read_state
            old_state = read_state(conn)
        mutate(db)
        new = observe(c).json()
        with db.connect() as conn:
            new_state = read_state(conn)
        Collector(repository).collect(apply=True)
        for manifest, expected in ((old, old_state), (new, new_state)):
            rebuilt, rows, facts = http_reconstruct(c, manifest)
            assert len(rows) == 11
            for table in TABLES:
                assert sorted(map(encode, rows[table])) == sorted(map(encode, expected[table]))
            context = accepted_context(manifest)
            catalog = build_facts(context, expected)
            assert sorted(map(encode, facts)) == sorted(encode(f.wire()) for f in catalog)
            index = Index.build(context, catalog).object()
            assert index.hash == manifest['target']['index_ref']['hash']
            assert len(rebuilt[manifest['target']['hot_ref']['hash']]['state']) == 12
        assert encode(repository.lookup(old['observation_id'], CRED, guard=lambda: CRED)) == old_bytes
    valid(db)


def accepted_context(manifest):
    from isolated_sync.canonical import Context, Namespace
    from isolated_sync.finalization import RAW_SCHEMA
    return Context(Namespace(**manifest['target']['ns']), RAW_SCHEMA)


def test_normal_http_requests_do_not_scan_history_or_gc_graph(db):
    repository = repo(db)
    with TestClient(create_app(repository)) as c:
        m = observe(c).json()
        calls = []
        original = db.connect
        def traced():
            conn = original()
            conn.set_trace_callback(calls.append)
            return conn
        with patch.object(db, 'connect', traced):
            response = c.post(URL+'/'+m['observation_id']+'/objects', json=request([m['target']['raw_ref']['hash']]), headers=headers())
        assert response.status_code == 200
        selects = [s.lower() for s in calls if s.lstrip().upper().startswith('SELECT')]
        assert not any(' from '+t in sql for sql in selects for t in ('sync_rows', 'sync_object_edges', 'sync_gc_counts', 'ledger_entries'))
        assert all('where hash=' in sql for sql in selects if ' from sync_objects' in sql)


def test_http_release_same_original_credential_idempotent_and_no_gc_route(db):
    repository = repo(db)
    with TestClient(create_app(repository)) as c:
        m = observe(c).json()
        endpoint = URL+'/'+m['observation_id']
        assert c.delete(endpoint).status_code == 401
        assert c.delete(endpoint, headers=headers(TOKEN_B)).status_code == 403
        assert c.delete(endpoint, headers=headers()).status_code == 204
        assert c.delete(endpoint, headers=headers()).status_code == 204
        repository.maintain()
        assert c.delete(endpoint, headers=headers()).status_code == 204
        assert c.post(endpoint+'/objects', json=request([m['target']['raw_ref']['hash']]), headers=headers()).status_code == 410
    valid(db)


@pytest.mark.parametrize('publication', ['writer', 'observer'])
def test_publication_commits_during_mark_snapshot_then_sweep_aborts(db, publication):
    repository = repo(db)
    collector = Collector(repository)
    entered, proceed = Event(), Event()
    def pause(stage, conn):
        if stage == 'marked':
            entered.set()
            assert proceed.wait(10)
    with ThreadPoolExecutor(1) as pool:
        marking = pool.submit(collector.mark, fault=pause)
        try:
            assert entered.wait(10)
            if publication == 'writer':
                mutate(db, 'during-mark')
            else:
                create(repository)
        finally:
            proceed.set()
        plan = marking.result(10)
    before = objects(db)
    with pytest.raises(CanonicalError, match='REJECT_GC_STALE_MARK'):
        collector.sweep(plan)
    assert objects(db) == before
    valid(db)


@pytest.mark.parametrize('budget', ['records', 'bytes'])
def test_budget_rejection_does_not_release_active_observation(db, budget):
    repository = repo(db)
    first = create(repository)
    limits = Limits(total_records=4, total_metadata_bytes=1024) if budget == 'bytes' else Limits(total_records=4)
    if budget == 'records':
        create(repository)
        other = BundleCredential(auth._hash_session_token(TOKEN_B), 2)
        for _ in range(2):
            repository.create(other, guard=lambda: other, request_id=str(uuid4()))
    before = objects(db)
    with pytest.raises(ObservationError):
        create(repo(db, limits=limits))
    assert objects(db) == before
    assert repository.lookup(first['observation_id'], CRED, guard=lambda: CRED) == first
    valid(db)


def test_explicit_retention_release_and_cross_principal_shared_content(db):
    repository = repo(db)
    first = create(repository)
    second_cred = BundleCredential(auth._hash_session_token(TOKEN_B), 2)
    second = repository.create(second_cred, guard=lambda: second_cred, request_id=str(uuid4()))
    assert first['target']['raw_ref'] == second['target']['raw_ref']
    obligation = str(uuid4())
    collector = Collector(repository)
    collector.protect(obligation, {'raw': first['target']['raw_ref']})
    mutate(db)
    repository.release(first['observation_id'], CRED, guard=lambda: CRED)
    collector.collect(apply=True)
    assert repository.lookup(second['observation_id'], second_cred, guard=lambda: second_cred) == second
    repository.release(second['observation_id'], second_cred, guard=lambda: second_cred)
    collector.collect(apply=True)
    assert first['target']['raw_ref']['hash'] in objects(db)
    collector.unprotect(obligation)
    collector.unprotect(obligation)
    collector.collect(apply=True)
    assert first['target']['raw_ref']['hash'] not in objects(db)
    valid(db)


@pytest.mark.parametrize('field,value', [('canon', 2), ('kind', 'unknown-object'), ('raw_schema', 'a'*64)])
def test_unsupported_or_changed_canonical_object_fails_closed(db, field, value):
    with sqlite3.connect(db.path) as conn:
        digest, raw = conn.execute("SELECT hash,body FROM sync_objects WHERE kind='index-leaf' LIMIT 1").fetchone()
        body = json.loads(raw)
        body[field] = value
        conn.execute('UPDATE sync_objects SET body=? WHERE hash=?', (encode(body), digest))
    before = objects(db)
    with pytest.raises((CanonicalError, ObservationError)):
        Collector(repo(db)).collect(apply=True)
    assert objects(db) == before


def test_real_financial_writer_and_twelve_projections_after_historical_gc(db):
    from app.repositories.cash_flows import create_cash_flow
    from app.repositories.entries import update_entry
    from app.schemas import CashFlowIn, LedgerEntryPatch
    from app.services.authoritative_state import _construct, _prepare
    from isolated_sync.inputs import BoundedInputs
    from isolated_sync.observation import financial_scope, hot_projections
    for n in range(3):
        mutate(db, str(n))
    assert Collector(repo(db)).collect(apply=True)['objects_deleted'] > 0
    with db.connect() as conn:
        conn.begin_capture()
        writer = BoundedInputs(conn)
        update_entry(100, LedgerEntryPatch(amount_value=1200, usage_place='synthetic-shop'), conn=writer)
        create_cash_flow(CashFlowIn(occurred_on='2026-10-05', title='new after GC', amount_value=500, sort_order=1), conn=writer)
        conn.finalize()
        conn.commit()
        conn.execute('BEGIN IMMEDIATE')
        accepted, _, _ = accepted_generation(conn)
        with patch('app.services.judgment.common._MESSAGE_RANDOM', random.Random(66303)), financial_scope(conn, accepted) as scope:
            actual = hot_projections(scope, EVAL)
        with (patch('app.services.authoritative_state.CURRENT_SCHEMA_VERSION', VERSION),
              patch('app.services.authoritative_state._validate_revision_triggers'),
              patch('app.services.authoritative_state.app_today', return_value=EVAL.today),
              patch('app.services.judgment.common._MESSAGE_RANDOM', random.Random(66303))):
            bundle, _, _ = _construct(conn, CRED)
            expected = json.loads(_prepare(bundle).body)['state']
        assert len(actual) == 12 and actual == expected
    valid(db)


def test_reclaim_failure_retains_pins_or_terminal_evidence_atomically(db):
    repository = repo(db)
    first = create(repository)
    repository.release(first['observation_id'], CRED, guard=lambda: CRED)
    before = objects(db)
    with pytest.raises(RuntimeError):
        repository.maintain(fault=boom('reclaimed'))
    with sqlite3.connect(db.path) as conn:
        assert conn.execute('SELECT count(*) FROM sync_observations').fetchone()[0] == 1
        assert conn.execute('SELECT count(*) FROM sync_observation_pins').fetchone()[0] == 5
        assert conn.execute('SELECT count(*) FROM sync_observation_replays').fetchone()[0] == 0
    assert objects(db) == before
    valid(db)


def test_epoch_bootstrap_releases_old_pins_but_preserves_certificate_evidence(db):
    repository = repo(db)
    first = create(repository)
    old_objects = set(objects(db))
    before = state(db)
    db.bootstrap()
    with sqlite3.connect(db.path) as conn:
        assert conn.execute('SELECT status FROM sync_observations').fetchone()[0] == 'retired'
        assert conn.execute('SELECT sum(active) FROM sync_observation_pins').fetchone()[0] == 0
        assert conn.execute('SELECT released FROM sync_observation_lifecycle').fetchone()[0] == 1
    with pytest.raises(ObservationError, match='EPOCH_CHANGED'):
        repository.lookup(first['observation_id'], CRED, guard=lambda: CRED)
    result = Collector(repository).collect(apply=True)
    assert result['objects_deleted'] and not (old_objects & objects(db).keys())
    after = state(db)
    assert after['sync_commits'][:len(before['sync_commits'])] == before['sync_commits']
    assert all(after[t] == before[t] for t in TABLES)
    assert create(repository)['target']['ns'] != first['target']['ns']
    valid(db)


@pytest.mark.parametrize('temporary_invalidation', ['session_expiry', 'user_inactive'])
def test_reclaimed_manifest_nonce_survives_reversible_credential_invalidation(db, temporary_invalidation):
    clock = [NOW]
    repository = repo(db, clock=lambda: clock[0])
    nonce = str(uuid4())
    observation = create(repository, request_id=nonce)
    if temporary_invalidation == 'session_expiry':
        clock[0] = NOW+timedelta(days=100)
    else:
        with db.connect() as conn:
            conn.execute('UPDATE users SET is_active=0 WHERE id=1')
    repository.maintain()
    clock[0] = NOW
    with db.connect() as conn:
        conn.execute('UPDATE users SET is_active=1 WHERE id=1')
    restarted = repo(db, clock=lambda: clock[0])
    with pytest.raises(ObservationError, match='OBSERVATION_EXPIRED'):
        create(restarted, request_id=nonce)
    with pytest.raises(ObservationError, match='OBSERVATION_INCOMPLETE'):
        restarted.lookup(observation['observation_id'], CRED, guard=lambda: CRED)
    with sqlite3.connect(db.path) as conn:
        assert conn.execute('SELECT count(*) FROM sync_observation_replays').fetchone()[0] == 1
    valid(db)

"""A01: real Unix SQLite descriptors and direct fresh-connection state checks.

All replacements are owned disposable fixtures. Never manipulate WAL/SHM files.
The ABA case defeats *both* pre-open and post-open pathname checks deliberately.
"""

from contextlib import closing, contextmanager
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import os
from pathlib import Path
import signal
import sqlite3
from threading import Event
from unittest.mock import patch
from uuid import uuid4

import pytest

from isolated_sync import owned_sqlite, retention_schema
from isolated_sync.canonical import CanonicalError
from isolated_sync.retention import Collector
from isolated_sync.retention_schema import RetentionSandbox
from tests.test_isolated_sync_retention import CRED, create, mutate, oracle, repo, valid

pytest_plugins = ('tests.test_isolated_sync_transfer',)
REAL_CONNECT = sqlite3.connect


@pytest.fixture
def db(template):
    with RetentionSandbox() as value:
        with closing(REAL_CONNECT(template.path)) as source, closing(REAL_CONNECT(value.path)) as target:
            source.backup(target)
        value.install()
        yield value


def snapshot(path):
    """No admission/GC helper in the persisted-state oracle, including evidence."""
    with closing(REAL_CONNECT(path, timeout=1)) as conn:
        conn.execute('BEGIN IMMEDIATE')  # Also proves cleanup of transaction locks.
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        state = {t: sorted(conn.execute('SELECT * FROM "'+t+'"').fetchall(), key=repr) for t in tables}
        assert conn.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        conn.rollback()
        return state


@pytest.mark.parametrize('existing', ['file', 'symlink'])
def test_initial_creation_never_adopts_a_preexisting_path(db, existing):
    before = snapshot(db.path)
    real_open = os.open
    planted = []
    def open_(path, flags, *args, **kwargs):
        if flags & os.O_EXCL and Path(path).name == 'synthetic.sqlite3':
            planted.append(Path(path))
            if existing == 'symlink':
                Path(path).symlink_to(db.path)
            else:
                with closing(REAL_CONNECT(db.path)) as source, closing(REAL_CONNECT(path)) as target:
                    source.backup(target)
        return real_open(path, flags, *args, **kwargs)
    with patch.object(retention_schema.os, 'open', open_):
        with pytest.raises(FileExistsError):
            RetentionSandbox()
    assert len(planted) == 1
    assert snapshot(db.path) == before


def test_exclusively_created_inode_is_bound_before_initial_sqlite_open(db):
    before = snapshot(db.path)
    attempted = []
    def connect(path, *args, **kwargs):
        if Path(path).name != 'synthetic.sqlite3' or Path(path) == db.path:
            return REAL_CONNECT(path, *args, **kwargs)
        attempted.append(Path(path))
        original = Path(path)
        saved = original.with_name('a01-initial-owned.sqlite3')
        original.rename(saved)
        original.symlink_to(db.path)
        try:
            return REAL_CONNECT(path, *args, **kwargs)
        finally:
            original.unlink()
            saved.rename(original)
    with patch.object(retention_schema.sqlite3, 'connect', connect):
        with pytest.raises(CanonicalError, match='OWNERSHIP'):
            RetentionSandbox()
    assert len(attempted) == 1
    assert snapshot(db.path) == before


@contextmanager
def cloned(db):
    """A copied profile/marker is not authority for the original sandbox."""
    with RetentionSandbox() as other:
        with closing(REAL_CONNECT(db.path)) as source, closing(REAL_CONNECT(other.path)) as target:
            source.backup(target)
        other.install()
        assert other._owned_file != db._owned_file
        yield other


@contextmanager
def replacement(db, other, mode):
    original = db.path
    saved = original.with_name('a01-owned-held.sqlite3')
    original.rename(saved)
    if mode == 'symlink':
        original.symlink_to(other.path)
    else:
        other.path.replace(original)  # Atomic same-path, different-inode replacement.
    try:
        yield
    finally:
        if mode == 'symlink':
            original.unlink()
        else:
            original.replace(other.path)
        saved.rename(original)


@contextmanager
def race(db, other, *, at='before_open', mode='symlink'):
    armed, opened, manager = [True], [], []

    def connect(path, *args, **kwargs):
        if Path(path) != db.path or not armed[0]:
            return REAL_CONNECT(path, *args, **kwargs)
        armed[0] = False
        if at == 'after_open':
            conn = REAL_CONNECT(path, *args, **kwargs)
            opened.append(conn)
        swap = replacement(db, other, mode)
        swap.__enter__()
        manager.append(swap)
        if at == 'after_open':
            return conn
        try:
            return REAL_CONNECT(path, *args, **kwargs)
        finally:
            if at == 'aba':
                # Restore the authorized pathname *before* Python connect returns.
                manager.pop().__exit__(None, None, None)

    try:
        with patch.object(retention_schema.sqlite3, 'connect', connect):
            yield armed
    finally:
        for conn in opened:
            conn.close()
        for swap in reversed(manager):
            swap.__exit__(None, None, None)


@pytest.mark.parametrize('at', ['before_open', 'after_open', 'aba'])
@pytest.mark.parametrize('mode', ['symlink', 'atomic'])
def test_sqlite_open_substitution_commits_no_unauthorized_deletion(db, at, mode):
    mutate(db)
    gc = Collector(repo(db))
    mark = gc.mark()
    original = snapshot(db.path)
    with cloned(db) as other:
        before = snapshot(other.path)
        with race(db, other, at=at, mode=mode) as armed:
            with pytest.raises(CanonicalError, match='OWNERSHIP'):
                gc.sweep(mark, batch=1)
        assert not armed[0]
        assert snapshot(other.path) == before
    assert snapshot(db.path) == original
    valid(db)


@pytest.mark.parametrize('operation', ['maintain', 'release', 'protect', 'unprotect', 'collect'])
def test_all_destructive_maintenance_connections_are_bound(db, operation):
    repository = repo(db)
    observation = create(repository)
    mutate(db)
    gc = Collector(repository)
    root = observation['target']['raw_ref']
    protection = str(uuid4())
    gc.protect(protection, {'raw': root})
    calls = dict(maintain=lambda: repository.maintain(),
                 release=lambda: repository.release(observation['observation_id'], CRED, guard=lambda: CRED),
                 protect=lambda: gc.protect(str(uuid4()), {'raw': root}),
                 unprotect=lambda: gc.unprotect(protection),
                 collect=lambda: gc.collect(apply=True))
    original = snapshot(db.path)
    with cloned(db) as other:
        before = snapshot(other.path)
        with race(db, other, at='aba', mode='atomic'):
            with pytest.raises(CanonicalError, match='OWNERSHIP'):
                calls[operation]()
        assert snapshot(other.path) == before
    assert snapshot(db.path) == original


def test_swap_between_gc_batches_keeps_only_authorized_prior_commit(db):
    mutate(db)
    gc = Collector(repo(db))
    initial = snapshot(db.path)
    result, following = gc.sweep(gc.mark(), batch=1)
    assert result['objects_deleted'] == 1
    committed = snapshot(db.path)
    assert len(initial['sync_objects'])-len(committed['sync_objects']) == 1
    with cloned(db) as other:
        before = snapshot(other.path)
        with race(db, other, mode='atomic'):
            with pytest.raises(CanonicalError, match='OWNERSHIP'):
                gc.sweep(following, batch=1)
        assert snapshot(other.path) == before
    assert snapshot(db.path) == committed
    valid(db)


def test_reused_connection_cannot_be_redirected_and_new_connection_rejects(db):
    mutate(db)
    original = snapshot(db.path)
    with cloned(db) as other:
        before = snapshot(other.path)
        with closing(db.connect()) as conn:
            fd, identity = conn._ownership[1:]
            assert (os.fstat(fd).st_dev, os.fstat(fd).st_ino) == db._owned_file == identity
            conn.execute('BEGIN IMMEDIATE')
            candidate = conn.execute('SELECT hash FROM sync_gc_counts WHERE incoming=0 AND pins=0 LIMIT 1').fetchone()[0]
            with replacement(db, other, 'atomic'):
                assert (os.fstat(fd).st_dev, os.fstat(fd).st_ino) == identity
                with conn._metadata():
                    conn.execute('DELETE FROM sync_object_edges WHERE parent=?', (candidate,))
                    conn.execute('DELETE FROM sync_objects WHERE hash=?', (candidate,))
                with pytest.raises(CanonicalError, match='OWNERSHIP'):
                    conn.commit()
                conn.rollback()
                with pytest.raises(CanonicalError, match='OWNERSHIP'):
                    db.connect()
        assert snapshot(other.path) == before
    assert snapshot(db.path) == original


@pytest.mark.parametrize('commit', ['explicit', 'context'])
def test_ownership_error_before_commit_rolls_back_actual_deletes(db, commit):
    mutate(db)
    before = snapshot(db.path)
    gc = Collector(repo(db))
    identity = db._owned_file
    try:
        if commit == 'explicit':
            def fault(stage, conn):
                if stage == 'before_commit':
                    db._owned_file = (-1, -1)
            with pytest.raises(CanonicalError, match='OWNERSHIP'):
                gc.sweep(gc.mark(), fault=fault)
        else:
            with closing(db.connect()) as conn:
                with pytest.raises(CanonicalError, match='OWNERSHIP'):
                    with conn:
                        conn.execute('BEGIN IMMEDIATE')
                        with conn._metadata():
                            conn.execute("DELETE FROM sync_observation_views")
                        db._owned_file = (-1, -1)
    finally:
        db._owned_file = identity
    assert snapshot(db.path) == before


def test_descriptor_validation_is_not_replaceable_by_copied_marker_or_path_check(db):
    mutate(db)
    gc = Collector(repo(db))
    plan = gc.mark()
    with cloned(db) as other:
        before = snapshot(other.path)
        # Supplementary adversarial test: even suppressing path checks cannot
        # turn copied certificates/profile/fence/bytes into FD authorization.
        with patch.object(db, 'assert_owned', lambda: None), race(db, other, at='aba', mode='atomic'):
            with pytest.raises(CanonicalError, match='OWNERSHIP'):
                gc.sweep(plan, batch=1)
        assert snapshot(other.path) == before


def test_wrong_external_ownership_identity_rejects_actual_opened_fd(db):
    before = snapshot(db.path)
    with patch.object(db, '_owned_file', (-1, -1)), patch.object(db, 'assert_owned', lambda: None):
        with pytest.raises(CanonicalError, match='OWNERSHIP'):
            db.connect()
    assert snapshot(db.path) == before


def test_missing_descriptor_observation_fails_closed_without_connection_leak(db):
    before = snapshot(db.path)
    @contextmanager
    def no_observation(expected):
        yield [expected, None, False]
        raise CanonicalError('REJECT_SYNTHETIC_OWNERSHIP')
    with patch.object(owned_sqlite, 'opened_identity', no_observation):
        with pytest.raises(CanonicalError, match='OWNERSHIP'):
            db.connect()
    assert snapshot(db.path) == before


@pytest.mark.parametrize('unsupported', ['platform', 'sqlite'])
def test_unreviewed_native_platform_fails_closed(db, unsupported):
    before = snapshot(db.path)
    target, attribute, value = ((owned_sqlite.sys, 'platform', 'unsupported') if unsupported == 'platform'
                                else (owned_sqlite.sqlite3, 'sqlite_version_info', (0, 0, 0)))
    with patch.object(owned_sqlite, '_installed', None), patch.object(target, attribute, value):
        with pytest.raises(CanonicalError, match='OWNERSHIP_PLATFORM'):
            db.connect()
    assert snapshot(db.path) == before


def test_quiescent_migration_open_is_independently_bound(template):
    # Migration formerly bypassed connect() with a separate raw SQLite open.
    with RetentionSandbox() as value, RetentionSandbox() as other:
        for target in (value, other):
            with closing(REAL_CONNECT(template.path)) as source, closing(REAL_CONNECT(target.path)) as conn:
                source.backup(conn)
        original, substitute = snapshot(value.path), snapshot(other.path)
        install = retention_schema.observation_schema.ObservationSandbox.install
        manager = []
        def before_migration(sandbox):
            install(sandbox)
            swap = race(value, other, at='aba', mode='atomic')
            swap.__enter__()
            manager.append(swap)
        try:
            with patch.object(retention_schema.observation_schema.ObservationSandbox, 'install', before_migration):
                with pytest.raises(CanonicalError, match='OWNERSHIP'):
                    value.install()
        finally:
            for swap in manager:
                swap.__exit__(None, None, None)
        assert snapshot(other.path) == substitute
        assert snapshot(value.path) == original
        value.install()
        valid(value)


def test_fd_reuse_during_wal_connections_keeps_actual_inode_binding(db):
    with closing(db.connect()) as first:
        first.execute('BEGIN')
        first.execute('SELECT * FROM sync_current').fetchall()
        for _ in range(8):
            with closing(db.connect()) as next_:
                fd, expected = next_._ownership[1:]
                assert (os.fstat(fd).st_dev, os.fstat(fd).st_ino) == expected == db._owned_file
                assert next_.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
        first.rollback()
    valid(db)


def test_crash_during_unowned_open_preserves_both_databases(db):
    mutate(db)
    original = snapshot(db.path)
    with cloned(db) as other:
        substitute = snapshot(other.path)
        def child():
            with race(db, other, at='aba', mode='atomic'):
                try:
                    Collector(repo(db)).collect(apply=True)
                except CanonicalError:
                    # ABA restores the original path before signaling failure.
                    os.kill(os.getpid(), signal.SIGKILL)
        process = multiprocessing.get_context('fork').Process(target=child)
        process.start()
        process.join(20)
        assert not process.is_alive() and process.exitcode == -signal.SIGKILL
        assert snapshot(other.path) == substitute
    assert snapshot(db.path) == original
    valid(db)


def test_wal_parallel_connections_post_open_swap_have_no_unauthorized_commit(db):
    mutate(db)
    original = snapshot(db.path)
    entered, resume = Event(), Event()
    with cloned(db) as other:
        before = snapshot(other.path)
        with closing(db.connect()) as reader:
            reader.execute('BEGIN')
            current = tuple(reader.execute('SELECT * FROM sync_current').fetchone())
            def connect(path, *args, **kwargs):
                conn = REAL_CONNECT(path, *args, **kwargs)
                if Path(path) == db.path:
                    entered.set()
                    assert resume.wait(10)
                return conn
            def writer():
                with pytest.raises(CanonicalError, match='OWNERSHIP'):
                    gc = Collector(repo(db))
                    gc.sweep(gc.mark())
            with ThreadPoolExecutor(max_workers=1) as pool, patch.object(retention_schema.sqlite3, 'connect', connect):
                future = pool.submit(writer)
                assert entered.wait(10)
                with replacement(db, other, 'symlink'):
                    resume.set()
                    future.result(10)
                    assert tuple(reader.execute('SELECT * FROM sync_current').fetchone()) == current
            reader.rollback()
        assert snapshot(other.path) == before
    assert snapshot(db.path) == original


@pytest.mark.parametrize('stage', ['opened', 'before_commit', 'after_commit'])
def test_process_interruption_around_admission_and_gc_commit(db, stage):
    mutate(db)
    before = snapshot(db.path)
    def child():
        if stage == 'opened':
            def connect(path, *args, **kwargs):
                conn = REAL_CONNECT(path, *args, **kwargs)
                if Path(path) == db.path:
                    os.kill(os.getpid(), signal.SIGKILL)
                return conn
            with patch.object(retention_schema.sqlite3, 'connect', connect):
                db.connect()
        else:
            def fault(at, conn):
                if at == stage:
                    os.kill(os.getpid(), signal.SIGKILL)
            gc = Collector(repo(db))
            gc.sweep(gc.mark(), batch=1, fault=fault)
    process = multiprocessing.get_context('fork').Process(target=child)
    process.start()
    process.join(20)
    assert not process.is_alive() and process.exitcode == -signal.SIGKILL
    after = snapshot(db.path)
    if stage == 'after_commit':
        assert len(before['sync_objects'])-len(after['sync_objects']) == 1
    else:
        assert after == before
    valid(db)
    Collector(repo(db)).collect(apply=True)
    valid(db)


def test_legitimate_owned_gc_and_repeat_preserve_reachable_objects_and_evidence(db):
    repository = repo(db)
    observation = create(repository)
    for value in ('a', 'b', 'c'):
        mutate(db, value)
    reached, garbage = oracle(db)
    before = snapshot(db.path)
    assert garbage
    gc = Collector(repository)
    result = gc.collect(apply=True, batch=2, max_batches=128)
    after = snapshot(db.path)
    assert result['objects_deleted'] == len(garbage)
    assert {r[0] for r in after['sync_objects']} == reached
    for table in ('sync_commits', 'sync_capture_commits', 'sync_current', 'sync_observations', 'sync_observation_pins'):
        assert before[table] == after[table]
    assert repository.lookup(observation['observation_id'], CRED, guard=lambda: CRED) == observation
    assert gc.collect(apply=True)['objects_deleted'] == 0
    valid(db)

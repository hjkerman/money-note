from pathlib import Path
import sqlite3

import pytest

from scripts.benchmarks.t66d3a import MaterializedCursor, ROOT, check_output


def test_d3a_output_scope_and_no_overwrite(tmp_path):
    output = tmp_path/'new.json'
    check_output(output)
    output.touch()
    for path in (output, ROOT/'bundle.json', Path('/var/lib/synthetic.json'), tmp_path):
        with pytest.raises(ValueError):
            check_output(path)


def test_d3a_materialized_bytes_are_returned_blobs_not_page_io():
    with sqlite3.connect(':memory:') as conn:
        rows, blobs = [0], [0]
        cursor = MaterializedCursor(conn.execute("SELECT x'000102' UNION ALL SELECT x'ff'"), rows, blobs)
        assert cursor.fetchone() == (b'\x00\x01\x02',)
        assert cursor.fetchall() == [(b'\xff',)]
        assert rows[0] == 2 and blobs[0] == 4
        assert cursor.fetchone() is None and blobs[0] == 4


def test_d3a_isolated_migration_failure_is_atomic():
    from unittest.mock import patch
    from isolated_sync.observation_schema import ObservationSandbox, SQL, VERSION
    from isolated_sync.finalization import FinalizationSandbox, VERSION as D2B_VERSION
    with ObservationSandbox() as db:
        FinalizationSandbox.install(db)
        with db.connect() as conn:
            before = list(conn.iterdump())
        with patch('isolated_sync.observation_schema.SQL', SQL+'CREATE TABLE sync_invalid AS SELECT * FROM absent;'):
            with pytest.raises(sqlite3.OperationalError):
                db.install()
        with db.connect() as conn:
            assert conn.execute('PRAGMA user_version').fetchone()[0] == D2B_VERSION
            assert list(conn.iterdump()) == before
        db.install()
        with db.connect() as conn:
            assert conn.execute('PRAGMA user_version').fetchone()[0] == VERSION


def test_d3a_restored_synthetic_database_requires_new_epoch():
    from isolated_sync.observation import ObservationRepository, ObservationError
    from isolated_sync.observation_schema import ObservationSandbox
    from isolated_sync.raw import MONEY_SETTINGS
    from tests.test_isolated_sync_observation import auth_seed, CREDENTIAL, EVAL, NOW
    with ObservationSandbox() as source, ObservationSandbox() as restored:
        with source.connect() as conn:
            for key in MONEY_SETTINGS:
                conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
            auth_seed(conn)
        source.install()
        source.bootstrap()
        def repository(db):
            return ObservationRepository(db, evaluation=lambda: EVAL, clock=lambda: NOW)
        old = repository(source).create(CREDENTIAL, request_id='aaaaaaaa-0000-4000-8000-000000000001', guard=lambda: CREDENTIAL)
        target = sqlite3.connect(restored.path)
        try:
            with source.connect() as conn:
                conn.backup(target)
        finally:
            target.close()
        restored.bootstrap()  # Mandatory cold startup after restore, not reopen.
        with pytest.raises(ObservationError, match='EPOCH_CHANGED'):
            repository(restored).lookup(old['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL)
        new = repository(restored).create(CREDENTIAL, request_id='aaaaaaaa-0000-4000-8000-000000000002', guard=lambda: CREDENTIAL)
        before, after = old['target']['ns'], new['target']['ns']
        assert before['server_id'] == after['server_id'] and before['dataset_id'] == after['dataset_id']
        assert before['epoch'] != after['epoch']


@pytest.mark.parametrize('sizes', [['10000'], ['376', '376'], ['376', '1000', '376']])
def test_expiry_cost_benchmark_rejects_unbounded_sizes(tmp_path, sizes):
    import subprocess
    import sys
    output = tmp_path/'costs.json'
    result = subprocess.run([sys.executable, str(ROOT/'scripts/benchmarks/t66d3a_expiry.py'),
                             '--output', str(output), '--sizes', *sizes], capture_output=True)
    assert result.returncode == 2 and not output.exists()


def test_expiry_cost_benchmark_rejects_overwrite_before_running(tmp_path):
    import subprocess
    import sys
    output = tmp_path/'costs.json'
    output.write_text('synthetic-preserve')
    result = subprocess.run([sys.executable, str(ROOT/'scripts/benchmarks/t66d3a_expiry.py'),
                             '--output', str(output)], capture_output=True)
    assert result.returncode != 0 and output.read_text() == 'synthetic-preserve'

"""Independent typed-shape witnesses and deterministic HTTP failure boundaries."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import sqlite3
import subprocess
import sys
from threading import Event
from unittest.mock import patch
from uuid import uuid4

import pytest

from isolated_sync.canonical import Object
from isolated_sync.observation import ObservationError
from isolated_sync.observation_schema import ObservationConnection
from isolated_sync.transfer import PathResolver
from tests.test_isolated_sync_observation import repository
from tests.test_isolated_sync_transfer import URL, client, download, error, graph, headers, observe, request

pytest_plugins = ('tests.test_isolated_sync_transfer',)


@pytest.mark.parametrize('defect', ['table_coverage', 'table_order', 'extra_field', 'descriptor_count', 'descriptor_height',
                                  'leaf_count', 'leaf_oversized', 'leaf_key', 'leaf_pk_order', 'leaf_domain',
                                  'node_height', 'node_count', 'node_range', 'node_fanout',
                                  'index_count', 'index_prefix', 'index_version', 'index_bucket', 'index_digest', 'index_empty'])
def test_hash_valid_but_invalid_typed_shapes(db, defect):
    c = client(db)
    m = observe(c).json()
    objects = graph(db, m)
    kind = ('raw-root' if defect in ('table_coverage', 'table_order', 'extra_field', 'descriptor_count', 'descriptor_height') else
            'snapshot-leaf' if defect.startswith('leaf_') else 'snapshot-node' if defect.startswith('node_') else
            'index-leaf' if defect in ('index_bucket', 'index_digest') else 'index-node')
    ref, path, raw, body = next(v for v in objects.values() if v[3]['kind'] == kind and (kind != 'snapshot-leaf' or len(v[3]['rows']) > 1))
    resolver = None
    with db.connect() as conn:
        resolver = PathResolver(conn, repository(db), m['target'])
        # Obtain the trusted edge via an independent walk of real parent bytes.
        from isolated_sync.transfer import Edge
        current = Edge(m['target']['raw_ref'], frozenset({'raw-root'}), root=True) if path[0] == m['target']['raw_ref']['hash'] else Edge(m['target']['index_ref'], frozenset({'index-root'}), root=True)
        for parent_hash, child_hash in zip(path, path[1:]):
            parent_raw = conn.execute('SELECT body FROM sync_objects WHERE hash=?', (parent_hash,)).fetchone()[0]
            parent_body = json.loads(parent_raw)
            if parent_body['kind'] == 'raw-root':
                t = next(v for v in parent_body['tables'] if v['root']['ref']['hash'] == child_hash)
                current = Edge(t['root']['ref'], frozenset({'snapshot-node', 'snapshot-leaf'}), t['name'], t['root'], True)
            elif parent_body['kind'] == 'snapshot-node':
                d = next(v for v in parent_body['children'] if v['ref']['hash'] == child_hash)
                current = Edge(d['ref'], frozenset({'snapshot-node', 'snapshot-leaf'}), parent_body['table'], d)
            elif parent_body['kind'] == 'index-root':
                current = Edge(parent_body['facts'], frozenset({'index-node', 'index-leaf'}), count=int(parent_body['count']))
            else:
                side = 'left' if parent_body['left']['hash'] == child_hash else 'right'
                current = Edge(parent_body[side], frozenset({'index-node', 'index-leaf'}), prefix=parent_body['prefix']+('0' if side == 'left' else '1'), parent_count=int(parent_body['count']))
        if defect == 'table_coverage':
            body['tables'].pop()
        elif defect == 'table_order':
            body['tables'].reverse()
        elif defect == 'extra_field':
            body['secret'] = 'synthetic'
        elif defect == 'descriptor_count':
            body['tables'][0]['root']['count'] = '0'
        elif defect == 'descriptor_height':
            body['tables'][0]['root']['height'] = True
        elif defect == 'leaf_count':
            body['count'] = '1'
        elif defect == 'leaf_oversized':
            body['oversized'] = not body['oversized']
        elif defect == 'leaf_key':
            body['rows'][0]['key'] = ['i', '999999']
        elif defect == 'leaf_pk_order':
            body['rows'].reverse()
        elif defect == 'leaf_domain':
            body['table'] = 'app_settings'
        elif defect == 'node_height':
            body['height'] += 1
        elif defect == 'node_count':
            body['children'][0]['count'] = '0'
        elif defect == 'node_range':
            body['children'][1]['min'] = body['children'][0]['max']
        elif defect == 'node_fanout':
            body['children'] *= 33
        elif defect == 'index_count':
            body['count'] = '0'
        elif defect == 'index_prefix':
            body['prefix'] = '2'
        elif defect == 'index_version':
            body['structural'] = True
        elif defect == 'index_bucket':
            body['facts'] *= 2
        elif defect == 'index_digest':
            body['digest'] = '0'*64
        else:
            body = dict(kind='index-empty', **resolver.context.fields(), structural=1, count='1')
        # Rehash deliberately: these are shape witnesses, not ordinary hash
        # mismatches. No production object/schema is changed to inject them.
        bad = Object.make(body)
        with pytest.raises((ObservationError, ValueError, KeyError, TypeError)):
            resolver.validate(bad, current)


@pytest.mark.parametrize('rotation', ['auth', 'epoch'])
def test_change_while_waiting_for_writer_lock(db, rotation):
    c = client(db)
    m = observe(c).json()
    attempted = Event()
    execute = ObservationConnection.execute
    def barrier(conn, sql, parameters=()):
        if sql == 'BEGIN IMMEDIATE':
            attempted.set()
        return execute(conn, sql, parameters)
    with sqlite3.connect(db.path) as writer:
        writer.execute('BEGIN IMMEDIATE')
        with patch.object(ObservationConnection, 'execute', barrier), ThreadPoolExecutor(1) as pool:
            future = pool.submit(download, c, m, [m['target']['raw_ref']['hash']])
            assert attempted.wait(5)
            if rotation == 'auth':
                writer.execute('DELETE FROM auth_sessions WHERE user_id=1')
            else:
                namespace = json.loads(writer.execute('SELECT namespace FROM sync_current').fetchone()[0])
                namespace['epoch'] = str(uuid4())
                from isolated_sync.canonical import encode
                writer.execute('UPDATE sync_current SET namespace=?', (encode(namespace),))
            writer.commit()
            response = future.result(10)
    error(response, 401 if rotation == 'auth' else 409, 'AUTH_REQUIRED' if rotation == 'auth' else 'EPOCH_CHANGED')
    assert 'chunks' not in response.json()


def test_response_sending_holds_no_sqlite_transaction(db):
    m = observe(client(db)).json()
    commit = []
    def fault(stage, ticket):
        if stage == 'serialized':
            # A different writer can commit before the HTTP terminal recheck.
            with db.connect() as conn:
                conn.begin_capture()
                conn.execute("UPDATE app_labels SET value='next-generation'")
                conn.finalize()
                conn.commit()
                commit.append(True)
    response = download(client(db, fault=fault), m, [m['target']['raw_ref']['hash']])
    assert response.status_code == 200 and commit == [True]


@pytest.mark.parametrize('stage', ['objects_prepared', 'serialized', 'terminal'])
def test_sigkill_during_object_request_restart_retry(db, tmp_path, stage):
    c = client(db)
    m = observe(c).json()
    ref = m['target']['raw_ref']
    body = request([ref['hash']])
    # Child owns a newly initialized sandbox, then takes a SQLite backup of this
    # synthetic fixture. It never accepts a configured/runtime database path.
    destination = tmp_path/'child.sqlite3'
    source = Path(__file__).resolve().parents[1]
    code = '''
import os, signal, sqlite3
from pathlib import Path
from isolated_sync.observation_schema import ObservationSandbox
from tests.test_isolated_sync_transfer import client, headers
db = ObservationSandbox()
with sqlite3.connect(SOURCE) as src, sqlite3.connect(db.path) as dst:
    src.backup(dst)
def fault(current, ticket):
    if current == STAGE:
        Path(DEST).write_text(str(db.path))
        os.kill(os.getpid(), signal.SIGKILL)
client(db, fault=fault).post(URL, json=BODY, headers=headers())
'''
    variables = dict(SOURCE=str(db.path), DEST=str(destination), STAGE=stage, URL=URL+'/'+m['observation_id']+'/objects', BODY=body)
    script = '\n'.join(key+'='+repr(value) for key, value in variables.items())+'\n'+code
    result = subprocess.run([sys.executable, '-c', script], cwd=source, env=dict(os.environ, PYTHONPATH=str(source)),
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=15)
    assert result.returncode == -signal.SIGKILL, result.stderr[-300:]
    crashed_path = Path(destination.read_text())
    assert crashed_path.is_relative_to('/tmp') and crashed_path.parent.name.startswith('money-note-d1-')
    with sqlite3.connect(crashed_path) as conn, sqlite3.connect(db.path) as original:
        assert conn.execute('SELECT * FROM sync_current').fetchall() == original.execute('SELECT * FROM sync_current').fetchall()
        assert conn.execute('SELECT * FROM sync_observation_pins').fetchall() == original.execute('SELECT * FROM sync_observation_pins').fetchall()
        assert conn.execute('SELECT status FROM sync_observations').fetchone()[0] == 'available'
    shutil.rmtree(crashed_path.parent)
    # Source is unaffected; same immutable read-only request remains retryable.
    response = c.post(URL+'/'+m['observation_id']+'/objects', json=body, headers=headers())
    assert response.status_code == 200
    assert hashlib.sha256(response.content).digest() == hashlib.sha256(c.post(URL+'/'+m['observation_id']+'/objects', json=body, headers=headers()).content).digest()

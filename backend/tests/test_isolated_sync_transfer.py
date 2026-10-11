"""Real isolated ASGI/auth/SQLite integration, independent graph/row oracle.

No normal app startup, configured database, network listener or real credential.
Hash and graph traversal expectations below do not call PathResolver.
"""

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
from threading import Barrier, Event
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app import auth
from isolated_sync.artifacts import release_bundle
from isolated_sync.canonical import encode
from isolated_sync.http import create_app
from isolated_sync.observation import ObservationRepository
from isolated_sync.observation_schema import ObservationSandbox
from isolated_sync.raw import MONEY_SETTINGS, SENSITIVE, TABLES
from isolated_sync.transfer import TransferLimits
from tests.test_isolated_sync_capture import ROWS, insert
from tests.test_isolated_sync_observation import NOW, EVAL

TOKEN_A, TOKEN_B, TOKEN_NEW = 'synthetic-d3b-A', 'synthetic-d3b-B', 'synthetic-d3b-new'
URL = '/api/sync/v1/observations'


@pytest.fixture(scope='module')
def template():
    with ObservationSandbox() as db:
        with db.connect() as conn:
            for table, row in ROWS.items():
                value = dict(row)
                if table == 'cash_flows':
                    value['amount_value'] = -50
                insert(conn, table, value)
            for n in range(260):
                insert(conn, 'ledger_entries', dict(id=1000+n, book_section='archive', entry_kind='expense',
                       entry_date='2026-07-03', title='한글 😀 e\u0301 '+str(n), amount_value=1000, sort_order=n,
                       payment_key='d3b-history-'+str(n)))
            for key in MONEY_SETTINGS:
                conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
            for key in SENSITIVE:
                conn.execute("INSERT INTO app_settings(key,value) VALUES (?, 'synthetic-do-not-transfer')", (key,))
            for n, token in ((1, TOKEN_A), (2, TOKEN_B), (1, TOKEN_NEW)):
                conn.execute("INSERT OR IGNORE INTO users(id,username,password_hash) VALUES (?,?, 'synthetic')", (n, 'd3b-'+str(n)))
                conn.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (?,?, '2026-12-31T00:00:00Z')",
                             (n, auth._hash_session_token(token)))
        db.install()
        db.bootstrap()
        yield db


@pytest.fixture
def db(template):
    with ObservationSandbox() as value:
        with sqlite3.connect(template.path) as source, sqlite3.connect(value.path) as target:
            source.backup(target)
        yield value


def client(db, *, clock=lambda: NOW, fault=None, limits=TransferLimits(), **kwargs):
    repo = ObservationRepository(db, clock=clock, evaluation=lambda: EVAL)
    return TestClient(create_app(repo, fault=fault, limits=limits, **kwargs))


def headers(token=TOKEN_A):
    return {'Authorization': 'Bearer '+token}


def observe(c, *, token=TOKEN_A, body=None):
    return c.post(URL, json=body or dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0), headers=headers(token))


def request(path, *, length=1, offset='0', request_id=None):
    return dict(protocol=1, request_id=request_id or str(uuid4()), items=[dict(path=path, offset=offset, length=length)])


def download(c, manifest, path, **kwargs):
    return c.post(URL+'/'+manifest['observation_id']+'/objects', json=request(path, **kwargs), headers=headers())


def graph_child(body):
    # Independent graph schema, not Store.edges/PathResolver output.
    kind = body['kind']
    if kind == 'raw-root':
        return [v['root']['ref'] for v in body['tables']]
    if kind == 'snapshot-node':
        return [v['ref'] for v in body['children']]
    if kind == 'index-root':
        return [body['facts']]
    if kind == 'index-node':
        return [body['left'], body['right']]
    return []


def graph(db, manifest):
    result = {}
    with sqlite3.connect(db.path) as conn:
        def visit(ref, path):
            raw = conn.execute('SELECT body FROM sync_objects WHERE hash=?', (ref['hash'],)).fetchone()[0]
            body = json.loads(raw)
            assert hashlib.sha256(b'money-note.sync.v1/'+body['kind'].encode()+b'\0'+raw).hexdigest() == ref['hash']
            result[ref['hash']] = (ref, path, raw, body)
            for child in graph_child(body):
                visit(child, path+[child['hash']])
        for role in ('raw', 'index', 'hot', 'control'):
            ref = manifest['target'][role+'_ref']
            visit(ref, [ref['hash']])
    return result


def error(response, status, code):
    assert response.status_code == status, response.text[:150]
    assert response.json()['error']['code'] == code
    assert set(response.json()) == {'protocol', 'request_id', 'error'}
    assert set(response.json()['error']) == {'code', 'action', 'retry_after_ms', 'current_ns'}
    assert response.headers['cache-control'] == 'no-store'


def test_manifest_real_auth_retry_conflict_and_read_only(db):
    with sqlite3.connect(db.path) as conn:
        before = {t: conn.execute('SELECT * FROM '+t).fetchall() for t in TABLES}
        revision = conn.execute('SELECT * FROM authoritative_state_revision').fetchall()
        sessions = conn.execute('SELECT * FROM auth_sessions').fetchall()
    c = client(db)
    body = dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=1048576)
    first, retry = observe(c, body=body), observe(c, body=body)
    assert (first.status_code, retry.status_code) == (201, 200)
    assert first.content == retry.content
    assert len(first.json()['target']) == 10
    assert first.headers['content-type'] == 'application/json'
    assert b'synthetic-do-not-transfer' not in first.content
    error(observe(c, body=dict(body, inline_bytes=0)), 409, 'REQUEST_CONFLICT')
    with sqlite3.connect(db.path) as conn:
        assert before == {t: conn.execute('SELECT * FROM '+t).fetchall() for t in TABLES}
        assert revision == conn.execute('SELECT * FROM authoritative_state_revision').fetchall()
        assert sessions == conn.execute('SELECT * FROM auth_sessions').fetchall()
        assert conn.execute('SELECT count(*) FROM sync_observation_pins').fetchone()[0] == 5


@pytest.mark.parametrize('role', ['raw', 'index', 'hot', 'control'])
def test_exact_root_response_retry_and_hash(db, role):
    c = client(db)
    m = observe(c).json()
    ref = m['target'][role+'_ref']
    body = request([ref['hash']], length=int(ref['bytes']))
    url = URL+'/'+m['observation_id']+'/objects'
    first, second = c.post(url, json=body, headers=headers()), c.post(url, json=body, headers=headers())
    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    chunk = first.json()['chunks'][0]
    raw = base64.b64decode(chunk['data_base64'], validate=True)
    with sqlite3.connect(db.path) as conn:
        assert raw == conn.execute('SELECT body FROM sync_objects WHERE hash=?', (ref['hash'],)).fetchone()[0]
    parsed = json.loads(raw)
    assert hashlib.sha256(b'money-note.sync.v1/'+parsed['kind'].encode()+b'\0'+raw).hexdigest() == ref['hash']


@pytest.mark.parametrize('kind', ['snapshot-node', 'snapshot-leaf', 'index-root', 'index-node', 'index-leaf'])
def test_descendant_and_grandchild_paths(db, kind):
    c = client(db)
    m = observe(c).json()
    ref, path, raw, _ = next(v for v in graph(db, m).values() if v[3]['kind'] == kind)
    result = download(c, m, path, length=min(len(raw), 1048576))
    assert result.status_code == 200
    chunk = result.json()['chunks'][0]
    assert chunk['ref'] == ref
    assert base64.b64decode(chunk['data_base64'], validate=True) == raw[:1048576]


@pytest.mark.parametrize('defect', ['arbitrary', 'internal_input', 'row_hash', 'wrong_edge', 'sibling_jump', 'root_jump', 'loop',
                                  'bad_hash', 'uppercase_hash', 'empty_path', 'wrong_type', 'absent_offset', 'negative_offset',
                                  'nonminimal_offset', 'float_length', 'bool_length', 'zero_length', 'past_end', 'extra_field'])
def test_independent_path_and_body_failures(db, defect):
    c = client(db)
    m = observe(c).json()
    g = graph(db, m)
    ref = m['target']['raw_ref']
    body = request([ref['hash']])
    item = body['items'][0]
    if defect == 'arbitrary':
        item['path'] = ['a'*64]
    elif defect == 'internal_input':
        with sqlite3.connect(db.path) as conn:
            item['path'] = [conn.execute('SELECT input_hash FROM sync_observations').fetchone()[0]]
    elif defect == 'row_hash':
        with sqlite3.connect(db.path) as conn:
            item['path'] = [conn.execute('SELECT hash FROM sync_rows LIMIT 1').fetchone()[0]]
    elif defect in ('wrong_edge', 'sibling_jump'):
        leaves = [v for v in g.values() if v[3]['kind'] == 'snapshot-leaf']
        item['path'] = leaves[0][1]+[leaves[1][0]['hash']]
    elif defect == 'root_jump':
        item['path'].append(m['target']['hot_ref']['hash'])
    elif defect == 'loop':
        item['path'].append(ref['hash'])
    elif defect in ('bad_hash', 'uppercase_hash'):
        item['path'] = ['invalid' if defect == 'bad_hash' else ref['hash'].upper()]
    elif defect == 'empty_path':
        item['path'] = []
    elif defect == 'wrong_type':
        item['path'] = ref
    elif defect == 'absent_offset':
        del item['offset']
    elif defect in ('negative_offset', 'nonminimal_offset'):
        item['offset'] = '-1' if defect == 'negative_offset' else '01'
    elif defect in ('float_length', 'bool_length', 'zero_length'):
        item['length'] = {'float_length': 1.0, 'bool_length': True, 'zero_length': 0}[defect]
    elif defect == 'past_end':
        item['offset'] = ref['bytes']
    else:
        item['parent_type'] = 'raw-root'
    result = c.post(URL+'/'+m['observation_id']+'/objects', json=body, headers=headers())
    error(result, 422, 'INVALID_REQUEST')
    assert 'chunks' not in result.json()


@pytest.mark.parametrize('defect', ['missing_auth', 'unknown_token', 'wrong_principal', 'new_token', 'revoked', 'inactive', 'expired_session', 'shared_cookie'])
def test_original_credential_auth_lifecycle(db, defect):
    c = client(db)
    m = observe(c).json()
    h = headers()
    expected = (401, 'AUTH_REQUIRED')
    if defect == 'missing_auth':
        h = {}
    elif defect == 'unknown_token':
        h = headers('does-not-exist')
    elif defect in ('wrong_principal', 'new_token'):
        h = headers(TOKEN_B if defect == 'wrong_principal' else TOKEN_NEW)
        expected = (403, 'PRINCIPAL_OR_SESSION_CHANGED')
    elif defect in ('revoked', 'inactive', 'expired_session'):
        with sqlite3.connect(db.path) as conn:
            if defect == 'revoked':
                conn.execute('DELETE FROM auth_sessions WHERE user_id=1')
            elif defect == 'inactive':
                conn.execute('UPDATE users SET is_active=0 WHERE id=1')
            else:
                conn.execute("UPDATE auth_sessions SET expires_at='2026-01-01T00:00:00Z' WHERE user_id=1")
    else:
        h = {'Cookie': 'money_note_share_session=synthetic-shared'}
    error(c.post(URL+'/'+m['observation_id']+'/objects', json=request([m['target']['raw_ref']['hash']]), headers=h), *expected)


def test_cookie_precedence_and_origin(db):
    c = client(db)
    name = auth.get_settings().session_cookie_name
    good = {'Cookie': name+'='+TOKEN_A, 'Authorization': 'Bearer invalid'}
    assert c.post(URL, json=dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0), headers=good).status_code == 201
    bad = dict(good, Origin='https://untrusted.example')
    error(c.post(URL, json=dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0), headers=bad), 403, 'PRINCIPAL_OR_SESSION_CHANGED')


@pytest.mark.parametrize('when', ['objects_prepared', 'serialized', 'terminal'])
@pytest.mark.parametrize('change', ['revoke', 'cancel', 'expire'])
def test_terminal_auth_expiry_cancellation_after_buffering(db, when, change):
    clock = [NOW]
    m = observe(client(db)).json()
    def fault(stage, ticket):
        if stage != when:
            return
        if change == 'expire':
            clock[0] = NOW+timedelta(seconds=900)
        elif change == 'cancel':
            ticket.cancelled.set()
        else:
            # At objects_prepared the short read/metadata transaction holds the
            # writer lock. Revoke at the two post-transaction HTTP boundaries.
            if stage == 'objects_prepared':
                ticket.cancelled.set()  # request-generation replacement guard
            else:
                with sqlite3.connect(db.path) as conn:
                    conn.execute('DELETE FROM auth_sessions WHERE user_id=1')
    result = download(client(db, clock=lambda: clock[0], fault=fault), m, [m['target']['raw_ref']['hash']])
    if change == 'expire':
        error(result, 410, 'OBSERVATION_EXPIRED')
        with sqlite3.connect(db.path) as conn:
            assert conn.execute('SELECT status FROM sync_observations').fetchone()[0] == 'retired'
    else:
        assert result.status_code in (401, 403)
    assert 'chunks' not in result.json()


@pytest.mark.parametrize('delta,success', [(899.999999, True), (900, False), (900.000001, False)])
def test_exact_expiry_and_rollback_persistence(db, delta, success):
    clock = [NOW]
    c = client(db, clock=lambda: clock[0])
    m = observe(c).json()
    clock[0] += timedelta(seconds=delta)
    first = download(c, m, [m['target']['raw_ref']['hash']])
    if success:
        assert first.status_code == 200
    else:
        error(first, 410, 'OBSERVATION_EXPIRED')
        clock[0] = NOW
        error(download(client(db), m, [m['target']['raw_ref']['hash']]), 410, 'OBSERVATION_EXPIRED')
        with sqlite3.connect(db.path) as conn:
            assert conn.execute('SELECT status FROM sync_observations').fetchone()[0] == 'retired'
            assert conn.execute('SELECT count(*) FROM sync_observation_pins WHERE active=1').fetchone()[0] == 5


def test_old_four_replacements_clock_rollback_no_pin_release(db):
    clock = [NOW]
    c = client(db, clock=lambda: clock[0])
    old = [observe(c).json() for _ in range(4)]
    clock[0] += timedelta(seconds=901)
    new = [observe(c).json() for _ in range(4)]
    clock[0] = NOW
    for m in old:
        error(download(c, m, [m['target']['hot_ref']['hash']]), 410, 'OBSERVATION_EXPIRED')
    for m in new:
        assert download(c, m, [m['target']['hot_ref']['hash']]).status_code == 200
    with sqlite3.connect(db.path) as conn:
        assert dict(conn.execute('SELECT status,count(*) FROM sync_observations GROUP BY status')) == {'available': 4, 'retired': 4}
        assert conn.execute('SELECT count(*) FROM sync_observation_pins WHERE active=1').fetchone()[0] == 40


@pytest.mark.parametrize('defect', ['missing', 'corrupt', 'domain', 'length', 'wrong_table', 'bad_child_type'])
def test_authorized_object_corruption_fails_closed(db, defect):
    c = client(db)
    m = observe(c).json()
    ref, path, raw, body = next(v for v in graph(db, m).values() if v[3]['kind'] == 'snapshot-leaf')
    with sqlite3.connect(db.path) as conn:
        if defect == 'missing':
            conn.execute('DELETE FROM sync_objects WHERE hash=?', (ref['hash'],))
        elif defect == 'domain':
            conn.execute("UPDATE sync_objects SET kind='index-leaf' WHERE hash=?", (ref['hash'],))
        else:
            if defect == 'length':
                new = raw+b' '
            elif defect == 'wrong_table':
                new = raw.replace(b'ledger_entries', b'monthly_panels')
            elif defect == 'bad_child_type':
                body['kind'] = 'index-root'
                new = encode(body)
            else:
                new = raw[:-1]+b']'
            conn.execute('UPDATE sync_objects SET body=? WHERE hash=?', (new, ref['hash']))
    result = download(c, m, path)
    error(result, 410 if defect == 'missing' else 500, 'OBSERVATION_INCOMPLETE' if defect == 'missing' else 'STORAGE_FAILED')


@pytest.mark.parametrize('defect', ['items', 'depth', 'chunk', 'total', 'body', 'content_length', 'encoded_body'])
def test_request_resource_limits(db, defect):
    c = client(db)
    m = observe(c).json()
    body = request([m['target']['raw_ref']['hash']])
    kwargs = {'json': body, 'headers': headers()}
    expected = (413, 'TRANSFER_BUDGET')
    if defect == 'items':
        body['items'] *= 65
    elif defect == 'depth':
        body['items'][0]['path'] = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(513)]
    elif defect == 'chunk':
        body['items'][0]['length'] = 1048577
    elif defect == 'total':
        body['items'] = [dict(body['items'][0], length=600000) for _ in range(2)]
    elif defect in ('body', 'content_length'):
        kwargs = dict(content=b' '*(3*1048576+1) if defect == 'body' else b'{}',
                      headers=dict(headers(), **{'Content-Type': 'application/json', 'Content-Length': str(3*1048576+1)}))
    else:
        kwargs['headers'] = dict(headers(), **{'Content-Encoding': 'gzip'})
        expected = (422, 'INVALID_REQUEST')
    error(c.post(URL+'/'+m['observation_id']+'/objects', **kwargs), *expected)


@pytest.mark.parametrize('body', [b'{"protocol":1,"protocol":1}', b'{} ', b'[]', b'{"request_id":"\\ud800"}', b'{"x":NaN}', b'{"x":1e999}'])
def test_strict_wire_json_and_shapes(db, body):
    result = client(db).post(URL, content=body, headers=dict(headers(), **{'Content-Type': 'application/json'}))
    error(result, 422, 'INVALID_REQUEST')


def test_cross_principal_and_cross_generation_objects(db):
    c = client(db)
    a = observe(c).json()
    old_graph = graph(db, a)
    old_leaf = next(v for v in old_graph.values() if v[3]['kind'] == 'snapshot-leaf')
    root_before = download(c, a, [a['target']['raw_ref']['hash']], length=int(a['target']['raw_ref']['bytes']))
    leaf_before = download(c, a, old_leaf[1], length=len(old_leaf[2]))
    assert root_before.status_code == leaf_before.status_code == 200
    assert base64.b64decode(leaf_before.json()['chunks'][0]['data_base64'], validate=True) == old_leaf[2]
    with db.connect() as conn:
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='B new generation' WHERE id=1000")
        conn.finalize()
        conn.commit()
    b = observe(c, token=TOKEN_B).json()
    new_graph = graph(db, b)
    changed = next(v for h, v in new_graph.items() if h not in old_graph and v[3]['kind'] == 'snapshot-leaf')
    # Known full B manifest/path cannot authorize A to use B's observation.
    result = c.post(URL+'/'+b['observation_id']+'/objects', json=request(changed[1]), headers=headers())
    error(result, 403, 'PRINCIPAL_OR_SESSION_CHANGED')
    assert c.post(URL+'/'+b['observation_id']+'/objects', json=request(changed[1]), headers=headers(TOKEN_B)).status_code == 200
    # Nor can a new B leaf be appended to the old A authorized graph.
    error(download(c, a, changed[1]), 422, 'INVALID_REQUEST')
    error(download(c, a, [a['target']['raw_ref']['hash']]+changed[1][1:]), 422, 'INVALID_REQUEST')
    leaf_after = download(c, a, old_leaf[1], length=len(old_leaf[2]))
    assert leaf_after.status_code == 200
    assert leaf_after.json()['chunks'][0]['ref'] == old_leaf[0]
    assert base64.b64decode(leaf_after.json()['chunks'][0]['data_base64'], validate=True) == old_leaf[2]
    assert observe(c, body=dict(protocol=1, request_id=str(uuid4()), base=a['target'], inline_bytes=0)).json()['change_kind'] == 'raw'


def test_large_oversized_singleton_chunked_exact_bytes(db):
    # Schema-valid long text; no arbitrary new row length restriction.
    with db.connect() as conn:
        conn.begin_capture()
        conn.execute('UPDATE app_labels SET value=?', ('한글😀'*120000,))
        conn.finalize()
        conn.commit()
    c = client(db)
    m = observe(c).json()
    ref, path, raw, body = next(v for v in graph(db, m).values() if v[3].get('oversized'))
    assert body['count'] == '1' and len(raw) > 1048576
    chunks = []
    for offset in range(0, len(raw), 1048576):
        response = download(c, m, path, offset=str(offset), length=min(1048576, len(raw)-offset))
        assert response.status_code == 200
        chunks.append(base64.b64decode(response.json()['chunks'][0]['data_base64'], validate=True))
    assert b''.join(chunks) == raw
    assert hashlib.sha256(b'money-note.sync.v1/snapshot-leaf\0'+b''.join(chunks)).hexdigest() == ref['hash']


def test_partial_batch_never_releases_first_protected_chunk(db):
    c = client(db)
    m = observe(c).json()
    body = request([m['target']['hot_ref']['hash']])
    body['items'].append(dict(path=['f'*64], offset='0', length=1))
    response = c.post(URL+'/'+m['observation_id']+'/objects', json=body, headers=headers())
    error(response, 422, 'INVALID_REQUEST')
    assert 'chunks' not in response.json()


def test_full_generation_http_reconstruction_oracle(db):
    c = client(db)
    m = observe(c).json()
    expected = graph(db, m)
    rows, facts, fetched = {t: [] for t in TABLES}, [], {}
    # O(N) traversal is deliberately TEST CODE, never the handler.
    batches, pending, size = [], [], 0
    for value in expected.values():
        if pending and (len(pending) == 64 or size+len(value[2]) > 1048576):
            batches.append(pending)
            pending, size = [], 0
        pending.append(value)
        size += len(value[2])
    if pending:
        batches.append(pending)
    for batch in batches:
        body = dict(protocol=1, request_id=str(uuid4()), items=[dict(path=v[1], offset='0', length=len(v[2])) for v in batch])
        response = c.post(URL+'/'+m['observation_id']+'/objects', json=body, headers=headers())
        assert response.status_code == 200
        for chunk, (ref, path, raw, body) in zip(response.json()['chunks'], batch, strict=True):
            fetched[ref['hash']] = base64.b64decode(chunk['data_base64'], validate=True)
            assert chunk['ref'] == ref and fetched[ref['hash']] == raw and len(raw) == int(ref['bytes'])
            if body['kind'] == 'snapshot-leaf':
                rows[body['table']].extend(v['value'] for v in body['rows'])
            if body['kind'] == 'index-leaf':
                facts.extend(body['facts'])
    with sqlite3.connect(db.path) as conn:
        conn.row_factory = sqlite3.Row
        for table in TABLES:
            raw_rows = [dict(r) for r in conn.execute('SELECT * FROM '+table)]
            if table == 'app_settings':
                raw_rows = [r for r in raw_rows if r['key'] not in SENSITIVE]
            assert sorted(map(encode, rows[table])) == sorted(map(encode, raw_rows))
    # Reference algorithm shares C1 and Fact definitions, but not incremental
    # D2b maintenance, transfer path logic, SQLite or HTTP serialization.
    from isolated_sync.patricia import Fact, Index
    from isolated_sync.canonical import Context, Namespace
    from isolated_sync.facts import build_facts, read_state
    context = Context(Namespace(**m['target']['ns']), m['target']['versions']['raw_schema'])
    with db.connect() as conn:
        catalog = build_facts(context, read_state(conn))
    assert sorted(encode(f) for f in facts) == sorted(encode(f.wire()) for f in catalog)
    index = Index.build(context, [Fact.make(f['key'], f['value']) for f in facts])
    assert index.object().ref() == m['target']['index_ref']
    assert len(fetched) == len(expected)
    assert b'synthetic-do-not-transfer' not in b''.join(fetched.values())


def test_bounded_concurrent_quota_and_same_request_status(db):
    c = client(db, limits=TransferLimits(concurrent_requests=8))
    barrier = Barrier(5)
    def create_one():
        barrier.wait(10)
        return observe(c)
    with ThreadPoolExecutor(5) as pool:
        results = list(pool.map(lambda _: create_one(), range(5)))
    assert sorted(r.status_code for r in results) == [201]*4+[429]
    with sqlite3.connect(db.path) as conn:
        assert conn.execute("SELECT count(*) FROM sync_observations WHERE status='available'").fetchone()[0] == 4
        assert conn.execute('SELECT count(*) FROM sync_observation_pins').fetchone()[0] == 20


def test_concurrent_duplicate_manifest_and_object_retries(db):
    c = client(db, limits=TransferLimits(concurrent_requests=8))
    body = dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: observe(c, body=body), range(2)))
    assert sorted(r.status_code for r in results) == [200, 201]
    assert results[0].content == results[1].content
    m = results[0].json()
    body = request([m['target']['control_ref']['hash']])
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: c.post(URL+'/'+m['observation_id']+'/objects', json=body, headers=headers()), range(2)))
    assert [r.status_code for r in results] == [200, 200]
    assert results[0].content == results[1].content


def test_transfer_concurrency_budget_and_busy_retry(db):
    entered, release = Event(), Event()
    def fault(stage, ticket):
        if stage == 'serialized':
            entered.set()
            assert release.wait(5)
    c = client(db, fault=fault, limits=TransferLimits(concurrent_requests=1))
    with ThreadPoolExecutor(1) as pool:
        pending = pool.submit(observe, c)
        assert entered.wait(5)
        error(observe(c), 503, 'ROOT_NOT_READY')
        release.set()
        first = pending.result(10)
    assert first.status_code == 201
    m = first.json()
    with sqlite3.connect(db.path) as lock:
        lock.execute('BEGIN IMMEDIATE')
        result = download(client(db), m, [m['target']['raw_ref']['hash']])
        error(result, 503, 'ROOT_NOT_READY')
        lock.rollback()
    assert download(client(db), m, [m['target']['raw_ref']['hash']]).status_code == 200


@pytest.mark.parametrize('when', ['authenticated', 'objects_prepared', 'serialized', 'terminal'])
def test_faults_and_response_loss_retry(db, when):
    c = client(db)
    m = observe(c).json()
    def fault(stage, ticket):
        if stage == when:
            raise RuntimeError('synthetic failure; must not enter public error')
    broken = download(client(db, fault=fault), m, [m['target']['control_ref']['hash']])
    error(broken, 500, 'STORAGE_FAILED')
    assert b'synthetic failure' not in broken.content
    assert download(c, m, [m['target']['control_ref']['hash']]).status_code == 200
    with sqlite3.connect(db.path) as conn:
        assert conn.execute('SELECT count(*) FROM sync_observation_pins WHERE active=1').fetchone()[0] == 5


def test_epoch_and_version_rejections(db):
    c = client(db)
    m = observe(c).json()
    error(observe(c, body=dict(protocol=2, request_id=str(uuid4()), base=None, inline_bytes=0)), 422, 'UNSUPPORTED_CONTRACT')
    db.bootstrap()
    error(download(c, m, [m['target']['raw_ref']['hash']]), 409, 'EPOCH_CHANGED')


@pytest.mark.parametrize('version', ['sync', 'canon', 'structural', 'raw_schema', 'snapshot', 'recurring_ownership', 'projection_schema', 'policy_registry'])
def test_unknown_base_version_is_unsupported_not_full_resync(db, version):
    c = client(db)
    base = observe(c).json()['target']
    base['versions'][version] = 'a'*64 if version in ('raw_schema', 'projection_schema', 'policy_registry') else base['versions'][version]+1
    # Independent domain hash, not the current-version sync_root admission
    # helper, constructs a self-consistent unsupported-version fixture.
    raw = encode({k: v for k, v in base.items() if k != 'sync_root'})
    base['sync_root'] = hashlib.sha256(b'money-note.sync.v1/view\0'+raw).hexdigest()
    response = observe(c, body=dict(protocol=1, request_id=str(uuid4()), base=base, inline_bytes=0))
    error(response, 422, 'UNSUPPORTED_CONTRACT')
    assert response.json()['error']['action'] == 'blocked'
    with sqlite3.connect(db.path) as conn:
        assert conn.execute('SELECT count(*) FROM sync_observations').fetchone()[0] == 1


def test_release_artifact_hashes_exact_bytes_and_target(db):
    bundle = release_bundle()
    artifact_path = Path(__file__).resolve().parents[2]/'docs/specimens/t66d3b-release-artifacts.json'
    assert json.loads(artifact_path.read_bytes()) == bundle
    m = observe(client(db)).json()
    for name, artifact in bundle['artifacts'].items():
        raw = base64.b64decode(artifact['data_base64'], validate=True)
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == artifact['sha256'] and len(raw) == int(artifact['bytes'])
        assert (m['target']['context']['financial_engine'] if name == 'financial_engine' else m['target']['versions'][name]) == digest
    assert bundle['versions'] == m['target']['versions']


def test_no_hash_release_artifact_or_normal_route_activation(db):
    c = client(db)
    assert c.get('/api/sync/v1/capabilities').status_code == 404  # R1 not advertised.
    assert c.get('/api/sync/v1/objects/'+'a'*64).status_code == 404
    assert c.get('/api/sync/v1/artifacts/financial_engine').status_code == 404
    assert c.delete(URL+'/'+str(uuid4())).status_code == 404
    source = Path(__file__).resolve().parents[1]/'app'
    assert not any('isolated_sync' in p.read_text() for p in source.rglob('*.py'))


def test_sql_point_access_no_financial_or_graph_scan(db):
    c = client(db)
    m = observe(c).json()
    calls = []
    connect = db.connect
    def traced():
        conn = connect()
        conn.set_trace_callback(calls.append)
        return conn
    with patch.object(db, 'connect', traced):
        assert download(c, m, [m['target']['raw_ref']['hash']]).status_code == 200
    financial = ('ledger_entries', 'cash_flows', 'card_payment_allocations', 'sync_rows', 'sync_reverse', 'sync_object_edges')
    selects = [s.lower() for s in calls if s.lstrip().upper().startswith('SELECT')]
    assert not any(' from '+table in sql for sql in selects for table in financial)
    assert all('where hash=' in s for s in selects if ' from sync_objects' in s)


def test_diagnostics_cannot_bypass_final_lease_guard(db):
    clock = [NOW]
    m = observe(client(db)).json()
    def metrics(value):
        clock[0] = NOW+timedelta(seconds=900)
    response = download(client(db, clock=lambda: clock[0], metrics=metrics), m, [m['target']['raw_ref']['hash']])
    error(response, 410, 'OBSERVATION_EXPIRED')

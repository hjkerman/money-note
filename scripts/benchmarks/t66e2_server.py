"""Test-only stdin/ASGI bridge: NEW self-owned synthetic SQLite, no listener.

Real D1/D2b/D3a/D3b/D3c and synthetic hashed sessions. JSON on stdout is a
private test pipe, never application diagnostics. No configured DB or .env.
"""
import base64
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import sys
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import auth  # noqa: E402
from isolated_sync.http import create_app  # noqa: E402
from isolated_sync.raw import MONEY_SETTINGS, TABLES, SENSITIVE  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionSandbox  # noqa: E402
from tests.test_isolated_sync_capture import ROWS, insert  # noqa: E402
from tests.test_isolated_sync_observation import NOW, EVAL  # noqa: E402


def children(body):
    # Independent schema parser, NOT PathResolver, Store.edges or E2 walker.
    if body['kind'] == 'raw-root':
        return [entry['root']['ref'] for entry in body['tables']]
    if body['kind'] == 'snapshot-node':
        return [entry['ref'] for entry in body['children']]
    if body['kind'] == 'index-root':
        return [body['facts']]
    if body['kind'] == 'index-node':
        return [body['left'], body['right']]
    return []


def oracle(db, manifest):
    objects, rows, facts = {}, {}, []
    with sqlite3.connect(db.path) as conn:
        def visit(ref, path):
            if ref['hash'] in objects:
                return
            raw = conn.execute('SELECT body FROM sync_objects WHERE hash=?', (ref['hash'],)).fetchone()[0]
            body = json.loads(raw)
            digest = hashlib.sha256(b'money-note.sync.v1/'+body['kind'].encode()+b'\0'+raw).hexdigest()
            assert digest == ref['hash'] and len(raw) == int(ref['bytes'])
            objects[digest] = dict(ref=ref, path=path, data_base64=base64.b64encode(raw).decode())
            if body['kind'] == 'snapshot-leaf':
                rows.setdefault(body['table'], []).extend(body['rows'])
            if body['kind'] == 'index-leaf':
                facts.extend(body['facts'])
            for child in children(body):
                visit(child, path+[child['hash']])
        for role in ('raw', 'index', 'hot', 'control'):
            ref = manifest['target'][role+'_ref']
            visit(ref, [ref['hash']])
        # Source rows independently read from financial SQLite, sensitive settings
        # excluded exactly as the normative snapshot representation requires.
        conn.row_factory = sqlite3.Row
        source = {table: [dict(row) for row in conn.execute('SELECT * FROM '+table)] for table in TABLES}
        source['app_settings'] = [r for r in source['app_settings'] if r['key'] not in SENSITIVE]
        revision = conn.execute('SELECT revision FROM authoritative_state_revision').fetchone()[0]
    return dict(manifest=manifest, objects=list(objects.values()), rows=rows, facts=facts,
                source=source, revision=revision)


def main():
    history = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    assert 0 <= history <= 1000
    clock = [NOW]
    token = secrets.token_urlsafe(32)
    with RetentionSandbox() as db:
        with db.connect() as conn:
            for table, row in ROWS.items():
                value = dict(row)
                if table == 'cash_flows':
                    value['amount_value'] = -50
                insert(conn, table, value)
            for n in range(history):
                insert(conn, 'ledger_entries', dict(id=1000+n, book_section='archive', entry_kind='expense',
                       entry_date='2026-07-03', title='합성 한글 😀 e\u0301 '+str(n), amount_value=1000,
                       sort_order=n, payment_key='e2-history-'+str(n)))
            for key in MONEY_SETTINGS:
                conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
            conn.execute("INSERT INTO users(id,username,password_hash) VALUES (1,'synthetic-e2','unused')")
            conn.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",
                         (auth._hash_session_token(token),))
        db.install()
        db.bootstrap()
        repo = RetentionRepository(db, clock=lambda: clock[0], evaluation=lambda: EVAL)
        # Only test wording selection is deterministic, never server production
        # financial formulas. Identical raw/context then has identical hot bytes.
        with patch('app.services.judgment.common._MESSAGE_RANDOM.randrange', return_value=0), TestClient(create_app(repo)) as client:
            initial = client.post('/api/sync/v1/observations', headers={'Authorization': 'Bearer '+token},
                                  json=dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0))
            assert initial.status_code == 201, initial.text
            manifest = initial.json()
            fixture = oracle(db, manifest)
            client.delete('/api/sync/v1/observations/'+manifest['observation_id'], headers={'Authorization': 'Bearer '+token})
            print(json.dumps(dict(token=token, fixture=fixture)), flush=True)
            for line in sys.stdin:
                request = json.loads(line)
                command = request['command']
                if command == 'http':
                    response = client.request(request['method'], request['path'], headers=request['headers'],
                                              content=base64.b64decode(request.get('body_base64', '')))
                    if request['method'] == 'POST' and request['path'] == '/api/sync/v1/observations' and response.status_code in (200, 201):
                        manifest = response.json()
                    result = dict(status=response.status_code, headers=dict(response.headers),
                                  body_base64=base64.b64encode(response.content).decode())
                elif command == 'mutate':
                    with db.connect() as conn:
                        conn.begin_capture()
                        conn.execute("UPDATE ledger_entries SET title=? WHERE id=100", ('합성 수정 '+str(uuid4()),))
                        conn.finalize()
                    result = dict(ok=True)
                elif command in ('insert_history', 'delete_history'):
                    # E3 split/delete frontier oracle. Only this freshly owned
                    # RetentionSandbox is reachable; no arbitrary SQL/path API.
                    count = request['count']
                    assert type(count) is int and 0 <= count <= 512
                    with db.connect() as conn:
                        conn.begin_capture()
                        for n in range(count):
                            if command == 'insert_history':
                                insert(conn, 'ledger_entries', dict(
                                    id=20000+n, book_section='archive', entry_kind='expense',
                                    entry_date='2026-07-03', title='E3 합성 경계 '+str(n),
                                    amount_value=1000, sort_order=n, payment_key='e3-history-'+str(n)))
                            else:
                                conn.execute('DELETE FROM ledger_entries WHERE id=?', (20000+n,))
                        conn.finalize()
                    result = dict(ok=True)
                elif command == 'advance':
                    clock[0] += timedelta(seconds=request['seconds'])
                    result = dict(ok=True)
                elif command == 'revoke':
                    with db.connect() as conn:
                        conn.execute('DELETE FROM auth_sessions')
                    result = dict(ok=True)
                elif command == 'oracle':
                    result = oracle(db, manifest)
                elif command == 'exit':
                    print('{"ok":true}', flush=True)
                    break
                else:
                    raise AssertionError('unknown synthetic command')
                print(json.dumps(result, ensure_ascii=True, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()

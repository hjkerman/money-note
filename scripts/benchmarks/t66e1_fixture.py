"""Print an E1 golden fixture from a disposable actual server generation.

Run with PYTHONPATH=backend; stdout only, no configured DB/API or file writes.
UUIDs are intentionally from the actual server bootstrap, not Dart expectations.
"""
import base64
from datetime import date, datetime, timezone
import hashlib
import json
from uuid import uuid4

from app.services.authoritative_state import BundleCredential
from isolated_sync.canonical import encode
from isolated_sync.observation import Evaluation, ObservationRepository
from isolated_sync.observation_schema import ObservationSandbox
from isolated_sync.patricia import Index
from isolated_sync.canonical import Context, Namespace
from isolated_sync.observation import versions


def fixture():
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    credential = BundleCredential(hashlib.sha256(b'synthetic-e1-fixture').hexdigest(), 1)
    with ObservationSandbox() as db:
        with db.connect() as conn:
            conn.execute("INSERT INTO users(id,username,password_hash) VALUES(1,'synthetic-e1','synthetic')")
            conn.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES(1,?,'2026-12-31T00:00:00Z')", (credential.token_hash,))
            for key in ('scheduled_income', 'cash_flow_balance', 'card_limit'):
                conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES(?,?)", (key, ' +0001000.00 '))
            for n in range(257):
                conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,entry_date,title,amount_value,sort_order,payment_key) VALUES(?,'archive','expense','2026-07-03',?,?,?,?)",
                             (n+1, '한글 😀 e\u0301 '+str(n), 1000.0, n, 'e1-'+str(n)))
        db.install()
        db.bootstrap()
        repo = ObservationRepository(db, clock=lambda: now, evaluation=lambda: Evaluation(date(2026, 10, 5), 540))
        manifest = repo.create(credential, request_id=str(uuid4()), guard=lambda: credential)
        ns = Namespace(**manifest['target']['ns'])
        empty = Index.build(Context(ns, versions()['raw_schema'])).root.object
        with db.connect() as conn:
            selected = {}
            for row in conn.execute('SELECT hash,kind,body FROM sync_objects ORDER BY hash'):
                if row['kind'] not in selected and row['kind'] in ('snapshot-leaf', 'snapshot-node', 'raw-root', 'index-root', 'index-leaf', 'index-node', 'hot', 'control'):
                    selected[row['kind']] = dict(kind=row['kind'], ref=dict(hash=row['hash'], bytes=str(len(row['body']))), data_base64=base64.b64encode(row['body']).decode())
                if row['kind'] == 'snapshot-leaf':
                    body = json.loads(row['body'])
                    if body['table'] == 'ledger_entries' and len(body['rows']) == 1:
                        selected[row['kind']] = dict(kind=row['kind'], ref=dict(hash=row['hash'], bytes=str(len(row['body']))), data_base64=base64.b64encode(row['body']).decode())
            selected['index-empty'] = dict(kind=empty.kind, ref=empty.ref(), data_base64=base64.b64encode(empty.raw).decode())
        return dict(provenance='actual isolated D2b/D3a server, synthetic SQLite; not a complete download fixture',
                    manifest_base64=base64.b64encode(encode(manifest)).decode(), objects=list(selected.values()))


if __name__ == '__main__':
    print(json.dumps(fixture(), ensure_ascii=False, separators=(',', ':')))

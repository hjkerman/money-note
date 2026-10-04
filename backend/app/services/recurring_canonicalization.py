"""Offline, explicit owner-attested metadata operation. Not a runtime repair.

No candidate matching, automatic approval, migration, or inferred mapping lives
here. The operator pins a privately reviewed manifest's SHA-256. The ordinary
canonical validators still decide whether its complete result is admissible.
"""

from collections.abc import Callable
from contextlib import contextmanager
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any

from app.config import get_settings
from app.db import SCHEMA
from app.db_migrations import _validate_current_schema
from app.money import allocation_totals, exact_money, money_sum, validate_database_money
from app.repositories.settings import list_settings
from app.services.card_charge import DiscountCard, evaluate_stored_charge, normalize_discount_policy
from app.services.clock import app_today
from app.services.financial_relationships import validate_runtime_card_payment_ownership
from app.services.snapshot import (
    _validate_confirmation_timestamp, export_snapshot_from_connection,
)
from app.services.summary import _current_summary_values, _manual_entry_discount

PURPOSE = 'owner-approved-recurring-canonicalization'
MAPPING_FIELDS = frozenset({'review_id', 'source_planned_id', 'child_location', 'child_id',
    'stable_key', 'confirmed_month', 'confirmed_at', 'owner_decision'})
MANIFEST_FIELDS = frozenset({'format_version', 'purpose', 'as_of_date', 'approved_review_ids',
    'approved_mappings_sha256', 'review_fingerprint', 'state_fingerprint',
    'financial_baseline', 'mappings'})


def encode_document(document: Any) -> bytes:
    return (json.dumps(document, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def _hash(document: Any) -> str:
    return hashlib.sha256(encode_document(document)).hexdigest()


def _load(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON member')
            result[key] = value
        return result
    document = json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    if not isinstance(document, dict):
        raise ValueError('document must be an object')
    return document


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def persistent_state(conn: sqlite3.Connection) -> dict:
    """Every persistent table and schema object, not just the selected rows."""
    def value(item):
        return {'sqlite_blob_hex': item.hex()} if isinstance(item, bytes) else item
    schema = [dict(row) for row in conn.execute(
        'SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name')]
    tables = {}
    for row in schema:
        if row['type'] == 'table':
            rows = [{key: value(item) for key, item in dict(record).items()}
                    for record in conn.execute(f'SELECT * FROM {_quoted(row["name"])}')]
            tables[row['name']] = sorted(rows, key=encode_document)
    return {'schema': schema, 'tables': tables,
            'user_version': conn.execute('PRAGMA user_version').fetchone()[0]}


def _review_fingerprint(state: dict, mappings: list[dict]) -> str:
    sources = {m['source_planned_id'] for m in mappings}
    children = {m['child_id'] for m in mappings}
    keys = {m['stable_key'] for m in mappings}
    # Collect competitors before filtering by source/epoch: NULL-source rows
    # with the same stable key are part of this guard, never positive proof.
    rows = [r for r in state['tables']['ledger_entries'] if r['id'] in sources | children
            or r['source_planned_entry_id'] in sources or r['payment_key'] in keys]
    return _hash({'mappings': mappings, 'relevant_rows': rows})


def _validate_manifest(document: dict) -> None:
    if set(document) != MANIFEST_FIELDS or type(document['format_version']) is not int or document['format_version'] != 1:
        raise ValueError('unsupported manifest format')
    if document['purpose'] != PURPOSE:
        raise ValueError('wrong manifest purpose')
    today = document['as_of_date']
    if not isinstance(today, str) or date.fromisoformat(today).isoformat() != today:
        raise ValueError('invalid financial comparison date')
    mappings = document['mappings']
    if not isinstance(mappings, list) or not 1 <= len(mappings) <= 100:
        raise ValueError('manifest must list every explicitly approved mapping')
    review_ids, children, keys, epochs = set(), set(), set(), set()
    for m in mappings:
        if not isinstance(m, dict) or set(m) != MAPPING_FIELDS:
            raise ValueError('unexpected mapping field')
        if m['owner_decision'] != 'YES':
            raise ValueError('every mapping requires an explicit owner YES')
        if not isinstance(m['review_id'], str) or not re.fullmatch(r'R[0-9]{2,3}', m['review_id']):
            raise ValueError('invalid review identity')
        if any(type(m[field]) is not int or m[field] <= 0 for field in ('source_planned_id', 'child_id')):
            raise ValueError('invalid row identity')
        if m['child_location'] not in ('current', 'archive') or not isinstance(m['stable_key'], str) or not m['stable_key']:
            raise ValueError('invalid child location or stable key')
        month = m['confirmed_month']
        if not isinstance(month, str) or not re.fullmatch(r'[0-9]{4}-(?:0[1-9]|1[0-2])', month):
            raise ValueError('invalid confirmation month')
        date.fromisoformat(month + '-01')
        _validate_confirmation_timestamp(m['confirmed_at'], 'invalid owner-approved timestamp')
        epoch = (m['source_planned_id'], month, m['confirmed_at'])
        # One source cannot have two claimed confirmations for the same month.
        source_month = epoch[:2]
        if m['review_id'] in review_ids or m['child_id'] in children or m['stable_key'] in keys or source_month in epochs:
            raise ValueError('overlapping approved mappings')
        review_ids.add(m['review_id'])
        children.add(m['child_id'])
        keys.add(m['stable_key'])
        epochs.add(source_month)
    if document['approved_review_ids'] != sorted(review_ids):
        raise ValueError('unreviewed or missing mapping')
    if document['approved_mappings_sha256'] != _hash(mappings):
        raise ValueError('approved mapping list changed')
    for field in ('approved_mappings_sha256', 'review_fingerprint', 'state_fingerprint'):
        if not isinstance(document[field], str) or not re.fullmatch('[0-9a-f]{64}', document[field]):
            raise ValueError('invalid manifest fingerprint')
    if not isinstance(document['financial_baseline'], dict) or not document['financial_baseline']:
        raise ValueError('reviewed authoritative financial baseline required')
    for key, amount in document['financial_baseline'].items():
        if type(amount) is not int:
            raise ValueError('financial baseline must contain exact integer money')
        exact_money(amount, key)


def build_manifest(conn: sqlite3.Connection, mappings: list[dict], as_of_date: str,
                   financial_baseline: dict[str, int]) -> dict:
    """Bind guards to already approved inputs; never enumerate/add mappings.

    The financial baseline is a separately reviewed authoritative calculation,
    not a Summary with its ownership validator disabled. See the runbook for
    epoch-less historical copies that current Summary intentionally refuses.
    """
    state = persistent_state(conn)
    document = {'format_version': 1, 'purpose': PURPOSE, 'as_of_date': as_of_date,
        'approved_review_ids': sorted(m['review_id'] for m in mappings),
        'approved_mappings_sha256': _hash(mappings), 'mappings': mappings,
        'review_fingerprint': _review_fingerprint(state, mappings),
        'state_fingerprint': _hash(state), 'financial_baseline': financial_baseline}
    _validate_manifest(document)
    return document


def _connection(path: Path, mode: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path.resolve().as_uri() + '?mode=' + mode, uri=True,
                           isolation_level=None, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def _integrity(conn: sqlite3.Connection) -> None:
    if [row[0] for row in conn.execute('PRAGMA integrity_check')] != ['ok'] or conn.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('database integrity/foreign-key validation failed')


@contextmanager
def _comparison_date(as_of: str):
    previous = os.environ.get('MONEY_NOTE_TODAY')
    os.environ['MONEY_NOTE_TODAY'] = as_of
    get_settings.cache_clear()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('MONEY_NOTE_TODAY', None)
        else:
            os.environ['MONEY_NOTE_TODAY'] = previous
        get_settings.cache_clear()


def _financial_observation(conn: sqlite3.Connection) -> dict[str, int]:
    """Independent exact raw components, without bypassing a Summary validator."""
    settings = list_settings(conn)
    discounts = allocation_totals(conn, 'discount')
    principal, effective_discount = 0, 0
    for record in conn.execute("SELECT * FROM ledger_entries WHERE source_planned_entry_id IS NOT NULL"):
        row = dict(record)
        row['override_discount_amount'] = discounts.get(row['payment_key'], 0)
        charge = evaluate_stored_charge(row['amount_value'], _manual_entry_discount(row),
            bool(row['discount_override'] or row['override_discount_amount'] or row['aux_amount_value']),
            normalize_discount_policy(settings.get(f"card_discount_policy:owner:{str(row['entry_date'] or '')[:7]}"), 'owner'),
            str(row['entry_date'] or '')[:7], row['title'], DiscountCard.OWNER,
            merchant=row['usage_place'], spending_category=row['spending_category'], settings=settings)
        principal += exact_money(row['amount_value'])
        effective_discount += charge.effective_discount_amount
    return {'recurring_principal': principal, 'recurring_discount': effective_discount,
            'recurring_burden': principal - effective_discount,
            'cash_flow_rows_total': money_sum(r[0] for r in conn.execute('SELECT amount_value FROM cash_flows')),
            'payment_total': money_sum(r[0] for r in conn.execute('SELECT total_amount FROM card_payment_events')),
            'payment_allocation_total': money_sum(r[0] for r in conn.execute('SELECT amount_value FROM card_payment_allocations'))}


def _preconditions(conn: sqlite3.Connection, document: dict, before: dict) -> None:
    if before['user_version'] not in (3, 4):
        raise ValueError('manual tool requires an already-current structural schema')
    _validate_current_schema(conn, SCHEMA)
    _integrity(conn)
    validate_database_money(conn)
    validate_runtime_card_payment_ownership(conn)
    if _hash(before) != document['state_fingerprint'] or _review_fingerprint(before, document['mappings']) != document['review_fingerprint']:
        raise ValueError('reviewed database changed; renewed owner review required')
    rows = {r['id']: r for r in before['tables']['ledger_entries']}
    closed = next((r['value'] for r in before['tables']['app_settings'] if r['key'] == 'last_closed_month'), '0000-00')
    for m in document['mappings']:
        source, child = rows.get(m['source_planned_id']), rows.get(m['child_id'])
        if source is None or source['entry_kind'] != 'planned' or child is None or child['entry_kind'] != 'expense':
            raise ValueError('approved source or generated expense missing')
        if (child['book_section'], child['payment_key'], child['source_planned_entry_id']) != (
                m['child_location'], m['stable_key'], m['source_planned_id']):
            raise ValueError('approved stable child/source/location does not match')
        if child['confirmed_month'] is not None or child['confirmed_at'] is not None:
            raise ValueError('epoch must be wholly absent; already-applied or incompatible mapping')
        if m['confirmed_month'] > closed and (source['confirmed_month'], source['confirmed_at']) != (
                m['confirmed_month'], m['confirmed_at']):
            raise ValueError('approved unclosed occurrence does not own current source confirmation')
        if any(r['id'] != child['id'] and r['source_planned_entry_id'] == source['id']
               and r['confirmed_month'] == m['confirmed_month'] for r in rows.values()):
            raise ValueError('another child already claims approved source/month')


def _allowed_diff(before: dict, after: dict, mappings: list[dict]) -> list[dict]:
    expected = json.loads(encode_document(before))
    rows = {r['id']: r for r in expected['tables']['ledger_entries']}
    changed = []
    for m in mappings:
        rows[m['child_id']]['confirmed_month'] = m['confirmed_month']
        rows[m['child_id']]['confirmed_at'] = m['confirmed_at']
        changed.append({'review_id': m['review_id'], 'child_id': m['child_id'],
                        'columns': ['confirmed_month', 'confirmed_at']})
    # The existing verified revision triggers run normally, once per UPDATE.
    expected['tables']['authoritative_state_revision'][0]['revision'] += len(mappings)
    expected['tables']['ledger_entries'].sort(key=encode_document)
    if expected != after:
        raise ValueError('unexpected persistent field changed outside metadata allowlist')
    return changed


def execute(db_path: Path, manifest: bytes, approved_manifest_sha256: str,
            backup_path: Path, backup_sha256: str, *, apply: bool = False,
            receipt: bytes | None = None, receipt_sha256: str | None = None,
            checkpoint: Callable[[str], None] | None = None) -> dict:
    """Dry-run uses an in-memory Online Backup and never opens target writable.

    Apply rechecks the exact same guards inside BEGIN IMMEDIATE. A prior dry-run
    receipt and independently pinned standalone verified backup are mandatory.
    Repeat apply deterministically rejects its stale preconditions, without any
    metadata or financial write. No startup/migration is invoked by this tool.
    """
    manifest_sha = hashlib.sha256(manifest).hexdigest()
    if manifest_sha != approved_manifest_sha256:
        raise ValueError('owner-approved manifest SHA-256 does not match')
    document = _load(manifest)
    _validate_manifest(document)
    if document['as_of_date'] != app_today().isoformat():
        raise ValueError('reviewed financial comparison date expired; fresh review required')
    target, backup = Path(db_path).resolve(strict=True), Path(backup_path).resolve(strict=True)
    if target.samefile(backup):
        raise ValueError('verified backup must be a separate file')
    if any(Path(str(backup) + suffix).exists() and Path(str(backup) + suffix).stat().st_size
           for suffix in ('-wal', '-journal')):
        raise ValueError('backup must be a standalone quiescent Online Backup')
    if hashlib.sha256(backup.read_bytes()).hexdigest() != backup_sha256:
        raise ValueError('verified backup SHA-256 does not match')
    signal = checkpoint or (lambda stage: None)
    signal('before_transaction')
    backup_conn = _connection(backup, 'ro')
    target_conn = _connection(target, 'rw' if apply else 'ro')
    working = target_conn if apply else sqlite3.connect(':memory:', isolation_level=None)
    working.row_factory = sqlite3.Row
    working.execute('PRAGMA foreign_keys=ON')
    try:
        backup_conn.execute('BEGIN')
        _integrity(backup_conn)
        backed_up = persistent_state(backup_conn)
        if hashlib.sha256(backup.read_bytes()).hexdigest() != backup_sha256:
            raise ValueError('verified backup changed while being read')
        target_conn.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        before = persistent_state(target_conn)
        if before != backed_up:
            raise ValueError('fresh backup does not match target logical state')
        if not apply:
            target_conn.backup(working)
            working.execute('BEGIN IMMEDIATE')
        _preconditions(working, document, before)
        binding = {'manifest_sha256': manifest_sha, 'backup_sha256': backup_sha256,
                   'before_state_fingerprint': _hash(before)}
        if apply:
            if receipt is None or hashlib.sha256(receipt).hexdigest() != receipt_sha256:
                raise ValueError('verified dry-run receipt required before apply')
            dry = _load(receipt)
            if dry.get('mode') != 'dry-run' or any(dry.get(k) != v for k, v in binding.items()) or any(dry.get('financial_difference', {}).values()):
                raise ValueError('dry-run receipt does not match current operation')
        observation = _financial_observation(working)
        signal('collected')
        for index, m in enumerate(document['mappings'], 1):
            cursor = working.execute('''UPDATE ledger_entries SET confirmed_month=?, confirmed_at=?
                WHERE id=? AND book_section=? AND payment_key=? AND source_planned_entry_id=?
                  AND confirmed_month IS NULL AND confirmed_at IS NULL''',
                (m['confirmed_month'], m['confirmed_at'], m['child_id'], m['child_location'],
                 m['stable_key'], m['source_planned_id']))
            if cursor.rowcount != 1:
                raise ValueError('approved child changed during apply')
            signal(f'updated:{index}')
        validate_database_money(working)
        _integrity(working)
        with _comparison_date(document['as_of_date']):
            summary = _current_summary_values(working)
            # Export runs all ordinary strict current-v7 contracts, not a
            # manifest-specific fallback or historical compatibility rule.
            _, snapshot = export_snapshot_from_connection(working, date.fromisoformat(document['as_of_date']))
        baseline = document['financial_baseline']
        if set(summary) != set(baseline) or summary != baseline or observation != _financial_observation(working):
            raise ValueError('financial equivalence is not zero won')
        after = persistent_state(working)
        changed = _allowed_diff(before, after, document['mappings'])
        result = {**binding, 'format_version': 1, 'purpose': PURPOSE,
            'mode': 'applied' if apply else 'dry-run', 'as_of_date': document['as_of_date'],
            'mapping_count': len(changed), 'changed_rows': changed,
            'revision_increment': len(changed), 'after_state_fingerprint': _hash(after),
            'financial_difference': {k: summary[k] - baseline[k] for k in summary},
            'raw_component_difference': {k: 0 for k in observation},
            'snapshot_id': snapshot['snapshot_id']}
        if apply:
            expected_receipt = {**result, 'mode': 'dry-run'}
            # Snapshot export time is intentionally fresh, not ownership. Every
            # deterministic state/field/financial result must still agree.
            expected_receipt['snapshot_id'] = dry.get('snapshot_id')
            if dry != expected_receipt or not isinstance(dry.get('snapshot_id'), str) or not re.fullmatch('[0-9a-f]{64}', dry['snapshot_id']):
                raise ValueError('incomplete or inconsistent dry-run receipt')
        encode_document(result)  # Required report body is serializable before COMMIT.
        signal('validated')
        signal('before_commit')
        working.execute('COMMIT' if apply else 'ROLLBACK')
        return result
    finally:
        for conn in (working, target_conn, backup_conn):
            if conn.in_transaction:
                conn.rollback()
        if working is not target_conn:
            working.close()
        target_conn.close()
        backup_conn.close()

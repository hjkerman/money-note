"""D1 proofs use owned disposable databases, never configured application DBs."""

from datetime import date
import random
import sqlite3
import subprocess
import sys
from unittest.mock import patch

import pytest

from app.db import AUTHORITATIVE_REVISION_TABLES, SCHEMA
from app.db_migrations import initialize_database


ROWS = {
    "ledger_entries": dict(id=100, book_section="current", entry_kind="expense",
                           entry_date="2026-10-05", title="card", amount_value=1200,
                           sort_order=1, payment_key="card-100", spending_category="general"),
    "monthly_panels": dict(id=100, month="2026-10", panel_type="claim", title="claim",
                           amount_value=300, sort_order=1),
    "cash_flows": dict(id=100, occurred_on="2026-10-05", title="cash", amount_value=-100,
                       sort_order=1),
    "card_payment_batches": dict(id=100, usage_month="2026-09"),
    "card_payment_batch_items": dict(id=100, batch_id=100, entry_id=100,
                                     entry_payment_key="card-100"),
    "card_payment_events": dict(id=100, batch_id=100, event_date="2026-10-05",
                                event_type="immediate", total_amount=50, cash_flow_id=100),
    "card_payment_allocations": dict(id=100, payment_event_id=100,
                                     entry_payment_key="card-100", amount_value=50),
    "card_payment_deferrals": dict(entry_payment_key="card-100", from_payment_month="2026-10",
                                   target_payment_month="2026-11"),
    "notification_candidate_registrations": dict(registration_key="reg-100", target="ledger",
                                                 target_id=100, request_fingerprint="request"),
    "app_settings": dict(key="d1-setting", value="setting"),
    "app_labels": dict(key="d1-label", value="label"),
}
KEYS = {table: next(iter(values)) for table, values in ROWS.items()}
UPDATE_COLUMNS = {
    "ledger_entries": "title", "monthly_panels": "title", "cash_flows": "title",
    "card_payment_batches": "source", "card_payment_batch_items": "entry_payment_key",
    "card_payment_events": "note", "card_payment_allocations": "entry_payment_key",
    "card_payment_deferrals": "target_payment_month",
    "notification_candidate_registrations": "request_fingerprint",
    "app_settings": "value", "app_labels": "value",
}


def insert(conn, table, values):
    fields = ",".join(values)
    conn.execute(f"INSERT INTO {table} ({fields}) VALUES ({','.join('?' for _ in values)})",
                 tuple(values.values()))


def seed(conn):
    for table, values in ROWS.items():
        insert(conn, table, values)


def raw_state(conn):
    return {table: {row[KEYS[table]]: dict(row) for row in conn.execute(f"SELECT * FROM {table}")}
            for table in ROWS}


def freeze_timestamps(conn):
    # Control volatile *stored* fields before hashing, not the resulting JSON.
    for table in AUTHORITATIVE_REVISION_TABLES:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        assignments = ",".join(f"{name}='2026-10-05 12:00:00'" for name in ("created_at", "updated_at")
                               if name in columns)
        if assignments:
            conn.execute(f"UPDATE {table} SET {assignments}")
        if "confirmed_at" in columns:
            conn.execute(f"UPDATE {table} SET confirmed_at='2026-10-05T12:00:00+00:00' "
                         "WHERE confirmed_at IS NOT NULL")


def replay(state, changes):
    for change in changes:
        table = state[change["table_name"]]
        if change["old"] is not None:
            assert table.pop(change["old_key"]) == change["old"]
        if change["new"] is not None:
            assert change["new_key"] not in table
            table[change["new_key"]] = change["new"]
    return state


@pytest.fixture
def sandbox():
    from isolated_sync.capture import CaptureSandbox

    with CaptureSandbox() as value:
        yield value


@pytest.mark.parametrize("table", AUTHORITATIVE_REVISION_TABLES)
@pytest.mark.parametrize("operation", ("INSERT", "UPDATE", "DELETE"))
def test_all_tables_exact_old_new(sandbox, table, operation):
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        conn.begin_capture()
        seed(conn)
        conn.finalize_capture()
    with sandbox.connect() as conn:
        base = raw_state(conn)
        tx_id = conn.begin_capture()
        if operation == "INSERT":
            values = dict(ROWS[table])
            values[KEYS[table]] = 200 if KEYS[table] == "id" else "second-key"
            if table == "card_payment_batch_items":
                values["entry_payment_key"] = "second-key"
            insert(conn, table, values)
        elif operation == "UPDATE":
            column = UPDATE_COLUMNS[table]
            value = "2026-12" if table == "card_payment_deferrals" else "changed 한글 😀"
            conn.execute(f"UPDATE {table} SET {column}=? WHERE {KEYS[table]}=?",
                         (value, ROWS[table][KEYS[table]]))
        else:
            conn.execute(f"DELETE FROM {table} WHERE {KEYS[table]}=?", (ROWS[table][KEYS[table]],))
        changes = read_changes(conn, tx_id)
        assert any(c["table_name"] == table and c["operation"] == operation for c in changes)
        assert replay(base, changes) == raw_state(conn)
        conn.finalize_capture()
    with sandbox.connect() as conn:
        assert read_changes(conn, tx_id) == changes
        record = conn.execute("SELECT * FROM sync_capture_commits WHERE tx_id=?", (tx_id,)).fetchone()
        assert record["target_revision"] - record["base_revision"] == len(changes)


@pytest.mark.parametrize("table", AUTHORITATIVE_REVISION_TABLES)
def test_every_table_requires_context(sandbox, table):
    with sandbox.connect() as conn:
        before = raw_state(conn)
        with pytest.raises(sqlite3.IntegrityError, match="capture context required"):
            insert(conn, table, ROWS[table])
        conn.rollback()
        assert raw_state(conn) == before


@pytest.mark.parametrize("table,key", [("cash_flows", "id"), ("app_labels", "key"),
                                      ("app_settings", "key"),
                                      ("card_payment_deferrals", "entry_payment_key"),
                                      ("notification_candidate_registrations", "registration_key")])
def test_primary_key_moves(sandbox, table, key):
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        tx_id = conn.begin_capture()
        insert(conn, table, ROWS[table])
        old = ROWS[table][key]
        new = 200 if key == "id" else "moved-key"
        conn.execute(f"UPDATE {table} SET {key}=? WHERE {key}=?", (new, old))
        change = read_changes(conn, tx_id)[-1]
        assert (change["old_key"], change["new_key"]) == (old, new)
        assert change["old"][key] == old and change["new"][key] == new
        conn.finalize_capture()


def test_all_fk_actions_capture_exact_closure(sandbox):
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        conn.begin_capture()
        seed(conn)
        conn.execute("UPDATE monthly_panels SET confirmed_cash_flow_id=100 WHERE id=100")
        insert(conn, "ledger_entries", dict(id=101, book_section="archive", title="child",
                                           sort_order=2, source_planned_entry_id=100))
        conn.finalize_capture()
    with sandbox.connect() as conn:
        before = raw_state(conn)
        tx_id = conn.begin_capture()
        conn.execute("DELETE FROM cash_flows WHERE id=100")
        conn.execute("DELETE FROM card_payment_batches WHERE id=100")
        conn.execute("DELETE FROM ledger_entries WHERE id=100")
        changes = read_changes(conn, tx_id)
        actions = {(c["table_name"], c["operation"]) for c in changes}
        assert {("monthly_panels", "UPDATE"), ("card_payment_events", "UPDATE"),
                ("card_payment_events", "DELETE"), ("card_payment_batch_items", "DELETE"),
                ("card_payment_allocations", "DELETE"), ("ledger_entries", "UPDATE")} <= actions
        assert replay(before, changes) == raw_state(conn)
        conn.finalize_capture()
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


@pytest.mark.parametrize("close_connection", [False, True])
@pytest.mark.parametrize("finalized", [False, True])
def test_rollback_or_connection_close_leaves_no_metadata(sandbox, close_connection, finalized):
    conn = sandbox.connect()
    before = raw_state(conn)
    revision = conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
    conn.begin_capture()
    seed(conn)
    if finalized:
        conn.finalize_capture()
    if close_connection:
        conn.close()
    else:
        conn.rollback()
        conn.close()
    with sandbox.connect() as reader:
        assert raw_state(reader) == before
        assert reader.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0] == revision
        for table in ("sync_tx_context", "sync_changes", "sync_change_cells", "sync_tx_fence",
                      "sync_capture_commits"):
            assert reader.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


def test_nested_savepoint_release_does_not_bypass_commit_fence(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        conn.execute("SAVEPOINT nested")
        insert(conn, "app_labels", ROWS["app_labels"])
        conn.execute("RELEASE nested")
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.commit()
        conn.rollback()
        assert conn.execute("SELECT count(*) FROM sync_changes").fetchone()[0] == 0


def test_failed_commit_can_only_be_recovered_by_finalization_or_rollback(sandbox):
    with sandbox.connect() as conn:
        tx_id = conn.begin_capture()
        insert(conn, "app_labels", ROWS["app_labels"])
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.commit()
        assert conn.in_transaction
        with sandbox.connect() as reader:
            assert reader.execute("SELECT value FROM app_labels WHERE key='d1-label'").fetchone() is None
            assert reader.execute("SELECT count(*) FROM sync_changes").fetchone()[0] == 0
        conn.finalize_capture()
        conn.commit()
    with sandbox.connect() as conn:
        assert conn.execute("SELECT tx_id FROM sync_capture_commits").fetchone()[0] == tx_id


def test_source_fk_failure_is_not_overridden_by_capture_certificate(sandbox):
    with sandbox.connect() as conn:
        before = raw_state(conn)
        conn.begin_capture()
        conn.execute("PRAGMA defer_foreign_keys=ON")
        insert(conn, "card_payment_events", ROWS["card_payment_events"])
        conn.finalize_capture()
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.commit()
        conn.rollback()
        assert raw_state(conn) == before
        assert conn.execute("SELECT count(*) FROM sync_capture_commits").fetchone()[0] == 0


@pytest.mark.parametrize("conflict", ["ABORT", "FAIL", "ROLLBACK", "IGNORE", "REPLACE"])
def test_statement_conflict_modes_preserve_source_capture_parity(sandbox, conflict):
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        tx_id = conn.begin_capture()
        before = raw_state(conn)
        try:
            conn.execute(f"INSERT OR {conflict} INTO cash_flows"
                         "(id,occurred_on,title,amount_value,sort_order) VALUES "
                         "(700,'2026-10-05','first',1,1),(700,'2026-10-05','second',2,2)")
        except sqlite3.IntegrityError:
            assert conflict in {"ABORT", "FAIL", "ROLLBACK"}
        if conn.in_transaction:
            assert replay(before, read_changes(conn, tx_id)) == raw_state(conn)
            conn.finalize_capture()
        else:
            assert conflict == "ROLLBACK"
            assert raw_state(conn) == before
            assert not read_changes(conn, tx_id)


def test_savepoint_rolls_back_changes_revision_and_finalization(sandbox):
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        tx_id = conn.begin_capture()
        insert(conn, "app_labels", ROWS["app_labels"])
        conn.execute("SAVEPOINT nested")
        conn.execute("UPDATE app_labels SET value='discard' WHERE key='d1-label'")
        conn.finalize_capture()
        conn.execute("ROLLBACK TO nested")
        conn.execute("RELEASE nested")
        assert conn.execute("SELECT count(*) FROM sync_capture_commits").fetchone()[0] == 0
        conn.execute("UPDATE app_labels SET value='keep' WHERE key='d1-label'")
        assert len(read_changes(conn, tx_id)) == 2
        conn.finalize_capture()
    with sandbox.connect() as conn:
        assert conn.execute("SELECT value FROM app_labels WHERE key='d1-label'").fetchone()[0] == "keep"


def test_writer_contention_and_fresh_transaction_ids(sandbox):
    first, second = sandbox.connect(), sandbox.connect()
    try:
        one = first.begin_capture()
        insert(first, "app_labels", ROWS["app_labels"])
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            second.begin_capture()
        first.finalize_capture()
        first.commit()
        two = second.begin_capture()
        assert one != two
        second.execute("UPDATE app_labels SET value='two' WHERE key='d1-label'")
        second.finalize_capture()
        second.commit()
        assert second.execute("SELECT count(*) FROM sync_capture_commits").fetchone()[0] == 2
    finally:
        first.close()
        second.close()


def test_interrupted_process_rolls_back_source_and_capture(sandbox):
    with sandbox.connect() as reader:
        before_revision = reader.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
    script = """
import os, sqlite3, sys
conn=sqlite3.connect(sys.argv[1])
conn.execute('PRAGMA foreign_keys=ON')
conn.execute('PRAGMA recursive_triggers=ON')
conn.execute('BEGIN IMMEDIATE')
revision=conn.execute('SELECT revision FROM authoritative_state_revision').fetchone()[0]
conn.execute('INSERT INTO sync_tx_context VALUES (1, ?, ?)', ('interrupted', revision))
conn.execute("INSERT INTO app_labels(key,value) VALUES ('interrupted','new')")
os._exit(37)
"""
    result = subprocess.run([sys.executable, "-c", script, str(sandbox.path)], check=False)
    assert result.returncode == 37
    with sandbox.connect() as conn:
        assert conn.execute("SELECT value FROM app_labels WHERE key='interrupted'").fetchone() is None
        assert conn.execute("SELECT count(*) FROM sync_changes").fetchone()[0] == 0
        assert conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0] == before_revision


@pytest.mark.parametrize("direction", ["excluded_to_included", "included_to_excluded", "excluded_only"])
@pytest.mark.parametrize("excluded_key", ["share_pin_hash", "share_pin_is_default"])
def test_sensitive_settings_are_markers_without_secrets(sandbox, direction, excluded_key):
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        tx_id = conn.begin_capture()
        initial = "d1-public" if direction == "included_to_excluded" else excluded_key
        conn.execute("INSERT INTO app_settings(key,value) VALUES (?,?)", (initial, "secret-synthetic"))
        if direction == "excluded_to_included":
            conn.execute("UPDATE app_settings SET key='d1-public',value='public' WHERE key=?", (initial,))
        elif direction == "included_to_excluded":
            conn.execute("UPDATE app_settings SET key=?,value='new-secret' WHERE key=?", (excluded_key, initial))
        else:
            conn.execute("UPDATE app_settings SET value='new-secret' WHERE key=?", (initial,))
        changes = read_changes(conn, tx_id)
        last = changes[-1]
        assert (last["old"] is not None) == (direction == "included_to_excluded")
        assert (last["new"] is not None) == (direction == "excluded_to_included")
        captured = [row[0] for row in conn.execute("SELECT value FROM sync_change_cells")]
        assert "new-secret" not in captured
        if initial == excluded_key:
            assert "secret-synthetic" not in captured
        conn.finalize_capture()


@pytest.mark.parametrize("value", [None, "", "한글 😀\x00e\u0301", 9007199254740991,
                                   -9007199254740991, 1.2345678901234567, b"\x00\xff"])
def test_capture_preserves_sqlite_storage_class_and_value(sandbox, value):
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        tx_id = conn.begin_capture()
        insert(conn, "ledger_entries", dict(id=100, book_section="current", sort_order=1,
                                           aux_amount_value=value))
        actual = conn.execute("SELECT aux_amount_value,typeof(aux_amount_value) FROM ledger_entries").fetchone()
        change = read_changes(conn, tx_id)[0]
        assert change["new"]["aux_amount_value"] == actual[0]
        cell = conn.execute("SELECT value,storage_type FROM sync_change_cells WHERE column_name='aux_amount_value'").fetchone()
        assert tuple(cell) == tuple(actual)
        conn.finalize_capture()


def test_replace_upsert_noop_and_randomized_replay(sandbox):
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        before = raw_state(conn)
        tx_id = conn.begin_capture()
        rng = random.Random(6601)
        for i in range(200):
            key = f"random-{rng.randrange(20)}"
            if rng.randrange(4) == 0:
                conn.execute("DELETE FROM app_labels WHERE key=?", (key,))
            else:
                conn.execute("INSERT OR REPLACE INTO app_labels(key,value) VALUES (?,?)", (key, str(i)))
        conn.execute("UPDATE app_labels SET value=value WHERE key LIKE 'random-%'")
        conn.execute("INSERT INTO app_labels(key,value) VALUES ('random-0','upsert') "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value")
        changes = read_changes(conn, tx_id)
        assert replay(before, changes) == raw_state(conn)
        conn.finalize_capture()


def test_revision_coverage_hole_fails_closed(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        insert(conn, "app_labels", ROWS["app_labels"])
        # Deliberate privileged corruption, not a permitted writer operation.
        conn.set_authorizer(None)
        conn.execute("DELETE FROM sync_change_cells")
        conn.execute("DELETE FROM sync_changes")
        with pytest.raises(RuntimeError, match="revision coverage"):
            conn.finalize_capture()
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.commit()
        conn.rollback()
        assert conn.execute("SELECT value FROM app_labels WHERE key='d1-label'").fetchone() is None


def test_complete_revision_markers_do_not_hide_missing_cells(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        insert(conn, "app_labels", ROWS["app_labels"])
        conn.set_authorizer(None)  # Privileged fault injection only.
        conn.execute("DELETE FROM sync_change_cells WHERE column_name='value'")
        with pytest.raises(RuntimeError, match="incomplete capture row payload"):
            conn.finalize_capture()
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.commit()
        conn.rollback()


def test_context_cannot_start_inside_an_existing_transaction(sandbox):
    with sandbox.connect() as conn:
        conn.execute("SAVEPOINT already_started")
        with pytest.raises(RuntimeError, match="new explicit transaction"):
            conn.begin_capture()
        conn.execute("RELEASE already_started")
        assert conn.execute("SELECT count(*) FROM sync_tx_context").fetchone()[0] == 0


def test_readonly_needs_no_context_and_empty_capture_can_finalize(sandbox):
    with sandbox.connect() as conn:
        conn.execute("BEGIN DEFERRED")
        before = raw_state(conn)
        conn.commit()
        conn.begin_capture()
        conn.finalize_capture()
        conn.commit()
        assert raw_state(conn) == before
        assert conn.execute("SELECT change_count FROM sync_capture_commits").fetchone()[0] == 0


def test_reused_transaction_identity_is_rejected(sandbox):
    from uuid import UUID

    with sandbox.connect() as conn:
        tx_id = conn.begin_capture()
        conn.finalize_capture()
        conn.commit()
        with patch("isolated_sync.capture.uuid4", return_value=UUID(tx_id)):
            with pytest.raises(RuntimeError, match="transaction identity reuse"):
                conn.begin_capture()
        assert not conn.in_transaction


def test_randomized_cross_table_cascade_and_statement_rollback_replay(sandbox):
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        before = raw_state(conn)
        tx_id = conn.begin_capture()
        seed(conn)
        rng = random.Random(660102)
        for sequence in range(150):
            table = rng.choice(tuple(ROWS))
            key = KEYS[table]
            rows = list(conn.execute(f"SELECT * FROM {table}"))
            action = rng.randrange(3)
            if rows and action != 0:
                row = rng.choice(rows)
                if action == 1:
                    column = UPDATE_COLUMNS[table]
                    value = "2026-12" if table == "card_payment_deferrals" else str(sequence)
                    conn.execute(f"UPDATE {table} SET {column}=? WHERE {key}=?", (value, row[key]))
                else:
                    conn.execute(f"DELETE FROM {table} WHERE {key}=?", (row[key],))
            else:
                values = dict(ROWS[table])
                values[key] = 200 + sequence if key == "id" else f"random-{sequence}"
                if table == "card_payment_batch_items":
                    values["entry_payment_key"] = f"random-{sequence}"
                try:
                    insert(conn, table, values)
                except sqlite3.IntegrityError as error:
                    assert "FOREIGN KEY" in str(error)  # Removed parent: entire statement rolls back.
        assert replay(before, read_changes(conn, tx_id)) == raw_state(conn)
        conn.finalize_capture()
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()


def test_failure_between_certificate_and_context_removal_keeps_fence(sandbox):
    with sandbox.connect() as conn:
        tx_id = conn.begin_capture()
        insert(conn, "app_labels", ROWS["app_labels"])

        def injected(action, first, second, database, source):
            if action == sqlite3.SQLITE_DELETE and first == "sync_tx_context":
                return sqlite3.SQLITE_DENY
            return conn._guard(action, first, second, database, source)

        conn.set_authorizer(injected)
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            conn.finalize_capture()
        conn.set_authorizer(conn._guard)
        assert conn.execute("SELECT * FROM sync_capture_commits WHERE tx_id=?", (tx_id,)).fetchone() is None
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.commit()
        conn.rollback()


@pytest.mark.parametrize("sql", ["DELETE FROM sync_tx_context", "DELETE FROM sync_changes",
                                "DELETE FROM sync_tx_fence", "DELETE FROM sync_capture_commits",
                                "UPDATE authoritative_state_revision SET revision=0",
                                "PRAGMA foreign_keys=OFF", "PRAGMA recursive_triggers=OFF",
                                "PRAGMA defer_foreign_keys=OFF",
                                "CREATE TEMP TRIGGER revision_app_labels_insert AFTER INSERT ON app_labels "
                                "BEGIN SELECT 1; END",
                                "DROP TRIGGER revision_app_labels_insert"])
def test_supported_connection_forbids_capture_bypass(sandbox, sql):
    with sandbox.connect() as conn:
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            conn.execute(sql)


def test_fresh_migration_data_preservation_idempotency_and_runtime_rejection():
    from isolated_sync.capture import CaptureSandbox, ISOLATED_SCHEMA_VERSION

    with CaptureSandbox(install=False) as sandbox:
        with sandbox.connect() as conn:
            seed(conn)
        with sandbox.connect() as conn:
            before = raw_state(conn)
            revision = conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
        sandbox.install()
        sandbox.install()
        with sandbox.connect() as conn:
            assert raw_state(conn) == before
            assert conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0] == revision
            assert conn.execute("PRAGMA user_version").fetchone()[0] == ISOLATED_SCHEMA_VERSION
            with pytest.raises(RuntimeError, match="unsupported future database"):
                initialize_database(conn, SCHEMA)


def test_migration_failure_is_atomic():
    from isolated_sync.capture import CaptureSandbox

    with CaptureSandbox(install=False) as sandbox:
        with sandbox.connect() as conn:
            before = tuple(conn.iterdump())
        with patch("isolated_sync.capture.validate_schema", side_effect=RuntimeError("injected admission")):
            with pytest.raises(RuntimeError, match="injected admission"):
                sandbox.install()
        with sandbox.connect() as conn:
            assert tuple(conn.iterdump()) == before


@pytest.mark.parametrize("damage", ["extra_trigger", "changed_trigger", "missing_trigger", "metadata_table",
                                   "extra_raw_column", "generated_raw_column"])
def test_schema_admission_rejects_damage(sandbox, damage):
    with sqlite3.connect(sandbox.path) as conn:
        if damage == "extra_trigger":
            conn.execute("CREATE TRIGGER surprise AFTER INSERT ON app_labels BEGIN SELECT 1; END")
        elif damage == "metadata_table":
            conn.execute("ALTER TABLE sync_changes ADD COLUMN surprise TEXT")
        elif damage == "extra_raw_column":
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN surprise TEXT")
        elif damage == "generated_raw_column":
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN surprise TEXT GENERATED ALWAYS AS (title||'x') VIRTUAL")
        else:
            conn.execute("DROP TRIGGER revision_app_labels_insert")
            if damage == "changed_trigger":
                conn.execute("CREATE TRIGGER revision_app_labels_insert AFTER INSERT ON app_labels "
                             "BEGIN UPDATE authoritative_state_revision SET revision=revision+1; END")
    with pytest.raises(RuntimeError):
        sandbox.connect()


def test_existing_financial_functions_and_snapshot_v7_parity():
    from app.repositories.cash_flows import create_cash_flow
    from app.schemas import CashFlowIn
    from app.services.snapshot import export_snapshot_from_connection, snapshot_state_fingerprint
    from app.services.summary import _summary_values_from_read_view
    from isolated_sync.capture import CaptureSandbox
    from tests.test_authoritative_state import FrozenSnapshotClock

    def observe(conn):
        with patch("app.services.snapshot.datetime", FrozenSnapshotClock):
            _, snapshot = export_snapshot_from_connection(conn, date(2026, 10, 5))
        return snapshot, snapshot_state_fingerprint(snapshot), _summary_values_from_read_view(
            conn, today=date(2026, 10, 5))

    results = []
    for captured in (False, True):
        with CaptureSandbox(install=captured) as sandbox, sandbox.connect() as conn:
            if captured:
                conn.begin_capture()
            else:
                conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE app_settings SET value='0' WHERE key IN ('scheduled_income','cash_flow_balance')")
            insert(conn, "ledger_entries", ROWS["ledger_entries"])
            flow = create_cash_flow(CashFlowIn(occurred_on="2026-10-05", title="현금 😀",
                                               amount_value=-123, sort_order=1,
                                               is_primary_income=False), conn=conn)
            conn.execute("UPDATE cash_flows SET amount_value=-456 WHERE id=?", (flow["id"],))
            freeze_timestamps(conn)
            results.append(observe(conn))
            if captured:
                conn.finalize_capture()
    assert results[0] == results[1]


@pytest.mark.parametrize("scenario", ["recurring", "fixed", "policy"])
def test_borrowed_domain_writers_and_durable_financial_parity(scenario):
    from app.repositories.entries import append_planned_entry, confirm_planned_entry, list_entries
    from app.repositories.panels import create_panel, list_panels
    from app.schemas import MonthlyPanelIn, PlannedEntryIn
    from app.services.card_charge.profiles import set_transit_discount_profile
    from app.services.card_payments import current_payment_status
    from app.services.panels import confirm_fixed_panel
    from app.services.snapshot import export_snapshot_from_connection, snapshot_state_fingerprint
    from app.services.summary import _current_summary_values
    from isolated_sync.capture import CaptureSandbox, read_changes
    from tests.test_authoritative_state import FrozenSnapshotClock

    results = []
    for captured in (False, True):
        with CaptureSandbox(install=captured) as sandbox:
            with sandbox.connect() as conn:
                tx_id = conn.begin_capture() if captured else None
                if not captured:
                    conn.execute("BEGIN IMMEDIATE")
                conn.execute("UPDATE app_settings SET value='0' WHERE key IN ('scheduled_income','cash_flow_balance')")
                if scenario == "recurring":
                    source = append_planned_entry(PlannedEntryIn(title="정기 😀", usage_place="service",
                                                               amount_value=5000, due_day=5), conn=conn)
                    with patch("app.repositories.entries.new_payment_key", return_value="fixed-synthetic-key"):
                        confirm_planned_entry(source["id"], today=date(2026, 10, 5), actual_amount=4500, conn=conn)
                elif scenario == "fixed":
                    panel = create_panel(MonthlyPanelIn(month="2026-10", panel_type="fixed", title="고정",
                                                       amount_value=5000, sort_order=1, due_day=5), conn=conn)
                    confirm_fixed_panel(panel["id"], "2026-10-05", actual_amount=4500,
                                        conn=conn, today=date(2026, 10, 5))
                else:
                    set_transit_discount_profile("2026-10", "owner", conn=conn)
                    set_transit_discount_profile("2026-10", "none", conn=conn)
                freeze_timestamps(conn)
                if captured:
                    assert read_changes(conn, tx_id)
                    conn.finalize_capture()
            with sandbox.connect() as reader:
                reader.execute("BEGIN DEFERRED")
                with patch("app.services.snapshot.datetime", FrozenSnapshotClock), patch(
                    "app.services.summary.app_today", return_value=date(2026, 10, 5)
                ):
                    _, snapshot = export_snapshot_from_connection(reader, date(2026, 10, 5))
                    results.append((snapshot, snapshot_state_fingerprint(snapshot),
                                    _current_summary_values(reader),
                                    current_payment_status(date(2026, 10, 5), conn=reader),
                                    list_entries("current", date(2026, 10, 5), conn=reader),
                                    list_panels("2026-10", include_confirmed_fixed=True, conn=reader)))
    assert results[0] == results[1]


def test_snapshot_raw_replacement_capture_and_v7_roundtrip(sandbox):
    from app.services.snapshot import (
        export_snapshot_from_connection,
        replace_reconciliation_snapshot,
        snapshot_state_fingerprint,
        validate_reconciliation_snapshot,
    )
    from isolated_sync.capture import read_changes

    with sandbox.connect() as conn:
        conn.begin_capture()
        insert(conn, "ledger_entries", ROWS["ledger_entries"])
        insert(conn, "cash_flows", ROWS["cash_flows"])
        conn.finalize_capture()
        conn.commit()
        _, snapshot = export_snapshot_from_connection(conn, date(2026, 10, 5))
        validated = validate_reconciliation_snapshot(snapshot)
        before = raw_state(conn)
        tx_id = conn.begin_capture()
        replace_reconciliation_snapshot(conn, validated)
        assert replay(before, read_changes(conn, tx_id)) == raw_state(conn)
        conn.finalize_capture()
    with sandbox.connect() as reader:
        _, restored = export_snapshot_from_connection(reader, date(2026, 10, 5))
        assert snapshot_state_fingerprint(restored) == snapshot_state_fingerprint(snapshot)
        assert restored["data"] == snapshot["data"]
        assert not reader.execute("PRAGMA foreign_key_check").fetchall()


def test_normal_authoritative_endpoint_constructor_rejects_isolated_profile(sandbox):
    from app.services.authoritative_state import BundleCredential, _construct

    with sandbox.connect() as conn:
        conn.execute("BEGIN DEFERRED")
        with pytest.raises(ValueError, match="current database version"):
            _construct(conn, BundleCredential("synthetic-unused-token", 1))


def test_unfinalized_direct_write_cannot_commit():
    from isolated_sync.capture import CaptureSandbox

    with CaptureSandbox() as sandbox:
        with sandbox.connect() as conn:
            before = conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
            conn.begin_capture()
            conn.execute("INSERT INTO app_labels(key,value) VALUES ('d1','new')")
            with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
                conn.commit()
            conn.rollback()
        with sandbox.connect() as reader:
            assert reader.execute("SELECT value FROM app_labels WHERE key='d1'").fetchone() is None
            assert reader.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0] == before
            assert reader.execute("SELECT count(*) FROM sync_changes").fetchone()[0] == 0


def test_finalized_commit_is_capture_only_not_a_sync_root():
    from isolated_sync.capture import CaptureSandbox

    with CaptureSandbox() as sandbox:
        with sandbox.connect() as conn:
            tx_id = conn.begin_capture()
            conn.execute("INSERT INTO app_labels(key,value) VALUES ('d1','new')")
            conn.finalize_capture()
        with sandbox.connect() as reader:
            assert reader.execute("SELECT value FROM app_labels WHERE key='d1'").fetchone()[0] == "new"
            record = reader.execute("SELECT * FROM sync_capture_commits WHERE tx_id=?", (tx_id,)).fetchone()
            assert record["status"] == "capture_only"
            assert record["target_revision"] - record["base_revision"] == record["change_count"] == 1
            assert not any("root" in name for name in record.keys())


def test_no_context_and_post_finalization_write_are_rejected():
    from isolated_sync.capture import CaptureSandbox

    with CaptureSandbox() as sandbox, sandbox.connect() as conn:
        with pytest.raises(sqlite3.IntegrityError, match="capture context required"):
            conn.execute("INSERT INTO app_labels(key,value) VALUES ('d1','bad')")
        conn.rollback()
        conn.begin_capture()
        conn.execute("INSERT INTO app_labels(key,value) VALUES ('d1','good')")
        conn.finalize_capture()
        with pytest.raises(sqlite3.IntegrityError, match="capture context required"):
            conn.execute("UPDATE app_labels SET value='bad' WHERE key='d1'")

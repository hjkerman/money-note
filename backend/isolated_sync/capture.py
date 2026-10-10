"""D1 capture-only schema, installable ONLY into self-owned temporary databases.

There is deliberately no existing-database/path installer, runtime feature flag,
sync endpoint, epoch bootstrap, or root finalizer here. D2 must provide those
contracts before any production integration. The isolated checkpoint is not an
application migration and is rejected by the legacy runtime.
"""

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4

from app.db import AUTHORITATIVE_REVISION_TABLES, SCHEMA
from app.db_migrations import (
    PRIMARY_KEYS,
    _apply_schema,
    _statements,
    _validate_current_schema,
    initialize_database,
)
from app.share_auth import SENSITIVE_SHARE_SETTING_KEYS


ISOLATED_SCHEMA_VERSION = 1_000_001
METADATA_SQL = """
CREATE TABLE sync_capture_profile (
    id INTEGER PRIMARY KEY CHECK (id=1),
    version INTEGER NOT NULL CHECK (version=1),
    status TEXT NOT NULL CHECK (status='isolated_capture_only')
);
CREATE TABLE sync_tx_context (
    id INTEGER PRIMARY KEY CHECK (id=1),
    tx_id TEXT NOT NULL UNIQUE,
    base_revision INTEGER NOT NULL CHECK (base_revision>=0)
);
CREATE TABLE sync_capture_commits (
    tx_id TEXT PRIMARY KEY NOT NULL,
    base_revision INTEGER NOT NULL,
    target_revision INTEGER NOT NULL,
    change_count INTEGER NOT NULL CHECK (change_count>=0),
    status TEXT NOT NULL CHECK (status='capture_only'),
    CHECK (target_revision-base_revision=change_count)
);
CREATE TABLE sync_changes (
    revision INTEGER PRIMARY KEY,
    tx_id TEXT NOT NULL,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('INSERT','UPDATE','DELETE')),
    old_key,
    new_key,
    old_visible INTEGER NOT NULL CHECK (old_visible IN (0,1)),
    new_visible INTEGER NOT NULL CHECK (new_visible IN (0,1))
);
CREATE INDEX sync_changes_tx ON sync_changes(tx_id,revision);
CREATE TABLE sync_change_cells (
    revision INTEGER NOT NULL REFERENCES sync_changes(revision),
    side TEXT NOT NULL CHECK (side IN ('old','new')),
    column_name TEXT NOT NULL,
    storage_type TEXT NOT NULL CHECK (storage_type IN ('null','integer','real','text','blob')),
    value,
    PRIMARY KEY (revision,side,column_name),
    CHECK (typeof(value)=storage_type)
);
CREATE TABLE sync_tx_fence (
    tx_id TEXT PRIMARY KEY NOT NULL,
    finalized_tx_id TEXT NOT NULL CHECK (finalized_tx_id=tx_id)
        REFERENCES sync_capture_commits(tx_id) DEFERRABLE INITIALLY DEFERRED
);
"""


@lru_cache(maxsize=1)
def _columns():
    with sqlite3.connect(":memory:") as reference:
        _apply_schema(reference, SCHEMA, {"CREATE TABLE"})
        return {table: tuple(row[1] for row in reference.execute(f"PRAGMA table_info({table})"))
                for table in AUTHORITATIVE_REVISION_TABLES}


def _visible(table, side):
    if table != "app_settings":
        return "1"
    keys = ",".join("'" + key.replace("'", "''") + "'"
                    for key in sorted(SENSITIVE_SHARE_SETTING_KEYS))
    return f"{side}.key NOT IN ({keys})"


def _trigger(table, operation):
    key, = PRIMARY_KEYS[table]
    old_key = f"OLD.{key}" if operation != "INSERT" else "NULL"
    new_key = f"NEW.{key}" if operation != "DELETE" else "NULL"
    old_visible = _visible(table, "OLD") if operation != "INSERT" else "0"
    new_visible = _visible(table, "NEW") if operation != "DELETE" else "0"
    statements = [
        "SELECT CASE WHEN (SELECT count(*) FROM sync_tx_context)!=1 "
        "THEN RAISE(ABORT,'capture context required') END;",
        "UPDATE authoritative_state_revision SET revision=revision+1 WHERE id=1;",
        "INSERT INTO sync_changes "
        "SELECT revision,tx_id," + f"'{table}','{operation}',{old_key},{new_key},"
        f"{old_visible},{new_visible} FROM authoritative_state_revision,sync_tx_context;",
        # A caller's UPSERT/FK conflict policy can override inner OR IGNORE.
        "INSERT INTO sync_tx_fence SELECT tx_id,tx_id FROM sync_tx_context "
        "WHERE NOT EXISTS (SELECT 1 FROM sync_tx_fence WHERE tx_id=sync_tx_context.tx_id);",
    ]
    for side, visible in (("OLD", old_visible), ("NEW", new_visible)):
        if visible == "0":
            continue
        for column in _columns()[table]:
            # No JSON conversion or affinity: preserve SQLite's exact typed cell.
            statements.append(
                "INSERT INTO sync_change_cells "
                f"SELECT revision,'{side.lower()}','{column}',typeof({side}.{column}),"
                f"{side}.{column} FROM authoritative_state_revision WHERE {visible};"
            )
    return (f"CREATE TRIGGER IF NOT EXISTS revision_{table}_{operation.lower()} "
            f"AFTER {operation} ON {table} BEGIN\n" + "\n".join(statements) + "\nEND;")


@lru_cache(maxsize=1)
def capture_schema():
    """Legacy table contract plus explicitly audited replacement trigger bodies."""
    base = [s for s in _statements(SCHEMA) if not s.startswith("CREATE TRIGGER")]
    return "\n".join(base + [_trigger(table, event) for table in AUTHORITATIVE_REVISION_TABLES
                             for event in ("INSERT", "UPDATE", "DELETE")])


@lru_cache(maxsize=1)
def _metadata_contract():
    with sqlite3.connect(":memory:") as reference:
        _apply_schema(reference, METADATA_SQL, {"all"})
        return tuple(reference.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name"
        ))


def validate_schema(conn):
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("capture requires foreign keys")
    if conn.execute("PRAGMA recursive_triggers").fetchone()[0] != 1:
        raise RuntimeError("capture requires recursive triggers (including REPLACE deletes)")
    if conn.execute("PRAGMA user_version").fetchone()[0] != ISOLATED_SCHEMA_VERSION:
        raise RuntimeError("invalid isolated schema version")
    _validate_current_schema(conn, capture_schema())
    for table, columns in _columns().items():
        actual_columns = {row[1] for row in conn.execute(f"PRAGMA table_xinfo({table})")}
        if actual_columns != set(columns):
            raise RuntimeError(f"unsupported capture columns: {table}")
    actual = tuple(tuple(row) for row in conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE tbl_name LIKE 'sync_%' ORDER BY type,name"
    ))
    if actual != _metadata_contract():
        raise RuntimeError("invalid capture metadata schema")
    expected = {_trigger(table, event).replace(" IF NOT EXISTS", "").rstrip(";")
                for table in AUTHORITATIVE_REVISION_TABLES for event in ("INSERT", "UPDATE", "DELETE")}
    actual = {row[0] for row in conn.execute("SELECT sql FROM sqlite_master WHERE type='trigger'")}
    if actual != expected:
        raise RuntimeError("invalid or unexpected capture trigger")
    profile = [tuple(row) for row in conn.execute("SELECT * FROM sync_capture_profile")]
    if profile != [(1, 1, "isolated_capture_only")]:
        raise RuntimeError("invalid capture profile")


def read_changes(conn, tx_id):
    result = []
    for row in conn.execute("SELECT * FROM sync_changes WHERE tx_id=? ORDER BY revision", (tx_id,)):
        change = dict(row)
        for side in ("old", "new"):
            change[side] = (dict(conn.execute(
                "SELECT column_name,value FROM sync_change_cells WHERE revision=? AND side=?",
                (row["revision"], side))) if row[f"{side}_visible"] else None)
        result.append(change)
    return result


class CaptureConnection(sqlite3.Connection):
    """Trusted metadata API; ordinary direct SQL remains database-trigger captured.

    The authorizer prevents accidental metadata/DDL/PRAGMA bypass on supported
    connections. Removing it, editing the database file, forging metadata with
    another privileged connection, or disabling FK enforcement is not supported.
    """

    _metadata_access = False

    def _guard(self, action, first, second, database, source):
        if self._metadata_access:
            return sqlite3.SQLITE_OK
        if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            if first.startswith("sync_") or first == "authoritative_state_revision":
                if source not in self._capture_trigger_names:
                    return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_PRAGMA and second is not None and first not in {
            "table_info", "table_xinfo", "index_list", "index_info", "index_xinfo",
            "foreign_key_list", "foreign_key_check", "query_only",
        }:
            # Restore uses ON, never OFF: toggling OFF can defeat deferred FKs.
            if first != "defer_foreign_keys" or second.lower() not in ("on", "1", "true"):
                return sqlite3.SQLITE_DENY
        if action in (sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_DROP_TRIGGER,
                      sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE,
                      sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX,
                      sqlite3.SQLITE_CREATE_TEMP_TRIGGER, sqlite3.SQLITE_DROP_TEMP_TRIGGER,
                      sqlite3.SQLITE_CREATE_TEMP_TABLE, sqlite3.SQLITE_DROP_TEMP_TABLE,
                      sqlite3.SQLITE_CREATE_TEMP_INDEX, sqlite3.SQLITE_DROP_TEMP_INDEX,
                      sqlite3.SQLITE_CREATE_VIEW, sqlite3.SQLITE_DROP_VIEW,
                      sqlite3.SQLITE_CREATE_TEMP_VIEW, sqlite3.SQLITE_DROP_TEMP_VIEW,
                      sqlite3.SQLITE_CREATE_VTABLE, sqlite3.SQLITE_DROP_VTABLE,
                      sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    @contextmanager
    def _metadata(self):
        self._metadata_access = True
        try:
            yield
        finally:
            self._metadata_access = False

    def begin_capture(self):
        if self.in_transaction:
            raise RuntimeError("capture requires a new explicit transaction")
        self.execute("BEGIN IMMEDIATE")
        try:
            self._validate_capture_schema()
            if self.execute("SELECT count(*) FROM sync_tx_context").fetchone()[0]:
                raise RuntimeError("stale capture context")
            tx_id = str(uuid4())
            if self.execute("SELECT 1 FROM sync_capture_commits WHERE tx_id=?", (tx_id,)).fetchone():
                raise RuntimeError("capture transaction identity reuse")
            revision = self.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
            with self._metadata():
                self.execute("INSERT INTO sync_tx_context VALUES (1,?,?)", (tx_id, revision))
                self.execute("INSERT INTO sync_tx_fence VALUES (?,?)", (tx_id, tx_id))
            return tx_id
        except BaseException:
            self.rollback()
            raise

    def finalize_capture(self):
        """D1-only coverage certificate. MUST NOT substitute for D2 finalization."""
        if not self.in_transaction:
            raise RuntimeError("capture finalization requires an active transaction")
        self._validate_capture_schema()
        contexts = self.execute("SELECT tx_id,base_revision FROM sync_tx_context").fetchall()
        if len(contexts) != 1:
            raise RuntimeError("capture finalization requires one context")
        tx_id, base = contexts[0]
        target = self.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
        changes = read_changes(self, tx_id)
        if (target < base or len(changes) != target - base
                or any(c["revision"] != base + offset for offset, c in enumerate(changes, 1))):
            raise RuntimeError("incomplete capture revision coverage")
        for change in changes:
            if change["table_name"] not in _columns():
                raise RuntimeError("invalid capture table")
            for side in ("old", "new"):
                if change[side] is not None and set(change[side]) != set(_columns()[change["table_name"]]):
                    raise RuntimeError("incomplete capture row payload")
        # Native COMMIT checks every FK, including the fence. Do not scan all
        # historical tables here; D2 must add incremental structural closure.
        with self._metadata():
            savepoint = "finalize_" + uuid4().hex
            self.execute(f"SAVEPOINT {savepoint}")
            try:
                self.execute("INSERT INTO sync_capture_commits VALUES (?,?,?,?,'capture_only')",
                             (tx_id, base, target, len(changes)))
                self.execute("DELETE FROM sync_tx_context WHERE tx_id=?", (tx_id,))
                self.execute(f"RELEASE {savepoint}")
            except BaseException:
                try:
                    self.execute(f"ROLLBACK TO {savepoint}")
                    self.execute(f"RELEASE {savepoint}")
                except BaseException:
                    self.rollback()
                    raise
                raise

    def _validate_capture_schema(self):
        """Isolated subclasses may supply a stricter, versioned schema contract."""
        validate_schema(self)

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class CaptureSandbox:
    """Owns a disposable actual migrated DB. Cannot target an existing DB path."""

    def __init__(self, *, install=True):
        self._temporary = tempfile.TemporaryDirectory(prefix="money-note-d1-")
        try:
            with self.connect() as conn:
                initialize_database(conn, SCHEMA)
            if install:
                self.install()
        except BaseException:
            self._temporary.cleanup()
            raise

    @property
    def path(self):
        return Path(self._temporary.name) / "synthetic.sqlite3"

    def connect(self):
        conn = sqlite3.connect(self.path, factory=CaptureConnection, timeout=0.1, cached_statements=0)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA recursive_triggers=ON")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version == ISOLATED_SCHEMA_VERSION:
                validate_schema(conn)
                conn._capture_trigger_names = {
                    f"revision_{table}_{event}" for table in AUTHORITATIVE_REVISION_TABLES
                    for event in ("insert", "update", "delete")
                }
                conn.set_authorizer(conn._guard)
            elif version not in (0, 4):
                raise RuntimeError("unsupported sandbox schema")
            return conn
        except BaseException:
            conn.close()
            raise

    def install(self):
        conn = self.connect()
        try:
            if conn.execute("PRAGMA user_version").fetchone()[0] == ISOLATED_SCHEMA_VERSION:
                return
            conn.execute("BEGIN IMMEDIATE")
            initialize_database(conn, SCHEMA)
            _apply_schema(conn, METADATA_SQL, {"all"})
            for table in AUTHORITATIVE_REVISION_TABLES:
                for event in ("INSERT", "UPDATE", "DELETE"):
                    conn.execute(f"DROP TRIGGER revision_{table}_{event.lower()}")
                    conn.execute(_trigger(table, event))
            conn.execute("INSERT INTO sync_capture_profile VALUES (1,1,'isolated_capture_only')")
            conn.execute(f"PRAGMA user_version={ISOLATED_SCHEMA_VERSION}")
            validate_schema(conn)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._temporary.cleanup()

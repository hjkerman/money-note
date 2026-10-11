"""D3c versioned, self-owned disposable SQLite profile. Never a runtime migration.

Historical certificates keep every field and both deferred fences. Only object
availability FKs move to live roots; financial tables/triggers are unchanged.
"""

from functools import lru_cache
from pathlib import Path
import sqlite3

from app.db import AUTHORITATIVE_REVISION_TABLES
from app.db_migrations import _apply_schema, _statements
from isolated_sync import capture, finalization, observation_schema
from isolated_sync.canonical import decode_c1, encode, fail


VERSION = 1_000_005


def evidence_sql(sql):
    # Named, reviewed availability constraints only. Certificate/fence identity
    # FKs, non-null digest fields, CHECKs and every financial FK remain intact.
    for table in ("sync_commits", "sync_observations", "sync_observation_pins"):
        statements = _statements(sql)
        sql = "\n".join(s.replace(" REFERENCES sync_objects(hash)", "") if
                        s.startswith("CREATE TABLE "+table+" ") else s for s in statements)
    return sql


SQL = """
CREATE TABLE sync_retention_profile (id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL CHECK(version=1),status TEXT NOT NULL CHECK(status='isolated_synthetic_gc'));
CREATE TABLE sync_gc_fence (id INTEGER PRIMARY KEY CHECK(id=1),serial INTEGER NOT NULL CHECK(typeof(serial)='integer' AND serial>=0));
CREATE TABLE sync_gc_counts (hash TEXT PRIMARY KEY NOT NULL REFERENCES sync_objects(hash) ON DELETE CASCADE,incoming INTEGER NOT NULL CHECK(incoming>=0),pins INTEGER NOT NULL CHECK(pins>=0));
CREATE INDEX sync_gc_zero ON sync_gc_counts(incoming,pins,hash);
CREATE INDEX sync_gc_edge_child ON sync_object_edges(child,parent);
CREATE TABLE sync_retention_roots (scope TEXT NOT NULL CHECK(scope IN ('current','observation','explicit')),owner TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('raw','index','input','hot','control')),hash TEXT NOT NULL REFERENCES sync_objects(hash),PRIMARY KEY(scope,owner,role));
CREATE INDEX sync_retention_hash ON sync_retention_roots(hash);
CREATE TABLE sync_observation_lifecycle (id TEXT PRIMARY KEY NOT NULL REFERENCES sync_observations(id) ON DELETE CASCADE,charge INTEGER NOT NULL CHECK(charge>=0),released INTEGER NOT NULL CHECK(released IN (0,1)));
CREATE INDEX sync_lifecycle_released ON sync_observation_lifecycle(released,id);
CREATE TABLE sync_observation_replays (credential_hash TEXT NOT NULL,request_id TEXT NOT NULL,request_hash TEXT NOT NULL,namespace BLOB NOT NULL,charge INTEGER NOT NULL CHECK(charge>=0),PRIMARY KEY(credential_hash,request_id));
CREATE INDEX sync_retention_expiry ON sync_observations(status,expires_at,id);
CREATE INDEX sync_retention_view_hot ON sync_observation_views(hot_hash,control_hash);
CREATE TRIGGER sync_gc_object_insert AFTER INSERT ON sync_objects BEGIN
 INSERT INTO sync_gc_counts VALUES (NEW.hash,0,0);
 UPDATE sync_gc_fence SET serial=serial+1 WHERE id=1;
END;
CREATE TRIGGER sync_gc_object_delete BEFORE DELETE ON sync_objects BEGIN
 SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM sync_gc_counts WHERE hash=OLD.hash AND incoming=0 AND pins=0) THEN RAISE(ABORT,'protected immutable object') END;
 UPDATE sync_gc_fence SET serial=serial+1 WHERE id=1;
END;
CREATE TRIGGER sync_gc_edge_insert AFTER INSERT ON sync_object_edges BEGIN
 UPDATE sync_gc_counts SET incoming=incoming+1 WHERE hash=NEW.child;
 UPDATE sync_gc_fence SET serial=serial+1 WHERE id=1;
END;
CREATE TRIGGER sync_gc_edge_delete AFTER DELETE ON sync_object_edges BEGIN
 UPDATE sync_gc_counts SET incoming=incoming-1 WHERE hash=OLD.child;
 UPDATE sync_gc_fence SET serial=serial+1 WHERE id=1;
END;
CREATE TRIGGER sync_gc_root_insert AFTER INSERT ON sync_retention_roots BEGIN
 UPDATE sync_gc_counts SET pins=pins+1 WHERE hash=NEW.hash;
 UPDATE sync_gc_fence SET serial=serial+1 WHERE id=1;
END;
CREATE TRIGGER sync_gc_root_delete AFTER DELETE ON sync_retention_roots BEGIN
 UPDATE sync_gc_counts SET pins=pins-1 WHERE hash=OLD.hash;
 UPDATE sync_gc_fence SET serial=serial+1 WHERE id=1;
END;
CREATE TRIGGER sync_gc_current_insert AFTER INSERT ON sync_current BEGIN
 INSERT INTO sync_retention_roots SELECT 'current','1','raw',NEW.raw_hash;
 INSERT INTO sync_retention_roots SELECT 'current','1','index',NEW.index_hash;
 INSERT INTO sync_retention_roots SELECT 'current','1','input',input_hash FROM sync_commits WHERE tx_id=NEW.tx_id;
END;
CREATE TRIGGER sync_gc_current_update AFTER UPDATE ON sync_current BEGIN
 DELETE FROM sync_retention_roots WHERE scope='current';
 INSERT INTO sync_retention_roots SELECT 'current','1','raw',NEW.raw_hash;
 INSERT INTO sync_retention_roots SELECT 'current','1','index',NEW.index_hash;
 INSERT INTO sync_retention_roots SELECT 'current','1','input',input_hash FROM sync_commits WHERE tx_id=NEW.tx_id;
END;
CREATE TRIGGER sync_gc_current_delete AFTER DELETE ON sync_current BEGIN
 DELETE FROM sync_retention_roots WHERE scope='current';
END;
CREATE TRIGGER sync_gc_pin_insert AFTER INSERT ON sync_observation_pins WHEN NEW.active=1 BEGIN
 INSERT INTO sync_retention_roots VALUES ('observation',NEW.observation_id,NEW.role,NEW.hash);
END;
CREATE TRIGGER sync_gc_pin_update AFTER UPDATE ON sync_observation_pins BEGIN
 SELECT CASE WHEN OLD.active=0 AND NEW.active=1 THEN RAISE(ABORT,'released pin') END;
 DELETE FROM sync_retention_roots WHERE scope='observation' AND owner=OLD.observation_id AND role=OLD.role;
 INSERT INTO sync_retention_roots SELECT 'observation',NEW.observation_id,NEW.role,NEW.hash WHERE NEW.active=1;
END;
CREATE TRIGGER sync_gc_pin_delete AFTER DELETE ON sync_observation_pins BEGIN
 DELETE FROM sync_retention_roots WHERE scope='observation' AND owner=OLD.observation_id AND role=OLD.role;
END;
CREATE TRIGGER sync_gc_observation_terminal BEFORE UPDATE OF status ON sync_observations WHEN OLD.status='retired' AND NEW.status<>'retired' BEGIN
 SELECT RAISE(ABORT,'retired observation');
END;
"""

# Any mutation capable of invalidating a mark/metadata validation changes the
# same transactional fence. Small fixed trigger overhead, never an object scan.
for _table in ("sync_objects", "sync_rows", "sync_object_edges", "sync_retention_roots",
               "sync_gc_counts", "sync_commits", "sync_observations", "sync_observation_pins",
               "sync_observation_lifecycle", "sync_observation_views", "sync_observation_replays", "sync_observation_budget"):
    for _op in ("INSERT", "UPDATE", "DELETE"):
        SQL += (f"CREATE TRIGGER sync_gc_fence_{_table}_{_op.lower()} AFTER {_op} ON {_table} BEGIN "
                "UPDATE sync_gc_fence SET serial=serial+1 WHERE id=1; END;\n")


@lru_cache(maxsize=1)
def metadata_contract():
    with sqlite3.connect(":memory:") as conn:
        _apply_schema(conn, capture.capture_schema(), {"all"})
        _apply_schema(conn, capture.METADATA_SQL+finalization.SQL+observation_schema.SQL, {"all"})
        rebuild_evidence(conn)
        _apply_schema(conn, SQL, {"all"})
        return tuple(conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE tbl_name LIKE 'sync_%' OR name LIKE 'sync_%' ORDER BY type,name"))


def rebuild_evidence(conn):
    for table, source in (("sync_commits", finalization.SQL), ("sync_observations", observation_schema.SQL),
                          ("sync_observation_pins", observation_schema.SQL)):
        statement = next(s for s in _statements(evidence_sql(source)) if s.startswith("CREATE TABLE "+table+" "))
        temporary = table+"_replacement"
        conn.execute(statement.replace("CREATE TABLE "+table+" ", "CREATE TABLE "+temporary+" ", 1))
        conn.execute(f"INSERT INTO {temporary} SELECT * FROM {table}")
        conn.execute(f"DROP TABLE {table}")
        conn.execute(f"ALTER TABLE {temporary} RENAME TO {table}")
    for statement in _statements(observation_schema.SQL):
        if statement.startswith("CREATE INDEX") and " ON sync_observation" in statement:
            conn.execute(statement)


def validate_schema(conn):
    finalization.validate_schema(conn, version=VERSION, metadata=metadata_contract())
    if [tuple(r) for r in conn.execute("SELECT * FROM sync_retention_profile")] != [(1, 1, "isolated_synthetic_gc")]:
        fail("REJECT_RETENTION_PROFILE")
    if [tuple(r) for r in conn.execute("SELECT * FROM sync_observation_profile")] != [(1, 1, "isolated_observation")]:
        fail("REJECT_OBSERVATION_PROFILE")
    for table, field in (("sync_gc_fence", "serial"), ("sync_observation_budget", "used_bytes")):
        rows = conn.execute(f"SELECT id,{field},typeof({field}) FROM {table}").fetchall()
        if len(rows) != 1 or rows[0][0] != 1 or rows[0][1] < 0 or rows[0][2] != 'integer':
            fail("REJECT_RETENTION_ACCOUNTING")


class RetentionConnection(observation_schema.ObservationConnection):
    def _validate_capture_schema(self):
        if self.execute("PRAGMA user_version").fetchone()[0] == VERSION:
            validate_schema(self)
        else:
            super()._validate_capture_schema()

    def _epoch_bootstrapped(self, namespace):
        if self.execute("PRAGMA user_version").fetchone()[0] != VERSION:
            return super()._epoch_bootstrapped(namespace)
        self.execute("UPDATE sync_observations SET status='retired' WHERE namespace<>?", (encode(namespace.wire()),))
        self.execute("UPDATE sync_observation_pins SET active=0 WHERE active=1 AND observation_id IN (SELECT id FROM sync_observations WHERE status='retired')")
        self.execute("UPDATE sync_observation_lifecycle SET released=1 WHERE id IN (SELECT id FROM sync_observations WHERE status='retired')")


def charge(row, identity_bytes, hot_bytes, control_bytes):
    # Charge shared hot/control per observation, conservatively. Reclaiming one
    # payer cannot under-account bytes still used by another observation.
    return sum(len(row[k]) for k in ("response", "request_body", "target"))+identity_bytes+hot_bytes+control_bytes+1024


class RetentionSandbox(observation_schema.ObservationSandbox):
    """Own a NEW temporary DB. No existing-path/flag/environment admission."""
    def __init__(self):
        super().__init__()
        self._owned_file = (self.path.stat().st_dev, self.path.stat().st_ino)

    def assert_owned(self):
        path = self.path
        if (path.is_symlink() or path.parent.resolve() != Path(self._temporary.name).resolve() or
                (path.stat().st_dev, path.stat().st_ino) != self._owned_file):
            fail("REJECT_SYNTHETIC_OWNERSHIP")

    def connect(self):
        if hasattr(self, "_owned_file"):
            self.assert_owned()
        conn = sqlite3.connect(self.path, factory=RetentionConnection, timeout=0.1, cached_statements=0)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA recursive_triggers=ON")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            validators = {VERSION: validate_schema, observation_schema.VERSION: observation_schema.validate_schema,
                          finalization.VERSION: finalization.validate_schema, capture.ISOLATED_SCHEMA_VERSION: capture.validate_schema}
            if version in validators:
                validators[version](conn)
                if version == VERSION and conn.execute("PRAGMA journal_mode").fetchone()[0] != 'wal':
                    fail("REJECT_RETENTION_JOURNAL")
                conn._capture_trigger_names = {f"revision_{t}_{op}" for t in AUTHORITATIVE_REVISION_TABLES
                                               for op in ("insert", "update", "delete")}
                conn.set_authorizer(conn._guard)
            elif version not in (0, 4):
                fail("REJECT_SANDBOX_VERSION")
            return conn
        except BaseException:
            conn.close()
            raise

    def install(self, *, fault=None):
        self.assert_owned()
        with self.connect() as conn:
            if conn.execute("PRAGMA user_version").fetchone()[0] == VERSION:
                validate_schema(conn)
                return
        super().install()
        # SQLite's table rebuild requires FK OFF *before* BEGIN. Only this
        # owned, validated, quiescent migration connection does so. No raw
        # writes; full FK check before COMMIT, then ON plus strict admission.
        conn = sqlite3.connect(self.path, factory=RetentionConnection, cached_statements=0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA recursive_triggers=ON")
            observation_schema.validate_schema(conn)
            # Owned experimental file ONLY. A mark snapshot must not hold back
            # financial COMMIT for an O(graph) traversal in rollback journal.
            if conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] != 'wal':
                fail("REJECT_RETENTION_JOURNAL")
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("BEGIN EXCLUSIVE")
            actual = tuple(tuple(r) for r in conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE tbl_name LIKE 'sync_%' OR name LIKE 'sync_%' ORDER BY type,name"))
            if (conn.execute("PRAGMA user_version").fetchone()[0] != observation_schema.VERSION or
                    actual != observation_schema.metadata_contract()):
                fail("REJECT_MIGRATION_SCHEMA")
            if conn.execute("SELECT 1 FROM sync_tx_context").fetchone() or conn.execute("PRAGMA foreign_key_check").fetchall():
                fail("REJECT_MIGRATION_STATE")
            rebuild_evidence(conn)
            _apply_schema(conn, SQL, {"CREATE TABLE", "CREATE INDEX"})
            conn.execute("INSERT INTO sync_retention_profile VALUES (1,1,'isolated_synthetic_gc')")
            conn.execute("INSERT INTO sync_gc_fence VALUES (1,0)")
            conn.execute("INSERT INTO sync_gc_counts SELECT hash,(SELECT count(*) FROM sync_object_edges WHERE child=hash),0 FROM sync_objects")
            current = conn.execute("SELECT * FROM sync_current WHERE id=1").fetchone()
            if current:
                cert = conn.execute("SELECT * FROM sync_commits WHERE tx_id=?", (current["tx_id"],)).fetchone()
                for role in ("raw", "index", "input"):
                    conn.execute("INSERT INTO sync_retention_roots VALUES ('current','1',?,?)", (role, cert[role+"_hash"]))
            conn.execute("INSERT INTO sync_retention_roots SELECT 'observation',observation_id,role,hash FROM sync_observation_pins WHERE active=1")
            conn.execute("UPDATE sync_gc_counts SET pins=(SELECT count(*) FROM sync_retention_roots WHERE sync_retention_roots.hash=sync_gc_counts.hash)")
            total = 0
            for row in conn.execute("SELECT * FROM sync_observations").fetchall():
                target = decode_c1(row["target"])
                hot = conn.execute("SELECT length(body) FROM sync_objects WHERE hash=?", (target["hot_ref"]["hash"],)).fetchone()
                control = conn.execute("SELECT length(body) FROM sync_objects WHERE hash=?", (target["control_ref"]["hash"],)).fetchone()
                identity = encode({k: target[k] for k in ("ns", "revision", "versions", "context", "hot_ref")})
                value = charge(row, len(identity), hot[0], control[0])
                released = not conn.execute("SELECT 1 FROM sync_observation_pins WHERE observation_id=? AND active=1", (row["id"],)).fetchone()
                conn.execute("INSERT INTO sync_observation_lifecycle VALUES (?,?,?)", (row["id"], value, int(released)))
                total += value
            conn.execute("UPDATE sync_observation_budget SET used_bytes=? WHERE id=1", (total,))
            _apply_schema(conn, SQL, {"CREATE TRIGGER"})
            conn.execute(f"PRAGMA user_version={VERSION}")
            if fault:
                fault("migration", conn)
            if conn.execute("PRAGMA foreign_key_check").fetchall():
                fail("REJECT_MIGRATION_FK")
            conn.commit()
            conn.execute("PRAGMA foreign_keys=ON")
            validate_schema(conn)
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

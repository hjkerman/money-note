"""D3a synthetic-only profile. No configured-path installer or runtime import."""

from functools import lru_cache
import sqlite3

from app.db import AUTHORITATIVE_REVISION_TABLES
from app.db_migrations import _apply_schema
from isolated_sync import capture, finalization
from isolated_sync.canonical import encode, fail

VERSION = 1_000_004
SQL = """
CREATE TABLE sync_observation_profile (id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL CHECK(version=1),status TEXT NOT NULL CHECK(status='isolated_observation'));
CREATE TABLE sync_observations (id TEXT PRIMARY KEY NOT NULL,request_id TEXT NOT NULL,credential_hash TEXT NOT NULL,principal_id INTEGER NOT NULL CHECK(principal_id>0),namespace BLOB NOT NULL,request_body BLOB NOT NULL,target BLOB NOT NULL,response BLOB NOT NULL,tx_id TEXT NOT NULL REFERENCES sync_commits(tx_id),input_hash TEXT NOT NULL REFERENCES sync_objects(hash),validated_at TEXT NOT NULL,expires_at TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('available','retired')),UNIQUE(credential_hash,request_id));
CREATE INDEX sync_observation_quota ON sync_observations(principal_id,status,expires_at);
CREATE TABLE sync_observation_pins (observation_id TEXT NOT NULL REFERENCES sync_observations(id),role TEXT NOT NULL CHECK(role IN ('raw','index','hot','control','input')),hash TEXT NOT NULL REFERENCES sync_objects(hash),active INTEGER NOT NULL CHECK(active IN (0,1)),PRIMARY KEY(observation_id,role));
CREATE INDEX sync_observation_pin_hash ON sync_observation_pins(hash,active);
CREATE TABLE sync_observation_views (identity BLOB PRIMARY KEY NOT NULL,hot_hash TEXT NOT NULL REFERENCES sync_objects(hash),control_hash TEXT NOT NULL REFERENCES sync_objects(hash));
CREATE TABLE sync_observation_budget (id INTEGER PRIMARY KEY CHECK(id=1),used_bytes INTEGER NOT NULL CHECK(used_bytes>=0));
"""


@lru_cache(maxsize=1)
def metadata_contract():
    with sqlite3.connect(":memory:") as conn:
        _apply_schema(conn, capture.capture_schema(), {"all"})
        _apply_schema(conn, capture.METADATA_SQL + finalization.SQL + SQL, {"all"})
        return tuple(conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE tbl_name LIKE 'sync_%' OR name LIKE 'sync_%' ORDER BY type,name"))


def validate_schema(conn):
    finalization.validate_schema(conn, version=VERSION, metadata=metadata_contract())
    if [tuple(r) for r in conn.execute("SELECT * FROM sync_observation_profile")] != [(1, 1, "isolated_observation")]:
        fail("REJECT_OBSERVATION_PROFILE")
    budget = conn.execute("SELECT id,used_bytes,typeof(used_bytes) FROM sync_observation_budget").fetchall()
    if len(budget) != 1 or budget[0][0] != 1 or budget[0][1] < 0 or budget[0][2] != 'integer':
        fail("REJECT_OBSERVATION_BUDGET")


class ObservationConnection(finalization.FinalizationConnection):
    def _validate_capture_schema(self):
        version = self.execute("PRAGMA user_version").fetchone()[0]
        if version == VERSION:
            validate_schema(self)
        else:
            super()._validate_capture_schema()

    def _epoch_bootstrapped(self, namespace):
        if self.execute("PRAGMA user_version").fetchone()[0] == VERSION:
            # Only the mandatory cold-bootstrap invalidation, NOT general lease
            # release/expiry/GC. Old records remain as non-authorizing evidence.
            self.execute("UPDATE sync_observations SET status='retired' WHERE namespace<>?", (encode(namespace.wire()),))
            self.execute("UPDATE sync_observation_pins SET active=0 WHERE observation_id IN (SELECT id FROM sync_observations WHERE status='retired')")


class ObservationSandbox(finalization.FinalizationSandbox):
    """Own a new temporary DB; seed, install, bootstrap, then use repository."""

    def connect(self):
        conn = sqlite3.connect(self.path, factory=ObservationConnection, timeout=0.1, cached_statements=0)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA recursive_triggers=ON")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            validators = {VERSION: validate_schema, finalization.VERSION: finalization.validate_schema,
                          capture.ISOLATED_SCHEMA_VERSION: capture.validate_schema}
            if version in validators:
                validators[version](conn)
                conn._capture_trigger_names = {f"revision_{t}_{op}" for t in AUTHORITATIVE_REVISION_TABLES
                                               for op in ("insert", "update", "delete")}
                conn.set_authorizer(conn._guard)
            elif version not in (0, 4):
                fail("REJECT_SANDBOX_VERSION")
            return conn
        except BaseException:
            conn.close()
            raise

    def install(self):
        with self.connect() as conn:
            if conn.execute("PRAGMA user_version").fetchone()[0] == VERSION:
                validate_schema(conn)
                return
        super().install()
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn._metadata():
                _apply_schema(conn, SQL, {"all"})
                conn.execute("INSERT INTO sync_observation_profile VALUES (1,1,'isolated_observation')")
                conn.execute("INSERT INTO sync_observation_budget VALUES (1,0)")
                conn.execute(f"PRAGMA user_version={VERSION}")
            validate_schema(conn)

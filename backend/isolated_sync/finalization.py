"""D2b experimental profile: atomic raw/object/index/aggregate finalization.

Only FinalizationSandbox owns/installs these databases. No configured path,
FastAPI dependency, normal migration, observation, transfer or GC entry point.
"""

from functools import lru_cache
import hashlib
import sqlite3
from time import perf_counter
from uuid import uuid4

from app.db import AUTHORITATIVE_REVISION_TABLES
from app.db_migrations import _apply_schema, _validate_current_schema
from isolated_sync import capture
from isolated_sync.canonical import Context, Namespace, decode_c1, encode, fail
from isolated_sync.facts import build_facts, read_state
from isolated_sync.maintenance import aggregate_keys, aggregates, closure, coalesce, update_adjacency, update_row_facts
from isolated_sync.inputs import checked_total, input_index, input_key
from isolated_sync.patricia import Fact, Index
from isolated_sync.raw import PRIMARY, SHAPES, SENSITIVE, TABLES, Row
from isolated_sync.segments import Tree, raw_root
from isolated_sync.store import Store, row_object


VERSION = 1_000_003
SQL = """
CREATE TABLE sync_finalization_profile (id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL CHECK(version=3),status TEXT NOT NULL CHECK(status='isolated_authoritative'));
CREATE TABLE sync_objects (hash TEXT PRIMARY KEY NOT NULL,kind TEXT NOT NULL,body BLOB NOT NULL CHECK(typeof(body)='blob'));
CREATE TABLE sync_object_edges (parent TEXT NOT NULL REFERENCES sync_objects(hash),child TEXT NOT NULL REFERENCES sync_objects(hash),PRIMARY KEY(parent,child));
CREATE TABLE sync_rows (hash TEXT PRIMARY KEY NOT NULL,body BLOB NOT NULL CHECK(typeof(body)='blob'));
CREATE TABLE sync_commits (tx_id TEXT PRIMARY KEY NOT NULL,base_epoch TEXT NOT NULL,base_revision INTEGER NOT NULL,target_epoch TEXT NOT NULL,target_revision INTEGER NOT NULL,raw_hash TEXT NOT NULL REFERENCES sync_objects(hash),index_hash TEXT NOT NULL REFERENCES sync_objects(hash),input_hash TEXT NOT NULL REFERENCES sync_objects(hash),change_count INTEGER NOT NULL,status TEXT NOT NULL CHECK(status='complete'),CHECK(target_revision>=base_revision));
CREATE TABLE sync_authority_fence (tx_id TEXT PRIMARY KEY NOT NULL REFERENCES sync_capture_commits(tx_id) DEFERRABLE INITIALLY DEFERRED,finalized_tx_id TEXT NOT NULL CHECK(finalized_tx_id=tx_id) REFERENCES sync_commits(tx_id) DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE sync_current (id INTEGER PRIMARY KEY CHECK(id=1),namespace BLOB NOT NULL,raw_schema TEXT NOT NULL,revision INTEGER NOT NULL,raw_hash TEXT NOT NULL REFERENCES sync_objects(hash),index_hash TEXT NOT NULL REFERENCES sync_objects(hash),tx_id TEXT NOT NULL REFERENCES sync_commits(tx_id));
CREATE TABLE sync_reverse (dst_table TEXT NOT NULL,dst_key BLOB NOT NULL,src_table TEXT NOT NULL,src_key BLOB NOT NULL,field TEXT NOT NULL,PRIMARY KEY(dst_table,dst_key,src_table,src_key,field));
CREATE INDEX sync_reverse_source ON sync_reverse(src_table,src_key);
CREATE TABLE sync_context_reverse (src_table TEXT NOT NULL,src_key BLOB NOT NULL,PRIMARY KEY(src_table,src_key));
CREATE TABLE sync_cash_prefix (ordinal INTEGER PRIMARY KEY,total TEXT NOT NULL);
CREATE TABLE sync_totals (domain TEXT NOT NULL,key TEXT NOT NULL,total TEXT NOT NULL,PRIMARY KEY(domain,key));
CREATE INDEX sync_fk_entry_source ON ledger_entries(source_planned_entry_id);
CREATE INDEX sync_fk_panel_cash ON monthly_panels(confirmed_cash_flow_id);
CREATE INDEX sync_fk_event_batch ON card_payment_events(batch_id);
CREATE INDEX sync_fk_event_cash ON card_payment_events(cash_flow_id);
CREATE INDEX sync_fk_item_entry ON card_payment_batch_items(entry_id);
CREATE INDEX sync_fk_allocation_event ON card_payment_allocations(payment_event_id);
CREATE INDEX sync_input_cash_sort ON cash_flows(sort_order);
CREATE INDEX sync_input_cash_month ON cash_flows(substr(occurred_on,1,7),is_primary_income);
CREATE INDEX sync_input_ledger_month ON ledger_entries(substr(entry_date,1,7));
CREATE INDEX sync_input_panel_type ON monthly_panels(panel_type);
CREATE INDEX sync_input_event_type_batch ON card_payment_events(event_type,batch_id);
CREATE INDEX sync_input_reverse_field ON sync_reverse(dst_table,dst_key,field,src_table,src_key);
CREATE INDEX sync_input_recurring_epoch ON ledger_entries(source_planned_entry_id,confirmed_month,confirmed_at);
CREATE INDEX sync_input_ledger_kind ON ledger_entries(entry_kind);
CREATE INDEX sync_input_ledger_epoch ON ledger_entries(confirmed_month);
CREATE INDEX sync_input_capture_fence_finalized ON sync_tx_fence(finalized_tx_id);
CREATE INDEX sync_input_authority_fence_finalized ON sync_authority_fence(finalized_tx_id);
"""


def schema_artifact():
    """Immutable isolated release descriptor; not a production compatibility ID."""
    return encode(dict(profile="isolated-d2b/1", canon=1, structural=1, snapshot=7,
                       tables=[dict(name=t, primary=PRIMARY[t], columns=SHAPES[t]) for t in TABLES],
                       excluded_settings=sorted(SENSITIVE),
                       capture_schema_sha256=hashlib.sha256(capture.capture_schema().encode()).hexdigest()))


RAW_SCHEMA = hashlib.sha256(schema_artifact()).hexdigest()


@lru_cache(maxsize=1)
def metadata_contract():
    with sqlite3.connect(":memory:") as conn:
        _apply_schema(conn, capture.capture_schema(), {"all"})
        _apply_schema(conn, capture.METADATA_SQL + SQL, {"all"})
        return tuple(conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE tbl_name LIKE 'sync_%' OR name LIKE 'sync_%' ORDER BY type,name"))


def validate_schema(conn, *, version=VERSION, metadata=None):
    # A later isolated profile supplies its EXACT extended contract, never an
    # allow-unknown exception. Legacy/D2b callers retain their original checks.
    if conn.execute("PRAGMA user_version").fetchone()[0] != version:
        fail("REJECT_FINALIZATION_VERSION")
    if any(conn.execute(f"PRAGMA {p}").fetchone()[0] != 1 for p in ("foreign_keys", "recursive_triggers")):
        fail("REJECT_FINALIZATION_PRAGMA")
    _validate_current_schema(conn, capture.capture_schema())
    for table, columns in capture._columns().items():
        if {r[1] for r in conn.execute(f"PRAGMA table_xinfo({table})")} != set(columns):
            fail("REJECT_FINALIZATION_COLUMNS")
    actual = tuple(tuple(r) for r in conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE tbl_name LIKE 'sync_%' OR name LIKE 'sync_%' ORDER BY type,name"))
    if actual != (metadata_contract() if metadata is None else metadata):
        fail("REJECT_FINALIZATION_SCHEMA")
    expected = {capture._trigger(t, op).replace(" IF NOT EXISTS", "").rstrip(";")
                for t in TABLES for op in ("INSERT", "UPDATE", "DELETE")}
    if {r[0] for r in conn.execute("SELECT sql FROM sqlite_master WHERE type='trigger'")} != expected:
        fail("REJECT_FINALIZATION_TRIGGER")
    if [tuple(r) for r in conn.execute("SELECT * FROM sync_capture_profile")] != [(1, 1, "isolated_capture_only")]:
        fail("REJECT_CAPTURE_PROFILE")
    if [tuple(r) for r in conn.execute("SELECT * FROM sync_finalization_profile")] != [(1, 3, "isolated_authoritative")]:
        fail("REJECT_FINALIZATION_PROFILE")


def generation(conn):
    row = conn.execute("SELECT * FROM sync_current WHERE id=1").fetchone()
    if row is None:
        fail("REJECT_BOOTSTRAP_REQUIRED")
    ns = Namespace(**decode_c1(row["namespace"]))
    if row["raw_schema"] != RAW_SCHEMA:
        fail("REJECT_RAW_SCHEMA")
    context = Context(ns, row["raw_schema"])
    store = Store(conn, context)

    def ref(digest):
        size = conn.execute("SELECT length(body) FROM sync_objects WHERE hash=?", (digest,)).fetchone()
        if size is None:
            fail("REJECT_OBJECT_MISSING")
        return dict(hash=digest, bytes=str(size[0]))

    raw = store.get(ref(row["raw_hash"]), {"raw-root"})
    if set(raw.body()) != set(context.fields()) | {"kind", "tables"}:
        fail("REJECT_RAW_ROOT")
    descriptors = raw.body()["tables"]
    if (type(descriptors) is not list or any(type(t) is not dict or set(t) != {"name", "root", "count"}
            for t in descriptors) or [t["name"] for t in descriptors] != list(TABLES)):
        fail("REJECT_TABLE_COVERAGE")
    trees = {t["name"]: store.tree(t["name"], t["root"]) for t in descriptors}
    if any(t["count"] != t["root"]["count"] for t in descriptors):
        fail("REJECT_TABLE_COUNT")
    index = store.index(ref(row["index_hash"]))
    certificate = conn.execute("SELECT * FROM sync_commits WHERE tx_id=?", (row["tx_id"],)).fetchone()
    if certificate is None or any(certificate[k] != row[k] for k in ("raw_hash", "index_hash")) or (
            certificate["target_epoch"] != ns.epoch or certificate["target_revision"] != row["revision"]):
        fail("REJECT_GENERATION_CERTIFICATE")
    return row, context, store, trees, index


def _persist_row(conn, context, row):
    digest, raw = row_object(context, row)
    previous = conn.execute("SELECT body FROM sync_rows WHERE hash=?", (digest,)).fetchone()
    if previous and previous[0] != raw:
        fail("REJECT_ROW_OBJECT_CONFLICT")
    if not previous:
        conn.execute("INSERT INTO sync_rows VALUES (?,?)", (digest, raw))
        return len(raw)
    return 0


def _derived(index, changes):
    events, deltas, active = {}, {}, 0
    context_changed, closed = False, None
    for old, new in changes:
        for row, sign in ((old, -1), (new, 1)):
            if row is None:
                continue
            value = row.value()
            if row.table == "card_payment_events":
                events[row.key.value] = new is not None
            elif row.table == "card_payment_allocations":
                event = value["payment_event_id"]
                count, total = deltas.get(event, (0, 0))
                deltas[event] = (count + sign, total + sign * int(value["amount_value"]))
            elif row.table == "card_payment_batches":
                active += sign * (value["status"] == "active")
            elif row.table == "app_settings" and row.key.value == "last_closed_month":
                context_changed, closed = True, new.value()["value"] if new else None
    for event in sorted(events.keys() | deltas.keys()):
        key = ["aggregate", "event", ["i", str(event)]]
        previous = index.lookup(key)
        if previous:
            count, total = map(int, decode_c1(previous.value))
            index = index.delete(key)
        else:
            count = total = 0
        dc, dt = deltas.get(event, (0, 0))
        if events.get(event, True):
            if count + dc < 0:
                fail("REJECT_EVENT_AGGREGATE")
            index = index.put(Fact.make(key, [str(count + dc), str(total + dt)]))
    key = ["aggregate", "active_batch"]
    count = int(decode_c1(index.lookup(key).value)) + active
    if not 0 <= count <= 1:
        fail("REJECT_ACTIVE_BATCH")
    if active:
        index = index.put(Fact.make(key, str(count)), replace=True)
    if context_changed:
        index = index.put(Fact.make(["context", "last_closed_month"], closed), replace=True)
    return index


class FinalizationConnection(capture.CaptureConnection):
    def _epoch_bootstrapped(self, namespace):
        """Later isolated profiles may invalidate their own epoch-bound metadata."""

    def _validate_capture_schema(self):
        validate_schema(self)

    def begin_capture(self):
        """D1 context plus an additional authoritative fence; no cap-only bypass."""
        started = perf_counter()
        tx_id = super().begin_capture()
        try:
            current = self.execute("SELECT revision FROM sync_current WHERE id=1").fetchone()
            revision = self.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
            if current is None or current[0] != revision:
                fail("REJECT_BASE_REVISION")
            with self._metadata():
                self.execute("INSERT INTO sync_authority_fence VALUES (?,?)", (tx_id, tx_id))
            self.metrics = {"begin_ms": (perf_counter()-started)*1000}
            return tx_id
        except BaseException:
            self.rollback()
            raise

    def finalize_capture(self):
        fail("REJECT_CAPTURE_ONLY_AUTHORITY")

    def finalize(self, *, expected_epoch=None, expected_revision=None, fault=None):
        """Failure rolls the entire transaction back; no partially completed retry.

        `fault(stage)` is an explicit isolated failure-injection/diagnostic hook,
        never a normal application callback. No source writes may follow finalize.
        """
        def checkpoint(stage, start):
            self.metrics[stage + "_ms"] = (perf_counter()-start)*1000
            if fault:
                fault(stage)
            return perf_counter()

        try:
            start = perf_counter()
            base, context, store, trees, index = generation(self)
            if ((expected_epoch is not None and expected_epoch != context.ns.epoch) or
                    (expected_revision is not None and expected_revision != base["revision"])):
                fail("REJECT_BASE_IDENTITY")
            contexts = self.execute("SELECT tx_id,base_revision FROM sync_tx_context").fetchall()
            if len(contexts) != 1 or contexts[0][1] != base["revision"]:
                fail("REJECT_BASE_CONTEXT")
            tx_id = contexts[0][0]
            changes = capture.read_changes(self, tx_id)
            # Audited D1 validates exact trigger/schema/R/cell coverage and closes
            # the source-write context. The SECOND fence remains unresolved.
            capture.CaptureConnection.finalize_capture(self)
            start = checkpoint("capture", start)
            net = coalesce(changes, trees, self)
            start = checkpoint("coalescing", start)
            for old, _ in net:
                if old:
                    trees[old.table] = trees[old.table].delete(old.key)
            for _, new in net:
                if new:
                    trees[new.table] = trees[new.table].put(new)
            start = checkpoint("trees", start)
            index = update_row_facts(context, index, net)
            index = _derived(index, net)
            start = checkpoint("facts", start)
            with self._metadata():
                for old, new in net:
                    update_adjacency(self, old, new)
                self.metrics["closure_rows"] = closure(self, trees, net, index)
            start = checkpoint("closure", start)
            inputs = input_index(self, store, base["tx_id"])
            touched = set().union(*(aggregate_keys(r) for pair in net for r in pair)) if net else set()
            for domain, key in touched:
                checked_total(self, inputs, domain, key)
            with self._metadata():
                for old, new in net:
                    aggregates(self, old, -1)
                    aggregates(self, new, 1)
            for domain, key in sorted(touched):
                if domain == "cash_prefix":
                    record = self.execute("SELECT total FROM sync_cash_prefix WHERE ordinal=?", (int(key),)).fetchone()
                else:
                    record = self.execute("SELECT total FROM sync_totals WHERE domain=? AND key=?", (domain, key)).fetchone()
                fact_key = input_key(domain, key)
                if record is None:
                    inputs = inputs.delete(fact_key)
                else:
                    inputs = inputs.put(Fact.make(fact_key, record[0]), replace=inputs.lookup(fact_key) is not None)
            start = checkpoint("aggregates", start)
            with self._metadata():
                row_bytes = row_writes = 0
                for old, new in net:
                    if new:
                        size = _persist_row(self, context, new)
                        row_bytes += size
                        row_writes += bool(size)
                for tree in trees.values():
                    store.persist_tree(tree.root)
                store.persist_index(index.root)
                store.persist_index(inputs.root)
                raw, idx = raw_root(context, trees), index.object()
                store.put(raw)
                store.put(idx)
                store.put(inputs.object())
            start = checkpoint("objects", start)
            revision = self.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
            with self._metadata():
                self.execute("INSERT INTO sync_commits VALUES (?,?,?,?,?,?,?,?,?, 'complete')",
                             (tx_id, context.ns.epoch, base["revision"], context.ns.epoch, revision,
                              raw.hash, idx.hash, inputs.object().hash, len(changes)))
                self.execute("UPDATE sync_current SET revision=?,raw_hash=?,index_hash=?,tx_id=? WHERE id=1",
                             (revision, raw.hash, idx.hash, tx_id))
            checkpoint("root", start)
            self.metrics.update(changes=len(changes), net_rows=len(net), object_reads=store.reads,
                                object_writes=store.writes, object_bytes=store.bytes_written,
                                row_object_writes=row_writes, row_object_bytes=row_bytes,
                                changed_leaves=store.changed_leaves, changed_tree_nodes=store.changed_tree_nodes,
                                changed_index_nodes=store.changed_index_nodes)
            return dict(self.metrics)
        except BaseException:
            self.rollback()
            raise


class FinalizationSandbox(capture.CaptureSandbox):
    """Self-owned synthetic DB only. Seed normal data, install, then bootstrap."""
    def __init__(self):
        super().__init__(install=False)

    def connect(self):
        conn = sqlite3.connect(self.path, factory=FinalizationConnection, timeout=0.1, cached_statements=0)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA recursive_triggers=ON")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version in (VERSION, capture.ISOLATED_SCHEMA_VERSION):
                (validate_schema if version == VERSION else capture.validate_schema)(conn)
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
        # D1 installer validates the complete old schema. D2b migration is then
        # atomic, with no source changes and no current authority until bootstrap.
        with self.connect() as existing:
            if existing.execute("PRAGMA user_version").fetchone()[0] == VERSION:
                validate_schema(existing)
                return
        capture.CaptureSandbox.install(self)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn._metadata():
                _apply_schema(conn, SQL, {"all"})
                conn.execute("INSERT INTO sync_finalization_profile VALUES (1,3,'isolated_authoritative')")
                conn.execute(f"PRAGMA user_version={VERSION}")
            validate_schema(conn)

    def bootstrap(self):
        """EXCLUSIVE O(N), rotate epoch on EACH explicit cold bootstrap/restart."""
        with self.connect() as conn:
            conn.execute("BEGIN EXCLUSIVE")
            conn._validate_capture_schema()
            prior = conn.execute("SELECT namespace FROM sync_current WHERE id=1").fetchone()
            identity = decode_c1(prior[0]) if prior else dict(server_id=str(uuid4()), dataset_id=str(uuid4()))
            context = Context(Namespace(identity["server_id"], identity["dataset_id"], str(uuid4())), RAW_SCHEMA)
            data = read_state(conn)
            facts = build_facts(context, data)
            trees = {t: Tree.build(context, t, [Row.make(t, r) for r in data[t]]) for t in TABLES}
            index, store = Index.build(context, facts), Store(conn, context)
            with conn._metadata():
                for table in ("sync_reverse", "sync_context_reverse", "sync_cash_prefix", "sync_totals"):
                    conn.execute(f"DELETE FROM {table}")
                for table in TABLES:
                    for value in data[table]:
                        row = Row.make(table, value)
                        _persist_row(conn, context, row)
                        update_adjacency(conn, None, row)
                        aggregates(conn, row, 1)
                for tree in trees.values():
                    tree.validate()
                    store.persist_tree(tree.root)
                index.validate()
                store.persist_index(index.root)
                input_facts = [Fact.make(input_key("cash_prefix", r[0]), r[1]) for r in conn.execute("SELECT ordinal,total FROM sync_cash_prefix")]
                input_facts.extend(Fact.make(input_key(r[0], r[1]), r[2]) for r in conn.execute("SELECT domain,key,total FROM sync_totals"))
                inputs = Index.build(context, input_facts)
                store.persist_index(inputs.root)
                store.put(inputs.object())
                raw, idx = raw_root(context, trees), index.object()
                store.put(raw)
                store.put(idx)
                revision = conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
                tx_id = str(uuid4())
                conn.execute("INSERT INTO sync_commits VALUES (?,?,?,?,?,?,?,?,?, 'complete')",
                             (tx_id, identity.get("epoch", context.ns.epoch), revision, context.ns.epoch, revision, raw.hash, idx.hash, inputs.object().hash, 0))
                conn.execute("INSERT OR REPLACE INTO sync_current VALUES (1,?,?,?,?,?,?)",
                             (encode(context.ns.wire()), RAW_SCHEMA, revision, raw.hash, idx.hash, tx_id))
                conn._epoch_bootstrapped(context.ns)
            return context

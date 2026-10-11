"""Explicit synthetic maintenance, never normal startup or financial-row GC.

Mark uses a coherent read snapshot. Each bounded sweep rechecks a transactional
publication/object fence under BEGIN IMMEDIATE, then drains validated zero-count
objects. A stale mark cannot delete. No persisted half-round is authoritative.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import hashlib
from time import perf_counter

from isolated_sync.canonical import Context, Namespace, Object, decode_c1, fail
from isolated_sync.finalization import RAW_SCHEMA
from isolated_sync.observation import ObservationRepository, accepted_generation, reject, timestamp, uuid, versions
from isolated_sync.raw import Row, SHAPES
from isolated_sync.retention_schema import RetentionSandbox
from isolated_sync.roots import sync_root
from isolated_sync.store import row_object
from isolated_sync.transfer import Edge, PathResolver


ROLES = {"raw": "raw-root", "index": "index-root", "input": "index-root", "hot": "hot", "control": "control"}
# Credential/nonce/request digest + namespace + conservative row framing.
REPLAY_CHARGE = 512


def session_valid(row, now):
    try:
        expiry = datetime.fromisoformat(row["session_expiry"].replace("Z", "+00:00"))
        return bool(row["session_active"]) and expiry.tzinfo is not None and expiry > now
    except (ValueError, TypeError, AttributeError):
        return False


class RetentionRepository(ObservationRepository):
    """D3a contract plus opt-in lifecycle; no GC over configurable DB paths."""
    def __init__(self, sandbox, **kwargs):
        if not isinstance(sandbox, RetentionSandbox):
            fail("REJECT_SYNTHETIC_OWNERSHIP")
        sandbox.assert_owned()
        super().__init__(sandbox, **kwargs)

    def _metadata_charge(self, conn, payload, request, target, identity, hot, control):
        return len(payload)+len(request)+len(target)+len(identity)+len(hot.raw)+len(control.raw)+1024

    def _record_charge(self, conn, observation_id, value):
        conn.execute("INSERT INTO sync_observation_lifecycle VALUES (?,?,0)", (observation_id, value))

    def _admit_request(self, conn, credential, request_id, request):
        row = conn.execute("SELECT request_hash,namespace FROM sync_observation_replays WHERE credential_hash=? AND request_id=?",
                           (credential.token_hash, request_id)).fetchone()
        if row is not None:
            if row["request_hash"] != hashlib.sha256(request).hexdigest():
                reject("REQUEST_CONFLICT")
            reject("OBSERVATION_EXPIRED", "new_observation")

    def _record(self, conn, row):
        """Metadata-only complete pin association, even after objects retire."""
        target, response = decode_c1(row["target"]), decode_c1(row["response"])
        if (target.get("sync_root") != sync_root({k: v for k, v in target.items() if k != "sync_root"}) or
                response.get("target") != target or response.get("observation_id") != row["id"] or
                response.get("expires_at") != row["expires_at"] or target["ns"] != decode_c1(row["namespace"]) or
                target["principal_id"] != row["principal_id"]):
            fail("REJECT_RETENTION_OBSERVATION")
        cert = conn.execute("SELECT * FROM sync_commits WHERE tx_id=?", (row["tx_id"],)).fetchone()
        if cert is None or cert["status"] != "complete" or any(cert[k] != value for k, value in (
                ("raw_hash", target["raw_ref"]["hash"]), ("index_hash", target["index_ref"]["hash"]),
                ("input_hash", row["input_hash"]), ("target_epoch", target["ns"]["epoch"]),
                ("target_revision", int(target["revision"])))):
            fail("REJECT_RETENTION_CERTIFICATE")
        expected = {role: target[role+"_ref"]["hash"] for role in ("raw", "index", "hot", "control")}
        expected["input"] = row["input_hash"]
        pins = list(conn.execute("SELECT role,hash,active FROM sync_observation_pins WHERE observation_id=?", (row["id"],)))
        state = conn.execute("SELECT charge,released FROM sync_observation_lifecycle WHERE id=?", (row["id"],)).fetchone()
        if (state is None or {r[0]: r[1] for r in pins} != expected or
                any(r[2] != 1-state["released"] for r in pins) or (row["status"] == "available" and state["released"])):
            fail("REJECT_RETENTION_PINS")
        return target, state

    def _release(self, conn, retired, row, fault):
        _, state = self._record(conn, row)
        if state["released"]:
            return False
        with conn._metadata():
            conn.execute("UPDATE sync_observations SET status='retired' WHERE id=?", (row["id"],))
            retired.add(row["id"])
            if fault:
                fault("retired", conn)
            for role in ROLES:
                conn.execute("UPDATE sync_observation_pins SET active=0 WHERE observation_id=? AND role=? AND active=1", (row["id"], role))
                if fault:
                    fault("release_"+role, conn)
            conn.execute("UPDATE sync_observation_lifecycle SET released=1 WHERE id=?", (row["id"],))
        return True

    def release(self, observation_id, credential, *, guard, fault=None):
        """Same original credential, atomic/idempotent 204 repository operation."""
        uuid(observation_id)
        with self._connection() as (conn, retired):
            self._guard(conn, credential, guard)
            row = conn.execute("SELECT * FROM sync_observations WHERE id=?", (observation_id,)).fetchone()
            if row is not None:
                if row["principal_id"] != credential.user_id or row["credential_hash"] != credential.token_hash:
                    reject("PRINCIPAL_OR_SESSION_CHANGED", "reauthenticate")
                self._release(conn, retired, row, fault)
            self._guard(conn, credential, guard)
            if fault:
                fault("before_commit", conn)
        if fault:
            fault("after_commit", None)

    def maintain(self, *, limit=128, reclaim=True, fault=None):
        """Explicit bounded metadata maintenance, not called by normal requests.

        Replay digests survive while the original credential row AND epoch
        exist. Timestamp expiry/inactive user state can reverse with clock
        rollback/reactivation, so neither is durable credential invalidation.
        Digests have no object FKs and consume the same finite byte budget.
        """
        if type(limit) is not int or not 1 <= limit <= 4096:
            fail("REJECT_MAINTENANCE_LIMIT")
        released = reclaimed = replay_reclaimed = 0
        started = perf_counter()
        with self._connection() as (conn, retired):
            accepted_generation(conn)
            now = self.clock()
            timestamp(now)
            namespace = conn.execute("SELECT namespace FROM sync_current WHERE id=1").fetchone()[0]
            rows = conn.execute("""SELECT o.*,s.expires_at AS session_expiry,u.is_active AS session_active
                FROM sync_observations o JOIN sync_observation_lifecycle l ON l.id=o.id
                LEFT JOIN auth_sessions s ON s.session_token_hash=o.credential_hash AND s.user_id=o.principal_id
                LEFT JOIN users u ON u.id=s.user_id WHERE l.released=0 ORDER BY o.id""").fetchall()
            for row in rows:
                if row["status"] == "retired" or row["expires_at"] <= timestamp(now) or row["namespace"] != namespace or not session_valid(row, now):
                    released += self._release(conn, retired, row, fault)
                    if released >= limit:
                        break
            with conn._metadata():
                # Bound evidence lifetime to its actual authorization context.
                stale = conn.execute("""SELECT r.*,EXISTS(SELECT 1 FROM auth_sessions s
                    WHERE s.session_token_hash=r.credential_hash) AS credential_present
                    FROM sync_observation_replays r""").fetchall()
                for row in stale:
                    if row["namespace"] != namespace or not row["credential_present"]:
                        conn.execute("DELETE FROM sync_observation_replays WHERE credential_hash=? AND request_id=?", (row["credential_hash"], row["request_id"]))
                        conn.execute("UPDATE sync_observation_budget SET used_bytes=used_bytes-? WHERE id=1", (row["charge"],))
                        replay_reclaimed += 1
                        if replay_reclaimed >= limit:
                            break
                if reclaim:
                    rows = conn.execute("""SELECT o.*,EXISTS(SELECT 1 FROM auth_sessions s
                        WHERE s.session_token_hash=o.credential_hash) AS credential_present
                        FROM sync_observations o JOIN sync_observation_lifecycle l ON l.id=o.id
                        WHERE o.status='retired' AND l.released=1 ORDER BY o.id LIMIT ?""", (limit,)).fetchall()
                    for row in rows:
                        _, state = self._record(conn, row)
                        refund = state["charge"]
                        if row["namespace"] == namespace and row["credential_present"]:
                            conn.execute("INSERT INTO sync_observation_replays VALUES (?,?,?,?,?)", (
                                row["credential_hash"], row["request_id"], hashlib.sha256(row["request_body"]).hexdigest(), namespace, REPLAY_CHARGE))
                            refund -= REPLAY_CHARGE
                        conn.execute("DELETE FROM sync_observation_pins WHERE observation_id=?", (row["id"],))
                        conn.execute("DELETE FROM sync_observations WHERE id=?", (row["id"],))
                        conn.execute("UPDATE sync_observation_budget SET used_bytes=used_bytes-? WHERE id=1", (refund,))
                        reclaimed += 1
                        if fault:
                            fault("reclaimed", conn)
                prune_views(conn)
            if fault:
                fault("before_commit", conn)
        if fault:
            fault("after_commit", None)
        return dict(released=released, metadata_reclaimed=reclaimed, replay_reclaimed=replay_reclaimed,
                    lifecycle_ms=(perf_counter()-started)*1000)


def prune_views(conn):
    # A cache entry is not extra authority. Remove it before its unpinned
    # object FKs could obstruct collection; immutable active retry bytes remain.
    conn.execute("""DELETE FROM sync_observation_views WHERE
        NOT EXISTS (SELECT 1 FROM sync_retention_roots WHERE hash=hot_hash) OR
        NOT EXISTS (SELECT 1 FROM sync_retention_roots WHERE hash=control_hash)""")


@dataclass(frozen=True)
class Mark:
    owner: object
    fence: int
    reachable: frozenset
    candidates: tuple
    row_candidates: tuple
    roots: int
    objects: int
    edges: int
    bytes: int
    mark_ms: float


class Collector:
    """Default dry-run. apply=True requires positive owned synthetic admission."""
    def __init__(self, repository, *, max_objects=1_000_000, max_bytes=1 << 30):
        if not isinstance(repository, RetentionRepository) or not isinstance(repository.sandbox, RetentionSandbox):
            fail("REJECT_SYNTHETIC_OWNERSHIP")
        if type(max_objects) is not int or max_objects < 1 or type(max_bytes) is not int or max_bytes < 1024:
            fail("REJECT_GC_LIMIT")
        self.repo, self.owner = repository, object()
        self.max_objects, self.max_bytes = max_objects, max_bytes

    def _roots(self, conn):
        accepted, proof, _ = accepted_generation(conn)
        current = accepted[0]
        expected = {("current", "1", role, digest) for role, digest in (
            ("raw", current["raw_hash"]), ("index", current["index_hash"]), ("input", proof["hash"]))}
        rows = conn.execute("SELECT * FROM sync_observations").fetchall()
        if len(rows) != conn.execute("SELECT count(*) FROM sync_observation_lifecycle").fetchone()[0]:
            fail("REJECT_RETENTION_LIFECYCLE")
        for row in rows:
            target, state = self.repo._record(conn, row)
            if not state["released"]:
                roots = {role: target[role+"_ref"]["hash"] for role in ("raw", "index", "hot", "control")}
                roots["input"] = row["input_hash"]
                expected.update(("observation", row["id"], role, digest) for role, digest in roots.items())
        actual = {tuple(r) for r in conn.execute("SELECT scope,owner,role,hash FROM sync_retention_roots")}
        if {r for r in actual if r[0] != "explicit"} != expected:
            fail("REJECT_RETENTION_ROOTS")
        budget = conn.execute("SELECT used_bytes FROM sync_observation_budget WHERE id=1").fetchone()[0]
        charged = conn.execute("SELECT coalesce(sum(charge),0) FROM sync_observation_lifecycle").fetchone()[0]
        charged += conn.execute("SELECT coalesce(sum(charge),0) FROM sync_observation_replays").fetchone()[0]
        if budget != charged:
            fail("REJECT_RETENTION_BUDGET")
        return actual

    def mark(self, *, fault=None):
        self.repo.sandbox.assert_owned()
        started = perf_counter()
        with self.repo.sandbox.connect() as conn:
            conn.execute("BEGIN")  # Snapshot, not an O(N) writer lock.
            fence = conn.execute("SELECT serial FROM sync_gc_fence WHERE id=1").fetchone()[0]
            roots = self._roots(conn)
            counts, total = conn.execute("SELECT count(*),coalesce(sum(length(body)),0) FROM sync_objects").fetchone()
            row_count, row_bytes = conn.execute("SELECT count(*),coalesce(sum(length(body)),0) FROM sync_rows").fetchone()
            if counts+row_count > self.max_objects or total+row_bytes > self.max_bytes:
                fail("REJECT_GC_LIMIT")
            objects, children, validators = {}, {}, {}
            interpretation = versions()
            for row in conn.execute("SELECT * FROM sync_objects"):
                obj = Object(row["kind"], row["body"])
                body = obj.body()
                if obj.hash != row["hash"] or type(body.get("canon")) is not int or body["canon"] != 1:
                    fail("REJECT_RETENTION_OBJECT")
                Namespace(**body["ns"])
                if obj.kind not in {"hot", "control"} and body.get("raw_schema") != RAW_SCHEMA:
                    fail("REJECT_RETENTION_VERSION")
                target = dict(ns=body["ns"], versions=interpretation, context=body.get("context"))
                resolver = PathResolver(conn, self.repo, target)
                table = body.get("table")
                if table is not None and table not in SHAPES:
                    fail("REJECT_RETENTION_TABLE")
                desc = {k: body[k] for k in ("height", "count", "min", "max")} if obj.kind in {"snapshot-leaf", "snapshot-node"} else None
                edge = Edge(obj.ref(), frozenset({obj.kind}), table, desc, True)
                children[obj.hash] = resolver.validate(obj, edge)
                objects[obj.hash], validators[obj.hash] = obj, resolver
            parsed = {(parent, child) for parent, links in children.items() for child in links}
            recorded = {tuple(r) for r in conn.execute("SELECT parent,child FROM sync_object_edges")}
            if parsed != recorded:
                fail("REJECT_RETENTION_EDGES")
            for parent, links in children.items():
                for digest, edge in links.items():
                    child = objects.get(digest)
                    if (child is None or child.ref() != edge.ref or child.kind not in edge.kinds or
                            child.body()["ns"] != objects[parent].body()["ns"]):
                        fail("REJECT_RETENTION_CHILD")
                    validators[parent].validate(child, edge)
                if objects[parent].kind == "index-node" and sum(int(objects[d].body()["count"]) for d in links) != int(objects[parent].body()["count"]):
                    fail("REJECT_RETENTION_COUNT")
            incoming = Counter(child for _, child in parsed)
            pins = Counter(r[3] for r in roots)
            actual = {r["hash"]: (r["incoming"], r["pins"]) for r in conn.execute("SELECT * FROM sync_gc_counts")}
            if actual != {h: (incoming[h], pins[h]) for h in objects}:
                fail("REJECT_RETENTION_COUNTS")
            for _, _, role, digest in roots:
                if digest not in objects or objects[digest].kind != ROLES[role]:
                    fail("REJECT_RETENTION_ROOT_TYPE")
            namespaces = {("current", "1"): decode_c1(conn.execute("SELECT namespace FROM sync_current WHERE id=1").fetchone()[0])}
            namespaces.update({("observation", r["id"]): decode_c1(r["namespace"])
                               for r in conn.execute("SELECT id,namespace FROM sync_observations")})
            for scope, owner, _, digest in roots:
                if scope != "explicit" and objects[digest].body()["ns"] != namespaces[scope, owner]:
                    fail("REJECT_RETENTION_NAMESPACE")
            reachable, pending = set(), [r[3] for r in roots]
            while pending:
                digest = pending.pop()
                if digest not in reachable:
                    reachable.add(digest)
                    pending.extend(children[digest])
            retained_rows = set()
            for digest in reachable:
                obj = objects[digest]
                if obj.kind == "snapshot-leaf":
                    body = obj.body()
                    context = Context(Namespace(**body["ns"]), RAW_SCHEMA)
                    retained_rows.update(row_object(context, Row.make(body["table"], r["value"]))[0] for r in body["rows"])
            row_candidates = []
            for row in conn.execute("SELECT * FROM sync_rows"):
                raw = row["body"]
                body = decode_c1(raw)
                if set(body) != {"ns", "raw_schema", "table", "key", "value"} or body["raw_schema"] != RAW_SCHEMA:
                    fail("REJECT_RETENTION_ROW")
                expected, encoded = row_object(Context(Namespace(**body["ns"]), RAW_SCHEMA), Row.make(body["table"], body["value"]))
                if row["hash"] != expected or raw != encoded:
                    fail("REJECT_RETENTION_ROW")
                if row["hash"] not in retained_rows:
                    row_candidates.append((row["hash"], len(raw)))
            candidates = tuple(sorted((h, len(o.raw)) for h, o in objects.items() if h not in reachable))
            if fault:
                fault("marked", conn)
        return Mark(self.owner, fence, frozenset(reachable), candidates, tuple(sorted(row_candidates)),
                    len(roots), len(objects), len(parsed), total, (perf_counter()-started)*1000)

    def sweep(self, mark, *, batch=128, seconds=1.0, fault=None):
        """Atomic bounded batch; caller cannot submit an arbitrary hash list."""
        if (not isinstance(mark, Mark) or mark.owner is not self.owner or type(batch) is not int or
                not 1 <= batch <= 1024 or not 0 < seconds <= 5):
            fail("REJECT_GC_PLAN")
        self.repo.sandbox.assert_owned()
        allowed, row_allowed = dict(mark.candidates), dict(mark.row_candidates)
        deleted = rows_deleted = reclaimed = 0
        started = perf_counter()
        with self.repo.sandbox.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            locked = perf_counter()
            if conn.execute("SELECT serial FROM sync_gc_fence WHERE id=1").fetchone()[0] != mark.fence:
                fail("REJECT_GC_STALE_MARK")
            # Bounded terminal admission inside the deletion consistency
            # boundary, also catches schema/current coverage corruption.
            conn._validate_capture_schema()
            accepted_generation(conn)
            with conn._metadata():
                prune_views(conn)
                while deleted+rows_deleted < batch and perf_counter()-locked < seconds:
                    zero = conn.execute("SELECT hash FROM sync_gc_counts WHERE incoming=0 AND pins=0 ORDER BY hash LIMIT 1").fetchone()
                    if zero is None:
                        break
                    digest = zero[0]
                    if digest not in allowed:
                        fail("REJECT_GC_REACHABLE_CANDIDATE")
                    conn.execute("DELETE FROM sync_object_edges WHERE parent=?", (digest,))
                    conn.execute("DELETE FROM sync_objects WHERE hash=?", (digest,))
                    reclaimed += allowed[digest]
                    deleted += 1
                    if fault:
                        fault("deleted", conn)
                for digest, size in row_allowed.items():
                    if deleted+rows_deleted >= batch or perf_counter()-locked >= seconds:
                        break
                    conn.execute("DELETE FROM sync_rows WHERE hash=?", (digest,))
                    reclaimed += size
                    rows_deleted += 1
                    if fault:
                        fault("row_deleted", conn)
            if not deleted and not rows_deleted and (allowed or row_allowed):
                fail("REJECT_GC_NO_PROGRESS")
            if fault:
                fault("before_commit", conn)
            conn.commit()
            lock_ms = (perf_counter()-locked)*1000
        if fault:
            fault("after_commit", None)
        # Validate ALL retained descendants after every committed batch, outside
        # the writer lock. A new publication is included in this fresh snapshot.
        following = self.mark()
        return dict(objects_deleted=deleted, rows_deleted=rows_deleted, logical_bytes_reclaimed=reclaimed,
                    lock_ms=lock_ms, sweep_ms=(perf_counter()-started)*1000), following

    def collect(self, *, apply=False, batch=128, max_batches=16, fault=None):
        if type(apply) is not bool or type(max_batches) is not int or not 1 <= max_batches <= 1024:
            fail("REJECT_GC_LIMIT")
        lifecycle = self.repo.maintain(limit=128, fault=fault) if apply else {}
        mark = self.mark(fault=fault)
        initial = mark
        batches = []
        if apply:
            for _ in range(max_batches):
                if not mark.candidates and not mark.row_candidates:
                    break
                result, mark = self.sweep(mark, batch=batch, fault=fault)
                batches.append(result)
        return dict(mode="synthetic_apply" if apply else "dry_run", root_count=mark.roots,
                    visited_objects=mark.objects, traversed_edges=mark.edges, reachable_objects=len(mark.reachable),
                    initial_candidates=len(initial.candidates), remaining_candidates=len(mark.candidates),
                    candidate_bytes=sum(v for _, v in mark.candidates), mark_ms=initial.mark_ms,
                    objects_deleted=sum(r["objects_deleted"] for r in batches),
                    rows_deleted=sum(r["rows_deleted"] for r in batches),
                    logical_bytes_reclaimed=sum(r["logical_bytes_reclaimed"] for r in batches),
                    batches=batches, lifecycle=lifecycle)

    def protect(self, protection_id, roots):
        """Trusted explicit obligation, not download authority. No default pins."""
        uuid(protection_id)
        if type(roots) is not dict or not roots or set(roots)-set(ROLES):
            fail("REJECT_RETENTION_ROOTS")
        with self.repo.sandbox.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn._metadata():
                for role, ref in roots.items():
                    row = conn.execute("SELECT kind,body FROM sync_objects WHERE hash=?", (ref["hash"],)).fetchone()
                    if row is None:
                        fail("REJECT_RETENTION_ROOTS")
                    obj = Object(row["kind"], row["body"])
                    if obj.ref() != ref or obj.kind != ROLES[role]:
                        fail("REJECT_RETENTION_ROOTS")
                    prior = conn.execute("SELECT hash FROM sync_retention_roots WHERE scope='explicit' AND owner=? AND role=?", (protection_id, role)).fetchone()
                    if prior and prior[0] != obj.hash:
                        fail("REJECT_RETENTION_ROOTS")
                    conn.execute("INSERT OR IGNORE INTO sync_retention_roots VALUES ('explicit',?,?,?)", (protection_id, role, obj.hash))

    def unprotect(self, protection_id):
        uuid(protection_id)
        with self.repo.sandbox.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            with conn._metadata():
                conn.execute("DELETE FROM sync_retention_roots WHERE scope='explicit' AND owner=?", (protection_id,))

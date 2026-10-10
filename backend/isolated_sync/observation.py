"""Isolated T6.6C observation repository. NO HTTP/transfer/GC authorization API.

Only self-owned ObservationSandbox databases are accepted. An original selected
BundleCredential plus a live caller ticket guard is mandatory. SQL auth checks
never touch last_seen_at. This is not authentication of a remote server and no
content hash is an access credential.
"""

from calendar import monthrange
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
import hashlib
from pathlib import Path
import sqlite3
from time import perf_counter
from types import MappingProxyType
from uuid import UUID, uuid4

from app.authoritative_schemas import AuthoritativeProjections
from app.money import validate_money_payload
from app.repositories.cash_flows import list_cash_flows
from app.repositories.entries import list_entries, list_confirmed_planned_entries, list_recent_closed_month_expense_counts
from app.repositories.panels import list_panels
from app.repositories.settings import list_settings
from app.services.authoritative_state import BundleCredential, EvaluationContext, _present_entries, _present_panels, _complete_rows
from app.schemas import CashFlow
from app.services.card_charge import default_discount_policy
from app.services.card_charge.registry import card_charge_policy_manifest
from app.services.card_charge.profiles import transit_discount_profile_status
from app.services.card_payments import current_payment_status, discount_month_status
from app.services.financial_relationships import card_ownership_read_view
from app.services.judgment import app_judgment
from app.services.month import month_close_status
from app.services.summary import _summary_values_from_read_view
from isolated_sync.canonical import CanonicalError, HASH, Object, decode_c1, encode
from isolated_sync.finalization import RAW_SCHEMA, generation
from isolated_sync.inputs import MaintainedInputs, input_index
from isolated_sync.observation_schema import ObservationSandbox, validate_schema
from isolated_sync.raw import TABLES, SHAPES, SENSITIVE
from isolated_sync.roots import sync_root


class ObservationError(ValueError):
    def __init__(self, code, action="blocked"):
        self.code, self.action = code, action
        super().__init__(code)  # Never include credentials, rows or SQL values.


def reject(code, action="blocked"):
    raise ObservationError(code, action)


def utc_now():
    return datetime.now(timezone.utc)


def timestamp(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        reject("INVALID_CLOCK")
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def uuid(value):
    try:
        parsed = UUID(value)
        if parsed.version == 4 and str(parsed) == value:
            return value
    except (ValueError, TypeError, AttributeError):
        pass
    reject("INVALID_REQUEST")


@lru_cache(maxsize=1)
def engine_artifact():
    """Exact isolated release artifact, code hashes not DB/fingerprint hashes.

    Fixed application-source build input, frozen per interpreter. Not a promise
    of compatibility with a production release. D3b rollout must ship/review
    these artifact bytes with its client compatibility allow-list.
    """
    root = Path(__file__).resolve().parents[1]
    files = sorted((root / "app").rglob("*.py")) + sorted((root / "isolated_sync").glob("*.py")) + sorted((root / "app/services/judgment/messages").glob("*.yaml"))
    return encode({"profile": "isolated-d3a/1", "sources": {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}})


def versions():
    return dict(sync=1, canon=1, structural=1, raw_schema=RAW_SCHEMA, snapshot=7, recurring_ownership=1,
                projection_schema=hashlib.sha256(encode(AuthoritativeProjections.model_json_schema())).hexdigest(),
                policy_registry=hashlib.sha256(encode(card_charge_policy_manifest())).hexdigest())


@dataclass(frozen=True)
class Evaluation:
    today: date
    offset: int
    engine: str = field(default_factory=lambda: hashlib.sha256(engine_artifact()).hexdigest())

    def wire(self):
        if type(self.today) is not date or type(self.offset) is not int or not -1439 <= self.offset <= 1439 or type(self.engine) is not str or not HASH.fullmatch(self.engine):
            reject("INVALID_EVALUATION_CONTEXT")
        return dict(evaluation_date=self.today.isoformat(), timezone_offset_minutes=self.offset, financial_engine=self.engine)


def current_evaluation():
    from app.config import get_settings
    from app.services.clock import app_today
    return Evaluation(app_today(), get_settings().timezone_offset_minutes)


@dataclass(frozen=True)
class Limits:
    lease_seconds: int = 900
    observations_per_principal: int = 4
    total_records: int = 4096
    metadata_bytes: int = 8 * 1024 * 1024
    total_metadata_bytes: int = 64 * 1024 * 1024
    transaction_seconds: float = 10.0
    lock_wait_ms: int = 1000

    def __post_init__(self):
        if (type(self.lease_seconds) is not int or not 1 <= self.lease_seconds <= 900 or
                type(self.observations_per_principal) is not int or not 1 <= self.observations_per_principal <= 4 or
                type(self.total_records) is not int or self.total_records < self.observations_per_principal or
                type(self.metadata_bytes) is not int or self.metadata_bytes < 1024 or
                type(self.total_metadata_bytes) is not int or not 1024 <= self.total_metadata_bytes <= (1 << 40) or
                not 0 < self.transaction_seconds <= 60 or type(self.lock_wait_ms) is not int or not 1 <= self.lock_wait_ms <= 5000):
            reject("INVALID_LIMITS")


class ObservationInputs(MaintainedInputs):
    """A NEW read-only lifetime, not a reused D2b writer ticket/provider."""
    def __init__(self, conn, accepted):
        self.conn = conn
        self.base, self.context, self.store, self.trees, _ = accepted
        self.proof = input_index(conn, self.store, self.base["tx_id"])
        self.relationship_rows = 0
        self.active = False
        self.changes = conn.total_changes

    def _check(self):
        if (not self.active or not self.conn.in_transaction or self.conn.total_changes != self.changes or
                self.conn.execute("PRAGMA query_only").fetchone()[0] != 1):
            reject("INVALID_READ_SCOPE")

    def net(self):
        self._check()
        return []  # Committed accepted state, no writer overlay/capture reads.

    def execute(self, sql, parameters=()):
        self._check()
        command = sql.lstrip().upper()
        if not (command.startswith("SELECT") or command.startswith("SAVEPOINT CARD_READ_") or
                command.startswith("RELEASE CARD_READ_") or command in ("PRAGMA QUERY_ONLY=ON", "PRAGMA QUERY_ONLY=1",
                    "PRAGMA QUERY_ONLY", "PRAGMA SCHEMA_VERSION", "PRAGMA TEMP.SCHEMA_VERSION")):
            reject("INVALID_READ_SCOPE")
        return self.conn.execute(sql, parameters)


@contextmanager
def financial_scope(conn, accepted):
    if not conn.in_transaction or conn.execute("SELECT 1 FROM sync_tx_context").fetchone():
        reject("INVALID_READ_SCOPE")
    scope = ObservationInputs(conn, accepted)
    name = "observation_read_" + uuid4().hex
    conn.execute(f"SAVEPOINT {name}")
    prior = conn.execute("PRAGMA query_only").fetchone()[0]
    conn.execute("PRAGMA query_only=ON")
    scope.active = True
    try:
        yield scope
        scope._check()
        conn.execute(f"RELEASE {name}")  # Detect transaction rollback/BEGIN ABA.
    finally:
        scope.active = False
        conn.execute(f"PRAGMA query_only={prior}")


def hot_projections(scope, evaluation):
    """Existing authoritative presenters, same shapes as B-1, no Snapshot scan."""
    today, month = evaluation.today, evaluation.today.strftime("%Y-%m")
    settings = MappingProxyType(dict(list_settings(conn=scope)))
    ctx = EvaluationContext(today, month, evaluation.offset, settings)
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    recent = date(today.year-1, 12, 1) if today.month == 1 else date(today.year, today.month-1, 1)
    with card_ownership_read_view(scope) as view:
        entries = list_entries("current", today=today, conn=view)
        panels = list_panels(month, include_confirmed_fixed=True, conn=view)
        summary = _summary_values_from_read_view(view, today=today, visible_current_entries=entries)
        payment = current_payment_status(today, conn=view)
        state = dict(
            month_close_status=month_close_status(today, conn=view, timezone_offset_minutes=evaluation.offset),
            entries=_present_entries(entries, view, ctx), panels=_present_panels(panels, view, ctx),
            summary=summary, card_payment_status=payment,
            judgment=app_judgment(entries, list_panels(month, conn=view), list_cash_flows(start, end, conn=view),
                                  summary, payment, settings, list_recent_closed_month_expense_counts(conn=view), today=today),
            confirmed_planned_entries=_present_entries(list_confirmed_planned_entries(today, conn=view), view, ctx),
            cash_flows=_complete_rows(list_cash_flows(recent, end, conn=view), CashFlow),
            settings={k: v for k, v in settings.items() if k not in SENSITIVE},
            owner_discount_month=discount_month_status(month, "owner", conn=view),
            family_discount_month=discount_month_status(month, "family", conn=view),
            transit_discount_profile=transit_discount_profile_status(month, conn=view))
    for key in ("entries", "panels", "confirmed_planned_entries", "cash_flows"):
        state[key] = [r.model_dump(mode="json") for r in state[key]]
    validate_money_payload(state)
    result = AuthoritativeProjections.model_validate(state).model_dump(mode="json")
    validate_money_payload(result)
    return result


def accepted_generation(conn):
    """Current COMPLETE certificate, bounded root/descriptor validation only.

    Provenance is D2b strict bootstrap + protected atomic updates, NOT a full
    arbitrary-bitrot scrub. Descendant verification belongs to read/transfer.
    Must run on this repository's fresh locked connection, never a writer alias.
    """
    if conn.execute("SELECT 1 FROM sync_tx_context").fetchone():
        reject("ROOT_NOT_READY", "retry_same")
    accepted = generation(conn)
    current, context, store, trees, index = accepted
    cert = conn.execute("SELECT * FROM sync_commits WHERE tx_id=?", (current["tx_id"],)).fetchone()
    revision = conn.execute("SELECT revision,typeof(revision) FROM authoritative_state_revision WHERE id=1").fetchone()
    if (cert is None or cert["status"] != "complete" or revision is None or revision[1] != "integer" or
            revision[0] != current["revision"] or current["revision"] < 0 or
            cert["target_revision"]-cert["base_revision"] != cert["change_count"]):
        reject("ROOT_NOT_READY", "retry_same")
    if cert["base_epoch"] == cert["target_epoch"]:
        capture = conn.execute("SELECT * FROM sync_capture_commits WHERE tx_id=?", (current["tx_id"],)).fetchone()
        # Bootstrap is allowed at R=R without a capture-only certificate.
        if (capture is None and cert["change_count"] != 0) or (capture and any(
                capture[k] != cert[k] for k in ("base_revision", "target_revision", "change_count"))):
            reject("ROOT_NOT_READY", "retry_same")
    for name, tree in trees.items():
        desc = tree.root.descriptor()
        obj = store.get(desc["ref"], {"snapshot-leaf", "snapshot-node"})
        body = obj.body()
        if (body.get("table") != name or any(body.get(k) != desc[k] for k in ("height", "count", "min", "max"))):
            reject("REQUIRED_METADATA_INVALID")
    proof = input_index(conn, store, current["tx_id"])
    return accepted, proof.object().ref(), index.object().ref()


class ObservationRepository:
    """D3a metadata only. No arbitrary DB path, object downloads or GC methods.

    Every public operation opens/closes its own connection and short transaction.
    Exceptions are explicit classifications; callers decide bounded retry. There
    is no hidden retry/sleep/reselection of a different credential or target.
    """
    def __init__(self, sandbox, *, evaluation=current_evaluation, clock=utc_now, limits=Limits()):
        if not isinstance(sandbox, ObservationSandbox):
            reject("INVALID_REPOSITORY")
        self.sandbox, self.evaluation, self.clock, self.limits = sandbox, evaluation, clock, limits
        self.metrics = {}

    @contextmanager
    def _connection(self):
        conn = self.sandbox.connect()
        try:
            with conn:
                with conn._metadata():
                    conn.execute(f"PRAGMA busy_timeout={self.limits.lock_wait_ms}")
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("SAVEPOINT observation_attempt")
                retired = set()
                try:
                    yield conn, retired
                except BaseException:
                    if retired and conn.in_transaction:
                        # Keep the same writer lock. Discard ALL candidate/auth/
                        # object/pin/budget writes, then persist ONLY established
                        # terminal lease decisions before returning the error.
                        conn.execute("ROLLBACK TO observation_attempt")
                        conn.execute("RELEASE observation_attempt")
                        with conn._metadata():
                            conn.executemany("UPDATE sync_observations SET status='retired' WHERE id=? AND status='available'",
                                             ((key,) for key in sorted(retired)))
                        conn.commit()
                    raise
        finally:
            # sqlite3.Connection.__exit__ commits/rolls back, but does NOT
            # close the handle. No repository handle survives a public call.
            conn.close()

    def _guard(self, conn, credential, guard):
        if (not isinstance(credential, BundleCredential) or type(credential.user_id) is not int or credential.user_id <= 0 or
                type(credential.token_hash) is not str or not HASH.fullmatch(credential.token_hash) or
                not callable(guard) or guard() != credential):
            reject("PRINCIPAL_OR_SESSION_CHANGED", "reauthenticate")
        row = conn.execute("""SELECT s.user_id,s.expires_at,u.is_active FROM auth_sessions s
            JOIN users u ON u.id=s.user_id WHERE s.session_token_hash=?""", (credential.token_hash,)).fetchone()
        now = self.clock()  # AFTER lock/SQL wait, never a pre-lock cached time.
        timestamp(now)
        try:
            expiry = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00")) if row else None
            valid = expiry is not None and expiry.tzinfo is not None and expiry > now
        except (ValueError, TypeError, AttributeError):
            valid = False
        if row is None or row["user_id"] != credential.user_id or not row["is_active"] or not valid:
            reject("AUTH_REQUIRED", "reauthenticate")
        return now

    def _retire_expired(self, conn, retired, credential, namespace, now, observation_id=None):
        """Indexed, monotonic authorization retirement; NEVER release pins.

        Record decisions for error-path replay after rolling back the attempt.
        Namespace/owner were authenticated under this same BEGIN IMMEDIATE.
        """
        sql = """UPDATE sync_observations SET status='retired'
            WHERE principal_id=? AND status='available' AND expires_at<=? AND namespace=?"""
        parameters = (credential.user_id, timestamp(now), namespace)
        if observation_id is not None:
            sql += " AND id=?"
            parameters += (observation_id,)
        with conn._metadata():
            rows = conn.execute(sql+" RETURNING id", parameters).fetchall()
        retired.update(row[0] for row in rows)

    def _check_lease(self, conn, retired, row, credential, now):
        if row["status"] != "available":
            reject("OBSERVATION_EXPIRED", "new_observation")
        if row["expires_at"] <= timestamp(now):
            self._retire_expired(conn, retired, credential, row["namespace"], now, row["id"])
            reject("OBSERVATION_EXPIRED", "new_observation")

    def _target_base(self, base, target):
        if base is None:
            return "initial"
        if type(base) is not dict or "sync_root" not in base:
            reject("BASE_INVALID", "full_resync")
        try:
            candidate = {k: v for k, v in base.items() if k != "sync_root"}
            valid = sync_root(candidate) == base["sync_root"]
        except (CanonicalError, TypeError, KeyError):
            valid = False
        if not valid or base["principal_id"] != target["principal_id"]:
            reject("BASE_INVALID", "full_resync")
        if base["ns"] != target["ns"]:
            reject("EPOCH_CHANGED", "full_resync")
        if base["versions"] != target["versions"]:
            reject("UNSUPPORTED_CONTRACT")
        if int(base["revision"]) > int(target["revision"]) or (base["revision"] == target["revision"] and
                any(base[k] != target[k] for k in ("raw_ref", "index_ref"))):
            reject("BASE_INVALID", "full_resync")
        if any(base[k] != target[k] for k in ("revision", "raw_ref", "index_ref")):
            return "raw"
        return "unchanged" if base == target else "context"

    def _view_object(self, conn, ref, kind, ns):
        row = conn.execute("SELECT kind,body FROM sync_objects WHERE hash=?", (ref["hash"],)).fetchone()
        if row is None:
            reject("OBSERVATION_INCOMPLETE", "new_observation")
        obj = Object(row["kind"], row["body"])
        if obj.kind != kind or obj.ref() != ref or obj.body().get("ns") != ns:
            reject("REQUIRED_METADATA_INVALID")
        return obj

    def _put_view(self, conn, obj):
        row = conn.execute("SELECT kind,body FROM sync_objects WHERE hash=?", (obj.hash,)).fetchone()
        if row and tuple(row) != (obj.kind, obj.raw):
            reject("REQUIRED_METADATA_INVALID")
        if not row:
            conn.execute("INSERT INTO sync_objects VALUES (?,?,?)", (obj.hash, obj.kind, obj.raw))
        # hot/control contain no typed child object refs (§9). No fake raw_schema
        # field or invented edge is added to bypass D2b Store context admission.

    def create(self, credential, *, request_id, guard, base=None, protocol=1, inline_bytes=0, fault=None):
        uuid(request_id)
        if type(protocol) is not int or protocol != 1:
            reject("UNSUPPORTED_CONTRACT")
        if type(inline_bytes) is not int or not 0 <= inline_bytes <= 1048576:
            reject("INVALID_REQUEST")
        request = encode(dict(protocol=protocol, request_id=request_id, base=base, inline_bytes=inline_bytes))
        if len(request) > self.limits.metadata_bytes:
            reject("TRANSFER_BUDGET", "retry_same")
        started = perf_counter()
        self.metrics = {}
        try:
            with self._connection() as (conn, retired):
                validate_schema(conn)
                now = self._guard(conn, credential, guard)
                evaluation, contracts = self.evaluation(), versions()
                context = evaluation.wire()
                if evaluation.engine != hashlib.sha256(engine_artifact()).hexdigest():
                    reject("UNSUPPORTED_CONTRACT")
                if fault:
                    fault("validation", conn)
                old = conn.execute("SELECT id,request_body FROM sync_observations WHERE credential_hash=? AND request_id=?",
                                   (credential.token_hash, request_id)).fetchone()
                if old:
                    if old["request_body"] != request:
                        reject("REQUEST_CONFLICT")
                    return self._lookup(conn, retired, old["id"], credential, guard)
                accepted, proof_ref, index_ref = accepted_generation(conn)
                current, raw_context, store, _, _ = accepted
                self.metrics["validation_ms"] = (perf_counter()-started)*1000
                mark = perf_counter()
                ns = raw_context.ns.wire()
                # Dynamic evaluation/registry checks below prevent cross-view reuse.
                with financial_scope(conn, accepted) as scope:
                    state = hot_projections(scope, evaluation)
                    horizon = scope.policy_horizon(evaluation.today.strftime("%Y-%m"))
                    self.metrics["relationship_rows"] = scope.relationship_rows
                self.metrics["financial_ms"] = (perf_counter()-mark)*1000
                hot = Object.make(dict(kind="hot", ns=ns, canon=1, projection_schema=contracts["projection_schema"], context=context, state=state))
                identity = encode(dict(ns=ns, revision=str(current["revision"]), versions=contracts, context=context, hot_ref=hot.ref()))
                view = conn.execute("SELECT hot_hash,control_hash FROM sync_observation_views WHERE identity=?", (identity,)).fetchone()
                if view:
                    size = conn.execute("SELECT length(body) FROM sync_objects WHERE hash=?", (view["control_hash"],)).fetchone()
                    if size is None or view["hot_hash"] != hot.hash:
                        reject("REQUIRED_METADATA_INVALID")
                    control = self._view_object(conn, dict(hash=view["control_hash"], bytes=str(size[0])), "control", ns)
                else:
                    control = Object.make(dict(kind="control", ns=ns, canon=1, snapshot_schema=7, recurring_ownership_version=1,
                                               exported_at=timestamp(now), range={"scope": "all"}, card_charge_policy=card_charge_policy_manifest(horizon),
                                               columns={t: sorted(SHAPES[t]) for t in TABLES},
                                               discount_policy_defaults={s: default_discount_policy(s) for s in ("owner", "family")}))
                raw_ref = store.get({"hash": current["raw_hash"], "bytes": str(conn.execute(
                    "SELECT length(body) FROM sync_objects WHERE hash=?", (current["raw_hash"],)).fetchone()[0])}, {"raw-root"}).ref()
                target = dict(ns=ns, principal_id=credential.user_id, versions=contracts, revision=str(current["revision"]), context=context,
                              raw_ref=raw_ref, index_ref=index_ref, hot_ref=hot.ref(), control_ref=control.ref())
                target["sync_root"] = sync_root(target)
                kind = self._target_base(base, target)
                if fault:
                    fault("roots", conn)
                terminal = self._guard(conn, credential, guard)
                if self.evaluation() != evaluation or versions() != contracts:
                    reject("OBSERVATION_CONFLICT", "new_observation")
                latest = conn.execute("SELECT tx_id,namespace,revision,raw_hash,index_hash FROM sync_current WHERE id=1").fetchone()
                if any(latest[k] != current[k] for k in latest.keys()):
                    reject("OBSERVATION_CONFLICT", "new_observation")
                if perf_counter()-started > self.limits.transaction_seconds:
                    reject("ROOT_NOT_READY", "retry_same")
                self._retire_expired(conn, retired, credential, encode(ns), terminal)
                quota = conn.execute("SELECT count(*) FROM sync_observations WHERE principal_id=? AND status='available'",
                                     (credential.user_id,)).fetchone()[0]
                if quota >= self.limits.observations_per_principal or conn.execute("SELECT count(*) FROM sync_observations").fetchone()[0] >= self.limits.total_records:
                    reject("LEASE_LIMIT", "retry_same")
                observation_id = str(uuid4())
                response = dict(protocol=1, request_id=request_id, status="available", observation_id=observation_id,
                                validated_at=timestamp(terminal), expires_at=timestamp(terminal+timedelta(seconds=self.limits.lease_seconds)),
                                base_sync_root=base["sync_root"] if base else None, change_kind=kind, target=target, inline_objects=[])
                payload, target_bytes = encode(response), encode(target)
                if len(payload)+len(request)+len(hot.raw)+len(control.raw) > self.limits.metadata_bytes:
                    reject("TRANSFER_BUDGET", "retry_same")
                # Monotonic logical-byte accounting, O(1), not SUM(all historical
                # objects). Includes conservative pin/record framing allowance.
                charge = len(payload)+len(request)+len(target_bytes)+len(identity)+1024
                for obj in (hot, control):
                    if conn.execute("SELECT 1 FROM sync_objects WHERE hash=?", (obj.hash,)).fetchone() is None:
                        charge += len(obj.raw)
                used = conn.execute("SELECT used_bytes FROM sync_observation_budget WHERE id=1").fetchone()[0]
                if used+charge > self.limits.total_metadata_bytes:
                    reject("LEASE_LIMIT", "retry_same")
                mark = perf_counter()
                with conn._metadata():
                    self._put_view(conn, hot)
                    self._put_view(conn, control)
                    if not view:
                        conn.execute("INSERT INTO sync_observation_views VALUES (?,?,?)", (identity, hot.hash, control.hash))
                    conn.execute("INSERT INTO sync_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'available')",
                                 (observation_id, request_id, credential.token_hash, credential.user_id, encode(ns), request, target_bytes, payload,
                                  current["tx_id"], proof_ref["hash"], response["validated_at"], response["expires_at"]))
                    for role, ref in (("raw", raw_ref), ("index", index_ref), ("hot", hot.ref()), ("control", control.ref()), ("input", proof_ref)):
                        conn.execute("INSERT INTO sync_observation_pins VALUES (?,?,?,1)", (observation_id, role, ref["hash"]))
                        if fault:
                            fault("pin_"+role, conn)
                    conn.execute("UPDATE sync_observation_budget SET used_bytes=used_bytes+? WHERE id=1", (charge,))
                if fault:
                    fault("before_commit", conn)
                # Last guard AFTER all potentially blocking work, before COMMIT.
                final_time = self._guard(conn, credential, guard)
                if (self.evaluation() != evaluation or versions() != contracts or timestamp(final_time) >= response["expires_at"] or
                        perf_counter()-started > self.limits.transaction_seconds):
                    reject("OBSERVATION_CONFLICT", "new_observation")
                self.metrics["pin_ms"] = (perf_counter()-mark)*1000
                mark = perf_counter()
                conn.commit()
                self.metrics.update(commit_ms=(perf_counter()-mark)*1000, total_ms=(perf_counter()-started)*1000,
                                    root_count=5, object_reads=store.reads, metadata_bytes=len(payload)+len(request)+len(target_bytes),
                                    hot_bytes=len(hot.raw), control_bytes=len(control.raw))
                if fault:
                    fault("after_commit", conn)
                return response
        except sqlite3.OperationalError as error:
            if "locked" in str(error) or "busy" in str(error):
                reject("ROOT_NOT_READY", "retry_same")
            reject("PIN_TRANSACTION_FAILED")
        except CanonicalError:
            reject("REQUIRED_METADATA_INVALID")

    def _lookup(self, conn, retired, observation_id, credential, guard):
        now = self._guard(conn, credential, guard)
        row = conn.execute("SELECT * FROM sync_observations WHERE id=?", (observation_id,)).fetchone()
        if row is None:
            reject("OBSERVATION_INCOMPLETE", "new_observation")
        if row["credential_hash"] != credential.token_hash or row["principal_id"] != credential.user_id:
            reject("PRINCIPAL_OR_SESSION_CHANGED", "reauthenticate")
        namespace = conn.execute("SELECT namespace FROM sync_current WHERE id=1").fetchone()
        if namespace is None or namespace[0] != row["namespace"]:
            reject("EPOCH_CHANGED", "full_resync")
        self._check_lease(conn, retired, row, credential, now)
        response, target = decode_c1(row["response"]), decode_c1(row["target"])
        if type(target) is not dict or "sync_root" not in target:
            reject("REQUIRED_METADATA_INVALID")
        derived_root = sync_root({k: v for k, v in target.items() if k != "sync_root"})
        if (type(response) is not dict or set(response) != {"protocol", "request_id", "status", "observation_id", "validated_at", "expires_at", "base_sync_root", "change_kind", "target", "inline_objects"} or
                response["protocol"] != 1 or response["observation_id"] != row["id"] or response["request_id"] != row["request_id"] or
                response["status"] != "available" or response["validated_at"] != row["validated_at"] or response["expires_at"] != row["expires_at"] or
                target["principal_id"] != row["principal_id"] or response["target"] != target or
                target["sync_root"] != derived_root or
                target["versions"] != versions() or target["ns"] != decode_c1(row["namespace"]) or
                target["context"]["financial_engine"] != hashlib.sha256(engine_artifact()).hexdigest()):
            reject("REQUIRED_METADATA_INVALID")
        cert = conn.execute("SELECT * FROM sync_commits WHERE tx_id=?", (row["tx_id"],)).fetchone()
        if cert is None or cert["status"] != "complete" or any(cert[k] != expected for k, expected in (
                ("raw_hash", target["raw_ref"]["hash"]), ("index_hash", target["index_ref"]["hash"]),
                ("target_revision", int(target["revision"])), ("target_epoch", target["ns"]["epoch"]), ("input_hash", row["input_hash"]))):
            reject("REQUIRED_METADATA_INVALID")
        pins = {r["role"]: r["hash"] for r in conn.execute("SELECT * FROM sync_observation_pins WHERE observation_id=? AND active=1", (observation_id,))}
        expected = {k: target[k+"_ref"]["hash"] for k in ("raw", "index", "hot", "control")}
        expected["input"] = row["input_hash"]
        if pins != expected:
            reject("OBSERVATION_INCOMPLETE", "new_observation")
        for kind in ("hot", "control"):
            obj = self._view_object(conn, target[kind+"_ref"], kind, target["ns"])
            if kind == "hot" and (obj.body().get("context") != target["context"] or obj.body().get("projection_schema") != target["versions"]["projection_schema"]):
                reject("REQUIRED_METADATA_INVALID")
        from isolated_sync.canonical import Context, Namespace
        from isolated_sync.store import Store
        store = Store(conn, Context(Namespace(**target["ns"]), target["versions"]["raw_schema"]))
        store.get(target["raw_ref"], {"raw-root"})
        store.index(target["index_ref"])
        input_index(conn, store, row["tx_id"])
        terminal = self._guard(conn, credential, guard)
        self._check_lease(conn, retired, row, credential, terminal)
        return response

    def lookup(self, observation_id, credential, *, guard):
        uuid(observation_id)
        try:
            with self._connection() as (conn, retired):
                return self._lookup(conn, retired, observation_id, credential, guard)
        except CanonicalError:
            reject("REQUIRED_METADATA_INVALID")
        except sqlite3.OperationalError:
            reject("ROOT_NOT_READY", "retry_same")

    def roots(self, observation_id, credential, *, guard):
        """Typed TRANSFER root refs only. Not descendants/bytes authorization.

        D3b MUST validate a requested typed parent-child path, budget and fresh
        credentials separately. The private local input proof is never exposed.
        """
        target = self.lookup(observation_id, credential, guard=guard)["target"]
        return {kind: target[kind+"_ref"] for kind in ("raw", "index", "hot", "control")}

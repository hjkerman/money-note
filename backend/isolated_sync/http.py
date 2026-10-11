"""Explicitly constructed synthetic-only T6.6D3b ASGI app.

Never imported/registered by app.main. Reuses real cookie/Bearer selection and
token hashing; reads the SAME users/auth_sessions model from the owned sandbox,
not app.db.session (which would select a configured normal runtime database).
There is no login, generic file/artifact/hash endpoint, release or GC API.
"""

from dataclasses import dataclass, field
import asyncio
import sqlite3
from threading import Event, BoundedSemaphore
from time import perf_counter

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response

from app import auth
from app.services.authoritative_state import BundleCredential
from isolated_sync.artifacts import ArtifactContract
from isolated_sync.canonical import CanonicalError, decode_json, encode
from isolated_sync.observation import ObservationError, ObservationRepository, reject, uuid
from isolated_sync.observation_schema import ObservationSandbox
from isolated_sync.transfer import TransferLimits, TransferRepository, fields, object_request


@dataclass
class RequestTicket:
    """One selected original credential + request identity + live cancellation.

    Not a new login generation or wire credential. A replaced/revoked real
    auth_sessions token is revalidated by D3a at every terminal guard.
    """
    credential: BundleCredential
    request_id: str
    observation_id: str | None = None
    cancelled: Event = field(default_factory=Event)

    def guard(self):
        return None if self.cancelled.is_set() else self.credential


STATUS = {
    "AUTH_REQUIRED": 401, "PRINCIPAL_OR_SESSION_CHANGED": 403,
    "EPOCH_CHANGED": 409, "BASE_INVALID": 409, "REQUEST_CONFLICT": 409, "OBSERVATION_CONFLICT": 409,
    "OBSERVATION_EXPIRED": 410, "OBSERVATION_INCOMPLETE": 410,
    "UNSUPPORTED_CONTRACT": 422, "INVALID_REQUEST": 422,
    "TRANSFER_BUDGET": 413, "LEASE_LIMIT": 429, "ROOT_NOT_READY": 503,
}
HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


def error_response(error, request_id=None):
    status = STATUS.get(error.code, 500)
    retry = 100 if error.action == "retry_same" else None
    # Internal exception classes, SQL and values never enter the public body.
    code = error.code if status != 500 else "STORAGE_FAILED"
    raw = encode(dict(protocol=1, request_id=request_id, error=dict(code=code, action=error.action,
                 retry_after_ms=retry, current_ns=None)))
    return Response(raw, status_code=status, media_type="application/json", headers=HEADERS)


class Adapter:
    def __init__(self, repository, limits, *, origins=(), fault=None, metrics=None):
        if not isinstance(repository, ObservationRepository) or not isinstance(repository.sandbox, ObservationSandbox):
            reject("INVALID_SANDBOX")
        self.repo, self.limits = repository, limits
        self.transfer = TransferRepository(repository, limits=limits)
        self.slots = BoundedSemaphore(limits.concurrent_requests)
        self.origins = frozenset(origins)
        if "*" in self.origins:
            reject("INVALID_LIMITS")
        self.fault, self.metrics = fault, metrics
        self.contract = ArtifactContract.current()

    def checkpoint(self, stage, ticket):
        # Explicit synthetic failure/barrier hook. Not exposed in HTTP input.
        if self.fault:
            self.fault(stage, ticket)

    async def body(self, request):
        if request.headers.get("content-encoding", "identity").lower() != "identity":
            reject("INVALID_REQUEST")
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            reject("INVALID_REQUEST")
        size = request.headers.get("content-length")
        if size is not None:
            if not size.isascii() or not size.isdecimal():
                reject("INVALID_REQUEST")
            if len(size) > 10 or int(size) > self.limits.request_bytes:
                reject("TRANSFER_BUDGET", "retry_same")
        # Protect cookie POSTs just as the normal mutation-origin middleware.
        origin = request.headers.get("origin", "").rstrip("/")
        same = str(request.base_url).rstrip("/")
        if origin and origin not in self.origins | {same}:
            reject("PRINCIPAL_OR_SESSION_CHANGED", "reauthenticate")
        data = bytearray()
        async for chunk in request.stream():
            if len(data)+len(chunk) > self.limits.request_bytes:
                reject("TRANSFER_BUDGET", "retry_same")
            data.extend(chunk)
        try:
            return decode_json(bytes(data))
        except (CanonicalError, RecursionError, ValueError):
            reject("INVALID_REQUEST")

    def credential(self, request):
        token = auth._session_token_from_request(request)
        if not token:
            reject("AUTH_REQUIRED", "reauthenticate")
        digest = auth._hash_session_token(token)
        conn = self.repo.sandbox.connect()
        try:
            # Same session/user principal resolution as app.auth; read-only, no
            # last_seen write or expired-session cleanup in this adapter.
            row = conn.execute("SELECT user_id FROM auth_sessions WHERE session_token_hash=?", (digest,)).fetchone()
            if row is None:
                reject("AUTH_REQUIRED", "reauthenticate")
            cred = BundleCredential(digest, row[0])
            self.repo._guard(conn, cred, lambda: cred)
            return cred
        finally:
            conn.close()

    def prepare(self, request, value, observation_id):
        started = perf_counter()
        credential = self.credential(request)
        auth_ms = (perf_counter()-started)*1000
        ticket = RequestTicket(credential, value["request_id"], observation_id)
        self.checkpoint("authenticated", ticket)
        if observation_id is None:
            base = value["base"]
            if base is not None:
                fields(base, ("ns", "principal_id", "versions", "revision", "context", "raw_ref", "index_ref", "hot_ref", "control_ref", "sync_root"))
                fields(base["versions"], ("sync", "canon", "structural", "raw_schema", "snapshot", "recurring_ownership", "projection_schema", "policy_registry"))
                # Unknown interpretation versions are not a damaged lineage
                # repaired by a full resync. Reject BEFORE D3a hashes Base
                # using the current C1/version contract (§4/§17).
                if encode(base["versions"]) != self.contract.versions_c1:
                    reject("UNSUPPORTED_CONTRACT")
            created = []
            # Status comes from the same serialized D3a transaction, not a
            # preflight race. The optional receipt does not alter wire content.
            result = self.repo.create(credential, guard=ticket.guard, creation_receipt=created, **value)
            self.contract.verify(result["target"])
            payload = encode(result)
            ticket.observation_id = result["observation_id"]
            status = 201 if created[0] else 200
            measurements = dict(response_bytes=len(payload))
        else:
            payload, measurements = self.transfer.acquire(observation_id, credential, guard=ticket.guard, request=value,
                                                         fault=lambda stage, conn: self.checkpoint("objects_"+stage, ticket))
            status = 200
        self.checkpoint("serialized", ticket)
        measurements["auth_ms"] = auth_ms
        return payload, status, ticket, measurements, started

    def terminal(self, ticket):
        self.checkpoint("terminal", ticket)
        # AFTER complete protected bytes are prepared, AFTER async disconnect
        # polling, AFTER any lock wait. M01/M02 are applied unchanged here.
        result = self.repo.lookup(ticket.observation_id, ticket.credential, guard=ticket.guard)
        self.contract.verify(result["target"])

    async def dispatch(self, request, observation_id=None):
        request_id, ticket = None, None
        if not self.slots.acquire(blocking=False):
            return error_response(ObservationError("ROOT_NOT_READY", "retry_same"))
        try:
            async with asyncio.timeout(self.limits.body_seconds):
                value = await self.body(request)
            if type(value) is dict:
                try:
                    request_id = uuid(value.get("request_id"))
                except ObservationError:
                    pass
            if observation_id is None:
                fields(value, ("protocol", "request_id", "base", "inline_bytes"))
                uuid(value["request_id"])
            else:
                uuid(observation_id)
                try:
                    object_request(value, self.limits)
                except CanonicalError:
                    reject("INVALID_REQUEST")
            payload, status, ticket, measurements, started = await run_in_threadpool(self.prepare, request, value, observation_id)
            response = Response(payload, status_code=status, media_type="application/json", headers=HEADERS)
            recorded = dict(measurements, prepared_ms=(perf_counter()-started)*1000, operation="manifest" if observation_id is None else "objects")
            # Even optional diagnostics/callbacks precede the terminal guard.
            if self.metrics:
                self.metrics(recorded)
            if await request.is_disconnected():
                ticket.cancelled.set()
                reject("PRINCIPAL_OR_SESSION_CHANGED", "reauthenticate")
            mark = perf_counter()
            await run_in_threadpool(self.terminal, ticket)
            # No network await/streaming occurs while a DB transaction is open.
            recorded.update(http_ms=(perf_counter()-started)*1000, terminal_http_ms=(perf_counter()-mark)*1000)
            return response
        except ObservationError as error:
            return error_response(error, request_id)
        except sqlite3.OperationalError as error:
            return error_response(ObservationError("ROOT_NOT_READY", "retry_same") if "locked" in str(error) or "busy" in str(error)
                                  else ObservationError("STORAGE_FAILED"), request_id)
        except TimeoutError:
            return error_response(ObservationError("ROOT_NOT_READY", "retry_same"), request_id)
        except (CanonicalError, RecursionError, ValueError, sqlite3.DatabaseError, RuntimeError):
            return error_response(ObservationError("STORAGE_FAILED"), request_id)
        except Exception:
            return error_response(ObservationError("STORAGE_FAILED"), request_id)
        finally:
            if ticket:
                ticket.cancelled.set()
            self.slots.release()


def create_app(repository, *, limits=TransferLimits(), origins=(), fault=None, metrics=None):
    """No startup hook, configured DB path, router registration or live socket.

    Full v1 capability selection stays explicitly unsupported (404) until R1
    can truthfully advertise large_restore:1 and its proven restore_bytes. The
    isolated observation/object endpoints exercise the exact §15 wire subset.
    DELETE/release is deliberately absent: it belongs to D3c.
    """
    adapter = Adapter(repository, limits, origins=origins, fault=fault, metrics=metrics)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/api/sync/v1/capabilities")
    async def capabilities():
        return Response(status_code=404, headers=HEADERS)

    @app.post("/api/sync/v1/observations")
    async def manifest(request: Request):
        return await adapter.dispatch(request)

    @app.post("/api/sync/v1/observations/{observation_id}/objects")
    async def objects(observation_id: str, request: Request):
        return await adapter.dispatch(request, observation_id)

    return app

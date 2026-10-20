"""기존 B02 합성 TLS 서버에 위임하는 조사 전용 계측. 제품/lease 변경 없음.

요청별 중첩 inclusive wall/thread-CPU 시간이다. 합산하여 wall 비율로 쓰지 않는다.
credential/body는 보존하지 않으며, 응답의 객체 hash/길이만 집계한다.
"""

from collections import Counter
from contextvars import ContextVar
from functools import wraps
import importlib.util
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "original_b02_synthetic_server",
    ROOT / "docs/benchmarks/t66f-b02-implementation/server.py",
)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
from isolated_sync import (  # noqa: E402
    http,
    observation,
    retention_schema,
    finalization,
    transfer,
    workers,
)  # noqa: E402
from app import db_migrations  # noqa: E402

CURRENT = ContextVar("a01_request", default=None)


def timed(owner, name, label=None):
    original = getattr(owner, name)

    @wraps(original)
    def call(*args, **kwargs):
        record = CURRENT.get()
        if record is None:
            return original(*args, **kwargs)
        start, cpu = time.perf_counter_ns(), time.thread_time_ns()
        try:
            return original(*args, **kwargs)
        finally:
            key = label or f"{getattr(owner, '__name__', type(owner).__name__)}.{name}"
            record["ns"][key] += time.perf_counter_ns() - start
            record["cpu_ns"][key] += time.thread_time_ns() - cpu
            record["calls"][key] += 1

    setattr(owner, name, call)


for owner, names in (
    (
        http.Adapter,
        ["credential", "prepare", "terminal", "prepare_release", "terminal_release"],
    ),
    (
        observation.ObservationRepository,
        ["_lookup", "_guard", "_check_lease", "_view_object"],
    ),
    (retention_schema.RetentionSandbox, ["connect", "_open"]),
    (retention_schema, ["validate_schema"]),
    (finalization, ["validate_schema"]),
    (
        db_migrations,
        [
            "_validate_critical_structure",
            "_expected_tables_and_columns",
            "_validate_revision_triggers",
        ],
    ),
    (transfer.PathResolver, ["resolve"]),
):
    for name in names:
        if hasattr(owner, name):
            timed(owner, name)
# finalization imported this function by value; instrument that exact call site.
timed(finalization, "_validate_current_schema", "schema.current")
# Fingerprints / C1 diagnostics are sampled inclusive operations, not byte counters.
for owner, name in [(observation, "engine_artifact"), (observation, "versions")]:
    if hasattr(owner, name):
        timed(owner, name)

original_execute = retention_schema.RetentionConnection.execute


@wraps(original_execute)
def execute(self, sql, *args, **kwargs):
    record = CURRENT.get()
    if record is None:
        return original_execute(self, sql, *args, **kwargs)
    kind = str(sql).lstrip().split(None, 1)[0].upper()
    label = "SQL." + kind
    if kind == "BEGIN":
        label = "SQL.BEGIN_IMMEDIATE"
    start = time.perf_counter_ns()
    try:
        return original_execute(self, sql, *args, **kwargs)
    finally:
        record["ns"][label] += time.perf_counter_ns() - start
        record["calls"][label] += 1
        record["connections"].add(id(self))


retention_schema.RetentionConnection.execute = execute
for name in ["commit", "rollback", "close"]:
    timed(retention_schema.RetentionConnection, name, "connection." + name)

old_acquire = workers.WorkerBudget.acquire


@wraps(old_acquire)
def acquire(self):
    record = CURRENT.get()
    start = time.perf_counter_ns()
    value = old_acquire(self)
    if record is not None:
        record["ns"]["permit.acquire"] += time.perf_counter_ns() - start
        record["calls"][
            "permit.admitted" if value is not None else "permit.rejected"
        ] += 1
        record["permit_after_acquire"] = self.snapshot()
    return value


workers.WorkerBudget.acquire = acquire
old_run = workers.WorkerLease.run


@wraps(old_run)
async def run(self, function, *args):
    record = CURRENT.get()
    start = time.perf_counter_ns()

    # Original creates/owns/releases its NativeJob. Only delegate body is wrapped.
    def native(*native_args):
        if record is not None:
            record["ns"]["executor.start_wait"] += time.perf_counter_ns() - start
        return function(*native_args)

    try:
        return await old_run(self, native, *args)
    finally:
        if record is not None:
            record["ns"]["worker.run_inclusive"] += time.perf_counter_ns() - start
            record["calls"]["worker.run"] += 1


workers.WorkerLease.run = run
old_close = workers.WorkerLease.close


@wraps(old_close)
def close(self):
    value = old_close(self)
    record = CURRENT.get()
    if record is not None:
        record["permit_after_close"] = self.budget.snapshot()
        record["calls"]["permit.close"] += 1
    return value


workers.WorkerLease.close = close

old_create_app = base.create_app


def create_app(*args, **kwargs):
    original_metrics = kwargs.get("metrics")

    def metrics(row):
        record = CURRENT.get()
        if record is not None:
            # Keep reference: Adapter later fills terminal_http_ms after final guard.
            record["implementation_metrics"] = row
        if original_metrics is not None:
            original_metrics(row)

    kwargs["metrics"] = metrics
    return old_create_app(*args, **kwargs)


base.create_app = create_app


class Wire(base.Wire):
    def __init__(self, app, out):
        super().__init__(app, out)
        self.log = (out / "requests.jsonl").open("w", buffering=1)
        self.unique = set()
        self.by_observation = {}
        self.request_serial = 0
        self.connections = set()
        self.active = 0
        self.max_active = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        self.request_serial += 1
        record = dict(
            serial=self.request_serial,
            start_ns=time.perf_counter_ns(),
            start_utc=time.time(),
            method=scope["method"],
            path=scope["path"],
            ns=Counter(),
            cpu_ns=Counter(),
            calls=Counter(),
            connections=set(),
        )
        token = CURRENT.set(record)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.connections.add(tuple(scope.get("client") or []))
        request_bytes = 0
        messages = []

        async def recv():
            nonlocal request_bytes
            message = await receive()
            request_bytes += len(message.get("body", b""))
            return message

        async def capture(message):
            messages.append(message)

        try:
            await self.app(scope, recv, capture)
            record["handler_end_ns"] = time.perf_counter_ns()
            start = next(m for m in messages if m["type"] == "http.response.start")
            raw = b"".join(m.get("body", b"") for m in messages)
            status, path = start["status"], scope["path"]
            record.update(
                status=status,
                request_bytes=request_bytes,
                response_bytes=len(raw),
                request_header_bytes=sum(
                    len(k) + len(v) + 4 for k, v in scope["headers"]
                ),
                response_header_bytes=sum(
                    len(k) + len(v) + 4 for k, v in start.get("headers", [])
                ),
            )
            self.counts["requests"] += 1
            self.counts[f"status_{status}"] += 1
            self.counts["request_entity_bytes"] += request_bytes
            self.counts["response_entity_bytes"] += len(raw)
            self.counts["handler_ns"] += record["handler_end_ns"] - record["start_ns"]
            if path.endswith("/objects") and status == 200:
                body = json.loads(raw)
                observation_id = path.split("/")[-2]
                seen = self.by_observation.setdefault(observation_id, set())
                record["observation_id"] = observation_id
                chunks = body["chunks"]
                hashes = {
                    c["object"]["hash"] if "object" in c else c["ref"]["hash"]
                    for c in chunks
                }
                record.update(
                    chunks=len(chunks),
                    decoded_bytes=sum(c["length"] for c in chunks),
                    new_global_hashes=len(hashes - self.unique),
                    reused_previous_observation_hashes=len(
                        hashes & (self.unique - seen)
                    ),
                    duplicate_same_observation_hashes=len(hashes & seen),
                    unique_hashes_in_response=len(hashes),
                )
                self.unique.update(hashes)
                seen.update(hashes)
                self.counts["object_requests"] += 1
                self.counts["chunks"] += len(chunks)
                self.counts["decoded_object_bytes"] += record["decoded_bytes"]
            elif path.endswith("/observations") and status in (200, 201):
                manifest = json.loads(raw)
                self.last_manifest = manifest
                self.counts["observation_requests"] += 1
                record["manifest"] = manifest
                base.write(
                    self.out / f"manifest-{self.counts['observation_requests']}.json",
                    manifest,
                )
            elif scope["method"] == "DELETE":
                self.counts["release_requests"] += 1
            if status >= 400:
                failure = dict(
                    status=status,
                    method=scope["method"],
                    path=path,
                    body=json.loads(raw),
                    wall_time=time.time(),
                )
                record["failure_body"] = failure["body"]
                self.failures.append(failure)
                base.write(self.out / "http-failures.json", self.failures)
            # Instrumentation postprocessing is charged separately from handler time.
            record["instrumentation_postprocess_ns"] = (
                time.perf_counter_ns() - record["handler_end_ns"]
            )
            for message in messages:
                await send(message)
            record["sent_ns"] = time.perf_counter_ns()
        finally:
            self.active -= 1
            record["end_ns"] = time.perf_counter_ns()
            record["connections"] = sorted(record["connections"])
            record.update(
                max_active=self.max_active,
                tcp_connections=len(self.connections),
                global_unique_objects=len(self.unique),
            )
            self.log.write(json.dumps(record, separators=(",", ":")) + "\n")
            if self.request_serial % 50 == 0 or "failure_body" in record:
                base.write(
                    self.out / "wire-progress.json",
                    dict(
                        self.counts,
                        global_unique_objects=len(self.unique),
                        tcp_connections=len(self.connections),
                        max_active=self.max_active,
                    ),
                )
            CURRENT.reset(token)


base.Wire = Wire
if __name__ == "__main__":
    base.main()

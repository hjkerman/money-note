"""합성 실행 전용 delegates. 제품/engine source와 sync 판단은 변경하지 않는다."""

from collections import Counter
from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
import functools
import hashlib
import sqlite3
import sys
from threading import Lock
from unittest.mock import patch

from isolated_sync import canonical

ACTIVE = ContextVar("b03_logical_cost", default=None)
HASH_PURPOSE = ContextVar("b03_hash_purpose", default="sha256")
STAGES = frozenset({"setup", "generation", "observation", "transfer", "calibration"})
NATIVE_HASH = hashlib.sha256
NATIVE_CONNECT = sqlite3.connect


class Collector:
    """고정 stage/operation과 최대 128개 SQL table 분류의 aggregate만 보존한다."""

    def __init__(self):
        self.values = Counter()
        self.lock = Lock()
        self.closed = False
        self.pending = 0
        self._completion = None

    def add(self, key, amount=1):
        with self.lock:
            if not self.closed:
                self.values[key] += amount

    def close(self):
        with self.lock:
            self.closed = True

    def merge(self, other):
        for key, value in other.snapshot().items():
            self.add(key, int(value))

    def hold(self):
        with self.lock:
            self.pending += 1

    def release(self):
        with self.lock:
            self.pending -= 1
        self._complete_if_idle()

    def finish_when_idle(self, completion):
        with self.lock:
            self._completion = completion
        self._complete_if_idle()

    def _complete_if_idle(self):
        completion = None
        with self.lock:
            if self.pending == 0 and self._completion is not None:
                self.closed = True
                completion, self._completion = self._completion, None
        if completion is not None:
            completion(self)

    @contextmanager
    def stage(self, stage):
        if stage not in STAGES:
            raise ValueError("B03 stage outside finite schema")
        token = ACTIVE.set((self, stage))
        try:
            yield self
        finally:
            ACTIVE.reset(token)

    def snapshot(self):
        with self.lock:
            return {key: str(value) for key, value in sorted(self.values.items())}


def add(operation, metric, amount=1):
    active = ACTIVE.get()
    if active:
        active[0].add(f"{active[1]}/{operation}/{metric}", amount)


class ObservedHash:
    def __init__(self, data=b"", **kwargs):
        self.inner = NATIVE_HASH(data, **kwargs)
        self.owner = ACTIVE.get()
        self.operation = HASH_PURPOSE.get()
        self._add("calls", 1)
        self._add("hash_input_bytes", memoryview(data).nbytes)

    def _add(self, metric, amount):
        if self.owner:
            self.owner[0].add(f"{self.owner[1]}/{self.operation}/{metric}", amount)

    def update(self, data):
        self.inner.update(data)
        self._add("hash_input_bytes", memoryview(data).nbytes)

    def copy(self):
        result = object.__new__(ObservedHash)
        result.inner, result.owner = self.inner.copy(), self.owner
        result.operation = self.operation
        self._add("copies", 1)
        return result

    def __getattr__(self, name):
        return getattr(self.inner, name)


@contextmanager
def authentication_hashes():
    """실제 auth 함수의 SHA만 별도 exclusive 분류. 입력/알고리즘은 그대로다."""
    token = HASH_PURPOSE.set("authentication_sha256")
    try:
        yield
    finally:
        HASH_PURPOSE.reset(token)


@contextmanager
def instrument_workers():
    """취소된 ASGI가 아니라 실제 기존 native job 종료가 계수 scope를 끝낸다."""
    from isolated_sync.workers import NativeJob

    init, finish = NativeJob.__init__, NativeJob._finish

    def owned_init(job, lease):
        init(job, lease)
        active = ACTIVE.get()
        job._b03_owner = active[0] if active else None
        if job._b03_owner is not None:
            job._b03_owner.hold()

    def owned_finish(job):
        was_finished = job.finished
        finish(job)
        if not was_finished and job._b03_owner is not None:
            job._b03_owner.release()

    with (
        patch.object(NativeJob, "__init__", owned_init),
        patch.object(NativeJob, "_finish", owned_finish),
    ):
        yield


@contextmanager
def instrument():
    """설치/해제는 test session이 소유한다. attribution은 request-local ContextVar다.

    test session 동안 실제 SHA primitive와 canonical global을 감싸므로 late import도
    같은 경계를 지난다. run/stage는 ContextVar이며 process-global current-run은 없다.
    기존 from-import alias만 시작 시 교체하고 종료 시 모두 복원한다.
    """
    parse = canonical._parse_json

    @functools.wraps(parse)
    def observed_parse(raw):
        size = len(raw) if isinstance(raw, bytes) else 0
        add("json", "calls")
        add("json", "submitted_bytes", size)
        try:
            result = parse(raw)
        except BaseException:
            add("json", "failed_calls")
            add("json", "failed_submitted_bytes", size)
            raise
        add("json", "completed_bytes", size)
        return result

    encode = canonical.encode

    @functools.wraps(encode)
    def observed_encode(value):
        result = encode(value)
        add("encoding", "calls")
        add("encoding", "output_bytes", len(result))
        return result

    with ExitStack() as stack:
        stack.enter_context(patch.object(canonical, "_parse_json", observed_parse))
        stack.enter_context(patch.object(canonical, "encode", observed_encode))
        stack.enter_context(patch.object(hashlib, "sha256", ObservedHash))
        for name, module in list(sys.modules.items()):
            if not name.startswith(("app.", "isolated_sync.")) or module is None:
                continue
            for key, value in list(vars(module).items()):
                if value is NATIVE_HASH:
                    stack.enter_context(patch.object(module, key, ObservedHash))
                elif value is encode:
                    stack.enter_context(patch.object(module, key, observed_encode))
        try:
            yield
        finally:
            # Imports performed inside the test session can retain from-import
            # aliases. Restore those too; no observer escapes into later tests.
            for name, module in list(sys.modules.items()):
                if not name.startswith(("app.", "isolated_sync.")) or module is None:
                    continue
                for key, value in list(vars(module).items()):
                    if value is ObservedHash:
                        setattr(module, key, NATIVE_HASH)
                    elif value is observed_encode:
                        setattr(module, key, encode)


def quote(value):
    return '"' + value.replace('"', '""') + '"'


class CostConnectionMixin:
    """원 Connection subclass의 authorizer/finalizer를 유지하는 test-only mixin."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cost_tables = set()
        self._cost_pending = Counter()
        self._cost_savepoints = []
        self._cost_exiting_error = False
        self._cost_initialized = False
        self._cost_closed = False
        self.create_function("b03_observe_row", 8, self._cost_row)

    def _cost_row(self, timing, table, operation, blob, text, scalar, null, columns):
        active = ACTIVE.get()
        if active is None:
            return
        owner, stage = active
        owner.add(f"{stage}/{table}/{operation}/{timing}/rows")
        for metric, amount in zip(
            ("blob_bytes", "text_bytes", "scalar_values", "null_values", "columns"),
            (blob, text, scalar, null, columns),
        ):
            owner.add(f"{stage}/{table}/{operation}/{timing}/{metric}", amount)
            if timing == "effective":
                self._cost_pending[(owner, stage, table, operation, metric)] += amount

    def _cost_install(self):
        native = super().execute
        for (table,) in native(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ):
            if table in self._cost_tables:
                continue
            if len(self._cost_tables) >= 128:
                raise RuntimeError("B03 table capacity exceeded")
            columns = [r[1] for r in native(f"PRAGMA table_info({quote(table)})")]

            def expression(predicate, lengths=False):
                terms = []
                for c in columns:
                    value = "NEW." + quote(c)
                    size = f"length(CAST({value} AS BLOB))" if lengths else "1"
                    terms.append(
                        f"CASE WHEN typeof({value}) {predicate} THEN {size} ELSE 0 END"
                    )
                return "+".join(terms)

            values = ",".join(
                [
                    expression("='blob'", True),
                    expression("='text'", True),
                    expression("IN ('integer','real')"),
                    expression("='null'"),
                    str(len(columns)),
                ]
            )
            for operation in ("INSERT", "UPDATE", "DELETE"):
                for timing, position in (
                    ("attempted", "BEFORE"),
                    ("effective", "AFTER"),
                ):
                    args = "0,0,0,0,0" if operation == "DELETE" else values
                    trigger = quote(f"b03_{table}_{operation}_{timing}")
                    native(
                        f"CREATE TEMP TRIGGER {trigger} {position} {operation} ON main.{quote(table)} "
                        f"BEGIN SELECT b03_observe_row('{timing}','{table}','{operation}',{args}); END"
                    )
            self._cost_tables.add(table)

    def _cost_settle(self, outcome, values=None):
        if values is None:
            values = self._cost_pending
        for (owner, stage, table, operation, metric), amount in values.items():
            owner.add(f"{stage}/{table}/{operation}/{outcome}/{metric}", amount)

    def execute(self, sql, parameters=(), /):
        words = sql.strip().split()
        verb = words[0].upper() if words else ""
        if not self._cost_initialized and verb in {
            "INSERT",
            "UPDATE",
            "DELETE",
            "REPLACE",
        }:
            # Native connect and B01's opened-FD witness have finished first.
            self._cost_install()
            self._cost_initialized = True
        add("sql", "statements")
        for value in (
            parameters.values() if isinstance(parameters, dict) else parameters
        ):
            if isinstance(value, bytes):
                add("sql", "bind_blob_bytes", len(value))
            elif isinstance(value, str):
                add("sql", "bind_text_characters", len(value))
            else:
                add("sql", "scalar_or_null_binds")
        before = self._cost_pending.copy()
        try:
            result = super().execute(sql, parameters)
            if verb == "SAVEPOINT":
                if len(self._cost_savepoints) == 32:
                    raise RuntimeError("B03 savepoint capacity exceeded")
                self._cost_savepoints.append((words[1], before))
            elif verb == "ROLLBACK" and len(words) > 1:
                name = words[-1]
                index = next(
                    i for i, p in enumerate(self._cost_savepoints) if p[0] == name
                )
                saved = self._cost_savepoints[index][1]
                self._cost_settle("rolled_back", self._cost_pending - saved)
                self._cost_pending = saved.copy()
                del self._cost_savepoints[index + 1 :]
            elif verb == "ROLLBACK":
                self._cost_settle("rolled_back")
                self._cost_pending.clear()
                self._cost_savepoints.clear()
            elif verb == "RELEASE":
                name = words[-1]
                index = next(
                    i for i, p in enumerate(self._cost_savepoints) if p[0] == name
                )
                del self._cost_savepoints[index:]
            if not self.in_transaction:
                self._cost_settle("committed")
                self._cost_pending.clear()
            if verb in {"CREATE", "ALTER"}:
                self._cost_initialized = False
            return result
        except BaseException:
            add("sql", "failed_statements")
            if not self.in_transaction:
                self._cost_settle("rolled_back")
                self._cost_pending.clear()
            else:
                self._cost_settle("statement_rolled_back", self._cost_pending - before)
                self._cost_pending = before
            raise

    def executemany(self, sql, parameters, /):
        # Native executemany commits no transaction itself. Observe each actual
        # iteration, retaining prior successful rows if a later row fails.
        if not self._cost_initialized:
            self._cost_install()
            self._cost_initialized = True
        latest = self._cost_pending.copy()

        def inputs():
            nonlocal latest
            for row in parameters:
                latest = self._cost_pending.copy()
                add("sql", "statements")
                for value in row.values() if isinstance(row, dict) else row:
                    if isinstance(value, bytes):
                        add("sql", "bind_blob_bytes", len(value))
                    elif isinstance(value, str):
                        add("sql", "bind_text_characters", len(value))
                    else:
                        add("sql", "scalar_or_null_binds")
                yield row

        try:
            result = super().executemany(sql, inputs())
        except BaseException:
            add("sql", "failed_statements")
            self._cost_settle("statement_rolled_back", self._cost_pending - latest)
            self._cost_pending = latest
            if not self.in_transaction:
                self._cost_settle("committed")
                self._cost_pending.clear()
            raise
        if not self.in_transaction:
            self._cost_settle("committed")
            self._cost_pending.clear()
        return result

    def commit(self):
        try:
            super().commit()
        except BaseException:
            add("sql", "failed_commits")
            raise
        self._cost_settle("committed")
        self._cost_pending.clear()
        self._cost_savepoints.clear()

    def rollback(self):
        super().rollback()
        self._cost_settle("rolled_back")
        self._cost_pending.clear()
        self._cost_savepoints.clear()

    def close(self):
        if self._cost_closed:
            return super().close()
        pending_transaction = self.in_transaction
        super().close()
        self._cost_closed = True
        self._cost_settle(
            "rolled_back_on_close"
            if pending_transaction or self._cost_exiting_error
            else "committed"
        )
        self._cost_pending.clear()

    def __exit__(self, *args):
        self._cost_exiting_error = args[0] is not None
        try:
            result = super().__exit__(*args)
        except BaseException:
            self._cost_settle("rolled_back")
            self._cost_pending.clear()
            raise
        self._cost_settle("rolled_back" if args[0] else "committed")
        self._cost_pending.clear()
        return result


@functools.lru_cache(maxsize=16)
def observed_factory(original=sqlite3.Connection):
    return type("B03" + original.__name__, (CostConnectionMixin, original), {})


@contextmanager
def instrument_connections():
    """기존 factory를 버리지 않는다. test session만 설치하며 비활성 요청은 원 연결이다."""

    def connect(*args, **kwargs):
        if ACTIVE.get() is not None:
            kwargs["factory"] = observed_factory(
                kwargs.get("factory", sqlite3.Connection)
            )
        return NATIVE_CONNECT(*args, **kwargs)

    with patch.object(sqlite3, "connect", connect):
        yield

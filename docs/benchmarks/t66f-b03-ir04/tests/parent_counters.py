"""합성 실행 전용 delegates. 제품/engine source와 sync 판단은 변경하지 않는다."""

from collections import Counter
from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
import functools
import hashlib
import sqlite3
import sys
from threading import Lock, RLock
from unittest.mock import patch

from isolated_sync import canonical

ACTIVE = ContextVar("b03_logical_cost", default=None)
HASH_PURPOSE = ContextVar("b03_hash_purpose", default="sha256")
STAGES = frozenset({"setup", "generation", "observation", "transfer", "calibration"})
NATIVE_HASH = hashlib.sha256
NATIVE_CONNECT = sqlite3.connect
INSTALL_LOCK = RLock()
INSTALLATIONS = {}
TRANSACTION_OWNER_LIMIT = 32


@contextmanager
def installation(name):
    """세 고정 diagnostic 설치의 refcount. run attribution과 무관하다."""
    with INSTALL_LOCK:
        state = INSTALLATIONS.get(name)
        first = state is None
        if first:
            state = [0, ExitStack()]
            INSTALLATIONS[name] = state
        state[0] += 1
    try:
        yield state[1] if first else None
    finally:
        with INSTALL_LOCK:
            state[0] -= 1
            if state[0] == 0:
                try:
                    state[1].close()
                finally:
                    del INSTALLATIONS[name]


def sql_words(sql):
    """선행/inter-token SQL 주석만 건너뛴다. SQL은 수정하지 않는다.

    제어문/명시 conflict prefix에 필요한 token만 읽는다. quoted savepoint는
    SQLite identifier escaping을 따른다. statement body/literal을 해석하지 않는다.
    """
    words, i = [], 0
    while i < len(sql) and len(words) < 6:
        if sql[i].isspace() or sql[i] == ";":
            i += 1
        elif sql.startswith("--", i):
            end = sql.find("\n", i + 2)
            i = len(sql) if end < 0 else end + 1
        elif sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            i = len(sql) if end < 0 else end + 2
        elif sql[i] in "\"'`[":
            end_quote = "]" if sql[i] == "[" else sql[i]
            i += 1
            value = ""
            while i < len(sql):
                ch = sql[i]
                i += 1
                if ch == end_quote:
                    if i < len(sql) and sql[i] == ch and ch != "]":
                        i += 1
                    else:
                        break
                value += ch
            words.append(
                value.translate(
                    str.maketrans(
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
                    )
                )
            )
        else:
            start = i
            while i < len(sql) and (sql[i].isalnum() or sql[i] == "_"):
                i += 1
            if i == start:
                break
            words.append(
                sql[start:i].translate(
                    str.maketrans(
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
                    )
                )
            )
    return words


def preserves_failed_prefix(words, error):
    # SQLite OR FAIL preserves prior rows for these native constraint classes.
    # FK and RAISE(ABORT) override it. Schema FAIL/RAISE(FAIL) are rejected by
    # the diagnostic schema gate, not guessed from an exception string.
    return words[1:3] == ["or", "fail"] and getattr(error, "sqlite_errorcode", 0) in {
        sqlite3.SQLITE_CONSTRAINT_CHECK,
        sqlite3.SQLITE_CONSTRAINT_NOTNULL,
        sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
        sqlite3.SQLITE_CONSTRAINT_UNIQUE,
    }


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
    from isolated_sync.workers import NativeJob, WorkerLease

    init, finish, run = NativeJob.__init__, NativeJob._finish, WorkerLease.run
    dispatched = ContextVar("b03_dispatch", default=None)

    def owned_init(job, lease):
        init(job, lease)
        active = ACTIVE.get()
        job._b03_owner = active[0] if active else None
        if job._b03_owner is not None:
            job._b03_owner.hold()
        created = dispatched.get()
        if created is not None:
            created.append(job)

    def owned_finish(job):
        was_finished = job.finished
        finish(job)
        if not was_finished and job._b03_owner is not None:
            job._b03_owner.release()
            job._b03_owner = None

    async def owned_run(lease, function, *args):
        created = []  # 원 run은 NativeJob을 정확히 하나 생성한다.
        token = dispatched.set(created)
        try:
            return await run(lease, function, *args)
        finally:
            dispatched.reset(token)
            with lease.budget._lock:
                for job in created:
                    if job not in lease._jobs and job._b03_owner is not None:
                        # 등록 이전 거부만 해당한다. 등록된 native tail의 hold는
                        # 기존 _finish가 소유하며 취소한 requester가 회수하지 않는다.
                        job._b03_owner.release()
                        job._b03_owner = None

    with installation("workers") as stack:
        if stack is not None:
            stack.enter_context(patch.object(NativeJob, "__init__", owned_init))
            stack.enter_context(patch.object(NativeJob, "_finish", owned_finish))
            stack.enter_context(patch.object(WorkerLease, "run", owned_run))
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

    with installation("primitives") as stack:
        if stack is None:
            yield
            return
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

        def restore_aliases():
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

        stack.callback(restore_aliases)
        yield


def quote(value):
    return '"' + value.replace('"', '""') + '"'


class CostConnectionMixin:
    """원 Connection subclass의 authorizer/finalizer를 유지하는 test-only mixin."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cost_tables = set()
        self._cost_pending = Counter()
        self._cost_owners = set()
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
                self._cost_owners.add(owner)
                self._cost_pending[(owner, stage, table, operation, metric)] += amount

    def _cost_install(self):
        native = super().execute
        # 이 좁은 observer는 explicit OR FAIL을 지원한다. schema-defined
        # FAIL/RAISE(FAIL)는 statement 결과를 확정할 수 없어 실행 전에 거부한다.
        for (sql,) in native("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"):
            import re

            if re.search(r"\bON\s+CONFLICT\s+FAIL\b|\bRAISE\s*\(\s*FAIL\b", sql, re.I):
                raise RuntimeError("B03 unsupported schema conflict mode")
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
                        f"CREATE TEMP TRIGGER IF NOT EXISTS {trigger} {position} {operation} ON main.{quote(table)} "
                        f"BEGIN SELECT b03_observe_row('{timing}','{table}','{operation}',{args}); END"
                    )
            self._cost_tables.add(table)

    def _cost_settle(self, outcome, values=None):
        if values is None:
            values = self._cost_pending
        for (owner, stage, table, operation, metric), amount in values.items():
            owner.add(f"{stage}/{table}/{operation}/{outcome}/{metric}", amount)

    def execute(self, sql, parameters=(), /):
        words = sql_words(sql)
        verb = words[0].upper() if words else ""
        if verb == "SAVEPOINT" and len(self._cost_savepoints) >= 32:
            raise RuntimeError("B03 savepoint capacity exceeded")
        if verb in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
            self._cost_check_owner()
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
                self._cost_savepoints.append((words[1], before))
            elif verb == "ROLLBACK" and "to" in words:
                name = words[-1]
                index = next(
                    i
                    for i in reversed(range(len(self._cost_savepoints)))
                    if self._cost_savepoints[i][0] == name
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
                    i
                    for i in reversed(range(len(self._cost_savepoints)))
                    if self._cost_savepoints[i][0] == name
                )
                del self._cost_savepoints[index:]
            if not self.in_transaction:
                self._cost_settle("committed")
                self._cost_pending.clear()
                self._cost_owners.clear()
                self._cost_savepoints.clear()
            if verb in {"CREATE", "ALTER", "ROLLBACK"}:
                self._cost_initialized = False
                if verb == "ROLLBACK":
                    self._cost_tables.clear()
            return result
        except BaseException as error:
            add("sql", "failed_statements")
            if preserves_failed_prefix(words, error):
                if not self.in_transaction:
                    self._cost_settle("committed")
                    self._cost_pending.clear()
            elif not self.in_transaction:
                self._cost_settle("rolled_back")
                self._cost_pending.clear()
            else:
                self._cost_settle("statement_rolled_back", self._cost_pending - before)
                self._cost_pending = before
            if not self.in_transaction:
                self._cost_owners.clear()
                self._cost_savepoints.clear()
                self._cost_initialized = False
                self._cost_tables.clear()
            raise

    def _cost_check_owner(self):
        active = ACTIVE.get()
        if (
            active
            and active[0] not in self._cost_owners
            and len(self._cost_owners) >= TRANSACTION_OWNER_LIMIT
        ):
            active[0].add(f"{active[1]}/coverage/transaction_owner_capacity")
            raise RuntimeError(
                "B03 transaction owner capacity exceeded; measurement incomplete"
            )

    def executemany(self, sql, parameters, /):
        # Native executemany commits no transaction itself. Observe each actual
        # iteration, retaining prior successful rows if a later row fails.
        if not self._cost_initialized:
            self._cost_install()
            self._cost_initialized = True
        latest = self._cost_pending.copy()
        latest_in_transaction = self.in_transaction
        executing_statement = False

        def inputs():
            nonlocal latest, latest_in_transaction, executing_statement
            for row in parameters:
                if not self.in_transaction:
                    self._cost_settle("committed")
                    self._cost_pending.clear()
                    self._cost_owners.clear()
                self._cost_check_owner()
                latest = self._cost_pending.copy()
                latest_in_transaction = self.in_transaction
                add("sql", "statements")
                for value in row.values() if isinstance(row, dict) else row:
                    if isinstance(value, bytes):
                        add("sql", "bind_blob_bytes", len(value))
                    elif isinstance(value, str):
                        add("sql", "bind_text_characters", len(value))
                    else:
                        add("sql", "scalar_or_null_binds")
                executing_statement = True
                yield row
                # Resumption proves the previous native iteration succeeded.
                # An input iterator exception before the next yield rolls back
                # no SQLite statement, and must retain that successful prefix.
                executing_statement = False

        try:
            result = super().executemany(sql, inputs())
        except BaseException as error:
            add("sql", "failed_statements")
            if not self.in_transaction and latest_in_transaction:
                self._cost_settle("rolled_back")
                self._cost_pending.clear()
            elif executing_statement and not preserves_failed_prefix(
                sql_words(sql), error
            ):
                self._cost_settle("statement_rolled_back", self._cost_pending - latest)
                self._cost_pending = latest
            if not self.in_transaction:
                self._cost_settle("committed")
                self._cost_pending.clear()
                self._cost_owners.clear()
                self._cost_savepoints.clear()
                self._cost_initialized = False
                self._cost_tables.clear()
            raise
        if not self.in_transaction:
            self._cost_settle("committed")
            self._cost_pending.clear()
            self._cost_owners.clear()
            self._cost_savepoints.clear()
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
        self._cost_owners.clear()

    def rollback(self):
        super().rollback()
        self._cost_settle("rolled_back")
        self._cost_pending.clear()
        self._cost_savepoints.clear()
        self._cost_owners.clear()
        self._cost_initialized = False
        self._cost_tables.clear()

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
        self._cost_savepoints.clear()
        self._cost_owners.clear()

    def __exit__(self, *args):
        self._cost_exiting_error = args[0] is not None
        try:
            result = super().__exit__(*args)
        except BaseException:
            self._cost_settle("rolled_back")
            self._cost_pending.clear()
            self._cost_owners.clear()
            self._cost_savepoints.clear()
            self._cost_initialized = False
            self._cost_tables.clear()
            raise
        self._cost_settle("rolled_back" if args[0] else "committed")
        self._cost_pending.clear()
        self._cost_savepoints.clear()
        self._cost_owners.clear()
        self._cost_initialized = False
        self._cost_tables.clear()
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

    with installation("connections") as stack:
        if stack is not None:
            stack.enter_context(patch.object(sqlite3, "connect", connect))
        yield

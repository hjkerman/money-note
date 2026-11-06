"""합성 실행 전용 delegates. 제품/engine source와 sync 판단은 변경하지 않는다."""

from collections import Counter
from contextlib import contextmanager, ExitStack, nullcontext
from contextvars import ContextVar
import dis
import functools
import hashlib
import signal
import sqlite3
import sys
from threading import Event, Lock, RLock, current_thread, main_thread
from types import MethodType
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
PATCH_LIMIT = 256
SIGNAL_REGION_LIMIT = 128
SIGNAL_REGIONS = []  # Main-thread active owners only; no retired history.
SIGNAL_BASE = None
CONTEXT_UNSET = object()
CANCELLABLE_LINES = {}  # Exactly two fixed generator codes, initialized below.


def signal_root(handler):
    while hasattr(handler, "_b03_previous"):
        handler = handler._b03_previous
    return handler


def deliver_signal(handler, signum, frame):
    if callable(handler):
        handler(signum, frame)
    elif handler == signal.SIG_DFL:
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)


def route_signal(signum, frame):
    frames = []
    cursor = frame
    while cursor is not None:
        frames.append(cursor)
        cursor = cursor.f_back
    # Waiting for another installer must remain cancellable. Its caller's
    # finally is protected once wait_for_installation has unwound.
    waiting = any(f.f_code is wait_for_installation.__code__ for f in frames)
    if not waiting:
        for region in reversed(SIGNAL_REGIONS):
            if any(f is region.frame for f in frames):
                if region.frame.f_lineno in CANCELLABLE_LINES.get(
                    region.frame.f_code, ()
                ):
                    # At the pre-yield checkpoint and yield itself the finally
                    # already owns cleanup. Never carry cancellation into the
                    # suspended user's body, even after checkpoint returned.
                    continue
                if region.pending is None:
                    region.pending = (signum, frame)
                return
    deliver_signal(SIGNAL_BASE, signum, frame)


def restored_signal_handler(previous):
    # Preserve a still-active enclosing synchronous guard. A retired temporary
    # guard must never become the delegate of the persistent lifecycle router.
    while hasattr(previous, "_b03_previous"):
        if previous._b03_active:
            return previous
        previous = previous._b03_previous
    if SIGNAL_REGIONS:
        return route_signal
    return SIGNAL_BASE if previous is route_signal else previous


class SignalRegion:
    """Shield active generator bookkeeping, not its suspended user body.

    Exact frame identity handles nested/async scopes. Removing an owner out of
    order cannot restore a retired signal handler over another live owner.
    """

    def __init__(self, frame):
        self.frame, self.pending = frame, None
        self.main = current_thread() is main_thread()

    def __enter__(self):
        global SIGNAL_BASE
        try:
            if self.main:
                if not SIGNAL_REGIONS:
                    SIGNAL_BASE = signal_root(signal.getsignal(signal.SIGINT))
                with ownership_change():
                    if len(SIGNAL_REGIONS) >= SIGNAL_REGION_LIMIT:
                        raise RuntimeError("B03 signal owner capacity exceeded")
                    SIGNAL_REGIONS.append(self)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def checkpoint(self):
        if self.pending is not None:
            pending, self.pending = self.pending, None
            deliver_signal(SIGNAL_BASE, *pending)

    def __exit__(self, *error):
        failure = None
        try:
            if self.main:
                for attempt in range(2):
                    try:
                        with ownership_change():
                            if self in SIGNAL_REGIONS:
                                SIGNAL_REGIONS.remove(self)
                        break
                    except BaseException as caught:
                        failure = failure or caught
        finally:
            self.frame = None
            self.checkpoint()
        if failure is not None:
            raise failure


@contextmanager
def ownership_change():
    """Defer SIGINT only through a synchronous ownership change, never an await.

    Python signal handlers run on the main thread. Worker threads have no
    synchronous Task.cancel boundary; their ordinary exceptions still unwind.
    The original handler runs as soon as consistency has been restored.
    """
    if current_thread() is not main_thread():
        yield
        return
    previous = signal.getsignal(signal.SIGINT)
    pending = []  # At most one pending delivery, matching signal coalescing.

    def defer(signum, frame):
        if not pending:
            pending.append((signum, frame))

    defer._b03_previous = previous
    defer._b03_active = True

    try:
        signal.signal(signal.SIGINT, defer)
        yield
    finally:
        defer._b03_active = False
        restored = restored_signal_handler(previous)
        try:
            signal.signal(signal.SIGINT, restored)
        finally:
            if signal.getsignal(signal.SIGINT) is defer:
                signal.signal(signal.SIGINT, restored)
        if pending:
            deliver_signal(restored, *pending[0])


class RecoveryPatch:
    """One reversible patch; fallback also handles a partially started mock."""

    def __init__(self, target, name, value):
        self.target, self.name, self.value = target, name, value
        self.local = name in vars(target)
        self.original = vars(target)[name] if self.local else getattr(target, name)
        self.inner = patch.object(target, name, value)

    def start(self):
        self.inner.start()

    def stop(self):
        current = getattr(self.target, self.name)
        if current is not self.value and current is not self.original:
            raise RuntimeError("B03 patch ownership changed; measurement incomplete")
        try:
            self.inner.stop()
        finally:
            # _patch.start can fail after setattr but before its active-list
            # append; stop alone then has no restoration action.
            if getattr(self.target, self.name) is self.value:
                if self.local:
                    setattr(self.target, self.name, self.original)
                else:
                    delattr(self.target, self.name)


class RecoveryStack:
    """Bounded restoration journal; failed callbacks remain owned and retryable."""

    def __init__(self):
        self.inner = ExitStack()

    def reserve(self, patcher):
        self.callback(patcher.stop)

    def callback(self, callback, *args, **kwargs):
        if isinstance(getattr(callback, "__self__", None), RecoveryPatch):
            # reserve and commit refer to one obligation, not two callbacks.
            for _, existing in self.inner._exit_callbacks:
                if getattr(existing, "__wrapped__", None) == callback:
                    return callback
        if len(self.inner._exit_callbacks) >= PATCH_LIMIT:
            raise RuntimeError("B03 patch capacity exceeded")
        return self.inner.callback(callback, *args, **kwargs)

    def enter_context(self, context):
        if len(self.inner._exit_callbacks) >= PATCH_LIMIT:
            raise RuntimeError("B03 patch capacity exceeded")
        return self.inner.enter_context(context)

    def close(self):
        while self.inner._exit_callbacks:
            synchronous, callback = self.inner._exit_callbacks[-1]
            assert synchronous
            callback(None, None, None)
            self.inner._exit_callbacks.pop()


@contextmanager
def scoped_value(variable, value):
    """Context registration and its reset obligation share one protected owner."""
    with SignalRegion(sys._getframe()) as region:
        token = None
        previous = variable.get(CONTEXT_UNSET)
        reset_done = False
        try:
            with ownership_change():
                token = variable.set(value)
            region.checkpoint()
            yield
        finally:
            try:
                if token is not None:
                    with ownership_change():
                        variable.reset(token)
                        reset_done = True
            finally:
                if token is not None and not reset_done:
                    # A failed first cleanup may precede reset, or follow a
                    # successful reset. Verify exact previous presence/identity
                    # before retrying an otherwise single-use native token.
                    if variable.get(CONTEXT_UNSET) is not previous:
                        with ownership_change():
                            variable.reset(token)


@contextmanager
def installation(name):
    """세 고정 diagnostic 설치의 refcount. run attribution과 무관하다."""
    with SignalRegion(sys._getframe()) as region:
        if name not in {"primitives", "workers", "connections"}:
            raise ValueError("B03 installation outside finite schema")
        state, first, held = None, False, False
        try:
            with ownership_change():
                with INSTALL_LOCK:
                    state = INSTALLATIONS.get(name)
                    if state is not None and state["refs"] == 0:
                        # A persistent cleanup failure retains ONE generation.
                        # Recovery must finish before a new delegate is captured.
                        restoring = state["stack"]
                        restoring.close()
                        del INSTALLATIONS[name]
                        state = None
                    first = state is None
                    if first:
                        state = {
                            "refs": 0,
                            "stack": RecoveryStack(),
                            "ready": Event(),
                            "error": None,
                            "status": "INSTALLING",
                        }
                        INSTALLATIONS[name] = state
                    before = state["refs"]
                    try:
                        state["refs"] = before + 1
                        held = True
                    except BaseException:
                        state["refs"], held = before, False
                        raise
            if not first:
                wait_for_installation(state)
                if state["error"] is not None:
                    raise RuntimeError(
                        f"B03 {name} instrumentation installation failed"
                    ) from state["error"]
            try:
                region.checkpoint()
                yield state["stack"] if first else None
            except BaseException as error:
                if first and not state["ready"].is_set():
                    with ownership_change():
                        with INSTALL_LOCK:
                            state["error"] = error
                            state["ready"].set()
                raise
        finally:
            cleanup_error = None
            for attempt in range(2):
                try:
                    with ownership_change():
                        with INSTALL_LOCK:
                            if state is not None and INSTALLATIONS.get(name) is state:
                                if first and not state["ready"].is_set():
                                    state["error"] = state["error"] or RuntimeError(
                                        f"B03 {name} installation incomplete"
                                    )
                                    state["ready"].set()
                                if held:
                                    before = state["refs"]
                                    try:
                                        state["refs"] = before - 1
                                        held = False
                                    except BaseException:
                                        state["refs"], held = before, True
                                        raise
                                if state["refs"] == 0:
                                    state["status"] = "RESTORING"
                                    try:
                                        state["stack"].close()
                                    except BaseException as error:
                                        state["status"], state["error"] = (
                                            "RECOVERING",
                                            error,
                                        )
                                        raise
                                    if INSTALLATIONS.get(name) is state:
                                        del INSTALLATIONS[name]
                    break
                except BaseException as error:
                    cleanup_error = cleanup_error or error
                    if attempt == 1:
                        cleanup_error.add_note(
                            "B03 bounded cleanup retry failed; generation retained if restoration incomplete"
                        )
            if cleanup_error is not None:
                raise cleanup_error


def wait_for_installation(state):
    """Concurrent scopes do not proceed until every wrapper is installed."""
    state["ready"].wait()


def installation_ready(name):
    with ownership_change():
        with INSTALL_LOCK:
            state = INSTALLATIONS.get(name)
            if state is None or state["ready"].is_set():
                raise RuntimeError(f"B03 {name} instrumentation readiness is invalid")
            state["status"] = "ACTIVE"
            state["ready"].set()


def install_patch(stack, target, name, value):
    """Install synchronously and register exact teardown before publishing readiness."""
    patcher = RecoveryPatch(target, name, value)
    with ownership_change():
        stack.reserve(patcher)
        patcher.start()
        stack.callback(patcher.stop)


def finish_installation(name, stack):
    installation_ready(name)
    # Keep the ExitStack lifecycle boundary after readiness. This also makes
    # pre-existing deterministic installers observe a fully active wrapper.
    stack.enter_context(nullcontext())


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
        self.completion_error = None

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
        try:
            try:
                with ownership_change():
                    with self.lock:
                        self._completion = completion
            finally:
                self._complete_if_idle()
        except BaseException as error:
            self.completion_error = type(error).__name__
            raise

    def _complete_if_idle(self):
        completion = None
        try:
            with ownership_change():
                with self.lock:
                    if self.pending == 0 and self._completion is not None:
                        self.closed = True
                        completion, self._completion = self._completion, None
            # Arbitrary observer/report code is NOT shielded. A failed handoff
            # is explicit, never replayed as if an arbitrary callback were pure.
            if completion is not None:
                completion(self)
        except BaseException as error:
            self.completion_error = type(error).__name__
            raise

    @contextmanager
    def stage(self, stage):
        if stage not in STAGES:
            raise ValueError("B03 stage outside finite schema")
        with scoped_value(ACTIVE, (self, stage)):
            yield self

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
    with scoped_value(HASH_PURPOSE, "authentication_sha256"):
        yield


def acquire_job_hold(job, owner):
    """Caller owns the synchronous transition; publish release ownership first."""
    job._b03_owner, job._b03_held = owner, False
    if owner is not None:
        with owner.lock:
            before = owner.pending
            try:
                owner.pending = before + 1
                job._b03_held = True
            except BaseException:
                owner.pending, job._b03_held = before, False
                raise


def release_job_hold(job):
    """Idempotent exact release, independent of ACTIVE and class patch lifetime."""
    owner = getattr(job, "_b03_owner", None)
    if owner is not None:
        with owner.lock:
            before = owner.pending
            was_held = job._b03_held
            try:
                if job._b03_held:
                    if before <= 0:
                        raise RuntimeError("B03 diagnostic hold ownership mismatch")
                    owner.pending = before - 1
                    job._b03_held = False
                job._b03_owner = None
            except BaseException:
                owner.pending, job._b03_held, job._b03_owner = before, was_held, owner
                raise


def settle_job_hold(job):
    """One bounded retry; preserve the first diagnostic failure after recovery."""
    failure = None
    for attempt in range(2):
        try:
            release_job_hold(job)
            break
        except BaseException as error:
            failure = failure or error
            if attempt == 1:
                failure.add_note("B03 diagnostic hold release incomplete")
    if failure is not None:
        raise failure


def settle_finished_job(job):
    if job.finished and job not in job.lease._jobs:
        settle_job_hold(job)


def settle_unregistered_jobs(created, lease, owners):
    with lease.budget._lock:
        for job in created:
            owner = getattr(job, "_b03_owner", None)
            if job not in lease._jobs and owner is not None:
                if owner not in owners:
                    owners.append(owner)
                settle_job_hold(job)


@contextmanager
def instrument_workers():
    """취소된 ASGI가 아니라 실제 기존 native job 종료가 계수 scope를 끝낸다."""
    from isolated_sync.workers import NativeJob, WorkerLease

    with installation("workers") as stack:
        if stack is None:
            yield
            return
        # Acquire this generation's reference before capturing delegates. The
        # prior generation's teardown has finished and this one cannot retire.
        init, finish, run = NativeJob.__init__, NativeJob._finish, WorkerLease.run
        dispatched = ContextVar("b03_dispatch", default=None)

        def owned_init(job, lease):
            owner = None
            try:
                with ownership_change():
                    init(job, lease)
                    active = ACTIVE.get()
                    owner = active[0] if active else None
                    # A live job owns its bound completion even after session
                    # teardown restores NativeJob._finish on the class.
                    job._finish = MethodType(owned_finish, job)
                    created = dispatched.get()
                    if created is not None:
                        if created:
                            raise RuntimeError(
                                "B03 native dispatch job capacity exceeded"
                            )
                        created.append(job)
                    acquire_job_hold(job, owner)
            except BaseException:
                with ownership_change():
                    settle_job_hold(job)
                if owner is not None:
                    owner._complete_if_idle()
                raise

        def owned_finish(job):
            owner = None
            try:
                with ownership_change():
                    owner = getattr(job, "_b03_owner", None)
                    try:
                        finish(job)
                    finally:
                        settle_finished_job(job)
            finally:
                try:
                    # The first cleanup itself may have raised after native
                    # release. This second pass is idempotent and still owned.
                    with ownership_change():
                        settle_finished_job(job)
                finally:
                    if owner is not None:
                        owner._complete_if_idle()

        async def owned_run(lease, function, *args):
            created = []  # 원 run은 NativeJob을 정확히 하나 생성한다.
            token = None
            try:
                with ownership_change():
                    token = dispatched.set(created)
                return await run(lease, function, *args)
            finally:
                owners = []  # Native run constructs one job, not an input queue.
                try:
                    with ownership_change():
                        try:
                            if token is not None:
                                try:
                                    dispatched.reset(token)
                                except BaseException:
                                    # A reset interrupted before taking effect
                                    # still owns this value; an already-used
                                    # token must never be reset a second time.
                                    if dispatched.get() is created:
                                        dispatched.reset(token)
                                    raise
                        finally:
                            settle_unregistered_jobs(created, lease, owners)
                finally:
                    try:
                        with ownership_change():
                            settle_unregistered_jobs(created, lease, owners)
                    finally:
                        for owner in owners:
                            owner._complete_if_idle()

        install_patch(stack, NativeJob, "__init__", owned_init)
        install_patch(stack, NativeJob, "_finish", owned_finish)
        install_patch(stack, WorkerLease, "run", owned_run)
        finish_installation("workers", stack)
        yield


@contextmanager
def instrument():
    """설치/해제는 test session이 소유한다. attribution은 request-local ContextVar다.

    test session 동안 실제 SHA primitive와 canonical global을 감싸므로 late import도
    같은 경계를 지난다. run/stage는 ContextVar이며 process-global current-run은 없다.
    기존 from-import alias만 시작 시 교체하고 종료 시 모두 복원한다.
    """
    with installation("primitives") as stack:
        if stack is None:
            yield
            return
        # Delegate capture belongs to the acquired installation generation,
        # never to the unreferenced interval before activation.
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
        install_patch(stack, canonical, "_parse_json", observed_parse)
        install_patch(stack, canonical, "encode", observed_encode)
        install_patch(stack, hashlib, "sha256", ObservedHash)
        for name, module in list(sys.modules.items()):
            if not name.startswith(("app.", "isolated_sync.")) or module is None:
                continue
            for key, value in list(vars(module).items()):
                if value is NATIVE_HASH:
                    install_patch(stack, module, key, ObservedHash)
                elif value is encode:
                    install_patch(stack, module, key, observed_encode)
        finish_installation("primitives", stack)
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
        self._cost_schema_version = None
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
        # Refresh schema-derived TEMP triggers after DDL. IF NOT EXISTS alone
        # would retain the pre-ALTER NEW-column expressions.
        for table in tuple(self._cost_tables):
            for operation in ("INSERT", "UPDATE", "DELETE"):
                for timing in ("attempted", "effective"):
                    trigger = quote(f"b03_{table}_{operation}_{timing}")
                    native(f"DROP TRIGGER IF EXISTS temp.{trigger}")
        self._cost_tables.clear()
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

    def _cost_ensure_schema(self):
        # One connection-local schema cookie, not cached row/result data. A
        # different connection can commit DDL without passing this wrapper.
        version = super().execute("PRAGMA main.schema_version").fetchone()[0]
        add("observer", "schema_checks")
        if (
            self._cost_schema_version is not None
            and version != self._cost_schema_version
        ):
            # Refreshing an unowned schema can change SQLite's own stale-schema
            # prepare error into success. Reject this measurement before DML.
            add("coverage", "external_schema_change")
            raise RuntimeError("B03 external schema change; measurement incomplete")
        if not self._cost_initialized or version != self._cost_schema_version:
            self._cost_install()
            self._cost_schema_version = version
            self._cost_initialized = True

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
        if verb in {
            "INSERT",
            "UPDATE",
            "DELETE",
            "REPLACE",
        }:
            # Native connect and B01's opened-FD witness have finished first.
            self._cost_ensure_schema()
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
        was_in_transaction = self.in_transaction
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
            if verb in {"CREATE", "ALTER", "DROP", "ROLLBACK"}:
                self._cost_initialized = False
                self._cost_schema_version = None
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
                if was_in_transaction:
                    self._cost_schema_version = None
                self._cost_owners.clear()
                self._cost_savepoints.clear()
                self._cost_initialized = False
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
                self._cost_ensure_schema()
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
                self._cost_schema_version = None
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
        self._cost_schema_version = None

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
            self._cost_schema_version = None
            raise
        self._cost_settle("rolled_back" if args[0] else "committed")
        self._cost_pending.clear()
        self._cost_savepoints.clear()
        self._cost_owners.clear()
        self._cost_initialized = False
        if args[0]:
            self._cost_schema_version = None
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
            install_patch(stack, sqlite3, "connect", connect)
            finish_installation("connections", stack)
        yield


# Fixed code metadata only, not a cache growing with operations or input SQL.
# Both generators have established cleanup before their checkpoint/yield window.
CANCELLABLE_LINES = {
    function.__wrapped__.__code__: frozenset(
        instruction.positions.lineno
        for instruction in dis.get_instructions(function.__wrapped__)
        if instruction.opname == "YIELD_VALUE"
        or (
            instruction.opname in {"LOAD_ATTR", "LOAD_METHOD"}
            and instruction.argval == "checkpoint"
        )
    )
    for function in (scoped_value, installation)
}

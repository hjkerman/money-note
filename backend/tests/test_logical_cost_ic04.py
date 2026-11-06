"""Bounded ownership faults: actual SIGINT, native frames and independent ledgers."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import contextlib
import gc
import importlib.util
import inspect
import os
from pathlib import Path
import random
import signal
import sys
from threading import Event, Lock
from types import ModuleType
from unittest import mock
import weakref

import pytest

from isolated_sync import canonical
from isolated_sync.workers import NativeJob, WorkerBudget, WorkerLease

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cost():
    spec = importlib.util.spec_from_file_location(
        "b03_ic04", ROOT / "docs/benchmarks/t66f-b03/counters.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    native = canonical._parse_json, canonical.encode
    patches = list(mock._patch._active_patches)
    handler = signal.getsignal(signal.SIGINT)
    yield module
    try:
        sys.settrace(None)
        sys.setprofile(None)
        assert not module.INSTALLATIONS
        assert (canonical._parse_json, canonical.encode) == native
        assert list(mock._patch._active_patches) == patches
        assert signal.getsignal(signal.SIGINT) == handler
    finally:
        for patcher in list(reversed(mock._patch._active_patches)):
            if patcher not in patches:
                patcher.stop()


def line_of(function, text, last=False):
    lines, start = inspect.getsourcelines(function)
    hits = [start + i for i, value in enumerate(lines) if text in value]
    assert hits, (function, text)
    return hits[-1] if last else hits[0]


def patch_target(frame):
    patcher = frame.f_locals.get("self")
    return (
        getattr(patcher, "target", None) is canonical
        and getattr(patcher, "attribute", getattr(patcher, "name", None)) == "_parse_json"
    )


def callback_target(frame):
    callback = frame.f_locals.get("callback")
    patcher = getattr(callback, "__self__", None)
    if patcher is None:
        callback = getattr(callback, "__wrapped__", None)
        patcher = getattr(callback, "__self__", None)
    return (
        getattr(patcher, "target", None) is canonical
        and getattr(patcher, "name", None) == "_parse_json"
    )


BOUNDARIES = [
    "before_ref",
    "registry_published",
    "ref_incremented",
    "ref_owned",
    "patch_construct",
    "patch_reserved",
    "patch_applied",
    "patch_committed",
    "stdlib_applied",
    "callback_reserved",
    "before_ready",
    "ready_publish",
    "ready_return",
    "release_decremented",
    "release_owned",
    "restore_begin",
    "patch_stop",
    "stdlib_stop_removed",
    "patch_restored",
    "journal_pop",
    "registry_retire",
    "signal_guard_enter",
    "signal_guard_exit",
]


def boundary(module, name):
    install = module.installation.__wrapped__
    data = {
        "before_ref": (install, "with INSTALL_LOCK:", False),
        "registry_published": (install, 'before = state["refs"]', False),
        "ref_incremented": (install, "held = True", False),
        "ref_owned": (install, "if not first:", False),
        "patch_construct": (module.install_patch, "patcher = RecoveryPatch", False),
        "patch_reserved": (module.install_patch, "patcher.start()", False),
        "patch_applied": (module.install_patch, "stack.callback(patcher.stop)", False),
        "patch_committed": (module.install_patch, None, False),
        "stdlib_applied": (mock._patch.start, "self._active_patches.append", False),
        "callback_reserved": (contextlib._BaseExitStack.callback, "return callback", False),
        "before_ready": (module.installation_ready, 'state["status"] = "ACTIVE"', False),
        "ready_publish": (module.installation_ready, 'state["ready"].set()', False),
        "ready_return": (module.installation_ready, None, False),
        "release_decremented": (install, "held = False", False),
        "release_owned": (install, 'if state["refs"] == 0:', True),
        "restore_begin": (install, 'state["stack"].close()', False),
        "patch_stop": (module.RecoveryPatch.stop, "self.inner.stop()", False),
        "stdlib_stop_removed": (mock._patch.stop, "return self.__exit__", False),
        "patch_restored": (module.RecoveryPatch.stop, None, False),
        "journal_pop": (module.RecoveryStack.close, "self.inner._exit_callbacks.pop()", False),
        "registry_retire": (install, "del INSTALLATIONS[name]", True),
        "signal_guard_enter": (module.ownership_change.__wrapped__, "yield", True),
        "signal_guard_exit": (module.ownership_change.__wrapped__, "if pending:", False),
    }
    function, anchor, last = data[name]
    position = line_of(function, anchor, last) if anchor else None
    return function.__code__, position


@pytest.mark.parametrize("point", BOUNDARIES)
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_all_installation_transitions_recover_exact_events(cost, point, failure):
    native = canonical._parse_json
    code, position = boundary(cost, point)
    patches = list(mock._patch._active_patches)
    seen, fired = [], []
    body = []
    collector = cost.Collector()

    def trace(frame, event, _):
        if event == "call" and frame.f_code is native.__code__:
            seen.append(bytes(frame.f_locals["raw"]))
        selected = frame.f_code is code and (
            (position is None and event == "return")
            or (event == "line" and frame.f_lineno == position)
        )
        if point in {"stdlib_applied", "stdlib_stop_removed", "patch_stop", "patch_restored"}:
            selected = selected and patch_target(frame)
        if point in {"callback_reserved", "journal_pop"}:
            selected = selected and callback_target(frame)
        if point.startswith("patch_") and frame.f_code is cost.install_patch.__code__:
            selected = (
                selected
                and frame.f_locals.get("target") is canonical
                and frame.f_locals.get("name") == "_parse_json"
            )
        if selected and not fired:
            fired.append(point)
            if failure == "SIGINT":
                signal.raise_signal(signal.SIGINT)
            else:
                raise RuntimeError("IC04 injected transition failure")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
            with cost.instrument(), collector.stage("transfer"):
                body.append(True)
                canonical.decode_c1(b"{}")
                canonical.decode_c1(b"{}")
    finally:
        sys.settrace(None)
    assert fired == [point]
    assert seen == [b"{}", b"{}"] * len(body)
    assert collector.values["transfer/json/calls"] == len(seen)
    assert collector.values["transfer/json/submitted_bytes"] == 2 * len(seen)
    assert canonical._parse_json is native and not cost.INSTALLATIONS
    assert list(mock._patch._active_patches) == patches
    fresh = cost.Collector()
    with cost.instrument(), fresh.stage("observation"):
        canonical.decode_c1('"한😀"'.encode())
    assert fresh.values["observation/json/calls"] == 1
    assert fresh.values["observation/json/submitted_bytes"] == len('"한😀"'.encode())


@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_late_import_alias_cleanup_is_reserved_before_publication(cost, failure):
    native = canonical.encode
    module = ModuleType("app.ic04_late_alias")
    sys.modules[module.__name__] = module
    context = cost.instrument()
    context.__enter__()
    module.encode = canonical.encode
    fired = []

    def trace(frame, event, _):
        if (
            event == "line"
            and frame.f_code.co_name == "restore_aliases"
            and frame.f_locals.get("module") is module
            and module.encode is not native
            and not fired
        ):
            fired.append(True)
            if failure == "SIGINT":
                signal.raise_signal(signal.SIGINT)
            else:
                raise RuntimeError("IC04 alias restoration")
        return trace

    try:
        sys.settrace(trace)
        with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
            context.__exit__(None, None, None)
    finally:
        sys.settrace(None)
        sys.modules.pop(module.__name__)
    assert fired and module.encode is native
    assert not cost.INSTALLATIONS


def test_persistent_cleanup_failure_is_bounded_and_next_activation_recovers(cost, monkeypatch):
    native = canonical._parse_json
    context = cost.instrument()
    context.__enter__()
    original = cost.RecoveryPatch.stop

    def broken(patcher):
        if patcher.target is canonical and patcher.name == "_parse_json":
            raise RuntimeError("IC04 persistent restoration fault")
        original(patcher)

    with monkeypatch.context() as scope:
        scope.setattr(cost.RecoveryPatch, "stop", broken)
        # Registered bound methods predate monkeypatch; replace the actual
        # native stop delegate instead, preserving the recovery journal entry.
        for _, callback in cost.INSTALLATIONS["primitives"]["stack"].inner._exit_callbacks:
            patcher = getattr(getattr(callback, "__wrapped__", None), "__self__", None)
            if isinstance(patcher, cost.RecoveryPatch) and patcher.name == "_parse_json":
                scope.setattr(
                    patcher.inner,
                    "stop",
                    lambda: (_ for _ in ()).throw(
                        RuntimeError("IC04 persistent restoration fault")
                    ),
                )
                scope.setattr(
                    patcher,
                    "stop",
                    lambda: (_ for _ in ()).throw(RuntimeError("unused bound method")),
                )
                # The fallback restores the callable even though mock handle
                # removal fails; it remains owned until an honest retry.
        with pytest.raises(RuntimeError, match="persistent"):
            context.__exit__(None, None, None)
        state = cost.INSTALLATIONS["primitives"]
        assert state["refs"] == 0 and state["status"] == "RECOVERING"
        pending = len(state["stack"].inner._exit_callbacks)
        for _ in range(8):
            with pytest.raises(RuntimeError):
                with cost.instrument():
                    pytest.fail("incomplete recovery must not activate")
            assert len(cost.INSTALLATIONS) == 1
            assert len(state["stack"].inner._exit_callbacks) == pending
    c = cost.Collector()
    with cost.instrument(), c.stage("transfer"):
        canonical.decode_c1(b"{}")
    assert canonical._parse_json is native and c.values["transfer/json/calls"] == 1


def test_patch_capacity_rejection_is_before_unowned_mutation(cost, monkeypatch):
    monkeypatch.setattr(cost, "PATCH_LIMIT", 2)
    with pytest.raises(RuntimeError, match="capacity"):
        with cost.instrument():
            pytest.fail("partial instrumentation must not run")
    assert not cost.INSTALLATIONS


HOLD_POINTS = [
    "before_hold",
    "hold_incremented",
    "hold_owned",
    "release_begin",
    "release_decremented",
    "release_owned",
]


@pytest.mark.parametrize("point", HOLD_POINTS)
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_native_hold_transitions_match_actual_native_budget(cost, point, failure):
    collector = cost.Collector()
    budget = WorkerBudget(1)
    lease = budget.acquire()
    native = NativeJob.__init__
    seen, fired = [], []
    acquiring = point.startswith("hold") or point == "before_hold"
    function = cost.acquire_job_hold if acquiring else cost.release_job_hold
    anchors = {
        "before_hold": "job._b03_owner, job._b03_held",
        "hold_incremented": "job._b03_held = True",
        "hold_owned": None,
        "release_begin": "owner = getattr",
        "release_decremented": "job._b03_held = False",
        "release_owned": "job._b03_owner = None",
    }
    position = line_of(function, anchors[point]) if anchors[point] else None

    def trace(frame, event, _):
        if event == "call" and frame.f_code is native.__code__:
            seen.append(1)
        if (
            frame.f_code is function.__code__
            and not fired
            and (
                (position is None and event == "return")
                or (position is not None and event == "line" and frame.f_lineno == position)
            )
        ):
            fired.append(point)
            if failure == "SIGINT":
                signal.raise_signal(signal.SIGINT)
            else:
                raise RuntimeError("IC04 hold transition")
        return trace

    # A queued job cancelled before native start uses the real settled(None)
    # cleanup on the event-loop/main thread. No financial function is executed.
    sys.settrace(trace)
    try:
        with cost.instrument_workers(), collector.stage("transfer"):
            with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
                job = NativeJob(lease)
                with budget._lock:
                    lease._jobs.add(job)
                lease.close()
                job.settled(None)
    finally:
        sys.settrace(None)
        lease.close()
    assert fired == [point] and seen == [1]
    completions = []
    collector.finish_when_idle(completions.append)
    assert collector.pending == 0 and collector.closed and completions == [collector]
    assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)


def test_live_native_tail_owns_hold_after_session_teardown(cost):
    collector = cost.Collector()
    entered, resume = Event(), Event()
    budget = WorkerBudget(1)
    lease = budget.acquire()

    def native(cancelled):
        entered.set()
        assert resume.wait(10)
        return 17

    async def run():
        with cost.instrument_workers(), collector.stage("transfer"):
            task = asyncio.create_task(lease.run(native, lease.cancelled))
            assert await asyncio.to_thread(entered.wait, 10)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            lease.close()
        assert not cost.INSTALLATIONS
        assert collector.pending == 1
        finished = asyncio.Event()
        loop = asyncio.get_running_loop()
        collector.finish_when_idle(lambda _: loop.call_soon_threadsafe(finished.set))
        assert not collector.closed
        resume.set()
        await asyncio.wait_for(finished.wait(), 10)

    try:
        asyncio.run(run())
    finally:
        resume.set()
        lease.close()
    assert collector.pending == 0 and collector.closed
    assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)


@pytest.mark.parametrize(
    "point",
    [
        "native_init_done",
        "instance_finish_bound",
        "native_finish_done",
        "finished_cleanup_entry",
        "hold_cleanup_done",
    ],
)
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_native_completion_ownership_transfers_are_exception_safe(cost, point, failure):
    c = cost.Collector()
    budget = WorkerBudget(1)
    lease = budget.acquire()
    native_init, native_finish = NativeJob.__init__, NativeJob._finish
    fired, seen = [], []
    with cost.instrument_workers(), c.stage("transfer"):
        init = NativeJob.__init__
        if point == "native_init_done":
            code, position = native_init.__code__, None
        elif point == "instance_finish_bound":
            code, position = init.__code__, line_of(init, "created = dispatched.get()")
        elif point == "native_finish_done":
            code, position = native_finish.__code__, None
        elif point == "finished_cleanup_entry":
            code, position = (
                cost.settle_finished_job.__code__,
                line_of(cost.settle_finished_job, "if job.finished"),
            )
        else:
            code, position = cost.settle_job_hold.__code__, None

        def trace(frame, event, _):
            if event == "call" and frame.f_code is native_init.__code__:
                seen.append(1)
            selected = frame.f_code is code and (
                (position is None and event == "return")
                or (event == "line" and frame.f_lineno == position)
            )
            if selected and not fired:
                fired.append(point)
                if failure == "SIGINT":
                    signal.raise_signal(signal.SIGINT)
                else:
                    raise RuntimeError("IC04 native transfer")
            return trace

        sys.settrace(trace)
        try:
            with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
                job = NativeJob(lease)
                with budget._lock:
                    lease._jobs.add(job)
                lease.close()
                job.settled(None)
        finally:
            sys.settrace(None)
            lease.close()
    assert fired and seen == [1]
    done = []
    c.finish_when_idle(done.append)
    assert c.pending == 0 and c.closed and done == [c]
    assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)


DISPATCH_CASES = [
    (point, rejected)
    for point in [
        "context_before",
        "context_after",
        "context_reset_before",
        "context_reset_after",
        "job_tracked",
        "unregistered_cleanup",
    ]
    for rejected in [False, True]
    if point != "unregistered_cleanup" or rejected
]


@pytest.mark.parametrize("point,rejected", DISPATCH_CASES)
@pytest.mark.parametrize("failure", ["exception", "Task.cancel", "SIGINT"])
def test_dispatch_context_and_unregistered_job_cleanup(cost, point, rejected, failure):
    c = cost.Collector()
    native_init = NativeJob.__init__
    budget = WorkerBudget(1)
    lease = budget.acquire()
    fired, seen, caught = [], [], []

    async def run():
        with cost.instrument_workers(), c.stage("transfer"):
            owned_run, owned_init = WorkerLease.run, NativeJob.__init__
            dispatch_scope = inspect.getclosurevars(owned_run).nonlocals["dispatch_scope"]
            dispatch_function = dispatch_scope.__wrapped__
            dispatched = inspect.getclosurevars(dispatch_function).nonlocals["dispatched"]
            previous = dispatched.get()
            functions = {
                "context_before": (dispatch_function, "token = dispatched.set(created)"),
                "context_after": (dispatch_function, "yield"),
                "context_reset_before": (dispatch_function, "dispatched.reset(token)"),
                "context_reset_after": (
                    dispatch_function,
                    "settle_unregistered_jobs(created, lease, owners)",
                ),
                "job_tracked": (owned_init, "acquire_job_hold(job, owner)"),
                "unregistered_cleanup": (cost.settle_unregistered_jobs, "settle_job_hold(job)"),
            }
            function, anchor = functions[point]
            position = line_of(function, anchor)
            main_task = asyncio.current_task()

            def trace(frame, event, _):
                if event == "call" and frame.f_code is native_init.__code__:
                    seen.append(1)
                if (
                    event == "line"
                    and frame.f_code is function.__code__
                    and frame.f_lineno == position
                    and not fired
                ):
                    if point == "job_tracked":
                        assert dispatched.get() == [frame.f_locals["job"]]
                    fired.append(point)
                    if failure == "SIGINT":
                        signal.raise_signal(signal.SIGINT)
                    elif failure == "Task.cancel":
                        main_task.cancel()
                    else:
                        raise RuntimeError("IC04 dispatch transition")
                return trace

            if rejected:
                lease.close()
            sys.settrace(trace)
            try:
                try:
                    await lease.run(lambda: 17)
                except (RuntimeError, asyncio.CancelledError):
                    caught.append(True)
            finally:
                sys.settrace(None)
                lease.close()
            # Cancellation requested in synchronous finally is delivered at
            # the next real await, rather than invented at a dictionary write.
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                caught.append(True)
            assert dispatched.get() is previous
            finished = asyncio.Event()
            loop = asyncio.get_running_loop()
            c.finish_when_idle(lambda _: loop.call_soon_threadsafe(finished.set))
            await asyncio.wait_for(finished.wait(), 10)
            assert c.pending == 0 and c.closed

    asyncio.run(run())
    assert fired and caught
    expected = 0 if failure == "exception" and point in {"context_before", "context_after"} else 1
    assert len(seen) == expected
    assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)


@pytest.mark.parametrize("seed", [4104, 907])
def test_stateful_bounded_reference_parse_cancel_sequences(cost, seed):
    rng = random.Random(seed)
    native = canonical._parse_json
    refs = []
    scope = cost.Collector()
    expected = []
    weak = []
    actual = []
    native_jobs, expected_jobs = [], 0
    native_init = NativeJob.__init__

    def profile(frame, event, _):
        if event == "call" and frame.f_code is native.__code__:
            actual.append(bytes(frame.f_locals["raw"]))
        if event == "call" and frame.f_code is native_init.__code__:
            native_jobs.append(1)

    sys.setprofile(profile)
    with scope.stage("calibration"):
        for _ in range(400):
            choices = (
                ["acquire", "abort_setup"]
                if not refs
                else ["parse", "parse", "release", "close", "acquire", "native"]
            )
            action = rng.choice(choices)
            if action == "acquire" and len(refs) < 5:
                context = cost.instrument()
                context.__enter__()
                refs.append(context)
                weak.append(weakref.ref(canonical._parse_json))
            elif action == "parse":
                payload = rng.choice([b"{}", b"{}", b"[1,2]", '"한😀"'.encode()])
                canonical.decode_c1(payload)
                expected.append(payload)
            elif action in {"release", "close"} and refs:
                context = refs.pop(rng.randrange(len(refs)))
                if action == "close":
                    context.__exit__(asyncio.CancelledError, asyncio.CancelledError(), None)
                else:
                    context.__exit__(None, None, None)
            elif action == "abort_setup":
                fired = []
                seam = line_of(cost.install_patch, "stack.callback(patcher.stop)")

                def interrupt(frame, event, _):
                    if (
                        event == "line"
                        and frame.f_code is cost.install_patch.__code__
                        and frame.f_lineno == seam
                        and not fired
                    ):
                        fired.append(True)
                        signal.raise_signal(signal.SIGINT)
                    return interrupt

                sys.settrace(interrupt)
                try:
                    with pytest.raises(KeyboardInterrupt):
                        with cost.instrument():
                            pytest.fail("aborted model activation must not parse")
                finally:
                    sys.settrace(None)
                assert fired
            elif action == "native":
                with cost.instrument_workers():
                    budget = WorkerBudget(1)
                    lease = budget.acquire()
                    job = NativeJob(lease)
                    with budget._lock:
                        lease._jobs.add(job)
                    assert scope.pending == 1
                    lease.close()
                    job.settled(None)
                    assert scope.pending == 0
                    assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)
                    expected_jobs += 1
            if refs:
                assert cost.INSTALLATIONS["primitives"]["refs"] == len(refs)
                assert canonical._parse_json.__wrapped__ is native
            else:
                assert canonical._parse_json is native and not cost.INSTALLATIONS
        while refs:
            refs.pop().__exit__(None, None, None)
    sys.setprofile(None)
    assert actual == expected and len(native_jobs) == expected_jobs
    assert scope.values["calibration/json/calls"] == len(expected)
    assert scope.values["calibration/json/submitted_bytes"] == sum(map(len, expected))
    gc.collect()
    assert not any(w() for w in weak)


def test_completion_callback_failure_is_explicit_and_not_replayed(cost):
    collector = cost.Collector()
    calls = []

    def fail(value):
        calls.append(value)
        raise RuntimeError("IC04 report callback failed")

    with pytest.raises(RuntimeError, match="report callback"):
        collector.finish_when_idle(fail)
    assert calls == [collector] and collector.pending == 0 and collector.closed
    assert collector.completion_error == "RuntimeError"
    collector._complete_if_idle()
    assert calls == [collector]


@pytest.mark.parametrize(
    "point", ["registration_before", "registration_after", "handoff_after", "callback_before"]
)
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_completion_handoff_cancellation_is_visible_not_false_complete(cost, point, failure):
    collector = cost.Collector()
    fired, calls = [], []
    if point == "registration_before":
        function, anchor = cost.Collector.finish_when_idle, "self._completion = completion"
    elif point == "registration_after":
        function, anchor = cost.Collector.finish_when_idle, "self._complete_if_idle()"
    elif point == "handoff_after":
        function, anchor = cost.Collector._complete_if_idle, "if completion is not None:"
    else:
        function, anchor = cost.Collector._complete_if_idle, "completion(self)"
    position = line_of(function, anchor)

    def trace(frame, event, _):
        if (
            event == "line"
            and frame.f_code is function.__code__
            and frame.f_lineno == position
            and not fired
        ):
            fired.append(point)
            if failure == "SIGINT":
                signal.raise_signal(signal.SIGINT)
            else:
                raise RuntimeError("IC04 completion handoff")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
            collector.finish_when_idle(calls.append)
    finally:
        sys.settrace(None)
    assert fired and collector.pending == 0
    assert collector.completion_error in {"RuntimeError", "KeyboardInterrupt"}
    assert len(calls) <= 1
    # An external report callback is not replayed speculatively. If it was
    # still registered, this explicit retry can execute it exactly once.
    collector._complete_if_idle()
    assert len(calls) == (
        0
        if point in {"handoff_after", "callback_before"}
        or (point == "registration_before" and failure == "exception")
        else 1
    )


@pytest.mark.parametrize("waiters", [1, 3])
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_failed_first_publication_wakes_all_waiters_without_events(cost, waiters, failure):
    patch_ready, all_waiting = Event(), Event()
    lock = Lock()
    waiting, fired = [], []
    collectors = [cost.Collector() for _ in range(waiters)]
    seam = line_of(cost.install_patch, "stack.callback(patcher.stop)")

    def waiter(index):
        assert patch_ready.wait(10)

        def trace(frame, event, _):
            if event == "call" and frame.f_code is cost.wait_for_installation.__code__:
                with lock:
                    waiting.append(index)
                    if len(waiting) == waiters:
                        all_waiting.set()
            return trace

        sys.settrace(trace)
        try:
            with pytest.raises(RuntimeError, match="installation failed"):
                with cost.instrument(), collectors[index].stage("transfer"):
                    pytest.fail("rejected waiter must not execute")
        finally:
            sys.settrace(None)

    def interrupt(frame, event, _):
        if (
            event == "line"
            and frame.f_code is cost.install_patch.__code__
            and frame.f_lineno == seam
            and frame.f_locals.get("target") is canonical
            and frame.f_locals.get("name") == "_parse_json"
            and not fired
        ):
            fired.append(True)
            patch_ready.set()
            assert all_waiting.wait(10)
            assert cost.INSTALLATIONS["primitives"]["refs"] == waiters + 1
            if failure == "SIGINT":
                signal.raise_signal(signal.SIGINT)
            else:
                raise RuntimeError("IC04 first publication failed")
        return interrupt

    with ThreadPoolExecutor(waiters) as pool:
        futures = [pool.submit(waiter, i) for i in range(waiters)]
        sys.settrace(interrupt)
        try:
            with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
                with cost.instrument():
                    pytest.fail("cancelled first scope must not execute")
        finally:
            sys.settrace(None)
            patch_ready.set()
        for future in futures:
            future.result(timeout=15)
    assert fired and not cost.INSTALLATIONS
    assert all(c.snapshot() == {} for c in collectors)


@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_cancelled_teardown_cannot_retire_a_new_recovered_generation(cost, monkeypatch, failure):
    native = canonical._parse_json
    old = cost.instrument()
    old.__enter__()
    state = cost.INSTALLATIONS["primitives"]
    restoration, attempted, opened, resume = Event(), Event(), Event(), Event()
    collector = cost.Collector()
    seen, fired = [], []
    install = cost.installation.__wrapped__
    close_line = line_of(install, 'state["stack"].close()')
    acquire_line = line_of(install, "with INSTALL_LOCK:")
    retry_line = line_of(install, "cleanup_error = cleanup_error or error")
    actual_close = state["stack"].close

    def fail_close_once():
        if not fired:
            fired.append(True)
            restoration.set()
            assert attempted.wait(10)
            raise RuntimeError("IC04 teardown callback failure")
        actual_close()

    if failure == "exception":
        monkeypatch.setattr(state["stack"], "close", fail_close_once)

    def next_generation():
        assert restoration.wait(10)

        def trace(frame, event, _):
            if (
                event == "line"
                and frame.f_code is install.__code__
                and frame.f_lineno == acquire_line
            ):
                attempted.set()
            if event == "call" and frame.f_code is native.__code__:
                seen.append(bytes(frame.f_locals["raw"]))
            return trace

        sys.settrace(trace)
        try:
            with cost.instrument(), collector.stage("observation"):
                assert cost.INSTALLATIONS["primitives"] is not state
                assert canonical._parse_json.__wrapped__ is native
                opened.set()
                assert resume.wait(10)
                canonical.decode_c1(b"{}")
                canonical.decode_c1(b"{}")
        finally:
            sys.settrace(None)

    def trace(frame, event, _):
        if event == "line" and frame.f_code is install.__code__:
            if failure == "SIGINT" and frame.f_lineno == close_line and not fired:
                fired.append(True)
                restoration.set()
                assert attempted.wait(10)
                signal.raise_signal(signal.SIGINT)
            if frame.f_lineno == retry_line:
                assert opened.wait(10)
        return trace

    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(next_generation)
        sys.settrace(trace)
        try:
            with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
                old.__exit__(None, None, None)
            assert opened.wait(10)
            assert canonical._parse_json.__wrapped__ is native
            assert cost.INSTALLATIONS["primitives"]["refs"] == 1
        finally:
            sys.settrace(None)
            resume.set()
        future.result(timeout=15)
    assert seen == [b"{}", b"{}"]
    assert collector.values["observation/json/calls"] == 2
    assert collector.values["observation/json/submitted_bytes"] == 4


@pytest.mark.parametrize("kind", ["stage", "hash_purpose"])
@pytest.mark.parametrize(
    "point", ["before_set", "after_set", "cleanup_entry", "before_reset", "after_reset"]
)
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_scoped_context_registration_and_reset_have_no_ownership_gap(cost, kind, point, failure):
    variable = cost.ACTIVE if kind == "stage" else cost.HASH_PURPOSE
    missing = object()
    previous = variable.get(missing)
    scope = cost.Collector()
    fired, body = [], []
    function = cost.scoped_value.__wrapped__
    anchors = {
        "before_set": "token = variable.set(value)",
        "after_set": "yield",
        "cleanup_entry": "if token is not None:",
        "before_reset": "variable.reset(token)",
        "after_reset": "reset_done = True",
    }
    position = line_of(function, anchors[point])

    def trace(frame, event, _):
        if (
            event == "line"
            and frame.f_code is function.__code__
            and frame.f_lineno == position
            and frame.f_locals.get("variable") is variable
            and not fired
        ):
            fired.append(point)
            if failure == "SIGINT":
                signal.raise_signal(signal.SIGINT)
            else:
                raise RuntimeError("IC04 scoped context ownership")
        return trace

    with cost.instrument():
        outer = scope.stage("transfer") if kind == "hash_purpose" else contextlib.nullcontext()
        with outer:
            context = scope.stage("transfer") if kind == "stage" else cost.authentication_hashes()
            sys.settrace(trace)
            try:
                with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
                    with context:
                        body.append(True)
                        if kind == "stage":
                            canonical.decode_c1(b"{}")
                        else:
                            cost.hashlib.sha256(b"abcd")
            finally:
                sys.settrace(None)
            assert fired == [point]
            assert variable.get(missing) is previous
    key = "transfer/json/calls" if kind == "stage" else "transfer/authentication_sha256/calls"
    assert scope.values[key] == len(body)
    if kind == "stage":
        assert scope.values["transfer/json/submitted_bytes"] == len(body) * 2
    else:
        assert scope.values["transfer/authentication_sha256/hash_input_bytes"] == len(body) * 4


def test_generator_contexts_out_of_order_restore_original_handler(cost):
    original = signal.getsignal(signal.SIGINT)
    contexts = []
    for _ in range(128):
        context = cost.instrument()
        context.__enter__()
        contexts.append(context)
        assert signal.getsignal(signal.SIGINT) is original
    for context in contexts[::2] + contexts[1::2]:
        context.__exit__(None, None, None)
        assert signal.getsignal(signal.SIGINT) is original
    assert not cost.INSTALLATIONS


def test_signal_during_user_body_is_immediate_and_not_deferred_to_scope_end(cost):
    c = cost.Collector()
    entered = []
    with cost.instrument(), c.stage("transfer"):
        with pytest.raises(KeyboardInterrupt):
            signal.raise_signal(signal.SIGINT)
            entered.append(True)
        canonical.decode_c1(b"{}")
    assert not entered and c.values["transfer/json/calls"] == 1


@pytest.mark.parametrize("point", ["enter_before", "enter_after", "exit_before", "exit_after"])
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_generator_resume_and_retirement_are_transactional(cost, point, failure):
    method = (
        cost.OwnershipContext.__enter__
        if point.startswith("enter")
        else cost.OwnershipContext.__exit__
    )
    anchor = (
        "result = self.inner.__enter__()"
        if point.startswith("enter")
        else "return self.inner.__exit__(*error)"
    )
    code, position = method.__code__, line_of(method, anchor)
    c, fired = cost.Collector(), []
    if point.endswith("after"):
        code = (
            contextlib._GeneratorContextManager.__enter__.__code__
            if point.startswith("enter")
            else contextlib._GeneratorContextManager.__exit__.__code__
        )
        position = None

    def trace(frame, event, _):
        selected = frame.f_code is code and (
            (position is None and event == "return")
            or (event == "line" and frame.f_lineno == position)
        )
        if point.endswith("after"):
            owner = frame.f_locals.get("self")
            selected = (
                selected
                and getattr(getattr(owner, "gen", None), "gi_code", None)
                is cost.instrument.__wrapped__.__code__
            )
        if selected and not fired:
            fired.append(point)
            if failure == "SIGINT":
                signal.raise_signal(signal.SIGINT)
            else:
                raise RuntimeError("IC04 generator resume")
        return trace

    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
            with cost.instrument(), c.stage("transfer"):
                canonical.decode_c1(b"{}")
    finally:
        sys.settrace(None)
    assert fired and not cost.INSTALLATIONS
    with cost.instrument(), cost.Collector().stage("generation"):
        canonical.decode_c1(b"{}")


def test_main_thread_waiter_remains_cancellable_while_owner_is_paused(cost):
    paused, release, waiting = Event(), Event(), Event()
    first = cost.Collector()
    install = cost.install_patch

    def owner():
        def trace(frame, event, _):
            if (
                event == "call"
                and frame.f_code is install.__code__
                and frame.f_locals.get("name") == "_parse_json"
            ):
                paused.set()
                assert release.wait(10)
            return trace

        sys.settrace(trace)
        try:
            with cost.instrument(), first.stage("transfer"):
                canonical.decode_c1(b"{}")
        finally:
            sys.settrace(None)

    def emit():
        assert waiting.wait(10)
        os.kill(os.getpid(), signal.SIGINT)

    def observe_wait(frame, event, _):
        if event == "call" and frame.f_code is cost.wait_for_installation.__code__:
            waiting.set()
        return observe_wait

    with ThreadPoolExecutor(2) as pool:
        worker = pool.submit(owner)
        assert paused.wait(10)
        signaler = pool.submit(emit)
        sys.settrace(observe_wait)
        try:
            with pytest.raises(KeyboardInterrupt):
                with cost.instrument():
                    pytest.fail("cancelled waiter must not activate")
            assert not worker.done()
        finally:
            sys.settrace(None)
            release.set()
        worker.result(timeout=15)
        signaler.result(timeout=15)
    assert first.values["transfer/json/calls"] == 1


def test_nested_identical_hash_purpose_and_no_retired_signal_owners(cost):
    c = cost.Collector()
    with cost.instrument(), c.stage("transfer"):
        with cost.authentication_hashes(), cost.authentication_hashes():
            cost.hashlib.sha256(b"a")
        cost.hashlib.sha256(b"b")
    assert c.values["transfer/authentication_sha256/hash_input_bytes"] == 1
    assert c.values["transfer/sha256/hash_input_bytes"] == 1
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


@pytest.mark.parametrize("kind", ["installation", "stage", "hash_purpose"])
@pytest.mark.parametrize("point", ["yield", "after_yield"])
def test_pending_signal_never_enters_suspended_user_body(cost, kind, point):
    collector = cost.Collector()
    function = (
        cost.installation.__wrapped__ if kind == "installation" else cost.scoped_value.__wrapped__
    )
    anchor = "yield"
    position = line_of(function, anchor)
    fired, body = [], []
    context = (
        cost.instrument()
        if kind == "installation"
        else (collector.stage("transfer") if kind == "stage" else cost.authentication_hashes())
    )

    def trace(frame, event, _):
        if (
            frame.f_code is function.__code__
            and (
                (point == "yield" and event == "line" and frame.f_lineno == position)
                or (point == "after_yield" and event == "return")
            )
            and not fired
        ):
            fired.append(True)
            signal.raise_signal(signal.SIGINT)
        return trace

    previous = cost.ACTIVE.get(), cost.HASH_PURPOSE.get()
    sys.settrace(trace)
    try:
        with pytest.raises(KeyboardInterrupt):
            with context:
                body.append(True)
                canonical.decode_c1(b"{}")
    finally:
        sys.settrace(None)
    assert fired and not body
    assert not cost.INSTALLATIONS
    assert (cost.ACTIVE.get(), cost.HASH_PURPOSE.get()) == previous
    assert collector.snapshot() == {}
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


@pytest.mark.parametrize("family", ["instrument", "instrument_workers", "instrument_connections"])
def test_main_origin_context_can_close_on_worker_without_process_handler_retention(cost, family):
    native = signal.getsignal(signal.SIGINT)
    context = getattr(cost, family)()
    context.__enter__()
    assert signal.getsignal(signal.SIGINT) is native
    with ThreadPoolExecutor(1) as pool:
        pool.submit(context.__exit__, None, None, None).result(timeout=10)
    assert signal.getsignal(signal.SIGINT) is native
    assert not cost.INSTALLATIONS


def test_observer_outside_asyncio_runner_preserves_native_SIGINT_cancellation(cost):
    native = signal.getsignal(signal.SIGINT)
    c = cost.Collector()
    ran, cancelled = [], []

    async def run():
        ran.append(True)
        assert signal.getsignal(signal.SIGINT) is not native
        signal.raise_signal(signal.SIGINT)
        with pytest.raises(asyncio.CancelledError):
            await asyncio.sleep(0)
        cancelled.append(True)

    with cost.instrument(), cost.instrument_workers(), c.stage("transfer"):
        assert signal.getsignal(signal.SIGINT) is native is signal.default_int_handler
        asyncio.run(run())
        assert signal.getsignal(signal.SIGINT) is native
    assert ran and cancelled


def test_context_decorator_recreates_independent_owned_generations(cost):
    c = cost.Collector()

    @cost.instrument()
    def parse():
        with c.stage("generation"):
            return canonical.decode_c1(b"{}")

    assert parse() == parse() == {}
    assert c.values["generation/json/calls"] == 2
    assert c.values["generation/json/submitted_bytes"] == 4


@pytest.mark.parametrize("family", ["instrument", "instrument_workers", "stage"])
def test_cancelled_outer_enter_return_transfers_no_unowned_reference_or_stage(cost, family):
    """Actual SIGINT after enter returns, before caller registers WITH cleanup."""
    import json

    output = Path(__file__).resolve().parents[2] / "docs/benchmarks/t66f-b03-ic04/evidence"
    c, fired, body, actual = cost.Collector(), [], [], []
    native = canonical._parse_json
    outer = cost.instrument() if family == "stage" else contextlib.nullcontext()
    with outer:
        previous = cost.ACTIVE.get()
        baseline = {key: value["refs"] for key, value in cost.INSTALLATIONS.items()}
        target = canonical._parse_json if family == "instrument" else NativeJob.__init__
        context = c.stage("transfer") if family == "stage" else getattr(cost, family)()

        def trace(frame, event, _):
            if (
                event == "return"
                and frame.f_code is cost.OwnershipContext.__enter__.__code__
                and frame.f_locals.get("self") is context
                and not fired
            ):
                fired.append(True)
                signal.raise_signal(signal.SIGINT)
            return trace

        try:
            sys.settrace(trace)
            try:
                with pytest.raises(KeyboardInterrupt):
                    with context:
                        body.append(True)
            finally:
                sys.settrace(None)
            refs = {key: value["refs"] for key, value in cost.INSTALLATIONS.items()}
            binding_restored = cost.ACTIVE.get() is previous
            callable_restored = (
                canonical._parse_json is target
                if family == "instrument"
                else NativeJob.__init__ is target
            )
            if family == "stage":

                def profile(frame, event, _):
                    if event == "call" and frame.f_code is native.__code__:
                        actual.append(bytes(frame.f_locals["raw"]))

                sys.setprofile(profile)
                try:
                    assert canonical.decode_c1(b"{}") == {}
                finally:
                    sys.setprofile(None)
            result = {
                "family": family,
                "actual_SIGINT_fired": bool(fired),
                "user_body_executions": len(body),
                "baseline_references": baseline,
                "actual_references": refs,
                "context_binding_restored": binding_restored,
                "callable_restored": callable_restored,
                "native_inputs_hex": [x.hex() for x in actual],
                "events_charged_to_cancelled_stage": c.values["transfer/json/calls"],
                "bytes_charged_to_cancelled_stage": c.values["transfer/json/submitted_bytes"],
                "expected_cancelled_stage_events": 0,
                "expected_cancelled_stage_bytes": 0,
                "native_hold_count": c.pending,
            }
            output.mkdir(parents=True, exist_ok=True)
            (output / ("outer-enter-return-" + family + ".json")).write_text(
                json.dumps(result, indent=2) + "\n"
            )
            assert fired and not body
            assert refs == baseline, result
            assert binding_restored, result
            assert callable_restored, result
            assert c.values["transfer/json/calls"] == 0, result
        finally:
            # Preserve the failed oracle; explicit manual recovery is not PASS.
            context.close()

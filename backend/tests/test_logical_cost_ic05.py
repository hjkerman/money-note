"""Entry ownership oracles: original observers execute, cancelled owners don't."""

import asyncio
from contextlib import ExitStack
import gc
import importlib.util
import inspect
from pathlib import Path
import signal
import sys
from unittest.mock import _patch
import weakref

import pytest

from isolated_sync import canonical
from isolated_sync.workers import NativeJob, WorkerBudget

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cost():
    spec = importlib.util.spec_from_file_location(
        "ic05_subject", ROOT / "docs/benchmarks/t66f-b03/counters.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    native = canonical._parse_json, canonical.encode, NativeJob.__init__, NativeJob._finish
    hooks = sys.gettrace(), sys.getprofile(), signal.getsignal(signal.SIGINT)
    patches = list(_patch._active_patches)
    yield module
    assert not module.INSTALLATIONS and module.ACTIVE.get() is None
    assert (
        canonical._parse_json,
        canonical.encode,
        NativeJob.__init__,
        NativeJob._finish,
    ) == native
    assert (sys.gettrace(), sys.getprofile(), signal.getsignal(signal.SIGINT)) == hooks
    assert list(_patch._active_patches) == patches


def fail(kind):
    if kind == "SIGINT":
        signal.raise_signal(signal.SIGINT)
    else:
        raise RuntimeError("IC05 observer failure")


def enter_with_return_fault(cost, context, observer, failure, method="__enter__"):
    before = sys.gettrace(), sys.getprofile()
    fired = []
    code = getattr(cost.OwnershipContext, method).__code__

    def callback(frame, event, _):
        if (
            event == "return"
            and frame.f_code is code
            and frame.f_locals.get("self") is context
            and not fired
        ):
            fired.append(True)
            fail(failure)
        return callback

    try:
        if observer == "trace":
            sys.settrace(callback)
        else:
            sys.setprofile(callback)
        yield_type = KeyboardInterrupt if failure == "SIGINT" else RuntimeError
        with pytest.raises(yield_type):
            with context:
                pytest.fail("failed entry must not execute user body")
    finally:
        sys.settrace(before[0])
        sys.setprofile(before[1])
    assert fired == [True]


@pytest.mark.parametrize(
    "family",
    ["instrument", "instrument_workers", "instrument_connections", "stage", "authentication"],
)
@pytest.mark.parametrize("observer", ["trace", "profile"])
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_return_observer_failure_rolls_back_all_factories(cost, family, observer, failure):
    a, b = cost.Collector(), cost.Collector()
    factories = {"stage": lambda: a.stage("transfer"), "authentication": cost.authentication_hashes}
    context = factories[family]() if family in factories else getattr(cost, family)()
    enter_with_return_fault(cost, context, observer, failure)
    # The failed object is deliberately retained: GC cannot satisfy the oracle.
    assert not cost.INSTALLATIONS and cost.ACTIVE.get() is None
    assert cost.HASH_PURPOSE.get() == "sha256" and a.snapshot() == {}
    native = canonical._parse_json
    actual = []

    def witness(frame, event, _):
        if event == "call" and frame.f_code is native.__code__:
            actual.append(bytes(frame.f_locals["raw"]))

    old = sys.getprofile()
    sys.setprofile(witness)
    try:
        with cost.instrument(), b.stage("calibration"):
            canonical.decode_c1(b"{}")
            canonical.decode_c1(b"{}")
    finally:
        sys.setprofile(old)
    assert actual == [b"{}", b"{}"]
    assert a.snapshot() == {}
    assert b.values["calibration/json/calls"] == 2
    assert b.values["calibration/json/submitted_bytes"] == 4
    context.close()
    context.close()
    assert not cost.INSTALLATIONS


@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
@pytest.mark.parametrize("point", ["registration_before", "registration_after", "helper_return"])
def test_stack_reservation_precedes_acquisition(cost, point, failure):
    context = cost.instrument()
    native = canonical._parse_json
    fired = []
    old_trace = sys.gettrace()
    with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
        with ExitStack() as stack:
            push = stack.push

            def fault_push(value):
                if point == "registration_before":
                    fired.append(True)
                    fail(failure)
                result = push(value)
                if point == "registration_after":
                    fired.append(True)
                    fail(failure)
                return result

            stack.push = fault_push

            def trace(frame, event, _):
                if (
                    point == "helper_return"
                    and event == "return"
                    and frame.f_code is cost.OwnershipContext.enter.__code__
                    and not fired
                ):
                    fired.append(True)
                    fail(failure)
                return trace

            try:
                sys.settrace(trace)
                context.enter(stack)
                pytest.fail("failed stack handoff must not execute caller work")
            finally:
                sys.settrace(old_trace)
    assert fired == [True]
    assert canonical._parse_json is native and not cost.INSTALLATIONS


@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_with_target_assignment_failure_is_already_cleanup_covered(cost, failure):
    class Target:
        def __setattr__(self, name, value):
            fail(failure)

    context = cost.instrument()
    target = Target()
    with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
        with context as target.value:
            pytest.fail("as assignment failed")
    assert not cost.INSTALLATIONS


def test_repeated_returns_no_gc_and_surviving_scope_ledger(cost):
    enabled = gc.isenabled()
    gc.disable()
    guards, retained = [], []
    original_attach = cost.EntryHandoff.attach

    def observe(guard):
        guards.append(weakref.ref(guard))
        original_attach(guard)

    cost.EntryHandoff.attach = observe
    a, b = cost.Collector(), cost.Collector()
    try:
        with cost.instrument(), b.stage("generation"):
            native_wrapper = canonical._parse_json
            for i in range(48):
                context = a.stage("transfer") if i % 2 else cost.instrument()
                retained.append(context)
                enter_with_return_fault(
                    cost,
                    context,
                    "trace" if i % 3 else "profile",
                    "SIGINT" if i % 2 else "exception",
                )
                assert cost.INSTALLATIONS["primitives"]["refs"] == 1
                assert canonical._parse_json is native_wrapper
                assert cost.ACTIVE.get() == (b, "generation")
                canonical.decode_c1(b"{}")
        assert a.snapshot() == {}
        assert b.values["generation/json/calls"] == 48
        assert b.values["generation/json/submitted_bytes"] == 96
        assert all(ref() is None for ref in guards)
        assert not cost.INSTALLATIONS
    finally:
        if enabled:
            gc.enable()


def test_native_job_after_cancelled_worker_entry_has_exact_hold(cost):
    first = cost.instrument_workers()
    enter_with_return_fault(cost, first, "profile", "SIGINT")
    c = cost.Collector()

    async def run():
        budget = WorkerBudget(1)
        lease = budget.acquire()
        try:
            with cost.instrument_workers(), c.stage("transfer"):
                assert await lease.run(lambda: 23) == 23
                assert c.pending == 0
        finally:
            lease.close()
        assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)

    asyncio.run(run())
    completed = []
    c.finish_when_idle(completed.append)
    assert completed == [c] and c.closed and c.pending == 0


def test_unsupported_monitoring_rejected_before_acquisition(cost):
    tool = next(i for i in range(6) if sys.monitoring.get_tool(i) is None)
    sys.monitoring.use_tool_id(tool, "IC05 unsupported observer")
    try:
        sys.monitoring.set_local_events(
            tool, cost.OwnershipContext.__enter__.__code__, sys.monitoring.events.PY_RETURN
        )
        with pytest.raises(RuntimeError, match="measurement incomplete"):
            with cost.instrument():
                pytest.fail("unsupported observer must fail before acquisition")
        assert not cost.INSTALLATIONS
    finally:
        sys.monitoring.set_local_events(tool, cost.OwnershipContext.__enter__.__code__, 0)
        sys.monitoring.free_tool_id(tool)


@pytest.mark.parametrize(
    "point", ["trace_flag", "trace_install", "profile_flag", "profile_install", "ready"]
)
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_observer_acquisition_failure_has_rollback_before_exposure(cost, point, failure):
    function = cost.EntryHandoff.ready if point == "ready" else cost.EntryHandoff.attach
    anchors = {
        "trace_flag": "self.trace_attached = True",
        "trace_install": "self.frame.f_trace = self.trace_hook",
        "profile_flag": "self.profile_attached = True",
        "profile_install": "sys.setprofile(self.profile_hook)",
        "ready": "self.check_monitoring()",
    }
    lines, first = inspect.getsourcelines(function)
    line = first + next(i for i, text in enumerate(lines) if anchors[point] in text)
    context, fired = cost.instrument(), []
    previous = sys.gettrace(), sys.getprofile()

    def profiler(frame, event, arg):
        pass

    def trace(frame, event, arg):
        if (
            event == "line"
            and frame.f_code is function.__code__
            and frame.f_lineno == line
            and not fired
        ):
            fired.append(True)
            fail(failure)
        return trace

    try:
        sys.setprofile(profiler)
        sys.settrace(trace)
        with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
            with context:
                pytest.fail("faulted activation cannot execute")
        assert not cost.INSTALLATIONS
        assert sys.getprofile() is profiler
    finally:
        sys.settrace(previous[0])
        sys.setprofile(previous[1])
    assert fired == [True]


@pytest.mark.parametrize("observer", ["trace", "profile"])
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_both_observers_are_forwarded_without_double_accounting(cost, observer, failure):
    context = cost.instrument()
    events = {"trace": 0, "profile": 0}
    before = sys.gettrace(), sys.getprofile()

    def observe(kind, frame, event):
        if (
            event == "return"
            and frame.f_code is cost.OwnershipContext.__enter__.__code__
            and frame.f_locals.get("self") is context
        ):
            events[kind] += 1
            if kind == observer and events[kind] == 1:
                fail(failure)

    def trace(frame, event, arg):
        observe("trace", frame, event)
        return trace

    def profile(frame, event, arg):
        observe("profile", frame, event)

    try:
        sys.settrace(trace)
        sys.setprofile(profile)
        with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
            with context:
                pytest.fail("observer rejected return")
        assert not cost.INSTALLATIONS
    finally:
        sys.settrace(before[0])
        sys.setprofile(before[1])
    assert events[observer] == 1
    assert events["trace"] >= 1 and events["profile"] >= 1


@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_profile_restoration_failure_still_releases_owned_resources(cost, monkeypatch, failure):
    native_setprofile = sys.setprofile
    old_profile = sys.getprofile()
    fired, guards = [], []
    original_attach = cost.EntryHandoff.attach

    def attach(guard):
        guards.append(weakref.ref(guard))
        original_attach(guard)

    def profile(frame, event, arg):
        pass

    def setter(value):
        if value is profile and not fired:
            fired.append(True)
            fail(failure)
        return native_setprofile(value)

    monkeypatch.setattr(cost.EntryHandoff, "attach", attach)
    native_setprofile(profile)
    monkeypatch.setattr(sys, "setprofile", setter)
    enabled = gc.isenabled()
    gc.disable()
    try:
        with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
            with cost.instrument():
                pytest.fail("failed return restoration cannot publish ownership")
        assert fired and not cost.INSTALLATIONS
        # Raising profile functions are unset by the interpreter itself.
        assert sys.getprofile() is None
        assert all(ref() is None for ref in guards)
    finally:
        native_setprofile(old_profile)
        if enabled:
            gc.enable()


def test_actual_task_cancel_is_delivered_at_await_after_successful_entry(cost):
    a, b = cost.Collector(), cost.Collector()

    async def run():
        task = asyncio.current_task()
        context = a.stage("transfer")
        requested = []
        before = sys.gettrace()

        def trace(frame, event, arg):
            if (
                event == "return"
                and frame.f_code is cost.OwnershipContext.__enter__.__code__
                and frame.f_locals.get("self") is context
                and not requested
            ):
                requested.append(True)
                task.cancel()
            return trace

        with cost.instrument():
            try:
                sys.settrace(trace)
                with pytest.raises(asyncio.CancelledError):
                    with context:
                        canonical.decode_c1(b"{}")
                        await asyncio.sleep(0)
            finally:
                sys.settrace(before)
            assert cost.ACTIVE.get() is None
            with b.stage("generation"):
                canonical.decode_c1(b"{}")
        assert requested

    asyncio.run(run())
    assert a.values["transfer/json/calls"] == b.values["generation/json/calls"] == 1
    assert (
        a.values["transfer/json/submitted_bytes"]
        == b.values["generation/json/submitted_bytes"]
        == 2
    )


def test_recovery_stack_preowns_one_exit_and_preserves_outer_scope(cost):
    a, b = cost.Collector(), cost.Collector()
    stack = cost.RecoveryStack()
    try:
        stack.enter_context(cost.instrument())
        stack.enter_context(a.stage("generation"))
        assert len(stack.inner._exit_callbacks) == 2
        failed = b.stage("transfer")
        enter_with_return_fault(cost, failed, "trace", "SIGINT")
        canonical.decode_c1(b"{}")
        assert cost.ACTIVE.get() == (a, "generation")
    finally:
        stack.close()
        stack.close()
    assert b.snapshot() == {}
    assert (
        a.values["generation/json/calls"] == 1 and a.values["generation/json/submitted_bytes"] == 2
    )


@pytest.mark.parametrize("failure", [False, True])
def test_local_trace_switch_and_opcode_events_are_forwarded(cost, failure):
    context, events = cost.instrument(), []
    old = sys.gettrace()
    frame = sys._getframe()
    opcode_before = frame.f_trace_opcodes

    def local(frame, event, arg):
        events.append(event)
        if event == "return" and failure:
            signal.raise_signal(signal.SIGINT)
        return local

    def start(frame, event, arg):
        if (
            frame.f_code is cost.OwnershipContext.__enter__.__code__
            and frame.f_locals.get("self") is context
        ):
            frame.f_trace_opcodes = True
            return local
        return start

    try:
        # CPython3.12 requires a prearmed existing frame before settrace.
        frame.f_trace_opcodes = True
        sys.settrace(start)
        if failure:
            with pytest.raises(KeyboardInterrupt):
                with context:
                    pytest.fail("opcode/local observer rejected entry")
        else:
            with context:
                assert sys.gettrace() is start
    finally:
        sys.settrace(old)
        frame.f_trace_opcodes = opcode_before
    assert "opcode" in events and "return" in events
    assert not cost.INSTALLATIONS


def test_profile_replacement_during_acquisition_is_explicit_incomplete(cost, monkeypatch):
    old = sys.getprofile()
    original_ready = cost.EntryHandoff.ready

    def profile(frame, event, arg):
        pass

    def ready(guard):
        sys.setprofile(None)
        original_ready(guard)

    monkeypatch.setattr(cost.EntryHandoff, "ready", ready)
    try:
        sys.setprofile(profile)
        with pytest.raises(RuntimeError, match="measurement incomplete"):
            with cost.instrument():
                pytest.fail("changed observer must not silently miss a return failure")
        assert sys.getprofile() is None and not cost.INSTALLATIONS
    finally:
        sys.setprofile(old)


@pytest.mark.parametrize("observer", ["trace", "profile"])
@pytest.mark.parametrize("failure", ["exception", "SIGINT"])
def test_exit_return_fault_is_after_resource_release(cost, observer, failure):
    context, c = cost.instrument(), cost.Collector()
    old = sys.gettrace(), sys.getprofile()
    fired = []

    def hook(frame, event, arg):
        if (
            event == "return"
            and frame.f_code is cost.OwnershipContext.__exit__.__code__
            and frame.f_locals.get("self") is context
            and not fired
        ):
            fired.append(True)
            fail(failure)
        return hook

    try:
        if observer == "trace":
            sys.settrace(hook)
        else:
            sys.setprofile(hook)
        with pytest.raises(KeyboardInterrupt if failure == "SIGINT" else RuntimeError):
            with context, c.stage("transfer"):
                canonical.decode_c1(b"{}")
    finally:
        sys.settrace(old[0])
        sys.setprofile(old[1])
    assert fired and not cost.INSTALLATIONS and cost.ACTIVE.get() is None
    assert c.values["transfer/json/calls"] == 1 and c.values["transfer/json/submitted_bytes"] == 2
    context.close()


def test_observer_returning_current_frame_trace_does_not_recurse(cost):
    old = sys.gettrace()
    c = cost.Collector()
    events = []

    def trace(frame, event, arg):
        if frame.f_code is cost.OwnershipContext.__enter__.__code__:
            events.append(event)
            return frame.f_trace or trace
        return trace

    try:
        sys.settrace(trace)
        with cost.instrument(), c.stage("generation"):
            canonical.decode_c1(b"{}")
        assert sys.gettrace() is trace
    finally:
        sys.settrace(old)
    assert events.count("return") >= 2
    assert c.values["generation/json/calls"] == 1
    assert c.values["generation/json/submitted_bytes"] == 2


@pytest.mark.parametrize("change", ["disable", "replace"])
def test_explicit_local_trace_assignment_is_preserved(cost, change):
    context = cost.instrument()
    old = sys.gettrace()
    lines, first = inspect.getsourcelines(cost.OwnershipContext.__enter__)
    seam = first + next(i for i, text in enumerate(lines) if "ownership_checkpoint()" in text)
    changed, old_after_change, replacement_events = [], [], []

    def replacement(frame, event, arg):
        replacement_events.append(event)
        return replacement

    def local(frame, event, arg):
        if changed:
            old_after_change.append(event)
        if event == "line" and frame.f_lineno == seam and not changed:
            changed.append(True)
            frame.f_trace = None if change == "disable" else replacement
            return None
        return local

    def global_trace(frame, event, arg):
        if (
            frame.f_code is cost.OwnershipContext.__enter__.__code__
            and frame.f_locals.get("self") is context
        ):
            return local
        return global_trace

    try:
        sys.settrace(global_trace)
        with context:
            assert sys.gettrace() is global_trace
    finally:
        sys.settrace(old)
    assert changed and not old_after_change
    assert bool(replacement_events) == (change == "replace")
    assert not cost.INSTALLATIONS


@pytest.mark.parametrize(
    "change", ["trace_adds_profile", "profile_replaces_profile", "profile_replaces_trace"]
)
def test_observer_control_mutation_at_return_cannot_escape_rollback(cost, change):
    context = cost.instrument()
    old = sys.gettrace(), sys.getprofile()
    fired, trace_returns, late_events, body = [], [], [], []

    def replacement(frame, event, arg):
        return replacement

    def late(frame, event, arg):
        late_events.append(event)
        raise RuntimeError("late local observer must not escape ownership")

    def tracer(frame, event, arg):
        if (
            event == "return"
            and frame.f_code is cost.OwnershipContext.__enter__.__code__
            and frame.f_locals.get("self") is context
        ):
            trace_returns.append(True)
        return tracer

    def hook(frame, event, arg):
        if (
            event == "return"
            and frame.f_code is cost.OwnershipContext.__enter__.__code__
            and frame.f_locals.get("self") is context
            and not fired
        ):
            fired.append(bool(trace_returns))
            if change == "profile_replaces_trace":
                frame.f_trace = late
            else:
                sys.setprofile(replacement)
        return hook

    try:
        if change == "trace_adds_profile":
            sys.settrace(hook)
        else:
            sys.settrace(tracer)
            sys.setprofile(hook)
        if change == "profile_replaces_trace":
            # CPython3.12 emits legacy trace-return BEFORE profile-return.
            # A later local trace assignment cannot retroactively add another
            # return callback. Verify this actual ordering, not a fictional race.
            with context:
                body.append(True)
            assert fired == [True] and body and not late_events
        else:
            with pytest.raises(RuntimeError, match="measurement incomplete"):
                with context:
                    pytest.fail("new return observer must not escape rollback")
        assert not cost.INSTALLATIONS
    finally:
        sys.settrace(old[0])
        sys.setprofile(old[1])


@pytest.mark.parametrize("error_type", [RuntimeError, KeyboardInterrupt])
def test_child_profile_failure_is_not_replaced_by_handoff_error(cost, error_type):
    old = sys.gettrace(), sys.getprofile()
    fired = []

    def trace(frame, event, arg):
        return trace

    def profile(frame, event, arg):
        if (
            event == "return"
            and frame.f_code is cost.installation.__wrapped__.__code__
            and not fired
        ):
            fired.append(True)
            raise error_type("IC05 exact child observer exception")

    try:
        sys.settrace(trace)
        sys.setprofile(profile)
        with pytest.raises(error_type, match="exact child observer exception"):
            with cost.instrument():
                pytest.fail("failed child cannot publish parent context")
        assert not cost.INSTALLATIONS and sys.getprofile() is None
    finally:
        sys.settrace(old[0])
        sys.setprofile(old[1])
    assert fired == [True]


@pytest.mark.parametrize("family", ["instrument", "stage"])
@pytest.mark.parametrize("observer", ["trace", "profile"])
@pytest.mark.parametrize("return_failure", [None, "exception", "SIGINT"])
def test_new_observer_during_entry_cannot_publish_unowned_state(
    cost, family, observer, return_failure
):
    a, b = cost.Collector(), cost.Collector()
    context = cost.instrument() if family == "instrument" else a.stage("transfer")
    checkpoint = cost.ownership_checkpoint
    armed, returned = [], []
    original_hooks = sys.gettrace(), sys.getprofile()
    actual = []
    native = canonical._parse_json.__code__

    def newly_enabled(frame, event, arg):
        if (
            frame.f_code is cost.OwnershipContext.__enter__.__code__
            and frame.f_locals.get("self") is context
            and event == "return"
        ):
            returned.append(True)
            if return_failure:
                fail(return_failure)
        return newly_enabled

    def arm_at_real_checkpoint():
        checkpoint()
        frame = sys._getframe().f_back
        while frame and not (
            frame.f_code is cost.OwnershipContext.__enter__.__code__
            and frame.f_locals.get("self") is context
        ):
            frame = frame.f_back
        if frame is not None and not armed:
            armed.append(True)
            if observer == "trace":
                sys.settrace(newly_enabled)
                frame.f_trace = newly_enabled
            else:
                sys.setprofile(newly_enabled)

    def witness(frame, event, arg):
        if event == "call" and frame.f_code is native:
            actual.append(bytes(frame.f_locals["raw"]))

    with cost.instrument(), b.stage("generation"):
        baseline = {k: v["refs"] for k, v in cost.INSTALLATIONS.items()}
        wrapper = canonical._parse_json
        cost.ownership_checkpoint = arm_at_real_checkpoint
        try:
            error = KeyboardInterrupt if return_failure == "SIGINT" else RuntimeError
            with pytest.raises(error):
                with context:
                    pytest.fail("new observer must not escape the entry contract")
        finally:
            sys.settrace(original_hooks[0])
            sys.setprofile(original_hooks[1])
            cost.ownership_checkpoint = checkpoint
        assert armed == [True] and returned == [True]
        assert {k: v["refs"] for k, v in cost.INSTALLATIONS.items()} == baseline
        assert cost.ACTIVE.get() == (b, "generation")
        assert canonical._parse_json is wrapper
        sys.setprofile(witness)
        try:
            canonical.decode_c1(b"{}")
        finally:
            sys.setprofile(original_hooks[1])
        context.close()
        context.close()
        assert a.snapshot() == {}
    assert actual == [b"{}"]
    assert b.values["generation/json/calls"] == 1
    assert b.values["generation/json/submitted_bytes"] == 2

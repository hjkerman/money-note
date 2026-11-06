"""IC03 generation handoff: native frame entries are the exact event oracle."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import importlib.util
import inspect
from pathlib import Path
import sys
from threading import Event, current_thread

import pytest

from isolated_sync import canonical
from isolated_sync.workers import NativeJob, WorkerBudget, WorkerLease

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def cost():
    spec = importlib.util.spec_from_file_location(
        "b03_ic03", ROOT / "docs/benchmarks/t66f-b03/counters.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = canonical._parse_json, canonical.encode
    yield module
    assert not module.INSTALLATIONS
    assert (canonical._parse_json, canonical.encode) == original


def assert_parse(collector, stage, payloads):
    assert collector.values[f"{stage}/json/calls"] == len(payloads)
    for metric in ("submitted_bytes", "completed_bytes"):
        assert collector.values[f"{stage}/json/{metric}"] == sum(map(len, payloads))


@pytest.mark.parametrize("payload", [b"{}", '"한😀"'.encode(), b'{"n":123}'])
@pytest.mark.parametrize("stage", ["generation", "transfer"])
def test_activation_preempted_before_reference_uses_new_native_delegate(cost, payload, stage):
    original = canonical._parse_json
    native_encode = canonical.encode
    function = cost.instrument.__wrapped__
    lines, start = inspect.getsourcelines(function)
    seam = start + next(
        i for i, line in enumerate(lines) if 'with installation("primitives")' in line
    )
    entered, resume = Event(), Event()
    native_calls = []
    native_encoded = []
    collector = cost.Collector()
    outer = cost.instrument()
    outer.__enter__()
    retiring_wrapper = canonical._parse_json

    def work():
        stopped = False

        def trace(frame, event, _):
            nonlocal stopped
            if event == "call" and frame.f_code is original.__code__:
                native_calls.append(frame.f_locals["raw"])
            if event == "return" and frame.f_code is native_encode.__code__:
                native_encoded.append(_)
            if (
                not stopped
                and event == "line"
                and frame.f_code is function.__code__
                and frame.f_lineno == seam
            ):
                stopped = True
                entered.set()
                assert resume.wait(10)
            return trace

        sys.settrace(trace)
        try:
            with cost.instrument(), collector.stage(stage):
                assert canonical._parse_json is not retiring_wrapper
                assert canonical._parse_json.__wrapped__ is original
                canonical.decode_c1(payload)
                canonical.encode({"v": "한😀"})
        finally:
            sys.settrace(None)

    try:
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(work)
            try:
                assert entered.wait(10)
                outer.__exit__(None, None, None)
                outer = None
                assert canonical._parse_json is original
            finally:
                resume.set()
            future.result(timeout=15)
    finally:
        if outer is not None:
            outer.__exit__(None, None, None)
    assert native_calls == [payload]
    assert_parse(collector, stage, [payload])
    # decode_c1 itself invokes canonical encode once, before our explicit call.
    assert len(native_encoded) == 2
    assert collector.values[f"{stage}/encoding/calls"] == len(native_encoded)
    assert collector.values[f"{stage}/encoding/output_bytes"] == sum(map(len, native_encoded))


@pytest.mark.parametrize("pause_after_restore", [False, True])
def test_new_generation_waits_for_retiring_generation_teardown(
    cost, monkeypatch, pause_after_restore
):
    native = canonical._parse_json
    entered, resume, activation_entered = Event(), Event(), Event()
    old = cost.instrument()
    old.__enter__()
    state = cost.INSTALLATIONS["primitives"]
    close = state["stack"].close
    installation = cost.installation
    collector = cost.Collector()

    def paused_close():
        if pause_after_restore:
            close()
        entered.set()
        assert resume.wait(10)
        if not pause_after_restore:
            close()

    @contextmanager
    def activating(name):
        activation_entered.set()
        with installation(name) as stack:
            yield stack

    monkeypatch.setattr(state["stack"], "close", paused_close)
    monkeypatch.setattr(cost, "installation", activating)

    def parse():
        with cost.instrument(), collector.stage("transfer"):
            assert cost.INSTALLATIONS["primitives"] is not state
            assert canonical._parse_json.__wrapped__ is native
            canonical.decode_c1(b"{}")

    with ThreadPoolExecutor(2) as pool:
        closing = pool.submit(old.__exit__, None, None, None)
        try:
            assert entered.wait(10)
            opening = pool.submit(parse)
            assert activation_entered.wait(10)
            assert not opening.done()
        finally:
            resume.set()
        closing.result(timeout=15)
        opening.result(timeout=15)
    assert_parse(collector, "transfer", [b"{}"])


def test_old_scope_closes_while_new_scope_keeps_same_generation(cost):
    native = canonical._parse_json
    opened, resume = Event(), Event()
    collector = cost.Collector()
    outer = cost.instrument()
    outer.__enter__()
    wrapper = canonical._parse_json
    state = cost.INSTALLATIONS["primitives"]
    native_calls = []

    def work():
        def trace(frame, event, _):
            if event == "call" and frame.f_code is native.__code__:
                native_calls.append(frame.f_locals["raw"])
            return trace

        sys.settrace(trace)
        try:
            with cost.instrument(), collector.stage("observation"):
                opened.set()
                assert resume.wait(10)
                assert cost.INSTALLATIONS["primitives"] is state
                assert state["refs"] == 1
                assert canonical._parse_json is wrapper
                canonical.decode_c1(b"{}")
                canonical.decode_c1(b"{}")
        finally:
            sys.settrace(None)

    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(work)
        try:
            assert opened.wait(10)
            outer.__exit__(None, None, None)
        finally:
            resume.set()
        future.result(timeout=15)
    assert native_calls == [b"{}", b"{}"]
    assert_parse(collector, "observation", native_calls)


def test_nested_scope_close_and_repeated_generations_have_bounded_state(cost):
    native = canonical._parse_json
    first, second = cost.Collector(), cost.Collector()
    for _ in range(100):
        with cost.instrument(), first.stage("generation"):
            wrapper = canonical._parse_json
            with cost.instrument(), cost.instrument(), second.stage("transfer"):
                assert cost.INSTALLATIONS["primitives"]["refs"] == 3
                assert canonical._parse_json is wrapper
                canonical.decode_c1(b"{}")
            canonical.decode_c1(b"{}")
        assert not cost.INSTALLATIONS
        assert canonical._parse_json is native
    assert_parse(first, "generation", [b"{}"] * 100)
    assert_parse(second, "transfer", [b"{}"] * 100)
    first.close()
    before = first.snapshot()
    with cost.instrument(), first.stage("generation"):
        canonical.decode_c1(b"{}")
    assert first.snapshot() == before


@pytest.mark.parametrize("error", [RuntimeError("install failure"), KeyboardInterrupt()])
def test_install_exception_releases_only_acquired_reference(cost, monkeypatch, error):
    native = canonical._parse_json
    original = cost.install_patch

    def fail(stack, target, name, value):
        if name == "encode":
            raise error
        original(stack, target, name, value)

    with monkeypatch.context() as scope:
        scope.setattr(cost, "install_patch", fail)
        with pytest.raises(type(error)):
            with cost.instrument():
                pytest.fail("rejected scope must not run")
    assert not cost.INSTALLATIONS and canonical._parse_json is native
    collector = cost.Collector()
    with cost.instrument(), collector.stage("transfer"):
        canonical.decode_c1(b"{}")
    assert_parse(collector, "transfer", [b"{}"])


@pytest.mark.parametrize("rejected", [False, True])
def test_worker_delegate_capture_cannot_duplicate_native_init_or_hold(cost, monkeypatch, rejected):
    native = NativeJob.__init__, NativeJob._finish, WorkerLease.run
    entered, resume = Event(), Event()
    installation = cost.installation
    calls = []
    collector = cost.Collector()

    @contextmanager
    def delayed(name):
        if name == "workers" and current_thread().name.startswith("ic03-worker"):
            entered.set()
            assert resume.wait(10)
        with installation(name) as stack:
            yield stack

    old = cost.instrument_workers()
    old.__enter__()

    def work():
        def trace(frame, event, _):
            if event == "call" and frame.f_code is native[0].__code__:
                calls.append(frame.f_locals["self"])
            return trace

        async def run():
            budget = WorkerBudget(1)
            lease = budget.acquire()
            with cost.instrument_workers(), collector.stage("transfer"):
                assert NativeJob.__init__ is not native[0]
                if rejected:
                    lease.close()
                    with pytest.raises(RuntimeError, match="closed worker lease"):
                        await lease.run(lambda: None)
                else:
                    assert await lease.run(lambda: 17) == 17
                    lease.close()
                assert collector.pending == 0
            assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)

        sys.settrace(trace)
        try:
            asyncio.run(run())
        finally:
            sys.settrace(None)

    monkeypatch.setattr(cost, "installation", delayed)
    with ThreadPoolExecutor(1, thread_name_prefix="ic03-worker") as pool:
        future = pool.submit(work)
        try:
            assert entered.wait(10)
            old.__exit__(None, None, None)
        finally:
            resume.set()
        future.result(timeout=15)
    assert len(calls) == 1
    assert (NativeJob.__init__, NativeJob._finish, WorkerLease.run) == native
    completions = []
    collector.finish_when_idle(completions.append)
    assert collector.closed and completions == [collector]

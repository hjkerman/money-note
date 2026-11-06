"""PEP669 실제 event 상태와 획득 전 거부·후속 실제 입력을 대조한다."""

import gc
import importlib.util
from pathlib import Path
import signal
import sys
from threading import Event, Thread
from unittest.mock import _patch

import pytest

from isolated_sync import canonical
from isolated_sync.workers import NativeJob

ROOT = Path(__file__).resolve().parents[2]
UNSUPPORTED = "B03 monitoring entry observer unsupported; measurement incomplete"
UNAVAILABLE = "B03 monitoring state unavailable; measurement incomplete"


@pytest.fixture
def cost():
    spec = importlib.util.spec_from_file_location(
        "ic06_subject", ROOT / "docs/benchmarks/t66f-b03/counters.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    delegates = canonical._parse_json, canonical.encode, NativeJob.__init__, NativeJob._finish
    hooks = sys.gettrace(), sys.getprofile(), signal.getsignal(signal.SIGINT)
    patches = list(_patch._active_patches)
    yield m
    assert not m.INSTALLATIONS and m.ACTIVE.get() is None
    assert (
        canonical._parse_json,
        canonical.encode,
        NativeJob.__init__,
        NativeJob._finish,
    ) == delegates
    assert (sys.gettrace(), sys.getprofile(), signal.getsignal(signal.SIGINT)) == hooks
    assert list(_patch._active_patches) == patches


def configure(tool, code, scope, active):
    m = sys.monitoring
    mask = m.events.PY_RETURN if active else 0
    if scope == "global":
        m.set_events(tool, mask)
    else:
        m.set_local_events(tool, code, mask)


def cleanup(tool, code, event=None):
    m = sys.monitoring
    if m.get_tool(tool) is None:
        m.use_tool_id(tool, "IC06 own cleanup")
    m.set_events(tool, 0)
    m.set_local_events(tool, code, 0)
    m.register_callback(tool, event or m.events.PY_RETURN, None)
    m.free_tool_id(tool)


def measured_recovery(cost):
    native = canonical._parse_json
    raw = [b"{}", '{"x":"한"}'.encode()]
    actual = []
    a, b = cost.Collector(), cost.Collector()

    def witness(frame, event, arg):
        if event == "call" and frame.f_code is native.__code__:
            actual.append(bytes(frame.f_locals["raw"]))

    old = sys.getprofile()
    sys.setprofile(witness)
    try:
        with cost.instrument(), a.stage("generation"):
            canonical.decode_c1(raw[0])
            with cost.instrument(), b.stage("transfer"):
                canonical.decode_c1(raw[1])
            assert cost.ACTIVE.get()[0] is a
    finally:
        sys.setprofile(old)
    assert actual == raw
    for collector, stage, body in [(a, "generation", raw[0]), (b, "transfer", raw[1])]:
        assert collector.values[f"{stage}/json/calls"] == 1
        assert collector.values[f"{stage}/json/submitted_bytes"] == len(body)
        assert collector.values[f"{stage}/json/completed_bytes"] == len(body)
        assert collector.pending == 0
    assert not cost.INSTALLATIONS and cost.ACTIVE.get() is None
    assert canonical._parse_json is native


@pytest.mark.parametrize("tool", range(6))
@pytest.mark.parametrize("state", ["allocated", "released", "reused"])
@pytest.mark.parametrize("scope", ["global", "local"])
@pytest.mark.parametrize("active", [False, True])
@pytest.mark.parametrize("registered", [False, True])
def test_monitoring_state_matrix(cost, tool, state, scope, active, registered):
    m = sys.monitoring
    assert m.get_tool(tool) is None and m.get_events(tool) == 0
    code = cost.OwnershipContext.__enter__.__code__
    target, callbacks, acquisitions = cost.instrument(), [], []
    native = canonical._parse_json
    original = target.inner.__enter__

    def acquire():
        acquisitions.append(True)
        return original()

    target.inner.__enter__ = acquire

    def callback(c, *args):
        if c is code and sys._getframe(1).f_locals.get("self") is target:
            callbacks.append(True)
            raise RuntimeError("IC06 unsafe return callback")

    m.use_tool_id(tool, "IC06 matrix")
    try:
        if registered:
            m.register_callback(tool, m.events.PY_RETURN, callback)
        configure(tool, code, scope, active)
        if state in {"released", "reused"}:
            m.free_tool_id(tool)
        if state == "reused":
            m.use_tool_id(tool, "IC06 reused")
        assert m.get_events(tool) == (m.events.PY_RETURN if active and scope == "global" else 0)
        assert m.get_local_events(tool, code) == (
            m.events.PY_RETURN if active and scope == "local" else 0
        )
        if active:
            with pytest.raises(RuntimeError, match="^" + UNSUPPORTED + "$"):
                with target:
                    pytest.fail("preflight must reject before body")
            assert acquisitions == [] and callbacks == []
        else:
            with target:
                assert acquisitions == [True]
        assert not cost.INSTALLATIONS and cost.ACTIVE.get() is None
        assert canonical._parse_json is native
        if registered:
            # register_callback returns the previous callback; no getter exists.
            assert m.register_callback(tool, m.events.PY_RETURN, callback) is callback
    finally:
        cleanup(tool, code)
    measured_recovery(cost)


@pytest.mark.parametrize("scope", ["global", "local"])
def test_reuse_uses_current_masks_and_unrelated_local_monitor_is_supported(cost, scope):
    m = sys.monitoring
    tool = next(i for i in range(6) if m.get_tool(i) is None)
    code = cost.OwnershipContext.__enter__.__code__
    delivered = []

    def unrelated():
        return 7

    def callback(c, *args):
        if c is unrelated.__code__:
            delivered.append(True)

    m.use_tool_id(tool, "IC06 transitions")
    try:
        m.register_callback(tool, m.events.PY_RETURN, callback)
        for active in [True, False, True, False]:
            configure(tool, code, scope, active)
            m.free_tool_id(tool)
            m.use_tool_id(tool, "IC06 current reuse")
            if active:
                with pytest.raises(RuntimeError, match=UNSUPPORTED):
                    with cost.instrument():
                        pytest.fail("stale cached classification")
            else:
                measured_recovery(cost)
        # A local event on unrelated code does not observe ownership entry.
        m.set_local_events(tool, unrelated.__code__, m.events.PY_RETURN)
        measured_recovery(cost)
        m.free_tool_id(tool)
        assert unrelated() == 7 and delivered == [True]
        measured_recovery(cost)
        m.use_tool_id(tool, "IC06 cleanup unrelated")
        m.set_local_events(tool, unrelated.__code__, 0)
    finally:
        cleanup(tool, code)


@pytest.mark.parametrize("family", ["instrument", "instrument_workers", "stage"])
@pytest.mark.parametrize("scope", ["global", "local"])
def test_repeated_rejection_retains_no_owner_or_cancelled_stage(cost, family, scope):
    m = sys.monitoring
    tool = next(i for i in range(6) if m.get_tool(i) is None)
    code = cost.OwnershipContext.__enter__.__code__
    cancelled = cost.Collector()
    held, callbacks = [], []

    def callback(c, *args):
        if c is code:
            callbacks.append(True)
            raise RuntimeError("IC06 cancelled entry")

    enabled = gc.isenabled()
    gc.disable()
    try:
        for index in range(24):
            m.use_tool_id(tool, "IC06 bounded rejection")
            m.register_callback(tool, m.events.PY_RETURN, callback)
            configure(tool, code, scope, True)
            m.free_tool_id(tool)
            target = cancelled.stage("transfer") if family == "stage" else getattr(cost, family)()
            held.append(target)  # GC cannot satisfy cleanup.
            with pytest.raises(RuntimeError, match=UNSUPPORTED):
                with target:
                    pytest.fail("rejected body")
            assert not cost.INSTALLATIONS and cost.ACTIVE.get() is None
            assert cancelled.snapshot() == {} and cancelled.pending == 0
            assert callbacks == []
            cleanup(tool, code)
            measured_recovery(cost)
        for target in held:
            target.close()
    finally:
        if enabled:
            gc.enable()
        cleanup(tool, code)


@pytest.mark.parametrize("api", ["get_events", "get_local_events", "missing_namespace"])
@pytest.mark.parametrize("failure", ["ordinary", "cancel"])
def test_inspection_failure_precedes_acquisition_and_recovers(cost, monkeypatch, api, failure):
    target = cost.instrument()
    acquisitions = []
    original = target.inner.__enter__

    def acquire():
        acquisitions.append(True)
        return original()

    def broken(*args):
        if failure == "cancel":
            raise KeyboardInterrupt("IC06 inspection cancelled")
        raise ValueError("IC06 inspection unavailable")

    target.inner.__enter__ = acquire
    with monkeypatch.context() as patch:
        if api == "missing_namespace":
            patch.delattr(sys, "monitoring")
        else:
            patch.setattr(sys.monitoring, api, broken)
        expected = (
            RuntimeError
            if api == "missing_namespace" or failure == "ordinary"
            else KeyboardInterrupt
        )
        with pytest.raises(expected) as error:
            with target:
                pytest.fail("inspection failure body")
        if expected is RuntimeError:
            assert str(error.value) == UNAVAILABLE
        assert acquisitions == [] and not cost.INSTALLATIONS and cost.ACTIVE.get() is None
    measured_recovery(cost)


@pytest.mark.parametrize("scope", ["global", "local"])
def test_detected_mid_entry_external_change_rolls_back_without_atomicity_claim(cost, scope):
    # A cooperative external actor changes configuration while acquisition is
    # blocked. ready() must detect it. Changes after the last check are outside
    # the stable-monitoring contract; this test does not certify those races.
    m = sys.monitoring
    tool = next(i for i in range(6) if m.get_tool(i) is None)
    code = cost.OwnershipContext.__enter__.__code__
    acquired, changed = Event(), Event()
    errors = []
    target = cost.instrument()
    original = target.inner.__enter__

    def acquire():
        result = original()
        acquired.set()
        assert changed.wait(5)
        return result

    target.inner.__enter__ = acquire
    m.use_tool_id(tool, "IC06 external change")

    def actor():
        try:
            assert acquired.wait(5)
            configure(tool, code, scope, True)
            m.free_tool_id(tool)
        except BaseException as error:
            errors.append(error)
        finally:
            changed.set()

    thread = Thread(target=actor)
    thread.start()
    try:
        with pytest.raises(RuntimeError, match=UNSUPPORTED):
            with target:
                pytest.fail("changed monitoring must not silently succeed")
        assert not cost.INSTALLATIONS and cost.ACTIVE.get() is None
    finally:
        thread.join(5)
        cleanup(tool, code)
    assert not thread.is_alive() and errors == []
    measured_recovery(cost)


@pytest.mark.parametrize(
    "event_name",
    [
        "PY_START",
        "PY_RETURN",
        "CALL",
        "LINE",
        "INSTRUCTION",
        "JUMP",
        "BRANCH",
        "RAISE",
        "PY_UNWIND",
    ],
)
def test_relevant_global_event_masks_rejected_without_callback_introspection(cost, event_name):
    m = sys.monitoring
    tool = next(i for i in range(6) if m.get_tool(i) is None)
    code = cost.OwnershipContext.__enter__.__code__
    event = getattr(m.events, event_name)
    m.use_tool_id(tool, "IC06 event masks")
    try:
        m.set_events(tool, event)
        m.free_tool_id(tool)
        with pytest.raises(RuntimeError, match=UNSUPPORTED):
            with cost.instrument():
                pytest.fail("active global mask")
        assert not cost.INSTALLATIONS and cost.ACTIVE.get() is None
    finally:
        cleanup(tool, code, event)
    measured_recovery(cost)


@pytest.mark.parametrize("event_name", ["PY_START", "LINE", "INSTRUCTION"])
@pytest.mark.parametrize("point", ["entry", "preflight"])
def test_actual_callback_exception_before_acquisition_has_no_cleanup_obligation(
    cost, event_name, point
):
    m = sys.monitoring
    tool = next(i for i in range(6) if m.get_tool(i) is None)
    code = (
        cost.OwnershipContext.__enter__ if point == "entry" else cost.EntryHandoff.check_monitoring
    ).__code__
    event = getattr(m.events, event_name)
    target, delivered, acquisitions = cost.instrument(), [], []
    original = target.inner.__enter__

    def acquire():
        acquisitions.append(True)
        return original()

    def callback(c, *args):
        if c is code and not delivered:
            delivered.append(True)
            raise RuntimeError("IC06 actual pre-acquisition event interruption")

    target.inner.__enter__ = acquire
    m.use_tool_id(tool, "IC06 actual interruption")
    try:
        m.register_callback(tool, event, callback)
        m.set_local_events(tool, code, event)
        m.free_tool_id(tool)
        with pytest.raises(RuntimeError, match="IC06 actual pre-acquisition event interruption"):
            with target:
                pytest.fail("interrupted preflight body")
        assert delivered == [True] and acquisitions == []
        assert not cost.INSTALLATIONS and cost.ACTIVE.get() is None
    finally:
        cleanup(tool, code, event)
    measured_recovery(cost)

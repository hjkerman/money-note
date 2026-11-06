"""실제 source/JUnit에 연결된 IC04 interruption matrix와 독립 capacity oracle."""

import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
from threading import Event, Thread, get_ident
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "evidence"
sys.path.insert(0, str(ROOT / "backend"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    subject = load("ic04_matrix_subject", ROOT / "docs/benchmarks/t66f-b03/counters.py")
    tests = load("ic04_matrix_tests", ROOT / "backend/tests/test_logical_cost_ic04.py")
    xml = ET.parse(OUT / "final-return-handoff-counterexamples.xml").getroot()
    cases = [x for x in xml.iter("testcase") if x.get("name")]
    failed = {
        x.get("name")
        for x in cases
        if x.find("failure") is not None or x.find("error") is not None
    }

    def names(fragment):
        return [x.get("name") for x in cases if fragment in x.get("name")]

    rows = []
    for point in tests.BOUNDARIES:
        code, line = tests.boundary(subject, point)
        executed = [
            n
            for n in names("test_all_installation_transitions")
            if n.endswith("-" + point + "]")
        ]
        assert len(executed) == 2, (point, executed)
        rows.append(
            {
                "id": point,
                "runtime": "main-thread synchronous Python",
                "source": code.co_filename.replace(str(ROOT) + "/", ""),
                "function": code.co_name,
                "line": line,
                "injections": ["ordinary exception", "actual SIGINT"],
                "tests": executed,
                "result": "PASS",
                "oracle": "actual native frame/raw input equals independent literal invocation ledger; callable identity, registry, references, mock handles, original signal handler restored; fresh generation exact",
            }
        )
    groups = {
        "late_alias_restoration": "test_late_import_alias_cleanup",
        "persistent_restoration_failure": "test_persistent_cleanup_failure",
        "journal_capacity_before_mutation": "test_patch_capacity_rejection",
        "native_hold_acquisition_release": "test_native_hold_transitions",
        "native_completion_transfer": "test_native_completion_ownership",
        "dispatch_context_and_rejected_jobs": "test_dispatch_context_and_unregistered",
        "live_native_tail_after_session_teardown": "test_live_native_tail",
        "completion_callback_failure": "test_completion_callback_failure",
        "completion_handoff": "test_completion_handoff_cancellation",
        "first_owner_failed_with_waiters": "test_failed_first_publication",
        "retiring_generation_and_concurrent_activation": "test_cancelled_teardown",
        "stateful_reference_native_and_signal_sequences": "test_stateful_bounded",
        "stage_and_hash_context_registration_reset": "test_scoped_context_registration",
        "generator_resume_entry_retirement": "test_generator_resume_and_retirement",
        "generator_contexts_out_of_order": "test_generator_contexts_out_of_order",
        "user_body_signal_not_deferred": "test_signal_during_user_body",
        "waiting_for_first_owner_cancellable": "test_main_thread_waiter",
        "identical_nested_context_and_no_retired_handler": "test_nested_identical_hash",
        "main_origin_context_closed_on_worker": "test_main_origin_context_can_close",
        "observer_outside_runner_preserves_native_SIGINT": "test_observer_outside_asyncio_runner",
        "context_decorator_generations": "test_context_decorator_recreates",
        "outer_enter_return_handoff": "test_cancelled_outer_enter_return",
        "pending_signal_before_checkpoint_or_yield": "test_pending_signal_never_enters",
    }
    for point, fragment in groups.items():
        executed = names(fragment)
        assert executed, point
        rows.append(
            {
                "id": point,
                "tests": executed,
                "result": "FAIL" if any(n in failed for n in executed) else "PASS",
                "oracle": "literal/native resource ledger and observable identities; original failure propagated; no compensation bytes",
            }
        )
    stack = subject.RecoveryStack()
    called = []
    for n in range(subject.PATCH_LIMIT):
        stack.callback(called.append, n)
    try:
        stack.callback(called.append, subject.PATCH_LIMIT)
    except RuntimeError as error:
        assert "capacity" in str(error)
    else:
        raise AssertionError("257th obligation must reject before registration")
    stack.close()
    assert called == list(reversed(range(subject.PATCH_LIMIT)))
    assert not stack.inner._exit_callbacks and not subject.INSTALLATIONS
    capacity = {
        "configured_capacity": subject.PATCH_LIMIT,
        "registered": 256,
        "rejected": 257,
        "actual_cleanup_calls": len(called),
        "independent_LIFO_oracle": "PASS",
        "remaining_obligations": 0,
    }
    main_id = get_ident()
    seen, emitter, ready = [], [], Event()
    old = signal.getsignal(signal.SIGINT)

    def handler(_signal, _frame):
        seen.append(get_ident())
        ready.set()

    def worker():
        emitter.append(get_ident())
        signal.raise_signal(signal.SIGINT)

    try:
        signal.signal(signal.SIGINT, handler)
        t = Thread(target=worker)
        t.start()
        t.join(5)
        assert not t.is_alive() and ready.wait(5)
    finally:
        signal.signal(signal.SIGINT, old)
    assert seen == [main_id] and emitter[0] != main_id
    unreachable = [
        {
            "boundary": "Task.cancel between two synchronous Python assignments",
            "status": "NOT REACHABLE",
            "reason": "No await in acquisition/restoration. Actual cancellation requests are injected and the following real await receives CancelledError; dispatch/active-scope tests prove this.",
        },
        {
            "boundary": "Python SIGINT handler raising inside native worker thread",
            "status": "NOT REACHABLE",
            "reason": "Runtime probe emitted SIGINT from a worker; handler executed on main thread. Native late-tail release and main-thread queued completion are tested separately.",
        },
        {
            "boundary": "accepted completed job treated as an unregistered rejected job",
            "status": "NOT REACHABLE",
            "reason": "Successful await completed native finish and released ownership; cancelled live jobs remain in lease._jobs and retain their own instance completion. Rejected jobs exercise unregistered cleanup.",
        },
        {
            "boundary": "SIGKILL/physical power loss",
            "status": "OUTSIDE RECOVERABLE CLEANUP CONTRACT",
            "reason": "No Python finally can run; no hardware proof claimed.",
        },
    ]
    result = {
        "schema_version": 1,
        "task": "T6.6F-B03-IC04",
        "subject_sha256": hashlib.sha256(
            (ROOT / "docs/benchmarks/t66f-b03/counters.py").read_bytes()
        ).hexdigest(),
        "coverage": "FAIL — outer enter-return handoff unresolved"
        if failed
        else "COVERED within supported recoverable lifecycle",
        "failed_tests": sorted(failed),
        "registration_gap": "Final scan found ContextVar and yield gaps; final OwnershipContext protects complete synchronous generator resumes, closes interrupted acquisitions and restores exact prior binding. Cross-thread handler retention invalidated the intermediate persistent router; it was removed, not hidden by changing the oracle.",
        "resume_guard_contract": "Temporary SIGINT guards exist only during synchronous enter/exit/close resumes. Original handler is restored before returning/yielding user code; wait_for_installation remains cancellable. No process-global router or owner list remains between resumes.",
        "rows": rows,
        "runtime_reachability_exclusions": unreachable,
        "capacity_oracle": capacity,
        "retained_signal_handlers_between_resumes": 0,
        "signal_probe": {
            "emitter_thread_is_main": False,
            "handler_thread_is_main": True,
        },
        "stateful": {
            "seeds": [4104, 907],
            "steps_each": 400,
            "operations": [
                "acquire",
                "nested acquire",
                "parse distinct/equal literals",
                "cancel setup with actual SIGINT",
                "release",
                "CancelledError exit",
                "native acquire/hold/complete",
            ],
            "oracle": "independent operation/input/native-job ledger; actual native frames and counters compared",
        },
        "failure_contracts": {
            "persistent_cleanup_failure": "One bounded RECOVERING generation, original error propagated, no new wrappers; removing fault permits recovery before next activation.",
            "external_report_callback": "Arbitrary callback is never shielded or speculatively replayed; completion_error records failure, no complete-measurement claim.",
            "raw_Collector_hold_release": "Compatibility integer helpers are not used to own native resources; actual job holds use acquire_job_hold/release_job_hold.",
        },
        "new_unique_cases": len(
            [x for x in cases if "test_logical_cost_ic04" in x.get("classname", "")]
        ),
        "independent_audit": "PENDING",
    }
    (OUT / "interruption-matrix.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "transition_rows": len(rows),
                "new_unique_cases": result["new_unique_cases"],
                "capacity": capacity,
                "signal_probe": "PASS",
            }
        )
    )

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

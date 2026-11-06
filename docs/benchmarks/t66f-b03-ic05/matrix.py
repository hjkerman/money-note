"""IC05 ownership coverage from final JUnit, unchanged original oracles and source."""

import ast
import dis
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "evidence"


def digest(body):
    return hashlib.sha256(body).hexdigest()


def main():
    runs = [
        "handoff-complete",
        "preserved-original-complete",
        "diagnostic-complete",
    ]
    rows = {}
    for label in runs:
        command = json.loads((OUT / (label + ".json")).read_text())
        assert command["exit_code"] == 0, label
        for path, expected in command["source_sha256"].items():
            assert digest((ROOT / path).read_bytes()) == expected, (label, path)
        cases = list(ET.parse(OUT / (label + ".xml")).getroot().iter("testcase"))
        assert all(
            x.find("failure") is None
            and x.find("error") is None
            and x.find("skipped") is None
            for x in cases
        )
        rows[label] = [x.get("name") for x in cases]
    current = rows[runs[0]]
    groups = {
        "internal_acquisition_and_return_observers": "test_return_observer_failure",
        "caller_stack_reservation_before_acquisition": "test_stack_reservation",
        "with_as_assignment_already_cleanup_covered": "test_with_target_assignment",
        "repeated_cancel_baseline_without_GC": "test_repeated_returns",
        "native_hold_after_cancelled_worker_entry": "test_native_job_after",
        "unsupported_monitoring_before_resources": "test_unsupported_monitoring",
        "observer_registration_rollback": "test_observer_acquisition",
        "trace_and_profile_together": "test_both_observers",
        "profile_restoration_failure": "test_profile_restoration",
        "actual_async_cancel_delivered_at_await": "test_actual_task_cancel",
        "recovery_stack_single_prereserved_exit": "test_recovery_stack",
        "local_trace_and_real_opcode_forwarding": "test_local_trace_switch",
        "observer_replacement_explicit_incomplete": "test_profile_replacement",
        "exit_return_already_released": "test_exit_return_fault",
        "trace_callback_observes_original_slot": "test_observer_returning_current_frame",
        "explicit_local_trace_control": "test_explicit_local_trace_assignment",
        "return_observer_control_mutation": "test_observer_control_mutation_at_return",
        "child_profile_failure_preserves_exception": "test_child_profile_failure",
        "first_observer_enabled_during_entry": "test_new_observer_during_entry",
    }
    matrix = []
    for boundary, fragment in groups.items():
        tests = [n for n in current if fragment in n]
        assert tests, boundary
        matrix.append({"boundary": boundary, "tests": tests, "result": "PASS"})
    original = [
        n
        for n in rows["diagnostic-complete"]
        if "test_cancelled_outer_enter_return" in n
    ]
    assert len(original) == 3
    matrix.append(
        {
            "boundary": "original_IC04_outer_return",
            "tests": original,
            "result": "PASS",
            "original_assertions": "unchanged; full-suite module output path only",
        }
    )
    script = ROOT / "docs/benchmarks/t66f-b03/counters.py"
    sys.path.insert(0, str(ROOT / "backend"))
    spec = importlib.util.spec_from_file_location("ic05_matrix_subject", script)
    subject = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)
    tail = [
        {"offset": i.offset, "op": i.opname, "line": i.positions.lineno}
        for i in dis.get_instructions(subject.OwnershipContext.__enter__)
    ]
    (OUT / "entry-bytecode.json").write_text(
        json.dumps(
            {
                "runtime": sys.version,
                "subject_sha256": digest(script.read_bytes()),
                "instructions": tail,
                "exception_entries": [
                    str(e)
                    for e in dis.Bytecode(
                        subject.OwnershipContext.__enter__
                    ).exception_entries
                ],
            },
            indent=2,
        )
        + "\n"
    )
    source_paths = [
        "docs/benchmarks/t66f-b03/counters.py",
        "docs/benchmarks/t66f-b03/server.py",
        "backend/tests/test_logical_cost_ic01.py",
        "backend/tests/test_logical_cost_ic02.py",
        "backend/tests/test_logical_cost_ic03.py",
        "backend/tests/test_logical_cost_ic04.py",
        "backend/tests/test_logical_cost_ic05.py",
    ]
    sites = []
    for relative in source_paths:
        body = (ROOT / relative).read_text()
        for node in ast.walk(ast.parse(body)):
            if not isinstance(node, ast.Call):
                continue
            fn = ast.unparse(node.func)
            if fn.endswith((".__enter__", ".__exit__", ".enter_context", ".enter")):
                classification = (
                    "structured reservation"
                    if fn.endswith(".enter")
                    else "internal controlled release/entry"
                    if relative.endswith("counters.py")
                    else "historical controlled test lifecycle"
                    if "/tests/" in relative
                    else "different stdlib patch protocol"
                )
                sites.append(
                    {
                        "path": relative,
                        "line": node.lineno,
                        "call": fn,
                        "classification": classification,
                    }
                )
    for relative in [
        "docs/benchmarks/t66f-b03-ic01-p01/packet_server.py",
        "docs/benchmarks/t66f-b03-ir05/tests/test_ir05_lifecycle.py",
    ]:
        for node in ast.walk(ast.parse((ROOT / relative).read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"__enter__", "__exit__", "enter_context"}
            ):
                sites.append(
                    {
                        "path": relative,
                        "line": node.lineno,
                        "call": ast.unparse(node.func),
                        "classification": "immutable historical fixture; original bytes retained; not a current benchmark implementation caller",
                    }
                )
    (OUT / "call-sites.json").write_text(
        json.dumps(
            {
                "production_application_OwnershipContext_callers": 0,
                "shared_factory_covers": [
                    "scoped_value",
                    "installation",
                    "Collector.stage",
                    "authentication_hashes",
                    "instrument_workers",
                    "dispatch_scope",
                    "instrument",
                    "instrument_connections",
                ],
                "current_benchmark_migrations": 4,
                "manual_contract": "establish caller finally before explicit enter; immutable orchestration oracles retain their controlled lifecycle",
                "ExitStack_contract": "use context.enter(stack) after establishing stack cleanup; exit reserved before resource acquisition; no second resource owner",
                "sites": sites,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    result = {
        "task": "T6.6F-B03-IC05",
        "coverage": "PASS within documented structured/observer contract",
        "rows": matrix,
        "current_new_cases": len(current),
        "preserved_original_cases": len(rows["preserved-original-complete"]),
        "backend_diagnostic_cases": len(rows["diagnostic-complete"]),
        "actual_event_oracle": "native parser frame/raw bytes, cancelled A0/0B, valid B2 identical parses/4B; repeated B48/96B",
        "resource_oracle": "refs/stage/wrappers/holds at baseline, weak metadata refs0 with GC disabled; original hooks restored",
        "reachability": [
            {
                "boundary": "ordinary Task.cancel between synchronous enter instructions",
                "status": "NOT REACHABLE",
                "reason": "No await in acquisition; request at return is delivered at actual subsequent await, with body parse before await legitimately counted.",
            },
            {
                "boundary": "legacy return observer raises before caller receives value",
                "status": "REACHABLE AND COVERED",
                "reason": "unchanged IC043 + trace/profile tests execute original callback and actual SIGINT; rollback precedes propagation.",
            },
            {
                "boundary": "Python tracing re-enters normal tracing callback cleanup",
                "status": "NOT REACHABLE",
                "reason": "CPython disables tracing in trace callback; native setter failure is independently injected and verified.",
            },
            {
                "boundary": "opcode hook without prearmed frame on CPython3.12",
                "status": "NOT REACHABLE IN THAT CONFIGURATION",
                "reason": "Official sys docs and bounded runtime probe; tests prearm f_trace_opcodes before settrace and observe actual opcode events.",
            },
            {
                "boundary": "custom PEP669 observer on entry code",
                "status": "EXPLICIT INCOMPLETE BEFORE ACQUISITION",
                "reason": "Not silently accepted as zero work or hidden; no mandatory benchmark path uses it.",
            },
        ],
        "no_additional_global_handoff_owner_registry": True,
        "GC_resource_safety_dependency": False,
        "source_sha256": {
            p: digest((ROOT / p).read_bytes())
            for p in [
                "docs/benchmarks/t66f-b03/counters.py",
                "docs/benchmarks/t66f-b03/server.py",
                "backend/tests/test_logical_cost_ic05.py",
            ]
        },
        "independent_audit": "PENDING",
    }
    (OUT / "handoff-transition-matrix.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "rows": len(matrix),
                "new_tests": len(current),
                "original_IC04": len(original),
                "coverage": "PASS",
            }
        )
    )


if __name__ == "__main__":
    main()

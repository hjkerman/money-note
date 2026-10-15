"""실제 machine/JUnit/SQL evidence를 축약한다. 원 감사 artifact는 변경하지 않는다."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location("phase_a_collect", HERE.parent / "t66e4-audit/collect.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def load(path):
    return json.loads(path.read_text())


def compact_graph(value):
    value = audit.compact_state(value)
    for g in value.get("generations", {}).values():
        if "closure" in g:
            closure = g.pop("closure")
            g["closure_objects"] = len(closure)
            g["closure_sha256"] = audit.digest(sorted(closure))
    return value


def compact_cost(rows):
    result = []
    for row in rows:
        phases = []
        for value in row["phases"]:
            p = {k: v for k, v in value.items() if k not in ["objects", "sql_texts"]}
            p["sql_statement_counts"] = dict(Counter(value.get("sql_texts", [])))
            phases.append(p)
        result.append(dict(history=row["history"], required_objects=row["required_objects"], phases=phases,
                           pins=row["pins"], persisted=compact_graph(row["persisted"])))
    return result


def collect(folder):
    files = {
        "original_before": "original-before.log", "original_after_and_t01_t02": "focused-first.log",
        "new_test_compile_failure": "new-first.log", "new_initial": "new-second.log",
        "new_pre_native": "new-final.log", "native_focused": "native-focused.log", "new_final": "new-final-native.log",
        "independent_first_with_bad_path": "independent.log", "independent_pre_native": "independent-final.log",
        "independent_final": "independent-native-final.log", "concurrent_recovery": "concurrent.log",
        "p0_integration": "p0-integration.log", "historical_diagnostic": "historical-diagnostic.log",
        "flutter_pre_native_full": "flutter-full.log", "flutter_full": "flutter-final.log",
        "cost_initial": "cost/cost.log", "cost": "cost-final/cost.log",
    }
    summary = {k: audit.machine(folder / v) for k, v in files.items()}
    for key in ["flutter_full", "flutter_pre_native_full", "original_after_and_t01_t02"]:
        summary[key].pop("cases", None)  # per-file counts remain available
    for name in ["backend", "crash", "crash-final", "crash-strict", "crash-native-final", "phase-a-crash", "phase-a-native-final", "p0-replay", "e2-cleanup", "scripts"]:
        summary[name] = audit.junit(folder / (name + ".xml"))
        if name in ["backend", "scripts"]:
            summary[name].pop("cases", None)
    summary["p0_original"] = audit.junit(folder / "p0-original.xml")
    summary["p0_differential"] = load(folder / "p0-original/differential.json")
    backend = re.findall(r"(\d+) passed.*?(\d+) subtests passed", (folder / "backend.log").read_text())
    summary["backend_stdout_counts"] = dict(tests=int(backend[-1][0]), subtests=int(backend[-1][1])) if backend else None
    inventory = load(HERE.parent / "t66e4-audit/source-inventory.json")["files"]
    changed = {"mobile/lib/src/segmented/workspace.dart", "mobile/lib/src/segmented/store_frozen.dart"}
    preserved = []
    for row in inventory:
        if row["path"] not in changed:
            assert hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"], row["path"]
            preserved.append(row["path"])
    summary["e4_inventory_preserved"] = dict(total=len(inventory), unchanged=len(preserved), changed=sorted(changed))
    summary["checks_pre_native"] = load(folder / "checks.json") if (folder / "checks.json").exists() else None
    summary["checks_pre_concurrent"] = load(folder / "final-checks/checks.json") if (folder / "final-checks/checks.json").exists() else None
    summary["checks"] = load(folder / "final-checks-v2/checks.json") if (folder / "final-checks-v2/checks.json").exists() else summary["checks_pre_concurrent"]
    summary["source_hashes"] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ["mobile/lib/src/segmented/workspace.dart", "mobile/lib/src/segmented/store_frozen.dart",
                     "mobile/test/segmented_e4_a01_test.dart", "docs/benchmarks/t66e4-a01/crash_child_test.dart",
                     "docs/benchmarks/t66e4-a01/concurrent_recovery_test.dart",
                     "docs/benchmarks/t66e4-a01/collect.py", "docs/benchmarks/t66e4-a01/validate.py",
                     "docs/benchmarks/t66e4-a01/test_crash.py"]
    }
    before = load(folder / "before.json") if (folder / "before.json").exists() else load(HERE / "reproducer.json")["before"]
    after = load(folder / "after-final-native.json")
    concurrent = load(folder / "concurrent-state.json")
    for value in [before, after, concurrent]:
        value["independent_graph"] = compact_graph(value["independent_graph"])
    costs = load(folder / "cost-final/cost.json")
    original = load(HERE.parent / "t66e4-audit/cost.json")
    work_fields = ["sql", "returned_rows", "body_bytes", "raw_nodes", "index_nodes", "pin_insert",
                   "pin_delete", "pin_update", "full_verify_calls", "frozen_recovery_calls",
                   "legacy_full_reads", "lineage_hashes"]
    comparison = []
    for new, old in zip(costs, original, strict=True):
        assert new["history"] == old["history"]
        for name in ["warm1", "warm2", "store_only_warm", "unrelated_accepted", "warm_after_fallback", "warm_after_reopen"]:
            a = next(p for p in new["phases"] if p["name"] == name)
            b = next(p for p in old["phases"] if p["name"] == name)
            assert {k: a[k] for k in work_fields} == {k: b[k] for k in work_fields}
            comparison.append(dict(history=new["history"], phase=name, unchanged_work=True))
    crashes = [load(p) for p in sorted((folder / "crash-final").glob("*.json"))]
    strict_crashes = [load(p) for p in sorted((folder / "crash-strict").glob("*.json"))]
    final_crashes = [load(p) for p in sorted((folder / "crash-native-final").glob("*.json"))]
    full = summary["flutter_full"].get("files", {})
    summary["existing_e4_authority_race"] = sum(full.get(n, {}).get("success", 0) for n in
        ["segmented_e4_handoff_test.dart", "segmented_adapter_authority_test.dart"])
    summary["existing_e4_process_crash"] = sum(full.get(n, {}).get("success", 0) for n in
        ["segmented_e4_handoff_crash_test.dart", "segmented_adapter_crash_test.dart"])
    summary["new_correction_cases"] = dict(unit=summary["new_final"].get("counts", {}),
        concurrent=summary["concurrent_recovery"].get("counts", {}),
        process_crash=summary["crash-native-final"], full_unit=full.get("segmented_e4_a01_test.dart", {}))
    if summary["independent_final"].get("done_success") and summary["phase-a-native-final"].get("tests"):
        summary["original_phase_a_cases"] = (summary["independent_final"]["counts"].get("success", 0)
            + summary["cost"]["counts"].get("success", 0)
            + summary["phase-a-native-final"]["tests"] + summary["p0-replay"]["tests"])
    return {"summary": summary, "reproducer": {"before": before, "after": after},
            "cost": compact_cost(costs), "cost_comparison": comparison, "crashes": crashes,
            "crashes_strict": strict_crashes, "crashes_final": final_crashes,
            "concurrent_recovery": concurrent}


if __name__ == "__main__":
    evidence = collect(Path(sys.argv[1]))
    if "--require-complete" in sys.argv[2:]:
        s = evidence["summary"]
        for key in ["flutter_full", "new_final", "concurrent_recovery", "independent_final", "cost", "p0_integration"]:
            assert s[key]["done_success"] is True, key
            assert not s[key]["counts"].get("failure", 0) and not s[key]["errors"], key
        assert s["flutter_full"]["counts"] == {"success": 1461, "skip": 2}
        assert s["original_before"]["counts"] == {"failure": 1}
        assert s["new_final"]["counts"] == {"success": 21}
        assert s["concurrent_recovery"]["counts"] == {"success": 1}
        assert s["original_phase_a_cases"] == 45
        for key in ["backend", "crash-native-final", "phase-a-native-final", "p0-replay", "e2-cleanup", "scripts"]:
            assert not s[key]["failures"] and not s[key]["errors"], key
        assert all(v["exit"] == 0 for v in s["checks"].values())
        for state in [evidence["reproducer"]["after"], evidence["concurrent_recovery"]]:
            assert state["source_before_old_recovery"] == state["source_after_old_recovery"]
            assert state["frozen_read_error"] is None and state["fresh_recovery_error"] is None
            assert state["legacy_b_unchanged_after_success"] and state["unknown_marker_unchanged"]
        s["completion_gate_assertions"] = "PASS"
    print(json.dumps(evidence, ensure_ascii=False, indent=2))

"""실제 완료 event와 독립 SQL/graph oracle를 읽는다. 저장은 호출자 apply_patch가 담당한다."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    "original_rai_collect", HERE.parent / "t66e4-a01-reaudit/collect.py"
)
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
audit = original.audit


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def compact_reproduction(rows):
    rows = copy.deepcopy(rows)
    for row in rows:
        for key in ["before", "before_recovery", "after"]:
            if key in row:
                row[key] = original.disk(row[key])
        if "independent_graph" in row:
            row["independent_graph"] = original.graph(row["independent_graph"])
    return rows


def collect(folder, complete=False):
    folder = Path(folder)
    paths = {
        "original_before": "before.log", "original_after": "reaudit-complete-final.log",
        "phase_a_and_a01_concurrent": "phase-a-verified.log",
        "flutter_full": "flutter-complete-final.log", "p0_integration": "p0-integration.log",
        "historical_diagnostic": "historical-diagnostic.log",
        "cost_before": "cost-before/cost.log", "cost_after": "cost-owner-final/cost.log",
        "phase_a_cost": "phase-a-cost/cost.log",
    }
    summary = {name: audit.machine(folder / path) for name, path in paths.items()}
    for name in ["backend", "crash-complete-final", "prior-crashes-p0-verified", "e2-cleanup"]:
        summary[name] = audit.junit(folder / (name + ".xml"))
    full = summary["flutter_full"]
    summary["new_unit"] = full.get("files", {}).get("segmented_e4_ra01_test.dart")
    summary["new_case_count"] = (summary["new_unit"] or {}).get("success", 0) + 7 + 2
    summary["checks"] = read(folder / "checks-release-final/checks.json")
    summary["intermediate_runs"] = {
        name: audit.machine(folder / (name + ".log"))
        for name in ["new-first", "new-second", "new-third", "flutter-full-final"]
    }
    summary["historical_p0_fixture"] = audit.junit(folder / "p0-historical.xml")
    log = (folder / "backend.log").read_text(errors="replace")
    match = re.findall(r"(\d+) passed.*?(\d+) subtests passed", log)
    summary["backend_counts"] = dict(tests=int(match[-1][0]), subtests=int(match[-1][1])) if match else None
    costs_before = read(folder / "cost-before/cost.json") or []
    costs_after = read(folder / "cost-owner-final/cost.json") or []
    comparisons = []
    for before, after in zip(costs_before, costs_after, strict=True):
        phases_before = {p["name"]: p for p in before["phases"]}
        for new in after["phases"]:
            if new["name"] in ["warm1", "warm2", "store_only_warm", "unrelated_accepted", "warm_after_fallback", "warm_after_reopen"]:
                old = phases_before[new["name"]]
                fields = ["sql", "body_bytes", "raw_nodes", "index_nodes", "raw_rows",
                          "full_verify_calls", "frozen_recovery_calls", "legacy_full_reads",
                          "lineage_hashes", "pin_insert", "pin_delete", "pin_update"]
                comparisons.append(dict(history=before["history"], phase=new["name"],
                                        before={k: old.get(k) for k in fields},
                                        after={k: new.get(k) for k in fields}))
                assert all(new.get(k) == old.get(k) for k in fields)
    crash = [read(p) for p in sorted((folder / "crash-complete-final").glob("*.json"))]
    checks = summary["checks"] or {}
    if complete:
        assert summary["original_before"]["counts"] == {"failure": 3}
        assert summary["original_before"]["done_success"] is False
        assert summary["original_after"]["counts"] == {"success": 18}
        assert summary["phase_a_and_a01_concurrent"]["counts"] == {"success": 37}
        assert full["done_success"] is True and not full["errors"]
        assert full["counts"] == {"success": 1503, "skip": 2}
        assert summary["new_unit"] == {"success": 42}
        assert full["files"]["segmented_e4_a01_test.dart"] == {"success": 21}
        assert summary["p0_integration"]["counts"] == {"success": 18}
        assert summary["historical_diagnostic"]["counts"] == {"success": 3, "failure": 2}
        assert summary["cost_after"]["counts"] == {"success": 4}
        assert summary["phase_a_cost"]["counts"] == {"success": 2}
        assert summary["crash-complete-final"]["tests"] == len(crash) == 7
        assert summary["prior-crashes-p0-verified"]["tests"] == 17
        for name in ["backend", "crash-complete-final", "prior-crashes-p0-verified", "e2-cleanup"]:
            assert summary[name]["errors"] == summary[name]["failures"] == 0, name
        assert summary["backend_counts"] == dict(tests=1315, subtests=1540)
        assert summary["historical_p0_fixture"]["failures"] == 1
        assert summary["historical_p0_fixture"]["errors"] == 0
        assert len(comparisons) == 12
        assert checks and all(v["exit"] == 0 for v in checks.values() if "exit" in v)
        for name in ["original_after", "phase_a_and_a01_concurrent", "p0_integration", "cost_before", "cost_after", "phase_a_cost"]:
            assert summary[name]["done_success"] is True, name
        for name in ["cost-before", "cost-owner-final", "phase-a-cost"]:
            assert read(folder / name / "cost-exit.json")["exit"] == 0, name
    # Keep current cases, not full success logs. Historical harness failures are
    # separately identified; never hide a current correctness failure in them.
    cases = {key: value.get("cases", []) for key, value in summary.items()
             if key in paths or key in ["crash-complete-final", "prior-crashes-p0-verified"]}
    cases["flutter_full"] = [c for c in cases["flutter_full"]
                              if c["file"] in ["segmented_e4_ra01_test.dart", "segmented_e4_a01_test.dart"]]
    for value in summary.values():
        if isinstance(value, dict):
            value.pop("cases", None)
    for value in summary["intermediate_runs"].values():
        value.pop("cases", None)
        for error in value.get("errors", []):
            error["error"] = str(error.get("error"))[:1200]
    summary["completion_guard"] = "COMPLETE" if complete else "PROVISIONAL"
    summary["independent_reaudit"] = "PENDING"
    summary["activation"] = dict(r1="CLOSED", phase_b="NOT_STARTED", deployed=False)
    after = read(folder / "reaudit-complete-final.json") or []
    native = read(folder / "cost-owner-final/cost.json.handoff.json")
    if native:
        for row in native:
            for phase in row["phases"]:
                refs = phase.get("objects", [])
                if len(refs) > 32:
                    phase.pop("objects")
                    phase["object_reads"] = len(refs)
                    phase["object_reads_sha256"] = audit.digest(refs)
                    phase["unique_object_reads"] = len(set(refs))
                    phase["unique_objects_sha256"] = audit.digest(sorted(set(refs)))
    result = {
        "summary.json": summary, "cases.json": cases,
        "reproducer-after.json": compact_reproduction([r for r in after if r.get("id") in ["RA16", "RA17", "RA18"]]),
        "cost-before.json": original.costs(costs_before),
        "cost-after.json": original.costs(costs_after),
        "cost-comparison.json": comparisons,
        "native-handoff-cost.json": native,
        "crashes.json": crash,
        "p0-differential.json": read(folder / "p0-audit/differential.json"),
        "corruption-selector.json": read(folder / "corruption-selector.json"),
    }
    hashes = {}
    for path in [*(ROOT / "mobile/lib/src/segmented").glob("*.dart"),
                 ROOT / "mobile/lib/src/app_state.dart", ROOT / "mobile/test/segmented_e4_ra01_test.dart",
                 *HERE.glob("*.py"), *HERE.glob("*.dart")]:
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    result["source-hashes.json"] = hashes
    observations = []
    for line in (folder / "observed-original-cost/cost.log").read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "print" and "frozen_corruption_target" in event.get("message", ""):
            observations.append(json.loads(event["message"]))
    result["cost-fixture-observations.json"] = observations
    return result


if __name__ == "__main__":
    print(json.dumps(collect(sys.argv[1], "--require-complete" in sys.argv[2:]), ensure_ascii=False))

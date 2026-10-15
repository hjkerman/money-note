"""이번 실행의 machine/JUnit/실제 SQLite·SQL observer 증거만 집계한다."""
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_phase_a", HERE.parent / "t66e4-audit/collect.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def graph(value):
    value = audit.compact_state(value)
    for generation in value.get("generations", {}).values():
        if "closure" in generation:
            closure = generation.pop("closure")
            generation["closure_count"] = len(closure)
            generation["closure_sha256"] = audit.digest(sorted(closure))
    return value


def disk(value):
    value = copy.deepcopy(value)
    import base64
    for key in ["source", "baseline", "pending"]:
        if key not in value:
            continue
        raw = base64.b64decode(value.pop(key))
        value[key + "_bytes"] = len(raw)
        value[key + "_sha256"] = hashlib.sha256(raw).hexdigest()
        if key != "baseline":
            value[key] = json.loads(raw)
    if "refs" in value:
        refs = value.pop("refs")
        value["refs_count"] = len(refs)
        value["refs_sha256"] = audit.digest(refs)
    return value


def costs(rows):
    rows = copy.deepcopy(rows)
    for row in rows:
        row["persisted"] = graph(row["persisted"])
        for phase in row["phases"]:
            objects = phase.pop("objects", [])
            phase["object_identities_count"] = len(objects)
            phase["object_identities_sha256"] = audit.digest(sorted(objects))
            # sql_texts already contains UNIQUE statements; never report it as frequencies.
    return rows


def main(folder, require_complete=False):
    folder = Path(folder)
    machines = {
        "original": "original-reproducer.log", "correction_unit": "correction-tests.log",
        "original_phase_a": "phase-a-independent.log", "correction_concurrent": "correction-concurrent.log",
        "new": "independent-final.log", "new_extra": "independent-extra-final.log",
        "newer_failed": "newer-failed.log",
        "invalid_predecessor": "invalid-predecessor-final.log", "invalid_predecessor_install": "invalid-predecessor-install-final.log",
        "invalid_predecessor_first": "invalid-predecessor.log",
        "invalid_predecessor_install_first": "invalid-predecessor-install.log",
        "journal_observation": "journal-observation.log", "ticket_observation": "ticket-observer-complete/observed.log",
        "original_cost": "original-cost/cost.log", "new_cost": "new-cost-final/cost.log",
        "flutter_full": "flutter-full.log", "historical_diagnostic": "historical-diagnostic.log",
        "p0_integration": "p0-integration.log",
        "interrupted_harness": "independent.log", "empty_extra_selection": "independent-extra.log",
        "observer_path_error": "ticket-observer/observed.log",
    }
    summary = {key: audit.machine(folder / path) for key, path in machines.items()}
    for name in ["phase-a-crash", "correction-crash", "p0-compatible", "p0-original", "e2-cleanup", "backend-full", "backend-focused", "backend-final", "scripts"]:
        summary[name] = audit.junit(folder / (name + ".xml"))
    groups = {
        "new_independent": ["new", "new_extra", "newer_failed", "new_cost", "invalid_predecessor", "invalid_predecessor_install"],
        "original_phase_a_cases": ["original_phase_a", "original", "original_cost", "phase-a-crash", "p0-compatible"],
        "implementation_correction_cases": ["correction_unit", "correction_concurrent", "correction-crash"],
    }
    cases = []
    for group, keys in groups.items():
        group_cases = []
        for key in keys:
            for case in summary[key].get("cases", []):
                group_cases.append(dict(group=group, run=key, **case))
        summary[group] = dict(Counter(case["result"] for case in group_cases))
        cases.extend(group_cases)
    summary["checks"] = {p.name: read(p) for p in folder.glob("*-exit.json")}
    summary["format_changed"] = read(folder / "format-changed.json")
    summary["format_full"] = read(folder / "format-full.json")
    summary["preservation"] = read(HERE / "preservation.json")
    final_backend = folder / "backend-final.log"
    text = final_backend.read_text(errors="replace") if final_backend.exists() else ""
    matched = re.findall(r"(\d+) passed.*?(\d+) subtests passed", text)
    summary["backend_stdout_counts"] = dict(tests=int(matched[-1][0]), subtests=int(matched[-1][1])) if matched else None
    summary["p0_differential"] = read(folder / "p0-original/differential.json")
    if require_complete:
        assert summary["new_independent"] == {"success": 17, "failure": 3}
        assert summary["invalid_predecessor"]["counts"] == {"failure": 2}
        assert summary["invalid_predecessor_install"]["counts"] == {"failure": 1}
        assert summary["invalid_predecessor"]["done_success"] is False
        assert summary["invalid_predecessor_install"]["done_success"] is False
        assert summary["original_phase_a_cases"] == {"success": 45}
        assert summary["implementation_correction_cases"] == {"success": 28}
        assert summary["flutter_full"]["done_success"] is True
        assert summary["flutter_full"]["counts"] == {"success": 1461, "skip": 2}
        assert summary["backend_stdout_counts"] == dict(tests=1315, subtests=1540)
        assert summary["backend-final"]["failures"] == summary["backend-final"]["errors"] == 0
        for name in ["original", "correction_unit", "correction_concurrent", "original_phase_a", "new", "new_extra", "newer_failed", "original_cost", "new_cost", "p0_integration", "ticket_observation"]:
            assert summary[name]["done_success"] is True, name
        for name in ["original-reproducer", "correction-tests", "correction-concurrent", "phase-a-independent", "independent-final", "independent-extra-final", "newer-failed", "phase-a-crash", "correction-crash", "p0-compatible", "flutter-full", "backend-final", "analyze", "build", "ruff", "compileall"]:
            value = read(folder / (name + "-exit.json"))
            assert value is not None and value["exit_code"] == 0, (name, value)
        for name in ["original-cost", "new-cost-final"]:
            assert read(folder / name / "cost-exit.json")["exit"] == 0, name
        for name in ["invalid-predecessor-final", "invalid-predecessor-install-final"]:
            assert read(folder / (name + "-exit.json"))["exit_code"] == 1, name
    summary["audit_verdict"] = "FAIL"
    summary["confirmed_finding"] = {"id": "E4-RA01", "severity": "MEDIUM", "phase_b_blocked": True}
    save("cases.json", cases)
    for value in summary.values():
        if isinstance(value, dict):
            value.pop("cases", None)
    save("summary.json", summary)
    rows = []
    for name in ["independent-final.json", "independent-extra-final.json", "newer-failed.json", "journal-observation.json", "invalid-predecessor-final.json", "invalid-predecessor-install-final.json"]:
        for value in read(folder / name) or []:
            for key in ["before_reopen", "after_reopen", "state", "before_recovery", "after_native_install"]:
                if key in value:
                    value[key] = disk(value[key])
            if "independent_graph" in value:
                value["independent_graph"] = graph(value["independent_graph"])
            rows.append(dict(run=name, **value))
    save("persisted.json", rows)
    save("finding-e4-ra01.json", [row for row in rows if row["id"] in ["RA16", "RA17", "RA18"]])
    value = read(folder / "original-reproducer.json")
    if value:
        value["independent_graph"] = graph(value["independent_graph"])
    save("original-reproducer.json", value)
    observer = folder / "ticket-observer-complete"
    tickets = [json.loads(line) for line in (observer / "tickets.jsonl").read_text().splitlines()]
    observed = read(observer / "persisted.json")
    observed["independent_graph"] = graph(observed["independent_graph"])
    save("operation-observation.json", dict(tickets=tickets, source_a=read(observer / "source-a.json"), final_source=observed["source_after_old_recovery"], final_persisted=observed))
    save("original-cost.json", costs(read(folder / "original-cost/cost.json")))
    save("new-cost.json", costs(read(folder / "new-cost-final/cost.json")))
    crashes = []
    for name in ["phase-a-crash", "correction-crash"]:
        for path in sorted((folder / name).glob("*.json")):
            value = read(path)
            for key in ["immediate", "recovered"]:
                if key in value:
                    value[key] = graph(value[key])
            crashes.append(dict(group=name, **value))
    save("crashes.json", crashes)
    print(json.dumps({key: summary[key] for key in groups}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], require_complete="--require-complete" in sys.argv)

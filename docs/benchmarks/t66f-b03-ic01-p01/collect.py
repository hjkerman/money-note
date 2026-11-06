"""P01 실제 exit·범위·분석 모델을 분리하는 최종 evidence. 제품 telemetry 아님."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"


def load(name):
    return json.loads((OUT / name).read_text())


def machine(name):
    values = Counter()
    done = None
    errors = []
    for line in gzip.open(OUT / (name + ".log.gz"), "rt"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict):
            continue
        if r.get("type") == "done":
            done = r["success"]
        if r.get("type") == "error":
            errors.append(r["error"])
        if r.get("type") == "testDone" and not r.get("hidden"):
            values[
                "SKIP"
                if r["skipped"]
                else "PASS"
                if r["result"] == "success"
                else "FAIL"
            ] += 1
    return {"counts": dict(values), "done": done, "errors": errors}


def main():
    checks = {}
    for name in [
        "backend-targeted",
        "flutter-targeted",
        "current-independent",
        "small-http",
        "components-final",
        "components-no-profile",
        "cost-parts-final",
        "historical-3",
        "packets",
        "cleanup",
        "preparation",
        "boundaries",
    ]:
        r = load(name + ".json")
        r["sampled_process_tree_peak_rss_bytes"] = max(
            (s[1] for s in r.pop("rss_samples", [])), default=None
        )
        if name != "backend-targeted":
            r["machine"] = machine(name)
        checks[name] = r
    tree = ET.parse(OUT / "backend-targeted.xml")
    checks["backend-targeted"]["junit"] = {
        k: len(list(tree.iter(k))) for k in ["testcase", "failure", "error", "skipped"]
    }
    proposal = load("preparation-results.json")
    result = {
        "schema_version": 1,
        "run_id": "T6.6F-B03-IC01-P01/preflight/1",
        "H": None,
        "D": 0,
        "N": 100000,
        "H_note": "original B02 fixed-H seed; no new full H-byte accounting claim",
        "environment": platform.platform(),
        "instrumentation_version": "unchanged IC01 sealed source",
        "go_no_go": "NO-GO",
        "verdict": "PREFLIGHT NO-GO — OBSERVER OVERHEAD CORRECTION REQUIRED",
        "new_full_100k_cold_attempts": 0,
        "new_100k_bounded_packet_fixture_count": 1,
        "full_run_snapshot_status": {
            "generation": "NOT RUN",
            "D3": "bounded subset only",
            "E2": "bounded subset only",
            "E1": "bounded subset only",
            "E3": "NOT RUN for 100k",
            "E4": "NOT RUN for 100k",
        },
        "checks": checks,
        "historical_baselines": load("historical-baselines.json"),
        "model": load("feasibility-model.json"),
        "preservation": load("preservation.json"),
        "full_backend_rerun": False,
        "full_flutter_rerun": False,
        "reason_not_rerun": "all 2852 preexisting files unchanged; P01 contains only new diagnostics; prior IC01 full results remain historical",
        "new_targeted_scenarios": {
            "PASS": 5,
            "FAIL": 1,
            "note": "profile/unprofile E1, parts, preparation, cleanup PASS; actual 100k packet run FAIL at shutdown. No double counting retries or old IC01 cases",
        },
        "proposal_counter_equivalence": "all existing SQL maps exactly equal; actual native rows/bytes equal in existing prepared vs execute API comparison",
        "proposal_bytes": proposal["bytes"],
        "proposal_objects": proposal["objects"],
        "scope_exclusions": [
            "full instrumented 100k execution",
            "complete five-point I25 proof",
            "physical I/O",
            "Android VFS/power",
            "unprofiled native zero fields are NOT INSTRUMENTED",
            "packet local cohort snapshot excludes subsequent cleanup release",
        ],
        "cleanup_uncertainty": "small close-client-before-exit PASS; no second large fixture replay and no retroactive PASS for failed 100k packet run",
        "commit": "NONE",
        "push": "NOT PERFORMED",
        "IC01": "INCOMPLETE",
        "independent_reaudit_ready": False,
    }
    result["refs"] = {
        k: subprocess.check_output(cmd, cwd=ROOT, text=True).strip()
        for k, cmd in {
            "local": ["git", "rev-parse", "HEAD", "main", "origin/main"],
            "actual_remote_main": ["git", "ls-remote", "origin", "refs/heads/main"],
            "staged": ["git", "diff", "--cached", "--name-only"],
            "status": ["git", "status", "--short"],
        }.items()
    }
    result["current_diagnostic_source_sha256"] = {
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        for p in [
            "docs/benchmarks/t66f-b03/counters.py",
            "docs/benchmarks/t66f-b03/server.py",
            "mobile/test/support/logical_cost_sqlite.dart",
        ]
    }
    (OUT / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "new_full_runs": 0,
                "checks": {k: v["status"] for k, v in checks.items()},
                "preserved": result["preservation"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

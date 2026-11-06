"""실패 원인과 실제 갱신 구간을 보존된 trace에서 추가 대조한다."""

import gzip
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "evidence"
analysis = json.loads((OUT / "full-analysis.json").read_text())
rows = [
    json.loads(line)
    for line in gzip.open(OUT / "actual-server-requests.jsonl.gz", "rt")
]
full = [r for r in rows if r["label"] == "full"]
renewals = []
for row in full:
    if row["status"] != 410:
        continue
    later = [r for r in full if r["start_ns"] > row["start_ns"]]
    manifest = next((r for r in later if "manifest" in r), None)
    resumed = next(
        (r for r in later if r["status"] == 200 and r["path"].endswith("/objects")),
        None,
    )
    renewals.append(
        {
            "expired_request_serial": row["serial"],
            "expired_request_wall_s": row["wall_ns"] / 1e9,
            "new_authorized_manifest_serial": manifest["serial"] if manifest else None,
            "new_manifest_wall_s": manifest["wall_ns"] / 1e9 if manifest else None,
            "resumed_request_serial": resumed["serial"] if resumed else None,
            "expiry_request_start_to_resumed_request_start_s": (
                (resumed["start_ns"] - row["start_ns"]) / 1e9 if resumed else None
            ),
            "new_manifest_response_boundary_to_resumed_request_s": (
                (resumed["start_ns"] - manifest["end_ns"]) / 1e9
                if resumed and manifest
                else None
            ),
            "terminal_attempt_limit": manifest is None,
        }
    )
clocks = [
    json.loads(s) for s in (OUT / "host-clock-samples.jsonl").read_text().splitlines()
]
offsets = [
    c["utc_ns"] - (c["monotonic_before_ns"] + c["monotonic_after_ns"]) // 2
    for c in clocks
]
analysis["actual_renewals"] = renewals
analysis["clock_offset_range_ns"] = [min(offsets), max(offsets)]
analysis["clock_offset_span_ns"] = max(offsets) - min(offsets)
analysis["failure_classification"] = "OBSERVATION_EXPIRED"
analysis["causal_attribution"] = {
    "lease_exhaustion": "MEASURED",
    "external_experiment_termination": "NONE",
    "resource_guard_failure": "NONE",
    "instrumentation_as_sole_cause": "NOT_ESTABLISHED",
    "reason": "Only bounded paired prefixes were OFF/ON. Two historical full runs differ in host/cache/identity and are not simultaneous full OFF controls.",
    "product_correctness_failure": "NOT_REPRODUCED",
    "measurement_coverage_error": "NOT_DETECTED_FOR_EXECUTED_BOUNDARIES",
}
analysis["missing_mandatory_evidence"] = [
    "Complete instrumented 400532-object cold acquisition under TTL900/max3",
    "Full-run graph closure and E3 accepted-generation publication",
    "Full-run E4 financial read and terminal E3/E4 cost snapshots",
]
analysis["additional_measurement_limits"] = [
    "Renewal-exclusive client hash/validation byte subdivision not isolated; cumulative retry work remains counted exactly in E2",
    "Pure E2 parser CPU and complete exclusive observer allocations not isolated",
    "No full-size OFF run in this campaign; no runtime population p95 from n=3 pairs",
    "P03 per-SQL/per-UDF Stopwatch, checkpoint JSON and RSS timers add observer workload; exclusive cost not isolated. Failure of untimed original P02 mode is not established.",
]
analysis["causal_attribution"]["additional_P03_timing_observer_overhead"] = (
    "NOT_ISOLATED"
)
analysis["smallest_next_experiment"] = (
    "Bounded paired OFF/ON replay from equivalent late-stage disposable stores, using the preserved failed staging state and same graph; separate backend D3/HTTP, E2 and diagnostic SQL costs without a second full cold run or TTL changes."
)
(OUT / "full-analysis.json").write_text(
    json.dumps(analysis, ensure_ascii=False, indent=2) + "\n"
)
print(
    json.dumps({"failure": "OBSERVATION_EXPIRED", "renewal_transitions": len(renewals)})
)

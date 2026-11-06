"""관측별 역사 진행률과 actual E1 pair 차이. 실제 full-run 결과가 아니다."""

import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"


def stats(xs):
    ordered = sorted(xs)
    return {
        "n": len(xs),
        "median": statistics.median(xs),
        "minimum": min(xs),
        "maximum": max(xs),
        "p95_nearest_rank": ordered[math.ceil(0.95 * len(xs)) - 1],
    }


def main():
    base = json.loads((OUT / "historical-baselines.json").read_text())
    c = json.loads((OUT / "components-no-profiling.json").read_text())
    profiled = json.loads((OUT / "components.json").read_text())
    result = {
        "schema_version": 1,
        "scope": "ANALYTICAL ESTIMATE; per-observation productive rates; not full path observation",
        "sample_objects": c["objects"],
        "sample_bytes": c["bytes"],
        "sample_kinds": c["sample_kinds"],
        "measured": {},
        "models": {},
        "uncertainty": [
            "Each sample uses a new small E1 DB, whereas a full run grows to >600MiB and has extra traversal reads",
            "Sample selected by kind/hash; original graph fixed-H and full distribution are separately recorded",
            "Timed native/SqlCosts delegates add perturbation to both modes; inclusive timings overlap",
            "Historical server harness overhead and current host load are not identical; no guaranteed future deadline",
            "Packet order/cache reuse across renewals may differ; rates by historical observation are not interchangeable leases",
            "Only cold insertion overhead is extrapolated here; backend/E2/reused work excluded, not claimed zero",
        ],
    }
    frequency = c["stopwatch_frequency"]
    result["unprofiled_timing_coverage"] = (
        "native/callback/add timers and native statement delegates disabled: raw zero fields mean NOT INSTRUMENTED, not zero work"
    )
    result["profiled_breakdown"] = {}
    result["profiled_breakdown_unit"] = (
        "seconds; native includes callbacks; callback includes add"
    )
    for enabled in [False, True]:
        rows = [
            r for r in profiled["records"] if r["enabled"] == enabled and not r["reuse"]
        ]
        result["profiled_breakdown"][str(enabled)] = {
            k: stats([r[k] / frequency for r in rows])
            for k in ["native_ticks", "callback_ticks", "add_ticks"]
        }
        result["profiled_breakdown"][str(enabled)]["counts"] = {
            k: stats([r[k] for r in rows])
            for k in ["statements", "callback_calls", "add_calls"]
        }
    deltas = []
    for reuse in [False, True]:
        groups = {}
        for enabled in [False, True]:
            rows = [
                r
                for r in c["records"]
                if r["enabled"] == enabled and r["reuse"] == reuse
            ]
            groups[str(enabled)] = {
                k: stats([r[k] for r in rows])
                for k in [
                    "wall_us",
                    "cpu_ticks",
                    "transactions",
                    "snapshot_us",
                ]
            }
        pair_delta = [
            next(
                r["wall_us"]
                for r in c["records"]
                if r["enabled"] and r["reuse"] == reuse and r["repeat"] == n
            )
            - next(
                r["wall_us"]
                for r in c["records"]
                if not r["enabled"] and r["reuse"] == reuse and r["repeat"] == n
            )
            for n in range(1, 6)
        ]
        result["measured"]["reuse" if reuse else "cold"] = {
            "groups": groups,
            "paired_extra_us": stats(pair_delta),
        }
        if not reuse:
            deltas = pair_delta
    for run in ["independent", "implementation"]:
        rows = base[run]["observations"]
        models = []
        for label, delta in [
            ("minimum_pair", min(deltas)),
            ("median_pair", statistics.median(deltas)),
            ("maximum_pair", max(deltas)),
        ]:
            extra_per_object = delta / 1e6 / c["objects"]
            progress = []
            for row in rows:
                product_s_per_object = row["productive_elapsed_s"] / row["new_objects"]
                # Each lease separately. Zero renewal/setup reserve is optimistic;
                # this does not allocate one aggregate 2700-second deadline.
                possible = 900 / (product_s_per_object + extra_per_object)
                progress.append(
                    {
                        "observation": row["number"],
                        "historical_productive_s_per_object": product_s_per_object,
                        "extra_e1_s_per_new_object": extra_per_object,
                        "optimistic_new_object_capacity_in_one_900s_lease": int(
                            possible
                        ),
                        "historical_new_objects": row["new_objects"],
                        "historical_headroom_s": row["last_success_headroom_s"],
                    }
                )
            models.append(
                {
                    "sample": label,
                    "observations": progress,
                    "sum_of_separate_capacity_estimates": sum(
                        p["optimistic_new_object_capacity_in_one_900s_lease"]
                        for p in progress
                    ),
                    "target": 400532,
                }
            )
        result["models"][run] = models
    packet = json.loads((OUT / "packet-results.json").read_text())
    backend = [r for r in packet["backend"]["rows"] if r["stage"] == "transfer"][30:]
    assert len(backend) == len(packet["samples"]) == 30
    assert all(a["enabled"] == b["enabled"] for a, b in zip(backend, packet["samples"]))
    result["actual_http_packets"] = {}
    for enabled in [False, True]:
        client = [r for r in packet["samples"] if r["enabled"] == enabled]
        server = [r for r in backend if r["enabled"] == enabled]
        result["actual_http_packets"][str(enabled)] = {
            "http_us": stats([r["http_us"] for r in client]),
            "validation_us": stats([r["validation_us"] for r in client]),
            "backend_wall_us": stats([r["wall_ns"] / 1000 for r in server]),
            "backend_cpu_us": stats([r["cpu_ns"] / 1000 for r in server]),
            "objects_per_packet": 64,
        }
    result["http_counter_complete"] = packet["backend"]["complete"]
    result["http_cleanup_result"] = (
        "FAIL: after measurement assertions, original server join fence failed; no lease failure; separate 1k close-client-before-exit regression PASS"
    )
    result["decision"] = (
        "NO-GO — measured observer cost makes full run unjustified. No full 100k acquisition attempted; model is not a demonstrated expiry"
    )
    (OUT / "feasibility-model.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                run: [
                    (r["sample"], r["sum_of_separate_capacity_estimates"]) for r in rows
                ]
                for run, rows in result["models"].items()
            }
        )
    )


if __name__ == "__main__":
    main()

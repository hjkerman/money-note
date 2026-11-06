"""역사 두 실행과 실제 paired critical path를 구분한 세 lease 민감도 모델."""

import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"


def main():
    a = json.loads((OUT / "analysis.json").read_text())
    pairs = a["pairs"]
    tails = a["tail_stratum"]
    h = a["historical"]
    target = 400532
    deltas = [
        tails[f"prefix-{i}-on"]["seconds_per_object"]
        - tails[f"prefix-{i}-off"]["seconds_per_object"]
        for i in range(3)
    ]
    prefix_extras = [p["wall_extra_us"] / 1e6 for p in pairs]
    prefix_objects = pairs[0]["objects"]
    renewal_on = a["renewal"]["renew-on"]
    renewal_off = a["renewal"]["renew-off"]
    renewal_extra = max(
        0,
        renewal_on["expiry_start_to_resumed_request_start_s"]
        - renewal_off["expiry_start_to_resumed_request_start_s"],
    )
    results = {}
    for label, hist in h.items():
        rows = []
        first = hist["observations"][0]
        prefix_last = hist["first_160"][-1]
        prefix_ns = prefix_last["end_ns"] - first["start_ns"]
        assert all("new_global_hashes" in r for r in hist["first_160"])
        assert sum(r["new_global_hashes"] for r in hist["first_160"]) == prefix_objects
        remaining = first["new_objects"] - prefix_objects
        rate_after_prefix = (
            first["productive_elapsed_s"] - prefix_ns / 1e9
        ) / remaining
        for scenario, delta, prefix_extra in [
            ("min", min(deltas), min(prefix_extras)),
            ("median", statistics.median(deltas), statistics.median(prefix_extras)),
            ("max", max(deltas), max(prefix_extras)),
        ]:
            observations = []
            for i, old in enumerate(hist["observations"]):
                if i == 0:
                    initial_s = prefix_ns / 1e9 + prefix_extra
                    rate = rate_after_prefix + delta
                    capacity = prefix_objects + max(0, int((900 - initial_s) / rate))
                    assumptions = "historical first160 prefix + measured paired full-prefix delta, then historical tail rate + actual paired index-cycle delta"
                else:
                    initial_s = renewal_extra
                    rate = old["productive_elapsed_s"] / old["new_objects"] + delta
                    capacity = max(0, int((900 - initial_s) / rate))
                    assumptions = "historical productive per-object mean + measured index-cycle delta; positive measured renewal delta reserved inside each fresh lease conservatively"
                observations.append(
                    {
                        "number": i + 1,
                        "capacity_estimate_objects": capacity,
                        "initial_or_renewal_seconds": initial_s,
                        "seconds_per_object_estimate": rate,
                        "historical_objects": old["new_objects"],
                        "historical_productive_seconds": old["productive_elapsed_s"],
                        "assumptions": assumptions,
                    }
                )
            capacity = sum(r["capacity_estimate_objects"] for r in observations)
            rows.append(
                {
                    "scenario": scenario,
                    "tail_extra_seconds_per_object": delta,
                    "prefix_extra_seconds": prefix_extra,
                    "observations": observations,
                    "capacity_estimate_objects": capacity,
                    "target_objects": target,
                    "capacity_margin_objects": capacity - target,
                    "measured_success": False,
                }
            )
        results[label] = rows
    absolute = []
    for label in [f"prefix-{i}-on" for i in range(3)]:
        original = json.loads((OUT / (label + ".json")).read_text())
        rate = tails[label]["seconds_per_object"]
        prefix = original["wall_us"] / 1e6
        cap1 = prefix_objects + max(0, int((900 - prefix) / rate))
        cap2 = max(
            0, int((900 - renewal_on["expiry_start_to_resumed_request_start_s"]) / rate)
        )
        absolute.append(
            {
                "label": label,
                "prefix_seconds": prefix,
                "index_seconds_per_object": rate,
                "lease_capacities_estimate": [cap1, cap2, cap2],
                "total_capacity_estimate_objects": cap1 + cap2 * 2,
                "scope": "current empty/small-store actual ON rate only; late large-store cost not measured; per-lease renewal reserved, no fungible2700s assumption",
            }
        )
    data = {
        "classification": "EXPERIMENTAL ESTIMATE, not full-run evidence",
        "paired_tail_extra_seconds_per_object": deltas,
        "paired_prefix_extra_seconds": prefix_extras,
        "measured_renewal_extra_seconds": renewal_extra,
        "historical_sensitivity": results,
        "current_absolute_sensitivity": absolute,
        "uncertainty": [
            "n=3 paired repetitions; no population p95",
            "raw-first prefix overweights initial large objects; latter index stratum covers small immutable work",
            "small client DB versus >600MiB historical full store; SQLite depth/cache/I/O can change",
            "historical independent server includes extra per-packet oracle work, implementation server differs; no averaging",
            "historical stored timestamp byte identity restored; fresh valid namespace/epoch changes object identity",
            "old per-observation transfer progress is not a native durable COMMIT timestamp",
            "terminal graph closure, hot/control tail, E3/E4 large counters only established by actual full run",
            "renewal clock skips901s waiting only; actual authorization/HTTP/staging/rebind measured",
            "three separate900s leases with expiry and new authorization; no unlimited shared2700s budget",
        ],
        "decision": "PENDING FINITE ENGINEERING ASSESSMENT",
    }
    (OUT / "lease-model.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "historical_capacity": {
                    k: {r["scenario"]: r["capacity_estimate_objects"] for r in v}
                    for k, v in results.items()
                },
                "absolute_capacity": [
                    r["total_capacity_estimate_objects"] for r in absolute
                ],
                "tail_extra": deltas,
            }
        )
    )


if __name__ == "__main__":
    main()

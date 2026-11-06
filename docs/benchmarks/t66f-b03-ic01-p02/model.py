"""P02 직접 관측과 서로 다른 역사 실행을 구분한 lease 사전 모델."""

import json
import math
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
P01 = HERE.parent / "t66f-b03-ic01-p01/evidence"


def stats(xs):
    ordered = sorted(xs)
    return {
        "n": len(xs),
        "median": statistics.median(xs),
        "min": min(xs),
        "max": max(xs),
        "p95_nearest_rank": ordered[math.ceil(0.95 * len(xs)) - 1],
    }


def main():
    path = OUT / "components-final-data.json"
    if not path.exists():
        path = OUT / "components-no-profiling.json"
    c = json.loads(path.read_text())
    b = json.loads((P01 / "historical-baselines.json").read_text())
    packet = json.loads((P01 / "packet-results.json").read_text())
    data = {
        "schema_version": 1,
        "measurement": {},
        "models": {},
        "source": path.name,
        "model_kind": "ANALYTICAL ESTIMATE; not observed lease completion/expiry",
        "full_100k_runs": 0,
    }
    for mode in ["off", "original", "reuse"]:
        for reused in [False, True]:
            rows = [
                r for r in c["records"] if r["mode"] == mode and r["reuse"] == reused
            ]
            data["measurement"][f"{mode}/{reused}"] = {
                k: stats([r[k] for r in rows])
                for k in [
                    "wall_us",
                    "cpu_ticks",
                    "transactions",
                    "snapshot_us",
                    "rss_bytes",
                ]
            }
    rows = {(r["repeat"], r["mode"], r["reuse"]): r for r in c["records"]}
    extra = [
        (rows[i, "reuse", False]["wall_us"] - rows[i, "off", False]["wall_us"])
        / 1e6
        / c["objects"]
        for i in range(1, 6)
    ]
    http_extra, validate_extra = [], []
    # 5 alternating repeats x (3 on + 3 off). Same packet index in each group.
    for i in range(5):
        group = packet["samples"][i * 6 : (i + 1) * 6]
        on = [r for r in group if r["enabled"]]
        off = [r for r in group if not r["enabled"]]
        assert len(on) == len(off) == 3
        for a, z in zip(on, off):
            assert (a["decoded_bytes"], a["request_bytes"], a["packet_objects"]) == (
                z["decoded_bytes"],
                z["request_bytes"],
                z["packet_objects"],
            )
            http_extra.append((a["http_us"] - z["http_us"]) / 1e6 / 64)
            validate_extra.append((a["validation_us"] - z["validation_us"]) / 1e6 / 64)
    data["e1_extra_seconds_per_new_object"] = stats(extra)
    data["historical_p01_http_extra_seconds_per_object"] = stats(http_extra)
    data["historical_p01_e2_packet_validation_extra_seconds_per_object"] = stats(
        validate_extra
    )
    for name in ["independent", "implementation"]:
        models = []
        for scenario, e, h, v in [
            ("e1_only_median", statistics.median(extra), 0, 0),
            (
                "paired_median",
                statistics.median(extra),
                statistics.median(http_extra),
                statistics.median(validate_extra),
            ),
            (
                "observed_max_sensitivity",
                max(extra),
                max(http_extra),
                max(validate_extra),
            ),
            (
                "observed_min_sensitivity",
                min(extra),
                min(http_extra),
                min(validate_extra),
            ),
        ]:
            leases = []
            for r in b[name]["observations"]:
                rate = r["productive_elapsed_s"] / r["new_objects"]
                leases.append(
                    {
                        "observation": r["number"],
                        "created": r["created"],
                        "expires": r["expires"],
                        "historical_new_objects": r["new_objects"],
                        "historical_productive_s": r["productive_elapsed_s"],
                        "historical_last_success_headroom_s": r[
                            "last_success_headroom_s"
                        ],
                        "extra_e1_s_per_new_object": e,
                        "extra_http_s_per_object": h,
                        "extra_e2_s_per_object": v,
                        "zero_reserve_capacity": int(900 / (rate + e + h + v)),
                    }
                )
            models.append(
                {
                    "scenario": scenario,
                    "observations": leases,
                    "sum_of_separate_capacities": sum(
                        x["zero_reserve_capacity"] for x in leases
                    ),
                    "target": 400532,
                }
            )
        data["models"][name] = {
            "historical_terminal_http_s": b[name]["terminal_http_s"],
            "scenarios": models,
        }
    data["decision"] = "INCONCLUSIVE — ADDITIONAL BOUNDED EVIDENCE REQUIRED"
    data["uncertainty"] = [
        "Independent and implementation baselines are separate runs, not interchangeable rates or a fungible 2700s deadline.",
        "Optimistic capacities use whole-observation average rates: front-loaded raw acquisition and shifted renewal positions are not simulated.",
        "Cold E1 samples use fresh small stores, not a growing >600MiB full store; extra lease-phase cached traversal and renewed staging work are not quantified.",
        "P01 deep 64-object HTTP packets are real, but not the entire request distribution; backend time is already inside HTTP and is not added again.",
        "Min/max are measured-sample sensitivity, not statistical confidence limits or invented acceptance thresholds.",
        "Positive headroom in one historical model does not prove completion; negative headroom in another does not prove an actual expiry.",
    ]
    data["next_discriminating_experiment"] = (
        "Bounded matched real E2→E1 cold prefix and cached traversal/renewal segment on the same 100k fixture; no full-run claim."
    )
    (OUT / "lease-model.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: [
                    (s["scenario"], s["sum_of_separate_capacities"])
                    for s in v["scenarios"]
                ]
                for k, v in data["models"].items()
            }
        )
    )


if __name__ == "__main__":
    main()

"""P03 원 trace와 실제 누적 checkpoint를 독립 재집계한다. 제품 실행은 없다."""

from collections import Counter
from datetime import datetime
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
OLD = HERE.parent / "t66f-b03-ic01-p03/evidence"


def read(name):
    return json.loads((OLD / name).read_text())


def difference(before, after):
    return {k: int(v) - int(before.get(k, 0)) for k, v in after.items()}


def main():
    rows = [
        json.loads(s) for s in gzip.open(OLD / "actual-server-requests.jsonl.gz", "rt")
    ]
    full = [r for r in rows if r["label"] == "full"]
    clocks = [
        json.loads(s)
        for s in (OLD / "host-clock-samples.jsonl").read_text().splitlines()
    ]
    offsets = [
        c["utc_ns"] - (c["monotonic_before_ns"] + c["monotonic_after_ns"]) // 2
        for c in clocks
    ]
    offset = sorted(offsets)[len(offsets) // 2]
    starts = [r for r in full if "manifest" in r]
    boundaries = read("full-observation-client-boundaries.json")
    result = read("full-result.json")
    observations = []
    for i, creation in enumerate(starts):
        manifest = creation["manifest"]
        prefix = "/api/sync/v1/observations/" + manifest["observation_id"]
        rr = [creation] + [
            r for r in full if r["path"] == prefix or r["path"].startswith(prefix + "/")
        ]
        successful = [
            r for r in rr if r["path"].endswith("/objects") and r["status"] == 200
        ]
        after = boundaries[i + 1] if i + 1 < len(boundaries) else result
        before = boundaries[i]
        v = {
            "number": i + 1,
            "id": manifest["observation_id"],
            "created": manifest["validated_at"],
            "expires": manifest["expires_at"],
            "raw_creation_request_start_ns": creation["start_ns"],
            "raw_last_success_request": successful[-1],
            "raw_last_attempt": sorted(rr, key=lambda r: r["start_ns"])[-1],
            "raw_last_object_attempt": [
                r for r in rr if r["path"].endswith("/objects")
            ][-1],
            "requests": len(rr),
            "successful_object_packets": len(successful),
            "statuses": dict(Counter(str(r["status"]) for r in rr)),
            "new_transfer_object_events": sum(
                r["wire"].get("chunks", 0) for r in successful
            ),
            "decoded_object_bytes": sum(
                r["wire"].get("decoded_object_bytes", 0) for r in successful
            ),
            "request_entity_bytes": sum(
                r["wire"].get("request_entity_bytes", 0) for r in rr
            ),
            "response_entity_bytes": sum(
                r["wire"].get("response_entity_bytes", 0) for r in rr
            ),
            "backend_handler_wall_s": sum(r["wall_ns"] for r in rr) / 1e9,
            "backend_process_cpu_s": sum(r["cpu_ns"] for r in rr) / 1e9,
            "first_to_last_success_interval_s": (
                successful[-1]["end_ns"] - successful[0]["start_ns"]
            )
            / 1e9,
            "sql_api_wall_boundary_delta_s": (after["sql_us"] - before["sql_us"]) / 1e6,
            "sql_callback_lower_bound_boundary_delta_s": (
                after.get("sql_observer_callback_us", after.get("observer_callback_us"))
                - before["sql_observer_callback_us"]
            )
            / 1e6,
            "primitive_boundary_delta": difference(
                before["primitive"], after["primitive"]
            ),
            "sql_boundary_delta": difference(before["sql"], after["sql"]),
            "work_boundary_delta": difference(before["work"], after["work"]),
            "timing_not_isolated": [
                "complete client HTTP wait",
                "hash-only wall",
                "validation-only wall",
                "graph-traversal-only wall",
                "auxiliary timing observer exclusive overhead",
            ],
            "clock_domain": "same-host time.perf_counter_ns; UTC mapping from preserved anchors",
        }
        observations.append(v)
    assert [o["new_transfer_object_events"] for o in observations] == [
        129376,
        137984,
        129786,
    ]
    assert (
        sum(o["new_transfer_object_events"] for o in observations)
        == result["durable_objects"]["n"]
        == 397146
    )
    expiry = (
        int(
            datetime.fromisoformat(
                starts[-1]["manifest"]["expires_at"].replace("Z", "+00:00")
            ).timestamp()
            * 1e9
        )
        - offset
    )
    windows = []
    successful = [
        r for r in full if r["path"].endswith("/objects") and r["status"] == 200
    ]
    for seconds in [10, 30, 60, 120, 300]:
        interval = [
            r for r in successful if expiry - seconds * 1e9 <= r["end_ns"] < expiry
        ]
        count = sum(r["wire"].get("chunks", 0) for r in interval)
        windows.append(
            {
                "seconds": seconds,
                "packets": len(interval),
                "object_events": count,
                "objects_per_second": count / seconds,
                "missing_3386_acquisition_seconds_estimate": 3386 / (count / seconds),
            }
        )
    fixture = read("fixture.json")["graph"]
    actual = {r["kind"]: r for r in result["durable_kinds"]}
    remaining = {
        k: {
            "objects": n - actual.get(k, {}).get("n", 0),
            "canonical_bytes": fixture["kind_bytes"][k]
            - actual.get(k, {}).get("bytes", 0),
        }
        for k, n in fixture["kinds"].items()
    }
    value = {
        "observations": observations,
        "last_windows": windows,
        "remaining_types": remaining,
        "missing_object_count": sum(v["objects"] for v in remaining.values()),
        "missing_canonical_bytes": sum(
            v["canonical_bytes"] for v in remaining.values()
        ),
        "clock_offset_ns_range": [min(offsets), max(offsets)],
        "p03_full_status": "FAIL",
        "P04_new_full_100k_cold_attempts": 0,
        "measurements_are_not_additive": True,
        "sql_boundary_note": "before fresh observation request to next such boundary includes release/renewal handling; last boundary is terminal failure, not E3/E4",
        "remaining_work_note": "3386 acquisition-time estimate excludes closure, restart rewalk, metadata proof, E3 and E4; not an extra shared observation budget",
    }
    assert value["missing_object_count"] == 3386
    assert value["missing_canonical_bytes"] == 1799308
    (OUT / "p03-reconstruction.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "objects_by_observation": [129376, 137984, 129786],
                "remaining": remaining,
                "tail_windows": windows,
            }
        )
    )


if __name__ == "__main__":
    main()

"""종료된 단 한 번의 실제 full 실행을 원 trace/checkpoint로 대조한다."""

from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"


def read(name):
    return json.loads((OUT / name).read_text())


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def delta(before, after):
    # Cumulative counters only. Missing keys denote not-yet-created counters at
    # the earlier boundary; raw boundary snapshots remain the primary evidence.
    return {
        k: int(v) - int(before.get(k, 0))
        for k, v in after.items()
        if int(v) != int(before.get(k, 0))
    }


def primitive_summary(values, backend=False):
    stages = sorted({k.split("/")[0] for k in values})
    result = {}
    suffixes = (
        {
            "hash_input_bytes": "/hash_input_bytes",
            "validation_submitted_span_bytes": "/submitted_bytes",
            "validation_completed_span_bytes": "/completed_bytes",
            "validation_failed_span_bytes": "/failed_bytes",
        }
        if backend
        else {
            "hash_input_bytes": "/hashInputBytes",
            "validation_submitted_span_bytes": "/submittedBytes",
            "validation_completed_span_bytes": "/completedBytes",
            "validation_failed_span_bytes": "/failedBytes",
        }
    )
    for stage in stages:
        result[stage] = {}
        for metric, suffix in suffixes.items():
            keys = [
                k for k in values if k.startswith(stage + "/") and k.endswith(suffix)
            ]
            result[stage][metric] = (
                {"value": sum(int(values[k]) for k in keys), "keys": keys}
                if keys
                else {"value": None, "status": "NO_COUNTER_KEY_IN_THIS_SNAPSHOT"}
            )
    return result


def sql_summary(values, backend=False):
    result = {}
    for stage in sorted({k.split("/")[0] for k in values}):
        result[stage] = {}
        for phase in ("attempted", "effective", "committed"):
            if backend:
                suffixes = (f"/{phase}/text_bytes", f"/{phase}/blob_bytes")
            elif phase == "committed":
                suffixes = ("/textBytes/committed", "/blobBytes/committed")
            else:
                suffixes = (f"/{phase}/textBytes", f"/{phase}/blobBytes")
            keys = [
                k for k in values if k.startswith(stage + "/") and k.endswith(suffixes)
            ]
            result[stage][phase] = (
                {
                    "text_plus_blob_bytes": sum(int(values[k]) for k in keys),
                    "keys": keys,
                }
                if keys
                else {"text_plus_blob_bytes": None, "status": "NO_COUNTER_KEY"}
            )
    return result


def main():
    result = read("full-result.json")
    backend = read("full-backend-snapshot.json")
    assert read("full-attempt.json")["attempt"] == 1
    root = Path(read("disposable-location.json")["root"])
    rows = [
        json.loads(line)
        for line in (root / "server/requests.jsonl").read_text().splitlines()
    ]
    full = [r for r in rows if r["label"] == "full"]
    clocks = [
        json.loads(s)
        for s in (OUT / "host-clock-samples.jsonl").read_text().splitlines()
    ]
    anchor = min(
        clocks, key=lambda c: c["monotonic_after_ns"] - c["monotonic_before_ns"]
    )
    offset = (
        anchor["utc_ns"]
        - (anchor["monotonic_before_ns"] + anchor["monotonic_after_ns"]) // 2
    )

    def utc(ns):
        return datetime.fromtimestamp((ns + offset) / 1e9, timezone.utc).isoformat()

    def epoch_ns(value):
        return int(
            datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1e9
        )

    manifests = [r for r in full if "manifest" in r]
    boundaries = read("full-observation-client-boundaries.json")
    observations = []
    for i, creation in enumerate(manifests):
        m = creation["manifest"]
        oid = m["observation_id"]
        prefix = f"/api/sync/v1/observations/{oid}"
        rr = [
            r for r in full if r["path"] == prefix or r["path"].startswith(prefix + "/")
        ]
        # Creation has no UUID path; associate this actual row explicitly.
        rr = sorted([creation] + rr, key=lambda r: r["start_ns"])
        objects = [
            r for r in rr if r["path"].endswith("/objects") and r["status"] == 200
        ]
        before = boundaries[i]
        after = boundaries[i + 1] if i + 1 < len(boundaries) else result
        errors = [r for r in rr if r["status"] >= 400]
        observations.append(
            {
                "number": i + 1,
                "id": oid,
                "created": m["validated_at"],
                "expires": m["expires_at"],
                "ttl_seconds": (epoch_ns(m["expires_at"]) - epoch_ns(m["validated_at"]))
                / 1e9,
                "requests_completed": len(rr),
                "statuses": dict(Counter(str(r["status"]) for r in rr)),
                "transferred_object_events": sum(
                    r["wire"].get("chunks", 0) for r in objects
                ),
                "request_entity_bytes": sum(
                    r["wire"].get("request_entity_bytes", 0) for r in rr
                ),
                "response_entity_bytes": sum(
                    r["wire"].get("response_entity_bytes", 0) for r in rr
                ),
                "backend_wall_sum_s": sum(r["wall_ns"] for r in rr) / 1e9,
                "backend_cpu_sum_s": sum(r["cpu_ns"] for r in rr) / 1e9,
                "first_object_request_utc": utc(objects[0]["start_ns"])
                if objects
                else None,
                "last_object_response_boundary_utc": utc(objects[-1]["end_ns"])
                if objects
                else None,
                "object_productive_interval_s": (
                    objects[-1]["end_ns"] - objects[0]["start_ns"]
                )
                / 1e9
                if objects
                else None,
                "last_success_headroom_s": (
                    epoch_ns(m["expires_at"]) - objects[-1]["end_ns"] - offset
                )
                / 1e9
                if objects
                else None,
                "native_pending_at_completed_boundary_max": max(
                    r["pending"] for r in rr
                ),
                "client_before_observation": before,
                "client_next_boundary": after,
                "client_cumulative_durable_objects": int(
                    after["sql"].get("e2/objects/INSERT/effective/rows", 0)
                ),
                "primitive_delta": delta(before["primitive"], after["primitive"]),
                "sql_delta": delta(before["sql"], after["sql"]),
                "error_boundaries": errors,
            }
        )
    aggregate = Counter()
    groups = {k: v for k, v in backend["groups"].items() if k.startswith("full/")}
    for values in groups.values():
        aggregate.update({k: int(v) for k, v in values.items()})
    transfer_events = sum(o["transferred_object_events"] for o in observations)
    summary = {
        "classification": "MEASURED_FULL_RUN",
        "status": result["status"],
        "full_attempts": 1,
        "elapsed_s": result["elapsed_us"] / 1e6,
        "publication_s": result.get("publication_us", 0) / 1e6
        if "publication_us" in result
        else None,
        "e4_read_including_independent_value_oracle_s": result.get("e4_read_us", 0)
        / 1e6
        if "e4_read_us" in result
        else None,
        "error": result.get("error"),
        "durable_objects": result["durable_objects"],
        "remaining_objects": 400532 - result["durable_objects"]["n"],
        "transferred_object_events": transfer_events,
        "retransmission_events_vs_native_unique_rows": transfer_events
        - result["durable_objects"]["n"],
        "observations": observations,
        "clock_anchor": anchor,
        "clock_note": "UTC conversion uses measured same-host monotonic midpoint; not wall-clock equality proof",
        "backend_full_only_counters": dict(sorted(aggregate.items())),
        "backend_full_only_groups": groups,
        "backend_primitive_stage_summary": primitive_summary(aggregate, True),
        "backend_sql_stage_summary": sql_summary(aggregate, True),
        "client_primitive_stage_summary": primitive_summary(result["primitive"]),
        "client_sql_stage_summary": sql_summary(result["sql"]),
        "generation_primitive_summary": primitive_summary(backend["generation"], True),
        "generation_sql_summary": sql_summary(backend["generation"], True),
        "client_sql_api_inclusive_s": result["sql_us"] / 1e6,
        "client_observer_callback_truncated_lower_bound_s": result[
            "observer_callback_us"
        ]
        / 1e6,
        "backend_all_cohorts_complete": backend["complete"],
        "backend_all_cohorts_started": backend["started"],
        "backend_all_cohorts_completed": backend["completed"],
        "backend_pending": backend["pending"],
        "backend_full_requests": len(full),
        "backend_full_wall_sum_s": sum(r["wall_ns"] for r in full) / 1e9,
        "backend_full_cpu_sum_s": sum(r["cpu_ns"] for r in full) / 1e9,
        "client_peak_sampled_rss": result["peak_sampled_rss"],
        "client_lifetime_max_rss": result["lifetime_max_rss"],
        "server_lifetime_peak_rss_bytes": backend["rss_peak_kib"] * 1024,
        "owned_process_sampled_peak_sum_rss_bytes": max(
            c.get("server_rss_bytes", 0) + c.get("flutter_rss_bytes", 0) for c in clocks
        ),
        "collector_closed": result["collector_closed"],
        "cache_closed": result["cache_closed"],
        "accepted_before": result["accepted_before"],
        "accepted_after": result["accepted_after"],
        "protected_unchanged": result["protected_unchanged"],
        "scope_note": "Full-only backend groups exclude prefix work. E4 wall includes independent digest oracle; HTTP client meter is header-only. Absent counter keys are not filled with measured zero.",
    }
    assert len(manifests) <= 3
    assert all(o["ttl_seconds"] == 900 for o in observations)
    assert backend["complete"] and backend["pending"] == 0
    assert result["collector_closed"] and result["protected_unchanged"]
    cache = result["cache_closed"]
    assert cache["peakLive"] <= 32 and cache["created"] == cache["finalized"]
    assert cache["capacityRejections"] == 0
    assert (
        int(result["sql"]["e2/objects/INSERT/effective/rows"])
        == result["durable_objects"]["n"]
    )
    assert (
        int(result["sql"]["e2/objects/INSERT/blobBytes/committed"])
        == result["durable_objects"]["bytes"]
    )
    if result["status"] == "PASS":
        assert result["durable_objects"] == {"n": 400532, "bytes": 261543083}
        assert result["accepted_after"] is not None and result["sequence"] == 1
    else:
        assert result["accepted_after"] is None
    for name in (
        "requests.jsonl",
        "backend-fixture.json",
        "generation-counters.json",
        "http-failures.json",
        "wire-progress.json",
    ):
        content = (root / "server" / name).read_bytes()
        target = OUT / ("actual-server-" + name + ".gz")
        with target.open("wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
                stream.write(content)
        summary.setdefault("preserved_raw_artifacts", {})[target.name] = {
            "sha256_uncompressed": hashlib.sha256(content).hexdigest(),
            "bytes_uncompressed": len(content),
        }
    save("full-analysis.json", summary)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "objects": summary["durable_objects"],
                "observations": len(observations),
                "attempts": 1,
            }
        )
    )


if __name__ == "__main__":
    main()

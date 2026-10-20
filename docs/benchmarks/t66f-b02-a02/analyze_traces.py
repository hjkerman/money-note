"""보존된 corrected cold HTTP trace를 독립적으로 재집계한다. 원본 쓰기 없음."""

from collections import Counter
from pathlib import Path
import gzip
import json
import statistics
import math

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "t66f-b02-a01-correction"


def load(name):
    return json.loads(gzip.decompress((SOURCE / name).read_bytes()))


def stat(v):
    v = sorted(v)
    return (
        {
            "n": len(v),
            "min": min(v),
            "median": statistics.median(v),
            "p95_nearest_rank": v[math.ceil(0.95 * len(v)) - 1],
            "max": max(v),
            "sum": sum(v),
        }
        if v
        else None
    )


def analyze(tag):
    rows = [
        json.loads(x)
        for x in gzip.decompress(
            (SOURCE / f"http-{tag}-server-requests.jsonl.gz").read_bytes()
        ).splitlines()
    ]
    result = load(f"http-{tag}-result.json.gz")
    stages = result.get(
        "cold_fault_boundary_counts", result.get("fault_boundary_counts", {})
    )["after_staging_insert"]
    births = {}
    for r in rows:
        if r.get("manifest"):
            births.setdefault(r["manifest"]["observation_id"], r)
    attempts = []
    cold = []
    for identity, b in list(births.items())[:stages]:
        objects = [r for r in rows if r["path"].endswith("/" + identity + "/objects")]
        ok = [r for r in objects if r["status"] == 200]
        cold += objects
        ns = Counter()
        cpu = Counter()
        calls = Counter()
        for r in objects:
            ns.update(r["ns"])
            cpu.update(r["cpu_ns"])
            calls.update(r["calls"])
        # Nested timers: disjoint top-level connection/lookup/resolver scopes only.
        buckets = {
            k: ns[k] / 1e9
            for k in (
                "RetentionSandbox.connect",
                "ObservationRepository._lookup",
                "PathResolver.resolve",
            )
        }
        wall = sum((r["handler_end_ns"] - r["start_ns"]) / 1e9 for r in objects)
        buckets["handler_other"] = wall - sum(buckets.values())
        renewgap = (objects[0]["start_ns"] - b["end_ns"]) / 1e9
        a = {
            "id": identity,
            "validated": b["manifest"]["validated_at"],
            "expires": b["manifest"]["expires_at"],
            "root": b["manifest"]["target"]["sync_root"],
            "post_manifest_gap_s": renewgap,
            "new_objects": sum(r.get("new_global_hashes", 0) for r in ok),
            "duplicate_http": sum(
                r.get("duplicate_same_observation_hashes", 0)
                + r.get("reused_previous_observation_hashes", 0)
                for r in ok
            ),
            "requests": len(objects),
            "status": dict(Counter(r["status"] for r in objects)),
            "packet_items": stat([r["chunks"] for r in ok]),
            "packet_histogram": dict(Counter(r["chunks"] for r in ok)),
            "request_wall_s": stat(
                [(r["handler_end_ns"] - r["start_ns"]) / 1e9 for r in ok]
            ),
            "request_fixed_inclusive_s": {
                k: ns[k] / 1e9
                for k in (
                    "isolated_sync.observation.versions",
                    "schema.current",
                    "ObservationRepository._view_object",
                    "permit.acquire",
                    "executor.start_wait",
                    "SQL.BEGIN_IMMEDIATE",
                    "SQL.SELECT",
                )
            },
            "request_exclusive_buckets_s": buckets,
            "timers_wall_s": {k: v / 1e9 for k, v in ns.items()},
            "timers_cpu_s": {k: v / 1e9 for k, v in cpu.items()},
            "calls": calls,
            "resolver_metrics": {
                k: sum(r.get("implementation_metrics", {}).get(k, 0) for r in ok)
                for k in (
                    "prefix_validations",
                    "prefix_cache_hits",
                    "object_reads",
                    "object_bytes_read",
                    "resolution_ms",
                    "admission_ms",
                    "terminal_http_ms",
                )
            },
            "prefix_peak": max(
                r.get("implementation_metrics", {}).get("prefix_cache_peak", 0)
                for r in ok
            ),
            "prefix_byte_peak": max(
                r.get("implementation_metrics", {}).get("prefix_cache_peak_bytes", 0)
                for r in ok
            ),
            "entity_response_bytes": sum(r["response_bytes"] for r in objects),
            "entity_request_bytes": sum(r["request_bytes"] for r in objects),
            "canonical_bytes": sum(r.get("decoded_bytes", 0) for r in ok),
            "instrumentation_postprocess_s": sum(
                r.get("instrumentation_postprocess_ns", 0) for r in objects
            )
            / 1e9,
            "last_response_ns": objects[-1]["end_ns"],
            "all_permits_closed": all(
                not any(r.get("permit_after_close", {}).values()) for r in objects
            ),
            "full_packets": sum(r["chunks"] == 64 for r in ok),
            "max_active": max(r["max_active"] for r in objects),
            "tcp_connection_count_max": max(r["tcp_connections"] for r in objects),
        }
        attempts.append(a)
    # Conservative critical path bound: ASGI handler intervals disjoint (actual max1).
    return {
        "tag": tag,
        "source_result_status": result["status"],
        "fixture": result["fixture"],
        "cold_elapsed_us": result.get("cold_elapsed_us", result["elapsed_us"]),
        "publication_completed_us": result.get("publication_completed_us"),
        "store_work": result.get("cold_store_work", result.get("store_work")),
        "attempts": attempts,
        "all_handler_s": sum((r["handler_end_ns"] - r["start_ns"]) / 1e9 for r in cold),
        "max_client_rss_bytes": result["client_process_rss_peak_bytes"],
        "measurement_limit": "기존 inclusive native timers와 같은 server monotonic clock. client CPU/hash/SQL별 exclusive 시간은 원 trace에 없다.",
    }


def main():
    data = {
        n: analyze(tag)
        for n, tag in [("50000", "50000-cursor-lifetime"), ("100000", "100000")]
    }
    (HERE / "trace-analysis.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    )
    for n, r in data.items():
        print(
            n,
            "elapsed",
            r["cold_elapsed_us"] / 1e6,
            "server handler",
            r["all_handler_s"],
            "store",
            r["store_work"],
        )
        for a in r["attempts"]:
            print(
                a["id"],
                a["new_objects"],
                a["post_manifest_gap_s"],
                a["request_exclusive_buckets_s"],
                a["request_fixed_inclusive_s"],
                a["request_wall_s"],
            )


if __name__ == "__main__":
    main()

"""기존 raw trace에서 cold observation별 독립 작업 계수를 집계한다."""

from collections import Counter
import json
from pathlib import Path
import sys


def summarize(out):
    result_path = out / "result.json"
    if not result_path.exists():
        raise ValueError("완료/실패 result.json이 있어야 한다")
    result = json.loads(result_path.read_text())
    rows = [json.loads(line) for line in (out / "server/requests.jsonl").open()]
    stages = (
        result.get("cold_fault_boundary_counts", {}).get("after_staging_insert", 0)
        or result["fault_boundary_counts"]["after_staging_insert"]
    )
    manifests, births = {}, {}
    for row in rows:
        if row.get("method") == "POST" and row.get("manifest"):
            manifest = row["manifest"]
            manifests.setdefault(manifest["observation_id"], manifest)
            births.setdefault(manifest["observation_id"], row)
    # The cold operation is first, with one new observation/stage per attempt.
    # Later identical/delta observations must NOT inflate cold attempt counts.
    cold = list(manifests.items())[:stages]
    attempts, aggregate = [], Counter()
    for identity, manifest in cold:
        objects = [
            row
            for row in rows
            if row.get("method") == "POST"
            and row.get("path", "").endswith(f"/{identity}/objects")
        ]
        success = [row for row in objects if row.get("status") == 200]
        hist = Counter(row["chunks"] for row in success)
        work, sql = Counter(), Counter()
        for row in success:
            work.update(
                {
                    key: val
                    for key, val in row.get("implementation_metrics", {}).items()
                    if isinstance(val, (int, float))
                }
            )
        for row in objects:
            sql.update(
                {k: v for k, v in row.get("calls", {}).items() if k.startswith("SQL.")}
            )
        measure = dict(
            observation_id=identity,
            validated_at=manifest["validated_at"],
            expires_at=manifest["expires_at"],
            sync_root=manifest["target"]["sync_root"],
            object_requests=len(objects),
            status_counts=Counter(str(row["status"]) for row in objects),
            first_request_utc=min((row["start_utc"] for row in objects), default=None),
            last_request_utc=max((row["start_utc"] for row in objects), default=None),
            post_manifest_request_gap_seconds=(
                (min(row["start_ns"] for row in objects) - births[identity]["end_ns"])
                / 1e9
                if objects
                else None
            ),
            objects_returned=sum(row["chunks"] for row in success),
            new_global_hashes=sum(row["new_global_hashes"] for row in success),
            cross_observation_retransfers=sum(
                row["reused_previous_observation_hashes"] for row in success
            ),
            request_entity_bytes=sum(row["request_bytes"] for row in objects),
            response_entity_bytes=sum(row["response_bytes"] for row in objects),
            decoded_object_bytes=sum(row["decoded_bytes"] for row in success),
            packet_histogram=hist,
            mean_success_packet_items=(
                sum(row["chunks"] for row in success) / len(success)
                if success
                else None
            ),
            sql_operations=sql,
            resolver_work={
                key: work[key]
                for key in (
                    "object_reads",
                    "object_bytes_read",
                    "prefix_cache_hits",
                    "prefix_validations",
                )
            },
            max_prefix_entries=max(
                (
                    row["implementation_metrics"].get("prefix_cache_peak", 0)
                    for row in success
                ),
                default=0,
            ),
            max_prefix_canonical_charge=max(
                (
                    row["implementation_metrics"].get("prefix_cache_peak_bytes", 0)
                    for row in success
                ),
                default=0,
            ),
            all_recorded_permits_closed=all(
                not any(row.get("permit_after_close", {}).values()) for row in objects
            ),
        )
        for key in (
            "object_requests",
            "objects_returned",
            "new_global_hashes",
            "cross_observation_retransfers",
            "request_entity_bytes",
            "response_entity_bytes",
            "decoded_object_bytes",
        ):
            aggregate[key] += measure[key]
        attempts.append(measure)
    value = dict(
        scope="DIRECT OBSERVATION; cold HTTP trace only, not all-layer logical byte accounting",
        n=result["n"],
        status=result["status"],
        observations_used=len(attempts),
        aggregate=aggregate,
        attempts=attempts,
        fixture=result["fixture"],
        same_cold_target=len({entry["sync_root"] for entry in attempts}) == 1,
        client_peak_rss=result["client_process_rss_peak_bytes"],
        cold_store_work=result.get(
            "cold_store_work",
            result.get("store_work") if result["status"] == "FAIL_COLD" else None,
        ),
        cold_elapsed_us=result.get("cold_elapsed_us"),
        cold_publication_transaction_us=result.get("cold_publication_transaction_us"),
        phases=result.get("phases"),
        recovery_exit=result.get("fresh_process_exit"),
        legacy_pending_bytes_preserved=(
            result["protected_legacy_before"] == result["protected_legacy_after"]
        ),
        r1=result["r1_activation"],
    )
    (out / "cold-summary.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({"n": value["n"], "status": value["status"], "cold": aggregate}))


if __name__ == "__main__":
    summarize(Path(sys.argv[1]))

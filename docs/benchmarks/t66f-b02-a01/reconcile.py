"""최종 raw evidence를 측정 경계별로 정리한다. 측정하지 않은 값은 만들지 않는다."""

from collections import Counter
import json
from pathlib import Path
import statistics
import sys

HERE = Path(__file__).resolve().parent
OUT = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(json.loads((HERE / "active-run.json").read_text())["out"])
)
a = json.loads((OUT / "analysis.json").read_text())
server = []
client = []
for file, dest in [
    ("server/requests.jsonl", server),
    ("client-timeline.jsonl", client),
]:
    for line in (OUT / file).read_text().splitlines():
        try:
            dest.append(json.loads(line))
        except ValueError:
            pass
server.sort(key=lambda r: r["serial"])
client.sort(key=lambda r: r.get("start_us", r.get("end_us", r.get("at_us", 0))))
manifest_client = [
    r
    for r in client
    if r.get("type") == "http"
    and r["method"] == "POST"
    and r["path"].endswith("/observations")
    and r["status"] == 201
]
commits = [r for r in client if r.get("type") == "commit"]
obs = []
for i, record in enumerate([r for r in server if "manifest" in r]):
    m = record["manifest"]
    oid = m["observation_id"]
    c = manifest_client[i] if i < len(manifest_client) else None
    nxt = (
        manifest_client[i + 1]["start_us"]
        if i + 1 < len(manifest_client)
        else float("inf")
    )
    owned = [r for r in commits if c and c["headers_us"] <= r["end_us"] < nxt]
    requests = [r for r in server if r["path"].endswith("/" + oid + "/objects")]
    http = [
        r
        for r in client
        if r.get("type") == "http" and r["path"].endswith("/" + oid + "/objects")
    ]
    ok = [r for r in requests if r.get("status") == 200]
    first_full_cached = next(
        (r for r in owned if r.get("batch_new") == 0 and r.get("batch_progress") == 64),
        None,
    )
    obs.append(
        dict(
            attempt=i + 1,
            id=oid,
            validated_at=m["validated_at"],
            expires_at=m["expires_at"],
            root=m["target"]["sync_root"],
            namespace=m["target"]["ns"],
            principal=m["target"]["principal_id"],
            new_durable_objects=sum(r.get("batch_new", 0) for r in owned),
            progress_links_attempted=sum(r.get("batch_progress", 0) for r in owned),
            commits=len(owned),
            new_object_commits=sum(r.get("batch_new", 0) > 0 for r in owned),
            cache_only_commits=sum(
                r.get("batch_new", 0) == 0 and r.get("batch_progress", 0) > 0
                for r in owned
            ),
            decoded_bytes=sum(r.get("decoded_bytes", 0) for r in ok),
            response_entity_bytes=sum(r["response_bytes"] for r in requests),
            request_entity_bytes=sum(r["request_bytes"] for r in requests),
            object_requests=len(requests),
            success_responses=len(ok),
            http_statuses=dict(Counter(r["status"] for r in requests)),
            client_headers_to_terminal_error_seconds=(
                http[-1]["headers_us"] - c["headers_us"]
            )
            / 1e6
            if http and c
            else None,
            first_object_scheduling_after_manifest_seconds=(
                http[0]["start_us"] - c["headers_us"]
            )
            / 1e6
            if http and c
            else None,
            first_64_cached_progress_commit_after_manifest_seconds=(
                first_full_cached["end_us"] - c["headers_us"]
            )
            / 1e6
            if first_full_cached and c
            else None,
            insert_to_commit_seconds=sum(
                r["end_us"] - r["first_insert_us"]
                for r in owned
                if r.get("first_insert_us") is not None
            )
            / 1e6,
            cache_progress_lower_bound_seconds=sum(
                r["end_us"] - r["first_progress_us"]
                for r in owned
                if not r.get("batch_new") and r.get("first_progress_us") is not None
            )
            / 1e6,
            redownload_prior_observation=sum(
                r.get("reused_previous_observation_hashes", 0) for r in ok
            ),
            repeated_same_observation=sum(
                r.get("duplicate_same_observation_hashes", 0) for r in ok
            ),
        )
    )
obj = [r for r in server if r.get("status") == 200 and r["path"].endswith("/objects")]
wall = sum(r["handler_end_ns"] - r["start_ns"] for r in obj) / 1e9
keys = [
    "ObservationRepository._lookup",
    "RetentionSandbox.connect",
    "PathResolver.resolve",
]
disjoint = {k: sum(r["ns"].get(k, 0) for r in obj) / 1e9 for k in keys}
cpu = {k: sum(r["cpu_ns"].get(k, 0) for r in obj) / 1e9 for k in keys}
packets = {
    n: dict(
        count=len(v := [r for r in obj if r.get("chunks") == n]),
        handler_median_ms=statistics.median(
            (r["handler_end_ns"] - r["start_ns"]) / 1e6 for r in v
        ),
        decoded_bytes=sum(r["decoded_bytes"] for r in v),
    )
    for n in sorted({r["chunks"] for r in obj})
}
resources = []
for line in (OUT / "resources.jsonl").read_text().splitlines():
    try:
        resources.extend(json.loads(line)["processes"])
    except ValueError:
        pass
peak = {}
for label, match in [
    ("backend", "/t66f-b02-a01/server.py"),
    ("client", "flutter_tester"),
]:
    rows = [r for r in resources if match in r["command"]]
    peak[label] = dict(
        sampled_peak_rss_kib=max(
            (int(r["rss_kib"].split()[0]) for r in rows if r["rss_kib"]), default=0
        ),
        sampled_peak_fds=max((r["open_fds"] for r in rows), default=0),
        max_user_cpu=max((r["user_cpu_seconds"] for r in rows), default=0),
        max_system_cpu=max((r["system_cpu_seconds"] for r in rows), default=0),
    )
transport_errors = [row for row in client if row.get("type") == "http_error"]
retry_gaps_us = []
for error in transport_errors:
    next_request = next(
        (
            row
            for row in client
            if row.get("type") == "http"
            and row["path"] == error["path"]
            and row["start_us"] > error["end_us"]
        ),
        None,
    )
    if next_request is not None:
        retry_gaps_us.append(next_request["start_us"] - error["end_us"])
value = dict(
    preheader_transport_errors=transport_errors,
    observed_retry_gaps_us=retry_gaps_us,
    observations=obs,
    successful_object_handler_seconds=wall,
    disjoint_server_work_seconds=disjoint,
    disjoint_server_cpu_seconds=cpu,
    disjoint_server_work_share={k: v / wall for k, v in disjoint.items()},
    packet_distribution=packets,
    mean_objects_per_packet=sum(r["chunks"] for r in obj) / len(obj) if obj else None,
    successful_decoded_bytes=sum(r["decoded_bytes"] for r in obj),
    sampled_resources=peak,
    request_header_field_bytes_partial=sum(
        r.get("request_header_bytes", 0) for r in server
    ),
    response_header_field_bytes_partial=sum(
        r.get("response_header_bytes", 0) for r in server
    ),
    critical_path_disclaimer="No TLS/TCP/late-response-body isolation; nested work is not summed. Snapshot/trace overhead included.",
    all_targets_equal=len(
        {
            json.dumps(r["manifest"]["target"], sort_keys=True)
            for r in server
            if "manifest" in r
        }
    )
    == 1,
    no_accepted_publication=a["client_result"].get("accepted_after") is None,
    commit_new_count_matches_usage=sum(r.get("batch_new", 0) for r in commits)
    == a["client_result"].get("usage", {}).get("objects"),
)
(OUT / "reconciled.json").write_text(
    json.dumps(value, ensure_ascii=False, indent=2) + "\n"
)
print(
    json.dumps(
        dict(
            attempts=len(obs),
            objects=[o["new_durable_objects"] for o in obs],
            work_seconds=disjoint,
        ),
        ensure_ascii=False,
    )
)

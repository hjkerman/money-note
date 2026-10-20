"""서버·클라이언트의 별도 monotonic timebase를 합치지 않는 원시 증거 요약."""

from collections import Counter
from datetime import datetime
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


def load(name):
    p = OUT / name
    return json.loads(p.read_text()) if p.exists() else None


def lines(name):
    p = OUT / name
    rows = []
    if not p.exists():
        return rows
    for line in p.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass  # Incomplete last buffered line is not evidence.
    return rows


def summary(values, divisor=1):
    v = sorted(n / divisor for n in values)
    if not v:
        return dict(n=0)
    return dict(
        n=len(v),
        total=sum(v),
        min=v[0],
        median=statistics.median(v),
        p95=v[max(0, (__import__("math").ceil(0.95 * len(v)) - 1))],
        max=v[-1],
    )


server = lines("server/requests.jsonl")
client = lines("client-timeline.jsonl")
manifests = [r for r in server if "manifest" in r]
objects = [r for r in server if r.get("path", "").endswith("/objects")]
success = [r for r in objects if r.get("status") == 200]
result = dict(
    out=str(OUT),
    execution=load("execution.json"),
    fixture=load("server/backend-fixture.json"),
    client_result=load("result.json"),
    requests=len(server),
    object_requests=len(objects),
    success_objects=sum(r.get("chunks", 0) for r in success),
    statuses=dict(Counter(r.get("status") for r in server)),
    observations=[],
)
for i, record in enumerate(manifests):
    m = record["manifest"]
    oid = m["observation_id"]
    rr = [r for r in objects if r["path"].split("/")[-2] == oid]
    ok = [r for r in rr if r.get("status") == 200]

    def epoch(x):
        return datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp()

    lease_start, expires = epoch(m["validated_at"]), epoch(m["expires_at"])
    result["observations"].append(
        dict(
            attempt=i + 1,
            id=oid,
            target=m["target"],
            validated_at=m["validated_at"],
            expires_at=m["expires_at"],
            ttl=expires - lease_start,
            client_acquisition_server_end_utc=record.get("start_utc", 0)
            + (record["handler_end_ns"] - record["start_ns"]) / 1e9,
            object_attempts=len(rr),
            success_responses=len(ok),
            statuses=dict(Counter(r.get("status") for r in rr)),
            chunks=sum(r.get("chunks", 0) for r in ok),
            decoded_bytes=sum(r.get("decoded_bytes", 0) for r in ok),
            response_entity_bytes=sum(r.get("response_bytes", 0) for r in rr),
            request_entity_bytes=sum(r.get("request_bytes", 0) for r in rr),
            new_global_objects=sum(r.get("new_global_hashes", 0) for r in ok),
            repeated_prior_observation_objects=sum(
                r.get("reused_previous_observation_hashes", 0) for r in ok
            ),
            repeated_same_observation_objects=sum(
                r.get("duplicate_same_observation_hashes", 0) for r in ok
            ),
            first_request_utc=rr[0]["start_utc"] if rr else None,
            first_request_lease_remaining=expires - rr[0]["start_utc"] if rr else None,
            first_success_utc=ok[0]["start_utc"] if ok else None,
            last_success_utc=ok[-1]["start_utc"] if ok else None,
            elapsed_to_last_response_seconds=(rr[-1]["end_ns"] - record["end_ns"]) / 1e9
            if rr
            else None,
            failure_bodies=[r.get("failure_body") for r in rr if "failure_body" in r],
        )
    )
result["server_work_inclusive_ms"] = {
    key: summary([r.get("ns", {}).get(key, 0) for r in success], 1e6)
    for key in sorted({k for r in success for k in r.get("ns", {})})
}
result["server_cpu_inclusive_ms"] = {
    key: summary([r.get("cpu_ns", {}).get(key, 0) for r in success], 1e6)
    for key in sorted({k for r in success for k in r.get("cpu_ns", {})})
}
result["server_calls"] = dict(
    sum((Counter(r.get("calls", {})) for r in server), Counter())
)
result["object_handler_ms"] = summary(
    [r["handler_end_ns"] - r["start_ns"] for r in success], 1e6
)
result["handler_work_seconds"] = (
    sum(r["handler_end_ns"] - r["start_ns"] for r in server) / 1e9
)
result["server_idle_between_requests_seconds"] = (
    sum(max(0, b["start_ns"] - a["end_ns"]) for a, b in zip(server, server[1:])) / 1e9
)
result["tcp_connections"] = max(
    (r.get("tcp_connections", 0) for r in server), default=0
)
result["max_concurrent_handlers"] = max(
    (r.get("max_active", 0) for r in server), default=0
)
result["instrumentation_postprocess_ms"] = summary(
    [r.get("instrumentation_postprocess_ns", 0) for r in server], 1e6
)
commits = [r for r in client if r.get("type") == "commit"]
new_commits = [r for r in commits if r.get("batch_new", 0) > 0]
result["e1_commits"] = len(commits)
result["e1_new_object_commits"] = len(new_commits)
result["e1_batch_new_objects"] = summary([r["batch_new"] for r in new_commits])
result["e1_batch_progress_objects"] = summary(
    [r["batch_progress"] for r in commits if r.get("batch_progress")]
)
result["e1_insert_to_commit_ms"] = summary(
    [r["end_us"] - r["first_insert_us"] for r in new_commits], 1000
)
result["e1_commit_only_ms"] = summary(
    [
        r["end_us"] - r["before_commit_us"]
        for r in commits
        if r.get("before_commit_us") is not None
    ],
    1000,
)
result["e1_cached_progress_commit_ms"] = summary(
    [
        r["end_us"] - r["first_progress_us"]
        for r in commits
        if not r.get("batch_new") and r.get("first_progress_us") is not None
    ],
    1000,
)
result["snapshots"] = [r for r in client if r.get("type") == "snapshot"]
http = [r for r in client if r.get("type") == "http"]
result["client_send_to_headers_ms"] = summary(
    [r["headers_us"] - r["start_us"] for r in http], 1000
)
result["client_between_http_ms"] = summary(
    [b["start_us"] - a["headers_us"] for a, b in zip(http, http[1:])], 1000
)
result["client_http_inclusive_seconds"] = (
    sum(r["headers_us"] - r["start_us"] for r in http) / 1e6
)
result["client_gap_seconds"] = (
    sum(b["start_us"] - a["headers_us"] for a, b in zip(http, http[1:])) / 1e6
)
result["errors"] = [r for r in server if "failure_body" in r]
result["permit_leak_at_completed_response"] = any(
    r.get("permit_after_close", {}).get("leases", 0) != 0 for r in server
)
(OUT / "analysis.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(
    json.dumps(
        dict(
            requests=result["requests"],
            statuses=result["statuses"],
            attempts=len(manifests),
            new_objects=sum(r["new_global_objects"] for r in result["observations"]),
            committed_objects=commits[-1]["inserted"] if commits else 0,
            object_handler_ms=result["object_handler_ms"],
            top_inclusive_seconds={
                k: round(v["total"] / 1000, 3)
                for k, v in sorted(
                    result["server_work_inclusive_ms"].items(),
                    key=lambda p: p[1].get("total", 0),
                    reverse=True,
                )[:10]
            },
        ),
        ensure_ascii=False,
    )
)

"""완료된 새 campaign의 실제 monotonic HTTP 경계·work만 재집계한다."""

from collections import Counter
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
results = {}
for n in (50000, 100000):
    pointer = json.loads((HERE / f"active-http-{n}.json").read_text())
    out = Path(pointer["out"])
    result = json.loads((out / "result.json").read_text())
    assert result["status"] == "PASS_COLD_IDENTICAL_DELTAS_RESTART"
    summary = json.loads((out / "cold-summary.json").read_text())
    attempts = summary["attempts"]
    rows = [json.loads(line) for line in (out / "server/requests.jsonl").open()]
    ids = {attempt["observation_id"] for attempt in attempts}
    manifests = [
        row for row in rows if row.get("manifest", {}).get("observation_id") in ids
    ]
    first = min(manifests, key=lambda row: row["start_ns"])
    terminal = max(manifests, key=lambda row: row["end_ns"])
    total_sql, resolver = Counter(), Counter()
    for attempt in attempts:
        total_sql.update(attempt["sql_operations"])
        resolver.update(attempt["resolver_work"])
    results[str(n)] = dict(
        status=result["status"],
        cold_observations=len(attempts),
        first_observe_start_utc=first["start_utc"],
        terminal_response_end_utc=terminal["start_utc"]
        + (terminal["end_ns"] - terminal["start_ns"]) / 1e9,
        first_observe_to_terminal_end_seconds=(terminal["end_ns"] - first["start_ns"])
        / 1e9,
        terminal_expires_utc=terminal["manifest"]["expires_at"],
        cold_backend_statement_calls=total_sql,
        cold_backend_resolver_work=resolver,
        interpretation="Statement calls != scanned rows/physical I/O; terminal transfer != later local E3/E4 time",
        post_reads=json.loads((out / "post-reads.json").read_text())
        if (out / "post-reads.json").exists()
        else None,
    )
(HERE / "large-final-review.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2) + "\n"
)
print(
    json.dumps(
        {
            n: {
                k: v[k]
                for k in (
                    "status",
                    "cold_observations",
                    "first_observe_to_terminal_end_seconds",
                )
            }
            for n, v in results.items()
        }
    )
)

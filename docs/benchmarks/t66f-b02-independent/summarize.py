"""저장된 원시 trace와 종료 코드를 다시 집계한다. 측정값을 추정으로 채우지 않는다."""

from collections import Counter
from datetime import datetime
from pathlib import Path
import gzip
import json
import math
import statistics
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(
        gzip.decompress(path.read_bytes())
        if path.suffix == ".gz"
        else path.read_bytes()
    )


def trace(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def utc(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def distribution(xs):
    xs = sorted(xs)
    return (
        {
            "count": len(xs),
            "min": min(xs),
            "median": statistics.median(xs),
            "p95_nearest_rank": xs[math.ceil(0.95 * len(xs)) - 1],
            "max": max(xs),
            "mean": statistics.mean(xs),
        }
        if xs
        else None
    )


def cold(rows):
    stop = next(
        i for i, r in enumerate(rows) if r.get("manifest") and r["status"] == 200
    )
    rows = rows[: stop + 1]
    issued = [r for r in rows if r.get("manifest") and r["status"] == 201]
    observations = []
    for issued_row in issued:
        m = issued_row["manifest"]
        items = [
            r
            for r in rows
            if r["path"].endswith("/" + m["observation_id"] + "/objects")
        ]
        good = [r for r in items if r["status"] == 200]
        last = max([r["end_ns"] for r in good], default=issued_row["end_ns"])
        estimated_last_utc = (
            issued_row["start_utc"] + (last - issued_row["start_ns"]) / 1e9
        )
        observations.append(
            {
                "id": m["observation_id"],
                "sync_root": m["target"]["sync_root"],
                "revision": m["target"]["revision"],
                "available": m["validated_at"],
                "expires": m["expires_at"],
                "ttl_seconds": utc(m["expires_at"]) - utc(m["validated_at"]),
                "object_requests": len(items),
                "successful_packets": len(good),
                "chunks": sum(r.get("chunks", 0) for r in good),
                "new_objects": sum(r.get("new_global_hashes", 0) for r in good),
                "response_entity_bytes": sum(r["response_bytes"] for r in items),
                "request_entity_bytes": sum(r["request_bytes"] for r in items),
                "first_object_after_manifest_s": (
                    items[0]["start_ns"] - issued_row["end_ns"]
                )
                / 1e9
                if items
                else None,
                "last_success_lease_remaining_s_approx": utc(m["expires_at"])
                - estimated_last_utc,
                "errors": [
                    {"status": r["status"], "body": r.get("error")}
                    for r in items
                    if r["status"] != 200
                ],
            }
        )
    good = [r for r in rows if r["path"].endswith("/objects") and r["status"] == 200]
    return {
        "observations": observations,
        "audit_response_postprocess_s": sum(
            r["end_ns"] - r["handler_end_ns"] for r in rows
        )
        / 1e9,
        "handler_aggregate_s": sum(r["handler_end_ns"] - r["start_ns"] for r in rows)
        / 1e9,
        "http_terminal_elapsed_s": (rows[-1]["end_ns"] - rows[0]["start_ns"]) / 1e9,
        "chunks": sum(r.get("chunks", 0) for r in good),
        "new_objects": sum(r.get("new_global_hashes", 0) for r in good),
        "request_entity_bytes": sum(r["request_bytes"] for r in good),
        "response_entity_bytes": sum(r["response_bytes"] for r in good),
        "object_payload_bytes": sum(r.get("decoded_bytes", 0) for r in good),
        "packets": distribution([r["chunks"] for r in good]),
        "status_distribution": dict(Counter(r["status"] for r in rows)),
        "sql_execute_tokens": dict(
            sum((Counter(r.get("sql", {})) for r in rows), Counter())
        ),
    }


def flutter(name):
    events = []
    for line in (HERE / (name + ".jsonl")).read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict):
            events.append(r)
    done = [e for e in events if e.get("type") == "testDone" and not e.get("hidden")]
    return {
        "exit": int((HERE / (name + ".exit")).read_text()),
        "pass": sum(e["result"] == "success" and not e["skipped"] for e in done),
        "fail": sum(e["result"] != "success" and not e["skipped"] for e in done),
        "skip": sum(e["skipped"] for e in done),
        "done": [e for e in events if e.get("type") == "done"],
    }


def main():
    summary = {
        "classification": "NEW INDEPENDENT AUDIT EVIDENCE",
        "large": {},
        "historical": {},
        "tests": {},
    }
    for n in [50000, 100000]:
        directory = HERE / "evidence" / str(n)
        r = load(directory / "result.json.gz")
        c = cold(trace(directory / "server-requests.jsonl.gz"))
        assert (
            r["status"] == "PASS_COLD_IDENTICAL_DELTAS_RESTART"
            and c["chunks"] == c["new_objects"] == r["fixture"]["objects"]
        )
        assert (
            all(o["ttl_seconds"] == 900 for o in c["observations"])
            and len(c["observations"]) <= 3
        )
        assert len({o["sync_root"] for o in c["observations"]}) == 1
        for phase in ["cold", "one_row_delta", "multiple_localized", "restart_delta"]:
            assert load(directory / f"independent-{phase}.json.gz")["status"] == "PASS"
        assert load(directory / "fresh-process.json.gz")["status"] == "PASS"
        x = load(HERE / f"execution-{n}.json")
        assert x["exit_code"] == 0 and x["external_termination"] is None
        summary["large"][str(n)] = {
            "cold_http": c,
            "publication_completed_s": r["publication_completed_us"] / 1e6,
            "cold_with_all_e4_and_readonly_oracle_s": r["cold_elapsed_us"] / 1e6,
            "campaign_client_s": r["elapsed_us"] / 1e6,
            "whole_process_s": x["elapsed_s"],
            "cold_store_work": r["cold_store_work"],
            "cold_publication_commit_us": r["cold_publication_transaction_us"],
            "phases": r["phases"],
            "e1_db_final_bytes": r["e1_database_bytes"],
            "usage_final": r["usage"],
            "client_proc_peak_rss": r["client_process_rss_peak_bytes"],
            "sampled_client_peak_rss": r["sampled_client_rss_peak_bytes"],
            "sampled_tree_peak_rss": x["peak_sampled_process_tree_rss"],
            "full_wire": load(directory / "server-wire-final.json.gz"),
            "fixture": r["fixture"],
            "legacy_files_equal": r["protected_legacy_before"]
            == r["protected_legacy_after"],
        }
        old = HERE.parent / "t66f-b02-a02-correction"
        oldr = load(old / f"http-{n}-result.json.gz")
        oldc = cold(trace(old / f"http-{n}-server-requests.jsonl.gz"))
        assert (
            oldr["status"] == "PASS_COLD_IDENTICAL_DELTAS_RESTART"
            and oldc["chunks"] == oldr["fixture"]["objects"]
        )
        summary["historical"][str(n)] = {
            "label": "CORROBORATED HISTORICAL RESULT — 새 독립 실행과 구별",
            "cold_http": oldc,
            "publication_s": oldr["publication_completed_us"] / 1e6,
            "cold_e4_s": oldr["cold_elapsed_us"] / 1e6,
            "cold_store_work": oldr["cold_store_work"],
            "phases": oldr["phases"],
            "rss_process": oldr["client_process_rss_peak_bytes"],
            "fresh_process_exit": oldr["fresh_process_exit"],
        }
    for name in ["flutter-full", "new-e2", "new-cross-layer", "new-budget"]:
        summary["tests"][name] = flutter(name)
    for name in ["backend-full", "new-backend"]:
        suite = ET.parse(HERE / (name + ".xml")).getroot().find("testsuite")
        summary["tests"][name] = {
            "exit": int((HERE / (name + ".exit")).read_text()),
            **suite.attrib,
        }
    (HERE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()

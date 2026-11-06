"""P03 관측값 집계. 미측정은 null이며 별개의 byte 열을 합산하지 않는다."""

from collections import Counter
import gzip
import json
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"


def load(name):
    return json.loads((OUT / name).read_text())


def stats(values):
    return {
        "n": len(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "population_p95": None,
    }


def machine(name):
    counts = Counter()
    done = None
    path = OUT / (name + ".log.gz")
    stream = gzip.open(path, "rt") if path.exists() else (OUT / (name + ".log")).open()
    for line in stream:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict):
            continue
        if r.get("type") == "done":
            done = r["success"]
        if r.get("type") == "testDone" and not r.get("hidden"):
            counts[
                "SKIP"
                if r.get("skipped")
                else "PASS"
                if r.get("result") == "success"
                else "FAIL"
            ] += 1
    return {"counts": dict(counts), "done": done}


def main():
    result = load("prefix-results.json")
    records = result["records"]
    measured = [r for r in records if not r["warmup"] and not r["renewal"]]
    pairs = []
    for repeat in range(3):
        a = next(r for r in measured if r["label"] == f"prefix-{repeat}-off")
        b = next(r for r in measured if r["label"] == f"prefix-{repeat}-on")
        assert load(a["label"] + "-hashes.json") == load(b["label"] + "-hashes.json")
        for key in [
            "objects",
            "payload_bytes",
            "response_bytes",
            "request_bytes",
            "kinds",
            "work",
        ]:
            assert a[key] == b[key], (repeat, key)
        assert [
            (r["method"], r["status"], r["response_bytes"], r["request_bytes"])
            for r in a["requests"]
        ] == [
            (r["method"], r["status"], r["response_bytes"], r["request_bytes"])
            for r in b["requests"]
        ]
        pairs.append(
            {
                "repeat": repeat,
                "objects": a["objects"],
                "payload_bytes": a["payload_bytes"],
                "wall_extra_us": b["wall_us"] - a["wall_us"],
                "http_extra_us": b["http_us"] - a["http_us"],
                "sql_extra_us": b["sql_us"] - a["sql_us"],
                "residual_extra_us": b["residual_e2_us"] - a["residual_e2_us"],
                "exact_object_set_equal": True,
                "request_shape_equal": True,
            }
        )
    measurements = {}
    for enabled in [False, True]:
        rows = [r for r in measured if r["enabled"] == enabled]
        measurements["ON" if enabled else "OFF"] = {
            k: stats([r[k] for r in rows])
            for k in [
                "wall_us",
                "cpu_ticks",
                "http_us",
                "sql_us",
                "residual_e2_us",
                "collector_store_init_us",
                "snapshot_us",
                "close_us",
                "rss_bytes",
            ]
        }
        if enabled:
            measurements["ON"]["sql_observer_callback_us"] = stats(
                [r["sql_observer_callback_us"] for r in rows]
            )
    loc = load("disposable-location.json")
    server = Path(loc["root"]) / "server"
    trace = [
        json.loads(s) for s in (server / "requests.jsonl").read_text().splitlines()
    ]
    tails = {}
    for row in measured:
        packets = [
            r
            for r in trace
            if r["label"] == row["label"]
            and r["path"].endswith("/objects")
            and r["status"] == 200
        ]
        assert len(packets) == 160
        # First80 packets include byte-heavy initial raw path. The latter79 complete
        # packet cycles are the small index DFS stratum. End=start of next request.
        spans = [
            packets[i + 1]["start_ns"] - packets[i]["start_ns"] for i in range(80, 159)
        ]
        objects = sum(packets[i]["wire"].get("chunks", 0) for i in range(80, 159))
        tails[row["label"]] = {
            "packets": len(spans),
            "objects": objects,
            "wall_ns": sum(spans),
            "seconds_per_object": sum(spans) / 1e9 / objects,
            "backend_wall_ns": sum(packets[i]["wall_ns"] for i in range(80, 159)),
            "scope": "actual sequential request cycles including HTTP/E2/E1 between starts; no terminal/snapshot private command",
        }
    renew = {}
    for label in ["renew-off", "renew-on"]:
        rows = [r for r in trace if r["label"] == label]
        expired = next(r for r in rows if r["status"] == 410)
        fail_index = rows.index(expired)
        observation = next(
            r
            for r in rows[fail_index + 1 :]
            if r["path"].endswith("/observations") and r["status"] == 201
        )
        first_success = next(
            r
            for r in rows[fail_index + 1 :]
            if r["path"].endswith("/objects") and r["status"] == 200
        )
        manifest_rows = [r for r in rows if "manifest" in r]
        assert len(manifest_rows) == 2
        assert (
            manifest_rows[0]["manifest"]["target"]
            == manifest_rows[1]["manifest"]["target"]
        )
        assert all(r["pending"] == 0 for r in rows)
        record = next(r for r in records if r["label"] == label)
        assert record["work"]["cold_same_target_continuations"] == 1
        renew[label] = {
            "expiry_detection_ns": expired["wall_ns"],
            "authorized_manifest_ns": observation["wall_ns"],
            "expiry_start_to_resumed_request_start_s": (
                first_success["start_ns"] - expired["start_ns"]
            )
            / 1e9,
            "expiry_start_to_resumed_response_end_s": (
                first_success["end_ns"] - expired["start_ns"]
            )
            / 1e9,
            "gap_new_manifest_to_resumed_request_s": (
                first_success["start_ns"] - observation["end_ns"]
            )
            / 1e9,
            "same_exact_target": True,
            "manifests": [r["manifest"] for r in manifest_rows],
            "old_observation_status": 410,
            "new_observation_status": 201,
            "retransmitted_objects": sum(r["wire"].get("chunks", 0) for r in rows)
            - record["objects"],
            "pending_native": 0,
            "record": record,
        }
    backend = load("backend-snapshot.json")
    assert backend["complete"] and backend["pending"] == 0
    correctness = []
    for row in records:
        if not row["enabled"]:
            continue
        s = row["sql"]
        prefix = "e2/objects/INSERT/"
        correctness.append(
            {
                "label": row["label"],
                "native_count": row["objects"],
                "native_blob_bytes": row["payload_bytes"],
                "attempted_blob_bytes": s[prefix + "attempted/blobBytes"],
                "effective_blob_bytes": s[prefix + "effective/blobBytes"],
                "committed_blob_bytes": s[prefix + "blobBytes/committed"],
                "primitive": row["primitive"],
                "sql": s,
                "work": row["work"],
                "scope_complete": row["complete_executed_counter_scope"],
                "cache_closed": row["cache_closed"],
            }
        )
    tree = ET.parse(OUT / "backend-targeted.xml")
    summary = {
        "schema_version": 1,
        "measurements": measurements,
        "pairs": pairs,
        "tail_stratum": tails,
        "renewal": renew,
        "counter_reconciliation": correctness,
        "backend": backend,
        "fixture": load("fixture.json"),
        "historical": load("historical-runs.json"),
        "fresh_tests": {
            "backend_targeted": {
                "cases": len(list(tree.iter("testcase"))),
                "failure": len(list(tree.iter("failure"))),
                "error": len(list(tree.iter("error"))),
            },
            "flutter_targeted": machine("flutter-targeted"),
            "small_http": machine("small-http"),
            "real_path": machine("real-path"),
        },
        "new_full_100k_attempts": 0,
        "full_100k_status": "NOT RUN",
        "runtime_exclusions": {
            "isolated_E2_CPU": None,
            "exclusive_observer_total": None,
            "physical_IO": None,
            "population_p95": None,
        },
        "host_peak_client_rss": result["host_peak_rss"],
    }
    (OUT / "analysis.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "pairs": len(pairs),
                "measurements": measurements,
                "renewal_s": {
                    k: v["expiry_start_to_resumed_request_start_s"]
                    for k, v in renew.items()
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

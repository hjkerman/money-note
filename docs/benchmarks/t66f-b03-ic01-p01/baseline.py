"""서로 다른 두 역사100k 실행을 합치지 않고 raw 관측별 timeline 집계."""

from collections import Counter
from datetime import datetime
import gzip
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"


def load(path):
    return json.load(gzip.open(path, "rt"))


def extract(path):
    observations = []
    current = None
    first = None
    terminal = None
    for line in gzip.open(path, "rt"):
        row = json.loads(line)
        if first is None:
            first = row
        if row["path"].endswith("/observations") and row["status"] in [200, 201]:
            manifest = row["manifest"]
            if current and manifest["observation_id"] == current["id"]:
                terminal = row
                break
            current = {
                "number": len(observations) + 1,
                "id": manifest["observation_id"],
                "created": manifest["validated_at"],
                "expires": manifest["expires_at"],
                "start_utc": row["start_utc"],
                "start_ns": row["start_ns"],
                "manifest_end_ns": row["end_ns"],
                "root": manifest["target"]["sync_root"],
                "new_objects": 0,
                "decoded_bytes": 0,
                "request_bytes": 0,
                "response_bytes": 0,
                "handler_ns": 0,
                "requests": 0,
                "status": Counter(),
                "packets": [],
                "sql": Counter(),
                "first_object_start_ns": None,
                "last_success_end_ns": None,
                "progress": [],
            }
            observations.append(current)
        elif current and row["path"].endswith("/objects"):
            current["requests"] += 1
            current["status"][str(row["status"])] += 1
            for k in ["request_bytes", "response_bytes"]:
                current[k] += row[k]
            current["handler_ns"] += row["handler_end_ns"] - row["start_ns"]
            current["sql"].update(row.get("sql", {}))
            if row["status"] == 200:
                current["new_objects"] += row.get("new_global_hashes", 0)
                current["decoded_bytes"] += row["decoded_bytes"]
                current["packets"].append(row["chunks"])
                current["first_object_start_ns"] = (
                    current["first_object_start_ns"] or row["start_ns"]
                )
                current["last_success_end_ns"] = row["end_ns"]
                if current["requests"] % 100 == 0:
                    current["progress"].append(
                        {
                            "elapsed_s": (row["end_ns"] - current["start_ns"]) / 1e9,
                            "new_objects": current["new_objects"],
                        }
                    )
    for r in observations:
        r["productive_elapsed_s"] = (r["last_success_end_ns"] - r["start_ns"]) / 1e9
        expiry = datetime.fromisoformat(r["expires"].replace("Z", "+00:00")).timestamp()
        last_utc = r["start_utc"] + (r["last_success_end_ns"] - r["start_ns"]) / 1e9
        r["last_success_headroom_s"] = expiry - last_utc
        r["packet_distribution"] = dict(Counter(r.pop("packets")))
        r["mean_packet_objects"] = r["new_objects"] / sum(
            r["packet_distribution"].values()
        )
    return {
        "source": str(path.relative_to(HERE.parents[2])),
        "observations": observations,
        "terminal_http_s": (terminal["end_ns"] - first["start_ns"]) / 1e9
        if terminal
        else None,
        "same_root": len({r["root"] for r in observations}) == 1,
        "limits": "HTTP server timestamps only. Client E1/traversal disjoint timing was not captured. Progress is newly transferred, not exact durable COMMIT timestamp.",
    }


def main():
    base = HERE.parent
    result = {
        "independent": extract(
            base / "t66f-b02-independent/evidence/100000/server-requests.jsonl.gz"
        ),
        "implementation": extract(
            base / "t66f-b02-a02-correction/http-100000-server-requests.jsonl.gz"
        ),
    }
    sample = json.loads(
        (base / "t66f-b03-ic01/evidence/high-n-sample-result.json").read_text()
    )
    med = {
        str(b): statistics.median(
            s["microseconds"] for s in sample["samples"] if s["enabled"] == b
        )
        / 1e6
        for b in [False, True]
    }
    result["old_sample"] = {
        "objects": sample["objects"],
        "bytes": sample["payload_bytes"],
        "kinds": sample["distribution"],
        "median_seconds": med,
        "absolute_extra_seconds": med["True"] - med["False"],
        "ratio": med["True"] / med["False"],
        "scope": "selected-by-kind/hash, E1 verify/schema/commit; new independent stores per mode; no cache flush/WAL sampling. Observer open/staging outside timer, first-install inside first DML. Five measured pairs after warmup.",
    }
    (OUT / "historical-baselines.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: {
                    "terminal_http_s": v["terminal_http_s"],
                    "objects": [r["new_objects"] for r in v["observations"]],
                }
                for k, v in result.items()
                if k != "old_sample"
            }
        )
    )


if __name__ == "__main__":
    main()

"""Bounded incremental read of synthetic trace; not a protocol authority."""

import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
n = int(sys.argv[1])
assert n in (1000, 50000, 100000)
pointer = json.loads((HERE / f"active-http-{n}.json").read_text())
out = Path(pointer["out"])
cache = HERE / f"progress-{n}.json"
state = (
    json.loads(cache.read_text())
    if cache.exists()
    else dict(
        offset=0, requests=0, objects=0, http_bytes=0, observations={}, statuses={}
    )
)
trace = out / "server/requests.jsonl"
if trace.exists():
    with trace.open("rb") as stream:
        stream.seek(state["offset"])
        raw = stream.read(4 * 1024 * 1024)
    lines = raw.split(b"\n")
    state["offset"] += sum(len(row) + 1 for row in lines[:-1])
    for line in lines[:-1]:
        row = json.loads(line)
        state["requests"] += 1
        status = str(row.get("status"))
        state["statuses"][status] = state["statuses"].get(status, 0) + 1
        state["objects"] = max(state["objects"], row.get("global_unique_objects", 0))
        state["http_bytes"] += row.get("response_bytes", 0)
        manifest = row.get("manifest")
        if manifest:
            state["observations"][manifest["observation_id"]] = {
                k: manifest[k] for k in ("validated_at", "expires_at")
            }
phase = "backend bootstrap"
fixture = out / "server/backend-fixture.json"
if fixture.exists():
    phase = "cold acquisition"
result = out / "result.json"
if result.exists():
    value = json.loads(result.read_text())
    phase = value.get("status", phase)
    state["phases"] = [p["phase"] for p in value.get("phases", [])]
fresh = out / "fresh-process.json"
if fresh.exists():
    verified = json.loads(fresh.read_text())
    state["fresh_process_healthy"] = verified["healthy"]
    state["fresh_objects_checked"] = verified["objects_checked"]
state.update(
    elapsed_seconds=round(time.time() - pointer["started_utc"], 1), phase=phase, n=n
)
cache.write_text(json.dumps(state, indent=2) + "\n")
print(json.dumps({k: v for k, v in state.items() if k != "offset"}))

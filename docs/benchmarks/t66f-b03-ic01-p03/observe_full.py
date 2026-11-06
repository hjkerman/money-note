"""원 trace를 한 번씩 읽어 actual observation 경계와 client checkpoint를 보존한다."""

from datetime import datetime
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
root = Path(json.loads((OUT / "disposable-location.json").read_text())["root"])
trace = (root / "server/requests.jsonl").open()
observations = {}
current = None
last_checkpoint = None
partial = ""
started = time.monotonic()
path = OUT / "full-live-observations.jsonl"
with path.open("x", buffering=1) as stream:
    for sample in range(3601):
        while True:
            pos = trace.tell()
            line = trace.readline()
            if not line:
                break
            if not line.endswith("\n"):
                trace.seek(pos)
                break
            row = json.loads(line)
            if row["label"] != "full":
                continue
            if "manifest" in row:
                manifest = row["manifest"]
                oid = manifest["observation_id"]
                if oid not in observations:
                    current = {
                        "number": len(observations) + 1,
                        "id": oid,
                        "created": manifest["validated_at"],
                        "expires": manifest["expires_at"],
                        "manifest_request_start_ns": row["start_ns"],
                        "manifest_response_pre_send_end_ns": row["end_ns"],
                        "requests": 0,
                        "transferred_object_events": 0,
                        "request_bytes": 0,
                        "response_bytes": 0,
                        "statuses": {},
                        "last_success_pre_send_ns": None,
                        "native_pending_peak": 0,
                    }
                    observations[oid] = current
                    stream.write(
                        json.dumps(
                            {
                                "event": "actual_new_observation",
                                "observed_utc": datetime.now().astimezone().isoformat(),
                                "state": current,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            path_parts = row["path"].split("/")
            oid = (
                path_parts[5]
                if len(path_parts) > 5
                else (current["id"] if current else None)
            )
            state = observations.get(oid)
            if state is not None:
                state["requests"] += 1
                state["request_bytes"] += row["wire"].get("request_entity_bytes", 0)
                state["response_bytes"] += row["wire"].get("response_entity_bytes", 0)
                key = str(row["status"])
                state["statuses"][key] = state["statuses"].get(key, 0) + 1
                state["native_pending_peak"] = max(
                    state["native_pending_peak"], row["pending"]
                )
                if row["path"].endswith("/objects") and row["status"] == 200:
                    state["transferred_object_events"] += row["wire"].get("chunks", 0)
                    state["last_success_pre_send_ns"] = row["end_ns"]
                if row["status"] >= 400:
                    stream.write(
                        json.dumps(
                            {
                                "event": "actual_http_error_boundary",
                                "observed_utc": datetime.now().astimezone().isoformat(),
                                "request": row,
                                "observation_state": state,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
        file = OUT / "full-progress.json"
        if file.exists():
            try:
                checkpoint = json.loads(file.read_text())
            except ValueError:
                checkpoint = None
            if checkpoint is not None and checkpoint["elapsed_us"] != last_checkpoint:
                last_checkpoint = checkpoint["elapsed_us"]
                stream.write(
                    json.dumps(
                        {
                            "event": "actual_client_checkpoint",
                            "observation_states": list(observations.values()),
                            "client": checkpoint,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                (OUT / "full-live-latest.json").write_text(
                    json.dumps(
                        {
                            "observations": list(observations.values()),
                            "checkpoint": checkpoint,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        if (OUT / "full-result.json").exists() or time.monotonic() - started >= 7200:
            break
        time.sleep(2)
trace.close()

"""두 원 실행의 lease 경계와 critical-path 진행을 별도 보존한다."""

import gzip
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "p03_historical", HERE.parent / "t66f-b03-ic01-p01/baseline.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
result = {}
for label, path in [
    (
        "independent",
        HERE.parent / "t66f-b02-independent/evidence/100000/server-requests.jsonl.gz",
    ),
    (
        "implementation",
        HERE.parent / "t66f-b02-a02-correction/http-100000-server-requests.jsonl.gz",
    ),
]:
    d = m.extract(path)
    trace = []
    cold = True
    last = None
    for line in gzip.open(path, "rt"):
        r = json.loads(line)
        if r["path"].endswith("/observations") and r["status"] in (200, 201):
            if last == r["manifest"]["observation_id"]:
                break
            last = r["manifest"]["observation_id"]
        if r["path"].endswith("/objects") and r["status"] == 200:
            trace.append(
                {
                    k: r[k]
                    for k in [
                        "start_ns",
                        "handler_end_ns",
                        "end_ns",
                        "chunks",
                        "decoded_bytes",
                        "new_global_hashes",
                        "unique_global_objects",
                    ]
                    if k in r
                }
            )
    d["cold_successful_packets"] = len(trace)
    d["first_160"] = trace[:160]
    result[label] = d
(HERE / "evidence/historical-runs.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(
    json.dumps(
        {
            k: {
                "terminal_s": v["terminal_http_s"],
                "objects": [o["new_objects"] for o in v["observations"]],
                "last_headroom_s": v["observations"][-1]["last_success_headroom_s"],
            }
            for k, v in result.items()
        }
    )
)

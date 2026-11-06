"""측정 사이의 독립 read-only SQLite reachable size census. hash/parse 재실행 없음."""

from collections import defaultdict
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import time

HERE = Path(__file__).resolve().parent
pid = int(sys.argv[1])
out = HERE / "evidence"
fixture = json.loads((out / "fixture.json").read_text())
target = fixture["target"]
paths = []
for fd in Path(f"/proc/{pid}/fd").iterdir():
    try:
        p = Path(os.readlink(fd))
    except OSError:
        continue
    if str(p).startswith("/tmp/money-note-d1-") and p.name == "synthetic.sqlite3":
        paths.append(p)
assert paths, "owned synthetic DB not found"
path = paths[0]
start = time.perf_counter()
conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
conn.execute("PRAGMA query_only=ON")
values = defaultdict(list)
try:
    rows = conn.execute(
        """WITH RECURSIVE reachable(hash) AS (
 VALUES (?),(?),(?),(?) UNION
 SELECT child FROM sync_object_edges JOIN reachable ON parent=reachable.hash
 ) SELECT kind,length(body) FROM sync_objects JOIN reachable USING(hash)""",
        tuple(target[k + "_ref"]["hash"] for k in ["raw", "index", "hot", "control"]),
    )
    for kind, size in rows:
        values[kind].append(size)
finally:
    conn.close()
result = {}
for kind, sizes in values.items():
    sizes.sort()
    n = len(sizes)
    result[kind] = {
        "count": n,
        "bytes": sum(sizes),
        "min": sizes[0],
        "p50": sizes[math.ceil(n * 0.5) - 1],
        "p95": sizes[math.ceil(n * 0.95) - 1],
        "max": sizes[-1],
    }
assert sum(r["count"] for r in result.values()) == 400532
assert sum(r["bytes"] for r in result.values()) == 261543083
for k, v in result.items():
    assert (
        v["count"] == fixture["graph"]["kinds"][k]
        and v["bytes"] == fixture["graph"]["kind_bytes"][k]
    )
(out / "fixture-size-distribution.json").write_text(
    json.dumps(
        {
            "method": "read-only recursive native edge reachability plus SQLite length(BLOB); no rehash/reparse; outside paired timing",
            "objects": 400532,
            "canonical_bytes": 261543083,
            "kinds": result,
            "wall_seconds": time.perf_counter() - start,
            "byte_size_p95": "exact census percentile, not runtime population p95",
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
print("PASS: 400532 reachable objects size census reconciled")

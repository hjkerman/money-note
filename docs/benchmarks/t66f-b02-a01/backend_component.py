"""실제 PathResolver의 작은 부표본 재생. HTTP/전체 D→E 성공 증거가 아니다.

제품 함수에 위임하는 count-only hook이며 검증을 생략/캐시하지 않는다.
"""

from collections import Counter
import base64
from functools import wraps
import json
from pathlib import Path
import sqlite3
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
from isolated_sync import canonical  # noqa: E402
from isolated_sync.observation import ObservationRepository  # noqa: E402
from isolated_sync.transfer import PathResolver  # noqa: E402

OUT = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(json.loads((HERE / "active-run.json").read_text())["out"])
)
sample = json.loads((OUT / "component-sample.json").read_text())
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("CREATE TABLE sync_objects(hash TEXT PRIMARY KEY,kind TEXT,body BLOB)")
conn.executemany(
    "INSERT INTO sync_objects VALUES(?,?,?)",
    [
        (o["ref"]["hash"], o["kind"], base64.b64decode(o["bytes_base64"]))
        for o in sample["objects"]
    ],
)
conn.commit()
repo = object.__new__(
    ObservationRepository
)  # Only _view_object uses supplied read-only conn.
conn.execute("PRAGMA query_only=1")
counts = Counter()
bytes_by_kind = Counter()
times = Counter()
contexts = Counter()


def hook(original, label, charge=None):
    @wraps(original)
    def call(*args, **kw):
        start = time.perf_counter_ns()
        counts[label] += 1
        if charge:
            charge(args, kw)
        try:
            return original(*args, **kw)
        finally:
            times[label] += time.perf_counter_ns() - start

    return call


old_hash = canonical.hash_bytes
old_decode = canonical.decode_c1
old_validate = PathResolver.validate


def charge_hash(args, kw):
    kind, raw = args
    # hash_bytes actual preimage: domain ASCII + NUL + exact raw input.
    n = len(f"money-note.sync.v1/{kind}\0".encode()) + len(raw)
    counts["hash_input_bytes"] += n
    bytes_by_kind[kind] += n


def charge_decode(args, kw):
    counts["canonical_validate_input_bytes"] += len(args[0])


def charge_validate(args, kw):
    obj, edge = args[1:3]
    key = (
        obj.hash,
        tuple(sorted(edge.kinds)),
        edge.table,
        edge.root,
        edge.prefix,
        edge.count,
        edge.parent_count,
        json.dumps(edge.desc, sort_keys=True),
    )
    contexts[key] += 1


baseline = []
for _ in range(3):
    resolver = PathResolver(conn, repo, sample["manifest"]["target"])
    start = time.perf_counter_ns()
    for path in sample["paths"]:
        obj = resolver.resolve(path)
        assert obj.hash == path[-1]
    baseline.append(
        dict(
            ns=time.perf_counter_ns() - start,
            reads=resolver.reads,
            bytes_read=resolver.bytes_read,
        )
    )
# Replace module aliases of the original callable, so imported decode/hash call
# sites in already loaded isolated modules are counted, still delegated exactly.
for module in list(sys.modules.values()):
    if module is None or not getattr(module, "__name__", "").startswith(
        "isolated_sync"
    ):
        continue
    for name, value in list(vars(module).items()):
        if value is old_hash:
            setattr(module, name, hook(old_hash, "hash", charge_hash))
        elif value is old_decode:
            setattr(module, name, hook(old_decode, "canonical_validate", charge_decode))
PathResolver.validate = hook(old_validate, "local_shape_validate", charge_validate)
resolver = PathResolver(conn, repo, sample["manifest"]["target"])
start = time.perf_counter_ns()
for path in sample["paths"]:
    obj = resolver.resolve(path)
    assert obj.hash == path[-1]
measured_ns = time.perf_counter_ns() - start
conn.close()
value = dict(
    label="ACTUAL UNCHANGED PATHRESOLVER COMPONENT, NOT HTTP OR FULL D-E",
    paths=len(sample["paths"]),
    unique_objects=sample["unique_objects"],
    baseline=baseline,
    instrumented_ns=measured_ns,
    counter_instrumentation_ratio=measured_ns
    / statistics.median(b["ns"] for b in baseline),
    calls=counts,
    inclusive_ns=times,
    hash_input_bytes_by_kind=bytes_by_kind,
    actual_object_reads=resolver.reads,
    actual_object_bytes_read=resolver.bytes_read,
    unique_validation_contexts=len(contexts),
    repeated_validation_contexts=sum(v - 1 for v in contexts.values()),
    validated_context_frequency=dict(Counter(contexts.values())),
    selected_terminal_bytes=sum(
        int(o["ref"]["bytes"])
        for o in sample["objects"]
        if o["ref"]["hash"] in {p[-1] for p in sample["paths"]}
    ),
    unchanged=True,
    read_only_sqlite=True,
)
(OUT / "backend-component.json").write_text(json.dumps(value, indent=2) + "\n")
print(
    json.dumps(
        {
            k: value[k]
            for k in [
                "label",
                "paths",
                "actual_object_reads",
                "unique_validation_contexts",
                "repeated_validation_contexts",
                "counter_instrumentation_ratio",
            ]
        }
    )
)

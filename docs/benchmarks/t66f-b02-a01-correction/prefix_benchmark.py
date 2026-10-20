"""동일 보존 부표본의 strict/요청-local prefix 비교. HTTP 전체 비용이 아니다."""

from collections import Counter
import base64
import gzip
import json
from pathlib import Path
import sqlite3
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
from isolated_sync.observation import ObservationRepository  # noqa: E402
from isolated_sync.transfer import PathResolver  # noqa: E402


def main():
    sample = json.loads(
        (
            ROOT / "docs/benchmarks/t66f-b02-a01/evidence/first/component-sample.json"
        ).read_text()
    )
    before = types.ModuleType("strict_before")
    exec(
        compile(
            gzip.decompress((HERE / "transfer.py.before.gz").read_bytes()),
            "strict_before",
            "exec",
        ),
        before.__dict__,
    )
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE sync_objects(hash TEXT PRIMARY KEY,kind TEXT,body BLOB)")
    conn.executemany(
        "INSERT INTO sync_objects VALUES(?,?,?)",
        [
            (
                o["ref"]["hash"],
                o["kind"],
                base64.b64decode(o["bytes_base64"], validate=True),
            )
            for o in sample["objects"]
        ],
    )
    conn.commit()
    conn.execute("PRAGMA query_only=1")
    repo = object.__new__(ObservationRepository)
    expected = {
        o["ref"]["hash"]: base64.b64decode(o["bytes_base64"]) for o in sample["objects"]
    }
    results = []
    for shape, paths in (
        ("shared64", sample["paths"]),
        ("repeated64", [sample["paths"][0]] * 64),
        ("root_only", [sample["paths"][0][:1]] * 64),
    ):
        for mode in ("before", "after"):
            for iteration in range(3):
                conn.execute("BEGIN")
                resolver = (
                    before.PathResolver(conn, repo, sample["manifest"]["target"])
                    if mode == "before"
                    else PathResolver(
                        conn,
                        repo,
                        sample["manifest"]["target"],
                        prefix_capacity=64 * 512,
                        prefix_bytes=1048576,
                    )
                )
                sql, validation = Counter(), Counter()
                conn.set_trace_callback(
                    lambda statement: sql.update([statement.split()[0].upper()])
                )
                original = resolver.validate

                def validate(obj, edge):
                    validation["calls"] += 1
                    validation["input_object_bytes"] += len(obj.raw)
                    return original(obj, edge)

                resolver.validate = validate
                started, cpu = time.perf_counter(), time.thread_time()
                for path in paths:
                    obj = resolver.resolve(path)
                    assert obj.raw == expected[path[-1]]
                value = dict(
                    shape=shape,
                    mode=mode,
                    iteration=iteration,
                    wall_seconds=time.perf_counter() - started,
                    cpu_seconds=time.thread_time() - cpu,
                    requested_objects=len(paths),
                    actual_object_reads=resolver.reads,
                    actual_read_bytes=resolver.bytes_read,
                    sql=sql,
                    validation=validation,
                    prefix_hits=getattr(resolver, "prefix_hits", 0),
                    prefix_peak=getattr(resolver, "prefix_peak", 0),
                    prefix_byte_peak=getattr(resolver, "prefix_byte_peak", 0),
                )
                conn.set_trace_callback(None)
                conn.rollback()
                results.append(value)
    conn.close()
    (HERE / "prefix-performance.json").write_text(
        json.dumps(
            dict(
                scope="동일 부표본의 resolver-only 비교; auth/admission/HTTP/E1은 측정 밖",
                source="docs/benchmarks/t66f-b02-a01/evidence/first/component-sample.json",
                results=results,
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            [
                {
                    k: r[k]
                    for k in (
                        "shape",
                        "mode",
                        "actual_object_reads",
                        "prefix_hits",
                        "wall_seconds",
                    )
                }
                for r in results
                if r["iteration"] == 0
            ]
        )
    )


if __name__ == "__main__":
    main()

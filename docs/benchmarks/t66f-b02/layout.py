"""독립 read-only graph 분석 + disposable SQLite footprint 모델.

제품 client store가 아니다. E1 budget/validator를 비활성화한 통합 성공으로 해석하지 않는다.
core table/index의 DDL만 재사용하며 bulk transaction 시간은 E1 fsync latency가 아니다.
"""

import argparse
import hashlib
import json
from pathlib import Path
import resource
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    str(ROOT / "backend"),
    str(ROOT / "scripts/benchmarks"),
    str(ROOT / "docs/benchmarks/t66f-phase-b"),
]
from t66e2_server import children  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    folder = args.directory
    manifest = json.loads((folder / "manifest-g1.json").read_text())
    src = sqlite3.connect(f"file:{folder / 'objects.sqlite'}?mode=ro", uri=True)
    out = folder / "layout-model.sqlite"
    assert not out.exists(), "새 disposable 모델만 허용"
    dst = sqlite3.connect(out)
    ddl = (ROOT / "mobile/lib/src/segmented/store.dart").read_text()
    schema = ddl.split("const _schema = '''", 1)[1].split("'''", 1)[0]
    # Mandatory triggers/usage/profile를 구현했다고 주장하지 않는 독립 layout 모델.
    dst.executescript(
        "\n".join(
            line
            for line in schema.splitlines()
            if line.startswith(("CREATE TABLE", "CREATE INDEX"))
        )
    )
    dst.execute("PRAGMA foreign_keys=ON")
    dst.execute("PRAGMA synchronous=EXTRA")
    stage = "66260200-0000-4000-8000-000000000001"
    encoded = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode()
    dst.execute(
        "INSERT INTO staging VALUES(?,?,?,?)",
        (stage, encoded, hashlib.sha256(encoded).hexdigest(), "synthetic"),
    )
    pending = [
        manifest["target"][r]
        for r in ("raw_ref", "index_ref", "hot_ref", "control_ref")
    ]
    for role, ref in zip(("raw", "index", "hot", "control"), pending):
        dst.execute(
            "INSERT OR IGNORE INTO refs VALUES(?,?)", (ref["hash"], ref["bytes"])
        )
        dst.execute(
            "INSERT INTO staging_roots VALUES(?,?,?)", (stage, role, ref["hash"])
        )
    seen = set()
    payload = edges = duplicates = 0
    start = time.perf_counter_ns()
    cpu = time.process_time_ns()
    while pending:
        ref = pending.pop()
        if ref["hash"] in seen:
            duplicates += 1
            continue
        assert len(seen) < 600000  # 이 분석기의 유한 작업 한도이며 제품 설정이 아니다.
        kind, body = src.execute(
            "SELECT kind,body FROM sync_objects WHERE hash=?", (ref["hash"],)
        ).fetchone()
        assert len(body) == int(ref["bytes"])
        assert (
            hashlib.sha256(
                b"money-note.sync.v1/" + kind.encode() + b"\0" + body
            ).hexdigest()
            == ref["hash"]
        )
        value = json.loads(body)
        assert value["kind"] == kind
        child = children(value)
        dst.execute(
            "INSERT OR IGNORE INTO refs VALUES(?,?)", (ref["hash"], ref["bytes"])
        )
        dst.execute(
            "INSERT INTO objects VALUES(?,?,?,?)",
            (ref["hash"], kind, body, "segmented-e1/1"),
        )
        dst.execute("INSERT INTO staging_objects VALUES(?,?)", (stage, ref["hash"]))
        for position, c in enumerate(child):
            dst.execute(
                "INSERT OR IGNORE INTO refs VALUES(?,?)", (c["hash"], c["bytes"])
            )
            # index-child는 두 타입을 허용. snapshot edge는 child의 실제 타입.
            ck = src.execute(
                "SELECT kind FROM sync_objects WHERE hash=?", (c["hash"],)
            ).fetchone()[0]
            kinds = "index-leaf,index-node" if ck.startswith("index-") else ck
            dst.execute(
                "INSERT INTO edges VALUES(?,?,?,?)",
                (ref["hash"], position, c["hash"], kinds),
            )
        seen.add(ref["hash"])
        payload += len(body)
        edges += len(child)
        pending.extend(reversed(child))
    dst.commit()
    counts = {
        t: dst.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        for t in ("objects", "refs", "edges", "staging_objects")
    }
    assert counts["objects"] == counts["refs"] == counts["staging_objects"] == len(seen)
    assert counts["edges"] == edges
    assert not dst.execute("PRAGMA foreign_key_check").fetchall()
    logical_metadata = len(seen) * 448 + edges * 256 + len(encoded) + 256 + 4 * 128
    report = dict(
        status="PASS",
        boundary="독립 footprint 모델; E1/E2 성공 아님",
        objects=len(seen),
        edges=edges,
        duplicate_references=duplicates,
        payload_bytes=payload,
        model_metadata_charge=logical_metadata,
        default_metadata_budget=32 * 1024**2,
        core_database_bytes=out.stat().st_size,
        page_size=dst.execute("PRAGMA page_size").fetchone()[0],
        page_count=dst.execute("PRAGMA page_count").fetchone()[0],
        journal_mode=dst.execute("PRAGMA journal_mode").fetchone()[0],
        wall_ns=time.perf_counter_ns() - start,
        cpu_ns=time.process_time_ns() - cpu,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        integrity=dst.execute("PRAGMA integrity_check").fetchone()[0],
        schema_shared_dependency="E1 core table/index DDL; trigger/guard 포함 안 함",
        write_bytes_not_measured=True,
        physical_io_not_measured=True,
    )
    (folder / "layout.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    dst.close()
    src.close()
    print(json.dumps({"input": str(folder), "objects": len(seen), "status": "PASS"}))


if __name__ == "__main__":
    main()

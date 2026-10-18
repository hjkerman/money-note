"""동일 seed/H의 실제 backend graph를 새 disposable DB에서 만든다.

저장하는 objects.sqlite는 read-only offline 분석 입력이며 E1/E2 client store가 아니다.
제품 한도·protocol·accepted pointer·financial 앱 저장소는 변경하지 않는다.
"""

from collections import Counter
from contextlib import closing
from datetime import date
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sqlite3
import sys
import time
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    str(ROOT / "backend"),
    str(ROOT / "scripts/benchmarks"),
    str(ROOT / "docs/benchmarks/t66f-phase-b"),
]
from app.services.authoritative_state import BundleCredential  # noqa: E402
from isolated_sync.observation import Evaluation  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionSandbox  # noqa: E402
from isolated_sync.inputs import BoundedInputs  # noqa: E402
from isolated_sync.raw import TABLES  # noqa: E402
from tests.test_isolated_sync_observation import NOW  # noqa: E402
from t66d2b_writers import seed  # noqa: E402
from tests.d2b_financial_reference import projections  # noqa: E402
from t66e2_server import children  # noqa: E402


def write(path, x):
    path.write_text(json.dumps(x, ensure_ascii=False, indent=2) + "\n")


def walk(db, target):
    pending = [
        (target[role], 0) for role in ["raw_ref", "index_ref", "hot_ref", "control_ref"]
    ]
    seen = set()
    kinds = Counter()
    sizes = Counter()
    edge_count = 0
    max_depth = 0
    max_fanout = 0
    largest = 0
    raw_rows = Counter()
    facts = Counter()
    largest_ref = None
    while pending:
        ref, depth = pending.pop()
        if ref["hash"] in seen:
            continue
        row = db.execute(
            "SELECT kind,body FROM sync_objects WHERE hash=?", (ref["hash"],)
        ).fetchone()
        assert row is not None
        kind, body = row
        assert len(body) == int(ref["bytes"])
        assert (
            hashlib.sha256(
                b"money-note.sync.v1/" + kind.encode() + b"\0" + body
            ).hexdigest()
            == ref["hash"]
        )
        obj = json.loads(body)
        assert obj["kind"] == kind
        seen.add(ref["hash"])
        kinds[kind] += 1
        sizes[kind] += len(body)
        if len(body) > largest:
            largest = len(body)
            largest_ref = ref
        max_depth = max(max_depth, depth)
        child = children(obj)
        edge_count += len(child)
        max_fanout = max(max_fanout, len(child))
        pending.extend((c, depth + 1) for c in child)
        if kind == "snapshot-leaf":
            raw_rows[obj["table"]] += len(obj["rows"])
        if kind == "index-leaf":
            for f in obj["facts"]:
                facts[f["key"][0]] += 1
    return seen, dict(
        objects=len(seen),
        canonical_bytes=sum(sizes.values()),
        kinds=dict(kinds),
        kind_bytes=dict(sizes),
        edges=edge_count,
        max_depth=max_depth,
        max_fanout=max_fanout,
        largest_object=largest,
        largest_ref=largest_ref,
        raw_rows=dict(raw_rows),
        fact_domains=dict(facts),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    assert args.n in [
        1000,
        5000,
        10000,
        12000,
        15000,
        20000,
        24900,
        25000,
        50000,
        100000,
    ]
    args.out.mkdir(parents=True, exist_ok=True)
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    report = dict(
        n=args.n,
        seed=662602,
        current_ledger_rows=105,
        d=1,
        status="RUNNING",
        producer="actual RetentionSandbox/bootstrap/finalizer/ObservationRepository",
        offline_export_not_client_store=True,
    )
    write(args.out / "result.json", report)
    cred = BundleCredential(hashlib.sha256(b"synthetic-b02-only").hexdigest(), 1)
    with (
        RetentionSandbox() as backend,
        patch("app.services.judgment.common._MESSAGE_RANDOM.randrange", return_value=0),
    ):
        with backend.connect() as conn:
            seed(conn, args.n)
            conn.execute(
                "INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order,is_primary_income) VALUES (101,'2026-10-05','fixed-width-cash',-50,2,0)"
            )
            conn.execute(
                "INSERT INTO users(id,username,password_hash) VALUES (1,'b02-synthetic','unused')"
            )
            conn.execute(
                "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",
                (cred.token_hash,),
            )
        backend.install()
        start = time.perf_counter_ns()
        cpu = time.process_time_ns()
        backend.bootstrap()
        report["bootstrap"] = dict(
            wall_ns=time.perf_counter_ns() - start,
            cpu_ns=time.process_time_ns() - cpu,
            max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            db_bytes=backend.path.stat().st_size,
        )
        repo = RetentionRepository(
            backend,
            clock=lambda: NOW,
            evaluation=lambda: Evaluation(date(2026, 10, 5), 540),
        )
        first = repo.create(cred, request_id=str(uuid4()), guard=lambda: cred)
        write(args.out / "manifest-g1.json", first)
        with closing(sqlite3.connect(backend.path)) as conn:
            rows = {
                t: conn.execute("SELECT count(*) FROM " + t).fetchone()[0]
                for t in TABLES
            }
            before, graph = walk(conn, first["target"])
            catalog_before = conn.execute(
                "SELECT count(*) FROM sync_objects"
            ).fetchone()[0]
            all_before = {r[0] for r in conn.execute("SELECT hash FROM sync_objects")}
        report.update(
            table_rows=rows,
            g1=graph,
            catalog_objects_g1=catalog_before,
            catalog_unreachable_g1=catalog_before - len(before),
        )
        write(args.out / "result.json", report)
        start = time.perf_counter_ns()
        cpu = time.process_time_ns()
        with backend.connect() as conn:
            conn.begin_capture()
            writer = BoundedInputs(conn)
            writer.execute(
                "UPDATE ledger_entries SET amount_value=? WHERE id=1002", (123456,)
            )
            projections(writer)
            conn.finalize()
            conn.commit()
        report["delta_generation"] = dict(
            wall_ns=time.perf_counter_ns() - start, cpu_ns=time.process_time_ns() - cpu
        )
        second = repo.create(
            cred, request_id=str(uuid4()), guard=lambda: cred, base=first["target"]
        )
        write(args.out / "manifest-g2.json", second)
        with closing(sqlite3.connect(backend.path)) as conn:
            after, graph2 = walk(conn, second["target"])
            fresh = after - before
            new_bytes = sum(
                conn.execute(
                    "SELECT length(body) FROM sync_objects WHERE hash=?", (h,)
                ).fetchone()[0]
                for h in fresh
            )
            all_after = {r[0] for r in conn.execute("SELECT hash FROM sync_objects")}
            report.update(
                g2=graph2,
                delta_new_reachable_objects=len(fresh),
                delta_new_reachable_bytes=new_bytes,
                reused_reachable_objects=len(after & before),
                g1_g2_union_objects=len(after | before),
                catalog_new_objects=len(all_after - all_before),
                catalog_objects_g2=len(all_after),
            )
            dest = sqlite3.connect(args.out / "objects.sqlite")
            dest.execute(
                "CREATE TABLE sync_objects(hash TEXT PRIMARY KEY,kind TEXT NOT NULL,body BLOB NOT NULL)"
            )
            dest.executemany(
                "INSERT INTO sync_objects VALUES(?,?,?)",
                conn.execute("SELECT hash,kind,body FROM sync_objects"),
            )
            dest.commit()
            dest.close()
        report.update(
            offline_export_bytes=(args.out / "objects.sqlite").stat().st_size,
            max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            status="PASS",
            e2_actual_downloads=None,
            e2_cache_hits=None,
            actual_wire_bytes=None,
        )
        write(args.out / "result.json", report)
    print(
        json.dumps(
            dict(
                n=args.n,
                objects=report["g1"]["objects"],
                delta=report["delta_new_reachable_objects"],
                status=report["status"],
            )
        )
    )


if __name__ == "__main__":
    main()

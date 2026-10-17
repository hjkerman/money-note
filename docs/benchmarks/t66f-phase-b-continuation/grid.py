"""고정 H/D backend grid. 실제 loopback HTTP와 test-only SQLite delegate."""

from collections import Counter
from contextlib import closing
from datetime import date
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import resource
import socket
import sqlite3
import statistics
import sys
import threading
import time
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts/benchmarks")]
from payload_bytes import Brotli  # noqa: E402

brotli = Brotli()
import httpx  # noqa: E402
import uvicorn  # noqa: E402
from app.auth import _hash_session_token  # noqa: E402
from isolated_sync.http import create_app  # noqa: E402
from isolated_sync.observation import Evaluation  # noqa: E402
from isolated_sync.observation_schema import ObservationConnection  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionSandbox  # noqa: E402
from isolated_sync.inputs import BoundedInputs  # noqa: E402
from tests.test_isolated_sync_observation import NOW  # noqa: E402
from tests.test_isolated_sync_finalization import verify  # noqa: E402
from tests.d2b_financial_reference import projections  # noqa: E402
from t66d2b_writers import seed  # noqa: E402


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class Cursor:
    def __init__(self, cursor, counts):
        self.cursor, self.counts = cursor, counts

    def __getattr__(self, name):
        return getattr(self.cursor, name)

    def row(self, row):
        if row is not None:
            self.counts["rows_returned"] += 1
            for value in row:
                if isinstance(value, bytes):
                    self.counts["blob_bytes_returned"] += len(value)
        return row

    def __iter__(self):
        for row in self.cursor:
            yield self.row(row)

    def fetchone(self):
        return self.row(self.cursor.fetchone())

    def fetchall(self):
        return [self.row(row) for row in self.cursor.fetchall()]


class Meter:
    def __init__(self):
        self.active = False
        self.counts = Counter()
        self.sql = Counter()
        self.queries = {}

    def __enter__(self):
        original = ObservationConnection.execute
        meter = self

        def execute(conn, sql, parameters=()):
            if not meter.active:
                return original(conn, sql, parameters)
            verb = sql.lstrip().split()[0].upper()
            meter.counts["sql"] += 1
            meter.counts[verb] += 1
            meter.sql[sql] += 1
            if verb == "SELECT":
                meter.queries[sql] = parameters
            for p in parameters:
                if isinstance(p, bytes):
                    meter.counts["bound_blob_bytes"] += len(p)
            if "sync_pins" in sql.lower():
                meter.counts["pin_" + verb.lower()] += 1
            return Cursor(original(conn, sql, parameters), meter.counts)

        self.patch = patch.object(ObservationConnection, "execute", execute)
        self.patch.start()
        return self

    def __exit__(self, *args):
        self.patch.stop()

    def begin(self):
        self.counts.clear()
        self.sql.clear()
        self.queries.clear()
        self.active = True

    def end(self):
        self.active = False
        return dict(self.counts)


def distribution(samples):
    ordered = sorted(samples)
    return dict(
        n=len(ordered),
        min=ordered[0],
        median=statistics.median(ordered),
        p95=ordered[math.ceil(0.95 * len(ordered)) - 1],
        max=ordered[-1],
        stdev=statistics.stdev(ordered) if len(ordered) > 1 else 0,
    )


def run(n, out):
    out.mkdir(parents=True, exist_ok=True)
    report = dict(
        n=n,
        hot_ledger_rows=105,
        d=dict(unchanged=0, card=1, cash=1),
        seed=662602,
        warmups=3,
        measurements=20,
        phases=[],
        status="RUNNING",
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    write(out / f"{n}.json", report)
    token = "synthetic-continuation-only"
    with RetentionSandbox() as db:
        with db.connect() as conn:
            seed(conn, n)
            conn.execute(
                "INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order,is_primary_income) VALUES (101,'2026-10-05','fixed-width-cash',-50,2,0)"
            )
            conn.execute(
                "INSERT INTO users(id,username,password_hash) VALUES (1,'synthetic-c','unused')"
            )
            conn.execute(
                "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')",
                (_hash_session_token(token),),
            )
        db.install()
        started = time.perf_counter_ns()
        db.bootstrap()
        report["cold_bootstrap_ns"] = time.perf_counter_ns() - started
        report["db_bytes_after_bootstrap"] = db.path.stat().st_size
        write(out / f"{n}.json", report)
        with db.connect() as conn:
            report["counts"] = {
                table: conn.execute("SELECT count(*) FROM " + table).fetchone()[0]
                for table in [
                    "ledger_entries",
                    "monthly_panels",
                    "cash_flows",
                    "app_settings",
                    "app_labels",
                    "sync_objects",
                ]
            }
            verify(conn)
        write(out / f"{n}.json", report)
        repo = RetentionRepository(
            db, clock=lambda: NOW, evaluation=lambda: Evaluation(date(2026, 10, 5), 540)
        )
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(repo),
                host="127.0.0.1",
                port=port,
                log_level="critical",
                access_log=False,
            )
        )
        worker = threading.Thread(
            target=server.run, kwargs={"sockets": [listener]}, daemon=True
        )
        worker.start()
        until = time.monotonic() + 30
        while not server.started and time.monotonic() < until:
            time.sleep(0.01)
        assert server.started
        headers = {"Authorization": "Bearer " + token}
        url = f"http://127.0.0.1:{port}/api/sync/v1/observations"
        try:
            with (
                httpx.Client(timeout=30) as client,
                Meter() as meter,
                patch(
                    "app.services.judgment.common._MESSAGE_RANDOM.randrange",
                    return_value=0,
                ),
            ):
                base = None
                for phase in ["unchanged", "card", "cash"]:
                    samples = []
                    for trial in range(23):
                        meter.begin()
                        t0 = time.perf_counter_ns()
                        generation_ns = 0
                        if phase != "unchanged":
                            tg = time.perf_counter_ns()
                            with db.connect() as conn:
                                conn.begin_capture()
                                writer = BoundedInputs(conn)
                                if phase == "card":
                                    writer.execute(
                                        "UPDATE ledger_entries SET amount_value=? WHERE id=1002",
                                        (1000 + trial % 2,),
                                    )
                                else:
                                    writer.execute(
                                        "UPDATE cash_flows SET amount_value=? WHERE id=101",
                                        (-50 - trial % 2,),
                                    )
                                # 실제 backend projection 경로를 포함한다.
                                actual = projections(writer)
                                conn.finalize()
                                conn.commit()
                            generation_ns = time.perf_counter_ns() - tg
                        payload = dict(
                            protocol=1,
                            request_id=str(uuid4()),
                            base=base,
                            inline_bytes=0,
                        )
                        th = time.perf_counter_ns()
                        response = client.post(url, headers=headers, json=payload)
                        http_ns = time.perf_counter_ns() - th
                        total_ns = time.perf_counter_ns() - t0
                        counts = meter.end()
                        assert response.status_code == 201, response.text
                        manifest = response.json()
                        if base and phase == "unchanged":
                            assert manifest["change_kind"] == "unchanged"
                            assert manifest["target"] == base
                        if trial == 0 and phase == "unchanged":
                            from t66e2_server import children

                            pending = [
                                manifest["target"][role]
                                for role in [
                                    "raw_ref",
                                    "index_ref",
                                    "hot_ref",
                                    "control_ref",
                                ]
                            ]
                            seen, kinds, byte_count = set(), Counter(), 0
                            with closing(sqlite3.connect(db.path)) as graph_db:
                                while pending:
                                    ref = pending.pop()
                                    if ref["hash"] in seen:
                                        continue
                                    body = graph_db.execute(
                                        "SELECT body FROM sync_objects WHERE hash=?",
                                        (ref["hash"],),
                                    ).fetchone()[0]
                                    obj = json.loads(body)
                                    assert len(body) == int(ref["bytes"])
                                    assert (
                                        hashlib.sha256(
                                            b"money-note.sync.v1/"
                                            + obj["kind"].encode()
                                            + b"\0"
                                            + body
                                        ).hexdigest()
                                        == ref["hash"]
                                    )
                                    seen.add(ref["hash"])
                                    kinds[obj["kind"]] += 1
                                    byte_count += len(body)
                                    pending.extend(children(obj))
                            report["independent_graph"] = dict(
                                objects=len(seen),
                                bytes=byte_count,
                                kinds=dict(kinds),
                                roots={
                                    k: manifest["target"][k]
                                    for k in [
                                        "raw_ref",
                                        "index_ref",
                                        "hot_ref",
                                        "control_ref",
                                    ]
                                },
                            )
                            write(out / f"{n}.json", report)
                        # Hot H/descriptor의 raw 크기를 따로 관찰한다. 전체 graph 순회가 아니다.
                        with closing(sqlite3.connect(db.path)) as oracle:
                            sizes = {
                                k: oracle.execute(
                                    "SELECT length(body) FROM sync_objects WHERE hash=?",
                                    (manifest["target"][k]["hash"],),
                                ).fetchone()[0]
                                for k in ["hot_ref", "control_ref"]
                            }
                        row = dict(
                            trial=trial,
                            total_ns=total_ns,
                            generation_ns=generation_ns,
                            http_ns=http_ns,
                            status=response.status_code,
                            change_kind=manifest["change_kind"],
                            http_entity_bytes=len(response.content),
                            http_header_field_bytes=sum(
                                len(k) + len(v) + 4
                                for k, v in response.headers.multi_items()
                            ),
                            h_object_sizes=sizes,
                            counters=counts,
                            sync_root=manifest["target"]["sync_root"],
                        )
                        if trial >= 3:
                            samples.append(row)
                        lease = manifest["observation_id"]
                        released = client.delete(url + "/" + lease, headers=headers)
                        assert released.status_code == 204
                        base = manifest["target"]
                        if trial == 22:
                            # 전체 oracle은 측정 밖에서 backend 금융 authority와 비교한다.
                            with db.connect() as conn:
                                if phase != "unchanged":
                                    conn.execute("BEGIN DEFERRED")
                                    assert projections(conn) == actual
                                    conn.rollback()
                            with db.connect() as conn:
                                plans = {
                                    sql: [
                                        r[3]
                                        for r in conn.execute(
                                            "EXPLAIN QUERY PLAN " + sql, params
                                        )
                                    ]
                                    for sql, params in meter.queries.items()
                                }
                    report["phases"].append(
                        dict(
                            phase=phase,
                            samples=samples,
                            distributions={
                                k: distribution([s[k] for s in samples])
                                for k in [
                                    "total_ns",
                                    "generation_ns",
                                    "http_ns",
                                    "http_entity_bytes",
                                ]
                            },
                            query_plans=plans,
                        )
                    )
                    write(out / f"{n}.json", report)
                with db.connect() as conn:
                    verify(conn)
                # 실제 backend full bundle의 오프라인 압축 평가다.
                from app.services.authoritative_state import (
                    _construct,
                    _prepare,
                    BundleCredential,
                )

                with db.connect() as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    with (
                        patch(
                            "app.services.authoritative_state.CURRENT_SCHEMA_VERSION",
                            conn.execute("PRAGMA user_version").fetchone()[0],
                        ),
                        patch(
                            "app.services.authoritative_state._validate_revision_triggers"
                        ),
                        patch(
                            "app.services.authoritative_state.app_today",
                            return_value=date(2026, 10, 5),
                        ),
                    ):
                        bundle, _, _ = _construct(
                            conn, BundleCredential(_hash_session_token(token), 1)
                        )
                        raw = bytes(_prepare(bundle).body)
                    conn.rollback()
                compressed = {}
                for name, encode, decode in [
                    (
                        "gzip6",
                        lambda v: gzip.compress(v, compresslevel=6, mtime=0),
                        gzip.decompress,
                    ),
                    (
                        "brotli4",
                        lambda v: brotli.compress(v, 4),
                        lambda v: brotli.decompress(v, len(raw)),
                    ),
                ]:
                    times, output = [], None
                    for _ in range(23):
                        t = time.perf_counter_ns()
                        output = encode(raw)
                        times.append(time.perf_counter_ns() - t)
                        assert decode(output) == raw
                    compressed[name] = dict(
                        bytes=len(output),
                        ratio=len(output) / len(raw),
                        latency_ns=distribution(times[3:]),
                        samples_ns=times[3:],
                    )
                report["compression"] = dict(
                    boundary="offline actual backend full authoritative bundle bytes; no wire Content-Encoding",
                    raw_bytes=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest(),
                    algorithms=compressed,
                )
                report["max_rss_kib"] = resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss
                report["db_files"] = {
                    s or "main": Path(str(db.path) + s).stat().st_size
                    if Path(str(db.path) + s).exists()
                    else 0
                    for s in ["", "-wal", "-shm"]
                }
                report["status"] = "PASS"
                write(out / f"{n}.json", report)
        finally:
            server.should_exit = True
            worker.join(30)
            assert not worker.is_alive()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--n", type=int, choices=[1000, 5000, 10000, 50000, 100000], required=True
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (12 * 1024**3, 12 * 1024**3))
    try:
        run(args.n, args.out)
        print(json.dumps(dict(n=args.n, status="PASS")))
    except BaseException as exc:
        write(
            args.out / f"{args.n}-error.json",
            dict(type=type(exc).__name__, message=str(exc)),
        )
        raise

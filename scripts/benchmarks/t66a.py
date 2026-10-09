"""Isolated T6.6A characterization; never imported by product startup.

Run with the repository development venv. Output must be outside the checkout.
Only synthetic freshly migrated DBs are used. No existing DB is accepted.
"""

import argparse
from contextlib import ExitStack
import csv
import ctypes
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import random
import resource
import shutil
import sqlite3
import socket
import socketserver
import sys
import subprocess
import threading
import time
from unittest.mock import patch
import zlib

from payload_bytes import Brotli, JsonBytes, accepts_gzip, gzip_bytes, partition, stats

REPO = Path(__file__).resolve().parents[2]
PARAMETERS = {"seed": 1234, "evaluation_date": "2026-10-05", "timezone_offset_minutes": 540,
              "timestamp": "2026-10-05 12:00:00", "current_added_rows": 100,
              "history_date": "2026-07-03", "ledger_targets": [376, 1000, 5000, 10000],
              "confirmed_sources": 600, "bundle_version": 1, "snapshot_version": 7}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def measure(fn, warmups, samples):
    result = []
    output = None
    for i in range(warmups + samples):
        wall, cpu = time.perf_counter(), time.process_time()
        output = fn()
        row = {"wall_ms": (time.perf_counter() - wall) * 1000,
               "cpu_ms": (time.process_time() - cpu) * 1000}
        if i >= warmups:
            result.append(row)
    return output, {"warmups": warmups, "samples": result,
                    "wall_ms": stats([r["wall_ms"] for r in result]),
                    "cpu_ms": stats([r["cpu_ms"] for r in result])}


def backend_imports(output):
    # Never inherit a production DB/API/credential configuration.
    for key in tuple(os.environ):
        if key.startswith("MONEY_NOTE_"):
            del os.environ[key]
    os.environ.update(MONEY_NOTE_DB_PATH=str(output / "unused-synthetic.sqlite3"),
                      MONEY_NOTE_TODAY=PARAMETERS["evaluation_date"],
                      MONEY_NOTE_TIMEZONE_OFFSET_MINUTES="540")
    sys.path.insert(0, str(REPO / "backend"))
    from tests.test_authoritative_state import AuthoritativeStateTest, FrozenSnapshotClock
    return AuthoritativeStateTest, FrozenSnapshotClock


def seed(case, target, varied=False, heavy=False):
    from app.db import session

    if heavy:
        source_id, child_id = case.recurring()
        with session() as conn:
            columns = [r[1] for r in conn.execute("PRAGMA table_info(ledger_entries)")]
            source = dict(conn.execute("SELECT * FROM ledger_entries WHERE id=?", (source_id,)).fetchone())
            child = dict(conn.execute("SELECT * FROM ledger_entries WHERE id=?", (child_id,)).fetchone())
            for i in range(1, PARAMETERS["confirmed_sources"]):
                for row in ({**source, "id": 2*i+1, "title": f"Synthetic source {i}"},
                            {**child, "id": 2*i+2, "source_planned_entry_id": 2*i+1,
                             "payment_key": f"synthetic-child-{i}"}):
                    conn.execute(f"INSERT INTO ledger_entries({','.join(columns)}) "
                                 f"VALUES({','.join('?' for _ in columns)})", [row[k] for k in columns])
    else:
        # Reuse the real backend's rich fixture: discounts, utility override,
        # active toll group/partial payment, Claim/Family/fixed/frozen, cash,
        # and an archived confirmed actual with NULL mutable date.
        case.test_rich_financial_state_raw_typed_and_baseline_equivalence()
        rng = random.Random(PARAMETERS["seed"])
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET title='합성 😀 é' WHERE payment_key='ordinary'")
            existing = conn.execute("SELECT count(*) FROM ledger_entries").fetchone()[0]
            rows = []
            for i in range(target - existing):
                title, merchant = f"Independent history {i}", "Synthetic merchant"
                if varied:
                    # Higher entropy control: not a claim about typical user data.
                    title = "기록 " + rng.randbytes(24).hex() + " 😀"
                    merchant = "상점 " + rng.randbytes(12).hex()
                rows.append(("current" if i < 100 else "archive",
                             "2026-10-03" if i < 100 else "2026-07-03", title, merchant, i+10))
            conn.executemany("INSERT INTO ledger_entries(book_section,entry_kind,entry_date,title,usage_place,"
                             "amount_value,sort_order) VALUES(?,'expense',?,?,?,1234,?)", rows)
    # Fix synthetic timestamps (including both sides of recurring epochs) in
    # the DATABASE before the real endpoint computes its hashes/projections.
    # Stable raw timestamps make bodies reproducible; no response resealing.
    from app.services.snapshot import SNAPSHOT_TABLES
    with session() as conn:
        for table in SNAPSHOT_TABLES:
            columns = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            for column in ("created_at", "updated_at", "confirmed_at"):
                if column in columns:
                    conn.execute(f"UPDATE {table} SET {column}=? WHERE {column} IS NOT NULL",
                                 (PARAMETERS["timestamp"],))
        for row in conn.execute("SELECT id FROM ledger_entries WHERE source_planned_entry_id IS NOT NULL").fetchall():
            key = hashlib.sha256(f"synthetic-child-{row[0]}".encode()).hexdigest()[:32]
            conn.execute("UPDATE ledger_entries SET payment_key=? WHERE id=?", (key, row[0]))


def capture(case):
    from app.services.judgment.common import _MESSAGE_RANDOM
    _MESSAGE_RANDOM.seed(PARAMETERS["seed"])
    response = case.client.get("/api/authoritative-state")
    if response.status_code != 200:
        raise AssertionError((response.status_code, response.text[:300]))
    return response


def attribute(body, brotli):
    wire = json.loads(body)
    paths = [(key,) for key in ("bundle_version", "principal", "authority")]
    paths += [("state", key) for key in wire["state"]]
    paths += [("snapshot", "data", key) for key in wire["snapshot"]["data"]]
    paths += [("snapshot", "manifest", "tables", key) for key in wire["snapshot"]["manifest"]["tables"]]
    paths += [("snapshot", "manifest", key) for key in wire["snapshot"]["manifest"] if key != "tables"]
    paths += [("snapshot", key) for key in wire["snapshot"] if key not in ("data", "manifest")]
    tree, spans, overhead = partition(body, paths)
    rows = []
    for path, span in spans:
        raw = tree.slice(span)
        value = json.loads(raw)
        kind = "CONTROL"
        if path[:2] == ("snapshot", "data"):
            kind = "SHARED"  # Entire restoreable B, not freely discardable.
        elif path[0] == "state":
            kind = "HOT"
        rows.append({"category": ".".join(path), "count": len(value) if isinstance(value, (list, dict)) else 1,
                     "raw_bytes": len(raw), "percent": 100*len(raw)/len(body),
                     "gzip6_bytes": len(gzip_bytes(raw)),
                     "brotli4_bytes": len(brotli.compress(raw)) if brotli else None, "hot_cold": kind})
    cursor, fragments = 0, []
    for _, span in sorted(spans, key=lambda pair: pair[1].start):
        fragments.append(body[cursor:span.start])
        cursor = span.end
    fragments.append(body[cursor:])
    structure = b"".join(fragments)
    assert len(structure) == overhead
    rows.append({"category": "json_structure", "count": None, "raw_bytes": overhead,
                 "percent": 100*overhead/len(body), "gzip6_bytes": len(gzip_bytes(structure)),
                 "brotli4_bytes": len(brotli.compress(structure)) if brotli else None,
                 "hot_cold": "CONTROL"})
    assert sum(row["raw_bytes"] for row in rows) == len(body)
    tables = []
    for name, records in wire["snapshot"]["data"].items():
        payload = tree.get("snapshot", "data", name)
        manifest = tree.get("snapshot", "manifest", "tables", name)
        sizes = [r.size for r in payload.children]
        hash_bytes = tree.get("snapshot", "manifest", "tables", name, "sha256").size
        total = payload.size + manifest.size
        tables.append({"table": name, "rows": len(records), "row_payload_bytes": payload.size,
                       "row_objects_bytes": sum(sizes), "array_structure_bytes": payload.size-sum(sizes),
                       "manifest_nonhash_bytes": manifest.size-hash_bytes, "hash_bytes": hash_bytes,
                       "total_bytes": total, "bundle_percent": 100*total/len(body),
                       "snapshot_percent": 100*total/tree.get("snapshot").size,
                       "avg_object_bytes": sum(sizes)/len(sizes) if sizes else 0,
                       "row_sizes": stats(sizes) if sizes else None})
    # Separate, overlapping semantic view. Do NOT add this to the partition.
    raw_by_id = {r["id"]: r for r in wire["snapshot"]["data"]["ledger_entries"]}
    raw_spans = dict(zip([r["id"] for r in wire["snapshot"]["data"]["ledger_entries"]],
                         tree.get("snapshot", "data", "ledger_entries").children))
    duplicate = []
    for section in ("entries", "confirmed_planned_entries", "panels", "cash_flows"):
        raw_table = {"panels": "monthly_panels", "cash_flows": "cash_flows"}.get(section, "ledger_entries")
        raw_records = {r["id"]: r for r in wire["snapshot"]["data"][raw_table]}
        raw_nodes = dict(zip([r["id"] for r in wire["snapshot"]["data"][raw_table]],
                             tree.get("snapshot", "data", raw_table).children))
        match_count = token_bytes = identical_row_bytes = identical_tokens = 0
        for record, span in zip(wire["state"][section], tree.get("state", section).children):
            source = raw_records.get(record["id"])
            if source is None:
                continue
            match_count += 1
            for key in source.keys() & record.keys():
                if source[key] == record[key]:
                    # Original value token lengths only. Key/delimiter savings
                    # need a protocol design and are deliberately not claimed.
                    token_bytes += span.children[key].size
                if tree.slice(raw_nodes[record["id"]].children[key]) == tree.slice(span.children[key]):
                    identical_tokens += span.children[key].size
            if tree.slice(raw_nodes[record["id"]]) == tree.slice(span):
                identical_row_bytes += span.size
        duplicate.append({"projection": section, "same_id_records": match_count,
                          "equal_raw_value_token_bytes": token_bytes, "identical_value_token_bytes": identical_tokens,
                          "identical_row_bytes": identical_row_bytes})
    payment_ids = {r["entry_id"] for r in wire["snapshot"]["data"]["card_payment_batch_items"]}
    archived = [r for r in raw_by_id.values() if r["book_section"] == "archive"]
    cold = [r for r in archived if r["id"] not in payment_ids and r["source_planned_entry_id"] is None]
    archived_bytes = sum(raw_spans[r["id"]].size for r in archived)
    cold_bytes = sum(raw_spans[r["id"]].size for r in cold)
    ledger_span = tree.get("snapshot", "data", "ledger_entries")
    ledger_key_bytes = sum(row.key_bytes for row in ledger_span.children)
    ledger_value_bytes = sum(value.size for row in ledger_span.children for value in row.children.values())
    ledger_null_bytes = sum(value.size for row in ledger_span.children for value in row.children.values()
                            if tree.slice(value) == b"null")
    return {"partition": rows, "tables": sorted(tables, key=lambda row: -row["total_bytes"]),
            "snapshot_bytes": tree.get("snapshot").size, "state_bytes": tree.get("state").size,
            "archive_row_bytes": archived_bytes, "cold_candidate_row_bytes": cold_bytes,
            "cold_candidate_rows": len(cold), "overlap": duplicate,
            "ledger_representation": {"keys_bytes": ledger_key_bytes, "value_token_bytes": ledger_value_bytes,
                                      "null_bytes_within_values": ledger_null_bytes,
                                      "structural_bytes": ledger_span.size-ledger_key_bytes-ledger_value_bytes,
                                      "total_bytes": ledger_span.size}}


def compressions(body, brotli, samples):
    import gzip

    result = []
    codecs = [("gzip", level, lambda b, q=level: gzip_bytes(b, q), gzip.decompress) for level in (1, 6, 9)]
    if brotli:
        codecs += [("brotli", q, lambda b, q=q: brotli.compress(b, q),
                    lambda b: brotli.decompress(b, len(body))) for q in (4, 6, 9)]
    for name, setting, encode, decode in codecs:
        encoded, encoding = measure(lambda: encode(body), 3, samples)
        decoded, decoding = measure(lambda: decode(encoded), 3, samples)
        assert decoded == body
        result.append({"codec": name, "setting": setting, "raw_bytes": len(body), "bytes": len(encoded),
                       "ratio": len(encoded)/len(body), "reduction_percent": 100*(1-len(encoded)/len(body)),
                       "sha256": hashlib.sha256(decoded).hexdigest(), "encode": encoding, "decode": decoding})
    return result


def generate(output, quick=False):
    Case, Clock = backend_imports(output)
    from app.services import authoritative_state as service
    from app.services.snapshot import validate_reconciliation_snapshot, replace_reconciliation_snapshot
    from app.db import session
    try:
        brotli = Brotli()
    except RuntimeError:
        brotli = None
    all_results = {}
    for name, target, varied, heavy in [(str(n), n, False, False) for n in PARAMETERS["ledger_targets"]] + [
            ("heavy600", 1200, False, True), ("varied10000", 10000, True, False)]:
        case = Case()
        case.setUp()
        try:
            seed(case, target, varied, heavy)
            with patch("app.services.snapshot.datetime", Clock):
                response = capture(case)
                body = response.content
                (output / f"body-{name}.json").write_bytes(body)
                # Actual canonical Snapshot admission and real migrated DB
                # INSERT/relationship path, rolled back, never product data.
                wire = json.loads(body)
                validate_reconciliation_snapshot(wire["snapshot"])
                with session() as conn:
                    conn.execute("SAVEPOINT diagnostic_restore")
                    replace_reconciliation_snapshot(conn, wire["snapshot"]["data"])
                    assert conn.execute("SELECT count(*) FROM ledger_entries").fetchone()[0] == target
                    conn.execute("ROLLBACK TO diagnostic_restore")
                    conn.execute("RELEASE diagnostic_restore")
                assert capture(case).content == body
                from tests.test_authoritative_state import legacy_acquisition
                from app.services.judgment.common import _MESSAGE_RANDOM
                legacy_requests = []
                original_get = case.client.get
                def legacy_get(path, **kwargs):
                    result = original_get(path, **kwargs)
                    legacy_requests.append({"path": path, "bytes": len(result.content)})
                    return result
                _MESSAGE_RANDOM.seed(PARAMETERS["seed"])
                with patch.object(case.client, "get", legacy_get):
                    old = legacy_acquisition(case.client)
                assert old["B0"] == old["B1"]
                assert old["B1"]["snapshot"] == wire["snapshot"]
                assert {k: v for k, v in old.items() if k not in ("B0", "B1")} == wire["state"]
                stages = []
                def wrap(label, fn):
                    def call(*args, **kwargs):
                        started = time.perf_counter()
                        try:
                            return fn(*args, **kwargs)
                        finally:
                            stages.append({"stage": label, "ms": (time.perf_counter()-started)*1000})
                    return call
                count = 2 if quick else 20
                with ExitStack() as stack:
                    for label in ("_construct", "_prepare", "_terminal_guard", "export_snapshot_from_connection"):
                        stack.enter_context(patch.object(service, label, wrap(label, getattr(service, label))))
                    stack.enter_context(patch.object(service.JSONResponse, "render", wrap("json_render", service.JSONResponse.render)))
                    _, timings = measure(lambda: capture(case), 3, count)
                # Stage samples are aligned, discard warmups. Snapshot is
                # INCLUDED in construct, never sum inclusive nested categories.
                stages = stages[3*5:]
                grouped = {label: stats([r["ms"] for r in stages if r["stage"] == label])
                           for label in {r["stage"] for r in stages}}
                data = wire["snapshot"]["data"]
                ledger = data["ledger_entries"]
                description = {"ledger_rows": len(ledger),
                               "archive_rows": sum(r["book_section"] == "archive" for r in ledger),
                               "current_rows": sum(r["book_section"] == "current" for r in ledger),
                               "confirmed_sources": len(wire["state"]["confirmed_planned_entries"]),
                               "typed_entries": len(wire["state"]["entries"]),
                               "policy_binding_count": sum(len(v) for v in wire["snapshot"]["card_charge_policy"]["cards"].values()),
                               "raw_bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                               "status": response.status_code, "headers": dict(response.headers),
                               "backend": timings, "backend_stages_inclusive": grouped,
                               "backend_stage_raw": stages,
                               "legacy_requests": legacy_requests,
                               "legacy_aggregate_body_bytes": sum(r["bytes"] for r in legacy_requests),
                               "attribution": attribute(body, brotli),
                               "compression": compressions(body, brotli, count),
                               "snapshot_canonical_and_migrated_restore": "PASS"}
                all_results[name] = description
                write_json(output / "measurements.json", all_results)
                print(f"captured {name}: {len(body)} bytes, canonical restore PASS", flush=True)
                if name == "10000":
                    receipt = case.client.post("/api/entries", json={
                        "book_section": "current", "entry_kind": "expense", "title": "Synthetic delta",
                        "sort_order": 20000, "usage_place": "Synthetic delta merchant",
                        "usage_item": "One new card expense", "amount_value": 1234,
                        "entry_date": "2026-10-05", "discount_enabled": True})
                    assert receipt.status_code == 200, receipt.text[:200]
                    after = capture(case).content
                    (output / "delta-after-10000.json").write_bytes(after)
                    after_wire = json.loads(after)
                    changes = {}
                    for table, before_rows in wire["snapshot"]["data"].items():
                        after_rows = after_wire["snapshot"]["data"][table]
                        if before_rows != after_rows:
                            changes[table] = {"before_count": len(before_rows), "after_count": len(after_rows)}
                    write_json(output / "delta.json", {"before_revision": wire["authority"]["state_revision"],
                               "after_revision": after_wire["authority"]["state_revision"],
                               "changed_tables": changes,
                               "changed_projections": [k for k in wire["state"] if wire["state"][k] != after_wire["state"][k]],
                               "before_bytes": len(body), "after_bytes": len(after),
                               "mutation_http_status": receipt.status_code})
        finally:
            case.tearDown()
    environment = {"starting_commit": "597a936d8fc53f35c693705c320223686a657f0e", "host_only": True,
                   "os": platform.platform(), "python": sys.version, "parameters": PARAMETERS,
                   "sqlite": sqlite3.sqlite_version, "zlib": zlib.ZLIB_VERSION,
                   "cpu": next(line.strip() for line in Path("/proc/cpuinfo").read_text().splitlines() if line.startswith("model name")),
                   "ram": Path("/proc/meminfo").read_text().splitlines()[0],
                   "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   "memory_scope": "whole Python generator including attribution, NOT per-codec peak",
                   "brotli_library": ctypes.util.find_library("brotlienc"), "brotli_encoder_version":
                   brotli.enc.BrotliEncoderVersion() if brotli else None,
                   "samples": 2 if quick else 20, "warmups": 3}
    write_json(output / "environment.json", environment)


class LocalHandler(socketserver.StreamRequestHandler):
    """Benchmark-only HTTP/1.1 wrapper: original ASGI app or frozen bytes.

    Headers are read/written as exact bytes; no reserialization of response
    bodies. Persistent connections and TCP_NODELAY. No TLS, no proxy claims.
    """

    def handle(self):
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        while line := self.rfile.readline():
            request_head = line
            headers = {}
            while (line := self.rfile.readline()) != b"\r\n":
                if not line:
                    return
                request_head += line
                key, value = line.decode("latin1").strip().split(":", 1)
                headers[key.lower()] = value.strip()
            request_head += b"\r\n"
            method, path, _ = request_head.split(b"\r\n", 1)[0].decode().split()
            if method != "GET":
                return
            started = time.perf_counter()
            encoding, compression_ms = None, 0
            name = path.split("/")[2]
            if path.startswith("/actual/"):
                # Real FastAPI response; this wrapper adds no compression.
                response = self.server.case.client.get("/api/authoritative-state", headers={
                    "Accept-Encoding": headers.get("accept-encoding", "identity")})
                body, status = response.content, response.status_code
                extra = [(k, v) for k, v in response.headers.items() if k not in ("content-length", "content-type")]
            else:
                body = (self.server.output / f"body-{name}.json").read_bytes()
                status, extra = 200, []
                if path.startswith("/gzip/") and accepts_gzip(headers.get("accept-encoding", "")):
                    encoding = "gzip"
                    encode_at = time.perf_counter()
                    body = gzip_bytes(body)
                    compression_ms = (time.perf_counter()-encode_at)*1000
                    extra = [("Content-Encoding", "gzip"), ("Vary", "Accept-Encoding")]
            response_head = (f"HTTP/1.1 {status} OK\r\nContent-Type: application/json\r\n"
                             f"Content-Length: {len(body)}\r\n" +
                             "".join(f"{k}: {v}\r\n" for k, v in extra) + "\r\n").encode("latin1")
            self.wfile.write(response_head)
            self.wfile.write(body)
            self.wfile.flush()
            record = {"method": method, "path": path, "status": status,
                      "request_header_bytes": len(request_head), "request_entity_bytes": 0,
                      "response_header_bytes": len(response_head), "response_entity_bytes": len(body),
                      "content_encoding": encoding, "accept_encoding": headers.get("accept-encoding"),
                      "content_length": len(body), "transfer_encoding": None, "http_version": "HTTP/1.1",
                      "connection": self.client_address[1], "compression_ms": compression_ms,
                      "handler_ms": (time.perf_counter()-started)*1000,
                      "tls": False, "response_sha256_encoded": hashlib.sha256(body).hexdigest()}
            with self.server.lock:
                with (self.server.output / "http.ndjson").open("a") as file:
                    file.write(json.dumps(record) + "\n")


def serve(output):
    Case, Clock = backend_imports(output)
    case = Case()
    case.setUp()
    try:
        seed(case, 376)
        with patch("app.services.snapshot.datetime", Clock):
            server = socketserver.ThreadingTCPServer(("127.0.0.1", 18081), LocalHandler)
            server.daemon_threads = True
            server.case, server.output, server.lock = case, output, threading.Lock()
            print("local-only HTTP diagnostic ready: 127.0.0.1:18081", flush=True)
            server.serve_forever()
    finally:
        case.tearDown()


def export(output, destination):
    """Compact tracked aggregate files; bulk bodies/raw samples stay in /tmp."""
    results = json.loads((output / "measurements.json").read_text())
    try:
        brotli = Brotli()
    except RuntimeError:
        brotli = None
    # Re-run exact accounting only, outside all timed measurements. This also
    # lets diagnostic attribution fixes be tested without changing frozen bytes.
    for dataset, result in results.items():
        result["attribution"] = attribute((output / f"body-{dataset}.json").read_bytes(), brotli)
    destination.mkdir(parents=True, exist_ok=True)
    compact = {}
    attribution, compression, samples = [], [], []
    for dataset, result in results.items():
        compact[dataset] = {k: v for k, v in result.items() if k not in ("backend", "compression", "backend_stage_raw")}
        compact[dataset]["backend"] = {k: v for k, v in result["backend"].items() if k != "samples"}
        for row in result["attribution"]["partition"]:
            category = row["category"]
            growth = "프로토콜/schema 고정 시 대체로 일정; 숫자 자릿수·정책 이력은 변동"
            if category == "snapshot.data.ledger_entries":
                growth = "전체 원장 행 수·행별 문자열 길이에 비례"
            elif category.startswith("snapshot.data."):
                growth = "해당 보존 테이블 행 수에 비례"
            elif category.startswith("state."):
                growth = "현재/미마감 행·active batch·설정/큐 크기에 의존; 역사 N의 직접 상한 아님"
            attribution.append({"dataset": dataset, **row, "growth_behavior": growth})
        for index, row in enumerate(result["backend"]["samples"]):
            samples.append({"dataset": dataset, "domain": "backend", "metric": "route",
                            "sample": index, **row})
        for stage in result["backend_stages_inclusive"]:
            observations = [r["ms"] for r in result["backend_stage_raw"] if r["stage"] == stage]
            assert len(observations) == result["backend"]["wall_ms"]["n"]
            for index, ms in enumerate(observations):
                samples.append({"dataset": dataset, "domain": "backend_inclusive", "metric": stage,
                                "sample": index, "wall_ms": ms, "cpu_ms": None})
        for row in result["compression"]:
            compression.append({"dataset": dataset, **{k: row[k] for k in ("codec", "setting", "raw_bytes", "bytes", "ratio", "reduction_percent")},
                                **{f"{stage}_{unit}_{stat}": row[stage][unit][stat]
                                   for stage in ("encode", "decode") for unit in ("wall_ms", "cpu_ms")
                                   for stat in ("median", "p95", "min", "max", "stdev", "n")}})
            for stage in ("encode", "decode"):
                for index, observation in enumerate(row[stage]["samples"]):
                    samples.append({"dataset": dataset, "domain": "compression",
                                    "metric": f"{row['codec']}-{row['setting']}-{stage}", "sample": index, **observation})
    write_json(destination / "attribution.json", compact)
    environment = json.loads((output / "environment.json").read_text())
    environment.update(sqlite=sqlite3.sqlite_version, zlib=zlib.ZLIB_VERSION)
    environment["runtime_packages"] = {name: version(name) for name in
                                       ("fastapi", "starlette", "pydantic", "httpx", "uvicorn")}
    if shutil.which("flutter"):
        framework = subprocess.run(["flutter", "--version", "--machine"], capture_output=True,
                                   text=True, check=True, timeout=20)
        environment["flutter"] = json.loads(framework.stdout)
    else:
        environment["flutter"] = "not available in export environment"
    write_json(destination / "environment.json", environment)
    for row in json.loads((output / "client-raw.json").read_text()):
        for key, ms in {**row["stages"], **{k: v for k, v in row.items() if k.endswith("_ms")}}.items():
            samples.append({"dataset": row["dataset"], "domain": "dart_host", "metric": key,
                            "sample": row["sample"], "wall_ms": ms, "cpu_ms": None})
    for row in json.loads((output / "client-http-raw.json").read_text()):
        if "sample" in row:
            samples.append({"dataset": row["dataset"], "domain": "dart_http", "metric": row["mode"],
                            "sample": row["sample"], "wall_ms": row["http_body_available_ms"], "cpu_ms": None})
        else:
            for index, ms in enumerate(row["samples_ms"]):
                samples.append({"dataset": row["dataset"], "domain": "dart_http", "metric": row["mode"],
                                "sample": index, "wall_ms": ms, "cpu_ms": None})
    for index, line in enumerate((output / "http.ndjson").read_text().splitlines()):
        row = json.loads(line)
        for metric in ("handler_ms", "compression_ms"):
            samples.append({"dataset": row["path"].split("/")[2], "domain": "http_including_warmups",
                            "metric": row["path"].split("/")[1]+"_"+metric,
                            "sample": index, "wall_ms": row[metric], "cpu_ms": None})
    for filename in ("client-summary.json", "http-summary.json", "bandwidth-model.json", "growth.json", "delta.json", "dart-gzip-summary.json"):
        write_json(destination / filename, json.loads((output / filename).read_text()))
    for filename in ("codec-memory.json", "specimen-comparison.json", "large-probe.json", "native-http.json", "reference-latency.json"):
        if (output / filename).exists():
            write_json(destination / filename, json.loads((output / filename).read_text()))
    for name, rows in (("attribution", attribution), ("compression", compression), ("samples", samples)):
        with (destination / f"{name}.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def codec_memory(output):
    """Fresh child per codec: coarse RSS high-watermark, NOT allocator tracing."""
    results = []
    try:
        Brotli()
        have_brotli = True
    except RuntimeError:
        have_brotli = False
    for codec, setting in (("gzip", 1), ("gzip", 6), ("gzip", 9), ("brotli", 4), ("brotli", 6), ("brotli", 9)):
        if codec == "brotli" and not have_brotli:
            continue
        script = (
            "import json,resource; from pathlib import Path; from payload_bytes import Brotli,gzip_bytes; "
            f"body=Path({str(output / 'body-10000.json')!r}).read_bytes(); "
            "baseline=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss; "
            f"encoded={'gzip_bytes(body,' + str(setting) + ')' if codec == 'gzip' else 'Brotli().compress(body,' + str(setting) + ')'}; "
            "print(json.dumps({'baseline_rss_kib':baseline,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'encoded_bytes':len(encoded)}))"
        )
        process = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).parent,
                                 text=True, capture_output=True, check=True)
        results.append({"dataset": "10000", "codec": codec, "setting": setting,
                        **json.loads(process.stdout), "samples": 1,
                        "scope": "fresh child process compression RSS high-water, coarse KiB"})
    write_json(output / "codec-memory.json", results)


def large_probe(output):
    """Optional one-shot 50k, 2 GiB address-space / 90 CPU-second ceilings.

    Not part of the repeated primary measurements or T6.9 acceptance.
    """
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    Case, Clock = backend_imports(output)
    case = Case()
    case.setUp()
    try:
        seed(case, 50000)
        with patch("app.services.snapshot.datetime", Clock):
            started = time.perf_counter()
            response = capture(case)
            route_ms = (time.perf_counter()-started)*1000
        body = response.content
        (output / "body-50000.json").write_bytes(body)
        tree = JsonBytes(body)
        brotli = None
        try:
            brotli = Brotli()
        except RuntimeError:
            pass
        codecs = compressions(body, brotli, 1)
        write_json(output / "large-probe.json", {
            "ledger_rows": 50000, "raw_bytes": len(body), "snapshot_bytes": tree.get("snapshot").size,
            "state_bytes": tree.get("state").size, "route_ms": route_ms, "route_samples": 1,
            "sha256": hashlib.sha256(body).hexdigest(), "compression": codecs,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "limits": {"address_space_bytes": 2 * 1024**3, "cpu_seconds": 90},
            "mobile_pipeline": "NOT RUN", "purpose": "optional characterization, NOT scalability approval"})
        print(f"50k optional: {len(body)} bytes, route {route_ms:.1f} ms", flush=True)
    finally:
        case.tearDown()


def compare_specimens(output, specimens):
    """Optional retained SYNTHETIC specimens; never read production resources."""
    result = []
    for path in specimens:
        path = path.resolve()
        if not path.is_relative_to(Path("/tmp")):
            raise ValueError("only explicitly selected temporary synthetic specimens are permitted")
        body = path.read_bytes()
        wire = json.loads(body)
        tree = JsonBytes(body)
        ledger = wire["snapshot"]["data"]["ledger_entries"]
        result.append({"path": str(path), "raw_bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                       "bundle_version": wire["bundle_version"], "snapshot_version": wire["snapshot"]["schema_version"],
                       "ledger_rows": len(ledger), "current_rows": sum(r["book_section"] == "current" for r in ledger),
                       "archive_rows": sum(r["book_section"] == "archive" for r in ledger),
                       "typed_entries": len(wire["state"]["entries"]),
                       "snapshot_bytes": tree.get("snapshot").size, "typed_state_bytes": tree.get("state").size,
                       "typed_entry_bytes": tree.get("state", "entries").size,
                       "revision": wire["authority"]["state_revision"],
                       "top_level_keys": list(wire), "state_keys": list(wire["state"]),
                       "snapshot_table_counts": {k: len(v) for k, v in wire["snapshot"]["data"].items()}})
    write_json(output / "specimen-comparison.json", result)


def native_http(output):
    """Unmodified FastAPI on actual Uvicorn, raw HTTP/1.1 observation.

    Port 18081 only; fails rather than stopping an existing local service.
    Fresh migrated synthetic DB; lifespan off because the fixture initialized
    it explicitly. No proxy/TLS or production credentials.
    """
    import uvicorn

    Case, Clock = backend_imports(output)
    from app.main import app
    from app.services.judgment.common import _MESSAGE_RANDOM
    case = Case()
    case.setUp()
    server = None
    try:
        seed(case, 376)
        # Prebind so a collision is a controlled failure, not a daemon exception.
        listener = socket.socket()
        listener.bind(("127.0.0.1", 18081))
        listener.listen()
        with listener, patch("app.services.snapshot.datetime", Clock):
            server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=18081,
                                                   lifespan="off", access_log=False, log_level="error"))
            worker = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
            worker.start()
            deadline = time.monotonic() + 10
            while not server.started:
                if time.monotonic() > deadline:
                    raise TimeoutError("isolated Uvicorn did not start")
                threading.Event().wait(.01)
            records = []
            for _ in range(3):
                _MESSAGE_RANDOM.seed(PARAMETERS["seed"])
                request = ("GET /api/authoritative-state HTTP/1.1\r\nHost: 127.0.0.1:18081\r\n"
                           "Accept-Encoding: gzip\r\nConnection: close\r\n"
                           f"Authorization: Bearer {case.token}\r\n\r\n").encode("ascii")
                with socket.create_connection(("127.0.0.1", 18081), timeout=15) as connection:
                    connection.sendall(request)
                    response = bytearray()
                    while chunk := connection.recv(65536):
                        response.extend(chunk)
                head, body = bytes(response).split(b"\r\n\r\n", 1)
                head += b"\r\n\r\n"
                headers = dict(line.decode("latin1").split(": ", 1) for line in head.split(b"\r\n")[1:-2])
                assert head.startswith(b"HTTP/1.1 200")
                assert int(headers["content-length"]) == len(body)
                assert "content-encoding" not in headers
                assert body == (output / "body-376.json").read_bytes()
                records.append({"request_header_bytes": len(request), "request_entity_bytes": 0,
                                "response_header_bytes": len(head), "response_entity_bytes": len(body),
                                "response_http_bytes": len(response), "headers": headers,
                                "body_sha256": hashlib.sha256(body).hexdigest(), "http_version": "HTTP/1.1",
                                "tls": False, "connection_reuse": False})
            write_json(output / "native-http.json", records)
    finally:
        if server:
            server.should_exit = True
            worker.join(timeout=10)
        case.tearDown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "serve", "export", "memory", "large", "compare", "native"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--destination", type=Path, default=REPO / "docs/benchmarks/t66a")
    parser.add_argument("--quick", action="store_true", help="smoke only, never final statistics")
    parser.add_argument("--specimen", action="append", type=Path, default=[], help="explicit retained synthetic /tmp body")
    args = parser.parse_args()
    resolved = args.output.resolve()
    if not resolved.is_relative_to(Path("/tmp")):
        parser.error("synthetic output must be under /tmp")
    resolved.mkdir(parents=True, exist_ok=True)
    if args.mode == "generate":
        generate(resolved, args.quick)
    elif args.mode == "serve":
        serve(resolved)
    elif args.mode == "memory":
        codec_memory(resolved)
    elif args.mode == "large":
        large_probe(resolved)
    elif args.mode == "compare":
        compare_specimens(resolved, args.specimen)
    elif args.mode == "native":
        native_http(resolved)
    else:
        export(resolved, args.destination)


if __name__ == "__main__":
    main()

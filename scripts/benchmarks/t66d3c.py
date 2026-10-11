"""Owned synthetic D3b/D3c matched hot-path + explicit maintenance costs.

No production path/env, no startup, no live socket. O(N) seed/bootstrap/oracles
are outside hot timings. Logical bytes are not physical SQLite file shrinkage.
"""

import argparse
from collections import Counter
from contextlib import ExitStack
from datetime import date
import json
import math
import os
from pathlib import Path
import platform
import resource
import sqlite3
import statistics
import sys
from time import perf_counter
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
sys.path.insert(0, str(ROOT/'scripts/benchmarks'))
from t66d2b import check_output  # noqa: E402
from t66d2b_writers import seed, command, prepare_next, CountedCursor, historical_scans  # noqa: E402


def stats(values):
    ordered = sorted(values)
    return dict(median=statistics.median(ordered), p95=ordered[math.ceil(.95*len(ordered))-1])


def run(sizes, warmups, samples):
    from fastapi.testclient import TestClient
    from app.auth import _hash_session_token
    from isolated_sync.http import create_app
    from isolated_sync.inputs import BoundedInputs
    from isolated_sync.observation import ObservationRepository, Evaluation
    from isolated_sync.observation_schema import ObservationSandbox, ObservationConnection
    from isolated_sync.retention import Collector, RetentionRepository
    from isolated_sync.retention_schema import RetentionSandbox
    from tests.test_isolated_sync_observation import NOW
    from tests.test_isolated_sync_transfer import graph
    token = 'synthetic-d3c-benchmark-only'
    headers = {'Authorization': 'Bearer '+token}
    url = '/api/sync/v1/observations'
    report = dict(profile='isolated-d3c/1', environment=dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version,
        platform=platform.platform(), cpu=platform.processor(), logical_cpus=os.cpu_count()), cells=[], maintenance=[])
    for size in sizes:
        for name, sandbox, repository in (('d3b_profile', ObservationSandbox, ObservationRepository),
                                          ('d3c_profile', RetentionSandbox, RetentionRepository)):
            with ExitStack() as stack:
                db = stack.enter_context(sandbox())
                with db.connect() as conn:
                    seed(conn, size)
                    conn.execute("INSERT INTO users(id,username,password_hash) VALUES (1,'synthetic','synthetic')")
                    conn.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?,'2026-12-31T00:00:00Z')", (_hash_session_token(token),))
                db.install()
                db.bootstrap()
                repo = repository(db, clock=lambda: NOW, evaluation=lambda: Evaluation(date(2026, 10, 5), 540))
                diagnostics = []
                c = stack.enter_context(TestClient(create_app(repo, metrics=diagnostics.append)))
                nonce = dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)
                manifest = c.post(url, json=nonce, headers=headers).json()
                objects = graph(db, manifest)
                leaf = next(v for v in objects.values() if v[3]['kind'] == 'snapshot-leaf' and v[3]['table'] == 'ledger_entries')
                endpoint = url+'/'+manifest['observation_id']+'/objects'
                for workload in ('no_change_observation', 'manifest_retry', 'root', 'leaf', 'card', 'cash'):
                    trials, plans, unexpected = [], {}, {}
                    for trial in range(-warmups, samples):
                        # Keep one new observation hot; explicit release is outside timing.
                        body = dict(nonce, request_id=str(uuid4())) if workload == 'no_change_observation' else nonce
                        rows, vm, calls, queries = [0], [0], Counter(), {}
                        original = ObservationConnection.execute
                        def execute(conn, sql, parameters=()):
                            calls[sql.lstrip().split()[0].upper()] += 1
                            if sql.lstrip().upper().startswith('SELECT'):
                                queries[sql] = parameters
                            return CountedCursor(original(conn, sql, parameters), rows)
                        connect = db.connect
                        def counted():
                            conn = connect()
                            def progress():
                                vm[0] += 100
                                return 0
                            conn.set_progress_handler(progress, 100)
                            return conn
                        diagnostics.clear()
                        stage = {}
                        with patch.object(ObservationConnection, 'execute', execute), patch.object(db, 'connect', counted):
                            started = perf_counter()
                            if workload in ('card', 'cash'):
                                with db.connect() as conn:
                                    conn.begin_capture()
                                    at = perf_counter()
                                    result = command(workload, BoundedInputs(conn), trial+warmups)
                                    stage['writer_ms'] = (perf_counter()-at)*1000
                                    at = perf_counter()
                                    metrics = conn.finalize()
                                    stage['finalize_ms'] = (perf_counter()-at)*1000
                                    at = perf_counter()
                                    conn.commit()
                                    stage.update(commit_ms=(perf_counter()-at)*1000, changed_objects=metrics['object_writes'])
                                output = None
                            elif workload in ('no_change_observation', 'manifest_retry'):
                                output = c.post(url, json=body, headers=headers)
                            else:
                                path = [manifest['target']['raw_ref']['hash']] if workload == 'root' else leaf[1]
                                ref = objects[path[-1]][0]
                                value = dict(protocol=1, request_id=str(uuid4()), items=[dict(path=path, offset='0', length=int(ref['bytes']))])
                                output = c.post(endpoint, json=value, headers=headers)
                            elapsed = (perf_counter()-started)*1000
                        if output is not None and output.status_code not in (200, 201):
                            raise RuntimeError('synthetic HTTP cell failed')
                        with db.connect() as conn:
                            for sql, parameters in queries.items():
                                if sql not in plans:
                                    plan = [r[3] for r in conn.execute('EXPLAIN QUERY PLAN '+sql, parameters)]
                                    plans[sql] = plan
                                    bad = [p for p in historical_scans(sql, plan) if not any(t in p for t in (
                                        'sync_observation', 'sync_retention_profile', 'sync_gc_fence'))]
                                    if bad:
                                        unexpected[sql] = bad
                        if trial >= 0:
                            info = dict(diagnostics[0]) if diagnostics else {}
                            info.pop('operation', None)
                            trials.append(dict(info, **stage, total_ms=elapsed, materialized_rows=rows[0], sql_statements=sum(calls.values()),
                                               vm_steps_lower_bound=vm[0], wire_bytes=len(output.content) if output else 0))
                        if workload == 'no_change_observation':
                            identity = output.json()['observation_id']
                            # Baseline has no D3c API: mark retired under its audited metadata contract.
                            if name == 'd3c_profile':
                                from app.services.authoritative_state import BundleCredential
                                cred = BundleCredential(_hash_session_token(token), 1)
                                repo.release(identity, cred, guard=lambda: cred)
                                repo.maintain()
                            else:
                                with db.connect() as conn, conn._metadata():
                                    conn.execute("UPDATE sync_observations SET status='retired' WHERE id=?", (identity,))
                        if workload == 'cash':
                            with db.connect() as conn:
                                prepare_next('cash', result, conn, None)
                    report['cells'].append(dict(profile=name, ledger_rows=size, workload=workload, warmups=warmups, measurements=samples,
                        stats={key: stats([v[key] for v in trials]) for key in trials[0]}, unexpected_history_scans=unexpected,
                        query_plans=plans, samples=trials))
                    if unexpected:
                        raise RuntimeError('historical SQL scan detected: '+json.dumps(unexpected))
                if name == 'd3c_profile':
                    gc = Collector(repo)
                    with db.connect() as conn:
                        before = dict(objects=conn.execute('SELECT count(*) FROM sync_objects').fetchone()[0],
                            bytes=conn.execute('SELECT sum(length(body)) FROM sync_objects').fetchone()[0],
                            metadata=conn.execute('SELECT count(*) FROM sync_observations').fetchone()[0])
                    start = perf_counter()
                    dry = gc.collect()
                    dry_ms = (perf_counter()-start)*1000
                    start = perf_counter()
                    actual = gc.collect(apply=True, batch=1024, max_batches=64)
                    total_ms = (perf_counter()-start)*1000
                    second = gc.collect(apply=True)
                    report['maintenance'].append(dict(ledger_rows=size, before=before, dry=dry, dry_ms=dry_ms, actual=actual,
                        total_ms=total_ms, second=second, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sizes', type=int, nargs='+', default=[376, 1000, 5000, 10000])
    parser.add_argument('--warmups', type=int, default=3)
    parser.add_argument('--samples', type=int, default=20)
    args = parser.parse_args()
    check_output(args.output)
    if not 1 <= args.warmups <= 5 or not 1 <= args.samples <= 30 or not args.sizes or any(n not in (376, 1000, 5000, 10000) for n in args.sizes):
        raise SystemExit('bounded synthetic configurations only')
    resource.setrlimit(resource.RLIMIT_CPU, (2400, 2400))
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    report = run(args.sizes, args.warmups, args.samples)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, separators=(',', ':'))
    print(json.dumps(dict(cells=len(report['cells']), samples=sum(v['measurements'] for v in report['cells']), maintenance=len(report['maintenance']))))


if __name__ == '__main__':
    main()

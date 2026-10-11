"""In-process synthetic D3b HTTP transport. New /tmp output; no live server.

Steady-state cells exclude bootstrap, path discovery and writer preparation.
Includes real auth, D3a lookup, terminal guards, exact base64/JSON wire bytes.
"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, timedelta
import hashlib
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
from t66d2b_writers import seed, command, CountedCursor, historical_scans  # noqa: E402


@contextmanager
def transfer_profile():
    """Per-request nested stage timings, instrumentation ONLY in this tool.

    ContextVar keeps concurrent requests separate. Nested inclusive timings
    must not be summed. No production codec/auth/transfer code is modified.
    """
    from isolated_sync import transfer
    from isolated_sync.observation import ObservationRepository
    from isolated_sync.store import Store
    from isolated_sync.transfer import PathResolver, TransferRepository
    profile = ContextVar('d3b_diagnostic_stages', default=None)
    acquire = TransferRepository.acquire
    def measured(self, *args, **kwargs):
        values = Counter()
        token = profile.set(values)
        try:
            payload, metrics = acquire(self, *args, **kwargs)
            return payload, dict(metrics, **values)
        finally:
            profile.reset(token)
    def timed(name, fn, *, payload_only=False):
        def wrapped(*args, **kwargs):
            values = profile.get()
            if values is None or (payload_only and not (args and type(args[0]) is dict and 'chunks' in args[0])):
                return fn(*args, **kwargs)
            start = perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                values[name] += (perf_counter()-start)*1000
        return wrapped
    with (patch.object(TransferRepository, 'acquire', measured),
          patch.object(Store, 'get', timed('object_resolution_ms', Store.get)),
          patch.object(ObservationRepository, '_view_object', timed('object_resolution_ms', ObservationRepository._view_object)),
          patch.object(PathResolver, 'resolve', timed('typed_path_total_ms', PathResolver.resolve)),
          patch.object(PathResolver, 'validate', timed('typed_shape_ms', PathResolver.validate)),
          patch.object(transfer, 'encode', timed('json_serialization_ms', transfer.encode, payload_only=True)),
          patch.object(transfer.base64, 'b64encode', timed('chunk_base64_ms', transfer.base64.b64encode))):
        yield


def run(sizes, warmups, samples):
    from fastapi.testclient import TestClient
    from app.auth import _hash_session_token
    from isolated_sync.http import create_app
    from isolated_sync.observation import ObservationRepository, Evaluation
    from isolated_sync.observation_schema import ObservationSandbox, ObservationConnection
    from isolated_sync.transfer import TransferLimits
    from isolated_sync.inputs import BoundedInputs
    from tests.test_isolated_sync_observation import NOW
    from tests.test_isolated_sync_transfer import graph

    report = dict(profile='isolated-d3b/1', environment=dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                  platform=platform.platform(), cpu=platform.processor(), logical_cpus=os.cpu_count()), cells=[])
    token = 'synthetic-d3b-benchmark-only'
    headers = {'Authorization': 'Bearer '+token}
    url = '/api/sync/v1/observations'
    for size in sizes:
        with ObservationSandbox() as db:
            with db.connect() as conn:
                seed(conn, size)
                conn.execute("INSERT INTO users(id,username,password_hash) VALUES (1,'synthetic', 'synthetic')")
                conn.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES (1,?, '2026-12-31T00:00:00Z')", (_hash_session_token(token),))
            db.install()
            db.bootstrap()  # ONE O(N) preparation, never repeated in timed cells.
            now, measured = [NOW], []
            repo = ObservationRepository(db, clock=lambda: now[0], evaluation=lambda: Evaluation(date(2026, 10, 5), 540))
            with TestClient(create_app(repo, limits=TransferLimits(concurrent_requests=8), metrics=measured.append)) as c:
                manifest_body = dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)
                old = c.post(url, json=manifest_body, headers=headers).json()
                old_graph = graph(db, old)  # Explicit test oracle outside timing.
                for workload in ('observation_create', 'manifest_retry', 'root', 'leaf', 'patricia_deep', 'changed_objects', 'unchanged_retry', 'concurrent'):
                    if workload == 'changed_objects':
                        with db.connect() as conn:
                            conn.begin_capture()
                            command('card', BoundedInputs(conn), 1)
                            conn.finalize()
                            conn.commit()
                        now[0] += timedelta(seconds=901)
                    if workload != 'observation_create':
                        manifest_body = dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)
                        m = c.post(url, json=manifest_body, headers=headers).json()
                        if 'target' not in m:
                            raise RuntimeError('fixture observation unavailable')
                        objects = graph(db, m)
                        if workload in ('root', 'unchanged_retry', 'concurrent'):
                            selected = [objects[m['target']['raw_ref']['hash']]]
                        elif workload == 'leaf':
                            selected = [next(v for v in objects.values() if v[3]['kind'] == 'snapshot-leaf' and v[3]['table'] == 'ledger_entries')]
                        elif workload == 'patricia_deep':
                            selected = [max((v for v in objects.values() if v[3]['kind'] == 'index-leaf'), key=lambda v: len(v[1]))]
                        elif workload == 'changed_objects':
                            selected = [v for h, v in objects.items() if h not in old_graph and v[3]['kind'] in ('snapshot-leaf', 'snapshot-node')][:3]
                        else:
                            selected = []
                        object_body = dict(protocol=1, request_id=str(uuid4()), items=[dict(path=v[1], offset='0', length=len(v[2])) for v in selected])
                        endpoint = url+'/'+m['observation_id']+'/objects'
                    trials, plans, bad = [], {}, {}
                    for trial in range(-warmups, samples):
                        if workload == 'observation_create':
                            now[0] += timedelta(seconds=901)
                            manifest_body = dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)
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
                        measured.clear()
                        def operation():
                            if workload in ('observation_create', 'manifest_retry'):
                                return c.post(url, json=manifest_body, headers=headers)
                            return c.post(endpoint, json=object_body, headers=headers)
                        with patch.object(ObservationConnection, 'execute', execute), patch.object(db, 'connect', counted), transfer_profile():
                            mark = perf_counter()
                            if workload == 'concurrent':
                                with ThreadPoolExecutor(2) as pool:
                                    outputs = list(pool.map(lambda _: operation(), range(2)))
                            else:
                                outputs = [operation()]
                            elapsed = (perf_counter()-mark)*1000
                        if any(r.status_code not in (200, 201) for r in outputs):
                            raise RuntimeError('synthetic HTTP cell failed')
                        with db.connect() as conn:
                            for sql, parameters in queries.items():
                                if sql not in plans:
                                    plan = [r[3] for r in conn.execute('EXPLAIN QUERY PLAN '+sql, parameters)]
                                    plans[sql] = plan
                                    offending = [p for p in historical_scans(sql, plan) if not any(s in p for s in (
                                        'sync_observation_profile', 'sync_observation_budget', 'sync_observations', 'sync_observation_pins'))]
                                    if offending:
                                        bad[sql] = offending
                        if trial >= 0:
                            metrics = measured[0].copy()
                            metrics.pop('operation')
                            trials.append(dict(metrics, total_http_ms=elapsed, sql_statements=sum(calls.values()), materialized_rows=rows[0],
                                               vm_steps_lower_bound=vm[0], sql=dict(calls), wire_bytes=sum(len(r.content) for r in outputs)))
                    numeric = [key for key, value in trials[0].items() if isinstance(value, (int, float))]
                    stats = {key: dict(median=statistics.median(v[key] for v in trials), p95=sorted(v[key] for v in trials)[math.ceil(.95*len(trials))-1]) for key in numeric}
                    report['cells'].append(dict(ledger_rows=size, workload=workload, warmups=warmups, measurements=samples, stats=stats,
                        query_plans=plans, unexpected_history_scans=bad, samples=trials, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        requested_objects=len(selected) if workload not in ('observation_create', 'manifest_retry') else 0,
                        changed_graph_objects=len(set(objects)-set(old_graph)) if workload == 'changed_objects' else None))
                    if bad:
                        raise RuntimeError('historical SQL scan detected')
                    # Expire preparatory/cell observations, do not release pins.
                    now[0] += timedelta(seconds=901)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sizes', type=int, nargs='+', default=[376, 1000, 5000, 10000])
    parser.add_argument('--warmups', type=int, default=3)
    parser.add_argument('--samples', type=int, default=20)
    args = parser.parse_args()
    check_output(args.output)
    if any(n not in (376, 1000, 5000, 10000) for n in args.sizes) or not 0 <= args.warmups <= 3 or not 1 <= args.samples <= 20:
        parser.error('bounded synthetic sizes and at most 3 warmups/20 samples required')
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (1800, 1800))
    report = run(args.sizes, args.warmups, args.samples)
    with args.output.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, separators=(',', ':'))
    print(json.dumps(dict(cells=len(report['cells']), unexpected_history_scans=sum(len(c['unexpected_history_scans']) for c in report['cells']),
                         sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()

"""Synthetic matched M01 HTTP-only before/after diagnostic; new /tmp output.

Loads the audited HTTP module from Git without changing the worktree. Both
variants share the CURRENT financial/codec/artifact implementation, isolating
the dispatch correction rather than comparing unrelated engine builds.
"""

import argparse
import asyncio
from datetime import date
import json
import math
from pathlib import Path
import platform
import resource
import sqlite3
import statistics
import subprocess
import sys
from time import perf_counter
from threading import BoundedSemaphore
import types
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
sys.path.insert(0, str(ROOT/'scripts/benchmarks'))
from t66d2b import check_output  # noqa: E402
from t66d2b_writers import seed  # noqa: E402

BASELINE = 'e97b1d7f54231e6cc21d7d2ec897f6fd150cbd32'


def stats(values):
    return {key: dict(median=statistics.median(v[key] for v in values),
                      p95=sorted(v[key] for v in values)[math.ceil(.95*len(values))-1]) for key in values[0]}


async def cancellation(db, manifest, samples, warmups):
    from tests.test_isolated_sync_transfer_cancellation import Barrier, Rig, cancel

    values = []
    for trial in range(-warmups, samples):
        barrier = Barrier(asyncio.get_running_loop())
        rig = Rig(db, manifest, fault=barrier.fault, limit=1)
        messages = []
        task = asyncio.create_task(rig.invoke(messages))
        try:
            await barrier.wait()
            started = perf_counter()
            await cancel(task)
            assert rig.adapter.workers.snapshot()['running'] == 1
            assert rig.adapter.workers.acquire() is None
            assert barrier.tickets[0].cancelled.is_set()
        finally:
            released = perf_counter()
            barrier.release.set()
            await rig.drain()
        finished = perf_counter()
        admitted = rig.adapter.workers.acquire()
        reacquired = perf_counter()
        assert admitted is not None and not messages
        admitted.close()
        if trial >= 0:
            values.append(dict(cancel_to_cleanup_ms=(finished-started)*1000,
                               barrier_release_to_cleanup_ms=(finished-released)*1000,
                               post_cleanup_admission_ms=(reacquired-finished)*1000))
    return dict(warmups=warmups, measurements=samples, stats=stats(values), samples=values)


def run(samples, warmups):
    from fastapi.testclient import TestClient
    from app.auth import _hash_session_token
    from isolated_sync import http, workers
    from isolated_sync.observation import ObservationRepository, Evaluation
    from isolated_sync.observation_schema import ObservationSandbox, ObservationConnection
    from tests.test_isolated_sync_observation import NOW
    from tests.test_isolated_sync_transfer import graph

    baseline = types.ModuleType('isolated_sync._m01_baseline')
    sys.modules[baseline.__name__] = baseline
    source = subprocess.check_output(['git', 'show', BASELINE+':backend/isolated_sync/http.py'], cwd=ROOT)
    exec(compile(source, '<audited-http>', 'exec'), baseline.__dict__)
    report = dict(baseline_http=BASELINE, shared_current_dependencies=True, ledger_rows=376,
                  environment=dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                                   platform=platform.platform()), cells=[])
    with ObservationSandbox() as db:
        token = 'synthetic-m01-benchmark'
        with db.connect() as conn:
            seed(conn, 376)
            conn.execute("INSERT INTO users(id,username,password_hash) VALUES(1,'synthetic','synthetic')")
            conn.execute("INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES(1,?,'2026-12-31T00:00:00Z')",
                         (_hash_session_token(token),))
        db.install()
        db.bootstrap()
        metrics = []
        repo = ObservationRepository(db, clock=lambda: NOW, evaluation=lambda: Evaluation(date(2026, 10, 5), 540))
        clients = {name: TestClient(module.create_app(repo, metrics=metrics.append))
                   for name, module in (('before', baseline), ('after', http))}
        headers = {'Authorization': 'Bearer '+token}
        url = '/api/sync/v1/observations'
        nonce = dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)
        manifest = clients['after'].post(url, json=nonce, headers=headers).json()
        objects = graph(db, manifest)  # O(N) discovery ONLY outside timing.
        root = objects[manifest['target']['raw_ref']['hash']]
        leaf = next(v for v in objects.values() if v[3]['kind'] == 'snapshot-leaf' and v[3]['table'] == 'ledger_entries')
        control = objects[manifest['target']['control_ref']['hash']]
        native_dispatch = workers.run_in_threadpool
        for workload, selected in (('manifest_retry', []), ('root', [root]), ('leaf', [leaf]), ('batch', [root, leaf, control])):
            trials = {'before': [], 'after': []}
            expected = None
            for trial in range(-warmups, samples):
                # Alternate order to reduce drift under unrelated host load.
                for variant in (('before', 'after') if trial % 2 else ('after', 'before')):
                    metrics.clear()
                    dispatches, statements = [], []
                    async def measured(function, *args):
                        admitted = perf_counter()
                        def native():
                            dispatches.append((perf_counter()-admitted)*1000)
                            return function(*args)
                        return await native_dispatch(native)
                    execute = ObservationConnection.execute
                    def traced(conn, sql, parameters=()):
                        statements.append(sql)
                        return execute(conn, sql, parameters)
                    body = dict(protocol=1, request_id=nonce['request_id'], items=[
                        dict(path=v[1], offset='0', length=len(v[2])) for v in selected])
                    with (patch.object(baseline, 'run_in_threadpool', measured),
                          patch.object(workers, 'run_in_threadpool', measured),
                          patch.object(ObservationConnection, 'execute', traced)):
                        start = perf_counter()
                        result = clients[variant].post(url if not selected else url+'/'+manifest['observation_id']+'/objects',
                                                       json=nonce if not selected else body, headers=headers)
                        elapsed = (perf_counter()-start)*1000
                    assert result.status_code == 200, result.status_code
                    if expected is None:
                        expected = result.content
                    assert result.content == expected
                    forbidden = [s for s in statements if 'LIMIT 0' not in s.upper() and
                                 any(' FROM '+t in s.upper() for t in ('LEDGER_ENTRIES', 'CASH_FLOWS', 'SYNC_ROWS', 'SYNC_OBJECT_EDGES'))]
                    assert not forbidden
                    if trial >= 0:
                        trials[variant].append(dict(total_ms=elapsed, dispatch_ms=sum(dispatches),
                                                    terminal_ms=metrics[0]['terminal_http_ms'], sql_statements=len(statements),
                                                    wire_bytes=len(result.content), object_reads=metrics[0].get('object_reads', 0)))
            for variant, values in trials.items():
                report['cells'].append(dict(variant=variant, workload=workload, warmups=warmups,
                                           measurements=samples, stats=stats(values), samples=values))
        with patch('tests.test_isolated_sync_transfer_cancellation.TOKEN_A', token):
            report['cancellation'] = asyncio.run(cancellation(db, manifest, samples, warmups))
        budget, semaphore = workers.WorkerBudget(2), BoundedSemaphore(2)
        costs = []
        for trial in range(-warmups, samples):
            start = perf_counter()
            assert semaphore.acquire(False)
            old = perf_counter()
            semaphore.release()
            start_new = perf_counter()
            lease = budget.acquire()
            new = perf_counter()
            lease.close()
            if trial >= 0:
                costs.append(dict(before_admission_us=(old-start)*1e6, after_admission_us=(new-start_new)*1e6))
        report['admission_primitive'] = dict(measurements=samples, stats=stats(costs), samples=costs)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=20)
    parser.add_argument('--warmups', type=int, default=3)
    args = parser.parse_args()
    check_output(args.output)
    if not 3 <= args.samples <= 100 or not 3 <= args.warmups <= 10:
        parser.error('bounded samples/warmups required')
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3, 4*1024**3))
    args.output.write_text(json.dumps(run(args.samples, args.warmups), ensure_ascii=False), encoding='utf-8')

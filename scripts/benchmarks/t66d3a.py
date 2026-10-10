"""Synthetic D3a observation only; no configured DB/HTTP/runtime startup.

New /tmp output only. 3 warmups + 20 measurements per cell by default.
Full financial oracle is outside timing. No bootstrap per measured observation.
"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import hashlib
import json
import math
import platform
import resource
import sqlite3
import statistics
import sys
from pathlib import Path
from threading import Event
from time import perf_counter, sleep
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
sys.path.insert(0, str(ROOT/'scripts/benchmarks'))
from t66d2b import check_output  # noqa: E402
from t66d2b_writers import seed, command, CountedCursor, historical_scans  # noqa: E402


class MaterializedCursor(CountedCursor):
    """Exact returned BLOB bytes, NOT filesystem/page I/O or wire bytes."""
    def __init__(self, cursor, counter, blobs):
        super().__init__(cursor, counter)
        self.blobs = blobs

    def count_blobs(self, row):
        if row is not None:
            self.blobs[0] += sum(len(value) for value in row if isinstance(value, bytes))
        return row

    def fetchone(self):
        return self.count_blobs(super().fetchone())

    def fetchall(self):
        return [self.count_blobs(row) for row in super().fetchall()]

    def __iter__(self):
        for row in super().__iter__():
            yield self.count_blobs(row)


def run(sizes, warmups, samples):
    from isolated_sync.observation import ObservationRepository, Evaluation
    from isolated_sync.observation_schema import ObservationSandbox, ObservationConnection
    from isolated_sync.inputs import BoundedInputs
    from tests.test_isolated_sync_observation import auth_seed, CREDENTIAL, NOW
    from tests.test_isolated_sync_finalization import verify
    report = dict(profile='isolated-d3a/1', environment=dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version,
                  platform=platform.platform(), cpu=platform.processor(), logical_cpus=__import__('os').cpu_count()), cells=[])
    for size in sizes:
        with ObservationSandbox() as db:
            with db.connect() as conn:
                seed(conn, size)
                auth_seed(conn)
            db.install()
            mark = perf_counter()
            db.bootstrap()
            bootstrap_ms = (perf_counter()-mark)*1000
            ordinal = 0
            base = None
            for workload in ('no_change', 'after_card', 'after_cash', 'date_transition', 'two_observers', 'writer_contention'):
                if workload in ('after_card', 'after_cash'):
                    with db.connect() as conn:
                        conn.begin_capture()
                        command(workload.removeprefix('after_'), BoundedInputs(conn), 1)
                        conn.finalize()
                        conn.commit()
                if workload in ('no_change', 'after_card', 'after_cash'):
                    with db.connect() as conn:
                        verify(conn)  # O(N) oracle once per raw state, OUTSIDE timing.
                if base is None:
                    base = ObservationRepository(db, evaluation=lambda: Evaluation(date(2026, 10, 5), 540), clock=lambda: NOW).create(
                        CREDENTIAL, request_id=str(uuid4()), guard=lambda: CREDENTIAL)['target']
                    ordinal = 1  # Let the preparatory lease expire; no GC/eviction.
                trials, plans, offending, statement_counts = [], {}, {}, Counter()
                for trial in range(-warmups, samples):
                    rows, calls, vm, blobs, writes = [0], Counter(), [0], [0], Counter()
                    queries = {}
                    original = ObservationConnection.execute
                    attempted = Event()
                    def execute(conn, sql, parameters=()):
                        if sql == 'BEGIN IMMEDIATE':
                            attempted.set()
                        calls[sql.lstrip().split()[0].upper()] += 1
                        if sql.lstrip().upper().startswith('SELECT'):
                            queries[sql] = parameters
                        cursor = original(conn, sql, parameters)
                        if sql.lstrip().upper().startswith(('INSERT', 'UPDATE')):
                            writes['written_blob_bytes'] += sum(len(v) for v in parameters if isinstance(v, bytes))
                        if sql.startswith('INSERT INTO sync_objects '):
                            writes['immutable_object_writes'] += 1
                            writes['immutable_object_bytes'] += len(parameters[2])
                        return MaterializedCursor(cursor, rows, blobs)
                    now = NOW+timedelta(seconds=901*ordinal)
                    ordinal += 1
                    evaluation = Evaluation(date(2026, 11, 1) if workload == 'date_transition' else date(2026, 10, 5), 540)
                    def observe():
                        repo = ObservationRepository(db, evaluation=lambda: evaluation, clock=lambda: now)
                        response = repo.create(CREDENTIAL, request_id=str(uuid4()), guard=lambda: CREDENTIAL, base=base)
                        return repo.metrics, response
                    # Count VM steps on EVERY repository connection, including
                    # read/input/metadata/schema work; no sensitive trace output.
                    original_connect = db.connect
                    def connect():
                        conn = original_connect()
                        def progress():
                            vm[0] += 100
                            return 0
                        conn.set_progress_handler(progress, 100)
                        return conn
                    writer = None
                    if workload == 'writer_contention':
                        writer = db.connect()
                        writer.execute('BEGIN IMMEDIATE')  # bounded auth/metadata writer, no financial mutation
                    with patch.object(ObservationConnection, 'execute', execute), patch.object(db, 'connect', connect):
                        mark = perf_counter()
                        if workload in ('two_observers', 'writer_contention'):
                            with ThreadPoolExecutor(2) as pool:
                                futures = [pool.submit(observe) for _ in range(2 if workload == 'two_observers' else 1)]
                                if writer:
                                    if not attempted.wait(2):
                                        raise RuntimeError('observer did not attempt lock')
                                    sleep(0.01)  # explicitly imposed 10ms contention, NOT server timing claim
                                    writer.rollback()
                                    writer.close()
                                outputs = [f.result(10) for f in futures]
                        else:
                            outputs = [observe()]
                        total = (perf_counter()-mark)*1000
                    # SQL plans inspected on a fresh connection, OUTSIDE timing.
                    with db.connect() as conn:
                        for sql, params in queries.items():
                            if sql not in plans:
                                plan = [r[3] for r in conn.execute('EXPLAIN QUERY PLAN '+sql, params)]
                                plans[sql] = plan
                                bad = [p for p in historical_scans(sql, plan) if not any(s in p for s in (
                                    'sync_observation_profile', 'sync_observation_budget', 'sync_observations', 'sync_observation_pins'))]
                                if bad:
                                    offending[sql] = bad
                    if trial >= 0:
                        # No bodies/token hashes in artifacts, only measurements.
                        metrics = outputs[0][0].copy()
                        metrics.update(total_request_ms=total, sql=dict(calls), materialized_rows=rows[0],
                                       returned_blob_bytes=blobs[0], vm_steps_lower_bound=vm[0])
                        metrics.update({key: writes[key] for key in ('written_blob_bytes', 'immutable_object_writes', 'immutable_object_bytes')})
                        metrics['change_kind'] = outputs[0][1]['change_kind']
                        trials.append(metrics)
                        statement_counts.update(calls)
                scalar_keys = [key for key, value in trials[0].items() if isinstance(value, (int, float))]
                stats = {key: dict(median=statistics.median(t[key] for t in trials),
                                   p95=sorted(t[key] for t in trials)[math.ceil(0.95*len(trials))-1]) for key in scalar_keys}
                report['cells'].append(dict(ledger_rows=size, workload=workload, warmups=warmups, measurements=samples,
                                            bootstrap_ms=bootstrap_ms, stats=stats, sql_plans=plans, historical_scans=offending,
                                            samples=trials, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
                if offending:
                    raise RuntimeError('historical scan detected: '+json.dumps(offending, sort_keys=True))
                base = outputs[0][1]['target']
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sizes', type=int, nargs='+', default=[376, 1000, 5000, 10000])
    parser.add_argument('--warmups', type=int, default=3)
    parser.add_argument('--samples', type=int, default=20)
    args = parser.parse_args()
    check_output(args.output)
    if any(size not in (376, 1000, 5000, 10000) for size in args.sizes) or args.warmups < 3 or args.samples < 20:
        parser.error('bounded fixed profiles require >=3 warmups and >=20 samples')
    resource.setrlimit(resource.RLIMIT_AS, (2*1024**3, 2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (1800, 1800))
    report = run(args.sizes, args.warmups, args.samples)
    with args.output.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, separators=(',', ':'))
    print(json.dumps(dict(cells=len(report['cells']), historical_scans=sum(len(c['historical_scans']) for c in report['cells']),
                          sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()

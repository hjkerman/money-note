"""Synthetic M01/M02 correction cost comparison; NO runtime/DB path input.

Read the audited source from Git (never checkout/reset), compare it with current
source on one self-owned sandbox. Output only to a new /tmp file. Bootstrap is
outside timing; 3 warmups/20 measurements, fixed hot set, no network/GC.
"""

import argparse
from collections import Counter
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from time import perf_counter
from types import ModuleType
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
sys.path.insert(0, str(ROOT/'scripts/benchmarks'))
from t66d2b import check_output  # noqa: E402
from t66d2b_writers import seed  # noqa: E402

AUDITED = 'c6ce6d9f84633b24a2f43330a90487ca16d0b3c4'


def run(sizes):
    import sqlite3
    from isolated_sync import observation
    from isolated_sync.observation_schema import ObservationConnection, ObservationSandbox
    from tests.test_isolated_sync_observation import CREDENTIAL, NOW, auth_seed
    path = 'backend/isolated_sync/observation.py'
    source = subprocess.run(['git', 'show', f'{AUDITED}:{path}'], cwd=ROOT, check=True, capture_output=True).stdout
    reference = ModuleType('isolated_observation_audited_cost_reference')
    reference.__file__ = str(ROOT/path)
    sys.modules[reference.__name__] = reference
    exec(compile(source, reference.__file__, 'exec'), reference.__dict__)
    result = dict(audited_commit=AUDITED, audited_source_sha256=hashlib.sha256(source).hexdigest(),
                  corrected_source_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
                  environment=dict(python=platform.python_version(), sqlite=sqlite3.sqlite_version, platform=platform.platform()),
                  warmups=3, measurements=20, cells=[])
    for size in sizes:
        with ObservationSandbox() as db:
            with db.connect() as conn:
                seed(conn, size)
                auth_seed(conn)
            db.install()
            db.bootstrap()
            ordinal = 0
            for label, implementation in [('audited', reference), ('corrected', observation)]:
                samples = []
                for trial in range(-3, 20):
                    counts = Counter()
                    original = ObservationConnection.execute
                    def execute(conn, sql, parameters=()):
                        counts[sql.lstrip().split()[0].upper()] += 1
                        return original(conn, sql, parameters)
                    # Expire the prior observation without sleeping. Both
                    # implementations share the CURRENT engine artifact bytes
                    # and identical source rows/presenter context for this cost
                    # control; this is not a legacy release compatibility test.
                    now = NOW+timedelta(seconds=901*ordinal)
                    ordinal += 1
                    repo = implementation.ObservationRepository(db, clock=lambda: now,
                        evaluation=lambda: observation.Evaluation(date(2026, 10, 5), 540))
                    with patch.object(ObservationConnection, 'execute', execute):
                        start = perf_counter()
                        response = repo.create(CREDENTIAL, request_id=str(uuid4()), guard=lambda: CREDENTIAL)
                        create_ms = (perf_counter()-start)*1000
                        create_sql = dict(counts)
                        counts.clear()
                        start = perf_counter()
                        assert repo.lookup(response['observation_id'], CREDENTIAL, guard=lambda: CREDENTIAL) == response
                        lookup_ms = (perf_counter()-start)*1000
                    if trial >= 0:
                        samples.append(dict(create_ms=create_ms, lookup_ms=lookup_ms, create_sql=create_sql,
                                            lookup_sql=dict(counts), object_reads=repo.metrics['object_reads']))
                cell = dict(rows=size, implementation=label, samples=samples)
                for operation in ('create', 'lookup'):
                    times = sorted(s[operation+'_ms'] for s in samples)
                    cell[operation] = dict(median_ms=statistics.median(times), p95_ms=times[math.ceil(len(times)*.95)-1])
                result['cells'].append(cell)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--sizes', nargs='+', type=int, default=[376, 1000])
    args = parser.parse_args()
    check_output(args.output)
    if not args.sizes or len(args.sizes) > 2 or len(set(args.sizes)) != len(args.sizes) or any(size not in (376, 1000) for size in args.sizes):
        parser.error('bounded correction benchmark supports 376/1000 only')
    report = run(args.sizes)
    with open(args.output, 'x', encoding='utf-8') as output:
        json.dump(report, output, indent=2)
    print(json.dumps([dict(rows=c['rows'], implementation=c['implementation'], create=c['create'], lookup=c['lookup']) for c in report['cells']]))

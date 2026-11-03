"""Host-only coding benchmark; no DB, network, Flutter CLI, or production access.

Run with repository .venv Python, PYTHONPATH=backend, --scratch TASK_OWNED_DIR.
The immutable discovery artifact supplies the six synthetic response bodies.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time

from starlette.requests import Request
from starlette.responses import Response
from app.routers.response_coding import code_json_response


def summary(samples, key):
    values = sorted(s[key] for s in samples)
    return {"median": statistics.median(values), "p95": values[int(len(values) * .95) - 1]}


def worker(folder, rows, route, mode, concurrency):
    raw = (folder / f"{rows}-{route}.raw").read_bytes()
    path = "/api/authoritative-state" if route == "bundle" else "/api/admin/snapshot"
    def one():
        req = Request({"type": "http", "method": "GET", "path": path,
                       "headers": [(b"accept-encoding", mode.encode())]})
        return code_json_response(req, Response(raw, media_type="application/json"))
    pool = ThreadPoolExecutor(max_workers=concurrency) if concurrency == 2 else None
    def batch():
        return list(pool.map(lambda _: one(), range(2))) if pool else [one()]
    rss_before = int(next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('VmRSS:')))
    samples = []
    for iteration in range(25):
        cpu, wall = time.process_time_ns(), time.perf_counter_ns()
        results = batch()
        elapsed = {"wall_ms": (time.perf_counter_ns() - wall) / 1e6,
                   "cpu_ms": (time.process_time_ns() - cpu) / 1e6}
        if iteration >= 5: samples.append(elapsed)
    status = Path('/proc/self/status').read_text().splitlines()
    peak = int(next(line.split()[1] for line in status if line.startswith('VmHWM:')))
    inherited_high_water = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if pool: pool.shutdown()
    for result in results:
        assert (gzip.decompress(result.body) if mode == "gzip" else result.body) == raw
    return {"rows": rows, "route": route, "mode": mode, "concurrency": concurrency,
            "identity_entity_bytes": len(raw), "entity_bytes_each": len(results[0].body),
            "sha256": hashlib.sha256(raw).hexdigest(), "rss_before_kib": rss_before,
            "peak_rss_kib": peak, "peak_above_before_kib": max(0, peak - rss_before),
            "rusage_maxrss_kib_not_attributed": inherited_high_water,
            "wall_ms": summary(samples, "wall_ms"), "cpu_ms": summary(samples, "cpu_ms"),
            "samples": samples}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--worker', nargs=4)
    args = parser.parse_args()
    folder = args.scratch.resolve()
    if args.worker:
        n, route, mode, c = args.worker
        print(json.dumps(worker(folder, int(n), route, mode, int(c))))
        return
    folder.mkdir(exist_ok=True)
    evidence_path = Path('docs/benchmarks/phase2-mobile-network-evidence.json.gz')
    old = json.loads(gzip.decompress(evidence_path.read_bytes()))
    fixtures = []
    for fixture in old['backend_capture']['fixtures']:
        n = fixture['rows']
        for route in ('bundle', 'snapshot'):
            rec = fixture['records'][route]
            raw = base64.b64decode(old['response_body_blobs'][rec['sha256']]['base64'])
            assert hashlib.sha256(raw).hexdigest() == rec['sha256']
            (folder / f'{n}-{route}.raw').write_bytes(raw)
            req = Request({'type': 'http', 'method': 'GET', 'path': rec['path'],
                           'headers': [(b'accept-encoding', b'gzip')]})
            coded = code_json_response(req, Response(raw, media_type='application/json'))
            assert len(coded.body) == rec['gzip6_bytes']
            assert gzip.decompress(coded.body) == raw
            (folder / f'{n}-{route}.gzip').write_bytes(coded.body)
            fixtures.append({'rows': n, 'route': route, 'sha256': rec['sha256'],
                             'identity_bytes': len(raw), 'gzip_bytes': len(coded.body)})
    results = []
    started = time.monotonic()
    for fixture in fixtures:
        for concurrency in (1, 2):
            for mode in ('identity', 'gzip'):
                command = [sys.executable, __file__, '--scratch', str(folder), '--worker',
                           str(fixture['rows']), fixture['route'], mode, str(concurrency)]
                run = subprocess.run(command, capture_output=True, text=True, timeout=35, check=True)
                results.append(json.loads(run.stdout))
    result = {'task': 'P2-N01', 'source_baseline': '741e053c49bbbd3b6eaf9ff268e525af0b2f8a35',
              'python': sys.version, 'platform': platform.platform(),
              'discovery_evidence_sha256': hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
              'fixtures': fixtures, 'results': results, 'elapsed_s': time.monotonic() - started,
              'method': '5 warmup + 20 measured batches; fresh child per configuration; two threads for concurrency=2; coding helper wall/process CPU only, JSON/backend/network excluded; /proc VmRSS before batches, VmHWM before verification (ru_maxrss inherited floor excluded); no additive latency claims'}
    (folder / 'benchmark.json').write_text(json.dumps(result))
    print(json.dumps({'configurations': len(results), 'measured_batches': len(results)*20,
                      'elapsed_s': result['elapsed_s'], 'output': str(folder/'benchmark.json')}))


if __name__ == '__main__':
    main()

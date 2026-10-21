"""독립 paired HOST 소형/중형 wall/CPU/RSS 관측. N=100k 실행이 아니다."""

from contextlib import closing
import json
from pathlib import Path
import resource
import sqlite3
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(HERE.parent / "t66f-b03")]
from isolated_sync import canonical  # noqa: E402
from counters import Collector, instrument, observed_factory  # noqa: E402


def rss():
    return int(Path("/proc/self/statm").read_text().split()[1]) * 4096


def main():
    results = {}
    for label, iterations, size, rows in [
        ("small", 200, 64, 20),
        ("medium", 2000, 4096, 200),
    ]:
        raw = ('{"kind":"hot","text":"' + "x" * size + '"}').encode()
        samples = {"off": [], "on": []}
        for repeat in range(23):
            for enabled in [True, False] if repeat % 2 else [False, True]:
                before_rss = rss()
                c = Collector()
                context = instrument() if enabled else None
                t = time.perf_counter_ns()
                if context:
                    context.__enter__()
                init = time.perf_counter_ns() - t
                wall, cpu = time.perf_counter_ns(), time.process_time_ns()
                with c.stage("calibration"):
                    for _ in range(iterations):
                        canonical.Object("hot", raw)
                primitive_wall = time.perf_counter_ns() - wall
                primitive_cpu = time.process_time_ns() - cpu
                t = time.perf_counter_ns()
                if context:
                    context.__exit__(None, None, None)
                teardown = time.perf_counter_ns() - t
                database_started = time.perf_counter_ns()
                database = sqlite3.connect(
                    ":memory:",
                    isolation_level=None,
                    factory=observed_factory() if enabled else sqlite3.Connection,
                )
                database_init = time.perf_counter_ns() - database_started
                with closing(database) as d:
                    d.execute("CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)")
                    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
                    with c.stage("generation"):
                        d.execute("BEGIN")
                        for i in range(rows):
                            d.execute("INSERT INTO payload VALUES (?,?)", (str(i), raw))
                        d.execute("COMMIT")
                    sql_wall = time.perf_counter_ns() - wall
                    sql_cpu = time.process_time_ns() - cpu
                    assert d.execute(
                        "SELECT count(*),sum(length(b)) FROM payload"
                    ).fetchone() == (rows, rows * len(raw))
                    database_close_started = time.perf_counter_ns()
                database_close = time.perf_counter_ns() - database_close_started
                if repeat >= 3:
                    samples["on" if enabled else "off"].append(
                        dict(
                            primitive_wall_ns=primitive_wall,
                            primitive_cpu_ns=primitive_cpu,
                            sql_wall_ns=sql_wall,
                            sql_cpu_ns=sql_cpu,
                            init_ns=init,
                            teardown_ns=teardown,
                            database_init_ns=database_init,
                            database_close_ns=database_close,
                            rss_delta_bytes=rss() - before_rss,
                            aggregate_keys=len(c.snapshot()),
                        )
                    )
        summary = {}
        for mode, values in samples.items():
            summary[mode] = {
                k: dict(
                    median=statistics.median(v[k] for v in values),
                    p95=sorted(v[k] for v in values)[18],
                )
                for k in values[0]
            }
        results[label] = dict(
            iterations=iterations,
            payload_bytes=len(raw),
            rows=rows,
            samples=samples,
            summary=summary,
        )
    output = dict(
        environment="HOST Linux same process, 3 warmup + 20 alternating pairs",
        results=results,
        maxrss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        limits="RSS 차분은 heap allocation이 아니다. 계측 설치/SQL TEMP 비용 포함 경계를 분리. 100k lease 및 Android는 미검증",
    )
    (HERE / "evidence/overhead-independent-python-complete.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({k: v["summary"] for k, v in results.items()}))


if __name__ == "__main__":
    main()

"""실제 C1/Object와 SQLite API의 paired HOST overhead. 비용 grid 결과가 아니다."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from isolated_sync import canonical  # noqa: E402
from counters import Collector, instrument, observed_factory  # noqa: E402


def main():
    raw = b'{"kind":"hot","value":"synthetic"}'
    samples = {"primitive_off": [], "primitive_on": [], "sql_off": [], "sql_on": []}
    last = None
    for repetition in range(13):
        for enabled in [False, True] if repetition % 2 else [True, False]:
            c = Collector()
            if enabled:
                with instrument(), c.stage("calibration"):
                    started = time.perf_counter_ns()
                    for _ in range(1000):
                        canonical.Object("hot", raw)
                    elapsed = time.perf_counter_ns() - started
            else:
                started = time.perf_counter_ns()
                for _ in range(1000):
                    canonical.Object("hot", raw)
                elapsed = time.perf_counter_ns() - started
            if repetition >= 3:
                samples["primitive_on" if enabled else "primitive_off"].append(elapsed)
            with (
                c.stage("calibration"),
                closing(
                    sqlite3.connect(
                        ":memory:",
                        factory=observed_factory() if enabled else sqlite3.Connection,
                        isolation_level=None,
                    )
                ) as db,
            ):
                db.execute("CREATE TABLE objects(k TEXT PRIMARY KEY,body BLOB)")
                started = time.perf_counter_ns()
                db.execute("BEGIN")
                for n in range(200):
                    db.execute("INSERT INTO objects VALUES (?,?)", (str(n), raw))
                db.execute("COMMIT")
                elapsed = time.perf_counter_ns() - started
                assert db.execute(
                    "SELECT sum(length(body)),count(*) FROM objects"
                ).fetchone() == (200 * len(raw), 200)
            if repetition >= 3:
                samples["sql_on" if enabled else "sql_off"].append(elapsed)
            if enabled:
                last = c.snapshot()
    result = {
        "schema_version": 1,
        "environment": "HOST paired alternating, 3 warmup + 10 measured",
        "samples_ns": samples,
        "median_ns": {k: statistics.median(v) for k, v in samples.items()},
        "last_counter": last,
        "claims": "소형 instrumentation overhead이며 100k lease 적합성·physical I/O proof가 아님",
    }
    if sys.argv[1:] not in ([], ["--approved"]):
        raise ValueError("허용된 합성 실행 이름이 아니다")
    filename = (
        "approved-overhead-python.json" if sys.argv[1:] else "overhead-python.json"
    )
    target = Path(__file__).resolve().parent / "evidence" / filename
    if target.exists():
        raise RuntimeError("과거 overhead 실행은 덮어쓰지 않는다")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["median_ns"]))


if __name__ == "__main__":
    main()

"""관측기 자체의 작은 HOST 비교. 앱 latency 또는 미래 Dart hook 비용이 아니다."""

import json
from pathlib import Path
import statistics
import time

from isolated_sync import canonical
from counters import Counters, observe_c1

HERE = Path(__file__).resolve().parent
RAW = b'{"kind":"hot","x":"\xed\x95\x9c"}'


def execute(count):
    for _ in range(count):
        canonical.Object("hot", RAW)


def main():
    samples = []
    for trial in range(23):
        c = Counters()
        values = {}
        # 교대 순서로 한쪽에만 warm cache가 유리한 영향을 줄인다.
        for enabled in [False, True] if trial % 2 else [True, False]:
            if enabled:
                with observe_c1(c):
                    start = time.perf_counter_ns()
                    execute(1000)
                    values["on_ns"] = time.perf_counter_ns() - start
            else:
                start = time.perf_counter_ns()
                execute(1000)
                values["off_ns"] = time.perf_counter_ns() - start
        assert c.values["hash_input_bytes"] == 1000 * len(
            b"money-note.sync.v1/hot\0" + RAW
        )
        assert c.values["validation_completed_input_bytes"] == 1000 * len(RAW)
        if trial >= 3:
            samples.append(values)
    result = dict(
        boundary="실제 Python Object constructor × 1000; 관측기 2개의 합산 overhead, SQL·Dart·disk·HTTP 비용 아님",
        timebase="perf_counter_ns",
        warmups=3,
        samples=samples,
        median_off_ns=statistics.median(s["off_ns"] for s in samples),
        median_on_ns=statistics.median(s["on_ns"] for s in samples),
        aggregate_only=True,
        per_object_logging=False,
        counter_fields=len(c.values),
        future_dart_overhead="NOT MEASURED",
    )
    (HERE / "evidence/overhead.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()

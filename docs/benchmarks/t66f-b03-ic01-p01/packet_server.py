"""원 B02 100k fixture의 유한 TLS packet 교대 측정. 새 endpoint 없음.

Private stdin만 계측을 선택한다. 256 HTTP requests 상한, 원 real clock/TTL.
Full acquisition이 아니며 bootstrap/oracle는 이 preflight의 계측 대상이 아니다.
"""

from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(HERE.parent / "t66f-b03")]
import counters as cost  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "p01_b02_server", HERE.parent / "t66f-b02-implementation/server.py"
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
wire = base.Wire
enabled = False
stack = None
rows = []
cohort = cost.Collector()
started = 0
completed = 0


class MeasuredWire(wire):
    async def __call__(self, scope, receive, send):
        global started, completed
        if scope["type"] != "http":
            return await super().__call__(scope, receive, send)
        if started >= 256:
            raise RuntimeError("P01 finite packet request budget exceeded")
        started += 1
        wall, cpu = time.perf_counter_ns(), time.process_time_ns()
        local = cost.Collector()
        stage = "transfer" if scope["path"].endswith("/objects") else "observation"
        before = dict(self.counts)
        try:
            if enabled:
                with local.stage(stage):
                    await super().__call__(scope, receive, send)
            else:
                await super().__call__(scope, receive, send)
        finally:
            elapsed = time.perf_counter_ns() - wall
            cpu_ns = time.process_time_ns() - cpu

            def finish(c):
                global completed
                completed += 1
                if enabled:
                    cohort.merge(c)
                rows.append(
                    {
                        "enabled": enabled,
                        "stage": stage,
                        "wall_ns": elapsed,
                        "cpu_ns": cpu_ns,
                        "completed": True,
                        "pending": c.pending,
                        "wire": {
                            k: v - before.get(k, 0)
                            for k, v in self.counts.items()
                            if v - before.get(k, 0)
                        },
                    }
                )

            local.finish_when_idle(finish)


class Commands:
    def __iter__(self):
        global stack, enabled
        for line in sys.__stdin__:
            r = json.loads(line)
            if r["command"] == "p01_mode":
                assert started == completed, "native request cohort incomplete"
                if stack is not None:
                    stack.close()
                    stack = None
                enabled = bool(r["enabled"])
                if enabled:
                    stack = ExitStack()
                    stack.enter_context(cost.instrument())
                    stack.enter_context(cost.instrument_connections())
                    stack.enter_context(cost.instrument_workers())
                print(
                    json.dumps(
                        {"enabled": enabled, "started": started, "completed": completed}
                    ),
                    flush=True,
                )
            elif r["command"] == "p01_snapshot":
                assert started == completed
                print(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "started": started,
                            "completed": completed,
                            "rows": rows,
                            "counters": cohort.snapshot(),
                            "pending": cohort.pending,
                            "complete": started == completed,
                        }
                    ),
                    flush=True,
                )
            else:
                yield line


if __name__ == "__main__":
    with (
        patch.object(base, "Wire", MeasuredWire),
        patch.object(sys, "stdin", Commands()),
    ):
        try:
            base.main()
        finally:
            if stack is not None:
                stack.close()

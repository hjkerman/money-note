"""P03 원 B02 seed/실제 D3 TLS. Private clock 이동만 expiry 시험에 사용한다."""

from contextlib import ExitStack
from datetime import timedelta
import importlib.util
import json
from pathlib import Path
import resource
import sys
from threading import Condition
import time
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(HERE.parent / "t66f-b03")]
import counters as cost  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "p03_base", HERE.parent / "t66f-b02-implementation/server.py"
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
spec = importlib.util.spec_from_file_location(
    "p03_oracle", HERE.parent / "t66f-b02-independent/oracle.py"
)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
base.oracle.walk = oracle.walk
from isolated_sync.observation import utc_now  # noqa: E402
from isolated_sync.finalization import FinalizationSandbox  # noqa: E402

state = {
    "enabled": True,
    "offset": 0,
    "label": "generation",
    "started": 0,
    "completed": 0,
}
lock = Condition()
stack = None
total = cost.Collector()
generation = cost.Collector()
groups = {}
wire_instance = None


def mode(enabled):
    global stack
    if stack is not None:
        stack.close()
        stack = None
    state["enabled"] = enabled
    if enabled:
        stack = ExitStack()
        for cm in [
            cost.instrument(),
            cost.instrument_connections(),
            cost.instrument_workers(),
        ]:
            stack.enter_context(cm)


mode(True)
old_bootstrap = FinalizationSandbox.bootstrap


def bootstrap(self):
    with generation.stage("generation"):
        return old_bootstrap(self)


old_repo = base.RetentionRepository


class Repository(old_repo):
    def __init__(self, *a, **kw):
        kw["clock"] = lambda: utc_now() + timedelta(seconds=state["offset"])
        super().__init__(*a, **kw)


class Wire(base.Wire):
    def __init__(self, app, out):
        global wire_instance
        super().__init__(app, out)
        wire_instance = self
        self.trace = (out / "requests.jsonl").open("x", buffering=1)
        base.write(out / "generation-counters.json", generation.snapshot())
        generation.close()
        mode(False)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await super().__call__(scope, receive, send)
        if state["started"] >= 16000:
            raise RuntimeError("P03 request guard")
        state["started"] += 1
        serial = state["started"]
        label = state["label"]
        enabled = state["enabled"]
        stage = "transfer" if scope["path"].endswith("/objects") else "observation"
        c = cost.Collector()
        before = dict(self.counts)
        start = time.perf_counter_ns()
        cpu = time.process_time_ns()
        status = None

        async def sent(m):
            nonlocal status
            if m["type"] == "http.response.start":
                status = m["status"]
            await send(m)

        try:
            if enabled:
                with c.stage(stage):
                    await super().__call__(scope, receive, sent)
            else:
                await super().__call__(scope, receive, sent)
        finally:
            end = time.perf_counter_ns()
            cpu_ns = time.process_time_ns() - cpu

            def finish(completed):
                with lock:
                    if enabled:
                        total.merge(completed)
                        if label not in groups:
                            if len(groups) >= 32:
                                raise RuntimeError("P03 group bound")
                            groups[label] = cost.Collector()
                        groups[label].merge(completed)
                    row = {
                        "serial": serial,
                        "label": label,
                        "enabled": enabled,
                        "path": scope["path"],
                        "status": status,
                        "start_ns": start,
                        "end_ns": end,
                        "wall_ns": end - start,
                        "cpu_ns": cpu_ns,
                        "pending": completed.pending,
                        "wire": {
                            k: v - before.get(k, 0)
                            for k, v in self.counts.items()
                            if v - before.get(k, 0)
                        },
                        "rss_peak_kib": resource.getrusage(
                            resource.RUSAGE_SELF
                        ).ru_maxrss,
                    }
                    if scope["path"].endswith("/observations") and status in (200, 201):
                        row["manifest"] = self.last_manifest
                    self.trace.write(json.dumps(row, separators=(",", ":")) + "\n")
                    completed.close()
                    state["completed"] += 1
                    lock.notify_all()

            c.finish_when_idle(finish)


class Commands:
    def __iter__(self):
        for line in sys.__stdin__:
            req = json.loads(line)
            cmd = req["command"]
            if cmd.startswith("p03_"):
                with lock:
                    if not lock.wait_for(
                        lambda: state["started"] == state["completed"], timeout=15
                    ):
                        raise RuntimeError("pending native cohort")
                if cmd == "p03_mode":
                    mode(bool(req["enabled"]))
                    state["label"] = req["label"]
                    reply = {"enabled": state["enabled"], "label": state["label"]}
                elif cmd == "p03_advance":
                    state["offset"] += 901
                    reply = {
                        "offset_seconds": state["offset"],
                        "ttl_seconds": 900,
                        "real_costs": True,
                        "simulated": "clock only +901 seconds; no CPU/network/persistence skipped",
                    }
                elif cmd == "p03_snapshot":
                    reply = {
                        "started": state["started"],
                        "completed": state["completed"],
                        "pending": total.pending,
                        "complete": state["started"] == state["completed"],
                        "generation": generation.snapshot(),
                        "counters": total.snapshot(),
                        "groups": {k: v.snapshot() for k, v in groups.items()},
                        "rss_peak_kib": resource.getrusage(
                            resource.RUSAGE_SELF
                        ).ru_maxrss,
                    }
                else:
                    raise ValueError(cmd)
                print(json.dumps(reply), flush=True)
            else:
                yield line


if __name__ == "__main__":
    with (
        patch.object(base, "Wire", Wire),
        patch.object(base, "RetentionRepository", Repository),
        patch.object(FinalizationSandbox, "bootstrap", bootstrap),
        patch.object(sys, "stdin", Commands()),
    ):
        try:
            base.main()
        finally:
            if stack:
                stack.close()

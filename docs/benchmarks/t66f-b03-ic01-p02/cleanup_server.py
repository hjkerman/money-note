"""P01 원 exit fence를 유지하며 TLS 종료 대기 원인만 관측한다."""

import asyncio
import importlib.util
from pathlib import Path
import threading
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "p02_cleanup_base", HERE.parent / "t66f-b03-ic01-p01/packet_server.py"
)
p01 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p01)
base = p01.base
original_server = base.uvicorn.Server
original_join = threading.Thread.join
observed = None


def await_chain(coroutine):
    chain = []
    while coroutine is not None and len(chain) < 16:
        chain.append(str(coroutine))
        coroutine = getattr(
            coroutine, "cr_await", getattr(coroutine, "gi_yieldfrom", None)
        )
    return chain


class ObservedServer(original_server):
    async def shutdown(self, sockets=None):
        global observed
        observed = self
        self.measure_loop = asyncio.get_running_loop()
        self.measure_transports = [c.transport for c in self.server_state.connections]
        self.measure_stage = "shutdown"
        try:
            return await super().shutdown(sockets)
        finally:
            self.measure_stage = "shutdown_done"

    async def _wait_tasks_to_complete(self):
        self.measure_stage = "wait_tasks_and_server_wait_closed"
        try:
            return await super()._wait_tasks_to_complete()
        finally:
            self.measure_stage = "wait_done"


def join(thread, timeout=None):
    target = getattr(thread, "_target", None)
    is_server = isinstance(getattr(target, "__self__", None), ObservedServer)
    result = original_join(thread, timeout)
    if not is_server:
        return result
    data = {
        "worker_alive_after_original_join": thread.is_alive(),
        "join_timeout": timeout,
    }
    event = threading.Event()

    def capture():
        try:
            data.update(
                stage=observed.measure_stage,
                request_tasks=len(observed.server_state.tasks),
                connections=len(observed.server_state.connections),
                loop_tasks=[
                    {
                        "name": t.get_name(),
                        "coroutine": str(t.get_coro()),
                        "await_chain": await_chain(t.get_coro()),
                        "stack": [
                            f"{f.f_code.co_filename}:{f.f_lineno}:{f.f_code.co_name}"
                            for f in t.get_stack()
                        ],
                    }
                    for t in asyncio.all_tasks(observed.measure_loop)
                ],
                transports=[
                    {
                        "class": type(t).__name__,
                        "closing": t.is_closing(),
                        "ssl_state": str(
                            getattr(getattr(t, "_ssl_protocol", None), "_state", None)
                        ),
                    }
                    for t in observed.measure_transports
                ],
                servers=[repr(s) for s in observed.servers],
            )
        finally:
            event.set()

    if thread.is_alive():
        observed.measure_loop.call_soon_threadsafe(capture)
        assert event.wait(2), "event-loop diagnostic callback did not run"
    else:
        data["stage"] = getattr(observed, "measure_stage", None)
    base.write(Path(sys.argv[2]) / "shutdown-state.json", data)
    return result


if __name__ == "__main__":
    with (
        patch.object(base, "Wire", p01.MeasuredWire),
        patch.object(sys, "stdin", p01.Commands()),
        patch.object(base.uvicorn, "Server", ObservedServer),
        patch.object(threading.Thread, "join", join),
    ):
        try:
            base.main()
        finally:
            if p01.stack is not None:
                p01.stack.close()

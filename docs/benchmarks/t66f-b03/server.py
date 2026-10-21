"""기존 Phase B TLS fixture 위의 test-only 계측. 새 endpoint/financial engine 없음."""

from contextlib import ExitStack
import asyncio
import functools
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import patch
from types import SimpleNamespace
from threading import Condition

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "backend"), str(Path(__file__).resolve().parent)]
spec = importlib.util.spec_from_file_location(
    "b03_original_tls", ROOT / "docs/benchmarks/t66f-phase-b/server.py"
)
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)

from counters import (  # noqa: E402
    Collector,
    NATIVE_HASH,
    add,
    authentication_hashes,
    instrument,
    instrument_connections,
    instrument_workers,
)
from isolated_sync.finalization import FinalizationSandbox  # noqa: E402


def main():
    collector = Collector()
    requests = []  # 명시적으로 제한한 요청 표본. object별 trace가 아니다.
    sample_lock = Condition()
    completed_requests = 0
    request_count = 0
    pair = asyncio.Event()
    pair_entered = 0
    wire = original.Wire

    class ObservedWire(wire):
        async def __call__(self, scope, receive, send):
            nonlocal request_count, pair_entered
            if scope["type"] != "http":
                return await super().__call__(scope, receive, send)
            stage = "transfer" if scope["path"].endswith("/objects") else "observation"
            local = Collector()
            with sample_lock:
                request_count += 1
                number = request_count
            status = None

            async def observed_send(message):
                nonlocal status
                if message["type"] == "http.response.start":
                    status = message["status"]
                await send(message)

            try:
                with local.stage(stage):
                    if dict(scope.get("headers", [])).get(b"x-b03-barrier") == b"pair":
                        pair_entered += 1
                        if pair_entered == 2:
                            pair.set()
                        await asyncio.wait_for(pair.wait(), timeout=10)
                    return await super().__call__(scope, receive, observed_send)
            finally:

                def finished(measurement):
                    nonlocal completed_requests
                    with sample_lock:
                        collector.merge(measurement)
                        completed_requests += 1
                        if len(requests) < 16:
                            requests.append(
                                dict(
                                    request=number,
                                    stage=stage,
                                    status=status,
                                    counters=measurement.snapshot(),
                                )
                            )
                        sample_lock.notify_all()

                local.finish_when_idle(finished)

    bootstrap = FinalizationSandbox.bootstrap
    session_hash = original.auth._hash_session_token
    create_app = original.create_app

    def observed_app(*args, **kwargs):
        def metrics(value):
            for key in (
                "object_reads",
                "object_bytes_read",
                "prefix_cache_hits",
                "prefix_validations",
                "path_edges",
                "decoded_bytes",
                "response_bytes",
            ):
                if key in value:
                    add("existing_d3", key, value[key])

        return create_app(*args, **kwargs, metrics=metrics)

    @functools.wraps(bootstrap)
    def observed_bootstrap(self):
        with collector.stage("generation"):
            return bootstrap(self)

    native_input = sys.stdin

    @functools.wraps(session_hash)
    def observed_session_hash(token):
        with authentication_hashes():
            return session_hash(token)

    class Commands:
        def __iter__(self):
            for line in native_input:
                request = json.loads(line)
                if request["command"] == "cost":
                    # Diagnostic cohort only: do not stamp a partially merged
                    # request as complete, or drop a cancelled native tail.
                    after = request.get("after_requests", 0)
                    with sample_lock:
                        if not sample_lock.wait_for(
                            lambda: (
                                request_count >= after
                                and completed_requests == request_count
                            ),
                            timeout=30,
                        ):
                            raise RuntimeError("B03 measurement cohort is incomplete")
                        value = {
                            "schema_version": 1,
                            "measurement_complete": True,
                            "counters": collector.snapshot(),
                            "request_count": request_count,
                            "completed_requests": completed_requests,
                            "request_samples": list(requests),
                            "request_sample_capacity": 16,
                        }
                    print(json.dumps(value), flush=True)
                    continue
                stage = "generation" if request["command"] == "mutate" else "setup"
                with collector.stage(stage):
                    yield line

    with ExitStack() as stack:
        stack.enter_context(instrument())
        stack.enter_context(instrument_connections())
        stack.enter_context(instrument_workers())
        stack.enter_context(patch.object(original, "Wire", ObservedWire))
        stack.enter_context(patch.object(original, "create_app", observed_app))
        stack.enter_context(
            patch.object(original.auth, "_hash_session_token", observed_session_hash)
        )
        # Existing independent response SHA is an oracle, not backend product work.
        stack.enter_context(
            patch.object(original, "hashlib", SimpleNamespace(sha256=NATIVE_HASH))
        )
        stack.enter_context(
            patch.object(FinalizationSandbox, "bootstrap", observed_bootstrap)
        )
        stack.enter_context(patch.object(sys, "stdin", Commands()))
        stack.enter_context(collector.stage("setup"))
        original.main()


if __name__ == "__main__":
    main()

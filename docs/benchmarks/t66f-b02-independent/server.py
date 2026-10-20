"""원 fixed-H/실제 TLS backend. 독립 oracle와 유한 wire/SQL 계측만 추가한다."""

from collections import Counter
from contextvars import ContextVar
import base64
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import oracle  # noqa: E402 — fixture 경로를 먼저 고정한다.

spec = importlib.util.spec_from_file_location(
    "audit_synthetic_server", ROOT / "docs/benchmarks/t66f-b02-implementation/server.py"
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.oracle.walk = oracle.walk
from isolated_sync.retention_schema import RetentionConnection  # noqa: E402 — fixture가 backend 경로를 설정한다.

CURRENT = ContextVar("audit_request", default=None)
original = RetentionConnection.execute


def execute(self, sql, *args, **kwargs):
    row = CURRENT.get()
    if row is not None:
        row["sql"][str(sql).lstrip().split()[0].upper()] += 1
    return original(self, sql, *args, **kwargs)


RetentionConnection.execute = execute


class Wire(base.Wire):
    def __init__(self, app, out):
        super().__init__(app, out)
        self.rows = (out / "requests.jsonl").open("w", buffering=1)
        self.hashes = set()
        self.observed = {}
        self.serial = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        self.serial += 1
        row = {
            "serial": self.serial,
            "method": scope["method"],
            "path": scope["path"],
            "start_ns": time.perf_counter_ns(),
            "start_utc": time.time(),
            "sql": Counter(),
        }
        token = CURRENT.set(row)
        messages = []
        request_bytes = 0

        async def recv():
            nonlocal request_bytes
            m = await receive()
            request_bytes += len(m.get("body", b""))
            return m

        async def capture(m):
            messages.append(m)

        try:
            await self.app(scope, recv, capture)
            row["handler_end_ns"] = time.perf_counter_ns()
            status = next(
                m["status"] for m in messages if m["type"] == "http.response.start"
            )
            raw = b"".join(m.get("body", b"") for m in messages)
            row.update(
                status=status, request_bytes=request_bytes, response_bytes=len(raw)
            )
            self.counts.update(
                requests=1,
                request_entity_bytes=request_bytes,
                response_entity_bytes=len(raw),
            )
            self.counts[f"status_{status}"] += 1
            if scope["path"].endswith("/objects"):
                self.counts["object_requests"] += 1
                if status == 200:
                    chunks = json.loads(raw)["chunks"]
                    row["chunks"] = len(chunks)
                    row["decoded_bytes"] = 0
                    row["new_global_hashes"] = 0
                    for chunk in chunks:
                        value = base64.b64decode(chunk["data_base64"], validate=True)
                        ref = chunk["ref"]
                        assert len(value) == chunk["length"]
                        # Mandatory grid has no oversized/chunked objects.
                        assert chunk["offset"] == "0" and len(value) == int(
                            ref["bytes"]
                        )
                        parsed = json.loads(value)
                        assert oracle.encode(parsed) == value
                        assert (
                            hashlib.sha256(
                                b"money-note.sync.v1/"
                                + parsed["kind"].encode()
                                + b"\0"
                                + value
                            ).hexdigest()
                            == ref["hash"]
                        )
                        row["decoded_bytes"] += len(value)
                        row["new_global_hashes"] += ref["hash"] not in self.hashes
                        self.hashes.add(ref["hash"])
                    self.counts.update(
                        chunks=len(chunks),
                        decoded_object_bytes=row["decoded_bytes"],
                        independent_wire_hash_checks=len(chunks),
                    )
                    row["unique_global_objects"] = len(self.hashes)
            elif (
                scope["method"] == "POST"
                and scope["path"].endswith("/observations")
                and status in (200, 201)
            ):
                self.counts["observation_requests"] += 1
                self.last_manifest = json.loads(raw)
                row["manifest"] = self.last_manifest
                base.write(self.out / "last-http-manifest.json", self.last_manifest)
            elif scope["method"] == "DELETE":
                self.counts["release_requests"] += 1
            if status >= 400:
                row["error"] = json.loads(raw)
                self.failures.append(
                    {"status": status, "body": row["error"], "path": scope["path"]}
                )
                base.write(self.out / "http-failures.json", self.failures)
            row["end_ns"] = time.perf_counter_ns()
            self.rows.write(json.dumps(row, separators=(",", ":")) + "\n")
            if self.counts["requests"] % 100 == 0:
                base.write(self.out / "wire-progress.json", dict(self.counts))
            for m in messages:
                await send(m)
        finally:
            CURRENT.reset(token)


base.Wire = Wire
if __name__ == "__main__":
    base.main()

"""이전 실제 TLS handler를 보존하고 새 응답 fault만 test-only로 주입한다."""

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "prior_real_server", HERE.parent / "t66f-phase-b/server.py"
)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
original = prior.Wire.__call__
MODES = {
    "dataset",
    "canon",
    "base_echo",
    "context",
    "ref_size",
    "base64",
    "chunk_length",
    "duplicate_chunk",
    "content_type",
    "unexpected_status",
    "missing_descendant",
}


async def observe(self, scope, receive, send):
    if (
        scope["type"] != "http"
        or not self.fault
        or self.fault[0] not in MODES
        or self.fault[1] not in scope["path"]
        or scope["method"] != "POST"
    ):
        return await original(self, scope, receive, send)
    mode, _ = self.fault
    self.fault = None
    messages = []

    async def capture(message):
        messages.append(message)

    await original(self, scope, receive, capture)
    start = next(m for m in messages if m["type"] == "http.response.start")
    body = json.loads(
        b"".join(
            m.get("body", b"") for m in messages if m["type"] == "http.response.body"
        )
    )
    if mode == "dataset":
        body["target"]["ns"]["dataset_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    elif mode == "canon":
        body["target"]["versions"]["canon"] = 9
    elif mode == "base_echo":
        body["base_sync_root"] = "e" * 64
    elif mode == "context":
        body["target"]["context"]["evaluation_date"] = "2026-02-30"
    elif mode == "ref_size":
        body["target"]["index_ref"]["bytes"] = "1"
    elif mode == "base64":
        body["chunks"][0]["data_base64"] = "@@=="
    elif mode == "chunk_length":
        body["chunks"][0]["length"] += 1
    elif mode == "duplicate_chunk":
        body["chunks"].append(body["chunks"][0])
    elif mode == "missing_descendant":
        body["chunks"] = []
    elif mode == "content_type":
        start["headers"] = [
            (k, v) for k, v in start["headers"] if k != b"content-type"
        ] + [(b"content-type", b"text/html")]
    elif mode == "unexpected_status":
        start["status"] = 206
    else:
        raise AssertionError(mode)
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    start["headers"] = [
        (k, v) for k, v in start["headers"] if k != b"content-length"
    ] + [(b"content-length", str(len(raw)).encode())]
    self.records[-1].update(
        injected=mode,
        mutated_status=start["status"],
        mutated_bytes=len(raw),
        mutated_headers={k.decode(): v.decode() for k, v in start["headers"]},
        mutated_sha256=__import__("hashlib").sha256(raw).hexdigest(),
    )
    await send(start)
    await send(dict(type="http.response.body", body=raw))


prior.Wire.__call__ = observe
if __name__ == "__main__":
    prior.main()

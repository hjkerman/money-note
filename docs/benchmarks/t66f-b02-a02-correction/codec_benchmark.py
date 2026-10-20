"""동일 관측/요청/bytes에서 역사 codec 대 새 codec. 실제 ASGI, TLS 제외."""

from contextlib import ExitStack
import base64
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
import types
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "backend"), str(HERE.parent / "t66f-b02-a02")]
import request_cost as rc  # noqa: E402
from isolated_sync import canonical  # noqa: E402


def main():
    previous = types.ModuleType("_a02_codec_before")
    sys.modules[previous.__name__] = previous
    exec(
        compile(
            gzip.decompress((HERE / "canonical.py.before.gz").read_bytes()),
            "canonical.py.before",
            "exec",
        ),
        previous.__dict__,
    )
    rows = []
    with (
        rc.RetentionSandbox() as db,
        patch("app.services.judgment.common._MESSAGE_RANDOM.randrange", return_value=0),
    ):
        with db.connect() as c:
            rc.seed(c, 1000)
            c.execute(
                "INSERT INTO users(id,username,password_hash) VALUES(1,'a02-synthetic','unused')"
            )
            c.execute(
                "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES(1,?,'2026-12-31T00:00:00Z')",
                (rc.auth._hash_session_token(rc.TOKEN_A),),
            )
        db.install()
        db.bootstrap()
        repo = rc.RetentionRepository(
            db,
            clock=lambda: rc.observation.datetime(
                2026, 10, 5, tzinfo=rc.observation.timezone.utc
            ),
            evaluation=lambda: rc.observation.Evaluation(rc.date(2026, 10, 5), 540),
        )
        meter = rc.Meter(rc.http.create_app(repo))
        with rc.TestClient(meter) as client:
            manifest = rc.observe(client).json()
            graph = rc.graph(db, manifest)
            leaves = [v for v in graph.values() if v[3]["kind"] == "index-leaf"]
            for shape in ("shared", "spread"):
                chosen = (
                    leaves[:64]
                    if shape == "shared"
                    else [leaves[i * len(leaves) // 64] for i in range(64)]
                )
                packet = dict(
                    protocol=1,
                    request_id=str(uuid4()),
                    items=[
                        dict(path=p, offset="0", length=len(raw))
                        for _, p, raw, _ in chosen
                    ],
                )
                url = rc.URL + "/" + manifest["observation_id"] + "/objects"
                expected = None
                for iteration in range(4):
                    for mode in ("before", "after"):
                        counts = {
                            "encode_calls": 0,
                            "encoded_output_bytes": 0,
                            "sql": 0,
                        }
                        with ExitStack() as stack:
                            if mode == "before":
                                original_decode = canonical.decode_c1
                                for module in list(sys.modules.values()):
                                    if module and getattr(
                                        module, "__name__", ""
                                    ).startswith("isolated_sync"):
                                        for name, fn in list(vars(module).items()):
                                            if fn is original_decode:
                                                stack.enter_context(
                                                    patch.object(
                                                        module, name, previous.decode_c1
                                                    )
                                                )
                            for codec in (canonical, previous):
                                original = codec.encode

                                def encode(value, fn=original):
                                    raw = fn(value)
                                    counts["encode_calls"] += 1
                                    counts["encoded_output_bytes"] += len(raw)
                                    return raw

                                stack.enter_context(
                                    patch.object(codec, "encode", encode)
                                )
                            original_sql = (
                                rc.retention_schema.RetentionConnection.execute
                            )

                            def execute(self, *a, **kw):
                                counts["sql"] += 1
                                return original_sql(self, *a, **kw)

                            stack.enter_context(
                                patch.object(
                                    rc.retention_schema.RetentionConnection,
                                    "execute",
                                    execute,
                                )
                            )
                            start = time.perf_counter()
                            response = client.post(
                                url, json=packet, headers=rc.headers()
                            )
                            elapsed = time.perf_counter() - start
                        assert response.status_code == 200, response.text[:100]
                        assert [
                            base64.b64decode(v["data_base64"])
                            for v in response.json()["chunks"]
                        ] == [v[2] for v in chosen]
                        if expected is None:
                            expected = response.content
                        assert response.content == expected, (
                            "exact HTTP entity equivalence"
                        )
                        if iteration:
                            rows.append(
                                dict(
                                    mode=mode,
                                    shape=shape,
                                    seconds=elapsed,
                                    handler_ns=meter.rows[-1]["wall_ns"],
                                    response_sha256=hashlib.sha256(
                                        response.content
                                    ).hexdigest(),
                                    **counts,
                                )
                            )
    (HERE / "codec-benchmark.json").write_text(
        json.dumps(
            dict(
                scope="same request/observation ASGI auth+SQLite; TCP/TLS excluded; counters are test instrumentation",
                rows=rows,
            ),
            indent=2,
        )
        + "\n"
    )
    print("PASS exact response equivalence", len(rows), "measured requests")


if __name__ == "__main__":
    main()

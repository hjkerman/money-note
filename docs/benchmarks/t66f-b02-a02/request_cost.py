# ruff: noqa: E402
"""실제 retention/auth/HTTP/typed resolver 소형 실험. product bytes 변경 없음.
ASGI TestClient이므로 TCP/TLS 전송은 제외된다. profiler 결과는 비용 순위용이다.
"""

from collections import Counter
from contextvars import ContextVar
from contextlib import ExitStack
from datetime import date
from functools import wraps
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
import base64
import cProfile
import json
import pstats
import sys
import time
import resource

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts/benchmarks")]
from fastapi.testclient import TestClient
from app import auth
from isolated_sync import observation, retention_schema, transfer, http
from isolated_sync.retention import RetentionRepository
from isolated_sync.retention_schema import RetentionSandbox
from tests.test_isolated_sync_transfer import graph, headers, observe, URL, TOKEN_A
from t66d2b_writers import seed

CURRENT = ContextVar("a02_record", default=None)
COUNT_CHOICES = [1, 8, 32, 64]
TRACED_CHOICES = [False, True, False, True]


class Meter:
    def __init__(self, app):
        self.app = app
        self.enabled = True
        self.rows = []

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.enabled:
            return await self.app(scope, receive, send)
        row = {"ns": Counter(), "cpu_ns": Counter(), "calls": Counter()}
        token = CURRENT.set(row)
        t = time.perf_counter_ns()
        try:
            return await self.app(scope, receive, send)
        finally:
            row["wall_ns"] = time.perf_counter_ns() - t
            self.rows.append(row)
            CURRENT.reset(token)


def instrument(stack, owner, name):
    original = getattr(owner, name)

    @wraps(original)
    def wrap(*a, **k):
        row = CURRENT.get()
        if row is None:
            return original(*a, **k)
        t, c = time.perf_counter_ns(), time.thread_time_ns()
        try:
            return original(*a, **k)
        finally:
            label = f"{owner.__name__}.{name}"
            row["ns"][label] += time.perf_counter_ns() - t
            row["cpu_ns"][label] += time.thread_time_ns() - c
            row["calls"][label] += 1

    stack.enter_context(patch.object(owner, name, wrap))


def run(n):
    with (
        RetentionSandbox() as db,
        patch("app.services.judgment.common._MESSAGE_RANDOM.randrange", return_value=0),
    ):
        with db.connect() as c:
            seed(c, n)
            c.execute(
                "INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order,is_primary_income) VALUES (101,'2026-10-05','fixed-width-cash',-50,2,0)"
            )
            c.execute(
                "INSERT INTO users(id,username,password_hash) VALUES(1,'a02-synthetic','unused')"
            )
            c.execute(
                "INSERT INTO auth_sessions(user_id,session_token_hash,expires_at) VALUES(1,?,'2026-12-31T00:00:00Z')",
                (auth._hash_session_token(TOKEN_A),),
            )
        db.install()
        db.bootstrap()
        repo = RetentionRepository(
            db,
            clock=lambda: observation.datetime(
                2026, 10, 5, tzinfo=observation.timezone.utc
            ),
            evaluation=lambda: observation.Evaluation(date(2026, 10, 5), 540),
        )
        metrics = []
        meter = Meter(http.create_app(repo, metrics=metrics.append))
        client = TestClient(meter)
        m = observe(client).json()
        g = graph(db, m)
        leaves = [x for x in g.values() if x[3]["kind"] == "index-leaf"]
        results = []
        for shape in ["shared", "spread"]:
            candidates = (
                leaves[:64]
                if shape == "shared"
                else [leaves[i * len(leaves) // 64] for i in range(64)]
            )
            for count in COUNT_CHOICES:
                chosen = candidates[:count]
                packet = dict(
                    protocol=1,
                    request_id=str(uuid4()),
                    items=[
                        dict(path=p, offset="0", length=len(raw))
                        for _, p, raw, _ in chosen
                    ],
                )
                url = URL + "/" + m["observation_id"] + "/objects"
                # First warmup excluded; alternating uninstrumented and instrumented path.
                assert (
                    client.post(url, json=packet, headers=headers()).status_code == 200
                )
                for traced in TRACED_CHOICES:
                    meter.enabled = traced
                    t = time.perf_counter()
                    response = client.post(url, json=packet, headers=headers())
                    wall = time.perf_counter() - t
                    assert response.status_code == 200, response.text[:100]
                    assert [
                        base64.b64decode(x["data_base64"])
                        for x in response.json()["chunks"]
                    ] == [v[2] for v in chosen]
                    results.append(
                        dict(
                            n=n,
                            graph_objects=len(g),
                            shape=shape,
                            count=count,
                            path_edges=sum(len(v[1]) - 1 for v in chosen),
                            canonical_bytes=sum(len(v[2]) for v in chosen),
                            instrumented=traced,
                            wall_s=wall,
                            metrics=dict(metrics[-1]),
                            trace=meter.rows[-1] if traced else None,
                        )
                    )
        # Native CPU cProfile includes auth + prepare + final terminal at real calls.
        profile = cProfile.Profile()
        original_prepare = http.Adapter.prepare
        original_terminal = http.Adapter.terminal

        def profiled(fn):
            def wrapped(*a, **k):
                profile.enable()
                try:
                    return fn(*a, **k)
                finally:
                    profile.disable()

            return wrapped

        with (
            patch.object(http.Adapter, "prepare", profiled(original_prepare)),
            patch.object(http.Adapter, "terminal", profiled(original_terminal)),
        ):
            meter.enabled = False
            r = client.post(url, json=packet, headers=headers())
            assert r.status_code == 200
        stat = pstats.Stats(profile)
        top = [
            {
                "function": f"{key[0]}:{key[1]}:{key[2]}",
                "primitive": v[0],
                "calls": v[1],
                "self_s": v[2],
                "cumulative_s": v[3],
            }
            for key, v in sorted(stat.stats.items(), key=lambda x: -x[1][3])[:65]
        ]
        # Real HTTP failure followed by valid recovery; no policy alteration.
        bad = dict(packet, items=[dict(packet["items"][0], path=["0" * 64])])
        assert client.post(url, json=bad, headers=headers()).status_code == 422
        assert client.post(url, json=packet, headers=headers()).status_code == 200
        return {
            "n": n,
            "graph_objects": len(g),
            "db_bytes": db.path.stat().st_size,
            "rows": results,
            "profile_top": top,
            "profile_total_s": stat.total_tt,
            "failure_then_valid": "PASS",
        }


def main():
    with ExitStack() as stack:
        for owner, names in [
            (http.Adapter, ["credential", "prepare", "terminal"]),
            (
                observation.ObservationRepository,
                ["_lookup", "_guard", "_check_lease", "_view_object"],
            ),
            (observation, ["versions"]),
            (retention_schema.RetentionSandbox, ["connect"]),
            (transfer.PathResolver, ["resolve", "validate"]),
        ]:
            for name in names:
                instrument(stack, owner, name)
        original = retention_schema.RetentionConnection.execute

        def execute(self, sql, *a, **k):
            r = CURRENT.get()
            if r is not None:
                r["calls"]["SQL." + str(sql).lstrip().split()[0].upper()] += 1
            return original(self, sql, *a, **k)

        stack.enter_context(
            patch.object(retention_schema.RetentionConnection, "execute", execute)
        )
        results = [run(n) for n in [1000, 5000]]
    (HERE / "request-cost.json").write_text(
        json.dumps(
            {
                "scope": "실제 retention ASGI/auth/typed path; TCP/TLS 및 client E1/E2 제외",
                "clock": "perf_counter_ns/thread_time_ns",
                "results": results,
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(
        "PASS request scenarios",
        sum(len(x["rows"]) for x in results),
        "fixtures",
        len(results),
    )


if __name__ == "__main__":
    main()

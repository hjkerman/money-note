"""실제 서버 객체와 별도 hashlib/C1 oracle로 합성 감사 corpus를 생성한다."""

import base64
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "docs/benchmarks/t66d3c-audit"))
from test_audit import seed, CRED  # noqa: E402
from isolated_sync.observation import Evaluation, ObservationRepository, versions  # noqa: E402
from isolated_sync.observation_schema import ObservationSandbox  # noqa: E402
from isolated_sync.canonical import Context, Namespace, encode  # noqa: E402
from isolated_sync.patricia import Index  # noqa: E402
from isolated_sync.raw import Row  # noqa: E402
from isolated_sync.segments import leaf  # noqa: E402


def c1(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def digest(kind, raw):
    return hashlib.sha256(b"money-note.sync.v1/" + kind.encode("ascii") + b"\0" + raw).hexdigest()


def obj(kind, raw, **metadata):
    assert raw == c1(json.loads(raw))
    return dict(kind=kind, ref=dict(hash=digest(kind, raw), bytes=str(len(raw))),
                data_base64=base64.b64encode(raw).decode(), **metadata)


def main():
    now = datetime(2026, 10, 12, tzinfo=timezone.utc)
    with ObservationSandbox() as db:
        with db.connect() as conn:
            seed(conn, history=257)
        db.install()
        db.bootstrap()
        repo = ObservationRepository(db, clock=lambda: now,
             evaluation=lambda: Evaluation(date(2026, 10, 12), 540))
        manifest = repo.create(CRED, guard=lambda: CRED, request_id=str(uuid4()), inline_bytes=0)
        context = Context(Namespace(**manifest["target"]["ns"]), versions()["raw_schema"])
        stored = []
        with db.connect() as conn:
            for row in conn.execute("SELECT hash,kind,body FROM sync_objects ORDER BY kind,hash"):
                if row["kind"] == "row":
                    continue
                if row["kind"].startswith("index-") and sum(o["kind"] == row["kind"] for o in stored) >= 5:
                    continue
                value = obj(row["kind"], row["body"], source="actual persisted server object")
                assert value["ref"]["hash"] == row["hash"]
                stored.append(value)
        empty = Index.build(context).root.object
        stored.append(obj(empty.kind, empty.raw, source="actual server Index.build"))
        settings = []
        for index, text in enumerate([" -000000.00 ", "+9007199254740991.0000", "-9007199254740991", "\x1c+0001\x1c", "\x1d-0001\x1d", "\x1e0.00\x1e", "\x1f1000\x1f", "\x851000\x85", "\u00a01000\u00a0", "\u20031000\u2003", "\u30001000\u3000"]):
            admitted = Row.make("app_settings", dict(key="scheduled_income", value=text, updated_at="synthetic"))
            node = leaf(context, "app_settings", [admitted]).object
            settings.append(obj(node.kind, node.raw, label="setting-"+str(index), money_string=text,
                                source="server Row.make and segments.leaf accepted"))
        unicode_rows = []
        for index, text in enumerate(["é", "e\u0301", "\U0001f600\x00\x08\x0c", "\U0010ffff\ufeff\u2028", "", "한글/a\\b\"c"]):
            admitted = Row.make("app_labels", dict(key=text, value=text, updated_at="synthetic"))
            node = leaf(context, "app_labels", [admitted]).object
            unicode_rows.append(obj(node.kind, node.raw, label="unicode-"+str(index), source="server Row.make and segments.leaf"))
    rng = random.Random(6601)
    scalars = [None, True, False, 0, -(1 << 63), (1 << 63)-1, -0.0, 0.0, 9007199254740991.0, "", "é", "e\u0301", "한글\x00😀\uffff", "\U00010000"]
    vectors = []
    for trial in range(128):
        value = {"trial": trial, "\U00010000": rng.choice(scalars), "\uffff": rng.choice(scalars),
                 "nested": [rng.choice(scalars), {"\"\\\n": rng.choice(scalars)}]}
        raw = encode(value)
        assert raw == c1(value)
        vectors.append(dict(raw=base64.b64encode(raw).decode(), canonical=True,
                            expected=base64.b64encode(raw).decode(), hash=digest("view", raw)))
    result = dict(manifest_base64=base64.b64encode(encode(manifest)).decode(), objects=stored,
                  settings=settings, unicode_objects=unicode_rows, vectors=vectors)
    destination = Path(__file__).parent / "server-fixture.json"
    destination.write_text(json.dumps(result, ensure_ascii=True, indent=2)+"\n")


if __name__ == "__main__":
    main()

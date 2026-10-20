"""실행 중인 자가 소유 합성 DB에서 작은 read-only 부표본만 수집.

전체 graph 복사나 E1 preload가 아니다. 이후 component 계측 전용으로 보존한다.
"""

import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import time

HERE = Path(__file__).resolve().parent
OUT = Path(json.loads((HERE / "active-run.json").read_text())["out"])
manifest = json.loads((OUT / "server/manifest-1.json").read_text())
pids = []
for p in Path("/proc").glob("[0-9]*"):
    try:
        cmd = (p / "cmdline").read_bytes().split(b"\0")
        if any(
            c.decode(errors="replace").endswith("/t66f-b02-a01/server.py") for c in cmd
        ):
            pids.append(p)
    except OSError:
        pass
assert len(pids) == 1, pids
paths = set()
for fd in (pids[0] / "fd").iterdir():
    try:
        p = fd.resolve()
        if p.is_file() and p.suffix in (".sqlite", ".sqlite3", ".db"):
            paths.add(p)
    except OSError:
        pass
assert len(paths) == 1, paths
start = time.monotonic()
conn = sqlite3.connect(f"file:{next(iter(paths))}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
objects = {}
paths64 = []


def read(ref):
    h = ref["hash"]
    if h not in objects:
        row = conn.execute(
            "SELECT kind,body FROM sync_objects WHERE hash=?", (h,)
        ).fetchone()
        raw = bytes(row["body"])
        kind = row["kind"]
        # Independent hashlib / JSON oracle; no product canonical decoder here.
        assert (
            hashlib.sha256(f"money-note.sync.v1/{kind}\0".encode() + raw).hexdigest()
            == h
        )
        assert len(raw) == int(ref["bytes"])
        body = json.loads(raw)
        assert body["ns"] == manifest["target"]["ns"]
        objects[h] = dict(
            ref=ref, kind=kind, bytes_base64=base64.b64encode(raw).decode(), body=body
        )
    return objects[h]["body"]


def walk(ref, path):
    if len(paths64) >= 64:
        return
    body = read(ref)
    if body["kind"] == "index-root":
        children = [body["facts"]]
    elif body["kind"] == "index-node":
        children = [body["left"], body["right"]]
    elif body["kind"] == "index-leaf":
        paths64.append(path)
        return
    else:
        raise AssertionError(body["kind"])
    for child in children:
        walk(child, path + [child["hash"]])


walk(manifest["target"]["index_ref"], [manifest["target"]["index_ref"]["hash"]])
conn.close()
assert len(paths64) == 64
value = dict(
    label="READ-ONLY SMALL COMPONENT SAMPLE, NOT D-E INTEGRATION",
    manifest=manifest,
    origin=json.loads((OUT / "result.json").read_text())["origin"],
    paths=paths64,
    objects=[{k: v for k, v in o.items() if k != "body"} for o in objects.values()],
    extraction_seconds=time.monotonic() - start,
    unique_objects=len(objects),
    logical_object_bytes=sum(int(o["ref"]["bytes"]) for o in objects.values()),
    repeated_path_objects=sum(map(len, paths64)),
)
(OUT / "component-sample.json").write_text(json.dumps(value, indent=2) + "\n")
print(
    json.dumps(
        {
            k: value[k]
            for k in [
                "label",
                "extraction_seconds",
                "unique_objects",
                "logical_object_bytes",
                "repeated_path_objects",
            ]
        }
    )
)

"""해당 감사 grid PID의 새 임시 DB만 독립 exact-byte/closure 관찰한다."""

from collections import Counter
from contextlib import closing
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time

ROOT = Path(__file__).resolve().parents[3]


def children(body):
    kind = body["kind"]
    if kind == "raw-root":
        return [t["root"]["ref"] for t in body["tables"]]
    if kind == "snapshot-node":
        return [c["ref"] for c in body["children"]]
    if kind == "index-root":
        return [body["facts"]]
    if kind == "index-node":
        return [body["left"], body["right"]]
    return []


def run(pid, out):
    command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    assert any(b"t66f-phase-b-continuation/grid.py" in a for a in command), command
    paths = set()
    for f in Path(f"/proc/{pid}/fd").glob("*"):
        try:
            p = os.readlink(f)
        except OSError:
            continue
        if p.startswith("/tmp/money-note-d1-") and p.endswith("/synthetic.sqlite3"):
            paths.add(p)
    assert len(paths) == 1
    path = paths.pop()
    start = time.perf_counter()
    with closing(sqlite3.connect("file:" + path + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        current = dict(conn.execute("SELECT * FROM sync_current").fetchone())
        pending = [dict(hash=current["raw_hash"]), dict(hash=current["index_hash"])]
        seen, kinds, rows, bytes_ = set(), Counter(), Counter(), 0
        while pending:
            ref = pending.pop()
            if ref["hash"] in seen:
                continue
            raw = conn.execute(
                "SELECT body FROM sync_objects WHERE hash=?", (ref["hash"],)
            ).fetchone()[0]
            body = json.loads(raw)
            if "bytes" in ref:
                assert len(raw) == int(ref["bytes"])
            actual = hashlib.sha256(
                b"money-note.sync.v1/" + body["kind"].encode() + b"\0" + raw
            ).hexdigest()
            assert actual == ref["hash"]
            seen.add(actual)
            kinds[body["kind"]] += 1
            bytes_ += len(raw)
            refs = children(body)
            assert {r["hash"] for r in refs} == {
                r[0]
                for r in conn.execute(
                    "SELECT child FROM sync_object_edges WHERE parent=?", (actual,)
                )
            }
            pending.extend(refs)
            if body["kind"] == "snapshot-leaf":
                rows[body["table"]] += len(body["rows"])
        sql_count = conn.execute(
            "WITH RECURSIVE reachable(hash) AS (SELECT raw_hash FROM sync_current UNION SELECT index_hash FROM sync_current UNION SELECT child FROM sync_object_edges JOIN reachable ON parent=hash) SELECT count(*) FROM reachable"
        ).fetchone()[0]
        assert sql_count == len(seen)
        assert (
            conn.execute("SELECT count(*) FROM ledger_entries").fetchone()[0]
            == rows["ledger_entries"]
        )
    source = ROOT / "mobile/lib/src/segmented/fetch.dart"
    maximum = int(re.search(r"graphObjects > (\d+)", source.read_text()).group(1))
    value = dict(
        pid=pid,
        n=rows["ledger_entries"],
        raw_index_objects=len(seen),
        complete_generation_minimum_objects=len(seen) + 2,
        kinds=dict(kinds),
        table_rows=dict(rows),
        raw_index_body_bytes=bytes_,
        sql_reachability_count=sql_count,
        roots={k: current[k] for k in ["raw_hash", "index_hash"]},
        namespace=json.loads(current["namespace"]),
        hash_set_sha256=hashlib.sha256("\n".join(sorted(seen)).encode()).hexdigest(),
        supported_fetch_maximum=maximum,
        supported_profile_can_fit=len(seen) + 2 <= maximum,
        fetch_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        seconds=time.perf_counter() - start,
    )
    assert not value["supported_profile_can_fit"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: value[k]
                for k in [
                    "n",
                    "raw_index_objects",
                    "supported_fetch_maximum",
                    "supported_profile_can_fit",
                ]
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pid", type=int)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    run(args.pid, args.out)

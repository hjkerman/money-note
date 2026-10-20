"""독립 read-only accepted pointer/receipt/pins/object bytes/closure 검사."""

from pathlib import Path
import hashlib
import json
import sqlite3
import sys
import time
import oracle


def inspect(path, expected_path):
    expected = json.loads(Path(expected_path).read_text())
    target = expected.get("target", expected.get("manifest", {}).get("target"))
    graph = expected["graph"]
    started = time.monotonic()
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        accepted = dict(db.execute("SELECT * FROM accepted").fetchone())
        assert accepted["current_id"]
        row = dict(
            db.execute(
                "SELECT * FROM generations WHERE id=?", (accepted["current_id"],)
            ).fetchone()
        )
        manifest = json.loads(row["manifest"])
        assert oracle.encode(manifest) == bytes(row["manifest"])
        assert manifest["target"] == target
        assert (
            hashlib.sha256(bytes(row["manifest"])).hexdigest()
            == row["manifest_checksum"]
        )
        assert (
            hashlib.sha256(bytes(row["receipt"])).hexdigest() == row["receipt_checksum"]
        )
        receipt = json.loads(row["receipt"])
        assert oracle.encode(receipt) == bytes(row["receipt"])
        seen, actual = oracle.walk(db, target, client=True, sql_values=False)
        for key in [
            "objects",
            "edges",
            "canonical_bytes",
            "raw_value_sha256",
            "audit_reachable_hash_set_sha256",
        ]:
            assert actual[key] == graph[key], (key, actual[key], graph[key])
        pins = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM generation_roots WHERE generation_id=?",
                (accepted["current_id"],),
            )
        ]
        assert {r["hash"] for r in pins} == {
            target[role + "_ref"]["hash"] for role in ["raw", "index", "hot", "control"]
        }
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        usage = dict(db.execute("SELECT * FROM usage").fetchone())
        return {
            "status": "PASS",
            "elapsed_s": time.monotonic() - started,
            "accepted": accepted,
            "receipt": receipt,
            "current_pins": pins,
            "reachable_objects": len(seen),
            "reachable_digest": actual["audit_reachable_hash_set_sha256"],
            "raw_value_sha256": actual["raw_value_sha256"],
            "usage": usage,
            "database_bytes": Path(path).stat().st_size,
            "readonly": True,
        }


if __name__ == "__main__":
    value = inspect(sys.argv[1], sys.argv[2])
    Path(sys.argv[3]).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "reachable": value["reachable_objects"]}))

"""종료 후 별도 process에서 부분 취득의 durable 상태를 읽기만 한다."""

import hashlib
import json
from pathlib import Path
import sqlite3

OUT = Path(__file__).resolve().parent / "evidence"
r = json.loads((OUT / "full-result.json").read_text())
assert r["status"] == "FAIL"
with sqlite3.connect("file:" + r["store_path"] + "?mode=ro", uri=True) as db:
    db.row_factory = sqlite3.Row
    objects = dict(
        db.execute("SELECT count(*) n,sum(length(body)) bytes FROM objects").fetchone()
    )
    accepted = dict(db.execute("SELECT * FROM accepted").fetchone())
    acquisitions = [dict(v) for v in db.execute("SELECT * FROM acquisition")]
    counts = {
        name: db.execute("SELECT count(*) FROM " + name).fetchone()[0]
        for name in ("generations", "generation_roots", "staging", "staging_objects")
    }
    foreign_keys = [tuple(v) for v in db.execute("PRAGMA foreign_key_check")]
    quick_check = [v[0] for v in db.execute("PRAGMA quick_check")]
    value = {
        "fresh_process": True,
        "read_only": True,
        "objects": objects,
        "accepted": accepted,
        "acquisitions": acquisitions,
        "counts": counts,
        "foreign_key_check": foreign_keys,
        "quick_check": quick_check,
        "no_hash_or_canonical_reparse_for_counting": True,
    }
assert objects == r["durable_objects"]
assert accepted["current_id"] is None and accepted["previous_id"] is None
assert accepted["sequence"] == 0
assert counts["generations"] == counts["generation_roots"] == 0
assert quick_check == ["ok"] and foreign_keys == []
legacy = {}
for name, before in r["protected_before"].items():
    # localChecksum is SHA-256 over the original bytes; this independent hash
    # validates preservation after the experiment, outside all product scopes.
    legacy[name] = hashlib.sha256(Path(name).read_bytes()).hexdigest()
assert legacy == r["protected_before"]
value["legacy_files_unchanged_fresh_process"] = True
value["status"] = "PASS"
(OUT / "failed-store-fresh-process.json").write_text(
    json.dumps(value, ensure_ascii=False, indent=2) + "\n"
)
print(json.dumps({"status": "PASS", "objects": objects["n"], "accepted": None}))

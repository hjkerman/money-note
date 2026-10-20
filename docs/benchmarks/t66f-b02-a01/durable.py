"""종료한 자기 소유 client DB를 별도 Python SQLite 연결로 읽는다."""

import hashlib
import json
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
OUT = Path(json.loads((HERE / "active-run.json").read_text())["out"])
result = json.loads((OUT / "result.json").read_text())
conn = sqlite3.connect(f"file:{result['store_path']}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
names = {
    r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
}
stages = []
for row in conn.execute("SELECT id,manifest FROM staging ORDER BY id"):
    manifest = json.loads(row["manifest"])
    stages.append(
        dict(
            staging_id=row["id"],
            observation_id=manifest["observation_id"],
            unique_progress_objects=conn.execute(
                "SELECT count(*) FROM staging_objects WHERE staging_id=?", (row["id"],)
            ).fetchone()[0],
        )
    )
state = dict(
    label="INDEPENDENT READ-ONLY SQLITE AFTER FAILURE",
    object_count=conn.execute("SELECT count(*) FROM objects").fetchone()[0],
    logical_object_blob_bytes=conn.execute(
        "SELECT sum(length(body)) FROM objects"
    ).fetchone()[0],
    per_stage=stages,
    counts={
        t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
        for t in sorted(names)
    },
    accepted=[dict(r) for r in conn.execute("SELECT * FROM accepted")],
    usage=[dict(r) for r in conn.execute("SELECT * FROM usage")],
    foreign_key_errors=[tuple(r) for r in conn.execute("PRAGMA foreign_key_check")],
    persistent_journal_mode=conn.execute("PRAGMA journal_mode").fetchone()[0],
    legacy_file_sha256={
        p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        for p in result["protected_legacy_before"]
    },
)
conn.close()
assert state["object_count"] == result["usage"]["objects"]
assert state["logical_object_blob_bytes"] == result["usage"]["payload"]
assert state["legacy_file_sha256"] == result["protected_legacy_before"]
(OUT / "durable-state.json").write_text(json.dumps(state, indent=2) + "\n")
print(
    json.dumps(
        {
            k: state[k]
            for k in [
                "object_count",
                "logical_object_blob_bytes",
                "per_stage",
                "persistent_journal_mode",
            ]
        }
    )
)

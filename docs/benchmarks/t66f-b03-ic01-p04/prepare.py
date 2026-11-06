"""원 P03을 읽기 전용으로 보존하고 backup API로 일관된 실험 복제본을 만든다."""

import hashlib
import json
import shutil
import sqlite3
import struct
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
PREVIOUS = HERE.parent / "t66f-b03-ic01-p03/evidence"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def file_sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def connect(path):
    return sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)


def logical_digest(path):
    """독립 clone integrity oracle. 측정 구간 밖에서 실제 SQL 값을 읽는다."""
    h = hashlib.sha256()
    counts = {}
    with connect(path) as db:
        tables = db.execute(
            "SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        for name, ddl in tables:
            h.update((name + "\0" + ddl + "\0").encode())
            quoted = '"' + name.replace('"', '""') + '"'
            cols = db.execute("PRAGMA table_info(" + quoted + ")").fetchall()
            pk = sorted((c[5], c[1]) for c in cols if c[5])
            order = ",".join('"' + x[1].replace('"', '""') + '"' for x in pk) or "rowid"
            count = 0
            for row in db.execute("SELECT * FROM " + quoted + " ORDER BY " + order):
                for value in row:
                    if value is None:
                        tag, raw = b"n", b""
                    elif isinstance(value, bytes):
                        tag, raw = b"b", value
                    elif isinstance(value, int):
                        tag, raw = b"i", str(value).encode()
                    elif isinstance(value, float):
                        tag, raw = b"f", value.hex().encode()
                    else:
                        tag, raw = b"t", value.encode()
                    h.update(tag + struct.pack(">Q", len(raw)))
                    h.update(raw)
                h.update(b"\xff")
                count += 1
            counts[name] = count
    return {"sha256": h.hexdigest(), "table_rows": counts}


def restore(source, destination):
    assert source != destination
    with connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)


def main():
    result = json.loads((PREVIOUS / "full-result.json").read_text())
    source = Path(result["store_path"])
    assert source.exists()
    assert not Path(str(source) + "-wal").exists()
    assert not Path(str(source) + "-shm").exists()
    sha_before = file_sha(source)
    state = logical_digest(source)
    assert state["table_rows"]["objects"] == 397146
    with connect(source) as db:
        db.row_factory = sqlite3.Row
        accepted = dict(db.execute("SELECT * FROM accepted").fetchone())
        assert accepted["current_id"] is None and accepted["sequence"] == 0
        assert db.execute("PRAGMA quick_check").fetchall()[0][0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        stages = [dict(r) for r in db.execute("SELECT * FROM acquisition")]
        assert len(stages) == 3
        assert all(x["error_code"] == "OBSERVATION_EXPIRED" for x in stages)
        manifest = bytes(
            db.execute(
                "SELECT manifest FROM staging ORDER BY created_at DESC LIMIT 1"
            ).fetchone()[0]
        )
        # Fixed hash order within the last observation's already-stored cohort.
        entries = [
            dict(r)
            for r in db.execute(
                "SELECT o.hash,r.bytes,o.kind FROM objects o JOIN refs r USING(hash) "
                "JOIN staging_objects s USING(hash) WHERE s.staging_id=? "
                "AND o.kind IN ('index-leaf','index-node') ORDER BY o.hash LIMIT 2048",
                (stages[-1]["staging_id"],),
            )
        ]
        assert len(entries) == 2048
    legacy = {name: file_sha(Path(name)) for name in result["protected_before"]}
    assert legacy == result["protected_before"]
    root = Path(tempfile.mkdtemp(prefix="mn-p04-late-"))
    plans = [
        {"name": "smoke-A", "mode": "A", "repeat": -1, "n": 128},
        {"name": "smoke-B", "mode": "B", "repeat": -1, "n": 128},
        *[{"name": m, "mode": m, "n": 2048} for m in "ABCD"],
    ]
    clones = []
    for plan in plans:
        private = root / plan["name"]
        destination = private / "segmented-store-v1" / source.name
        destination.parent.mkdir(parents=True)
        started = time.monotonic()
        restore(source, destination)
        for directory in (source.parent.parent / "offline-mode",):
            shutil.copytree(directory, private / directory.name)
        actual = logical_digest(destination)
        assert actual == state
        clones.append(
            {
                **plan,
                "root": str(private),
                "path": str(destination),
                "initial_logical": actual,
                "preparation_s": time.monotonic() - started,
            }
        )
    assert file_sha(source) == sha_before
    save(
        OUT / "clone-plan.json",
        {
            "source": str(source),
            "source_sha256": sha_before,
            "source_logical": state,
            "accepted": accepted,
            "legacy": legacy,
            "clones": clones,
            "manifest": json.loads(manifest),
            "entries": entries,
            "original_wal_shm": "ABSENT",
            "backup_method": "sqlite3.Connection.backup",
            "original_modified": False,
        },
    )
    save(
        OUT / "disposable-location.json",
        {
            "root": str(root),
            "physical_clones": len(clones),
            "new_full_100k_cold_attempts": 0,
        },
    )
    print(
        json.dumps(
            {
                "source_objects": 397146,
                "clones": len(clones),
                "logical_equivalence": "PASS",
                "original_sha_unchanged": True,
            }
        )
    )


if __name__ == "__main__":
    main()

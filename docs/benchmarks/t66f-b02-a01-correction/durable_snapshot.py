"""완료된 합성 campaign의 E1을 독립 read-only SQLite로 관찰한다."""

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def main(out):
    out = out.resolve()
    result = json.loads((out / "result.json").read_text())
    assert result["status"] != "RUNNING"
    path = Path(result["store_path"]).resolve()
    assert path.is_relative_to(out / "client")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA busy_timeout=1000")
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        rows = {}
        for name in (
            "profile",
            "usage",
            "accepted",
            "generations",
            "generation_roots",
            "staging",
            "acquisition",
            "installed",
            "frozen",
        ):
            if name in tables:
                rows[name] = [dict(r) for r in conn.execute(f"SELECT * FROM {name}")]
        # Body BLOBs and financial values are deliberately not exported.
        for values in rows.values():
            for row in values:
                for key, value in list(row.items()):
                    if isinstance(value, bytes):
                        row[key] = {
                            "bytes": len(value),
                            "sha256": hashlib.sha256(value).hexdigest(),
                        }
        objects = [
            dict(r)
            for r in conn.execute(
                "SELECT kind,count(*) AS count,sum(length(body)) AS logical_body_bytes FROM objects GROUP BY kind ORDER BY kind"
            )
        ]
        stages = [
            dict(r)
            for r in conn.execute(
                "SELECT staging_id,count(*) AS linked_objects FROM staging_objects GROUP BY staging_id ORDER BY staging_id"
            )
        ]
        value = dict(
            scope="DIRECT OBSERVATION; synthetic read-only SQLite, not an authority receipt",
            status=result["status"],
            tables=sorted(tables),
            rows=rows,
            objects=objects,
            stage_links=stages,
            isolated_store_user_version=conn.execute("PRAGMA user_version").fetchone()[
                0
            ],
            journal_mode=conn.execute("PRAGMA journal_mode").fetchone()[0],
            foreign_key_errors=[
                list(r) for r in conn.execute("PRAGMA foreign_key_check")
            ],
            protected_files={
                str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest()
                for p in result["protected_legacy_before"]
            },
            files={
                str(p.relative_to(out)): p.stat().st_size
                for p in out.rglob("*")
                if p.is_file()
            },
        )
    # localChecksum in the Dart oracle is SHA-256; compare exact bytes, not rows.
    value["legacy_pending_bytes_preserved"] = (
        value["protected_files"] == result["protected_legacy_before"]
    )
    (out / "durable-state.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "status": value["status"],
                "objects": sum(r["count"] for r in objects),
                "fk_errors": len(value["foreign_key_errors"]),
                "legacy_pending_bytes_preserved": value[
                    "legacy_pending_bytes_preserved"
                ],
            }
        )
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))

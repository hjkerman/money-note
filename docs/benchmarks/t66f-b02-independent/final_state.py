"""새 실행 DB의 pointer checksum/receipt/물리 profile을 read-only로 대조한다."""

from pathlib import Path
import hashlib
import json
import sqlite3
import oracle

HERE = Path(__file__).resolve().parent


def main():
    result = {}
    for n in [50000, 100000]:
        out = Path(json.loads((HERE / f"active-{n}.json").read_text())["out"])
        record = json.loads((out / "result.json").read_text())
        path = Path(record["store_path"])
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            pointer = dict(db.execute("SELECT * FROM accepted").fetchone())
            expected = hashlib.sha256(
                oracle.encode(
                    {
                        "namespace": path.stem,
                        "current": pointer["current_id"],
                        "previous": pointer["previous_id"],
                        "sequence": str(pointer["sequence"]),
                    }
                )
            ).hexdigest()
            assert pointer["checksum"] == expected
            generation = dict(
                db.execute(
                    "SELECT * FROM generations WHERE id=?", (pointer["current_id"],)
                ).fetchone()
            )
            receipt = json.loads(generation["receipt"])
            manifest = json.loads(generation["manifest"])
            assert receipt["target"] == manifest["target"]
            preimage = {k: v for k, v in manifest["target"].items() if k != "sync_root"}
            assert (
                hashlib.sha256(
                    b"money-note.sync.v1/view\0" + oracle.encode(preimage)
                ).hexdigest()
                == manifest["target"]["sync_root"]
            )
            assert (
                receipt["authority_history"]["owner"]
                == manifest["target"]["principal_id"]
                == 1
            )
            assert (
                hashlib.sha256(generation["receipt"]).hexdigest()
                == generation["receipt_checksum"]
            )
            assert (
                hashlib.sha256(generation["manifest"]).hexdigest()
                == generation["manifest_checksum"]
            )
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert db.execute("PRAGMA foreign_key_check").fetchall() == []
            usage = dict(db.execute("SELECT * FROM usage").fetchone())
            assert (
                usage["objects"] <= 500000
                and usage["payload"] <= 512 * 1024**2
                and usage["metadata"] <= 384 * 1024**2
            )
            result[str(n)] = {
                "status": "PASS",
                "pointer_checksum": expected,
                "receipt_target_matches": True,
                "sync_root_independently_verified": True,
                "user_version": db.execute("PRAGMA user_version").fetchone()[0],
                "journal_mode": db.execute("PRAGMA journal_mode").fetchone()[0],
                "page_count": db.execute("PRAGMA page_count").fetchone()[0],
                "page_size": db.execute("PRAGMA page_size").fetchone()[0],
                "usage": usage,
                "wal_file_bytes": Path(str(path) + "-wal").stat().st_size
                if Path(str(path) + "-wal").exists()
                else 0,
                "frozen_rows": db.execute("SELECT count(*)FROM frozen").fetchone()[0],
                "native_frozen_exercised": False,
            }
    (HERE / "final-state.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()

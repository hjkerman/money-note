"""지정한 합성 실행만 관측한다. RSS/파일 크기는 logical write bytes가 아니다."""

import json
from pathlib import Path
import sqlite3
import sys
import time


def main():
    out = Path(sys.argv[1]).resolve()
    result = json.loads((out / "result.json").read_text())
    snapshot = {"wall_time": time.time(), "processes": {}, "files": {}}
    for role, raw_pid in zip(("client", "backend"), sys.argv[2:], strict=True):
        process = Path("/proc") / str(int(raw_pid))
        command = (process / "cmdline").read_bytes().split(b"\0")
        if role == "backend" and str(out / "server").encode() not in command:
            raise ValueError("not the explicitly selected synthetic server")
        if role == "client" and not any(b"flutter_tester" in c for c in command):
            raise ValueError("not a HOST Flutter test client")
        snapshot["processes"][role] = {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in (process / "status").read_text().splitlines()
            if line.startswith(("VmRSS:", "VmHWM:", "Threads:"))
        }
    path = Path(result["store_path"]).resolve()
    if not path.is_relative_to(out / "client"):
        raise ValueError("store is outside the selected disposable run")
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=1) as db:
        db.row_factory = sqlite3.Row
        snapshot["usage"] = dict(db.execute("SELECT * FROM usage").fetchone())
        snapshot["generation_count"] = db.execute(
            "SELECT count(*) FROM generations"
        ).fetchone()[0]
        snapshot["pin_rows"] = db.execute(
            "SELECT count(*) FROM generation_roots"
        ).fetchone()[0]
        snapshot["page_count"] = db.execute("PRAGMA page_count").fetchone()[0]
        snapshot["page_size"] = db.execute("PRAGMA page_size").fetchone()[0]
    for suffix in ("", "-wal", "-shm", "-journal"):
        file = Path(f"{path}{suffix}")
        snapshot["files"][file.name] = file.stat().st_size if file.exists() else 0
    snapshots = out / "resource-snapshots.json"
    prior = json.loads(snapshots.read_text()) if snapshots.exists() else []
    prior.append(snapshot)
    snapshots.write_text(json.dumps(prior, indent=2) + "\n")
    print(json.dumps(snapshot))


if __name__ == "__main__":
    main()

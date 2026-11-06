"""측정 종료 후 clone 간 전체 SQL 값과 원본·B/J 보존을 독립 대조한다."""

import json
from pathlib import Path
from prepare import OUT, connect, file_sha, logical_digest

plan = json.loads((OUT / "clone-plan.json").read_text())
source = Path(plan["source"])
assert file_sha(source) == plan["source_sha256"]
assert logical_digest(source) == plan["source_logical"]
values = []
for clone in plan["clones"]:
    path = Path(clone["path"])
    actual = logical_digest(path)
    with connect(path) as db:
        count = db.execute("SELECT count(*) FROM objects").fetchone()[0]
        accepted = db.execute(
            "SELECT current_id,previous_id,sequence FROM accepted"
        ).fetchone()
        assert count == 397146 and accepted == (None, None, 0)
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    for name, before in plan["legacy"].items():
        assert file_sha(Path(name)) == before
        assert (
            file_sha(Path(clone["root"]) / "offline-mode" / Path(name).name) == before
        )
    values.append(
        {
            "name": clone["name"],
            "logical": actual,
            "objects": count,
            "accepted": list(accepted),
            "legacy_unchanged": True,
        }
    )
normal = [r["logical"] for r in values if r["name"] in "ABCD"]
assert len(normal) == 4 and all(v == normal[0] for v in normal)
smoke = [r["logical"] for r in values if r["name"].startswith("smoke")]
assert len(smoke) == 2 and smoke[0] == smoke[1]
assert not Path(str(source) + "-wal").exists()
assert not Path(str(source) + "-shm").exists()
(OUT / "clone-final-equivalence.json").write_text(
    json.dumps(
        {
            "status": "PASS",
            "original_unchanged": True,
            "original_sha256": plan["source_sha256"],
            "clones": values,
            "note": "One deliberate local staging addition; no new immutable objects, graph closure or authority publication",
        },
        indent=2,
    )
    + "\n"
)
print(json.dumps({"status": "PASS", "clones": 6, "original_unchanged": True}))

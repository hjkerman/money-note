"""쓰기 가능한 폐기용 clone만 시작 상태로 돌린다. 원 DB는 read-only다."""

import json
from pathlib import Path
import sys
import time
from prepare import OUT, logical_digest, restore

plan = json.loads((OUT / "clone-plan.json").read_text())
destination = Path(sys.argv[1])
assert str(destination) in {c["path"] for c in plan["clones"]}
assert destination != Path(plan["source"])
started = time.monotonic()
restore(Path(plan["source"]), destination)
proof = logical_digest(destination)
assert proof == plan["source_logical"]
print(
    json.dumps(
        {"logical": proof, "backup_and_integrity_wall_s": time.monotonic() - started}
    )
)

"""실패한 P01 adapter revision을 보존한다. 기존 감사 source는 불변."""

import gzip
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
raw = (here / "packets_test.dart").read_bytes()
target = here / "evidence/packet-before-cleanup-fix.dart.txt.gz"
assert not target.exists()
with gzip.open(target, "wb") as f:
    f.write(raw)
(here / "evidence/packet-source-receipt.json").write_text(
    json.dumps(
        {
            "executed_source_sha256": hashlib.sha256(raw).hexdigest(),
            "archived_source": target.name,
            "actual_result": "paired packet assertions and cohort snapshot succeeded; child shutdown assertion failed",
            "full_cold_attempts": 0,
        },
        indent=2,
    )
    + "\n"
)

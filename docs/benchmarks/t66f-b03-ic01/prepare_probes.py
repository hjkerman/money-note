"""원 독립 probe의 import/assertion을 유지하고 출력 경로만 분리한다."""

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
records = []
for name in ["http_test.dart", "overhead_test.dart"]:
    source = HERE.parent / "t66f-b03-independent" / name
    raw = source.read_text()
    rendered = raw.replace(
        "/docs/benchmarks/t66f-b03-independent/evidence/",
        "/docs/benchmarks/t66f-b03-ic01/evidence/",
    )
    target = HERE / ("current_" + name)
    target.write_text(rendered)
    records.append(
        {
            "source": str(source.relative_to(HERE.parents[2])),
            "source_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "target": target.name,
            "target_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
            "replacement": "evidence output path only; assertions unchanged",
        }
    )
(HERE / "probe-manifest.json").write_text(json.dumps(records, indent=2) + "\n")

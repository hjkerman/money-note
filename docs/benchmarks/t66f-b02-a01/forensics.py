"""보존된 이전 machine 로그의 실패만 추출한다. 과거 결과는 변경하지 않는다."""

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EVIDENCE = ROOT / "docs/benchmarks/t66f-b02-implementation/evidence"
records = {}
for path in sorted(EVIDENCE.glob("*.jsonl.gz")):
    names = {}
    errors = []
    failed = []
    terminal = None
    with gzip.open(path, "rt") as stream:
        for line in stream:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                continue
            if row.get("type") == "testStart":
                names[row["test"]["id"]] = row["test"]
            if row.get("type") == "error":
                errors.append(row)
            if row.get("type") == "testDone" and row.get("result") in (
                "error",
                "failure",
            ):
                failed.append(row)
            if row.get("type") == "done":
                terminal = row
    if errors or failed or "full" in path.name:
        records[path.name] = dict(
            file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            terminal=terminal,
            errors=[dict(test=names.get(r.get("testID")), error=r) for r in errors],
            failed=[dict(test=names.get(r.get("testID")), result=r) for r in failed],
        )
(HERE / "historical-failures.json").write_text(
    json.dumps(records, ensure_ascii=False, indent=2) + "\n"
)
for name in ("flutter-bounded-full.jsonl.gz", "flutter-full.jsonl.gz"):
    print(name)
    for row in records.get(name, {}).get("errors", []):
        print(
            json.dumps(
                dict(
                    test=row["test"],
                    error=row["error"].get("error"),
                    stack=row["error"].get("stackTrace"),
                ),
                ensure_ascii=False,
            )
        )

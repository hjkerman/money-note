"""기존 원본 fixed-H/TLS 서버와 A01 요청 계측을 변경 없이 위임한다."""

import importlib.util
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "preserved_a01_investigation_server",
    ROOT / "docs/benchmarks/t66f-b02-a01/server.py",
)
instrumented = importlib.util.module_from_spec(spec)
spec.loader.exec_module(instrumented)

# Additional test-only oracle. Existing walk still checks full typed closure,
# sizes and SHA. Digest canonical authoritative VALUES, never financial recomputation.
original_walk = instrumented.base.oracle.walk


def walk(db, target):
    from isolated_sync.canonical import encode

    seen, graph = original_walk(db, target)

    def read(ref):
        return json.loads(
            db.execute(
                "SELECT body FROM sync_objects WHERE hash=?", (ref["hash"],)
            ).fetchone()[0]
        )

    def values(ref):
        body = read(ref)
        if body["kind"] == "snapshot-node":
            for child in body["children"]:
                yield from values(child["ref"])
        else:
            assert body["kind"] == "snapshot-leaf"
            yield from (row["value"] for row in body["rows"])

    digests = {}
    for table in read(target["raw_ref"])["tables"]:
        digest, count = hashlib.sha256(), 0
        for value in values(table["root"]["ref"]):
            digest.update(hashlib.sha256(encode(value)).hexdigest().encode() + b"\n")
            count += 1
        digests[table["name"]] = {"count": count, "sha256": digest.hexdigest()}
    graph["raw_value_sha256"] = digests
    return seen, graph


instrumented.base.oracle.walk = walk

if __name__ == "__main__":
    instrumented.base.main()

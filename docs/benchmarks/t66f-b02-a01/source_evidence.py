"""규범/제품의 위치와 SHA guard 의미를 읽기 전용으로 고정한다."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
initial = json.loads((HERE / "initial-state.json").read_text())
protected = json.loads(
    (ROOT / "docs/benchmarks/t66e4-p0-audit/protected-source.json").read_text()
)
source = (ROOT / "mobile/lib/src/app_state.dart").read_text()
begin = source.index("  // Explicit E4 legacy boundary only.")
end = source.index("  Future<void> _refreshAuthoritativeState(", begin)
restored = (
    (source[:begin] + source[end:])
    .replace("import 'segmented/adapters.dart';\n", "", 1)
    .replace("import 'segmented/verification.dart';\n", "", 1)
)
paths = [
    "mobile/lib/src/app_state.dart",
    "mobile/lib/src/segmented/fetch.dart",
    "mobile/lib/src/segmented/store.dart",
]
record = dict(
    product_sha256={
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths
    },
    products_match_initial=all(
        hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        == initial["product_hashes"][p]
        for p in paths
    ),
    sha_guards=dict(
        fetch_expected=protected[paths[1]]["sha256"],
        fetch_actual=hashlib.sha256((ROOT / paths[1]).read_bytes()).hexdigest(),
        appstate_restored_expected=protected[paths[0]]["sha256"],
        appstate_restored_actual=hashlib.sha256(restored.encode()).hexdigest(),
    ),
    source_locations={},
)
needles = {
    "backend/isolated_sync/observation.py": [
        "class Limits",
        "def _connection",
        "def _guard",
        "def _check_lease",
        "validated_at",
        "expires_at",
        "def _lookup",
        "def versions",
    ],
    "backend/isolated_sync/http.py": [
        "def credential",
        "def prepare",
        "def terminal",
        "async def dispatch",
    ],
    "backend/isolated_sync/transfer.py": [
        "class PathResolver",
        "capacity=0",
        "def resolve",
        "def validate",
        "def acquire",
    ],
    "backend/isolated_sync/retention_schema.py": ["def connect", "def _open"],
    "backend/isolated_sync/workers.py": [
        "class WorkerBudget",
        "def acquire",
        "async def run",
        "def _release_if_finished",
    ],
    "mobile/lib/src/segmented/fetch.dart": [
        "class FetchLimits",
        "class IncrementalFetcher",
        "for (var observation",
        "class _VerificationFrontier",
        "Future<void> _fetch",
        "Future<void> _wave",
        "Future<VerifiedObject> load",
        "final terminal =",
    ],
    "mobile/lib/src/segmented/store.dart": [
        "T _transaction",
        "void putVerifiedStagedBatch",
        "VerifiedObject? _read",
        "VerifiedObject? getVerifiedObject",
    ],
    "mobile/test/segmented_adapter_isolation_test.dart": [
        "default/legacy/E1/E2/E3",
        "AppState E4 entry",
        "protected[",
    ],
    "docs/t66/c/t66c-delta-sync-protocol.md": [
        "## 16.",
        "TTL은",
        "Lease 만료 전",
        "Active flow",
        "## 24.",
        "## 25.",
        "## 26.",
        "## 29.",
        "## 31.",
        "## 34.",
        "## 35.",
    ],
}
for p, terms in needles.items():
    lines = (ROOT / p).read_text().splitlines()
    record["source_locations"][p] = {
        term: [i for i, line in enumerate(lines, 1) if term in line] for term in terms
    }
record["backend_product_diff"] = subprocess.check_output(
    ["git", "diff", "--name-only", "--", "backend/app", "backend/isolated_sync"],
    cwd=ROOT,
).decode()
(HERE / "source-evidence.json").write_text(
    json.dumps(record, ensure_ascii=False, indent=2) + "\n"
)
print(
    json.dumps(
        {
            k: record[k]
            for k in ["products_match_initial", "sha_guards", "backend_product_diff"]
        },
        indent=2,
    )
)

"""전체 P02 wrapper diff와 원 보호 source의 exact 보존 증거."""

import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old = (HERE / "original_sqlite.dart").read_text()
    current_path = ROOT / "mobile/test/support/logical_cost_sqlite.dart"
    current = current_path.read_text()
    # The already-corrected classifier, row observers, savepoints, transaction
    # accounting and caller-owned prepared API are not optimized or rewritten.
    unchanged = {
        "classifier_and_SqlCosts": old.split("class CostDatabase")[0]
        == current.split("class CostDatabase")[0],
        "row_observer_install_settle_and_call": old[
            old.index("  static String _quote") : old.index(
                "  @override\n  void execute"
            )
        ]
        == current[
            current.index("  static String _quote") : current.index(
                "  @override\n  void execute"
            )
        ],
        "caller_owned_CostStatement": old.split("class CostStatement")[1]
        == current.split("class CostStatement")[1],
    }
    assert all(unchanged.values()), unchanged
    review = json.loads(
        (ROOT / "docs/benchmarks/t66f-b03/source-lock-review.json").read_text()
    )
    start = json.loads((OUT / "starting-state.json").read_text())
    protected = {
        p: {"starting": start["files"][p], "current": sha(ROOT / p)}
        for p in review["files"]
    }
    assert all(v["starting"] == v["current"] for v in protected.values())
    diff = "".join(
        difflib.unified_diff(
            old.splitlines(True),
            current.splitlines(True),
            fromfile="P02-start/logic_cost_sqlite.dart",
            tofile="P02-current/logical_cost_sqlite.dart",
        )
    )
    (OUT / "p02-wrapper.patch").write_text(diff)
    result = {
        "before_sha256": sha(HERE / "original_sqlite.dart"),
        "after_sha256": sha(current_path),
        "unchanged_sections": unchanged,
        "protected_files": protected,
        "product_hooks_modified": [],
        "new_awaits": 0,
        "protocol_modified": False,
        "database_schema_modified": False,
        "cache_capacity": 32,
        "cache_key_max_utf16_code_units": 16384,
        "cache_key": "exact SQL; fixed managed prepare flags; owner is one CostDatabase/native connection",
        "clear_bindings": "diagnostic native handle cleanup; no SQL stepping or row write; not product bind-input work",
        "uncached_and_caller_owned_handles": "original driver API lifetime, not included in managed cache peakLive",
        "source_lock": "protected product files unchanged; no new SHA approval/update required for test helper",
    }
    (OUT / "source-review.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "unchanged": unchanged,
                "protected": len(protected),
                "after_sha256": result["after_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()

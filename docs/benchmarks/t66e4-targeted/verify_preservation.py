"""P0 checkpoint 및 원래 E4 증거 보존 검사. 제품/감사 파일을 변경하지 않는다."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    audited = json.loads((ROOT / "docs/benchmarks/t66e4-p0-audit/worktree-targets.json").read_text())
    for name, evidence in audited["files"].items():
        assert digest((ROOT / name).read_bytes()) == evidence["sha256"], name
        checkpoint = subprocess.check_output(
            ["git", "show", "35d7c53f1652310de75e492a98491efc3fd5cbba:" + name], cwd=ROOT
        )
        assert digest(checkpoint) == evidence["sha256"], name
    original = json.loads((ROOT / "docs/benchmarks/t66e4/worktree-preservation.json").read_text())
    report = "docs/t66e4-implementation-resumption.md"
    before = original["files"][report]
    assert digest((ROOT / report).read_bytes()[:before["bytes"]]) == before["sha256"]
    unchanged = [
        "docs/benchmarks/t66e4/README.md",
        "docs/benchmarks/t66e4/measure.dart",
        "docs/benchmarks/t66e4/pagination-before.json",
        "docs/benchmarks/t66e4/read-cost-final.json",
        "docs/benchmarks/t66e4/read-cost-with-storage.json",
        "docs/benchmarks/t66e4/regression-summary.json",
        "docs/benchmarks/t66e4/summarize_flutter.py",
        "mobile/test/segmented_adapter_authority_test.dart",
        "mobile/test/segmented_adapter_crash_test.dart",
        "mobile/test/segmented_adapters_test.dart",
        "mobile/test/support/e4_backend_oracle.py",
        "mobile/test/support/segmented_read_crash_child.dart",
    ]
    for name in unchanged:
        assert digest((ROOT / name).read_bytes()) == original["files"][name]["sha256"], name
    print(json.dumps({"p0_current_and_checkpoint": len(audited["files"]),
                      "historical_report_prefix_bytes": before["bytes"],
                      "old_e4_unchanged_files": len(unchanged), "status": "MATCHED"}))


if __name__ == "__main__":
    main()

"""승인된 exact artifact 갱신용 검토 기록과 apply_patch 입력을 생성한다."""

import base64
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
from isolated_sync.artifacts import release_bundle  # noqa: E402


def main():
    paths = [
        "docs/specimens/t66d3b-release-artifacts.json",
        "mobile/assets/segmented/isolated-release-artifacts.json",
    ]
    old = (ROOT / paths[0]).read_bytes()
    assert old == (ROOT / paths[1]).read_bytes()
    previous, current = json.loads(old), release_bundle()
    assert previous["versions"] == current["versions"]
    for key in ("raw_schema", "projection_schema", "policy_registry"):
        assert previous["artifacts"][key] == current["artifacts"][key]

    def engine(bundle):
        return json.loads(
            base64.b64decode(bundle["artifacts"]["financial_engine"]["data_base64"])
        )

    a, b = engine(previous), engine(current)
    assert a["profile"] == b["profile"]
    changes = {
        k: {"old": a["sources"].get(k), "new": b["sources"].get(k)}
        for k in a["sources"].keys() | b["sources"].keys()
        if a["sources"].get(k) != b["sources"].get(k)
    }
    assert set(changes) == {"isolated_sync/transfer.py"}, changes
    archive = HERE / "release-artifacts.before.json.gz"
    assert not archive.exists(), "최초 artifact bytes를 덮어쓰지 않는다"
    archive.write_bytes(gzip.compress(old, mtime=0))
    result = dict(
        approval="사용자: 두 exact hash의 최소 호환 갱신 승인",
        old_engine=previous["artifacts"]["financial_engine"]["sha256"],
        new_engine=current["artifacts"]["financial_engine"]["sha256"],
        changed_sources=changes,
        unchanged=["versions", "raw_schema", "projection_schema", "policy_registry"],
        historical_goldens="원본 유지",
        old_artifact_sha256=hashlib.sha256(old).hexdigest(),
    )
    (HERE / "artifact-review.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    new = json.dumps(current, ensure_ascii=False, separators=(",", ":")) + "\n"
    print("*** Begin Patch")
    for name in paths:
        print(f"*** Update File: {ROOT / name}\n@@")
        print("-" + old.decode().rstrip("\n"))
        print("+" + new.rstrip("\n"))
    print("*** End Patch")


if __name__ == "__main__":
    main()

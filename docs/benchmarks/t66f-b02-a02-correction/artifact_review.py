"""사용자 승인: 새 current exact hash와 기존 두 hash만 유지. patch 출력만 한다."""

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
    changed = {
        k: {"old": a["sources"].get(k), "new": b["sources"].get(k)}
        for k in a["sources"].keys() | b["sources"].keys()
        if a["sources"].get(k) != b["sources"].get(k)
    }
    assert set(changed) == {"isolated_sync/canonical.py"}, changed
    old_hash = previous["artifacts"]["financial_engine"]["sha256"]
    new_hash = current["artifacts"]["financial_engine"]["sha256"]
    assert (
        old_hash == "afe26b70856b5a3fa06477641d91e8e1784e9184906281843f0a39a9c99cbdf5"
    )
    assert (
        new_hash == "7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c"
    )
    archive = HERE / "release-artifacts.before.json.gz"
    assert not archive.exists()
    archive.write_bytes(gzip.compress(old, mtime=0))
    (HERE / "artifact-review-approved.json").write_text(
        json.dumps(
            dict(
                approval="사용자: 승인합니다. — 새 exact engine와 기존 두 exact engine만 유지",
                new_engine=new_hash,
                previous_engine=old_hash,
                historical_engine="f34aef259c801ada33ccb88cfb103ee6654fb4467c49a66ce509f2239ffe449d",
                changed_sources=changed,
                unchanged=[
                    "versions",
                    "raw_schema",
                    "projection_schema",
                    "policy_registry",
                    "engine profile",
                ],
                previous_artifact_sha256=hashlib.sha256(old).hexdigest(),
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    new = json.dumps(current, ensure_ascii=False, separators=(",", ":")) + "\n"
    print("*** Begin Patch")
    for path in paths:
        print(f"*** Update File: {ROOT / path}\n@@")
        print("-" + old.decode().rstrip("\n"))
        print("+" + new.rstrip("\n"))
    print("*** End Patch")


if __name__ == "__main__":
    main()

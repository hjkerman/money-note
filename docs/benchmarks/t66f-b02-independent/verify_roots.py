"""보존된 Target의 view hash를 제품 helper 없이 별도로 대조한다."""

from pathlib import Path
import gzip
import hashlib
import json
import oracle

HERE = Path(__file__).resolve().parent


def main():
    checked = []
    for n in [50000, 100000]:
        for path in (HERE / "evidence" / str(n)).glob("*.json.gz"):
            value = json.loads(gzip.decompress(path.read_bytes()))
            if not isinstance(value, dict):
                continue
            target = value.get("target", value.get("manifest", {}).get("target"))
            if target is None:
                continue
            preimage = {k: v for k, v in target.items() if k != "sync_root"}
            assert (
                hashlib.sha256(
                    b"money-note.sync.v1/view\0" + oracle.encode(preimage)
                ).hexdigest()
                == target["sync_root"]
            )
            checked.append(str(path.relative_to(HERE)))
    (HERE / "independent-target-roots.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "checked": checked,
                "definition": "§9 view domain framing + stdlib canonical encoding; product helper 미사용",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()

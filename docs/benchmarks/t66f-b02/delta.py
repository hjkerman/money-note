"""기존 reachable G1와 새 frontier를 별도 SQL에서 비교한다. 실제 전송 counter가 아니다."""

from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts/benchmarks")]
from t66e2_server import children  # noqa: E402


def main():
    for n in [50000, 100000]:
        folder = Path("/tmp/mn-b02") / str(n)
        first = json.loads((folder / "manifest-g1.json").read_text())
        assert not first["inline_objects"]
        second = json.loads((folder / "manifest-g2.json").read_text())
        with closing(
            sqlite3.connect(f"file:{folder}/layout-model.sqlite?mode=ro", uri=True)
        ) as model:
            old = {r[0] for r in model.execute("SELECT hash FROM objects")}
            full_base64 = sum(
                4 * ((r[0] + 2) // 3)
                for r in model.execute("SELECT length(body) FROM objects")
            )
        pending = [
            second["target"][k]
            for k in ["raw_ref", "index_ref", "hot_ref", "control_ref"]
        ]
        seen = set()
        kinds = Counter()
        sizes = Counter()
        frontier_hits = 0
        with closing(
            sqlite3.connect(f"file:{folder}/objects.sqlite?mode=ro", uri=True)
        ) as source:
            while pending:
                ref = pending.pop()
                if ref["hash"] in old:
                    frontier_hits += 1
                    continue
                if ref["hash"] in seen:
                    continue
                kind, body = source.execute(
                    "SELECT kind,body FROM sync_objects WHERE hash=?", (ref["hash"],)
                ).fetchone()
                assert (
                    hashlib.sha256(
                        b"money-note.sync.v1/" + kind.encode() + b"\0" + body
                    ).hexdigest()
                    == ref["hash"]
                )
                seen.add(ref["hash"])
                kinds[kind] += 1
                sizes[kind] += len(body)
                pending.extend(children(json.loads(body)))
        expected = json.loads((folder / "result.json").read_text())
        assert len(seen) == expected["delta_new_reachable_objects"]
        assert sum(sizes.values()) == expected["delta_new_reachable_bytes"]
        result = dict(
            n=n,
            status="PASS",
            new_objects=len(seen),
            new_kinds=dict(kinds),
            new_kind_bytes=dict(sizes),
            reused_frontier_refs=frontier_hits,
            full_base64_payload_bytes_offline_estimate=full_base64,
            actual_http_measured=False,
            minimum_cold_object_requests_if_empty_cache=expected["g1"]["objects"],
            request_assumption="실제 E2 single-item·한 object<1MiB·inline 없음·성공 최초 시도; observation/release/header 제외",
            new_hashes=sorted(seen),
        )
        (folder / "delta-analysis.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        )
        print(n, len(seen), "신규 객체의 독립 frontier 확인")


if __name__ == "__main__":
    main()

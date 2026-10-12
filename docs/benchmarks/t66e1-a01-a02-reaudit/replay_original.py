"""원래 독립 ASGI/SQLite 반례를 변경 없이 실행하고 출력 파일만 분리한다."""

import hashlib
import json
from pathlib import Path
import runpy
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT / "docs/benchmarks/t66e1-audit"
OUT = Path("/tmp/mn-e1-a01-a02-reaudit")
OUT.mkdir(parents=True, exist_ok=True)


def main():
    old = ORIGINAL / "findings.json"
    before = hashlib.sha256(old.read_bytes()).hexdigest()
    write = Path.write_text

    def redirected(path, value, *args, **kwargs):
        destination = OUT / "original-replay.json" if path.resolve() == old.resolve() else path
        return write(destination, value, *args, **kwargs)

    with patch.object(Path, "write_text", redirected):
        runpy.run_path(str(ORIGINAL / "reproduce_findings.py"), run_name="__main__")
    assert hashlib.sha256(old.read_bytes()).hexdigest() == before
    observed = json.loads((OUT / "original-replay.json").read_text())
    assert all(v["manifest_status"] == 201 and v["object_status"] == 200 and v["dart"]["ok"]
               for v in observed["money"])
    assert not observed["bom_money"]["dart"]["ok"]
    assert observed["schema"]["actual_objects"] == [[0]]
    assert observed["schema"]["dart"]["error"] == "STORE_SCHEMA_CORRUPT"
    print(json.dumps(dict(original_artifact_unchanged=True, asgi_cases=4,
                         bom_rejected=True, unauthorized_additional_committed_objects=0)))


if __name__ == "__main__":
    main()

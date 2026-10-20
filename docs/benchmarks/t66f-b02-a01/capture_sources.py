"""성능 실행에 사용된 조사 코드의 현 내용만 별도 snapshot으로 보존한다."""

import gzip
import hashlib
import json
from pathlib import Path
import tarfile
import io

HERE = Path(__file__).resolve().parent
names = [
    "server.py",
    "run.py",
    "monitor.py",
    "cold_test.dart",
    "cold-first.dart.txt",
    "backend_component.py",
    "e1_component.dart",
    "reuse_diagnostic_test.dart",
    "sink_probe.dart",
    "sink_transport_probe.dart",
    "postcheck.py",
]
manifest = {}
with io.BytesIO() as output:
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name in names:
            path = HERE / name
            data = path.read_bytes()
            manifest[name] = dict(
                bytes=len(data), sha256=hashlib.sha256(data).hexdigest()
            )
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mtime = 0
            archive.addfile(item, io.BytesIO(data))
    (HERE / "execution-sources.tgz").write_bytes(
        gzip.compress(output.getvalue(), mtime=0)
    )
(HERE / "execution-sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("실행 계측 source snapshot:", len(manifest), "files")

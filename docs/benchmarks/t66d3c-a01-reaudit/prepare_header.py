"""공식 SQLite 3.45.1 public ABI header를 /tmp 감사 경로에만 준비한다."""

import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

URL = "https://www.sqlite.org/2024/sqlite-amalgamation-3450100.zip"
ARCHIVE_SHA = "5592243caf28b2cdef41e6ab58d25d653dfc53deded8450eb66072c929f030c4"
HEADER_SHA = "41e066ccd4f89e938f136ceb48c996c54dc381b59fe566dea48864c3750b779e"


def main():
    with urllib.request.urlopen(URL, timeout=30) as response:
        data = response.read()
    assert hashlib.sha256(data).hexdigest() == ARCHIVE_SHA
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        header = archive.read("sqlite-amalgamation-3450100/sqlite3.h")
    assert hashlib.sha256(header).hexdigest() == HEADER_SHA
    output = Path("/tmp/mn-d3c-a01-reaudit")
    directory = output / "sqlite-3.45.1"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "sqlite3.h").write_bytes(header)
    (output / "official-header.json").write_text(
        json.dumps(
            dict(
                url=URL,
                archive_sha256=ARCHIVE_SHA,
                header_sha256=HEADER_SHA,
                header_bytes=len(header),
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

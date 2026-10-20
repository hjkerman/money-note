"""기존 파일의 Ruff format 차이를 원본과 대조. 제품 bytes를 쓰지 않는다."""

import ast
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
rows = []
for name, before in [
    ("canonical.py", HERE / "canonical.py.before.gz"),
    ("transfer.py", HERE.parent / "t66f-b02-a01-correction/transfer.py.before.gz"),
]:
    current = ROOT / "backend/isolated_sync" / name
    for revision, raw in (
        ("before", gzip.decompress(before.read_bytes())),
        ("current", current.read_bytes()),
    ):
        check = subprocess.run(
            [
                str(ROOT / ".venv/bin/ruff"),
                "format",
                "--check",
                "--stdin-filename",
                str(current),
                "-",
            ],
            input=raw,
            capture_output=True,
        )
        formatted = subprocess.run(
            [
                str(ROOT / ".venv/bin/ruff"),
                "format",
                "--stdin-filename",
                str(current),
                "-",
            ],
            input=raw,
            capture_output=True,
            check=True,
        ).stdout
        rows.append(
            dict(
                name=name,
                revision=revision,
                format_check_exit=check.returncode,
                source_sha256=hashlib.sha256(raw).hexdigest(),
                formatter_only_ast_equal=ast.dump(ast.parse(raw))
                == ast.dump(ast.parse(formatted)),
            )
        )
(HERE / "format-baseline-review.json").write_text(
    json.dumps(
        dict(
            scope="기존 스타일 차이는 before/current 모두 존재. 불필요한 전체 재format/새 engine hash 생성 없이 보존. 신규 Python·변경 Dart 별도 검사",
            rows=rows,
        ),
        indent=2,
        ensure_ascii=False,
    )
    + "\n"
)
assert all(
    row["format_check_exit"] == 1 and row["formatter_only_ast_equal"] for row in rows
)
print("PASS baseline format deviations preserved", len(rows), "comparisons")

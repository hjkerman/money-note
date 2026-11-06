"""승인된 역사/현재 분리. 원 감사 파일/원 assertion 및 source hash 보존."""

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = "ebcbd54d90eeee194a04b9eea6367f446ee2fd28"
FILES = {
    "counters.py": "docs/benchmarks/t66f-b03/counters.py",
    "logical_cost_sqlite.dart": "mobile/test/support/logical_cost_sqlite.dart",
}


def main():
    target = HERE / "historical"
    target.mkdir(exist_ok=True)
    manifest = {
        "commit": BASE,
        "approval": "역사 재현과 현재 검증 분리 승인",
        "files": {},
    }
    for name, source in FILES.items():
        raw = subprocess.check_output(["git", "show", BASE + ":" + source], cwd=ROOT)
        (target / name).write_bytes(raw)
        manifest["files"][source] = hashlib.sha256(raw).hexdigest()
    original = "mobile/test/segmented_logical_cost_independent_audit_test.dart"
    raw = (ROOT / original).read_text()
    rendered = raw.replace(
        "'support/logical_cost_sqlite.dart'", "'historical/logical_cost_sqlite.dart'"
    )
    rendered = rendered.replace(
        "'support/offline_mode_fixtures.dart'",
        "'../../../mobile/test/support/offline_mode_fixtures.dart'",
    )
    rendered = rendered.replace(
        "'${Directory.current.parent.path}/docs/benchmarks/t66f-b03-independent/evidence'",
        "'${Directory.current.parent.path}/docs/benchmarks/t66f-b03-ic01/evidence'",
    )
    rendered = rendered.replace(
        "'${auditOut.parent.path}/lineage-goldens.json'",
        "'${auditOut.parent.path}/../t66f-b03-independent/lineage-goldens.json'",
    )
    # The longer golden fixture path needs only setup-expression wrapping under
    # the source mobile package's Dart 3.3 formatter. Assertions stay verbatim.
    rendered = rendered.replace(
        "final goldens = jsonDecode(\n"
        "      File('${auditOut.parent.path}/../t66f-b03-independent/lineage-goldens.json')\n"
        "          .readAsStringSync()) as List;",
        "final goldens = jsonDecode(File(\n"
        "          '${auditOut.parent.path}/../t66f-b03-independent/lineage-goldens.json')\n"
        "      .readAsStringSync()) as List;",
    )
    (HERE / "historical_flutter_test.dart").write_text(rendered)
    manifest["original_test_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    manifest["rendered_test_sha256"] = hashlib.sha256(rendered.encode()).hexdigest()
    manifest["setup_path_format"] = (
        "Dart 3.3; golden file setup only; assertions unchanged"
    )
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()

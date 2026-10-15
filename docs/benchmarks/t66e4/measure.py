"""폐기용 source copy의 SQL observer로 E4 read 비용을 측정한다."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def main():
    with tempfile.TemporaryDirectory(prefix="mn-e4-sql-") as temporary:
        mobile = Path(temporary) / "mobile"
        shutil.copytree(ROOT / "mobile/lib", mobile / "lib")
        store = mobile / "lib/src/segmented/store.dart"
        text = store.read_text()
        assert text.count("db = sqlite3.open(path);") == 1
        store.write_text(text.replace("import 'work.dart';",
            "import 'work.dart';\nimport 'audit_trace.dart';").replace(
            "db = sqlite3.open(path);", "db = AuditDatabase(sqlite3.open(path));"))
        shutil.copyfile(ROOT / "docs/benchmarks/t66e3-audit/audit_trace.dart",
                        store.with_name("audit_trace.dart"))
        original = ROOT / "mobile/.dart_tool/package_config.json"
        config = json.loads(original.read_text())
        for package in config["packages"]:
            if ":" not in package["rootUri"]:
                package["rootUri"] = (original.parent / package["rootUri"]).resolve().as_uri() + "/"
            if package["name"] == "money_note_mobile":
                package["rootUri"] = mobile.as_uri() + "/"
        location = mobile / ".dart_tool/package_config.json"
        location.parent.mkdir()
        location.write_text(json.dumps(config))
        shutil.copyfile(original.with_name("native_assets.yaml"),
                        location.with_name("native_assets.yaml"))
        run = subprocess.run([
            "/home/hjkerman/.flutter/bin/dart", "--packages=" + str(location),
            str(ROOT / ("docs/benchmarks/t66e4-targeted/measure.dart" if "--frozen" in sys.argv else "docs/benchmarks/t66e4/measure.dart")),
            *([sys.argv[2]] if "--frozen" in sys.argv else []),
        ], cwd=ROOT, capture_output=True, text=True, timeout=600)
        if run.returncode:
            print(run.stderr[-6000:], file=sys.stderr)
            raise SystemExit(run.returncode)
        result = json.loads(run.stdout)
        Path(sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        phase_key = "phases" if "--frozen" in sys.argv else "reads"
        print(json.dumps({"scales": len(result), "scenarios": sum(len(r[phase_key]) for r in result)}))


if __name__ == "__main__":
    main()

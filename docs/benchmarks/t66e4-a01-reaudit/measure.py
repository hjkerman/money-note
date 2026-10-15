"""제품 source는 보존하고 폐기용 copy에서만 SQL·실제 함수 진입을 계측한다."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent


def replace(path, before, after):
    source = path.read_text()
    assert source.count(before) == 1, (path, before)
    path.write_text(source.replace(before, after))


def main(out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mn-e4-independent-cost-") as tmp:
        project = Path(tmp)
        mobile = project / "mobile"
        shutil.copytree(ROOT / "mobile/lib", mobile / "lib")
        shutil.copytree(ROOT / "mobile/assets", mobile / "assets")
        (mobile / "test").symlink_to(ROOT / "mobile/test", target_is_directory=True)
        for name in ["pubspec.yaml", "pubspec.lock", ".flutter-plugins-dependencies"]:
            shutil.copyfile(ROOT / "mobile" / name, mobile / name)
        for name in [".venv", "scripts", "docs"]:
            (project / name).symlink_to(ROOT / name, target_is_directory=True)
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
        for name in ["native_assets.yaml", "package_graph.json"]:
            if (original.parent / name).exists():
                shutil.copyfile(original.parent / name, location.parent / name)
        store = mobile / "lib/src/segmented/store.dart"
        replace(store, "import 'work.dart';", "import 'work.dart';\nimport 'audit_trace.dart';")
        replace(store, "db = sqlite3.open(path);", "db = AuditDatabase(sqlite3.open(path));")
        trace = (ROOT / "docs/benchmarks/t66e3-audit/audit_trace.dart").read_text()
        trace = trace.replace("  static void reset(String value) {", "  static void note(String value) { if (enabled) events.add({'note':value}); }\n  static void reset(String value) {")
        store.with_name("audit_trace.dart").write_text(trace)
        frozen = store.with_name("store_frozen.dart")
        replace(frozen, "    work.add('frozen_full_recoveries');", "    AuditTrace.note('frozen_full_recovery');\n    work.add('frozen_full_recoveries');")
        verify = store.with_name("verification.dart")
        replace(verify, "import 'work.dart';", "import 'work.dart';\nimport 'audit_trace.dart';")
        replace(verify, "  work?.add('full_verifications');", "  AuditTrace.note('full_verify');\n  work?.add('full_verifications');")
        legacy = mobile / "lib/src/offline/offline_store.dart"
        replace(legacy, "import '../money.dart';", "import '../money.dart';\nimport '../segmented/audit_trace.dart';")
        replace(legacy, "  Future<OfflineBaseline?> loadBaseline() async {", "  Future<OfflineBaseline?> loadBaseline() async {\n    AuditTrace.note('legacy_full_read');")
        replace(legacy, "  String recoveryLineageFingerprint(OfflineBaseline baseline) {", "  String recoveryLineageFingerprint(OfflineBaseline baseline) {\n    AuditTrace.note('lineage_hash');")
        start = time.monotonic()
        with (out / "cost.log").open("w") as log:
            result = subprocess.run([
                "/home/hjkerman/.flutter/bin/flutter", "test", "--no-pub", "--machine",
                "--dart-define=AUDIT_E4_COST=" + str(out / "cost.json"),
                str(HERE / "cost_test.dart"),
            ], cwd=mobile, stdout=log, stderr=subprocess.STDOUT, timeout=1500)
        summary = dict(exit=result.returncode, seconds=time.monotonic()-start)
        (out / "cost-exit.json").write_text(json.dumps(summary))
        print(json.dumps(summary))
        if result.returncode:
            print("\n".join((out / "cost.log").read_text().splitlines()[-15:]))
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))

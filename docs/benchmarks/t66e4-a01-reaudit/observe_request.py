"""원 assertion은 유지하고 폐기용 copy에서 실제 ticket과 A source를 추가 관찰한다."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def main(destination):
    out = Path(destination).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mn-e4-ticket-observer-") as directory:
        project = Path(directory)
        mobile = project / "mobile"
        shutil.copytree(ROOT / "mobile/lib", mobile / "lib")
        shutil.copytree(ROOT / "mobile/assets", mobile / "assets")
        for name in [".venv", "docs", "scripts"]:
            (project / name).symlink_to(ROOT / name, target_is_directory=True)
        for name in ["pubspec.yaml", "pubspec.lock", ".flutter-plugins-dependencies"]:
            shutil.copyfile(ROOT / "mobile" / name, mobile / name)
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
        coordinator = mobile / "lib/src/coherent_refresh_coordinator.dart"
        code = coordinator.read_text()
        before = """  RefreshTicket begin(int lineageGeneration, int authenticationGeneration) =>
      RefreshTicket(
          lineageGeneration, authenticationGeneration, ++_requestGeneration);"""
        after = """  RefreshTicket begin(int lineageGeneration, int authenticationGeneration) {
    final ticket=RefreshTicket(lineageGeneration,authenticationGeneration,++_requestGeneration);
    const output=String.fromEnvironment('REAUDIT_TICKETS');
    File(output).writeAsStringSync(jsonEncode({'lineage':ticket.lineageGeneration,'authentication':ticket.authenticationGeneration,'request':ticket.requestGeneration})+'\\n',mode:FileMode.append,flush:true);
    return ticket;
  }"""
        assert code.count(before) == 1
        coordinator.write_text("import 'dart:convert';\nimport 'dart:io';\n" + code.replace(before, after))
        code = (ROOT / "docs/benchmarks/t66e4-audit/stale_recovery_test.dart").read_text()
        code = code.replace("../../../mobile/test/", (ROOT / "mobile/test").as_uri() + "/")
        before = "      await workspace.entered.future.timeout(const Duration(seconds: 90));"
        after = before + """
      const observed=String.fromEnvironment('REAUDIT_SOURCE_A');
      final observedDb=sqlite3.open(store.path);
      File(observed).writeAsStringSync(jsonEncode({
        'source':jsonDecode(File('${workspace.root.path}/e4-source.json').readAsStringSync()),
        'accepted':observedDb.select('SELECT * FROM accepted').map((r)=>Map<String,dynamic>.from(r)).toList(),
        'frozen':observedDb.select('SELECT * FROM frozen').map((r)=>r.map((k,v)=>MapEntry(k,v is List<int> ? jsonDecode(utf8.decode(v)) : v))).toList(),
        'roots':observedDb.select('SELECT * FROM generation_roots').map((r)=>Map<String,dynamic>.from(r)).toList()
      }),flush:true);
      observedDb.close();"""
        assert code.count(before) == 1
        code = code.replace(before, after)
        worker = mobile / "test/observed_test.dart"
        worker.parent.mkdir()
        (worker.parent / "support").symlink_to(ROOT / "mobile/test/support", target_is_directory=True)
        worker.write_text(code)
        with (out / "observed.log").open("w") as log:
            result = subprocess.run([
                "/home/hjkerman/.flutter/bin/flutter", "test", "--no-pub", "--machine",
                "--dart-define=REAUDIT_TICKETS=" + str(out / "tickets.jsonl"),
                "--dart-define=REAUDIT_SOURCE_A=" + str(out / "source-a.json"),
                "--dart-define=AUDIT_E4_STALE_OUTPUT=" + str(out / "persisted.json"),
                str(worker),
            ], cwd=mobile, stdout=log, stderr=subprocess.STDOUT, timeout=600)
        (out / "exit.json").write_text(json.dumps(dict(exit_code=result.returncode)))
        print(json.dumps(dict(exit_code=result.returncode)))
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))

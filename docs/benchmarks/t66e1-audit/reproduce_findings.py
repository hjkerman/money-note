"""실제 격리 ASGI 응답과 직접 SQLite 조회로 E1 반례를 보존한다."""

import base64
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from uuid import uuid4

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "docs/benchmarks/t66d3c-audit"))

from fastapi.testclient import TestClient  # noqa: E402
from isolated_sync.http import create_app  # noqa: E402
from isolated_sync.observation import Evaluation, ObservationRepository  # noqa: E402
from isolated_sync.observation_schema import ObservationSandbox  # noqa: E402
from isolated_sync.raw import setting_money  # noqa: E402
from isolated_sync.canonical import CanonicalError  # noqa: E402
from test_audit import seed, TOKEN  # noqa: E402


def main():
    # import 이름이 같은 기존 감사 module과 새 Harness를 분리한다.
    import importlib.util
    spec = importlib.util.spec_from_file_location("e1_audit", HERE / "test_audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evidence = {"money": [], "schema": {}}
    now = datetime(2026, 10, 12, tzinfo=timezone.utc)
    for codepoint in range(0x1C, 0x20):
        text = chr(codepoint) + "+0001000.00" + chr(codepoint)
        with ObservationSandbox() as db, tempfile.TemporaryDirectory(prefix="e1-money-") as directory:
            with db.connect() as connection:
                seed(connection, history=0)
                connection.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES('base_next_month_liquidity',?)", (text,))
            db.install()
            db.bootstrap()
            repo = ObservationRepository(db, clock=lambda: now,
                       evaluation=lambda: Evaluation(date(2026, 10, 12), 540))
            with TestClient(create_app(repo)) as client:
                headers = {"Authorization": "Bearer " + TOKEN}
                created = client.post("/api/sync/v1/observations", headers=headers,
                    json=dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0))
                assert created.status_code == 201, created.text
                manifest = created.json()
                root = manifest["target"]["raw_ref"]
                with db.connect() as connection:
                    raw_root = json.loads(connection.execute("SELECT body FROM sync_objects WHERE hash=?",
                                                           (root["hash"],)).fetchone()[0])
                    entry = next(t for t in raw_root["tables"] if t["name"] == "app_settings")
                    reference = entry["root"]["ref"]
                    assert entry["root"]["height"] == 0
                    original = connection.execute("SELECT value FROM app_settings WHERE key='base_next_month_liquidity'").fetchone()[0]
                response = client.post("/api/sync/v1/observations/" + manifest["observation_id"] + "/objects",
                    headers=headers, json=dict(protocol=1, request_id=str(uuid4()), items=[
                        dict(path=[root["hash"], reference["hash"]], offset="0", length=int(reference["bytes"]))]))
                assert response.status_code == 200, response.text
                chunk = response.json()["chunks"][0]
                raw = base64.b64decode(chunk["data_base64"])
                independent_hash = hashlib.sha256(b"money-note.sync.v1/snapshot-leaf\0" + raw).hexdigest()
                assert independent_hash == reference["hash"] and original == text
                item = dict(kind="snapshot-leaf", ref=reference, data_base64=chunk["data_base64"])
                temporary = Path(directory)
                fixture = temporary / "fixture.json"
                fixture.write_text(json.dumps(dict(manifest_base64=base64.b64encode(created.content).decode())))
                job = temporary / "job.json"
                job.write_text(json.dumps(dict(action="put", fixture=str(fixture), root=str(temporary / "store"), objects=[item])))
                result = subprocess.run(module.COMMAND + [str(job)], cwd=ROOT, capture_output=True, text=True, timeout=40)
                assert result.returncode == 0, result.stderr
                observed = json.loads(result.stdout)
                evidence["money"].append(dict(codepoint=f"U+{codepoint:04X}",
                    persisted_string_repr=repr(original), manifest_status=created.status_code,
                    object_status=response.status_code, independent_hash=independent_hash,
                    ref=reference, data_base64=item["data_base64"], dart=observed,
                    expected="서버가 검증하여 전달한 bytes의 저장 성공"))
    with tempfile.TemporaryDirectory(prefix="e1-schema-") as directory:
        audit = module.Harness(Path(directory))
        text = "\ufeff1000\ufeff"
        try:
            setting_money(text)
            raise AssertionError("server unexpectedly accepted BOM money")
        except CanonicalError as error:
            server_error = str(error)
        item = module.rehash(module.DATA["settings"][0],
            lambda b: b["rows"][0]["value"].update(value=text))
        evidence["bom_money"] = dict(value_repr=repr(text), server_error=server_error,
            dart=audit.call("verify", [item])["results"][0],
            expected="서버가 거부한 금액 문자열을 E1도 거부함")
        assert audit.call("open")["ok"]
        before = audit.rows("SELECT objects,payload FROM usage")
        audit.sql("DROP TRIGGER object_usage;")
        result = audit.call("put", [module.EMPTY, module.HOT], limits=dict(objectCount=1))
        evidence["schema"] = dict(initial_usage=before, missing_trigger="object_usage",
            configured_object_count=1, dart=result, actual_objects=audit.rows("SELECT count(*) FROM objects"),
            actual_payload=audit.rows("SELECT sum(length(body)) FROM objects"),
            usage_after=audit.rows("SELECT objects,payload FROM usage"),
            sqlite_integrity=audit.rows("PRAGMA integrity_check"),
            foreign_keys=audit.rows("PRAGMA foreign_key_check"),
            reopen=audit.call("open"), expected="schema 누락을 쓰기 전에 거부하고 quota를 초과하지 않음")
    (HERE / "findings.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(dict(money_cases=len(evidence["money"]), schema_actual=evidence["schema"]["actual_objects"])))


if __name__ == "__main__":
    main()

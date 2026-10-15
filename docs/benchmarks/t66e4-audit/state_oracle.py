"""새 연결의 실제 E4 저장 행을 검사하는 독립 C1/graph/lineage oracle."""
import base64
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
EXPORT_ORDER = {
    'ledger_entries': ('book_section','entry_kind','entry_date','sort_order','id'),
    'monthly_panels': ('month','panel_type','sort_order','id'),
    'cash_flows': ('occurred_on','sort_order','id'),
    'card_payment_batches': ('id',), 'card_payment_batch_items': ('batch_id','id'),
    'card_payment_events': ('event_date','id'),
    'card_payment_allocations': ('payment_event_id','id'),
    'card_payment_deferrals': ('target_payment_month','entry_payment_key'),
    'notification_candidate_registrations': ('registration_key',),
    'app_settings': ('key',), 'app_labels': ('key',),
}


def sqlite_sort(value):
    return (0, 0) if value is None else (2, value.encode('utf8')) if isinstance(value, str) else (1, value)


spec = importlib.util.spec_from_file_location(
    "independent_e3_graph", ROOT / "docs/benchmarks/t66e3-audit/oracle.py"
)
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
sys.path.insert(0, str(ROOT / "backend"))
from app.services.snapshot import (  # noqa: E402
    snapshot_state_fingerprint, validate_reconciliation_snapshot,
)


def inspect(path, workspace=None):
    with closing(sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        namespace = db.execute("SELECT namespace FROM profile").fetchone()[0]
        generations = {}
        for row in db.execute("SELECT * FROM generations"):
            manifest, receipt = json.loads(row["manifest"]), json.loads(row["receipt"])
            assert hashlib.sha256(row["manifest"]).hexdigest() == row["manifest_checksum"]
            assert hashlib.sha256(row["receipt"]).hexdigest() == row["receipt_checksum"]
            target = manifest["target"]
            roots = {x[0] for x in db.execute(
                "SELECT hash FROM generation_roots WHERE generation_id=?", (row["id"],)
            )}
            assert roots == {target[k + "_ref"]["hash"] for k in ("raw", "index", "hot", "control")}
            pending, seen, objects = list(roots), set(), []
            while pending:
                digest = pending.pop()
                if digest in seen:
                    continue
                seen.add(digest)
                stored = db.execute("SELECT body FROM objects WHERE hash=?", (digest,)).fetchone()
                assert stored is not None, "required object missing"
                raw = bytes(stored[0])
                body = json.loads(raw)
                assert oracle.c1(body) == raw and oracle.h(body["kind"], raw) == digest
                children = {e[0]["hash"] for e in oracle.edges(body)}
                assert children == {e[0] for e in db.execute("SELECT child FROM edges WHERE parent=?", (digest,))}
                pending.extend(children)
                objects.append(dict(ref=dict(hash=digest, bytes=str(len(raw))), data_base64=base64.b64encode(raw).decode()))
            # Raw state is independently decoded, not taken from an E4 flag.
            source = {t: [] for t in oracle.TABLES}
            control = None
            for item in objects:
                body = json.loads(base64.b64decode(item["data_base64"]))
                if body["kind"] == "snapshot-leaf":
                    source[body["table"]].extend(r["value"] for r in body["rows"])
                if body['kind'] == 'control':
                    control = body
            fixture = dict(manifest=manifest, objects=objects, source=source)
            closure, raw_rows, edges = oracle.graph(fixture)
            facts = oracle.facts(target, raw_rows)
            assert oracle.patricia(target, facts) == target["index_ref"]
            assert row["object_count"] == len(closure) == receipt["objects"]
            assert receipt["edges"] == edges and int(receipt["facts"]) == len(facts)
            assert receipt["target"] == target
            generations[row["id"]] = dict(sync_root=target["sync_root"], objects=len(closure),
                closure=sorted(closure), source=source, control=control, receipt=row["receipt_checksum"])
        pointers = {}
        for table, current in (("accepted", "current_id"), ("installed", "generation_id")):
            p = db.execute("SELECT * FROM " + table).fetchone()
            if p:
                p = dict(p)
                identity = dict(namespace=namespace, current=p[current], previous=p["previous_id"], sequence=str(p["sequence"]))
                assert p["checksum"] == hashlib.sha256(oracle.c1(identity)).hexdigest()
                for ident in (p[current], p["previous_id"]):
                    assert ident is None or ident in generations
            pointers[table] = p
        frozen = []
        for f in db.execute("SELECT * FROM frozen"):
            b = json.loads(f["binding"])
            assert hashlib.sha256(f["binding"]).hexdigest() == f["checksum"]
            assert b["namespace"] == namespace and b["generation"] == f["generation_id"]
            assert f["receipt_checksum"] == generations[f["generation_id"]]["receipt"]
            frozen.append(dict(id=f["id"], generation=f["generation_id"], state=f["state"], binding=b))
        result = dict(pointers=pointers, frozen=frozen, generations=generations,
            objects=db.execute("SELECT count(*) FROM objects").fetchone()[0],
            pins=db.execute("SELECT count(*) FROM generation_roots").fetchone()[0])
    if workspace:
        folder = Path(workspace)
        bfile = folder / "offline-mode/baseline.json"
        if bfile.exists() and any(f['state'] == 'installed' for f in frozen):
            baseline = json.loads(bfile.read_bytes())
            snapshot = baseline["authoritative_snapshot"]
            validate_reconciliation_snapshot(snapshot)
            assert snapshot_state_fingerprint(snapshot) == baseline["server_state_fingerprint"]
            lineage = hashlib.sha256(oracle.c1(dict(schema_version=1, origin="mobile-baseline-lineage", baseline=baseline))).hexdigest()
            for f in frozen:
                if f["state"] == "installed":
                    assert f["binding"]["legacy_lineage"] == lineage
                    assert f["binding"]["legacy_fingerprint"] == baseline["server_state_fingerprint"]
                    assert f["binding"]["baseline_sha256"] == hashlib.sha256(oracle.c1(baseline)).hexdigest()
                    assert baseline["server_state_fingerprint"] != generations[f["generation"]]["sync_root"]
                    control = generations[f['generation']]['control']
                    for snapshot_key, control_key in [('schema_version','snapshot_schema'), ('recurring_ownership_version','recurring_ownership_version'), ('exported_at','exported_at'), ('range','range'), ('card_charge_policy','card_charge_policy')]:
                        assert snapshot[snapshot_key] == control[control_key]
                    # Independently implement the binding export order, NULL-first and UTF8 BINARY.
                    for table in oracle.TABLES:
                        expected_rows = sorted(generations[f['generation']]['source'][table], key=lambda r: tuple(sqlite_sort(r[k]) for k in EXPORT_ORDER[table]))
                        assert snapshot['data'][table] == expected_rows
                        assert snapshot['manifest']['tables'][table]['columns'] == control['columns'][table]
            result["legacy"] = dict(fingerprint=baseline["server_state_fingerprint"], lineage=lineage,
                sha256=hashlib.sha256(bfile.read_bytes()).hexdigest())
        elif bfile.exists():
            # Initial test baseline is the existing legacy fixture, not an installed E4 v7.
            result['legacy'] = dict(sha256=hashlib.sha256(bfile.read_bytes()).hexdigest(), e4_installed=False)
    return result


if __name__ == "__main__":
    print(json.dumps(inspect(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else None)))

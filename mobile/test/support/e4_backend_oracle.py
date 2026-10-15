"""Independent complete legacy oracle from a new synthetic backend only."""
import base64
import contextlib
import importlib.util
import io
import json
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.snapshot import (  # noqa: E402
    _build_manifest, _snapshot_metadata, snapshot_state_fingerprint,
    validate_reconciliation_snapshot,
)


def main(empty=False):
    # Reuse the historical producer without editing its bytes/expectations.
    # Only this NEW disposable fixture's seed is extended for ordering/Unicode.
    spec = importlib.util.spec_from_file_location("e4_probe_seed", ROOT / "docs/benchmarks/t66e4-contract/probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    probe.ROWS = {} if empty else {table: dict(row) for table, row in probe.ROWS.items()}
    original_insert = probe.insert

    def insert(conn, table, row):
        row = dict(row)
        if "title" in row:
            row["title"] += " 합성 한글 e\u0301 😀"
        original_insert(conn, table, row)
        if table == "ledger_entries":
            original_insert(conn, table, dict(id=101, book_section="archive",
                entry_kind="expense", entry_date=None, title="원문 😀 e\u0301",
                amount_value=1000.0, sort_order=7, payment_key="e4-null-archive"))
        if table == "app_labels":
            for key in ("\ue000", "😀", "e\u0301"):
                original_insert(conn, table, dict(key=key, value="원문 " + key))
    probe.insert = insert
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        probe.main()
    evidence = json.loads(output.getvalue())
    control = next(json.loads(base64.b64decode(o["data_base64"]))
                   for o in evidence["fixture"]["objects"]
                   if json.loads(base64.b64decode(o["data_base64"]))["kind"] == "control")
    # Actual SQLite exporter ordered these rows. NOT the adapter's sort/hash.
    snapshot = dict(schema_version=control["snapshot_schema"],
                    recurring_ownership_version=control["recurring_ownership_version"],
                    exported_at=control["exported_at"], range=control["range"],
                    card_charge_policy=control["card_charge_policy"],
                    data=evidence["wire"]["snapshot"]["data"])
    snapshot["manifest"] = _build_manifest(
        snapshot["data"], empty_table_columns=control["columns"],
        policy_context=control["card_charge_policy"],
        snapshot_metadata=_snapshot_metadata(snapshot),
    )
    snapshot["snapshot_id"] = snapshot["manifest"]["content_sha256"]
    validate_reconciliation_snapshot(snapshot)
    evidence["expected_snapshot"] = snapshot
    evidence["expected_restore_admission"] = True
    evidence["expected_fingerprint"] = snapshot_state_fingerprint(snapshot)
    print(json.dumps(evidence, ensure_ascii=True))


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "--empty":
        main(empty=len(sys.argv) > 1)
    else:
        root = Path(sys.argv[1])
        assert (root / "e4-synthetic-owned").read_text() == "E4 TEST"
        baseline = json.loads((root / "offline-mode/baseline.json").read_bytes())
        validate_reconciliation_snapshot(baseline["authoritative_snapshot"])
        assert snapshot_state_fingerprint(baseline["authoritative_snapshot"]) == baseline["server_state_fingerprint"]
        journal = [json.loads(line) for line in (root / "offline-mode/journal.ndjson").read_text().splitlines()]
        assert [row["sequence"] for row in journal] == [1]
        assert journal[0]["payload"]["amount_value"] == "+0007.00"
        encoded = json.dumps(dict(schema_version=1, origin="mobile-baseline-lineage",
                                  baseline=baseline), ensure_ascii=False,
                             sort_keys=True, separators=(",", ":")).encode()
        print(json.dumps(dict(fingerprint=baseline["server_state_fingerprint"],
                             lineage=hashlib.sha256(encoded).hexdigest(), journal_count=len(journal))))

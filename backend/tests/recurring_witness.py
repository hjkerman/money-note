"""Explicit synthetic prior ownership evidence for historical-format controls.

This is NOT an inference algorithm. The checked-in synthetic scenario declares
source 41 -> generated 42; tests supply that independently known canonical
relationship as an additional recovery document, never manufacture production
evidence or change the historical fixture itself.
"""

import json
from pathlib import Path

from app.services import snapshot


def preserve_synthetic_witnesses(db_path: Path) -> None:
    directory = db_path.parent / "snapshot-backups"
    directory.mkdir(exist_ok=True)
    for version in (4, 5, 6):
        artifact = json.loads((Path(__file__).parent / "fixtures" / f"snapshot_v{version}_recurring.json").read_text())
        for table in snapshot.SNAPSHOT_TABLES:
            artifact["data"].setdefault(table, [])
        for row in artifact["data"]["ledger_entries"]:
            row.setdefault("source_planned_entry_id", None)
        source = next(row for row in artifact["data"]["ledger_entries"] if row["id"] == 41)
        child = next(row for row in artifact["data"]["ledger_entries"] if row["id"] == 42)
        child.update(source_planned_entry_id=41, confirmed_month=source["confirmed_month"],
                     confirmed_at=source["confirmed_at"])
        artifact.update(schema_version=7, recurring_ownership_version=1)
        artifact["manifest"] = snapshot._build_manifest(artifact["data"],
            policy_context=artifact["card_charge_policy"], snapshot_metadata=snapshot._snapshot_metadata(artifact))
        artifact["snapshot_id"] = artifact["manifest"]["content_sha256"]
        (directory / f"pre_restore-20260611T00000{version}Z.money-note-snapshot.json").write_text(json.dumps(artifact))

"""표시된 임시 synthetic workspace의 bytes와 기존 logical hashes만 독립 검사한다."""

import hashlib
import json
from pathlib import Path
import sys


def canonical(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def inspect(root):
    root = Path(root)
    assert (root / "audit-owned").read_text() == "E4-P0 SYNTHETIC AUDIT"
    folder = root / "offline-mode"
    baseline = json.loads((folder / "baseline.json").read_bytes())
    snapshot = baseline["authoritative_snapshot"]
    fingerprint = hashlib.sha256(
        canonical(
            {
                "schema_version": snapshot["schema_version"],
                "range": snapshot["range"],
                "card_charge_policy": snapshot["card_charge_policy"],
                "data": snapshot["data"],
            }
        )
    ).hexdigest()
    assert fingerprint == baseline["server_state_fingerprint"]
    assert baseline["schema_version"] == 4
    value = next(
        r["value"]
        for r in snapshot["data"]["app_settings"]
        if r["key"] == "cash_flow_balance"
    )
    assert value == "\x1c+0001000.00\x1f"
    assert baseline["settings"]["cash_flow_balance"] == value
    lineage = hashlib.sha256(
        canonical(
            dict(schema_version=1, origin="mobile-baseline-lineage", baseline=baseline)
        )
    ).hexdigest()
    normalized = json.loads(json.dumps(snapshot))
    for row in normalized["data"]["app_settings"]:
        if row["key"] == "cash_flow_balance":
            row["value"] = "1000"
    normalized_hash = hashlib.sha256(
        canonical(
            {
                "schema_version": normalized["schema_version"],
                "range": normalized["range"],
                "card_charge_policy": normalized["card_charge_policy"],
                "data": normalized["data"],
            }
        )
    ).hexdigest()
    assert normalized_hash != fingerprint
    return dict(
        fingerprint=fingerprint,
        lineage=lineage,
        original_codepoints=[ord(c) for c in value],
        normalization_changes_fingerprint=True,
        files={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.glob("*")
            if p.is_file()
        },
    )


if __name__ == "__main__":
    print(json.dumps(inspect(sys.argv[1]), ensure_ascii=False))

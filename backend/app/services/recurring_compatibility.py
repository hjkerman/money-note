"""One-time, evidence-only upgrade of historical explicit recurring links.

The old writer stored the source ID, but the child had no epoch. Month close
copied it with a new row ID/creation time; its payment key survived.
Only a complete canonical relationship witness can recover that lost identity.
The original writer did not persist any alternative immutable epoch identity;
timestamps, even with a source ID and a unique candidate, cannot recover it.
Amounts, descriptions, occurrence dates and book locations are never proof.
"""

from collections.abc import Mapping, Sequence
from datetime import date
import re
from typing import Any

from app.services.legacy_recurring import (
    validate_recurring_ownership, validate_source_epoch, valid_nonnegative_money,
)

RECURRING_OWNERSHIP_VERSION = 1


def _valid_time(value: Any) -> bool:
    from app.services.snapshot import _validate_confirmation_timestamp

    try:
        _validate_confirmation_timestamp(value, "invalid historical identity timestamp")
    except ValueError:
        return False
    return True


def _valid_period(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", value):
        return False
    try:
        date.fromisoformat(value + "-01")
    except ValueError:
        return False
    return True


def _closed(data: Mapping[str, Any]) -> str:
    return next((row["value"] for row in data.get("app_settings", ())
                 if row.get("key") == "last_closed_month"), "0000-00")


def _proofs(data: Mapping[str, Any]) -> dict[str, set[tuple[Any, str, str, str]]]:
    rows = data["ledger_entries"]
    by_id = {row.get("id"): row for row in rows}
    if None in by_id or len(by_id) != len(rows):
        raise ValueError("historical recurring evidence has duplicate or missing IDs")
    keyed = [row for row in rows if row.get("payment_key") is not None]
    if any(not isinstance(row["payment_key"], str) or not row["payment_key"] for row in keyed):
        raise ValueError("historical recurring evidence has no valid stable payment key")
    if len({row["payment_key"] for row in keyed}) != len(keyed):
        raise ValueError("historical recurring evidence has duplicate payment keys")
    sources = {key: row for key, row in by_id.items() if row.get("entry_kind") == "planned"}
    for row in rows:
        if row.get("entry_kind") == "planned" or row.get("source_planned_entry_id") is not None:
            validate_source_epoch(row)
    try:
        validate_recurring_ownership(rows, _closed(data), require_execution_epoch=False)
    except ValueError:
        # An epoch-less historical document is not an epoch witness. Reusing
        # its timestamps would only move the same unsafe inference elsewhere.
        return {}
    result: dict[str, set[tuple[Any, str, str, str]]] = {}
    for row in keyed:
        source = sources.get(row.get("source_planned_entry_id"))
        if (source is None or row.get("entry_kind") != "expense"
            or not _valid_time(source.get("created_at")) or not valid_nonnegative_money(row.get("amount_value"))):
            continue
        period, timestamp = row.get("confirmed_month"), row.get("confirmed_at")
        if _valid_period(period) and _valid_time(timestamp):
            result.setdefault(row["payment_key"], set()).add(
                (source["id"], source["created_at"], period, timestamp))
    return result


def canonicalize_legacy_recurring(
    data: Mapping[str, Any], witnesses: Sequence[Mapping[str, Any]] = (),
    *, require_execution_epoch: bool = True,
) -> list[dict[str, Any]]:
    """Return canonical rows or fail without changing the caller's representation."""
    rows = [dict(row) for row in data["ledger_entries"]]
    by_id = {row.get("id"): row for row in rows}
    proofs = _proofs(data)
    claims: dict[str, set[tuple[Any, Any]]] = {}
    epochs: dict[str, set[tuple[Any, Any, Any, Any]]] = {}
    # Even an epoch-less document can contradict a stable source assertion.
    # It cannot supply an epoch proof, but must not be silently discarded to
    # make another witness unique.
    for document in (data, *witnesses):
        owners = {row.get("id"): row for row in document["ledger_entries"]
                  if row.get("entry_kind") == "planned"}
        for row in document["ledger_entries"]:
            key, source_id = row.get("payment_key"), row.get("source_planned_entry_id")
            if key and source_id is not None:
                source = owners.get(source_id)
                if source is None:
                    raise ValueError("legacy recurring witness has no valid source")
                claims.setdefault(key, set()).add((source_id, source.get("created_at")))
                period, timestamp = row.get("confirmed_month"), row.get("confirmed_at")
                if period is not None and timestamp is not None:
                    if not _valid_period(period) or not _valid_time(timestamp):
                        raise ValueError("legacy recurring witness has no valid confirmation epoch")
                    epochs.setdefault(key, set()).add((source_id, source.get("created_at"), period, timestamp))
    if any(len(owners) != 1 for owners in claims.values()):
        raise ValueError("legacy recurring witness contradicts the source identity")
    if any(len(identities) != 1 for identities in epochs.values()):
        raise ValueError("legacy recurring confirmation has conflicting immutable epoch witnesses")
    for witness in witnesses:
        for key, identities in _proofs(witness).items():
            proofs.setdefault(key, set()).update(identities)
    for row in rows:
        source_id = row.get("source_planned_entry_id")
        if row.get("confirmed_month") is not None or row.get("confirmed_at") is not None:
            continue
        identities = proofs.get(row.get("payment_key"), set())
        if source_id is None:
            # A source-less historical child is recoverable only by its
            # already-preserved canonical key ownership, never by resemblance.
            if not identities or row.get("entry_kind") != "expense":
                continue
            if len(identities) != 1:
                raise ValueError("legacy recurring confirmation source has conflicting immutable witnesses")
            source_id = next(iter(identities))[0]
        source = by_id.get(source_id)
        if source is None or source.get("entry_kind") != "planned" or row.get("entry_kind") != "expense":
            raise ValueError("legacy recurring link has no valid source")
        if len(identities) != 1:
            raise ValueError("legacy recurring confirmation epoch has no unique immutable witness")
        owner_id, owner_created, period, timestamp = next(iter(identities))
        if owner_id != source_id or owner_created != source.get("created_at"):
            raise ValueError("legacy recurring witness contradicts the source identity")
        row.update(source_planned_entry_id=source_id, confirmed_month=period, confirmed_at=timestamp)
    validate_recurring_ownership(rows, _closed(data), require_execution_epoch=require_execution_epoch)
    return rows


def legacy_recurring_witnesses() -> list[dict[str, Any]]:
    """Read immutable recovery documents; never restore, rewrite or repair them."""
    from app.config import get_settings
    from app.money import validate_money_payload
    from app.services.snapshot import (
        PRE_RESTORE_FILENAME_RE, _validate_snapshot, parse_snapshot_json,
    )

    directory = get_settings().db_path.parent / "snapshot-backups"
    witnesses = []
    for path in sorted(directory.glob("*.money-note-snapshot.json")):
        if not PRE_RESTORE_FILENAME_RE.fullmatch(path.name):
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError("historical recurring witness must be a regular file")
        # Invalid evidence cannot silently disappear to resolve a conflict.
        document = parse_snapshot_json(path.read_bytes())
        _validate_snapshot(document)
        if document["schema_version"] != 7:
            continue
        validate_money_payload(document["data"])
        if "recurring_ownership_version" in document:
            validate_recurring_ownership(document["data"]["ledger_entries"], _closed(document["data"]))
        witnesses.append(document["data"])
    return witnesses


def upgrade_legacy_recurring(conn: Any, *, dry_run: bool = False) -> int:
    """The caller owns BEGIN/COMMIT, including the semantic version checkpoint."""
    data = {"ledger_entries": [dict(row) for row in conn.execute("SELECT * FROM ledger_entries")],
            "app_settings": [dict(row) for row in conn.execute("SELECT key,value FROM app_settings")]}
    try:
        validate_recurring_ownership(data["ledger_entries"], _closed(data), require_execution_epoch=False)
        needs_epoch = False
    except ValueError:
        needs_epoch = True
    rows = canonicalize_legacy_recurring(
        data, legacy_recurring_witnesses() if needs_epoch else (), require_execution_epoch=False)
    changed = 0
    for before, after in zip(data["ledger_entries"], rows, strict=True):
        if (before.get("source_planned_entry_id"), before.get("confirmed_month"), before.get("confirmed_at")) != (
            after.get("source_planned_entry_id"), after.get("confirmed_month"), after.get("confirmed_at")
        ):
            if not dry_run:
                _write_epoch(conn, after)
            changed += 1
    return changed


def _write_epoch(conn: Any, row: Mapping[str, Any]) -> None:
    conn.execute("UPDATE ledger_entries SET source_planned_entry_id=?,confirmed_month=?,confirmed_at=? WHERE id=?",
                 (row["source_planned_entry_id"], row["confirmed_month"], row["confirmed_at"], row["id"]))

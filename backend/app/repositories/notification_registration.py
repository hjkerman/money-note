import hashlib
import json
from typing import Any


def registration_fingerprint(target: str, values: dict[str, Any], *, legacy_panel: bool = False) -> str:
    fields = (
        ("entry_date", "usage_place", "usage_item", "title", "amount_value", "spending_category")
        if target == "ledger"
        else ("month", "panel_type", "title", "spent_on", "amount_value")
    )
    if target != "ledger" and not legacy_panel:
        fields += ("discount_override", "discount_amount")
    if target == "ledger":
        fields += tuple(
            field for field in ("discount_enabled", "discount_override_amount") if field in values
        )
    payload = [target, *(values.get(field) for field in fields)]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def existing_registration(conn: Any, key: str, target: str, fingerprint: str) -> int | None:
    row = conn.execute(
        "SELECT target, target_id, request_fingerprint FROM notification_candidate_registrations WHERE registration_key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    if row["target"] != target or row["request_fingerprint"] != fingerprint:
        raise ValueError("이미 등록한 알림 후보를 다른 내용이나 등록 대상으로 다시 사용할 수 없습니다.")
    return int(row["target_id"])


def save_registration(conn: Any, key: str, target: str, target_id: int, fingerprint: str) -> None:
    conn.execute(
        "INSERT INTO notification_candidate_registrations(registration_key, target, target_id, request_fingerprint) VALUES (?, ?, ?, ?)",
        (key, target, target_id, fingerprint),
    )

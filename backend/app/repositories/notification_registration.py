import hashlib
import json
from typing import Any


def registration_fingerprint(target: str, values: dict[str, Any], *, legacy_panel: bool = False) -> str:
    if target == "ledger":
        # Bind the *effective input*, not its legacy/current wire spelling.
        # The initial override helper replaces the legacy stored discount fields.
        if values.get("discount_override_amount") is not None:
            discount = ["manual", values["discount_override_amount"]]
            residual_aux = None
        elif values.get("discount_enabled") is False:
            discount = ["manual", 0]
            residual_aux = None
        elif values.get("discount_override") == 1:
            discount = ["manual", values.get("aux_amount_value") or 0]
            residual_aux = None
        else:
            discount = ["automatic"]
            residual_aux = values.get("aux_amount_value")
        fields = (
            "book_section", "entry_kind", "entry_date", "date_label", "group_label",
            "title", "usage_place", "usage_item", "amount_value", "amount_expr",
            "aux_amount_expr", "extra_value", "sort_order", "due_day",
            "confirmed_at", "spending_category", "payment_key",
        )
        payload = [target, *(values.get(field) for field in fields), residual_aux, discount]
    else:
        fields = ("month", "panel_type", "title", "spent_on", "amount_value")
        if not legacy_panel:
            fields += ("discount_override", "discount_amount")
        payload = [target, *(values.get(field) for field in fields)]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def legacy_ledger_registration_fingerprint(values: dict[str, Any]) -> str:
    """Read-only compatibility for registrations written before full input binding."""
    fields = ("entry_date", "usage_place", "usage_item", "title", "amount_value", "spending_category")
    fields += tuple(field for field in ("discount_enabled", "discount_override_amount") if field in values)
    payload = ["ledger", *(values.get(field) for field in fields)]
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

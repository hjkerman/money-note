from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import date, datetime, timezone
from typing import Any

from app.db import session
from app.repositories.cash_flows import create_cash_flow
from app.repositories.entries import confirm_planned_entry, create_entry
from app.schemas import (
    CashFlowIn,
    LedgerEntryIn,
    OfflineMobileWinsIn,
    OfflineReconciliationOperationIn,
    OfflineRecoveryPointIn,
)
from app.services.card_payments import set_entry_discount
from app.services.clock import app_today
from app.services.panels import confirm_fixed_panel
from app.services.snapshot import (
    create_pre_reconcile_server_backup,
    export_snapshot_from_connection,
    replace_reconciliation_snapshot,
    snapshot_state_fingerprint,
    validate_reconciled_financial_state,
    validate_reconciliation_snapshot,
)
from app.services.summary import _current_summary_values


FailureInjector = Callable[[str, int | None], None]

_FORBIDDEN_DERIVED_KEYS = {
    "remaining_liquidity",
    "card_total",
    "cash_flow_balance",
    "effective_discount_amount",
    "effective_amount_value",
    "automatic_discount_amount",
    "current_spending_total",
    "summary",
}


class ReconciliationConflictError(ValueError):
    def __init__(self, current_fingerprint: str, server_changed: bool) -> None:
        super().__init__("server state changed; refresh conflict status and confirm again")
        self.current_fingerprint = current_fingerprint
        self.server_changed = server_changed


class ReconciliationDigestMismatchError(ValueError):
    pass


def export_offline_baseline() -> dict[str, Any]:
    """Mobile baseline B에 결합할 검증 가능한 authoritative Snapshot을 반환한다."""
    with session(transaction_mode="DEFERRED") as conn:
        _, snapshot = export_snapshot_from_connection(conn)
        return {
            "snapshot": snapshot,
            "state_fingerprint": snapshot_state_fingerprint(snapshot),
        }


def inspect_reconciliation(
    baseline_fingerprint: str,
    reconciliation_id: str | None = None,
) -> dict[str, Any]:
    """현재 server state와 baseline의 차이 및 durable outcome을 조회한다."""
    with session(transaction_mode="DEFERRED") as conn:
        _, snapshot = export_snapshot_from_connection(conn)
        current_fingerprint = snapshot_state_fingerprint(snapshot)
        record = (
            conn.execute(
                "SELECT * FROM offline_reconciliations WHERE reconciliation_id = ?",
                (reconciliation_id,),
            ).fetchone()
            if reconciliation_id
            else None
        )
    return {
        "baseline_fingerprint": baseline_fingerprint,
        "current_server_fingerprint": current_fingerprint,
        "server_changed": current_fingerprint != baseline_fingerprint,
        "reconciliation": _record_result(record),
    }


def create_server_recovery_point(payload: OfflineRecoveryPointIn) -> dict[str, Any]:
    """Server Wins 직전 S를 기존 Snapshot 보관 위치에 생성하고 검증한다."""
    with session(transaction_mode="IMMEDIATE") as conn:
        _, snapshot = export_snapshot_from_connection(conn)
        current_fingerprint = snapshot_state_fingerprint(snapshot)
        artifact = create_pre_reconcile_server_backup(conn)
    return {
        "reconciliation_id": payload.reconciliation_id,
        "baseline_fingerprint": payload.baseline_fingerprint,
        "current_server_fingerprint": current_fingerprint,
        "server_changed": current_fingerprint != payload.baseline_fingerprint,
        "server_artifact_filename": artifact.name,
    }


def apply_mobile_wins(
    payload: OfflineMobileWinsIn,
    *,
    failure_injector: FailureInjector | None = None,
) -> dict[str, Any]:
    """B를 복원하고 ordered J를 적용해 하나의 transaction으로 commit한다."""
    operations = list(payload.operations)
    _validate_operation_order(operations)
    request_digest = _request_digest(payload)

    existing = _load_reconciliation(payload.reconciliation_id)
    if existing is not None:
        return _existing_result(existing, request_digest)

    baseline_data = validate_reconciliation_snapshot(payload.baseline_snapshot)
    actual_baseline_fingerprint = snapshot_state_fingerprint(payload.baseline_snapshot)
    if actual_baseline_fingerprint != payload.baseline_fingerprint:
        raise ValueError("baseline fingerprint does not match baseline snapshot")

    result: dict[str, Any] | None = None
    with session(transaction_mode="IMMEDIATE") as conn:
        existing = conn.execute(
            "SELECT * FROM offline_reconciliations WHERE reconciliation_id = ?",
            (payload.reconciliation_id,),
        ).fetchone()
        if existing is not None:
            return _existing_result(existing, request_digest)

        _, current_snapshot = export_snapshot_from_connection(conn)
        current_fingerprint = snapshot_state_fingerprint(current_snapshot)
        server_changed = current_fingerprint != payload.baseline_fingerprint
        if payload.expected_server_fingerprint != current_fingerprint or (
            server_changed and not payload.confirm_server_changed
        ):
            raise ReconciliationConflictError(current_fingerprint, server_changed)

        server_artifact = create_pre_reconcile_server_backup(conn)
        conn.execute(
            """
            INSERT INTO offline_reconciliations(
                reconciliation_id, request_digest, baseline_fingerprint,
                pre_server_fingerprint, server_changed,
                server_artifact_filename, operation_count, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                payload.reconciliation_id,
                request_digest,
                payload.baseline_fingerprint,
                current_fingerprint,
                1 if server_changed else 0,
                server_artifact.name,
                len(operations),
            ),
        )

        replace_reconciliation_snapshot(conn, baseline_data)
        _inject(failure_injector, "before_replay", None)
        operation_results: list[dict[str, Any]] = []
        for operation in operations:
            operation_digest = _stable_hash(operation.model_dump(mode="json"))
            reused = conn.execute(
                """
                SELECT reconciliation_id, operation_digest
                FROM offline_reconciliation_operations
                WHERE operation_id = ?
                """,
                (operation.operation_id,),
            ).fetchone()
            if reused is not None:
                raise ValueError("offline operation_id was already reconciled")
            conn.execute(
                """
                INSERT INTO offline_reconciliation_operations(
                    operation_id, reconciliation_id, sequence, operation_digest
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    operation.operation_id,
                    payload.reconciliation_id,
                    operation.sequence,
                    operation_digest,
                ),
            )
            _inject(failure_injector, "before_operation", operation.sequence)
            operation_results.append(_apply_operation(conn, operation))
            _inject(failure_injector, "after_operation", operation.sequence)

        validate_reconciled_financial_state(conn)
        summary = _current_summary_values(conn)
        _, result_snapshot = export_snapshot_from_connection(conn)
        result_fingerprint = snapshot_state_fingerprint(result_snapshot)
        committed_at = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
        result = {
            "reconciliation_id": payload.reconciliation_id,
            "status": "committed",
            "request_digest": request_digest,
            "baseline_fingerprint": payload.baseline_fingerprint,
            "pre_server_fingerprint": current_fingerprint,
            "result_fingerprint": result_fingerprint,
            "server_changed": server_changed,
            "server_artifact_filename": server_artifact.name,
            "mobile_artifact_sha256": payload.mobile_artifact_sha256,
            "operation_count": len(operations),
            "operation_results": operation_results,
            "summary": summary,
            "committed_at": committed_at,
        }
        conn.execute(
            """
            UPDATE offline_reconciliations
            SET result_fingerprint = ?,
                result_json = ?,
                status = 'committed',
                committed_at = ?
            WHERE reconciliation_id = ?
            """,
            (
                result_fingerprint,
                _canonical_json(result),
                committed_at,
                payload.reconciliation_id,
            ),
        )
        _inject(failure_injector, "before_commit", None)

    if result is None:
        raise RuntimeError("reconciliation result was not produced")
    return result


def reconciliation_result(reconciliation_id: str) -> dict[str, Any] | None:
    record = _load_reconciliation(reconciliation_id)
    return _record_result(record)


def _apply_operation(
    conn: Any,
    operation: OfflineReconciliationOperationIn,
) -> dict[str, Any]:
    payload = operation.payload
    _reject_derived_values(payload)
    match operation.operation_type:
        case "CREATE_CARD_EXPENSE":
            result = _apply_card_expense(conn, payload)
        case "CREATE_CASH_FLOW":
            result = _apply_cash_flow(conn, payload)
        case "CONFIRM_FIXED_EXPENSE":
            result = _apply_fixed_confirmation(conn, payload)
        case "CONFIRM_PLANNED_CARD_EXPENSE":
            result = _apply_planned_confirmation(conn, payload)
        case _:
            raise ValueError("unsupported offline operation")
    return {
        "operation_id": operation.operation_id,
        "sequence": operation.sequence,
        "operation_type": operation.operation_type,
        **result,
    }


def _apply_card_expense(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    _require_payload_keys(
        payload,
        {
            "book_section",
            "entry_kind",
            "entry_date",
            "title",
            "usage_place",
            "usage_item",
            "amount_value",
            "spending_category",
            "discount_enabled",
        },
        {"discount_override_amount", "candidate_registration_key"},
    )
    if payload["book_section"] != "current" or payload["entry_kind"] != "expense":
        raise ValueError("offline card expense must target current expense ledger")
    amount = _integer(payload["amount_value"], "card expense amount")
    if amount < 0:
        raise ValueError("card expense amount must be non-negative")
    discount_enabled = payload["discount_enabled"]
    if not isinstance(discount_enabled, bool):
        raise ValueError("discount_enabled must be boolean")

    entry = create_entry(
        LedgerEntryIn(
            book_section="current",
            entry_kind="expense",
            entry_date=payload["entry_date"],
            date_label=None,
            group_label=None,
            title=str(payload["title"]),
            usage_place=payload["usage_place"],
            usage_item=payload["usage_item"],
            amount_value=amount,
            amount_expr=None,
            aux_amount_value=None,
            aux_amount_expr=None,
            extra_value=None,
            sort_order=0,
            due_day=None,
            confirmed_at=None,
            spending_category=payload["spending_category"],
            candidate_registration_key=payload.get("candidate_registration_key"),
        ),
        conn=conn,
    )
    payment_key = str(entry.get("payment_key") or "")
    if not payment_key:
        raise ValueError("created card expense has no payment identity")

    override = payload.get("discount_override_amount")
    if override is not None:
        discount_amount = _integer(override, "discount override")
        if discount_amount < 0 or discount_amount > amount:
            raise ValueError("discount override is outside the original amount")
        set_entry_discount(payment_key, discount_amount, conn=conn)
    elif not discount_enabled:
        set_entry_discount(payment_key, 0, conn=conn)
    return {"target_id": int(entry["id"]), "payment_key": payment_key}


def _apply_cash_flow(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    _require_payload_keys(
        payload,
        {"occurred_on", "title", "amount_value", "is_primary_income"},
        set(),
    )
    primary = _integer(payload["is_primary_income"], "is_primary_income")
    if primary not in {0, 1}:
        raise ValueError("is_primary_income must be 0 or 1")
    flow = create_cash_flow(
        CashFlowIn(
            occurred_on=payload["occurred_on"],
            title=str(payload["title"]),
            amount_value=_integer(payload["amount_value"], "cash flow amount"),
            sort_order=0,
            is_primary_income=primary,
        ),
        conn=conn,
    )
    return {"target_id": int(flow["id"])}


def _apply_fixed_confirmation(
    conn: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_payload_keys(
        payload,
        {"panel_id", "occurred_on", "actual_amount"},
        set(),
    )
    panel_id = _positive_integer(payload["panel_id"], "panel_id")
    actual_amount = _integer(payload["actual_amount"], "actual_amount")
    if actual_amount < 0:
        raise ValueError("actual_amount must be non-negative")
    result = confirm_fixed_panel(
        panel_id,
        str(payload["occurred_on"]),
        actual_amount,
        conn=conn,
        today=app_today(),
    )
    if result is None:
        raise ValueError("fixed expense target was not found in baseline")
    return {
        "target_id": int(result["panel"]["id"]),
        "created_cash_flow_id": int(result["cash_flow"]["id"]),
    }


def _apply_planned_confirmation(
    conn: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _require_payload_keys(
        payload,
        {"entry_id", "entry_date", "actual_amount"},
        set(),
    )
    entry_id = _positive_integer(payload["entry_id"], "entry_id")
    actual_amount = _integer(payload["actual_amount"], "actual_amount")
    if actual_amount < 0:
        raise ValueError("actual_amount must be non-negative")
    try:
        operation_date = date.fromisoformat(str(payload["entry_date"]))
    except ValueError:
        raise ValueError("entry_date must be YYYY-MM-DD") from None
    result = confirm_planned_entry(
        entry_id,
        today=operation_date,
        entry_date=operation_date.isoformat(),
        actual_amount=actual_amount,
        conn=conn,
    )
    if result is None:
        raise ValueError("planned expense target was not found in baseline")
    return {
        "target_id": int(result["planned"]["id"]),
        "created_entry_id": int(result["entry"]["id"]),
    }


def _validate_operation_order(
    operations: list[OfflineReconciliationOperationIn],
) -> None:
    ids: set[str] = set()
    expected_sequence = 1
    for operation in operations:
        if operation.sequence != expected_sequence:
            raise ValueError("offline journal sequence must be contiguous and ordered")
        if operation.operation_id in ids:
            raise ValueError("offline journal contains duplicate operation_id")
        ids.add(operation.operation_id)
        expected_sequence += 1


def _request_digest(payload: OfflineMobileWinsIn) -> str:
    return _stable_hash(
        {
            "schema_version": payload.schema_version,
            "baseline_fingerprint": payload.baseline_fingerprint,
            "baseline_snapshot_content_sha256": payload.baseline_snapshot.get("manifest", {}).get(
                "content_sha256"
            ),
            "operations": [operation.model_dump(mode="json") for operation in payload.operations],
            "mobile_artifact_sha256": payload.mobile_artifact_sha256,
        }
    )


def _load_reconciliation(reconciliation_id: str) -> Any | None:
    with session() as conn:
        return conn.execute(
            "SELECT * FROM offline_reconciliations WHERE reconciliation_id = ?",
            (reconciliation_id,),
        ).fetchone()


def _existing_result(record: Any, request_digest: str) -> dict[str, Any]:
    if str(record["request_digest"]) != request_digest:
        raise ReconciliationDigestMismatchError(
            "same reconciliation_id cannot be used with a different logical payload"
        )
    result = _record_result(record)
    if result is None or result.get("status") != "committed":
        raise ValueError("reconciliation is not committed")
    return result


def _record_result(record: Any | None) -> dict[str, Any] | None:
    if record is None:
        return None
    raw = record["result_json"]
    if record["status"] == "committed" and raw:
        value = json.loads(str(raw))
        if isinstance(value, dict):
            return value
    return {
        "reconciliation_id": str(record["reconciliation_id"]),
        "status": str(record["status"]),
        "request_digest": str(record["request_digest"]),
    }


def _require_payload_keys(
    payload: dict[str, Any],
    required: set[str],
    optional: set[str],
) -> None:
    missing = required - set(payload)
    unknown = set(payload) - required - optional
    if missing:
        raise ValueError("offline operation payload is missing: " + ", ".join(sorted(missing)))
    if unknown:
        raise ValueError(
            "offline operation payload has unsupported keys: " + ", ".join(sorted(unknown))
        )


def _reject_derived_values(payload: dict[str, Any]) -> None:
    forbidden = set(payload) & _FORBIDDEN_DERIVED_KEYS
    if forbidden:
        raise ValueError(
            "offline operation contains derived financial values: " + ", ".join(sorted(forbidden))
        )


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(label + " must be an integer")
    return value


def _positive_integer(value: Any, label: str) -> int:
    result = _integer(value, label)
    if result <= 0:
        raise ValueError(label + " must be positive")
    return result


def _inject(
    failure_injector: FailureInjector | None,
    stage: str,
    sequence: int | None,
) -> None:
    if failure_injector is not None:
        failure_injector(stage, sequence)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

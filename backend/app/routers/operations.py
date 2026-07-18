from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_user
from app.db import session
from app.repository import (
    create_cash_flow,
    delete_cash_flow,
    list_cash_flows,
    list_labels,
    upsert_label,
)
from app.schemas import CashFlow, CashFlowIn, SettingPatch

settings_router = APIRouter(prefix="/api/settings", tags=["settings"])
cash_router = APIRouter(prefix="/api/cash-flows", tags=["cash-flows"])
labels_router = APIRouter(prefix="/api/labels", tags=["labels"])


@settings_router.get("")
def get_settings_values(_: dict = Depends(require_user)) -> dict[str, str]:
    with session() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


@settings_router.patch("/{key}")
def patch_setting(key: str, patch: SettingPatch, _: dict = Depends(require_user)) -> dict[str, str]:
    numeric_settings = {"base_next_month_liquidity", "interest_expense", "liquidity_status", "card_limit"}
    card_last4_settings = {"owner_card_last4", "family_card_last4"}
    if key not in numeric_settings | card_last4_settings:
        raise HTTPException(status_code=404, detail="unknown setting")
    value = patch.value
    if key in numeric_settings:
        try:
            amount = float(value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{key} must be numeric") from exc
        if amount < 0:
            raise HTTPException(status_code=422, detail=f"{key} must be greater than or equal to zero")
        if not amount.is_integer():
            raise HTTPException(status_code=422, detail=f"{key} must be an integer")
        value = str(int(amount))
    else:
        value = value.strip()
        if value and (not value.isdigit() or len(value) != 4):
            raise HTTPException(status_code=422, detail=f"{key} must be empty or four digits")
    with session() as conn:
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
    return {key: value}


@cash_router.get("", response_model=list[CashFlow])
def get_cash_flows(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    limit: int | None = Query(default=None, ge=1),
    _: dict = Depends(require_user),
) -> list[dict]:
    try:
        return list_cash_flows(date_from=date_from, date_to=date_to, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@cash_router.post("", response_model=CashFlow)
def post_cash_flow(flow: CashFlowIn, _: dict = Depends(require_user)) -> dict:
    return create_cash_flow(flow)


@cash_router.delete("/{flow_id}")
def remove_cash_flow(flow_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_cash_flow(flow_id):
        raise HTTPException(status_code=404, detail="cash flow not found")
    return {"deleted": True}


@labels_router.get("")
def get_labels(_: dict = Depends(require_user)) -> dict[str, str]:
    return list_labels()


@labels_router.patch("/{key}")
def patch_label(key: str, patch: SettingPatch, _: dict = Depends(require_user)) -> dict[str, str]:
    allowed = set(list_labels().keys())
    if key not in allowed:
        raise HTTPException(status_code=404, detail="unknown label")
    return upsert_label(key, patch.value)

from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_user
from app.db import session
from app.repository import (
    append_planned_entry,
    complete_panels_by_type,
    confirm_planned_entry,
    create_panel,
    delete_panel,
    delete_panels_by_type,
    delete_planned_entry,
    list_confirmed_planned_entries,
    list_cash_flows,
    list_entries,
    list_recent_closed_month_expense_counts,
    list_panels,
    list_settings,
    reorder_current_entries,
    update_panel,
)
from app.schemas import (
    EntryReorder,
    LedgerEntry,
    MonthCloseIn,
    MonthlyPanel,
    MonthlyPanelIn,
    MonthlyPanelPatch,
    PanelDiscountPatch,
    PlannedConfirmIn,
    PlannedEntryIn,
    Summary,
)
from app.services.card_payments import current_payment_status
from app.services.judgment import app_judgment
from app.services.month import calendar_month_label, close_current_month, month_close_status
from app.services.summary import current_summary_values

router = APIRouter(prefix="/api/month/current", tags=["month"])
judgment_router = APIRouter(prefix="/api/judgment", tags=["judgment"])


@router.post("/planned", response_model=LedgerEntry)
def post_planned_entry(entry: PlannedEntryIn, _: dict = Depends(require_user)) -> dict:
    return append_planned_entry(entry)


@router.post("/planned/{entry_id}/confirm")
def post_confirm_planned_entry(entry_id: int, payload: PlannedConfirmIn | None = None, _: dict = Depends(require_user)) -> dict:
    try:
        result = confirm_planned_entry(entry_id, entry_date=payload.entry_date if payload else None)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="planned entry not found")
    return result


@router.get("/planned/confirmed", response_model=list[LedgerEntry])
def get_confirmed_planned_entries(_: dict = Depends(require_user)) -> list[dict]:
    return list_confirmed_planned_entries()


@router.delete("/planned/{entry_id}")
def remove_planned_entry(entry_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_planned_entry(entry_id):
        raise HTTPException(status_code=404, detail="planned entry not found")
    return {"deleted": True}


@router.post("/reorder", response_model=list[LedgerEntry])
def reorder_entries(payload: EntryReorder, _: dict = Depends(require_user)) -> list[dict]:
    return reorder_current_entries(payload.ordered_ids)


@router.post("/planned/reorder", response_model=list[LedgerEntry])
def reorder_planned_entries(payload: EntryReorder, _: dict = Depends(require_user)) -> list[dict]:
    return reorder_current_entries(payload.ordered_ids, entry_kind="planned")


@router.get("/panels", response_model=list[MonthlyPanel])
def get_current_panels(_: dict = Depends(require_user)) -> list[dict]:
    return list_panels(calendar_month_label())


@router.post("/panels", response_model=MonthlyPanel)
def post_panel(panel: MonthlyPanelIn, _: dict = Depends(require_user)) -> dict:
    try:
        return create_panel(panel)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/panels/{panel_id}", response_model=MonthlyPanel)
def patch_panel(panel_id: int, patch: MonthlyPanelPatch, _: dict = Depends(require_user)) -> dict:
    if patch.discount_amount is not None:
        with session() as conn:
            current = conn.execute("SELECT * FROM monthly_panels WHERE id = ?", (panel_id,)).fetchone()
        if current is None:
            raise HTTPException(status_code=404, detail="panel not found")
        if current["panel_type"] != "claim":
            raise HTTPException(status_code=422, detail="청구 항목에만 본인회원 카드 할인을 적용할 수 있습니다.")
        if patch.discount_amount > float(current["amount_value"] or 0):
            raise HTTPException(status_code=422, detail="할인액은 원래 청구금액을 초과할 수 없습니다.")
    panel = update_panel(panel_id, patch)
    if panel is None:
        raise HTTPException(status_code=404, detail="panel not found")
    return panel


@router.patch("/panels/{panel_id}/discount", response_model=MonthlyPanel)
def patch_panel_discount(panel_id: int, patch: PanelDiscountPatch, _: dict = Depends(require_user)) -> dict:
    with session() as conn:
        panel = conn.execute("SELECT * FROM monthly_panels WHERE id = ?", (panel_id,)).fetchone()
    if panel is None:
        raise HTTPException(status_code=404, detail="panel not found")
    if panel["panel_type"] not in {"claim", "family_card"}:
        raise HTTPException(status_code=422, detail="청구 또는 가족카드 항목에만 카드 할인을 적용할 수 있습니다.")
    if patch.discount_amount > float(panel["amount_value"] or 0):
        raise HTTPException(status_code=422, detail="할인액은 원래 청구금액을 초과할 수 없습니다.")
    updated = update_panel(panel_id, MonthlyPanelPatch(discount_amount=patch.discount_amount, discount_override=1))
    if updated is None:
        raise HTTPException(status_code=404, detail="panel not found")
    return updated


@router.delete("/panels/{panel_id}/discount")
def remove_panel_discount(panel_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    updated = update_panel(panel_id, MonthlyPanelPatch(discount_amount=0, discount_override=0))
    if updated is None:
        raise HTTPException(status_code=404, detail="panel not found")
    return {"deleted": True}


@router.delete("/panels/{panel_id}")
def remove_panel(panel_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_panel(panel_id):
        raise HTTPException(status_code=404, detail="panel not found")
    return {"deleted": True}


@router.delete("/panels/type/{panel_type}")
def remove_panels_by_type(panel_type: str, _: dict = Depends(require_user)) -> dict[str, int]:
    if panel_type not in {"fixed", "frozen", "claim", "family_card"}:
        raise HTTPException(status_code=404, detail="unknown panel type")
    return {"deleted": delete_panels_by_type(calendar_month_label(), panel_type)}


@router.post("/panels/type/{panel_type}/complete")
def complete_current_panels_by_type(panel_type: str, _: dict = Depends(require_user)) -> dict[str, int]:
    if panel_type not in {"claim", "family_card"}:
        raise HTTPException(status_code=404, detail="only claim and family_card can be completed in bulk")
    return {"completed": complete_panels_by_type(calendar_month_label(), panel_type)}


@router.get("/summary", response_model=Summary)
def current_summary(_: dict = Depends(require_user)) -> Summary:
    try:
        return Summary(**current_summary_values())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/close")
def close_month(payload: MonthCloseIn, _: dict = Depends(require_user)) -> dict:
    try:
        return close_current_month(allow_early_close=payload.allow_early_close)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/status")
def get_month_close_status(_: dict = Depends(require_user)) -> dict:
    return month_close_status()


@judgment_router.get("/current")
def current_judgment(_: dict = Depends(require_user)) -> dict:
    return app_judgment(
        list_entries("current"),
        list_panels(calendar_month_label()),
        list_cash_flows(),
        current_summary_values(),
        current_payment_status(),
        list_settings(),
        list_recent_closed_month_expense_counts(),
    )

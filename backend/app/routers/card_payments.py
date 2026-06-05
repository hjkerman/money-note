from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_user
from app.schemas import CardDiscountPolicyPatch, CardPaymentEventIn, LateCardEntryIn, PanelDiscountPatch
from app.services.card_payments import (
    acknowledge_liquidity_reset,
    cancel_toll_deferral,
    clear_entry_discount,
    create_card_payment_event,
    create_late_card_entry,
    current_payment_status,
    defer_toll_payment,
    delete_card_payment_event,
    discount_month_status,
    set_discount_month_policy,
    set_entry_discount,
)

payments_router = APIRouter(prefix="/api/card-payments", tags=["card-payments"])
discounts_router = APIRouter(prefix="/api/card-discounts", tags=["card-discounts"])


@payments_router.get("/current")
def get_current_card_payments(_: dict = Depends(require_user)) -> dict:
    return current_payment_status()


@discounts_router.get("/months/{month}")
def get_card_discount_month(month: str, scope: str = "owner", _: dict = Depends(require_user)) -> dict:
    try:
        return discount_month_status(month, scope)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@discounts_router.patch("/months/{month}")
def patch_card_discount_month(
    month: str,
    patch: CardDiscountPolicyPatch,
    scope: str = "owner",
    _: dict = Depends(require_user),
) -> dict:
    try:
        return set_discount_month_policy(month, patch.policy, scope)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@discounts_router.patch("/entries/{entry_payment_key}")
def patch_entry_discount(entry_payment_key: str, patch: PanelDiscountPatch, _: dict = Depends(require_user)) -> dict:
    try:
        return set_entry_discount(entry_payment_key, patch.discount_amount)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@discounts_router.delete("/entries/{entry_payment_key}")
def remove_entry_discount(entry_payment_key: str, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not clear_entry_discount(entry_payment_key):
        raise HTTPException(status_code=404, detail="discount target entry not found")
    return {"deleted": True}


@payments_router.post("/events")
def post_card_payment_event(payload: CardPaymentEventIn, _: dict = Depends(require_user)) -> dict:
    try:
        return create_card_payment_event(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@payments_router.delete("/events/{event_id}")
def remove_card_payment_event(event_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_card_payment_event(event_id):
        raise HTTPException(status_code=404, detail="card payment event not found")
    return {"deleted": True}


@payments_router.post("/acknowledge-liquidity-reset")
def post_acknowledge_liquidity_reset(_: dict = Depends(require_user)) -> dict[str, str]:
    return acknowledge_liquidity_reset()


@payments_router.post("/late-entries")
def post_late_card_entry(payload: LateCardEntryIn, _: dict = Depends(require_user)) -> dict:
    try:
        return create_late_card_entry(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@payments_router.post("/deferrals/{entry_payment_key}")
def post_card_payment_deferral(entry_payment_key: str, _: dict = Depends(require_user)) -> dict[str, str]:
    try:
        return defer_toll_payment(entry_payment_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@payments_router.delete("/deferrals/{entry_payment_key}")
def remove_card_payment_deferral(entry_payment_key: str, _: dict = Depends(require_user)) -> dict[str, bool]:
    try:
        deleted = cancel_toll_deferral(entry_payment_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="current payment deferral not found")
    return {"deleted": True}

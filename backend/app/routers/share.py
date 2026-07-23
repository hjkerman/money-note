from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from app.auth import require_user
from app.config import get_settings
from app.schemas import SharePinIn
from app.security import AttemptLimit, FailedAttemptLimiter, request_client_key
from app.share_auth import (
    set_share_pin,
    share_access_allowed,
    share_pin_needs_change,
    share_unlock_html,
    unlock_share,
)
from app.services.share import shared_panel, shared_panel_html

api_router = APIRouter(prefix="/api/share", tags=["share"])
page_router = APIRouter(prefix="/share", tags=["share-pages"])
settings = get_settings()
share_pin_limiter = FailedAttemptLimiter(
    AttemptLimit(settings.share_pin_max_failures, settings.share_pin_window_seconds)
)
SHARED_PANEL_TYPES = frozenset({"claim", "family_card"})


@api_router.post("/pin")
def post_share_pin(payload: SharePinIn, _: dict = Depends(require_user)) -> dict[str, bool]:
    set_share_pin(payload.pin)
    return {"configured": True, "needs_change": share_pin_needs_change()}


@api_router.post("/unlock")
def post_share_unlock(payload: SharePinIn, request: Request, response: Response) -> dict[str, bool]:
    attempt_key = request_client_key(request)
    share_pin_limiter.check(attempt_key)
    if not unlock_share(payload.pin, response):
        share_pin_limiter.register_failure(attempt_key)
        raise HTTPException(status_code=401, detail="invalid share pin")
    share_pin_limiter.clear(attempt_key)
    return {"unlocked": True}


@api_router.get("/{panel_type}")
def get_shared_panel(panel_type: str, request: Request) -> dict:
    if not share_access_allowed(request):
        raise HTTPException(status_code=401, detail="share pin required")
    try:
        return shared_panel(panel_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="unknown shared panel") from exc


@page_router.get("/{panel_type}", response_class=HTMLResponse)
def read_shared_panel(panel_type: str, request: Request) -> HTMLResponse:
    if panel_type not in SHARED_PANEL_TYPES:
        raise HTTPException(status_code=404, detail="unknown shared panel")
    if not share_access_allowed(request):
        return HTMLResponse(share_unlock_html(f"/share/{panel_type}"))
    try:
        return HTMLResponse(shared_panel_html(panel_type))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="unknown shared panel") from exc

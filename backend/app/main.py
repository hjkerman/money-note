from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from app.auth import (
    authenticate_user,
    clear_session_cookie,
    create_session_cookie,
    current_user_from_request,
    require_user,
)
from app.config import get_settings
from app.db import init_db, session
from app.repository import (
    append_planned_entry,
    confirm_planned_entry,
    create_cash_flow,
    create_installment,
    create_panel,
    complete_panels_by_type,
    create_entry,
    delete_cash_flow,
    delete_installment,
    delete_planned_entry,
    delete_panel,
    delete_panels_by_type,
    delete_entry,
    list_cash_flows,
    list_installments,
    list_archive_rows,
    list_entries,
    list_labels,
    list_panels,
    list_settings,
    reorder_current_entries,
    update_panel,
    update_entry,
    upsert_label,
)
from app.schemas import (
    AuthUser,
    CardPaymentEventIn,
    CardDiscountPolicyPatch,
    CashFlow,
    CashFlowIn,
    Installment,
    InstallmentIn,
    LedgerEntry,
    LedgerEntryIn,
    LedgerEntryPatch,
    MonthCloseIn,
    LateCardEntryIn,
    EntryReorder,
    LoginIn,
    MonthlyPanel,
    MonthlyPanelIn,
    MonthlyPanelPatch,
    PanelDiscountPatch,
    PlannedEntryIn,
    SettingPatch,
    SharePinIn,
    Summary,
)
from app.share_auth import (
    ensure_default_share_pin,
    set_share_pin,
    share_access_allowed,
    share_pin_needs_change,
    share_unlock_html,
    unlock_share,
)
from app.services.card_payments import (
    acknowledge_liquidity_reset,
    cancel_toll_deferral,
    create_late_card_entry,
    create_card_payment_event,
    current_payment_status,
    discount_month_status,
    defer_toll_payment,
    delete_card_payment_event,
    set_discount_month_policy,
)
from app.services.audit import clear_audit_logs, list_audit_logs, record_audit_log
from app.services.month import calendar_month_label, close_current_month, month_close_status
from app.services.share import shared_panel, shared_panel_html
from app.services.summary import current_summary_values
from app.services.workbook import export_workbook

app = FastAPI(title="money-note")
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIT_METHODS = {"POST", "PATCH", "DELETE"}
AUDIT_CLEAR_PATH = "/api/audit-logs"


@app.middleware("http")
async def audit_mutating_api_requests(request: Request, call_next):
    """변경 API의 경로와 결과만 기록하고 민감한 요청 본문은 남기지 않는다."""
    user = current_user_from_request(request)
    response = await call_next(request)
    if (
        request.method in AUDIT_METHODS
        and request.url.path.startswith("/api/")
        and not (request.method == "DELETE" and request.url.path == AUDIT_CLEAR_PATH)
    ):
        try:
            record_audit_log(
                str(user["username"]) if user else "anonymous",
                request.method,
                request.url.path,
                response.status_code,
            )
        except Exception:
            # 감사 로그 장애가 실제 가계부 조작을 실패시키지는 않는다.
            pass
    return response


@app.on_event("startup")
def startup() -> None:
    init_db()
    ensure_default_share_pin()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/audit-logs")
def get_audit_logs(_: dict = Depends(require_user)) -> list[dict]:
    return list_audit_logs()


@app.delete("/api/audit-logs")
def delete_audit_logs(_: dict = Depends(require_user)) -> dict[str, int]:
    return {"deleted": clear_audit_logs()}


@app.post("/api/auth/login", response_model=AuthUser)
def login(payload: LoginIn, response: Response) -> dict:
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid username or password")
    session_token = create_session_cookie(response, user["id"])
    return {**user, "session_token": session_token, "share_pin_needs_change": share_pin_needs_change()}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    clear_session_cookie(request, response)
    return {"ok": True}


@app.get("/api/auth/me", response_model=AuthUser)
def me(request: Request) -> dict:
    user = current_user_from_request(request)
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return {**user, "share_pin_needs_change": share_pin_needs_change()}


@app.get("/api/entries/{section}", response_model=list[LedgerEntry])
def get_entries(section: str, _: dict = Depends(require_user)) -> list[dict]:
    if section not in {"current", "archive"}:
        raise HTTPException(status_code=404, detail="unknown section")
    return list_entries(section)


@app.post("/api/entries", response_model=LedgerEntry)
def post_entry(entry: LedgerEntryIn, _: dict = Depends(require_user)) -> dict:
    try:
        return create_entry(entry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.patch("/api/entries/{entry_id}", response_model=LedgerEntry)
def patch_entry(entry_id: int, patch: LedgerEntryPatch, _: dict = Depends(require_user)) -> dict:
    try:
        entry = update_entry(entry_id, patch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if entry is None:
        raise HTTPException(status_code=404, detail="entry not found")
    return entry


@app.delete("/api/entries/{entry_id}")
def remove_entry(entry_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="entry not found")
    return {"deleted": True}


@app.post("/api/month/current/planned", response_model=LedgerEntry)
def post_planned_entry(entry: PlannedEntryIn, _: dict = Depends(require_user)) -> dict:
    return append_planned_entry(entry)


@app.post("/api/month/current/planned/{entry_id}/confirm")
def post_confirm_planned_entry(entry_id: int, _: dict = Depends(require_user)) -> dict:
    try:
        result = confirm_planned_entry(entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="planned entry not found")
    return result


@app.delete("/api/month/current/planned/{entry_id}")
def remove_planned_entry(entry_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_planned_entry(entry_id):
        raise HTTPException(status_code=404, detail="planned entry not found")
    return {"deleted": True}


@app.post("/api/month/current/reorder", response_model=list[LedgerEntry])
def reorder_entries(payload: EntryReorder, _: dict = Depends(require_user)) -> list[dict]:
    return reorder_current_entries(payload.ordered_ids)


@app.post("/api/month/current/planned/reorder", response_model=list[LedgerEntry])
def reorder_planned_entries(payload: EntryReorder, _: dict = Depends(require_user)) -> list[dict]:
    return reorder_current_entries(payload.ordered_ids, entry_kind="planned")


@app.get("/api/month/current/panels", response_model=list[MonthlyPanel])
def get_current_panels(_: dict = Depends(require_user)) -> list[dict]:
    return list_panels(calendar_month_label())


@app.post("/api/month/current/panels", response_model=MonthlyPanel)
def post_panel(panel: MonthlyPanelIn, _: dict = Depends(require_user)) -> dict:
    return create_panel(panel)


@app.patch("/api/month/current/panels/{panel_id}", response_model=MonthlyPanel)
def patch_panel(panel_id: int, patch: MonthlyPanelPatch, _: dict = Depends(require_user)) -> dict:
    if patch.discount_amount is not None:
        with session() as conn:
            current = conn.execute("SELECT * FROM monthly_panels WHERE id = ?", (panel_id,)).fetchone()
        if current is None:
            raise HTTPException(status_code=404, detail="panel not found")
        if current["panel_type"] != "claim":
            raise HTTPException(status_code=422, detail="청구 항목에만 본인회원 카드 할인을 적용할 수 있습니다.")
        if discount_month_status(current["month"], "owner")["policy"] == "disabled":
            raise HTTPException(status_code=422, detail=f"{current['month']}은 본인회원 카드 할인 혜택이 없는 달입니다.")
        if patch.discount_amount > float(current["amount_value"] or 0):
            raise HTTPException(status_code=422, detail="할인액은 원래 청구금액을 초과할 수 없습니다.")
    panel = update_panel(panel_id, patch)
    if panel is None:
        raise HTTPException(status_code=404, detail="panel not found")
    return panel


@app.patch("/api/month/current/panels/{panel_id}/discount", response_model=MonthlyPanel)
def patch_panel_discount(panel_id: int, patch: PanelDiscountPatch, _: dict = Depends(require_user)) -> dict:
    with session() as conn:
        panel = conn.execute("SELECT * FROM monthly_panels WHERE id = ?", (panel_id,)).fetchone()
    if panel is None:
        raise HTTPException(status_code=404, detail="panel not found")
    if panel["panel_type"] != "claim":
        raise HTTPException(status_code=422, detail="청구 항목에만 본인회원 카드 할인을 적용할 수 있습니다.")
    if discount_month_status(panel["month"], "owner")["policy"] == "disabled":
        raise HTTPException(status_code=422, detail=f"{panel['month']}은 본인회원 카드 할인 혜택이 없는 달입니다.")
    if patch.discount_amount > float(panel["amount_value"] or 0):
        raise HTTPException(status_code=422, detail="할인액은 원래 청구금액을 초과할 수 없습니다.")
    updated = update_panel(panel_id, MonthlyPanelPatch(discount_amount=patch.discount_amount))
    if updated is None:
        raise HTTPException(status_code=404, detail="panel not found")
    return updated


@app.delete("/api/month/current/panels/{panel_id}")
def remove_panel(panel_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_panel(panel_id):
        raise HTTPException(status_code=404, detail="panel not found")
    return {"deleted": True}


@app.delete("/api/month/current/panels/type/{panel_type}")
def remove_panels_by_type(panel_type: str, _: dict = Depends(require_user)) -> dict[str, int]:
    if panel_type not in {"fixed", "frozen", "claim", "settlement"}:
        raise HTTPException(status_code=404, detail="unknown panel type")
    return {"deleted": delete_panels_by_type(calendar_month_label(), panel_type)}


@app.post("/api/month/current/panels/type/{panel_type}/complete")
def complete_current_panels_by_type(panel_type: str, _: dict = Depends(require_user)) -> dict[str, int]:
    if panel_type not in {"claim", "settlement"}:
        raise HTTPException(status_code=404, detail="only claim and settlement can be completed in bulk")
    return {"completed": complete_panels_by_type(calendar_month_label(), panel_type)}


@app.get("/api/month/current/summary", response_model=Summary)
def current_summary(_: dict = Depends(require_user)) -> Summary:
    try:
        return Summary(**current_summary_values())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/card-payments/current")
def get_current_card_payments(_: dict = Depends(require_user)) -> dict:
    return current_payment_status()


@app.get("/api/card-discounts/months/{month}")
def get_card_discount_month(month: str, scope: str = "owner", _: dict = Depends(require_user)) -> dict:
    try:
        return discount_month_status(month, scope)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.patch("/api/card-discounts/months/{month}")
def patch_card_discount_month(
    month: str,
    patch: CardDiscountPolicyPatch,
    scope: str = "owner",
    _: dict = Depends(require_user),
) -> dict:
    try:
        return set_discount_month_policy(month, patch.policy, scope)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/card-payments/events")
def post_card_payment_event(payload: CardPaymentEventIn, _: dict = Depends(require_user)) -> dict:
    try:
        return create_card_payment_event(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.delete("/api/card-payments/events/{event_id}")
def remove_card_payment_event(event_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_card_payment_event(event_id):
        raise HTTPException(status_code=404, detail="card payment event not found")
    return {"deleted": True}


@app.post("/api/card-payments/acknowledge-liquidity-reset")
def post_acknowledge_liquidity_reset(_: dict = Depends(require_user)) -> dict[str, str]:
    return acknowledge_liquidity_reset()


@app.post("/api/card-payments/late-entries")
def post_late_card_entry(payload: LateCardEntryIn, _: dict = Depends(require_user)) -> dict:
    try:
        return create_late_card_entry(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/card-payments/deferrals/{entry_payment_key}")
def post_card_payment_deferral(entry_payment_key: str, _: dict = Depends(require_user)) -> dict[str, str]:
    try:
        return defer_toll_payment(entry_payment_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.delete("/api/card-payments/deferrals/{entry_payment_key}")
def remove_card_payment_deferral(entry_payment_key: str, _: dict = Depends(require_user)) -> dict[str, bool]:
    try:
        deleted = cancel_toll_deferral(entry_payment_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail="current payment deferral not found")
    return {"deleted": True}


@app.post("/api/month/current/close")
def close_month(payload: MonthCloseIn, _: dict = Depends(require_user)) -> dict:
    try:
        return close_current_month(allow_early_close=payload.allow_early_close)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/month/current/status")
def get_month_close_status(_: dict = Depends(require_user)) -> dict:
    return month_close_status()


@app.post("/api/share/pin")
def post_share_pin(payload: SharePinIn, _: dict = Depends(require_user)) -> dict[str, bool]:
    set_share_pin(payload.pin)
    return {"configured": True, "needs_change": share_pin_needs_change()}


@app.post("/api/share/unlock")
def post_share_unlock(payload: SharePinIn, request: Request, response: Response) -> dict[str, bool]:
    if not unlock_share(payload.pin, response):
        raise HTTPException(status_code=401, detail="invalid share pin")
    return {"unlocked": True}


@app.get("/api/share/{panel_type}")
def get_shared_panel(panel_type: str, request: Request) -> dict:
    if not share_access_allowed(request):
        raise HTTPException(status_code=401, detail="share pin required")
    try:
        return shared_panel(panel_type)
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown shared panel")


@app.get("/share/{panel_type}", response_class=HTMLResponse)
def read_shared_panel(panel_type: str, request: Request) -> HTMLResponse:
    if not share_access_allowed(request):
        return HTMLResponse(share_unlock_html(f"/share/{panel_type}"))
    try:
        return HTMLResponse(shared_panel_html(panel_type))
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown shared panel")


@app.get("/api/settings")
def get_settings_values(_: dict = Depends(require_user)) -> dict[str, str]:
    with session() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


@app.patch("/api/settings/{key}")
def patch_setting(key: str, patch: SettingPatch, _: dict = Depends(require_user)) -> dict[str, str]:
    allowed = {"base_next_month_liquidity", "interest_expense", "liquidity_status", "settlement_card_limit"}
    if key not in allowed:
        raise HTTPException(status_code=404, detail="unknown setting")
    with session() as conn:
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, patch.value),
        )
    return {key: patch.value}


@app.get("/api/cash-flows", response_model=list[CashFlow])
def get_cash_flows(_: dict = Depends(require_user)) -> list[dict]:
    return list_cash_flows()


@app.get("/api/installments", response_model=list[Installment])
def get_installments(_: dict = Depends(require_user)) -> list[dict]:
    return list_installments()


@app.post("/api/installments", response_model=Installment)
def post_installment(installment: InstallmentIn, _: dict = Depends(require_user)) -> dict:
    if installment.months < 1:
        raise HTTPException(status_code=422, detail="months must be greater than zero")
    if installment.remaining_months is not None and installment.remaining_months < 1:
        raise HTTPException(status_code=422, detail="remaining_months must be greater than zero")
    return create_installment(installment)


@app.delete("/api/installments/{installment_id}")
def remove_installment(installment_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_installment(installment_id):
        raise HTTPException(status_code=404, detail="installment not found")
    return {"deleted": True}


@app.post("/api/cash-flows", response_model=CashFlow)
def post_cash_flow(flow: CashFlowIn, _: dict = Depends(require_user)) -> dict:
    return create_cash_flow(flow)


@app.delete("/api/cash-flows/{flow_id}")
def remove_cash_flow(flow_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_cash_flow(flow_id):
        raise HTTPException(status_code=404, detail="cash flow not found")
    return {"deleted": True}


@app.get("/api/labels")
def get_labels(_: dict = Depends(require_user)) -> dict[str, str]:
    return list_labels()


@app.patch("/api/labels/{key}")
def patch_label(key: str, patch: SettingPatch, _: dict = Depends(require_user)) -> dict[str, str]:
    allowed = set(list_labels().keys())
    if key not in allowed:
        raise HTTPException(status_code=404, detail="unknown label")
    return upsert_label(key, patch.value)


@app.post("/api/export")
def create_export(_: dict = Depends(require_user)) -> dict[str, str]:
    settings = get_settings()
    hard_archive_rows = list_archive_rows()
    archive_entries = list_entries("archive")
    current_entries = list_entries("current")
    panels = list_panels()
    labels = list_labels()
    export_settings = list_settings()

    filename = f"money-note-{datetime.now().strftime('%Y%m%d-%H%M%S')}.xlsx"
    output_path = settings.export_dir / filename
    export_workbook(
        hard_archive_rows,
        archive_entries,
        current_entries,
        panels,
        labels,
        export_settings,
        output_path,
        template_path=settings.template_path,
    )
    latest_path = settings.export_dir / "latest.xlsx"
    export_workbook(
        hard_archive_rows,
        archive_entries,
        current_entries,
        panels,
        labels,
        export_settings,
        latest_path,
        template_path=settings.template_path,
    )
    return {"filename": filename, "latest": "latest.xlsx"}


@app.get("/api/export/latest.xlsx")
def latest_export(_: dict = Depends(require_user)) -> FileResponse:
    path = get_settings().export_dir / "latest.xlsx"
    if not path.exists():
        raise HTTPException(status_code=404, detail="no export has been created")
    return FileResponse(path, filename="money-note-latest.xlsx")

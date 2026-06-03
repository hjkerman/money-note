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
    confirm_frozen_panel,
    confirm_planned_entry,
    create_cash_flow,
    create_panel,
    create_entry,
    delete_cash_flow,
    delete_planned_entry,
    delete_panel,
    delete_entry,
    list_cash_flows,
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
    CashFlow,
    CashFlowIn,
    LedgerEntry,
    LedgerEntryIn,
    LedgerEntryPatch,
    EntryReorder,
    LoginIn,
    MonthlyPanel,
    MonthlyPanelIn,
    MonthlyPanelPatch,
    PlannedEntryIn,
    SettingPatch,
    Summary,
)
from app.services.month import close_current_month, current_month_label
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


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=AuthUser)
def login(payload: LoginIn, response: Response) -> dict:
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid username or password")
    create_session_cookie(response, user["id"])
    return user


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    clear_session_cookie(request, response)
    return {"ok": True}


@app.get("/api/auth/me", response_model=AuthUser)
def me(request: Request) -> dict:
    user = current_user_from_request(request)
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return user


@app.get("/api/entries/{section}", response_model=list[LedgerEntry])
def get_entries(section: str, _: dict = Depends(require_user)) -> list[dict]:
    if section not in {"current", "archive"}:
        raise HTTPException(status_code=404, detail="unknown section")
    return list_entries(section)


@app.post("/api/entries", response_model=LedgerEntry)
def post_entry(entry: LedgerEntryIn, _: dict = Depends(require_user)) -> dict:
    return create_entry(entry)


@app.patch("/api/entries/{entry_id}", response_model=LedgerEntry)
def patch_entry(entry_id: int, patch: LedgerEntryPatch, _: dict = Depends(require_user)) -> dict:
    entry = update_entry(entry_id, patch)
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
    return list_panels(current_month_label())


@app.post("/api/month/current/panels", response_model=MonthlyPanel)
def post_panel(panel: MonthlyPanelIn, _: dict = Depends(require_user)) -> dict:
    return create_panel(panel)


@app.patch("/api/month/current/panels/{panel_id}", response_model=MonthlyPanel)
def patch_panel(panel_id: int, patch: MonthlyPanelPatch, _: dict = Depends(require_user)) -> dict:
    panel = update_panel(panel_id, patch)
    if panel is None:
        raise HTTPException(status_code=404, detail="panel not found")
    return panel


@app.post("/api/month/current/panels/{panel_id}/confirm-frozen")
def post_confirm_frozen_panel(panel_id: int, _: dict = Depends(require_user)) -> dict:
    try:
        result = confirm_frozen_panel(panel_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="panel not found")
    return result


@app.delete("/api/month/current/panels/{panel_id}")
def remove_panel(panel_id: int, _: dict = Depends(require_user)) -> dict[str, bool]:
    if not delete_panel(panel_id):
        raise HTTPException(status_code=404, detail="panel not found")
    return {"deleted": True}


@app.get("/api/month/current/summary", response_model=Summary)
def current_summary(_: dict = Depends(require_user)) -> Summary:
    try:
        return Summary(**current_summary_values())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/month/current/close")
def close_month(_: dict = Depends(require_user)) -> dict[str, int]:
    return close_current_month()


@app.get("/api/share/{panel_type}")
def get_shared_panel(panel_type: str) -> dict:
    try:
        return shared_panel(panel_type)
    except ValueError:
        raise HTTPException(status_code=404, detail="unknown shared panel")


@app.get("/share/{panel_type}", response_class=HTMLResponse)
def read_shared_panel(panel_type: str) -> HTMLResponse:
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
    allowed = {"base_next_month_liquidity", "interest_expense", "liquidity_status"}
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

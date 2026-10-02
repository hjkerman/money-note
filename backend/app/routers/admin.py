import json

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from app.auth import require_user, verify_user_password
from app.config import get_settings
from app.db import session
from app.routers.responses import financial_response
from app.routers.money_input import read_request_body
from app.schemas import PasswordConfirmIn, PreRestoreRestoreIn, SnapshotRestoreIn
from app.services.operation_stats import operation_data_stats
from app.services.reset import reset_ledger_data
from app.services.snapshot import (
    delete_all_pre_restore_backups,
    delete_pre_restore_backup,
    export_snapshot,
    list_pre_restore_backups,
    restore_pre_restore_backup,
    restore_snapshot,
    parse_snapshot_json,
    validate_snapshot_json_money,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset-ledger-data")
def post_reset_ledger_data(payload: PasswordConfirmIn, user: dict = Depends(require_user)) -> dict[str, dict[str, int]]:
    if not verify_user_password(int(user["id"]), payload.password):
        raise HTTPException(status_code=422, detail="현재 비밀번호가 맞지 않습니다.")
    with session(transaction_mode="IMMEDIATE") as conn:
        return financial_response({"deleted": reset_ledger_data(conn=conn)})


@router.get("/snapshot")
def get_snapshot(_: dict = Depends(require_user)) -> Response:
    filename, snapshot = export_snapshot()
    return Response(
        content=json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/apk")
def get_apk(_: dict = Depends(require_user)) -> FileResponse:
    settings = get_settings()
    apk_path = settings.apk_path
    if apk_path is None or not apk_path.is_file():
        raise HTTPException(status_code=404, detail="apk file not found")
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename=settings.apk_filename,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/operation-stats")
def get_operation_stats(_: dict = Depends(require_user)) -> dict:
    return operation_data_stats()


@router.post("/snapshot/restore")
def post_snapshot_restore(
    payload: SnapshotRestoreIn, user: dict = Depends(require_user),
    request_body: bytes = Depends(read_request_body),
) -> dict[str, dict[str, int]]:
    if not verify_user_password(int(user["id"]), payload.password):
        raise HTTPException(status_code=422, detail="현재 비밀번호가 맞지 않습니다.")
    try:
        if payload.snapshot_text is not None:
            snapshot = parse_snapshot_json(payload.snapshot_text)
        elif payload.snapshot is not None:
            if isinstance(request_body, bytes):
                validate_snapshot_json_money(request_body, document_path=("snapshot",))
            snapshot = payload.snapshot
        else:
            raise ValueError("snapshot is missing")
        with session(transaction_mode="IMMEDIATE") as conn:
            return financial_response({"restored": restore_snapshot(snapshot, conn=conn)})
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="snapshot file is not valid JSON") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/snapshot/pre-restore")
def get_pre_restore_backups(_: dict = Depends(require_user)) -> dict[str, list[dict]]:
    try:
        backups = list_pre_restore_backups()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"backups": backups}


@router.delete("/snapshot/pre-restore")
def delete_all_pre_restore(_: dict = Depends(require_user)) -> dict[str, int]:
    try:
        deleted = delete_all_pre_restore_backups()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": deleted}


@router.delete("/snapshot/pre-restore/{filename}")
def delete_pre_restore(filename: str, _: dict = Depends(require_user)) -> dict[str, bool]:
    try:
        deleted = delete_pre_restore_backup(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="pre_restore backup not found")
    return {"deleted": True}


@router.post("/snapshot/pre-restore/{filename}/restore")
def post_pre_restore_backup_restore(
    filename: str,
    payload: PreRestoreRestoreIn,
    user: dict = Depends(require_user),
) -> dict[str, dict[str, int]]:
    if not verify_user_password(int(user["id"]), payload.password):
        raise HTTPException(status_code=422, detail="현재 비밀번호가 맞지 않습니다.")
    try:
        with session(transaction_mode="IMMEDIATE") as conn:
            return financial_response({"restored": restore_pre_restore_backup(filename, conn=conn)})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

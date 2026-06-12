import json

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import require_user, verify_user_password
from app.schemas import PasswordConfirmIn, PreRestoreRestoreIn, SnapshotRestoreIn
from app.services.reset import reset_ledger_data
from app.services.snapshot import (
    export_snapshot,
    list_pre_restore_backups,
    read_pre_restore_backup,
    restore_pre_restore_backup,
    restore_snapshot,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset-ledger-data")
def post_reset_ledger_data(payload: PasswordConfirmIn, user: dict = Depends(require_user)) -> dict[str, dict[str, int]]:
    if not verify_user_password(int(user["id"]), payload.password):
        raise HTTPException(status_code=422, detail="현재 비밀번호가 맞지 않습니다.")
    return {"deleted": reset_ledger_data()}


@router.get("/snapshot")
def get_snapshot(_: dict = Depends(require_user)) -> Response:
    filename, snapshot = export_snapshot()
    return Response(
        content=json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/snapshot/restore")
def post_snapshot_restore(payload: SnapshotRestoreIn, user: dict = Depends(require_user)) -> dict[str, dict[str, int]]:
    if not verify_user_password(int(user["id"]), payload.password):
        raise HTTPException(status_code=422, detail="현재 비밀번호가 맞지 않습니다.")
    try:
        restored = restore_snapshot(payload.snapshot)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"restored": restored}


@router.get("/snapshot/pre-restore")
def get_pre_restore_backups(_: dict = Depends(require_user)) -> dict[str, list[dict]]:
    try:
        backups = list_pre_restore_backups()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"backups": backups}


@router.get("/snapshot/pre-restore/{filename}")
def get_pre_restore_backup(filename: str, _: dict = Depends(require_user)) -> Response:
    try:
        safe_filename, snapshot = read_pre_restore_backup(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.post("/snapshot/pre-restore/{filename}/restore")
def post_pre_restore_backup_restore(
    filename: str,
    payload: PreRestoreRestoreIn,
    user: dict = Depends(require_user),
) -> dict[str, dict[str, int]]:
    if not verify_user_password(int(user["id"]), payload.password):
        raise HTTPException(status_code=422, detail="현재 비밀번호가 맞지 않습니다.")
    try:
        restored = restore_pre_restore_backup(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"restored": restored}

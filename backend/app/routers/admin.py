import json

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import require_user, verify_user_password
from app.schemas import PasswordConfirmIn, SnapshotRestoreIn
from app.services.reset import reset_ledger_data
from app.services.snapshot import export_snapshot, restore_snapshot

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

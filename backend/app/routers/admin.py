from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_user, verify_user_password
from app.schemas import PasswordConfirmIn
from app.services.reset import reset_ledger_data

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reset-ledger-data")
def post_reset_ledger_data(payload: PasswordConfirmIn, user: dict = Depends(require_user)) -> dict[str, dict[str, int]]:
    if not verify_user_password(int(user["id"]), payload.password):
        raise HTTPException(status_code=422, detail="현재 비밀번호가 맞지 않습니다.")
    return {"deleted": reset_ledger_data()}

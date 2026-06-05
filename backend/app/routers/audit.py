from fastapi import APIRouter, Depends

from app.auth import require_user
from app.services.audit import clear_audit_logs, list_audit_logs

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("")
def get_audit_logs(_: dict = Depends(require_user)) -> list[dict]:
    return list_audit_logs()


@router.delete("")
def delete_audit_logs(_: dict = Depends(require_user)) -> dict[str, int]:
    return {"deleted": clear_audit_logs()}

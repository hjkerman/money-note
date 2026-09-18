from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_user, verify_user_password
from app.schemas import OfflineMobileWinsIn, OfflineRecoveryPointIn
from app.services.offline_reconciliation import (
    ReconciliationConflictError,
    ReconciliationDigestMismatchError,
    apply_mobile_wins,
    create_server_recovery_point,
    export_offline_baseline,
    inspect_reconciliation,
    reconciliation_result,
)


router = APIRouter(
    prefix="/api/offline-reconciliation",
    tags=["offline-reconciliation"],
)


@router.get("/baseline")
def get_offline_baseline(_: dict = Depends(require_user)) -> dict:
    return export_offline_baseline()


@router.get("/status")
def get_offline_reconciliation_status(
    baseline_fingerprint: str = Query(pattern=r"^[0-9a-f]{64}$"),
    reconciliation_id: str | None = Query(
        default=None,
        min_length=16,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$",
    ),
    _: dict = Depends(require_user),
) -> dict:
    return inspect_reconciliation(baseline_fingerprint, reconciliation_id)


@router.get("/result/{reconciliation_id}")
def get_offline_reconciliation_result(
    reconciliation_id: str,
    _: dict = Depends(require_user),
) -> dict:
    result = reconciliation_result(reconciliation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="reconciliation not found")
    return result


@router.post("/server-recovery")
def post_offline_server_recovery(
    payload: OfflineRecoveryPointIn,
    _: dict = Depends(require_user),
) -> dict:
    try:
        return create_server_recovery_point(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/mobile-wins")
def post_offline_mobile_wins(
    payload: OfflineMobileWinsIn,
    user: dict = Depends(require_user),
) -> dict:
    if not verify_user_password(int(user["id"]), payload.password):
        raise HTTPException(status_code=422, detail="현재 비밀번호가 맞지 않습니다.")
    try:
        return apply_mobile_wins(payload)
    except ReconciliationConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "server_state_changed",
                "message": "오프라인 모드 시작 이후 서버 데이터도 변경되었습니다.",
                "current_server_fingerprint": exc.current_fingerprint,
                "server_changed": exc.server_changed,
            },
        ) from exc
    except ReconciliationDigestMismatchError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "reconciliation_digest_mismatch",
                "message": str(exc),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

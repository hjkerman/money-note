from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.authoritative_schemas import AuthoritativeState
from app.services.authoritative_state import (
    BundleCredential, authoritative_state_response, require_bundle_credential,
)


router = APIRouter(tags=["authoritative-state"])


@router.get("/api/authoritative-state", response_model=AuthoritativeState)
def get_authoritative_state(credential: BundleCredential = Depends(require_bundle_credential)) -> JSONResponse:
    try:
        return authoritative_state_response(credential)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, detail=str(exc)) from exc

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.routers.response_coding import code_json_response

from app.authoritative_schemas import AuthoritativeState
from app.services.authoritative_state import (
    BundleCredential, authoritative_state_response, require_bundle_credential,
)


router = APIRouter(tags=["authoritative-state"])


@router.get("/api/authoritative-state", response_model=AuthoritativeState)
def get_authoritative_state(request: Request, credential: BundleCredential = Depends(require_bundle_credential)) -> Response:
    try:
        return code_json_response(request, authoritative_state_response(credential))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, detail=str(exc)) from exc

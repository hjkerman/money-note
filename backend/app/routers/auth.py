from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth import (
    authenticate_user,
    change_password,
    clear_session_cookie,
    create_mobile_session_token,
    create_session_cookie,
    current_user_from_request,
    require_user,
)
from app.schemas import AuthUser, LoginIn, PasswordChangeIn
from app.share_auth import share_pin_needs_change

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthUser)
def login(payload: LoginIn, response: Response) -> dict:
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid username or password")
    session_token = create_session_cookie(response, user["id"])
    return {**user, "session_token": session_token, "share_pin_needs_change": share_pin_needs_change()}


@router.post("/mobile-login", response_model=AuthUser)
def mobile_login(payload: LoginIn) -> dict:
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid username or password")
    session_token = create_mobile_session_token(user["id"])
    return {**user, "session_token": session_token, "share_pin_needs_change": share_pin_needs_change()}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    clear_session_cookie(request, response)
    return {"ok": True}


@router.get("/me", response_model=AuthUser)
def me(request: Request) -> dict:
    user = current_user_from_request(request)
    if user is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return {**user, "share_pin_needs_change": share_pin_needs_change()}


@router.patch("/password")
def patch_password(payload: PasswordChangeIn, user: dict = Depends(require_user)) -> dict[str, bool]:
    if not change_password(int(user["id"]), payload.current_password, payload.new_password):
        raise HTTPException(status_code=422, detail="현재 비밀번호가 맞지 않습니다.")
    return {"changed": True}

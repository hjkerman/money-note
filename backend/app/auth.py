from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import secrets
from typing import Any

from fastapi import HTTPException, Request, Response, status

from app.config import get_settings
from app.db import session


PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 390000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return "$".join(
        [
            PASSWORD_HASH_PREFIX,
            str(PASSWORD_HASH_ITERATIONS),
            _b64encode(salt),
            _b64encode(digest),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        prefix, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if prefix != PASSWORD_HASH_PREFIX:
            return False
        iterations = int(iterations_text)
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    with session() as conn:
        row = conn.execute(
            """
            SELECT id, username, password_hash, display_name, is_active
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
    if row is None or not row["is_active"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return _public_user(row)


def create_user(username: str, password: str, display_name: str = "") -> dict[str, Any]:
    password_hash = hash_password(password)
    with session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users(username, password_hash, display_name)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, display_name or username),
        )
        row = conn.execute(
            "SELECT id, username, display_name FROM users WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return _public_user(row)


def create_session_cookie(response: Response, user_id: int) -> str:
    settings = get_settings()
    token = secrets.token_urlsafe(48)
    token_hash = _hash_session_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    with session() as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions(user_id, session_token_hash, expires_at)
            VALUES (?, ?, ?)
            """,
            (user_id, token_hash, _datetime_to_db(expires_at)),
        )
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_days * 24 * 60 * 60,
        expires=settings.session_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return token


def clear_session_cookie(request: Request, response: Response) -> None:
    settings = get_settings()
    token = _session_token_from_request(request)
    if token:
        with session() as conn:
            conn.execute(
                "DELETE FROM auth_sessions WHERE session_token_hash = ?",
                (_hash_session_token(token),),
            )
    response.delete_cookie(settings.session_cookie_name, path="/")


def require_user(request: Request) -> dict[str, Any]:
    user = current_user_from_request(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )
    return user


def current_user_from_request(request: Request) -> dict[str, Any] | None:
    token = _session_token_from_request(request)
    if not token:
        return None

    token_hash = _hash_session_token(token)
    now = _datetime_to_db(datetime.now(timezone.utc))
    with session() as conn:
        row = conn.execute(
            """
            SELECT users.id, users.username, users.display_name, users.is_active,
                   auth_sessions.id AS session_id, auth_sessions.expires_at
            FROM auth_sessions
            JOIN users ON users.id = auth_sessions.user_id
            WHERE auth_sessions.session_token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] <= now or not row["is_active"]:
            conn.execute("DELETE FROM auth_sessions WHERE id = ?", (row["session_id"],))
            return None
        conn.execute(
            "UPDATE auth_sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["session_id"],),
        )
    return _public_user(row)


def _session_token_from_request(request: Request) -> str | None:
    settings = get_settings()
    cookie_token = request.cookies.get(settings.session_cookie_name)
    if cookie_token:
        return cookie_token

    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _datetime_to_db(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _public_user(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "username": str(row["username"]),
        "display_name": str(row["display_name"] or row["username"]),
    }


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)

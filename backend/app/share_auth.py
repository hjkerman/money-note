from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import Request, Response

from app.auth import hash_password, verify_password
from app.config import get_settings
from app.db import session


SHARE_COOKIE_NAME = "money_note_share_session"
SHARE_SESSION_DAYS = 3650
DEFAULT_SHARE_PIN = "0000"


def ensure_default_share_pin() -> None:
    """공유 PIN이 없는 기존 DB를 기본 PIN 0000으로 잠근다."""
    with session() as conn:
        pin_row = conn.execute("SELECT value FROM app_settings WHERE key = 'share_pin_hash'").fetchone()
        state_row = conn.execute("SELECT value FROM app_settings WHERE key = 'share_pin_is_default'").fetchone()
        if pin_row is not None and pin_row["value"]:
            if state_row is None:
                conn.execute(
                    "INSERT INTO app_settings(key, value) VALUES ('share_pin_is_default', '0')"
                )
            return
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES ('share_pin_hash', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (hash_password(DEFAULT_SHARE_PIN),),
        )
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES ('share_pin_is_default', '1', CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = '1', updated_at = CURRENT_TIMESTAMP
            """
        )


def set_share_pin(pin: str) -> None:
    """가족 공유용 네 자리 PIN을 해시로 저장하고 기존 공유 세션을 모두 종료한다."""
    with session() as conn:
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES ('share_pin_hash', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (hash_password(pin),),
        )
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES ('share_pin_is_default', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            ("1" if pin == DEFAULT_SHARE_PIN else "0",),
        )
        conn.execute("DELETE FROM share_sessions")


def share_pin_needs_change() -> bool:
    """공유 PIN이 아직 기본값 0000인지 반환한다."""
    with session() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'share_pin_is_default'").fetchone()
    return row is None or row["value"] == "1"


def unlock_share(pin: str, response: Response) -> bool:
    """PIN이 맞으면 장기 공유 세션 cookie를 발급한다."""
    with session() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'share_pin_hash'").fetchone()
    if row is None or not verify_password(pin, row["value"]):
        return False

    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SHARE_SESSION_DAYS)
    with session() as conn:
        conn.execute(
            """
            INSERT INTO share_sessions(session_token_hash, expires_at)
            VALUES (?, ?)
            """,
            (_token_hash(token), _datetime_to_db(expires_at)),
        )
    settings = get_settings()
    response.set_cookie(
        key=SHARE_COOKIE_NAME,
        value=token,
        max_age=SHARE_SESSION_DAYS * 24 * 60 * 60,
        expires=SHARE_SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return True


def share_access_allowed(request: Request) -> bool:
    """유효한 공유 전용 세션이 있는 요청만 허용한다."""
    token = request.cookies.get(SHARE_COOKIE_NAME)
    if not token:
        return False
    now = _datetime_to_db(datetime.now(timezone.utc))
    with session() as conn:
        row = conn.execute(
            """
            SELECT id, expires_at
            FROM share_sessions
            WHERE session_token_hash = ?
            """,
            (_token_hash(token),),
        ).fetchone()
        if row is None:
            return False
        if row["expires_at"] <= now:
            conn.execute("DELETE FROM share_sessions WHERE id = ?", (row["id"],))
            return False
        conn.execute(
            "UPDATE share_sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["id"],),
        )
    return True


def share_unlock_html(next_path: str) -> str:
    """공유 페이지 앞에 표시하는 간단한 가족 PIN 입력 화면이다."""
    safe_next = next_path if next_path.startswith("/share/") else "/share/claim"
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>가족 공유 확인 - money-note</title>
  <style>
    body {{ margin:0; min-height:100vh; display:grid; place-items:center; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#f7f7f4; color:#242424; }}
    main {{ width:min(360px,calc(100% - 32px)); padding:22px; border:1px solid #ddd8ce; border-radius:8px; background:#fff; }}
    h1 {{ margin:0 0 8px; font-size:20px; }}
    p {{ color:#666; }}
    form {{ display:grid; gap:10px; }}
    input,button {{ font:inherit; padding:10px; border:1px solid #ccc; border-radius:6px; }}
    button {{ cursor:pointer; background:#eef5e9; }}
    #message {{ min-height:20px; color:#8d2424; font-size:13px; }}
  </style>
</head>
<body>
  <main>
    <h1>가족 공유 확인</h1>
    <p>가족 공식 비밀번호 네 자리를 입력하세요.</p>
    <form id="unlock-form">
      <input id="pin" inputmode="numeric" pattern="[0-9]{{4}}" maxlength="4" autocomplete="one-time-code" required>
      <button type="submit">확인</button>
      <div id="message"></div>
    </form>
  </main>
  <script>
    document.getElementById("unlock-form").addEventListener("submit", async (event) => {{
      event.preventDefault();
      const response = await fetch("/api/share/unlock", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        credentials: "include",
        body: JSON.stringify({{ pin: document.getElementById("pin").value }})
      }});
      if (response.ok) window.location.href = {safe_next!r};
      else document.getElementById("message").textContent = "비밀번호가 맞지 않습니다.";
    }});
  </script>
</body>
</html>"""


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _datetime_to_db(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

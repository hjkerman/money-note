import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import Request, Response

from app.auth import (
    change_password,
    create_mobile_session_token,
    create_session_cookie,
    create_user,
    current_user_from_request,
)
from app.config import get_settings
from app.db import init_db, session
from app.routers.auth import login, login_limiter, mobile_login
from app.schemas import LoginIn


class _Request:
    def __init__(self, token: str) -> None:
        self.cookies = {}
        self.headers = {"Authorization": f"Bearer {token}"}


class AuthSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "money-note.sqlite3"
        self.env = patch.dict(
            os.environ,
            {
                "MONEY_NOTE_DB_PATH": str(self.db_path),
                "MONEY_NOTE_SESSION_DAYS": "30",
                "MONEY_NOTE_MOBILE_SESSION_DAYS": "3650",
            },
        )
        self.env.start()
        get_settings.cache_clear()
        init_db()
        login_limiter.reset()
        self.user = create_user("tester", "test-secret-123", "테스트")

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_web_and_mobile_session_ttl_are_separated(self) -> None:
        create_session_cookie(Response(), self.user["id"])
        create_mobile_session_token(self.user["id"])

        with session() as conn:
            rows = conn.execute(
                "SELECT expires_at FROM auth_sessions ORDER BY id"
            ).fetchall()

        self.assertEqual(len(rows), 2)
        self.assertLess(rows[0]["expires_at"], rows[1]["expires_at"])

    def test_mobile_login_returns_long_lived_bearer_token(self) -> None:
        response = mobile_login(
            LoginIn(username="tester", password="test-secret-123"),
            self._request(),
        )
        token = response["session_token"]

        self.assertTrue(token)
        self.assertEqual(current_user_from_request(_Request(token))["username"], "tester")
        with session() as conn:
            expires_at = conn.execute(
                "SELECT expires_at FROM auth_sessions"
            ).fetchone()["expires_at"]
        self.assertGreater(expires_at[:4], "2030")

    def test_web_login_does_not_expose_cookie_token_in_json(self) -> None:
        response = Response()
        result = login(
            LoginIn(username="tester", password="test-secret-123"),
            self._request(),
            response,
        )

        self.assertIsNone(result["session_token"])
        self.assertIn(get_settings().session_cookie_name, response.headers["set-cookie"])

    def test_password_change_invalidates_all_existing_sessions(self) -> None:
        web_response = Response()
        web_token = create_session_cookie(web_response, self.user["id"])
        mobile_token = create_mobile_session_token(self.user["id"])

        self.assertTrue(change_password(self.user["id"], "test-secret-123", "new-secret-1234"))

        self.assertIsNone(current_user_from_request(_Request(web_token)))
        self.assertIsNone(current_user_from_request(_Request(mobile_token)))

    def test_repeated_mobile_login_failures_are_throttled(self) -> None:
        for _ in range(5):
            with self.assertRaises(Exception):
                mobile_login(LoginIn(username="tester", password="wrong"), self._request())

        with self.assertRaises(Exception) as raised:
            mobile_login(LoginIn(username="tester", password="test-secret-123"), self._request())

        self.assertEqual(getattr(raised.exception, "status_code", None), 429)

    def test_account_creation_rejects_short_password(self) -> None:
        with self.assertRaises(ValueError):
            create_user("short-password-user", "short", "테스트")

    @staticmethod
    def _request() -> Request:
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/auth/mobile-login",
                "headers": [],
                "client": ("127.0.0.1", 50000),
                "server": ("testserver", 80),
                "scheme": "http",
                "query_string": b"",
            }
        )


if __name__ == "__main__":
    unittest.main()

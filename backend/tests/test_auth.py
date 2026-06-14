import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import Response

from app.auth import (
    create_mobile_session_token,
    create_session_cookie,
    create_user,
    current_user_from_request,
)
from app.config import get_settings
from app.db import init_db, session
from app.routers.auth import mobile_login
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
        self.user = create_user("tester", "secret", "테스트")

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
        response = mobile_login(LoginIn(username="tester", password="secret"))
        token = response["session_token"]

        self.assertTrue(token)
        self.assertEqual(current_user_from_request(_Request(token))["username"], "tester")
        with session() as conn:
            expires_at = conn.execute(
                "SELECT expires_at FROM auth_sessions"
            ).fetchone()["expires_at"]
        self.assertGreater(expires_at[:4], "2030")


if __name__ == "__main__":
    unittest.main()

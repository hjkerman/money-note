import os
import asyncio
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import Request

from app.config import Settings, get_settings
from app.db import init_db, session
from app.security import (
    ApiBodyLimitMiddleware,
    AttemptLimit,
    FailedAttemptLimiter,
    request_client_key,
)
from app.services.maintenance import run_startup_maintenance


def _request(client_host: str, forwarded_for: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/login",
            "headers": [(b"x-forwarded-for", forwarded_for.encode("ascii"))],
            "client": (client_host, 50000),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


class SecurityPolicyTest(unittest.TestCase):
    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_proxy_key_uses_last_forwarded_address(self) -> None:
        with patch.dict(os.environ, {"MONEY_NOTE_TRUST_PROXY_HEADERS": "true"}):
            get_settings.cache_clear()
            key = request_client_key(
                _request("172.18.0.1", "198.51.100.7, 203.0.113.9"),
                "Tester",
            )

        self.assertEqual(key, "203.0.113.9:tester")

    def test_untrusted_direct_client_cannot_spoof_forwarded_address(self) -> None:
        with patch.dict(os.environ, {"MONEY_NOTE_TRUST_PROXY_HEADERS": "true"}):
            get_settings.cache_clear()
            key = request_client_key(_request("8.8.8.8", "203.0.113.9"), "Tester")

        self.assertEqual(key, "8.8.8.8:tester")

    def test_production_https_requires_secure_cookie(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MONEY_NOTE_CORS_ORIGINS": "https://money.example.test",
                "MONEY_NOTE_COOKIE_SECURE": "false",
            },
        ):
            with self.assertRaises(RuntimeError):
                Settings().validate_runtime()

    def test_cors_wildcard_is_rejected(self) -> None:
        with patch.dict(os.environ, {"MONEY_NOTE_CORS_ORIGINS": "*"}):
            with self.assertRaises(RuntimeError):
                Settings().validate_runtime()

    def test_snapshot_body_limit_rejects_chunked_oversize_body(self) -> None:
        async def consume_body(scope, receive, send) -> None:
            while True:
                message = await receive()
                if not message.get("more_body"):
                    break
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        messages = iter(
            [
                {"type": "http.request", "body": b"123456", "more_body": True},
                {"type": "http.request", "body": b"789012", "more_body": False},
            ]
        )
        sent = []

        async def receive():
            return next(messages)

        async def send(message):
            sent.append(message)

        middleware = ApiBodyLimitMiddleware(
            consume_body,
            api_max_bytes=8,
            snapshot_max_bytes=10,
        )
        asyncio.run(
            middleware(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/api/admin/snapshot/restore",
                    "headers": [],
                },
                receive,
                send,
            )
        )

        self.assertEqual(sent[0]["status"], 413)

    def test_api_body_limit_rejects_non_snapshot_oversize_body(self) -> None:
        async def consume_body(scope, receive, send) -> None:
            await receive()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        sent = []

        async def receive():
            return {
                "type": "http.request",
                "body": b"123456789",
                "more_body": False,
            }

        async def send(message):
            sent.append(message)

        middleware = ApiBodyLimitMiddleware(
            consume_body,
            api_max_bytes=8,
            snapshot_max_bytes=10,
        )
        asyncio.run(
            middleware(
                {
                    "type": "http",
                    "method": "POST",
                    "path": "/api/auth/login",
                    "headers": [],
                },
                receive,
                send,
            )
        )

        self.assertEqual(sent[0]["status"], 413)

    def test_failed_attempt_limiter_bounds_tracked_identity_count(self) -> None:
        limiter = FailedAttemptLimiter(
            AttemptLimit(max_failures=5, window_seconds=300),
            max_tracked_keys=2,
        )

        limiter.register_failure("first")
        limiter.register_failure("second")
        limiter.register_failure("third")

        self.assertLessEqual(len(limiter._failures), 2)


class StartupMaintenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "money-note.sqlite3"
        self.env = patch.dict(os.environ, {"MONEY_NOTE_DB_PATH": str(self.db_path)})
        self.env.start()
        get_settings.cache_clear()
        init_db()

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_expired_sessions_and_old_audit_logs_are_removed(self) -> None:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO users(username, password_hash, display_name)
                VALUES ('tester', 'hash', '테스트')
                """
            )
            conn.execute(
                """
                INSERT INTO auth_sessions(user_id, session_token_hash, expires_at)
                VALUES (1, 'expired', '2000-01-01T00:00:00Z')
                """
            )
            conn.execute(
                """
                INSERT INTO share_sessions(session_token_hash, expires_at)
                VALUES ('expired', '2000-01-01T00:00:00Z')
                """
            )
            conn.execute(
                """
                INSERT INTO audit_logs(
                    occurred_at, actor_username, method, path, status_code
                )
                VALUES ('2000-01-01T00:00:00Z', 'tester', 'POST', '/api/test', 200)
                """
            )

        run_startup_maintenance(audit_retention_days=180, pre_restore_keep_count=30)

        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM share_sessions").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()

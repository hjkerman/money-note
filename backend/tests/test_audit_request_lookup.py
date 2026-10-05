"""Per-request audit/auth responsibilities, not a fixed refresh topology."""

from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import auth, db, main
from app.config import get_settings
from app.routers import auth as auth_router
from app.services.audit import list_audit_logs, record_audit_log
from tests.db_fixture import IsolatedDatabaseTestCase


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 6, 11, 12, tzinfo=timezone.utc).astimezone(tz)


class AuditRequestLookupTest(IsolatedDatabaseTestCase):
    GETS = (
        "/api/auth/me", "/api/settings", "/api/entries/current",
        "/api/month/current/summary", "/api/month/current/status",
        "/api/offline-reconciliation/baseline", "/api/audit-logs",
    )

    def setUp(self):
        super().setUp()
        self.day = patch.dict("os.environ", {"MONEY_NOTE_TODAY": "2026-06-11"})
        self.day.start()
        get_settings.cache_clear()
        self.user = auth.create_user("synthetic-owner", "synthetic-password-123")
        self.token = auth.create_mobile_session_token(self.user["id"])
        self.client = TestClient(main.app)
        auth_router.login_limiter.reset()

    def tearDown(self):
        self.client.close()
        self.day.stop()
        super().tearDown()

    @contextmanager
    def observe(self):
        real_connect, real_lookup = db.connect, auth.current_user_from_request
        statements = []

        def connect():
            conn = real_connect()
            conn.set_trace_callback(lambda sql: statements.append(" ".join(sql.split())))
            return conn

        with patch.object(db, "connect", side_effect=connect), \
                patch.object(main, "current_user_from_request", wraps=real_lookup) as audit, \
                patch.object(auth, "current_user_from_request", wraps=real_lookup) as dependency, \
                patch.object(auth_router, "current_user_from_request", wraps=real_lookup) as direct:
            yield audit, dependency, direct, statements

    def request(self, method, path, *, token=None, **kwargs):
        return self.client.request(method, path, headers={"Authorization": f"Bearer {token or self.token}"}, **kwargs)

    def assert_work(self, observed, *, audit, authentication, touches):
        auditor, dependency, direct, statements = observed
        self.assertEqual(auditor.call_count, audit)
        self.assertEqual(dependency.call_count + direct.call_count, authentication)
        self.assertEqual(sum(sql.startswith("UPDATE auth_sessions SET last_seen_at")
                             for sql in statements), touches)

    def test_authenticated_gets_do_not_resolve_an_unused_audit_actor(self):
        for path in self.GETS:
            with self.subTest(path=path), self.observe() as observed:
                response = self.request("GET", path)
                self.assertEqual(response.status_code, 200)
                self.assert_work(observed, audit=0, authentication=1, touches=1)
            self.assertEqual(list_audit_logs(), [])

    def test_get_still_touches_session_once_without_extending_expiry(self):
        with db.session() as conn:
            conn.execute("UPDATE auth_sessions SET last_seen_at='2000-01-01T00:00:00Z'")
            expiry = conn.execute("SELECT expires_at FROM auth_sessions").fetchone()[0]
        with self.observe() as observed:
            response = self.request("GET", "/api/settings")
            self.assertEqual(response.status_code, 200)
            self.assert_work(observed, audit=0, authentication=1, touches=1)
        with db.session() as conn:
            row = conn.execute("SELECT last_seen_at,expires_at FROM auth_sessions").fetchone()
        self.assertNotEqual(row["last_seen_at"], "2000-01-01T00:00:00Z")
        self.assertEqual(row["expires_at"], expiry)

    def test_expired_and_inactive_get_sessions_reject_and_are_removed(self):
        for reason in ("expired", "at_expiry", "inactive"):
            with self.subTest(reason=reason):
                token = auth.create_mobile_session_token(self.user["id"])
                token_hash = auth._hash_session_token(token)
                with db.session() as conn:
                    conn.execute("UPDATE users SET is_active=1 WHERE id=?", (self.user["id"],))
                    if reason == "inactive":
                        conn.execute("UPDATE users SET is_active=0 WHERE id=?", (self.user["id"],))
                    else:
                        expires = "2026-06-11T11:59:59Z" if reason == "expired" else "2026-06-11T12:00:00Z"
                        conn.execute("UPDATE auth_sessions SET expires_at=? WHERE session_token_hash=?", (expires, token_hash))
                with patch.object(auth, "datetime", FixedDatetime), self.observe() as observed:
                    response = self.request("GET", "/api/settings", token=token)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.json(), {"detail": "authentication required"})
                    self.assert_work(observed, audit=0, authentication=1, touches=0)
                with db.session() as conn:
                    self.assertIsNone(conn.execute("SELECT id FROM auth_sessions WHERE session_token_hash=?", (token_hash,)).fetchone())
        self.assertEqual(list_audit_logs(), [])

    def test_missing_unknown_revoked_and_share_tokens_cannot_authenticate_gets(self):
        with db.session() as conn:
            conn.execute("DELETE FROM auth_sessions")
        for headers in ({}, {"Authorization": "Bearer unknown"},
                        {"Authorization": f"Bearer {self.token}"},
                        {"Cookie": "money_note_share_session=not-an-owner-session"}):
            for path in self.GETS:
                with self.subTest(path=path, headers=bool(headers)), self.observe() as observed:
                    response = self.client.get(path, headers=headers)
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.json(), {"detail": "authentication required"})
                    self.assert_work(observed, audit=0, authentication=1, touches=0)
        self.assertEqual(list_audit_logs(), [])

    def test_cookie_precedence_and_different_principals_do_not_leak(self):
        other = auth.create_user("synthetic-other", "synthetic-password-456")
        other_token = auth.create_mobile_session_token(other["id"])
        cookie_name = get_settings().session_cookie_name
        headers = {"Authorization": f"Bearer {self.token}", "Cookie": f"{cookie_name}={other_token}"}
        with self.observe() as observed:
            response = self.client.get("/api/auth/me", headers=headers)
            self.assertEqual(response.json()["id"], other["id"])
            self.assert_work(observed, audit=0, authentication=1, touches=1)
        headers["Cookie"] = f"{cookie_name}=invalid-cookie"
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)
        self.assertEqual(self.request("GET", "/api/auth/me").json()["id"], self.user["id"])

    def test_parallel_reads_authenticate_each_request_without_principal_reuse(self):
        other = auth.create_user("synthetic-other", "synthetic-password-456")
        other_token = auth.create_mobile_session_token(other["id"])
        cases = [(self.token, self.user["id"]), (other_token, other["id"])] * 4

        def read(case):
            token, owner_id = case
            result = self.request("GET", "/api/auth/me", token=token)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["id"], owner_id)

        with self.observe() as observed, ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(read, cases))
            self.assert_work(observed, audit=0, authentication=len(cases), touches=len(cases))
        self.assertEqual(list_audit_logs(), [])

    def test_non_audited_methods_and_public_paths_do_not_resolve_owner(self):
        cases = (("GET", "/health", 200), ("GET", "/not-found", 404),
                 ("HEAD", "/api/settings", 405), ("OPTIONS", "/api/settings", 405))
        for method, path, status in cases:
            with self.subTest(method=method, path=path), self.observe() as observed:
                self.assertEqual(self.request(method, path).status_code, status)
                self.assert_work(observed, audit=0, authentication=0, touches=0)
        self.assertEqual(list_audit_logs(), [])

    def test_audit_clear_keeps_authentication_but_does_not_resolve_audit_actor(self):
        record_audit_log("synthetic-owner", "POST", "/api/entries", 200)
        with self.observe() as observed:
            response = self.request("DELETE", "/api/audit-logs")
            self.assertEqual(response.json(), {"deleted": 1})
            self.assert_work(observed, audit=0, authentication=1, touches=1)
        self.assertEqual(list_audit_logs(), [])

    def test_post_patch_delete_keep_actor_and_exactly_one_audit_row(self):
        payload = {"book_section": "current", "entry_date": "2026-06-11", "title": "synthetic expense",
                   "usage_place": "synthetic merchant", "amount_value": 10000, "sort_order": 0}
        with self.observe() as observed:
            response = self.request("POST", "/api/entries", json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            self.assert_work(observed, audit=1, authentication=1, touches=2)
        child = response.json()["id"]
        for method, body in (("PATCH", {"amount_value": 7000}), ("DELETE", None)):
            with self.subTest(method=method), self.observe() as observed:
                response = self.request(method, f"/api/entries/{child}", **({"json": body} if body else {}))
                self.assertEqual(response.status_code, 200)
                self.assert_work(observed, audit=1, authentication=1, touches=2)
        rows = list(reversed(list_audit_logs()))
        self.assertEqual([(r["actor_username"], r["method"], r["path"], r["status_code"]) for r in rows],
                         [("synthetic-owner", "POST", "/api/entries", 200),
                          ("synthetic-owner", "PATCH", f"/api/entries/{child}", 200),
                          ("synthetic-owner", "DELETE", f"/api/entries/{child}", 200)])

    def test_failed_and_unauthorized_mutations_still_have_audit_evidence(self):
        for method, path, status in (("POST", "/api/entries", 422),
                                     ("PATCH", "/api/entries/999999", 404),
                                     ("DELETE", "/api/entries/999999", 404)):
            for authorized in (True, False):
                with self.subTest(method=method, authorized=authorized), self.observe() as observed:
                    result = self.request(method, path, token=self.token if authorized else "unknown",
                                          **({"json": {}} if method != "DELETE" else {}))
                    expected = status if authorized else 401
                    self.assertEqual(result.status_code, expected)
                    self.assert_work(observed, audit=1, authentication=1, touches=2 if authorized else 0)
                row = list_audit_logs()[0]
                self.assertEqual((row["actor_username"], row["method"], row["path"], row["status_code"]),
                                 ("synthetic-owner" if authorized else "anonymous", method, path, expected))

    def test_cross_origin_rejection_still_records_the_original_actor(self):
        with self.observe() as observed:
            result = self.client.post("/api/entries", json={}, headers={
                "Authorization": f"Bearer {self.token}", "Origin": "https://untrusted.invalid",
            })
            self.assertEqual(result.status_code, 403)
            self.assert_work(observed, audit=1, authentication=0, touches=1)
        row = list_audit_logs()[0]
        self.assertEqual((row["actor_username"], row["status_code"]), ("synthetic-owner", 403))

    def test_logout_relogin_and_password_change_revoke_without_stale_actor(self):
        result = self.request("POST", "/api/auth/logout")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(list_audit_logs()[0]["actor_username"], "synthetic-owner")
        self.assertEqual(self.request("GET", "/api/auth/me").status_code, 401)
        login = self.client.post("/api/auth/mobile-login", json={
            "username": "synthetic-owner", "password": "synthetic-password-123",
        })
        self.assertEqual(login.status_code, 200)
        new_token = login.json()["session_token"]
        self.assertNotEqual(new_token, self.token)
        self.assertEqual(self.request("GET", "/api/auth/me", token=new_token).json()["id"], self.user["id"])
        changed = self.request("PATCH", "/api/auth/password", token=new_token, json={
            "current_password": "synthetic-password-123", "new_password": "synthetic-new-password-123",
        })
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(list_audit_logs()[0]["actor_username"], "synthetic-owner")
        self.assertEqual(self.request("GET", "/api/auth/me", token=new_token).status_code, 401)

    def test_audit_storage_failure_does_not_change_mutation_response(self):
        with patch.object(main, "record_audit_log", side_effect=OSError("synthetic audit failure")):
            response = self.request("POST", "/api/cash-flows", json={
                "occurred_on": "2026-06-11", "title": "cash", "amount_value": 1000, "sort_order": 0,
            })
        self.assertEqual(response.status_code, 200)
        with db.session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM cash_flows").fetchone()[0], 1)

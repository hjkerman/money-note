import gzip
import json
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from app.auth import create_mobile_session_token, create_user
from app.main import app
from app.routers.response_coding import code_json_response
from app.services.snapshot import _validate_snapshot
from tests.db_fixture import IsolatedDatabaseTestCase
from tests.test_authoritative_state import FrozenSnapshotClock, _MESSAGE_RANDOM


def request(encoding=None, path="/api/admin/snapshot", method="GET"):
    headers = [] if encoding is None else [(b"accept-encoding", encoding.encode())]
    return Request({"type": "http", "method": method, "path": path, "headers": headers})


def response(size=1024, **kwargs):
    return Response(b"x" * size, media_type="application/json", **kwargs)


class ResponseCodingTest(TestCase):
    def test_negotiation(self):
        cases = [
            (None, None, 200), ("", None, 200), ("identity", None, 200),
            ("gzip", "gzip", 200), ("GZip;Q=1.000", "gzip", 200),
            ("gzip;q=0", None, 200), ("gzip;q=0, *;q=1", None, 200),
            ("*", "gzip", 200), ("*;q=0", None, 406),
            ("gzip;q=1, identity;q=0", "gzip", 200),
            ("gzip;q=0.5, identity;q=0.1", "gzip", 200),
            ("gzip;q=0.5", None, 200), ("br", None, 200),
            ("br, identity;q=0", None, 406),
            ("*;q=0, gzip;q=1", "gzip", 200),
            ("*;q=0, identity;q=1", None, 200),
            ("gzip;q=1.001, identity;q=0", None, 406),
            ("gzip;q=nan", None, 200), ("gzip;q=-1", None, 200),
            ("gzip;q=0, gzip;q=1", None, 200),
        ]
        for encoding, expected, status in cases:
            with self.subTest(encoding=encoding):
                result = code_json_response(request(encoding), response())
                self.assertEqual(result.status_code, status)
                self.assertEqual(result.headers.get("content-encoding"), expected)
                self.assertEqual(int(result.headers["content-length"]), len(result.body))
                if expected: self.assertEqual(gzip.decompress(result.body), b"x" * 1024)
                if status == 406: self.assertEqual(result.body, b"")

    def test_threshold_and_forbidden_identity(self):
        for size in (0, 1023, 1024):
            with self.subTest(size=size):
                result = code_json_response(request("gzip"), response(size))
                self.assertEqual(result.headers.get("content-encoding"), "gzip" if size >= 1024 else None)
        self.assertEqual(code_json_response(request("gzip, identity;q=0"), response(1023)).status_code, 406)

    def test_repeated_header_fields_and_vary(self):
        r = request("gzip")
        r.scope["headers"].append((b"accept-encoding", b"identity;q=0"))
        original = response(headers={"vary": "Origin", "cache-control": "no-store", "content-disposition": 'attachment; filename="test.json"'})
        original.raw_headers.append((b"vary", b"X-Example"))
        result = code_json_response(r, original)
        self.assertEqual(result.headers["vary"], "Origin, X-Example, Accept-Encoding")
        self.assertEqual(result.headers["cache-control"], "no-store")
        self.assertEqual(result.headers["content-disposition"], 'attachment; filename="test.json"')
        self.assertIs(code_json_response(r, result), result)
        self.assertEqual(gzip.decompress(result.body), b"x" * 1024)
        for vary in ("*", "Origin, accept-encoding"):
            result = code_json_response(request("identity"), response(headers={"vary": vary}))
            self.assertEqual(result.headers["vary"], vary)

    def test_exclusions(self):
        cases = [(request("gzip", method="POST"), response()),
                 (request("gzip", path="/api/entries"), response()),
                 (request("gzip"), response(status_code=401)),
                 (request("gzip"), response(status_code=422)),
                 (request("gzip"), Response(b"x" * 2048, media_type="application/octet-stream")),
                 (request("gzip"), StreamingResponse(iter([b"x" * 2048]), media_type="application/json")),
                 (request("gzip"), response(headers={"content-encoding": "br"}))]
        for req, original in cases:
            with self.subTest(method=req.method, path=req.url.path, status=original.status_code):
                self.assertIs(code_json_response(req, original), original)
                self.assertNotEqual(original.headers.get("content-encoding"), "gzip")

    def test_compression_failure_is_atomic(self):
        with patch("app.routers.response_coding.gzip.compress", side_effect=RuntimeError("private failure")):
            original = response()
            self.assertIs(code_json_response(request("gzip"), original), original)
            self.assertEqual(original.body, b"x" * 1024)
            failed = code_json_response(request("gzip, identity;q=0"), response())
            self.assertEqual(failed.status_code, 503)
            self.assertEqual(failed.body, b"")
            self.assertNotIn("content-encoding", failed.headers)


class EndpointCodingTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        user = create_user("coding-owner", "synthetic-password-123")
        self.token = create_mobile_session_token(user["id"])
        self.client = TestClient(app, headers={"Authorization": f"Bearer {self.token}"})
        self.addCleanup(self.client.close)

    def read(self, path, encoding):
        _MESSAGE_RANDOM.seed(1234)
        with patch("app.services.snapshot.datetime", FrozenSnapshotClock):
            with self.client.stream("GET", path, headers={"Accept-Encoding": encoding}) as r:
                return r.status_code, dict(r.headers), b"".join(r.iter_raw())

    def test_both_routes_byte_exact_snapshot_integrity_and_headers(self):
        for path in ("/api/admin/snapshot", "/api/authoritative-state"):
            with self.subTest(path=path):
                a, ah, raw = self.read(path, "identity")
                b, bh, encoded = self.read(path, "gzip")
                self.assertEqual((a, b), (200, 200))
                self.assertEqual(gzip.decompress(encoded), raw)
                self.assertEqual(bh["content-encoding"], "gzip")
                self.assertEqual(int(bh["content-length"]), len(encoded))
                self.assertEqual(ah["cache-control"], bh["cache-control"])
                self.assertIn("no-store", bh["cache-control"])
                self.assertEqual(ah.get("content-disposition"), bh.get("content-disposition"))
                value = json.loads(raw)
                _validate_snapshot(value if path.endswith("snapshot") else value["snapshot"])
                self.assertIn("Accept-Encoding", bh["vary"])

    def test_auth_errors_and_unrelated_route_unchanged(self):
        anonymous = TestClient(app)
        self.addCleanup(anonymous.close)
        for path in ("/api/admin/snapshot", "/api/authoritative-state"):
            r = anonymous.get(path, headers={"Accept-Encoding": "gzip"})
            self.assertEqual(r.status_code, 401)
            self.assertNotIn("content-encoding", r.headers)
        with patch("app.routers.authoritative_state.authoritative_state_response", side_effect=ValueError("rejected")):
            r = self.client.get("/api/authoritative-state", headers={"Accept-Encoding": "gzip"})
            self.assertEqual(r.status_code, 422)
            self.assertNotIn("content-encoding", r.headers)
        r = self.client.get("/api/entries/current", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("content-encoding", r.headers)

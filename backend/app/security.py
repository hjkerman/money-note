from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from ipaddress import ip_address
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import get_settings


@dataclass(frozen=True)
class AttemptLimit:
    max_failures: int
    window_seconds: int


class FailedAttemptLimiter:
    """로그인 실패를 짧게 기억해 공개 엔드포인트의 무제한 대입을 막는다."""

    def __init__(self, limit: AttemptLimit, max_tracked_keys: int = 4096) -> None:
        self.limit = limit
        self.max_tracked_keys = max_tracked_keys
        self._failures: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = monotonic()
        with self._lock:
            failures = self._active_failures(key, now)
            if len(failures) < self.limit.max_failures:
                return
            retry_after = max(1, int(self.limit.window_seconds - (now - failures[0])))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many authentication attempts",
            headers={"Retry-After": str(retry_after)},
        )

    def register_failure(self, key: str) -> None:
        now = monotonic()
        with self._lock:
            failures = self._active_failures(key, now)
            if key not in self._failures:
                self._prune_expired(now)
                if len(self._failures) >= self.max_tracked_keys:
                    self._failures.pop(next(iter(self._failures)))
                self._failures[key] = failures
            failures.append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        """테스트와 프로세스 초기화 시 누적된 실패 횟수를 비운다."""
        with self._lock:
            self._failures.clear()

    def _active_failures(self, key: str, now: float) -> deque[float]:
        failures = self._failures.get(key)
        if failures is None:
            return deque()
        cutoff = now - self.limit.window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        if not failures:
            self._failures.pop(key, None)
        return failures

    def _prune_expired(self, now: float) -> None:
        for key in tuple(self._failures):
            self._active_failures(key, now)


class ApiBodyLimitMiddleware:
    """길이 헤더 유무와 무관하게 변경 API 요청 본문 크기를 제한한다."""

    def __init__(
        self,
        app: ASGIApp,
        api_max_bytes: int,
        snapshot_max_bytes: int,
    ) -> None:
        self.app = app
        self.api_max_bytes = api_max_bytes
        self.snapshot_max_bytes = snapshot_max_bytes

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        path = str(scope.get("path") or "")
        if (
            scope["type"] != "http"
            or scope.get("method") not in {"POST", "PATCH", "DELETE"}
            or not path.startswith("/api/")
        ):
            await self.app(scope, receive, send)
            return
        max_bytes = (
            self.snapshot_max_bytes
            if path == "/api/admin/snapshot/restore"
            else self.api_max_bytes
        )

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        try:
            content_length = int(headers.get("content-length", "0"))
        except ValueError:
            content_length = max_bytes + 1
        if content_length > max_bytes:
            await self._reject(scope, receive, send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    raise _ApiBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _ApiBodyTooLarge:
            await self._reject(scope, receive, send)

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        response = JSONResponse(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            content={"detail": "request body is too large"},
        )
        await response(scope, receive, send)


class _ApiBodyTooLarge(Exception):
    pass


def request_client_key(request: Request, identity: str = "") -> str:
    """리버스 프록시 환경에서도 인증 시도자를 구분할 최소 키를 만든다."""
    client_host = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if get_settings().trust_proxy_headers and forwarded_for and _is_local_proxy(client_host):
        # Apache/mod_proxy는 실제 접속자를 목록의 마지막에 덧붙인다. 첫 값을 믿으면
        # 외부 사용자가 임의 X-Forwarded-For로 로그인 제한을 우회할 수 있다.
        client_host = forwarded_for.rsplit(",", 1)[-1].strip() or client_host
    normalized_identity = identity.strip().casefold()
    return f"{client_host}:{normalized_identity}"


def _is_local_proxy(host: str) -> bool:
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address.is_private

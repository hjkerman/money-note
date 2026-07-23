from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.auth import current_user_from_request
from app.config import get_settings
from app.db import init_db
from app.routers import admin, audit, auth, card_payments, entries, month, operations, share
from app.services.audit import record_audit_log
from app.security import ApiBodyLimitMiddleware
from app.services.maintenance import run_startup_maintenance
from app.share_auth import ensure_default_share_pin


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime()
    init_db()
    ensure_default_share_pin()
    run_startup_maintenance(
        settings.audit_log_retention_days,
        settings.pre_restore_keep_count,
    )
    yield


app = FastAPI(title="money-note", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    ApiBodyLimitMiddleware,
    api_max_bytes=settings.api_request_max_bytes,
    snapshot_max_bytes=settings.snapshot_restore_max_bytes,
)

AUDIT_METHODS = {"POST", "PATCH", "DELETE"}
AUDIT_CLEAR_PATH = "/api/audit-logs"


@app.middleware("http")
async def reject_cross_origin_mutations(request: Request, call_next):
    """브라우저 cookie를 쓰는 변경 요청은 같은 사이트나 허용한 UI에서만 받는다."""
    if request.method in AUDIT_METHODS:
        origin = request.headers.get("origin", "").rstrip("/")
        if origin and origin not in _allowed_request_origins(request):
            return JSONResponse(status_code=403, content={"detail": "origin is not allowed"})
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """동적 금융 응답의 캐시·프레임·MIME 정책을 서버에서도 고정한다."""
    response = await call_next(request)
    if request.url.path.startswith(("/api/", "/share/")):
        response.headers.setdefault("Cache-Control", "no-store, max-age=0")
        response.headers.setdefault("Pragma", "no-cache")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
    if request.url.path.startswith("/share/"):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
    return response


@app.middleware("http")
async def audit_mutating_api_requests(request: Request, call_next):
    """변경 API의 경로와 결과만 기록하고 민감한 요청 본문은 남기지 않는다."""
    user = current_user_from_request(request)
    response = await call_next(request)
    if (
        request.method in AUDIT_METHODS
        and request.url.path.startswith("/api/")
        and not (request.method == "DELETE" and request.url.path == AUDIT_CLEAR_PATH)
    ):
        try:
            record_audit_log(
                str(user["username"]) if user else "anonymous",
                request.method,
                request.url.path,
                response.status_code,
            )
        except Exception:
            # 감사 로그 장애가 실제 가계부 조작을 실패시키지는 않는다.
            pass
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(audit.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(entries.router)
app.include_router(month.router)
app.include_router(month.judgment_router)
app.include_router(card_payments.payments_router)
app.include_router(card_payments.discounts_router)
app.include_router(share.api_router)
app.include_router(share.page_router)
app.include_router(operations.settings_router)
app.include_router(operations.cash_router)
app.include_router(operations.labels_router)


def _allowed_request_origins(request: Request) -> set[str]:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    scheme = forwarded_proto or request.url.scheme
    same_origin = f"{scheme}://{request.headers.get('host', '')}".rstrip("/")
    return {origin.rstrip("/") for origin in settings.cors_origins} | {same_origin}

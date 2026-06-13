from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.auth import current_user_from_request
from app.config import get_settings
from app.db import init_db
from app.routers import admin, audit, auth, card_payments, entries, month, operations, share
from app.services.audit import record_audit_log
from app.share_auth import ensure_default_share_pin

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_default_share_pin()
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

AUDIT_METHODS = {"POST", "PATCH", "DELETE"}
AUDIT_CLEAR_PATH = "/api/audit-logs"


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

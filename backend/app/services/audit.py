from __future__ import annotations

from typing import Any

from app.db import session


def record_audit_log(actor_username: str, method: str, path: str, status_code: int) -> None:
    """요청 본문 없이 변경 API의 결과만 감사 로그로 남긴다."""
    with session() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs(actor_username, method, path, status_code)
            VALUES (?, ?, ?, ?)
            """,
            (actor_username or "anonymous", method, path, status_code),
        )


def list_audit_logs(limit: int = 300) -> list[dict[str, Any]]:
    """관리 화면에 최근 감사 로그를 최신순으로 반환한다."""
    safe_limit = min(max(limit, 1), 1000)
    with session() as conn:
        rows = conn.execute(
            """
            SELECT id, occurred_at, actor_username, method, path, status_code
            FROM audit_logs
            ORDER BY occurred_at DESC, id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def clear_audit_logs() -> int:
    """사용자가 요청하면 감사 로그 전체를 초기화한다."""
    with session() as conn:
        cursor = conn.execute("DELETE FROM audit_logs")
    return cursor.rowcount

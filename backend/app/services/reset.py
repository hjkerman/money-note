from __future__ import annotations

from app.db import session


RESET_TABLES = [
    "card_payment_deferrals",
    "card_payment_allocations",
    "card_payment_events",
    "cash_flows",
    "monthly_panels",
    "ledger_entries",
]


def reset_ledger_data() -> dict[str, int]:
    """계정과 설정은 남기고 사용자가 입력한 장부 운용 데이터만 비운다."""
    deleted: dict[str, int] = {}
    with session() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in RESET_TABLES:
            cursor = conn.execute(f"DELETE FROM {table}")
            deleted[table] = cursor.rowcount if cursor.rowcount is not None else 0
        conn.execute("PRAGMA foreign_keys = ON")
    return deleted

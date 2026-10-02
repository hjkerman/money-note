from __future__ import annotations

from typing import Any

from app.db import borrowed_or_new_session
from app.services.snapshot import create_pre_restore_backup


RESET_TABLES = [
    "card_payment_batch_items",
    "card_payment_deferrals",
    "card_payment_allocations",
    "card_payment_events",
    "card_payment_batches",
    "cash_flows",
    "monthly_panels",
    "ledger_entries",
]


def reset_ledger_data(*, conn: Any | None = None) -> dict[str, int]:
    """계정과 설정은 남기고 사용자가 입력한 장부 운용 데이터만 비운다."""
    deleted: dict[str, int] = {}
    with borrowed_or_new_session(conn, transaction_mode="IMMEDIATE") as conn:
        create_pre_restore_backup(conn)
        for table in RESET_TABLES:
            cursor = conn.execute(f"DELETE FROM {table}")
            deleted[table] = cursor.rowcount if cursor.rowcount is not None else 0
    return deleted

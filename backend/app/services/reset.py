from __future__ import annotations

from app.db import session
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


def reset_ledger_data() -> dict[str, int]:
    """계정과 설정은 남기고 사용자가 입력한 장부 운용 데이터만 비운다."""
    deleted: dict[str, int] = {}
    create_pre_restore_backup()
    with session() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in RESET_TABLES:
            cursor = conn.execute(f"DELETE FROM {table}")
            deleted[table] = cursor.rowcount if cursor.rowcount is not None else 0
        conn.execute("PRAGMA foreign_keys = ON")
    return deleted

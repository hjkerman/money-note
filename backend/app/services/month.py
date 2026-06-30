from __future__ import annotations

from datetime import date
from typing import Any

from app.db import session
from app.services.clock import app_today
from app.services.card_payments import create_month_close_card_payment_batch
from app.services.snapshot import create_pre_restore_backup


EARLY_CLOSE_START_DAY = 27


def close_current_month(today: date | None = None, allow_early_close: bool = False) -> dict[str, Any]:
    """현재 장부에서 가장 오래된 미마감 월 하나만 archive로 옮긴다."""
    today = today or app_today()
    with session() as conn:
        target_row = conn.execute(
            """
            SELECT MIN(substr(entry_date, 1, 7)) AS month
            FROM ledger_entries
            WHERE book_section = 'current'
              AND entry_kind != 'planned'
              AND entry_date IS NOT NULL
            """
        ).fetchone()
        target_month = str(target_row["month"] or "")
        if not target_month:
            return {"closed_month": None, "archived": 0, "deleted_from_current": 0}
        calendar_month = today.strftime("%Y-%m")
        if target_month > calendar_month:
            raise ValueError("미래 달은 월마감할 수 없습니다.")
        if target_month == calendar_month:
            if today.day < EARLY_CLOSE_START_DAY:
                raise ValueError(f"현재 달 조기 월마감은 매월 {EARLY_CLOSE_START_DAY}일부터 가능합니다.")
            if not allow_early_close:
                raise ValueError("현재 달을 조기 월마감하려면 명시적인 확인이 필요합니다.")

        current_entries = conn.execute(
            """
            SELECT *
            FROM ledger_entries
            WHERE book_section = 'current'
              AND entry_kind != 'planned'
              AND entry_date LIKE ?
            ORDER BY sort_order, id
            """,
            (f"{target_month}%",),
        ).fetchall()

        create_pre_restore_backup()

        archived = 0
        next_order_row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM ledger_entries WHERE book_section = 'archive'"
        ).fetchone()
        next_order = int(next_order_row["next_order"])

        for entry in current_entries:
            conn.execute(
                """
                INSERT INTO ledger_entries (
                    book_section, entry_kind, entry_date, date_label, group_label, title, usage_place, usage_item,
                    amount_value, amount_expr, aux_amount_value, aux_amount_expr, extra_value,
                    sort_order, due_day, confirmed_at, spending_category, payment_key, discount_override
                )
                VALUES (
                    'archive', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    entry["entry_kind"],
                    entry["entry_date"],
                    entry["date_label"],
                    entry["group_label"],
                    entry["title"],
                    entry["usage_place"],
                    entry["usage_item"],
                    entry["amount_value"],
                    entry["amount_expr"],
                    entry["aux_amount_value"],
                    entry["aux_amount_expr"],
                    entry["extra_value"],
                    next_order,
                    entry["due_day"],
                    entry["confirmed_at"],
                    entry["spending_category"],
                    entry["payment_key"],
                    entry["discount_override"],
                ),
            )
            next_order += 1
            archived += 1

        deleted = conn.execute(
            """
            DELETE FROM ledger_entries
            WHERE book_section = 'current'
              AND entry_kind != 'planned'
              AND entry_date LIKE ?
            """,
            (f"{target_month}%",),
        ).rowcount
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES ('last_closed_month', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (target_month,),
        )
        conn.execute(
            """
            UPDATE ledger_entries
            SET entry_date = NULL,
                confirmed_at = NULL,
                confirmed_month = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE book_section = 'current'
              AND entry_kind = 'planned'
              AND confirmed_month = ?
            """,
            (target_month,),
        )
        create_month_close_card_payment_batch(conn, target_month)

    return {"closed_month": target_month, "archived": archived, "deleted_from_current": deleted}


def month_close_status(today: date | None = None) -> dict[str, Any]:
    """달력상 새 달인데 이전 월 장부가 남았는지 확인한다."""
    today = today or app_today()
    calendar_month = today.strftime("%Y-%m")
    with session() as conn:
        row = conn.execute(
            """
            SELECT MIN(substr(entry_date, 1, 7)) AS month
            FROM ledger_entries
            WHERE book_section = 'current'
              AND entry_kind != 'planned'
              AND entry_date IS NOT NULL
            """
        ).fetchone()
        setting = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'last_closed_month'"
        ).fetchone()
    oldest_open_month = str(row["month"] or "") or None
    is_early_close = bool(oldest_open_month and oldest_open_month == calendar_month)
    early_close_available = bool(is_early_close and today.day >= EARLY_CLOSE_START_DAY)
    return {
        "calendar_date": today.isoformat(),
        "calendar_month": calendar_month,
        "oldest_open_month": oldest_open_month,
        "last_closed_month": str(setting["value"]) if setting else None,
        "needs_close": bool(oldest_open_month and oldest_open_month < calendar_month),
        "is_early_close": is_early_close,
        "early_close_available": early_close_available,
        "early_close_start_day": EARLY_CLOSE_START_DAY,
        "can_close": bool(oldest_open_month and (oldest_open_month < calendar_month or early_close_available)),
    }


def current_month_label() -> str:
    """현재 기록에서 월 라벨을 추정하고, 기록이 없으면 오늘 기준 월을 사용한다."""
    with session() as conn:
        row = conn.execute(
            """
            SELECT entry_date
            FROM ledger_entries
            WHERE book_section = 'current' AND entry_date IS NOT NULL
            ORDER BY entry_date
            LIMIT 1
            """
        ).fetchone()
    if row and row["entry_date"]:
        return str(row["entry_date"])[:7]
    return app_today().strftime("%Y-%m")


def calendar_month_label(today: date | None = None) -> str:
    """청구·가족카드처럼 월마감과 무관한 기능에 달력상 현재 월을 제공한다."""
    return (today or app_today()).strftime("%Y-%m")

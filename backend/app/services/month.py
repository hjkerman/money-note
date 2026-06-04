from __future__ import annotations

from datetime import date

from app.db import session


def close_current_month() -> dict[str, int]:
    """당월 기록을 archive로 옮기고 다음 달에도 남아야 할 항목만 current에 유지한다."""
    with session() as conn:
        current_entries = conn.execute(
            """
            SELECT *
            FROM ledger_entries
            WHERE book_section = 'current'
            ORDER BY sort_order, id
            """
        ).fetchall()

        archived = 0
        next_order_row = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM ledger_entries WHERE book_section = 'archive'"
        ).fetchone()
        next_order = int(next_order_row["next_order"])

        for entry in current_entries:
            if entry["entry_kind"] == "planned":
                continue
            conn.execute(
                """
                INSERT INTO ledger_entries (
                    book_section, entry_kind, entry_date, date_label, group_label, title, usage_place, usage_item,
                    amount_value, amount_expr, aux_amount_value, aux_amount_expr, extra_value,
                    sort_order, due_day, confirmed_at, spending_category, payment_key
                )
                VALUES (
                    'archive', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
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
                ),
            )
            next_order += 1
            archived += 1

        deleted = conn.execute(
            "DELETE FROM ledger_entries WHERE book_section = 'current' AND entry_kind != 'planned'"
        ).rowcount
        conn.execute(
            """
            UPDATE ledger_entries
            SET confirmed_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE book_section = 'current' AND entry_kind = 'planned'
            """
        )
        conn.execute(
            """
            UPDATE installments
            SET remaining_months = MAX(remaining_months - 1, 0),
                is_active = CASE WHEN remaining_months <= 1 THEN 0 ELSE is_active END,
                updated_at = CURRENT_TIMESTAMP
            WHERE is_active = 1
            """
        )

    return {"archived": archived, "deleted_from_current": deleted}


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
    return date.today().strftime("%Y-%m")

from __future__ import annotations

from datetime import date

from app.db import session


def close_current_month() -> dict[str, int]:
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
                    book_section, entry_kind, entry_date, date_label, group_label, title,
                    amount_value, amount_expr, aux_amount_value, aux_amount_expr, extra_value, sort_order
                )
                VALUES (
                    'archive', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    entry["entry_kind"],
                    entry["entry_date"],
                    entry["date_label"],
                    entry["group_label"],
                    entry["title"],
                    entry["amount_value"],
                    entry["amount_expr"],
                    entry["aux_amount_value"],
                    entry["aux_amount_expr"],
                    entry["extra_value"],
                    next_order,
                ),
            )
            next_order += 1
            archived += 1

        deleted = conn.execute(
            "DELETE FROM ledger_entries WHERE book_section = 'current' AND entry_kind != 'planned'"
        ).rowcount

    return {"archived": archived, "deleted_from_current": deleted}


def current_month_label() -> str:
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

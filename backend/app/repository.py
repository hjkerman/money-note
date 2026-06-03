from datetime import date
from typing import Any

from app.db import session
from app.schemas import CashFlowIn, LedgerEntryIn, LedgerEntryPatch, MonthlyPanelIn, MonthlyPanelPatch, PlannedEntryIn


ENTRY_COLUMNS = [
    "book_section",
    "entry_kind",
    "entry_date",
    "date_label",
    "group_label",
    "title",
    "amount_value",
    "amount_expr",
    "aux_amount_value",
    "aux_amount_expr",
    "extra_value",
    "sort_order",
    "due_day",
    "confirmed_at",
    "spending_category",
]

PANEL_COLUMNS = [
    "month",
    "panel_type",
    "title",
    "amount_value",
    "amount_expr",
    "sort_order",
    "due_day",
    "confirmed_at",
]


def row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def list_entries(section: str) -> list[dict[str, Any]]:
    filter_confirmed_planned = " AND NOT (entry_kind = 'planned' AND confirmed_at IS NOT NULL)" if section == "current" else ""
    with session() as conn:
        rows = conn.execute(
            f"SELECT * FROM ledger_entries WHERE book_section = ?{filter_confirmed_planned} ORDER BY sort_order, id",
            (section,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def list_archive_rows() -> list[dict[str, Any]]:
    with session() as conn:
        rows = conn.execute("SELECT * FROM archive_rows ORDER BY sort_order, id").fetchall()
    return [row_to_dict(row) for row in rows]


def list_panels(month: str | None = None, include_confirmed_fixed: bool = False) -> list[dict[str, Any]]:
    filter_confirmed = "" if include_confirmed_fixed else " AND NOT (panel_type = 'fixed' AND confirmed_at IS NOT NULL)"
    with session() as conn:
        if month:
            rows = conn.execute(
                f"SELECT * FROM monthly_panels WHERE month = ?{filter_confirmed} ORDER BY sort_order, id",
                (month,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM monthly_panels WHERE 1 = 1{filter_confirmed} ORDER BY sort_order, id"
            ).fetchall()
    return [row_to_dict(row) for row in rows]


def list_labels() -> dict[str, str]:
    with session() as conn:
        rows = conn.execute("SELECT key, value FROM workbook_labels ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


def list_settings() -> dict[str, str]:
    with session() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


def upsert_label(key: str, value: str) -> dict[str, str]:
    with session() as conn:
        conn.execute(
            """
            INSERT INTO workbook_labels(key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
    return {key: value}


def create_panel(panel: MonthlyPanelIn) -> dict[str, Any]:
    values = panel.model_dump()
    placeholders = ", ".join("?" for _ in PANEL_COLUMNS)
    columns = ", ".join(PANEL_COLUMNS)
    with session() as conn:
        cursor = conn.execute(
            f"INSERT INTO monthly_panels ({columns}) VALUES ({placeholders})",
            tuple(values.get(column) for column in PANEL_COLUMNS),
        )
        row = conn.execute(
            "SELECT * FROM monthly_panels WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return row_to_dict(row)


def list_cash_flows() -> list[dict[str, Any]]:
    with session() as conn:
        rows = conn.execute(
            "SELECT * FROM cash_flows ORDER BY occurred_on DESC, sort_order DESC, id DESC"
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_cash_flow(flow: CashFlowIn) -> dict[str, Any]:
    values = flow.model_dump()
    with session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order)
            VALUES (?, ?, ?, ?)
            """,
            (values["occurred_on"], values["title"], values["amount_value"], values["sort_order"]),
        )
        row = conn.execute("SELECT * FROM cash_flows WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row)


def delete_cash_flow(flow_id: int) -> bool:
    with session() as conn:
        cursor = conn.execute("DELETE FROM cash_flows WHERE id = ?", (flow_id,))
    return cursor.rowcount > 0


def confirm_planned_entry(entry_id: int) -> dict[str, Any] | None:
    with session() as conn:
        planned = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        if planned is None:
            return None
        if planned["entry_kind"] != "planned":
            raise ValueError("only card recurring entries can be confirmed")
        if planned["confirmed_at"] is not None:
            raise ValueError("card recurring entry already confirmed")

        payment_date = planned_entry_payment_date(planned["due_day"])
        date_label = f"{payment_date:%Y.%m.%d}."
        max_order = conn.execute(
            """
            SELECT MAX(sort_order) AS sort_order
            FROM ledger_entries
            WHERE book_section = 'current'
            """
        ).fetchone()["sort_order"]
        sort_order = int(max_order or 2) + 1
        cursor = conn.execute(
            """
            INSERT INTO ledger_entries(
                book_section, entry_kind, entry_date, date_label, group_label, title,
                amount_value, amount_expr, sort_order
            )
            VALUES ('current', 'expense', ?, ?, NULL, ?, ?, ?, ?)
            """,
            (
                payment_date.isoformat(),
                date_label,
                planned["title"],
                planned["amount_value"],
                planned["amount_expr"],
                sort_order,
            ),
        )
        conn.execute(
            "UPDATE ledger_entries SET confirmed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (entry_id,),
        )
        entry = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (cursor.lastrowid,)).fetchone()
        updated_planned = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
    return {"planned": row_to_dict(updated_planned), "entry": row_to_dict(entry)}


def confirm_frozen_panel(panel_id: int) -> dict[str, Any] | None:
    today = date.today()
    date_label = f"{today:%Y.%m.%d}."
    with session() as conn:
        panel = conn.execute("SELECT * FROM monthly_panels WHERE id = ?", (panel_id,)).fetchone()
        if panel is None:
            return None
        if panel["panel_type"] != "frozen":
            raise ValueError("only frozen panels can be confirmed")

        max_order = conn.execute(
            """
            SELECT MAX(sort_order) AS sort_order
            FROM ledger_entries
            WHERE book_section = 'current'
            """
        ).fetchone()["sort_order"]
        sort_order = int(max_order or 2) + 1
        cursor = conn.execute(
            """
            INSERT INTO ledger_entries(
                book_section, entry_kind, entry_date, date_label, group_label, title,
                amount_value, amount_expr, sort_order, due_day, confirmed_at, spending_category
            )
            VALUES ('current', 'expense', ?, ?, NULL, ?, ?, ?, ?, NULL, NULL, NULL)
            """,
            (
                today.isoformat(),
                date_label,
                panel["title"],
                panel["amount_value"],
                panel["amount_expr"],
                sort_order,
            ),
        )
        conn.execute("DELETE FROM monthly_panels WHERE id = ?", (panel_id,))
        entry = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return {"entry": row_to_dict(entry)}


def planned_entry_payment_date(due_day: int | None) -> date:
    today = date.today()
    day = due_day if due_day and due_day > 0 else today.day
    return date(today.year, today.month, min(day, 28 if today.month == 2 else 30 if today.month in {4, 6, 9, 11} else 31))


def update_panel(panel_id: int, patch: MonthlyPanelPatch) -> dict[str, Any] | None:
    values = patch.model_dump(exclude_unset=True)
    if not values:
        with session() as conn:
            row = conn.execute("SELECT * FROM monthly_panels WHERE id = ?", (panel_id,)).fetchone()
        return row_to_dict(row) if row else None

    assignments = ", ".join(f"{column} = ?" for column in values)
    params = list(values.values()) + [panel_id]
    with session() as conn:
        conn.execute(
            f"UPDATE monthly_panels SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params,
        )
        row = conn.execute("SELECT * FROM monthly_panels WHERE id = ?", (panel_id,)).fetchone()
    return row_to_dict(row) if row else None


def delete_panel(panel_id: int) -> bool:
    with session() as conn:
        cursor = conn.execute("DELETE FROM monthly_panels WHERE id = ?", (panel_id,))
    return cursor.rowcount > 0


def create_entry(entry: LedgerEntryIn) -> dict[str, Any]:
    values = entry.model_dump()
    placeholders = ", ".join("?" for _ in ENTRY_COLUMNS)
    columns = ", ".join(ENTRY_COLUMNS)
    with session() as conn:
        cursor = conn.execute(
            f"INSERT INTO ledger_entries ({columns}) VALUES ({placeholders})",
            tuple(values[column] for column in ENTRY_COLUMNS),
        )
        row = conn.execute(
            "SELECT * FROM ledger_entries WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return row_to_dict(row)


def append_planned_entry(entry: PlannedEntryIn) -> dict[str, Any]:
    with session() as conn:
        max_planned = conn.execute(
            """
            SELECT MAX(sort_order) AS sort_order
            FROM ledger_entries
            WHERE book_section = 'current' AND entry_kind = 'planned'
            """
        ).fetchone()["sort_order"]
        if max_planned is None:
            min_current = conn.execute(
                """
                SELECT MIN(sort_order) AS sort_order
                FROM ledger_entries
                WHERE book_section = 'current'
                """
            ).fetchone()["sort_order"]
            sort_order = int(min_current or 3)
        else:
            sort_order = int(max_planned) + 1
            conn.execute(
                """
                UPDATE ledger_entries
                SET sort_order = sort_order + 1, updated_at = CURRENT_TIMESTAMP
                WHERE book_section = 'current' AND sort_order >= ?
                """,
                (sort_order,),
            )

        cursor = conn.execute(
            """
            INSERT INTO ledger_entries(
                book_section, entry_kind, entry_date, date_label, group_label, title,
                amount_value, amount_expr, sort_order, due_day, confirmed_at
            )
            VALUES ('current', 'planned', NULL, '카드 정기결제', '카드 정기결제', ?, ?, ?, ?, NULL)
            """,
            (entry.title, entry.amount_value, entry.amount_expr, sort_order, entry.due_day),
        )
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row)


def delete_planned_entry(entry_id: int) -> bool:
    with session() as conn:
        cursor = conn.execute(
            """
            DELETE FROM ledger_entries
            WHERE id = ? AND book_section = 'current' AND entry_kind = 'planned'
            """,
            (entry_id,),
        )
    return cursor.rowcount > 0


def reorder_current_entries(ordered_ids: list[int], entry_kind: str | None = None) -> list[dict[str, Any]]:
    with session() as conn:
        if entry_kind:
            rows = conn.execute(
                """
                SELECT id
                FROM ledger_entries
                WHERE book_section = 'current' AND entry_kind = ?
                ORDER BY sort_order, id
                """,
                (entry_kind,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id
                FROM ledger_entries
                WHERE book_section = 'current'
                ORDER BY sort_order, id
                """
            ).fetchall()

        existing_ids = [row["id"] for row in rows]
        existing_set = set(existing_ids)
        requested = [entry_id for entry_id in ordered_ids if entry_id in existing_set]
        tail = [entry_id for entry_id in existing_ids if entry_id not in requested]
        final_ids = requested + tail

        base_order = 3
        for offset, entry_id in enumerate(final_ids):
            conn.execute(
                "UPDATE ledger_entries SET sort_order = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (base_order + offset, entry_id),
            )

        if entry_kind:
            result = conn.execute(
                """
                SELECT *
                FROM ledger_entries
                WHERE book_section = 'current' AND entry_kind = ?
                ORDER BY sort_order, id
                """,
                (entry_kind,),
            ).fetchall()
        else:
            result = conn.execute(
                """
                SELECT *
                FROM ledger_entries
                WHERE book_section = 'current'
                ORDER BY sort_order, id
                """
            ).fetchall()
    return [row_to_dict(row) for row in result]


def update_entry(entry_id: int, patch: LedgerEntryPatch) -> dict[str, Any] | None:
    values = patch.model_dump(exclude_unset=True)
    if not values:
        with session() as conn:
            row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        return row_to_dict(row) if row else None

    assignments = ", ".join(f"{column} = ?" for column in values)
    params = list(values.values()) + [entry_id]
    with session() as conn:
        conn.execute(
            f"UPDATE ledger_entries SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params,
        )
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
    return row_to_dict(row) if row else None


def delete_entry(entry_id: int) -> bool:
    with session() as conn:
        cursor = conn.execute("DELETE FROM ledger_entries WHERE id = ?", (entry_id,))
    return cursor.rowcount > 0

from typing import Any

from app.db import session
from app.repositories.common import row_to_dict
from app.schemas import MonthlyPanelIn, MonthlyPanelPatch
from app.services.snapshot import create_pre_restore_backup


PANEL_COLUMNS = [
    "month",
    "panel_type",
    "title",
    "spent_on",
    "amount_value",
    "discount_amount",
    "amount_expr",
    "sort_order",
    "due_day",
    "confirmed_at",
    "discount_override",
]


def list_panels(month: str | None = None, include_confirmed_fixed: bool = False) -> list[dict[str, Any]]:
    filter_confirmed = "" if include_confirmed_fixed else " AND NOT (panel_type = 'fixed' AND confirmed_at IS NOT NULL)"
    with session() as conn:
        if month:
            rows = conn.execute(
                f"""
                SELECT *
                FROM monthly_panels
                WHERE (month = ? OR panel_type = 'fixed'){filter_confirmed}
                ORDER BY
                  CASE WHEN panel_type = 'fixed' THEN 0 ELSE 1 END,
                  CASE WHEN spent_on IS NULL THEN 1 ELSE 0 END,
                  spent_on,
                  sort_order,
                  id
                """,
                (month,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT *
                FROM monthly_panels
                WHERE 1 = 1{filter_confirmed}
                ORDER BY
                  CASE WHEN spent_on IS NULL THEN 1 ELSE 0 END,
                  spent_on,
                  sort_order,
                  id
                """
            ).fetchall()
    return [row_to_dict(row) for row in rows]


def create_panel(panel: MonthlyPanelIn) -> dict[str, Any]:
    _validate_panel_create(panel)
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


def _validate_panel_create(panel: MonthlyPanelIn) -> None:
    if not panel.title.strip():
        raise ValueError("세부내역을 입력해야 합니다.")
    if panel.amount_value is None:
        raise ValueError("금액을 입력해야 합니다.")
    if panel.panel_type == "frozen" and not str(panel.spent_on or "").strip():
        raise ValueError("동결 항목은 등록일자가 필요합니다.")


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


def delete_panels_by_type(month: str, panel_type: str) -> int:
    with session() as conn:
        cursor = conn.execute(
            "DELETE FROM monthly_panels WHERE month = ? AND panel_type = ?",
            (month, panel_type),
        )
    return cursor.rowcount


def complete_panels_by_type(month: str, panel_type: str) -> int:
    """청구 또는 가족카드의 현재 전달분을 일괄 처리하고 제거한다."""
    create_pre_restore_backup()
    with session() as conn:
        cursor = conn.execute(
            "DELETE FROM monthly_panels WHERE month = ? AND panel_type = ?",
            (month, panel_type),
        )
    return cursor.rowcount

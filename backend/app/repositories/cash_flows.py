from typing import Any

from app.db import session
from app.repositories.common import row_to_dict
from app.schemas import CashFlowIn


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
            INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order, is_primary_income)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                values["occurred_on"],
                values["title"],
                values["amount_value"],
                values["sort_order"],
                1 if values["is_primary_income"] and values["amount_value"] > 0 else 0,
            ),
        )
        row = conn.execute("SELECT * FROM cash_flows WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_dict(row)


def delete_cash_flow(flow_id: int) -> bool:
    with session() as conn:
        cursor = conn.execute("DELETE FROM cash_flows WHERE id = ?", (flow_id,))
    return cursor.rowcount > 0

from datetime import date
from typing import Any

from app.db import session
from app.repositories.common import row_to_dict
from app.schemas import CashFlowIn


def list_cash_flows(
    date_from: date | str | None = None,
    date_to: date | str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """현금흐름 전체 또는 지정한 기간의 최신 기록을 조회한다."""
    from_value = date_from.isoformat() if isinstance(date_from, date) else date_from
    to_value = date_to.isoformat() if isinstance(date_to, date) else date_to
    if from_value and to_value and from_value > to_value:
        raise ValueError("현금흐름 조회 시작일은 종료일보다 늦을 수 없습니다.")
    if limit is not None and limit <= 0:
        raise ValueError("현금흐름 조회 건수는 1 이상이어야 합니다.")

    conditions: list[str] = []
    params: list[Any] = []
    if from_value:
        conditions.append("occurred_on >= ?")
        params.append(from_value)
    if to_value:
        conditions.append("occurred_on <= ?")
        params.append(to_value)
    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    limit_clause = " LIMIT ?" if limit is not None else ""
    if limit is not None:
        params.append(limit)

    with session() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM cash_flows{where_clause}
            ORDER BY occurred_on DESC, sort_order DESC, id DESC{limit_clause}
            """,
            params,
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

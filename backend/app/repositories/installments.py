from math import ceil
from typing import Any

from app.db import session
from app.repositories.common import installment_to_dict
from app.schemas import InstallmentIn


def list_installments(active_only: bool = True) -> list[dict[str, Any]]:
    """활성 할부 항목을 월 납입액 계산값과 함께 반환한다."""
    filter_active = "WHERE is_active = 1 AND remaining_months > 0" if active_only else ""
    with session() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM installments
            {filter_active}
            ORDER BY sort_order, id
            """
        ).fetchall()
    return [installment_to_dict(row) for row in rows]


def create_installment(installment: InstallmentIn) -> dict[str, Any]:
    """수수료율을 금액으로 환산하고 원 단위 올림 월 납입액 기준의 할부 항목을 만든다."""
    values = installment.model_dump()
    months = max(1, int(values["months"]))
    remaining_months = values["remaining_months"] if values["remaining_months"] is not None else months
    remaining_months = max(1, min(months, int(remaining_months)))
    fee_rate = max(0.0, float(values["fee_rate"]))
    fee_amount = ceil(float(values["principal_amount"]) * fee_rate / 100)
    with session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO installments(
                title, principal_amount, fee_rate, fee_amount, months, remaining_months, start_month, sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values["title"],
                values["principal_amount"],
                fee_rate,
                fee_amount,
                months,
                remaining_months,
                values["start_month"],
                values["sort_order"],
            ),
        )
        row = conn.execute(
            """
            SELECT *
            FROM installments
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    return installment_to_dict(row)


def delete_installment(installment_id: int) -> bool:
    with session() as conn:
        cursor = conn.execute("DELETE FROM installments WHERE id = ?", (installment_id,))
    return cursor.rowcount > 0

from datetime import date, datetime, timezone
from typing import Any

from app.db import session
from app.repositories.common import row_to_dict
from app.repositories.panels import delete_panels_by_type
from app.services.clock import app_today
from app.services.snapshot import create_pre_restore_backup


def complete_panels_by_type(month: str, panel_type: str) -> int:
    """청구·가족카드 전달분을 지우기 전에 복원 가능한 서버 snapshot을 남긴다."""
    with session(transaction_mode="IMMEDIATE") as conn:
        create_pre_restore_backup(conn)
        return delete_panels_by_type(month, panel_type, conn)


def confirm_fixed_panel(
    panel_id: int,
    occurred_on: str,
    actual_amount: int | None = None,
) -> dict[str, dict[str, Any]] | None:
    """현금성 고정지출을 미지급 의무에서 실제 현금 유출로 원자적으로 전환한다."""
    try:
        confirmed_date = date.fromisoformat(occurred_on)
    except ValueError:
        raise ValueError("처리일은 YYYY-MM-DD 형식이어야 합니다.") from None

    today = app_today()
    if confirmed_date > today:
        raise ValueError("미래 날짜로 현금성 고정지출을 확인할 수 없습니다.")

    confirmed_month = confirmed_date.strftime("%Y-%m")
    with session(transaction_mode="IMMEDIATE") as conn:
        panel = conn.execute(
            "SELECT * FROM monthly_panels WHERE id = ?",
            (panel_id,),
        ).fetchone()
        if panel is None:
            return None
        if panel["panel_type"] != "fixed":
            raise ValueError("현금성 고정지출만 확인 처리할 수 있습니다.")
        if panel["confirmed_cash_flow_id"] is not None:
            raise ValueError("이미 확인 처리된 현금성 고정지출입니다.")
        if panel["amount_value"] is None:
            raise ValueError("확인 처리할 금액이 없습니다.")

        amount = int(panel["amount_value"] if actual_amount is None else actual_amount)
        if amount < 0:
            raise ValueError("현금성 고정지출 실제 출금액은 0원 이상이어야 합니다.")
        next_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS value FROM cash_flows",
        ).fetchone()["value"]
        cash_flow_id = conn.execute(
            """
            INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order, is_primary_income)
            VALUES (?, ?, ?, ?, 0)
            """,
            (confirmed_date.isoformat(), panel["title"], -amount, int(next_order)),
        ).lastrowid
        confirmed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        updated = conn.execute(
            """
            UPDATE monthly_panels
            SET spent_on = ?,
                confirmed_at = ?,
                confirmed_month = ?,
                confirmed_cash_flow_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND confirmed_cash_flow_id IS NULL
            """,
            (confirmed_date.isoformat(), confirmed_at, confirmed_month, cash_flow_id, panel_id),
        )
        if updated.rowcount != 1:
            raise ValueError("현금성 고정지출 확인 상태가 이미 변경되었습니다.")
        confirmed_panel = conn.execute(
            "SELECT * FROM monthly_panels WHERE id = ?",
            (panel_id,),
        ).fetchone()
        cash_flow = conn.execute(
            "SELECT * FROM cash_flows WHERE id = ?",
            (cash_flow_id,),
        ).fetchone()
    confirmed_panel_data = row_to_dict(confirmed_panel)
    confirmed_panel_data["confirmed_amount_value"] = amount
    return {
        "panel": confirmed_panel_data,
        "cash_flow": row_to_dict(cash_flow),
    }

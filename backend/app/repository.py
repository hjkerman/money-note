from math import ceil
from datetime import date
from typing import Any

from app.db import session
from app.schemas import (
    CashFlowIn,
    InstallmentIn,
    LedgerEntryIn,
    LedgerEntryPatch,
    MonthlyPanelIn,
    MonthlyPanelPatch,
    PlannedEntryIn,
)


ENTRY_COLUMNS = [
    "book_section",
    "entry_kind",
    "entry_date",
    "date_label",
    "group_label",
    "title",
    "usage_place",
    "usage_item",
    "amount_value",
    "amount_expr",
    "aux_amount_value",
    "aux_amount_expr",
    "extra_value",
    "sort_order",
    "due_day",
    "confirmed_at",
    "spending_category",
    "payment_key",
    "discount_checked",
]

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
    "discount_checked",
]


def row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def installment_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["monthly_amount"] = ceil((data["principal_amount"] + data["fee_amount"]) / data["months"])
    return data


def list_entries(section: str, today: date | None = None) -> list[dict[str, Any]]:
    current_month = (today or date.today()).strftime("%Y-%m")
    filter_confirmed_planned = " AND NOT (entry_kind = 'planned' AND confirmed_month = ?)" if section == "current" else ""
    params: tuple[Any, ...] = (section, current_month) if section == "current" else (section,)
    with session() as conn:
        rows = conn.execute(
            f"""
            SELECT *
            FROM ledger_entries
            WHERE book_section = ?{filter_confirmed_planned}
            ORDER BY
              CASE WHEN entry_kind = 'planned' THEN COALESCE(due_day, 99) ELSE 0 END,
              CASE WHEN entry_kind = 'planned' THEN NULL ELSE entry_date END,
              sort_order,
              id
            """,
            params,
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def list_panels(month: str | None = None, include_confirmed_fixed: bool = False) -> list[dict[str, Any]]:
    filter_confirmed = "" if include_confirmed_fixed else " AND NOT (panel_type = 'fixed' AND confirmed_at IS NOT NULL)"
    with session() as conn:
        if month:
            rows = conn.execute(
                f"""
                SELECT *
                FROM monthly_panels
                WHERE month = ?{filter_confirmed}
                ORDER BY
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


def list_labels() -> dict[str, str]:
    with session() as conn:
        rows = conn.execute("SELECT key, value FROM app_labels ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


def list_settings() -> dict[str, str]:
    with session() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


def upsert_label(key: str, value: str) -> dict[str, str]:
    with session() as conn:
        conn.execute(
            """
            INSERT INTO app_labels(key, value, updated_at)
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


def confirm_planned_entry(entry_id: int, today: date | None = None) -> dict[str, Any] | None:
    today = today or date.today()
    confirmed_month = today.strftime("%Y-%m")
    with session() as conn:
        planned = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        if planned is None:
            return None
        if planned["entry_kind"] != "planned":
            raise ValueError("only card recurring entries can be confirmed")
        if planned["confirmed_month"] == confirmed_month:
            raise ValueError("card recurring entry already confirmed")

        payment_date = planned_entry_payment_date(planned["due_day"], today)
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
                usage_place, usage_item, amount_value, amount_expr, sort_order, payment_key
            )
            VALUES ('current', 'expense', ?, ?, NULL, ?, ?, ?, ?, ?, ?, lower(hex(randomblob(16))))
            """,
            (
                payment_date.isoformat(),
                date_label,
                planned["title"],
                planned["usage_place"],
                planned["usage_item"],
                planned["amount_value"],
                planned["amount_expr"],
                sort_order,
            ),
        )
        conn.execute(
            """
            UPDATE ledger_entries
            SET confirmed_at = CURRENT_TIMESTAMP, confirmed_month = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (confirmed_month, entry_id),
        )
        entry = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (cursor.lastrowid,)).fetchone()
        updated_planned = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
    return {"planned": row_to_dict(updated_planned), "entry": row_to_dict(entry)}


def planned_entry_payment_date(due_day: int | None, today: date | None = None) -> date:
    today = today or date.today()
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


def delete_panels_by_type(month: str, panel_type: str) -> int:
    with session() as conn:
        cursor = conn.execute(
            "DELETE FROM monthly_panels WHERE month = ? AND panel_type = ?",
            (month, panel_type),
        )
    return cursor.rowcount


def complete_panels_by_type(month: str, panel_type: str) -> int:
    """청구 또는 타인정산의 현재 전달분을 일괄 처리하고 제거한다."""
    with session() as conn:
        cursor = conn.execute(
            "DELETE FROM monthly_panels WHERE month = ? AND panel_type = ?",
            (month, panel_type),
        )
    return cursor.rowcount


def create_entry(entry: LedgerEntryIn) -> dict[str, Any]:
    values = entry.model_dump()
    _validate_structured_entry(values)
    if values["entry_kind"] != "planned" and not values.get("payment_key"):
        values["payment_key"] = None
    placeholders = ", ".join("?" for _ in ENTRY_COLUMNS)
    columns = ", ".join(ENTRY_COLUMNS)
    with session() as conn:
        # 이미 마감한 달의 뒤늦은 지출은 다음 달 장부에 섞지 않고 전체 기록에 바로 보관한다.
        if values["book_section"] == "current" and values["entry_kind"] != "planned" and values.get("entry_date"):
            setting = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'last_closed_month'"
            ).fetchone()
            entry_month = str(values["entry_date"])[:7]
            if setting and entry_month <= str(setting["value"]):
                values["book_section"] = "archive"
                next_order = conn.execute(
                    "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM ledger_entries WHERE book_section = 'archive'"
                ).fetchone()["next_order"]
                values["sort_order"] = int(next_order)
        cursor = conn.execute(
            f"INSERT INTO ledger_entries ({columns}) VALUES ({placeholders})",
            tuple(values[column] for column in ENTRY_COLUMNS),
        )
        if values["entry_kind"] != "planned" and not values.get("payment_key"):
            conn.execute(
                """
                UPDATE ledger_entries
                SET payment_key = lower(hex(randomblob(16)))
                WHERE id = ?
                """,
                (cursor.lastrowid,),
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
                usage_place, usage_item, amount_value, amount_expr, sort_order, due_day, confirmed_at
            )
            VALUES ('current', 'planned', NULL, '카드 정기결제', '카드 정기결제', ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                entry.title,
                entry.usage_place,
                entry.usage_item,
                entry.amount_value,
                entry.amount_expr,
                sort_order,
                entry.due_day,
            ),
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

    with session() as conn:
        existing = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        if existing is None:
            return None
        merged = {**dict(existing), **values}
        _validate_structured_entry(merged)
        assignments = ", ".join(f"{column} = ?" for column in values)
        params = list(values.values()) + [entry_id]
        conn.execute(
            f"UPDATE ledger_entries SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params,
        )
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
    return row_to_dict(row) if row else None


def _validate_structured_entry(values: dict[str, Any]) -> None:
    """현재 일반 지출과 카드 정기결제의 필수 필드를 쓰기 직전에 검증한다."""
    if values.get("book_section") != "current":
        return
    kind = values.get("entry_kind")
    if kind == "expense":
        required = ("entry_date", "usage_place", "amount_value")
    elif kind == "planned":
        required = ("due_day", "usage_place", "amount_value")
    else:
        return
    missing = [
        field
        for field in required
        if values.get(field) is None or (isinstance(values.get(field), str) and not values[field].strip())
    ]
    if missing:
        raise ValueError(f"required fields missing: {', '.join(missing)}")
    if float(values["amount_value"]) < 0:
        raise ValueError("amount_value must be greater than or equal to zero")


def delete_entry(entry_id: int) -> bool:
    with session() as conn:
        cursor = conn.execute("DELETE FROM ledger_entries WHERE id = ?", (entry_id,))
    return cursor.rowcount > 0

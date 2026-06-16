from datetime import date, datetime
from typing import Any

from app.db import session
from app.repositories.common import row_to_dict
from app.schemas import LedgerEntryIn, LedgerEntryPatch, PlannedEntryIn
from app.services.clock import app_today


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
    "discount_override",
]


def list_entries(section: str, today: date | None = None) -> list[dict[str, Any]]:
    current_month = (today or app_today()).strftime("%Y-%m")
    filter_confirmed_planned = " AND NOT (entry_kind = 'planned' AND COALESCE(confirmed_month, '') = ?)" if section == "current" else ""
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


def list_confirmed_planned_entries(today: date | None = None) -> list[dict[str, Any]]:
    """이번 달에 이미 원장 편입한 카드 정기결제 원본을 조회한다."""
    confirmed_month = (today or app_today()).strftime("%Y-%m")
    with session() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM ledger_entries
            WHERE book_section = 'current'
              AND entry_kind = 'planned'
              AND confirmed_month = ?
            ORDER BY COALESCE(due_day, 99), sort_order, id
            """,
            (confirmed_month,),
        ).fetchall()
        confirmed_entries = []
        for row in rows:
            item = row_to_dict(row)
            expense = conn.execute(
                """
                SELECT entry_date
                FROM ledger_entries
                WHERE book_section = 'current'
                  AND entry_kind = 'expense'
                  AND entry_date LIKE ?
                  AND title = ?
                  AND COALESCE(usage_place, '') = COALESCE(?, '')
                  AND COALESCE(usage_item, '') = COALESCE(?, '')
                  AND COALESCE(amount_value, 0) = COALESCE(?, 0)
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    f"{confirmed_month}%",
                    row["title"],
                    row["usage_place"],
                    row["usage_item"],
                    row["amount_value"],
                ),
            ).fetchone()
            if expense and expense["entry_date"]:
                item["entry_date"] = expense["entry_date"]
            confirmed_entries.append(item)
    return confirmed_entries


def confirm_planned_entry(entry_id: int, today: date | None = None, entry_date: str | None = None) -> dict[str, Any] | None:
    today = today or app_today()
    confirmed_month = today.strftime("%Y-%m")
    with session() as conn:
        planned = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        if planned is None:
            return None
        if planned["entry_kind"] != "planned":
            raise ValueError("only card recurring entries can be confirmed")
        if planned["confirmed_month"] == confirmed_month:
            raise ValueError("card recurring entry already confirmed")

        payment_date = _parse_confirm_entry_date(entry_date, confirmed_month) if entry_date else planned_entry_payment_date(planned["due_day"], today)
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
            SET entry_date = ?, confirmed_at = CURRENT_TIMESTAMP, confirmed_month = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (payment_date.isoformat(), confirmed_month, entry_id),
        )
        entry = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (cursor.lastrowid,)).fetchone()
        updated_planned = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
    return {"planned": row_to_dict(updated_planned), "entry": row_to_dict(entry)}


def _parse_confirm_entry_date(value: str, expected_month: str) -> date:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("정기결제 등록 날짜 형식이 올바르지 않습니다.") from exc
    if parsed.strftime("%Y-%m") != expected_month:
        raise ValueError("정기결제 등록 날짜는 이번 달 날짜여야 합니다.")
    return parsed


def planned_entry_payment_date(due_day: int | None, today: date | None = None) -> date:
    today = today or app_today()
    day = due_day if due_day and due_day > 0 else today.day
    return date(today.year, today.month, min(day, 28 if today.month == 2 else 30 if today.month in {4, 6, 9, 11} else 31))


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


def delete_entry(entry_id: int) -> bool:
    with session() as conn:
        entry = conn.execute("SELECT payment_key FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        if entry is None:
            return False
        if entry["payment_key"]:
            _delete_card_payment_references(conn, str(entry["payment_key"]))
        cursor = conn.execute("DELETE FROM ledger_entries WHERE id = ?", (entry_id,))
    return cursor.rowcount > 0


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


def _delete_card_payment_references(conn: Any, payment_key: str) -> None:
    """장부 행 삭제 시 결제/할인 배분과 이월 상태를 함께 정리한다."""
    allocation_rows = conn.execute(
        """
        SELECT card_payment_allocations.id,
               card_payment_allocations.payment_event_id,
               card_payment_allocations.amount_value,
               card_payment_events.cash_flow_id
        FROM card_payment_allocations
        JOIN card_payment_events
          ON card_payment_events.id = card_payment_allocations.payment_event_id
        WHERE card_payment_allocations.entry_payment_key = ?
        """,
        (payment_key,),
    ).fetchall()
    conn.execute("DELETE FROM card_payment_deferrals WHERE entry_payment_key = ?", (payment_key,))
    conn.execute("DELETE FROM card_payment_allocations WHERE entry_payment_key = ?", (payment_key,))
    for allocation in allocation_rows:
        event_id = allocation["payment_event_id"]
        remaining = conn.execute(
            "SELECT COALESCE(SUM(amount_value), 0) AS total FROM card_payment_allocations WHERE payment_event_id = ?",
            (event_id,),
        ).fetchone()["total"]
        if float(remaining or 0) <= 0:
            conn.execute("DELETE FROM card_payment_events WHERE id = ?", (event_id,))
            if allocation["cash_flow_id"] is not None:
                conn.execute("DELETE FROM cash_flows WHERE id = ?", (allocation["cash_flow_id"],))
            continue
        conn.execute(
            "UPDATE card_payment_events SET total_amount = ? WHERE id = ?",
            (remaining, event_id),
        )
        if allocation["cash_flow_id"] is not None:
            conn.execute(
                "UPDATE cash_flows SET amount_value = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (-float(remaining), allocation["cash_flow_id"]),
            )

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Any

from app.db import session
from app.schemas import CardPaymentEventIn, LateCardEntryIn


def current_payment_status(today: date | None = None) -> dict[str, Any]:
    """이번 달 결제 대상인 직전월 사용내역과 결제 현황을 반환한다."""
    today = today or date.today()
    usage_month = _previous_month(today)
    due_date = date(today.year, today.month, min(14, monthrange(today.year, today.month)[1]))
    payment_month = today.strftime("%Y-%m")
    rows = _payment_rows_for_month(usage_month, payment_month)
    payable_rows = [row for row in rows if not row["is_deferred"]]
    recorded_remaining_total = sum(row["remaining_amount"] for row in payable_rows)
    is_after_due = today > due_date
    liquidity_reset_acknowledged = _setting_value("card_payment_liquidity_reset_ack_month") == payment_month
    return {
        "payment_month": payment_month,
        "usage_month": usage_month,
        "due_date": due_date.isoformat(),
        "immediate_allowed": today <= due_date,
        "needs_liquidity_reset": is_after_due and recorded_remaining_total > 0 and not liquidity_reset_acknowledged,
        "liquidity_reset_acknowledged": liquidity_reset_acknowledged,
        "original_total": sum(row["original_amount"] for row in payable_rows),
        "immediate_paid_total": sum(row["immediate_paid_amount"] for row in payable_rows),
        "discount_total": sum(row["discount_amount"] for row in payable_rows),
        "recorded_remaining_total": recorded_remaining_total,
        "effective_remaining_total": 0 if is_after_due else recorded_remaining_total,
        "primary_income_total": _primary_income_total(today.strftime("%Y-%m")),
        "rows": rows,
        "events": _events_for_payment_month(payment_month),
    }


def create_card_payment_event(payload: CardPaymentEventIn, today: date | None = None) -> dict[str, Any]:
    """일부 결제를 포함한 즉시결제 또는 수기 할인 배분을 기록한다."""
    today = today or date.today()
    event_date = datetime.strptime(payload.event_date, "%Y-%m-%d").date()
    due_date = date(event_date.year, event_date.month, min(14, monthrange(event_date.year, event_date.month)[1]))
    if event_date > due_date:
        raise ValueError("즉시결제와 할인액 처리는 매월 14일까지 가능합니다.")
    if not payload.allocations:
        raise ValueError("결제 또는 할인액을 배분할 항목이 없습니다.")

    allocations: list[tuple[str, float]] = []
    seen_keys: set[str] = set()
    with session() as conn:
        for allocation in payload.allocations:
            key = allocation.entry_payment_key
            amount = float(allocation.amount_value)
            if key in seen_keys:
                raise ValueError("같은 항목이 중복 선택되었습니다.")
            if amount <= 0:
                raise ValueError("처리 금액은 0원보다 커야 합니다.")
            seen_keys.add(key)
            row = conn.execute(
                """
                SELECT title, amount_value
                FROM ledger_entries
                WHERE payment_key = ? AND entry_kind != 'planned'
                """,
                (key,),
            ).fetchone()
            if row is None:
                raise ValueError("결제 대상 사용내역을 찾을 수 없습니다.")
            deferral = conn.execute(
                """
                SELECT target_payment_month
                FROM card_payment_deferrals
                WHERE entry_payment_key = ?
                """,
                (key,),
            ).fetchone()
            if deferral is not None and deferral["target_payment_month"] > event_date.strftime("%Y-%m"):
                raise ValueError("다음 달로 이월한 항목은 이번 달에 처리할 수 없습니다.")
            paid = conn.execute(
                """
                SELECT COALESCE(SUM(amount_value), 0) AS total
                FROM card_payment_allocations
                WHERE entry_payment_key = ?
                """,
                (key,),
            ).fetchone()["total"]
            remaining = max(0.0, float(row["amount_value"] or 0) - float(paid or 0))
            if amount > remaining + 0.0001:
                raise ValueError("처리 금액이 해당 항목의 남은 결제금액을 초과합니다.")
            if _is_toll(str(row["title"] or "")):
                if payload.event_type == "discount":
                    raise ValueError("통행료와 하이패스 항목에는 할인액을 반영할 수 없습니다.")
                if abs(amount - remaining) > 0.0001:
                    raise ValueError("통행료와 하이패스 항목은 남은 금액 전액만 결제할 수 있습니다.")
            allocations.append((key, amount))

        total = sum(amount for _, amount in allocations)
        cash_flow_id = None
        if payload.event_type == "immediate":
            next_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) + 1 AS value FROM cash_flows"
            ).fetchone()["value"]
            cash_cursor = conn.execute(
                """
                INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (payload.event_date, "카드 즉시결제", -total, next_order),
            )
            cash_flow_id = cash_cursor.lastrowid

        cursor = conn.execute(
            """
            INSERT INTO card_payment_events(event_date, event_type, total_amount, note, cash_flow_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.event_date, payload.event_type, total, payload.note.strip(), cash_flow_id),
        )
        for key, amount in allocations:
            conn.execute(
                """
                INSERT INTO card_payment_allocations(payment_event_id, entry_payment_key, amount_value)
                VALUES (?, ?, ?)
                """,
                (cursor.lastrowid, key, amount),
            )
        event = conn.execute(
            "SELECT * FROM card_payment_events WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(event)


def delete_card_payment_event(event_id: int) -> bool:
    """즉시결제/할인 기록과 연결된 현금흐름을 함께 취소한다."""
    with session() as conn:
        event = conn.execute(
            "SELECT cash_flow_id FROM card_payment_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        if event is None:
            return False
        conn.execute("DELETE FROM card_payment_events WHERE id = ?", (event_id,))
        if event["cash_flow_id"] is not None:
            conn.execute("DELETE FROM cash_flows WHERE id = ?", (event["cash_flow_id"],))
    return True


def acknowledge_liquidity_reset(today: date | None = None) -> dict[str, str]:
    """정규 결제 의제 후 사용자가 실제 계좌 유동성을 수동 보정했음을 기록한다."""
    payment_month = (today or date.today()).strftime("%Y-%m")
    with session() as conn:
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES ('card_payment_liquidity_reset_ack_month', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (payment_month,),
        )
    return {"payment_month": payment_month}


def create_late_card_entry(payload: LateCardEntryIn, today: date | None = None) -> dict[str, Any]:
    """카드사 매입 지연으로 뒤늦게 확인된 직전월 사용내역을 archive에 추가한다."""
    today = today or date.today()
    usage_month = _previous_month(today)
    try:
        entry_date = datetime.strptime(payload.entry_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("전월 보정 날짜 형식이 올바르지 않습니다.") from exc
    if entry_date.strftime("%Y-%m") != usage_month:
        raise ValueError("전월 매입 지연 보정은 직전월 날짜만 사용할 수 있습니다.")
    if payload.amount_value <= 0:
        raise ValueError("전월 보정 금액은 0원보다 커야 합니다.")
    usage_place = (payload.usage_place or "").strip()
    usage_item = (payload.usage_item or "").strip()
    title = _usage_title(usage_place, usage_item)
    if not title:
        raise ValueError("사용처 또는 사용항목을 입력하세요.")
    with session() as conn:
        sort_order = conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0) + 1 AS value
            FROM ledger_entries
            WHERE book_section = 'archive'
            """
        ).fetchone()["value"]
        cursor = conn.execute(
            """
            INSERT INTO ledger_entries(
                book_section, entry_kind, entry_date, date_label, group_label, title,
                usage_place, usage_item, amount_value, sort_order, payment_key
            )
            VALUES (
                'archive', 'late_expense', ?, ?, NULL, ?, ?, ?, ?, ?, lower(hex(randomblob(16)))
            )
            """,
            (
                entry_date.isoformat(),
                f"{entry_date:%Y.%m.%d}.",
                title,
                usage_place or None,
                usage_item or None,
                float(payload.amount_value),
                sort_order,
            ),
        )
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def defer_toll_payment(entry_payment_key: str, today: date | None = None) -> dict[str, str]:
    """통행료/하이패스 미처리액을 다음 결제월로 한 번 이월한다."""
    today = today or date.today()
    due_date = date(today.year, today.month, min(14, monthrange(today.year, today.month)[1]))
    if today > due_date:
        raise ValueError("통행료 이월 선택은 매월 14일까지 가능합니다.")
    payment_month = today.strftime("%Y-%m")
    usage_month = _previous_month(today)
    target_payment_month = _next_month(today)
    with session() as conn:
        row = conn.execute(
            """
            SELECT book_section, title, entry_date, date_label, group_label, amount_value, sort_order
            FROM ledger_entries
            WHERE payment_key = ? AND entry_kind != 'planned'
            """,
            (entry_payment_key,),
        ).fetchone()
        if row is None or not str(row["entry_date"] or "").startswith(usage_month):
            raise ValueError("이번 달 이월 대상으로 선택할 수 없는 사용내역입니다.")
        if not _is_toll(str(row["title"] or "")):
            raise ValueError("통행료 또는 하이패스 항목만 이월할 수 있습니다.")
        allocated = conn.execute(
            """
            SELECT COALESCE(SUM(amount_value), 0) AS total
            FROM card_payment_allocations
            WHERE entry_payment_key = ?
            """,
            (entry_payment_key,),
        ).fetchone()["total"]
        if float(allocated or 0) > 0:
            raise ValueError("이미 일부결제 또는 할인이 반영된 항목은 이월할 수 없습니다.")
        conn.execute(
            """
            INSERT INTO card_payment_deferrals(
                entry_payment_key, from_payment_month, target_payment_month,
                original_book_section, original_entry_date, original_date_label,
                original_group_label, original_title, original_sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entry_payment_key) DO UPDATE SET
                from_payment_month = excluded.from_payment_month,
                target_payment_month = excluded.target_payment_month,
                original_book_section = excluded.original_book_section,
                original_entry_date = excluded.original_entry_date,
                original_date_label = excluded.original_date_label,
                original_group_label = excluded.original_group_label,
                original_title = excluded.original_title,
                original_sort_order = excluded.original_sort_order,
                created_at = CURRENT_TIMESTAMP
            """,
            (
                entry_payment_key,
                payment_month,
                target_payment_month,
                row["book_section"],
                row["entry_date"],
                row["date_label"],
                row["group_label"],
                row["title"],
                row["sort_order"],
            ),
        )
        first_order = conn.execute(
            """
            SELECT COALESCE(MIN(sort_order), 1) - 1 AS value
            FROM ledger_entries
            WHERE book_section = 'current'
            """
        ).fetchone()["value"]
        conn.execute(
            """
            UPDATE ledger_entries
            SET book_section = 'current',
                entry_date = ?,
                date_label = '',
                group_label = '',
                title = ?,
                sort_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE payment_key = ?
            """,
            (
                f"{payment_month}-01",
                _carried_title(str(row["title"] or "")),
                first_order,
                entry_payment_key,
            ),
        )
    return {
        "entry_payment_key": entry_payment_key,
        "from_payment_month": payment_month,
        "target_payment_month": target_payment_month,
    }


def cancel_toll_deferral(entry_payment_key: str, today: date | None = None) -> bool:
    """현재 결제월에서 방금 이월한 통행료를 이번 달 처리 대상으로 되돌린다."""
    today = today or date.today()
    due_date = date(today.year, today.month, min(14, monthrange(today.year, today.month)[1]))
    if today > due_date:
        raise ValueError("통행료 이월은 매월 14일까지만 취소할 수 있습니다.")
    payment_month = today.strftime("%Y-%m")
    with session() as conn:
        deferral = conn.execute(
            """
            SELECT *
            FROM card_payment_deferrals
            WHERE entry_payment_key = ? AND from_payment_month = ?
            """,
            (entry_payment_key, payment_month),
        ).fetchone()
        if deferral is None:
            return False
        conn.execute(
            """
            UPDATE ledger_entries
            SET book_section = ?,
                entry_date = ?,
                date_label = ?,
                group_label = ?,
                title = ?,
                sort_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE payment_key = ?
            """,
            (
                deferral["original_book_section"],
                deferral["original_entry_date"],
                deferral["original_date_label"],
                deferral["original_group_label"],
                deferral["original_title"],
                deferral["original_sort_order"],
                entry_payment_key,
            ),
        )
        conn.execute(
            "DELETE FROM card_payment_deferrals WHERE entry_payment_key = ?",
            (entry_payment_key,),
        )
    return True


def _payment_rows_for_month(usage_month: str, payment_month: str) -> list[dict[str, Any]]:
    with session() as conn:
        rows = conn.execute(
            """
            SELECT ledger_entries.*,
                   card_payment_deferrals.from_payment_month AS deferred_from_payment_month,
                   card_payment_deferrals.target_payment_month AS deferred_target_payment_month,
                   COALESCE(SUM(CASE WHEN card_payment_events.event_type = 'immediate'
                                     THEN card_payment_allocations.amount_value ELSE 0 END), 0) AS immediate_paid_amount,
                   COALESCE(SUM(CASE WHEN card_payment_events.event_type = 'discount'
                                     THEN card_payment_allocations.amount_value ELSE 0 END), 0) AS discount_amount
            FROM ledger_entries
            LEFT JOIN card_payment_allocations
              ON card_payment_allocations.entry_payment_key = ledger_entries.payment_key
            LEFT JOIN card_payment_events
              ON card_payment_events.id = card_payment_allocations.payment_event_id
            LEFT JOIN card_payment_deferrals
              ON card_payment_deferrals.entry_payment_key = ledger_entries.payment_key
            WHERE ledger_entries.entry_kind != 'planned'
              AND (
                    ledger_entries.entry_date LIKE ?
                    OR card_payment_deferrals.from_payment_month = ?
                    OR card_payment_deferrals.target_payment_month = ?
                  )
              AND COALESCE(ledger_entries.amount_value, 0) > 0
            GROUP BY ledger_entries.id
            ORDER BY
              CASE WHEN card_payment_deferrals.target_payment_month = ? THEN 0
                   WHEN card_payment_deferrals.from_payment_month = ? THEN 2
                   ELSE 1 END,
              ledger_entries.entry_date,
              ledger_entries.sort_order,
              ledger_entries.id
            """,
            (f"{usage_month}%", payment_month, payment_month, payment_month, payment_month),
        ).fetchall()
    result = []
    for row in rows:
        data = dict(row)
        original = float(data.get("amount_value") or 0)
        immediate = float(data.pop("immediate_paid_amount") or 0)
        discount = float(data.pop("discount_amount") or 0)
        deferred_from = data.pop("deferred_from_payment_month", None)
        deferred_target = data.pop("deferred_target_payment_month", None)
        data.update(
            {
                "original_amount": original,
                "immediate_paid_amount": immediate,
                "discount_amount": discount,
                "remaining_amount": max(0.0, original - immediate - discount),
                "is_transport": "교통" in str(data.get("title") or ""),
                "is_toll": _is_toll(str(data.get("title") or "")),
                "is_deferred": deferred_from == payment_month and deferred_target > payment_month,
                "is_carried_over": deferred_target == payment_month,
            }
        )
        result.append(data)
    return result


def _events_for_payment_month(payment_month: str) -> list[dict[str, Any]]:
    with session() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM card_payment_events
            WHERE event_date LIKE ?
            ORDER BY event_date DESC, id DESC
            """,
            (f"{payment_month}%",),
        ).fetchall()
    return [dict(row) for row in rows]


def _previous_month(value: date) -> str:
    if value.month == 1:
        return f"{value.year - 1}-12"
    return f"{value.year}-{value.month - 1:02d}"


def _next_month(value: date) -> str:
    if value.month == 12:
        return f"{value.year + 1}-01"
    return f"{value.year}-{value.month + 1:02d}"


def _is_toll(title: str) -> bool:
    lowered = title.lower()
    return "통행료" in lowered or "하이패스" in lowered


def _carried_title(title: str) -> str:
    return title if title.startswith("[이월]") else f"[이월] {title}"


def _usage_title(usage_place: str, usage_item: str) -> str:
    if usage_place and usage_item:
        return f"[{usage_place}] {usage_item}"
    if usage_place:
        return f"[{usage_place}]"
    return usage_item


def _primary_income_total(payment_month: str) -> float:
    with session() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(amount_value), 0) AS total
            FROM cash_flows
            WHERE occurred_on LIKE ?
              AND is_primary_income = 1
              AND amount_value > 0
            """,
            (f"{payment_month}%",),
        ).fetchone()
    return float(row["total"])


def _setting_value(key: str) -> str:
    with session() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else ""

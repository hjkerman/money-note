from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
from typing import Any
from app.money import exact_money, query_money_sum, allocation_totals, validate_money_payload

from app.db import borrowed_or_new_session
from app.repositories.common import new_payment_key
from app.schemas import CardPaymentEventIn, LateCardEntryIn
from app.services.card_charge import (
    DiscountCard,
    card_charge_projection_policy,
    default_discount_policy,
    evaluate_stored_charge,
    normalize_discount_policy,
    utility_default_discount_excluded,
)
from app.services.card_payment_reads import (
    CardPaymentContext as CardPaymentContext,
    _active_payment_context,
    _events_for_batch,
    _group_toll_rows,
    _manual_entry_discount,
    _next_month_from_month,
    _payment_rows_for_batch,
    _primary_income_total,
    _setting_value,
    _settings_values,
)
from app.services.clock import app_today
from app.services.financial_relationships import validate_runtime_card_payment_ownership




def current_payment_status(today: date | None = None) -> dict[str, Any]:
    """최근 월마감이 생성한 카드 결제 작업함과 결제 현황을 반환한다."""
    today = today or app_today()
    context = _active_payment_context(today)
    item_rows = _payment_rows_for_batch(context)
    payable_rows = [row for row in item_rows if not row["is_deferred"]]
    rows = _group_toll_rows(item_rows)
    recorded_remaining_total = _remaining_total(payable_rows)
    is_after_due = today > context.due_date
    liquidity_reset_acknowledged = _setting_value("card_payment_liquidity_reset_ack_month") == context.payment_month
    result = {
        "calendar_date": today.isoformat(),
        "payment_month": context.payment_month,
        "usage_month": context.usage_month,
        "due_date": context.due_date.isoformat(),
        "immediate_allowed": context.batch_id is not None and today <= context.due_date,
        "needs_liquidity_reset": is_after_due and recorded_remaining_total > 0 and not liquidity_reset_acknowledged,
        "liquidity_reset_acknowledged": liquidity_reset_acknowledged,
        "original_total": sum(row["original_amount"] for row in payable_rows),
        "immediate_paid_total": sum(row["immediate_paid_amount"] for row in payable_rows),
        "discount_total": sum(row["discount_amount"] for row in payable_rows),
        "recorded_remaining_total": recorded_remaining_total,
        "effective_remaining_total": recorded_remaining_total,
        "primary_income_total": _primary_income_total(context.payment_month),
        "discount_policy": discount_month_status(context.usage_month, "owner")["policy"],
        "rows": rows,
        "events": _events_for_batch(context.batch_id),
    }
    validate_money_payload(result)
    return result


def active_card_payment_unpaid_total(today: date | None = None, conn: Any | None = None) -> int:
    """현재 원장으로 이월되지 않은 활성 결제 batch의 미지급 채무다."""
    context = _active_payment_context(today or app_today(), conn)
    if _setting_value("card_payment_liquidity_reset_ack_month", conn) == context.payment_month:
        return 0
    payable_rows = [row for row in _payment_rows_for_batch(context, conn) if not row["is_deferred"]]
    return _remaining_total(payable_rows)


def closed_month_payment_batch_id(conn: Any, entry_month: str, today: date) -> int:
    context = _active_payment_context(today, conn)
    if context.batch_id is None or context.usage_month != entry_month:
        raise ValueError("마감한 달의 지출을 현재 결제 작업함에 안전하게 연결할 수 없습니다.")
    if today > context.due_date or _setting_value("card_payment_liquidity_reset_ack_month", conn) == context.payment_month:
        raise ValueError("이미 정산된 결제월에는 과거 카드 지출을 추가할 수 없습니다.")
    rows = [row for row in _payment_rows_for_batch(context, conn) if not row["is_deferred"]]
    if rows and _remaining_total(rows) == 0:
        raise ValueError("완납된 결제 작업함에는 과거 카드 지출을 추가할 수 없습니다.")
    return context.batch_id


def _remaining_total(rows: list[dict[str, Any]]) -> int:
    return exact_money(sum(exact_money(row.get("remaining_amount") or 0) for row in rows), 'card remaining total')


def create_month_close_card_payment_batch(conn: Any, usage_month: str) -> int:
    """월마감 직후 해당 사용월의 카드 원장을 결제 작업함으로 만든다."""
    _validate_month(usage_month)
    validate_runtime_card_payment_ownership(conn)
    payment_month = _next_month_from_month(usage_month)

    carryover_rows = conn.execute(
        """
        SELECT entry_payment_key
        FROM card_payment_deferrals
        WHERE target_payment_month = ?
        """,
        (payment_month,),
    ).fetchall()
    carryover_keys = {str(row["entry_payment_key"]) for row in carryover_rows}

    conn.execute(
        """
        DELETE FROM card_payment_allocations
        WHERE payment_event_id IN (
            SELECT id FROM card_payment_events WHERE batch_id IS NOT NULL
        )
        """
    )
    conn.execute("DELETE FROM card_payment_events WHERE batch_id IS NOT NULL")
    conn.execute("DELETE FROM card_payment_batch_items")
    conn.execute("DELETE FROM card_payment_batches")
    if carryover_keys:
        placeholders = ",".join("?" for _ in carryover_keys)
        conn.execute(
            f"""
            DELETE FROM card_payment_deferrals
            WHERE target_payment_month != ?
              AND entry_payment_key NOT IN ({placeholders})
            """,
            (payment_month, *tuple(carryover_keys)),
        )
    else:
        conn.execute("DELETE FROM card_payment_deferrals WHERE target_payment_month != ?", (payment_month,))

    cursor = conn.execute(
        """
        INSERT INTO card_payment_batches(usage_month, source, status)
        VALUES (?, 'month_close', 'active')
        """,
        (usage_month,),
    )
    batch_id = int(cursor.lastrowid)
    rows = conn.execute(
        """
        SELECT ledger_entries.id, ledger_entries.payment_key
        FROM ledger_entries
        LEFT JOIN card_payment_deferrals
          ON card_payment_deferrals.entry_payment_key = ledger_entries.payment_key
        WHERE ledger_entries.entry_kind != 'planned'
          AND ledger_entries.payment_key IS NOT NULL
          AND COALESCE(ledger_entries.amount_value, 0) > 0
          AND (
                ledger_entries.entry_date LIKE ?
                OR card_payment_deferrals.target_payment_month = ?
              )
        ORDER BY
          CASE WHEN card_payment_deferrals.target_payment_month = ? THEN 0 ELSE 1 END,
          ledger_entries.entry_date,
          ledger_entries.sort_order,
          ledger_entries.id
        """,
        (f"{usage_month}%", payment_month, payment_month),
    ).fetchall()
    for row in rows:
        _add_card_payment_batch_item(conn, batch_id, int(row["id"]), str(row["payment_key"]))
    validate_runtime_card_payment_ownership(conn)
    return batch_id


def discount_month_status(month: str, scope: str = "owner", *, conn: Any | None = None) -> dict[str, Any]:
    """사용월의 할인 혜택 정책과 사용내역별 누적 할인액을 반환한다."""
    _validate_month(month)
    _validate_discount_scope(scope)
    with borrowed_or_new_session(conn) as conn:
        settings = _settings_values(conn)
        policy = _discount_policy_value(conn, month, scope)
        rows = [] if scope == "family" else conn.execute(
            """
            SELECT ledger_entries.payment_key,
                   ledger_entries.amount_value,
                   ledger_entries.title,
                   ledger_entries.usage_place,
                   ledger_entries.spending_category,
                   ledger_entries.discount_override,
                   ledger_entries.aux_amount_value
            FROM ledger_entries
            WHERE ledger_entries.entry_date LIKE ?
              AND ledger_entries.payment_key IS NOT NULL
              AND ledger_entries.entry_kind != 'planned'
            """,
            (f"{month}%",),
        ).fetchall()
        allocated_discounts = allocation_totals(conn, 'discount')
        rows = [{**dict(row), 'override_discount_amount': allocated_discounts.get(row['payment_key'], 0)} for row in rows]
    discounts = {
        row["payment_key"]: evaluate_stored_charge(
            row["amount_value"],
            _manual_entry_discount(row),
            bool(row["discount_override"] or row["override_discount_amount"] or row["aux_amount_value"]),
            policy,
            month,
            row["title"],
            DiscountCard.OWNER,
            merchant=row["usage_place"],
            spending_category=row["spending_category"],
            settings=settings,
        ).effective_discount_amount
        for row in rows
        if row["payment_key"]
    }
    return {
        "month": month,
        "scope": scope,
        "policy": policy,
        "projection_policy": card_charge_projection_policy(
            DiscountCard.OWNER if scope == "owner" else DiscountCard.FAMILY,
            month,
        ),
        "discounts": discounts,
        "discount_total": exact_money(sum(discounts.values()), 'discount_total'),
    }


def set_discount_month_policy(month: str, policy: str, scope: str = "owner", *, conn: Any | None = None) -> dict[str, Any]:
    """사용월 전체 카드 지출에 적용할 할인 혜택 여부를 저장한다."""
    _validate_month(month)
    _validate_discount_scope(scope)
    if policy not in {"enabled", "disabled"}:
        raise ValueError("알 수 없는 할인 혜택 설정입니다.")
    with borrowed_or_new_session(conn) as conn:
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (f"card_discount_policy:{scope}:{month}", policy),
        )
        return discount_month_status(month, scope, conn=conn)


def create_card_payment_event(payload: CardPaymentEventIn, today: date | None = None, *, conn: Any | None = None) -> dict[str, Any]:
    """일부 결제를 포함한 즉시결제 또는 호환용 할인 배분을 기록한다."""
    today = today or app_today()
    event_date = payload.event_date
    request_fingerprint = _card_payment_request_fingerprint(payload)
    allocations: list[tuple[str, int]] = []
    seen_keys: set[str] = set()
    with borrowed_or_new_session(conn, transaction_mode="IMMEDIATE") as conn:
        validate_runtime_card_payment_ownership(conn)
        existing = conn.execute(
            "SELECT * FROM card_payment_events WHERE idempotency_key = ?",
            (payload.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["request_fingerprint"] != request_fingerprint:
                raise ValueError("같은 idempotency key에 서로 다른 결제 요청을 사용할 수 없습니다.")
            return dict(existing)

        if event_date > today:
            raise ValueError("실제 카드 결제일은 서버 기준 오늘 이후일 수 없습니다.")

        context = _active_payment_context(today, conn)
        if context.batch_id is None:
            raise ValueError("월마감 후 생성된 결제 작업함이 없습니다.")
        usage_start = datetime.strptime(f"{context.usage_month}-01", "%Y-%m-%d").date()
        if event_date < usage_start or event_date > context.due_date:
            raise ValueError("결제 처리는 월마감 사용월부터 익월 14일까지 가능합니다.")
        if payload.event_type == "immediate" and event_date > context.due_date:
            raise ValueError("즉시결제는 매월 14일까지 가능합니다.")
        if not payload.allocations:
            raise ValueError("결제 또는 할인액을 배분할 항목이 없습니다.")

        settings = _settings_values(conn)
        for allocation in payload.allocations:
            key = allocation.entry_payment_key
            amount = int(allocation.amount_value)
            if key in seen_keys:
                raise ValueError("같은 항목이 중복 선택되었습니다.")
            if payload.event_type == "immediate" and amount <= 0:
                raise ValueError("처리 금액은 0원보다 커야 합니다.")
            if payload.event_type == "discount" and amount < 0:
                raise ValueError("할인액은 0원 이상이어야 합니다.")
            seen_keys.add(key)
            row = conn.execute(
                """
                SELECT title, usage_place, spending_category, amount_value,
                       entry_date, discount_override, aux_amount_value
                FROM ledger_entries
                JOIN card_payment_batch_items
                  ON card_payment_batch_items.entry_id = ledger_entries.id
                WHERE payment_key = ? AND entry_kind != 'planned'
                  AND card_payment_batch_items.batch_id = ?
                """,
                (key, context.batch_id),
            ).fetchone()
            if row is None:
                raise ValueError("현재 결제 작업함의 사용내역을 찾을 수 없습니다.")
            usage_month = str(row["entry_date"] or "")[:7]
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
            paid = query_money_sum(conn,
                """
                SELECT amount_value
                FROM card_payment_allocations
                JOIN card_payment_events
                  ON card_payment_events.id = card_payment_allocations.payment_event_id
                WHERE entry_payment_key = ?
                  AND card_payment_events.event_type = 'immediate'
                  AND card_payment_events.batch_id = ?
                """,
                (key, context.batch_id),
            )
            override_discount = query_money_sum(conn,
                """
                SELECT amount_value
                FROM card_payment_allocations
                JOIN card_payment_events
                  ON card_payment_events.id = card_payment_allocations.payment_event_id
                WHERE entry_payment_key = ?
                  AND card_payment_events.event_type = 'discount'
                  AND card_payment_events.batch_id = ?
                """,
                (key, context.batch_id),
            )
            if payload.event_type == "discount":
                remaining = max(0, exact_money(row["amount_value"] or 0) - paid)
            else:
                current_discount = evaluate_stored_charge(
                    row["amount_value"],
                    _manual_entry_discount({**dict(row), "override_discount_amount": override_discount}),
                    bool(row["discount_override"] or override_discount or row["aux_amount_value"]),
                    _discount_policy_value(conn, usage_month, "owner") if usage_month else "enabled",
                    usage_month,
                    row["title"],
                    DiscountCard.OWNER,
                    merchant=row["usage_place"],
                    spending_category=row["spending_category"],
                    settings=settings,
                ).effective_discount_amount
                remaining = max(0, exact_money(row["amount_value"] or 0) - paid - current_discount)
            if amount > remaining:
                raise ValueError("처리 금액이 해당 항목의 남은 결제금액을 초과합니다.")
            allocations.append((key, amount))

        total = exact_money(sum(amount for _, amount in allocations), 'card payment total')
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
                (event_date.isoformat(), "카드 즉시결제", -int(total), next_order),
            )
            cash_flow_id = cash_cursor.lastrowid

        cursor = conn.execute(
            """
            INSERT INTO card_payment_events(
                batch_id, event_date, event_type, total_amount, note, cash_flow_id,
                idempotency_key, request_fingerprint
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                context.batch_id,
                event_date.isoformat(),
                payload.event_type,
                int(total),
                payload.note.strip(),
                cash_flow_id,
                payload.idempotency_key,
                request_fingerprint,
            ),
        )
        for key, amount in allocations:
            conn.execute(
                """
                INSERT INTO card_payment_allocations(payment_event_id, entry_payment_key, amount_value)
                VALUES (?, ?, ?)
                """,
                (cursor.lastrowid, key, amount),
            )
            if payload.event_type == "discount":
                conn.execute(
                    """
                    UPDATE ledger_entries
                    SET discount_override = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE payment_key = ?
                    """,
                    (key,),
                )
        event = conn.execute(
            "SELECT * FROM card_payment_events WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        validate_runtime_card_payment_ownership(conn)
        return dict(event)


def _card_payment_request_fingerprint(payload: CardPaymentEventIn) -> str:
    normalized = {
        "event_date": payload.event_date.isoformat(),
        "event_type": payload.event_type,
        "note": payload.note.strip(),
        "allocations": sorted(
            (
                {
                    "entry_payment_key": allocation.entry_payment_key,
                    "amount_value": int(allocation.amount_value),
                }
                for allocation in payload.allocations
            ),
            key=lambda item: (item["entry_payment_key"], item["amount_value"]),
        ),
    }
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def set_entry_discount(
    entry_payment_key: str,
    amount: int,
    event_date: str | None = None,
    conn: Any | None = None,
) -> dict[str, Any]:
    """당월 사용내역의 개별 할인 예외를 저장한다."""
    if amount < 0:
        raise ValueError("할인액은 0원 이상이어야 합니다.")
    event_date = event_date or app_today().isoformat()
    with borrowed_or_new_session(conn) as conn:
        validate_runtime_card_payment_ownership(conn)
        row = conn.execute(
            """
            SELECT id, title, amount_value, entry_date
            FROM ledger_entries
            WHERE payment_key = ? AND entry_kind != 'planned'
            """,
            (entry_payment_key,),
        ).fetchone()
        if row is None:
            raise ValueError("할인 대상 사용내역을 찾을 수 없습니다.")
        if amount > exact_money(row["amount_value"] or 0):
            raise ValueError("할인액은 원래 금액을 초과할 수 없습니다.")
        _delete_entry_discount_events(conn, entry_payment_key)
        conn.execute(
            """
            UPDATE ledger_entries
            SET aux_amount_value = ?, discount_override = 1, updated_at = CURRENT_TIMESTAMP
            WHERE payment_key = ?
            """,
            (int(amount), entry_payment_key),
        )
        updated = conn.execute("SELECT * FROM ledger_entries WHERE payment_key = ?", (entry_payment_key,)).fetchone()
        return dict(updated)


def clear_entry_discount(entry_payment_key: str, *, conn: Any | None = None) -> bool:
    """당월 사용내역에 적용한 할인 확인과 할인 이벤트를 취소한다."""
    with borrowed_or_new_session(conn) as conn:
        validate_runtime_card_payment_ownership(conn)
        row = conn.execute("SELECT id FROM ledger_entries WHERE payment_key = ?", (entry_payment_key,)).fetchone()
        if row is None:
            return False
        _delete_entry_discount_events(conn, entry_payment_key)
        conn.execute(
            """
            UPDATE ledger_entries
            SET aux_amount_value = NULL, discount_override = 0, updated_at = CURRENT_TIMESTAMP
            WHERE payment_key = ?
            """,
            (entry_payment_key,),
        )
    return True


def delete_card_payment_event(event_id: int, *, conn: Any | None = None) -> bool:
    """즉시결제/할인 기록과 연결된 현금흐름을 함께 취소한다."""
    with borrowed_or_new_session(conn) as conn:
        validate_runtime_card_payment_ownership(conn)
        event = conn.execute(
            "SELECT cash_flow_id FROM card_payment_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        if event is None:
            return False
        conn.execute("DELETE FROM card_payment_events WHERE id = ?", (event_id,))
        if event["cash_flow_id"] is not None:
            conn.execute("DELETE FROM cash_flows WHERE id = ?", (event["cash_flow_id"],))
        validate_runtime_card_payment_ownership(conn)
    return True


def acknowledge_liquidity_reset(today: date | None = None, *, conn: Any | None = None) -> dict[str, str]:
    """정규 결제 의제 후 사용자가 실제 계좌 유동성을 수동 보정했음을 기록한다."""
    with borrowed_or_new_session(conn) as conn:
        payment_month = _active_payment_context(today or app_today(), conn).payment_month
        conn.execute(
            """
            INSERT INTO app_settings(key, value, updated_at)
            VALUES ('card_payment_liquidity_reset_ack_month', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (payment_month,),
        )
    return {"payment_month": payment_month}


def create_late_card_entry(payload: LateCardEntryIn, today: date | None = None, *, conn: Any | None = None) -> dict[str, Any]:
    """카드사 매입 지연으로 확인된 결제 작업함 사용월 내역을 archive와 batch에 추가한다."""
    today = today or app_today()
    entry_date = payload.entry_date
    if payload.amount_value <= 0:
        raise ValueError("전월 보정 금액은 0원보다 커야 합니다.")
    usage_place = (payload.usage_place or "").strip()
    usage_item = (payload.usage_item or "").strip()
    title = _usage_title(usage_place, usage_item)
    if not title:
        raise ValueError("사용처 또는 세부내역을 입력하세요.")
    with borrowed_or_new_session(conn, transaction_mode="IMMEDIATE") as conn:
        context = _active_payment_context(today, conn)
        if context.batch_id is None:
            raise ValueError("월마감 후 생성된 결제 작업함이 없습니다.")
        if entry_date.strftime("%Y-%m") != context.usage_month:
            raise ValueError("전월 매입 지연 보정은 현재 결제 작업함의 사용월 날짜만 사용할 수 있습니다.")
        closed_month_payment_batch_id(conn, context.usage_month, today)
        sort_order = conn.execute(
            """
            SELECT COALESCE(MAX(sort_order), 0) + 1 AS value
            FROM ledger_entries
            WHERE book_section = 'archive'
            """
        ).fetchone()["value"]
        payment_key = new_payment_key(conn)
        cursor = conn.execute(
            """
            INSERT INTO ledger_entries(
                book_section, entry_kind, entry_date, date_label, group_label, title,
                usage_place, usage_item, amount_value, sort_order, payment_key, discount_override
            )
            VALUES (
                'archive', 'late_expense', ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                entry_date.isoformat(),
                f"{entry_date:%Y.%m.%d}.",
                title,
                usage_place or None,
                usage_item or None,
                int(payload.amount_value),
                sort_order,
                payment_key,
                int(utility_default_discount_excluded(usage_place, usage_item)),
            ),
        )
        payment_key_row = conn.execute(
            "SELECT payment_key FROM ledger_entries WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        _add_card_payment_batch_item(conn, context.batch_id, int(cursor.lastrowid), str(payment_key_row["payment_key"]))
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def defer_toll_payment(entry_payment_key: str, today: date | None = None, *, conn: Any | None = None) -> dict[str, str]:
    """카드 사용내역의 미처리액을 다음 결제월로 한 번 이월한다."""
    today = today or app_today()
    with borrowed_or_new_session(conn, transaction_mode="IMMEDIATE") as conn:
        context = _active_payment_context(today, conn)
        if context.batch_id is None:
            raise ValueError("월마감 후 생성된 결제 작업함이 없습니다.")
        if today > context.due_date:
            raise ValueError("이월 선택은 매월 14일까지 가능합니다.")
        payment_month = context.payment_month
        target_payment_month = _next_month_from_month(payment_month)
        row = conn.execute(
            """
            SELECT ledger_entries.book_section,
                   ledger_entries.title,
                   ledger_entries.entry_date,
                   ledger_entries.date_label,
                   ledger_entries.group_label,
                   ledger_entries.amount_value,
                   ledger_entries.sort_order
            FROM ledger_entries
            JOIN card_payment_batch_items
              ON card_payment_batch_items.entry_id = ledger_entries.id
            WHERE ledger_entries.payment_key = ?
              AND ledger_entries.entry_kind != 'planned'
              AND card_payment_batch_items.batch_id = ?
            """,
            (entry_payment_key, context.batch_id),
        ).fetchone()
        if row is None:
            raise ValueError("이번 달 이월 대상으로 선택할 수 없는 사용내역입니다.")
        allocated = query_money_sum(conn,
            """
            SELECT amount_value
            FROM card_payment_allocations
            JOIN card_payment_events
              ON card_payment_events.id = card_payment_allocations.payment_event_id
            WHERE entry_payment_key = ?
              AND card_payment_events.batch_id = ?
            """,
            (entry_payment_key, context.batch_id),
        )
        if allocated > 0:
            raise ValueError("이미 일부결제 또는 할인이 반영된 항목은 이월할 수 없습니다.")
        previous = conn.execute(
            "SELECT from_payment_month, target_payment_month FROM card_payment_deferrals WHERE entry_payment_key = ?",
            (entry_payment_key,),
        ).fetchone()
        if previous and previous["from_payment_month"] == payment_month:
            if previous["target_payment_month"] != target_payment_month:
                raise ValueError("이미 다른 결제월로 이월된 내역입니다.")
            if row["book_section"] != "current" or row["entry_date"] != f"{payment_month}-01":
                raise ValueError("이월 기록과 원장 상태가 일치하지 않습니다.")
            return {
                "entry_payment_key": entry_payment_key,
                "from_payment_month": payment_month,
                "target_payment_month": target_payment_month,
            }
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
                _carried_title(str(row["title"] or ""), str(row["entry_date"] or "")),
                first_order,
                entry_payment_key,
            ),
        )
    return {
        "entry_payment_key": entry_payment_key,
        "from_payment_month": payment_month,
        "target_payment_month": target_payment_month,
    }


def cancel_toll_deferral(entry_payment_key: str, today: date | None = None, *, conn: Any | None = None) -> bool:
    """현재 결제월에서 방금 이월한 카드 사용내역을 이번 달 처리 대상으로 되돌린다."""
    today = today or app_today()
    context = _active_payment_context(today, conn)
    if context.batch_id is None:
        return False
    if today > context.due_date:
        raise ValueError("이월은 매월 14일까지만 취소할 수 있습니다.")
    payment_month = context.payment_month
    with borrowed_or_new_session(conn) as conn:
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




def _delete_entry_discount_events(conn: Any, entry_payment_key: str) -> None:
    event_rows = conn.execute(
        """
        SELECT DISTINCT card_payment_events.id
        FROM card_payment_events
        JOIN card_payment_allocations
          ON card_payment_allocations.payment_event_id = card_payment_events.id
        WHERE card_payment_events.event_type = 'discount'
          AND card_payment_allocations.entry_payment_key = ?
        """,
        (entry_payment_key,),
    ).fetchall()
    conn.execute(
        """
        DELETE FROM card_payment_allocations
        WHERE entry_payment_key = ?
          AND payment_event_id IN (
            SELECT id FROM card_payment_events WHERE event_type = 'discount'
          )
        """,
        (entry_payment_key,),
    )
    for row in event_rows:
        remaining = conn.execute(
            "SELECT COUNT(*) AS count FROM card_payment_allocations WHERE payment_event_id = ?",
            (row["id"],),
        ).fetchone()["count"]
        if remaining == 0:
            conn.execute("DELETE FROM card_payment_events WHERE id = ?", (row["id"],))




def _clear_owner_discounts_for_month(conn: Any, month: str) -> None:
    rows = conn.execute(
        """
        SELECT payment_key
        FROM ledger_entries
        WHERE entry_date LIKE ?
          AND payment_key IS NOT NULL
        """,
        (f"{month}%",),
    ).fetchall()
    for row in rows:
        _delete_entry_discount_events(conn, row["payment_key"])
    conn.execute(
        """
        UPDATE ledger_entries
        SET discount_override = 0, updated_at = CURRENT_TIMESTAMP
        WHERE entry_date LIKE ?
        """,
        (f"{month}%",),
    )
    conn.execute(
        """
        UPDATE monthly_panels
        SET discount_amount = 0, discount_override = 0, updated_at = CURRENT_TIMESTAMP
        WHERE month = ? AND panel_type = 'claim'
        """,
        (month,),
    )




def _validate_month(value: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValueError("월 형식은 YYYY-MM이어야 합니다.") from exc


def _validate_discount_scope(value: str) -> None:
    if value not in {"owner", "family"}:
        raise ValueError("카드 구분은 owner 또는 family여야 합니다.")


def _discount_policy_value(conn: Any, month: str, scope: str) -> str:
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (f"card_discount_policy:{scope}:{month}",),
    ).fetchone()
    value = str(row["value"]) if row else default_discount_policy(scope)
    return normalize_discount_policy(value, scope)




def _add_card_payment_batch_item(conn: Any, batch_id: int | None, entry_id: int, payment_key: str) -> None:
    if batch_id is None or not payment_key:
        return
    entry = conn.execute("SELECT payment_key, entry_kind FROM ledger_entries WHERE id=?", (entry_id,)).fetchone()
    if entry is None or entry["entry_kind"] == "planned" or entry["payment_key"] != payment_key:
        raise ValueError("card batch item does not identify its ledger entry")
    existing = conn.execute("SELECT batch_id,entry_id,entry_payment_key FROM card_payment_batch_items "
                            "WHERE entry_id=? OR entry_payment_key=?", (entry_id, payment_key)).fetchall()
    if existing:
        if len(existing) == 1 and tuple(existing[0]) == (batch_id, entry_id, payment_key):
            return
        raise ValueError("duplicate card batch ownership")
    conn.execute(
        """
        INSERT INTO card_payment_batch_items(batch_id, entry_id, entry_payment_key)
        VALUES (?, ?, ?)
        """,
        (batch_id, entry_id, payment_key),
    )


def _carried_title(title: str, original_entry_date: str = "") -> str:
    if title.startswith("[이월]"):
        return title
    original_month = str(original_entry_date or "")[:7]
    if len(original_month) == 7 and original_month[5:7].isdigit():
        return f"[이월] [{int(original_month[5:7])}월 사용 내역] {title}"
    return f"[이월] {title}"


def _usage_title(usage_place: str, usage_item: str) -> str:
    if usage_place and usage_item:
        return f"[{usage_place}] {usage_item}"
    if usage_place:
        return f"[{usage_place}]"
    return usage_item

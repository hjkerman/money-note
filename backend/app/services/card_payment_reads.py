from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from app.money import exact_money, query_money_sum, allocation_totals

from app.db import session
from app.services.financial_relationships import validate_runtime_card_payment_ownership
from app.services.card_charge import (
    DiscountCard,
    evaluate_stored_charge,
    normalize_discount_policy,
    toll_title,
    transport_title,
)


@dataclass(frozen=True)
class CardPaymentContext:
    batch_id: int | None
    usage_month: str
    payment_month: str
    due_date: date


def _active_payment_context(today: date, conn: Any | None = None) -> CardPaymentContext:
    """달력 추정값이 아니라 마지막 월마감 batch를 기준으로 결제 작업 대상을 찾는다."""
    if conn is None:
        with session() as owned_conn:
            batch = _active_payment_batch(owned_conn)
    else:
        batch = _active_payment_batch(conn)
    if batch is None:
        payment_month = today.strftime("%Y-%m")
        return CardPaymentContext(
            batch_id=None,
            usage_month=_previous_month(today),
            payment_month=payment_month,
            due_date=_payment_due_date(payment_month),
        )
    usage_month = str(batch["usage_month"])
    payment_month = _next_month_from_month(usage_month)
    return CardPaymentContext(
        batch_id=int(batch["id"]),
        usage_month=usage_month,
        payment_month=payment_month,
        due_date=_payment_due_date(payment_month),
    )


def _active_payment_batch(conn: Any) -> Any:
    validate_runtime_card_payment_ownership(conn)
    return conn.execute(
        """
        SELECT *
        FROM card_payment_batches
        WHERE status = 'active'
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()


def _payment_rows_for_batch(
    context: CardPaymentContext,
    conn: Any | None = None,
) -> list[dict[str, Any]]:
    if context.batch_id is None:
        return []
    if conn is None:
        with session() as owned_conn:
            return _payment_rows_for_batch(context, owned_conn)
    validate_runtime_card_payment_ownership(conn)
    payment_month = context.payment_month
    settings = _settings_values(conn)
    rows = conn.execute(
        """
            SELECT ledger_entries.*,
                   card_payment_deferrals.from_payment_month AS deferred_from_payment_month,
                   card_payment_deferrals.target_payment_month AS deferred_target_payment_month
            FROM card_payment_batch_items
            JOIN ledger_entries
              ON ledger_entries.id = card_payment_batch_items.entry_id
            LEFT JOIN card_payment_deferrals
              ON card_payment_deferrals.entry_payment_key = ledger_entries.payment_key
            WHERE card_payment_batch_items.batch_id = ?
              AND ledger_entries.entry_kind != 'planned'
              AND COALESCE(ledger_entries.amount_value, 0) > 0
            ORDER BY
              CASE WHEN card_payment_deferrals.target_payment_month = ? THEN 0
                   WHEN card_payment_deferrals.from_payment_month = ? THEN 2
                   ELSE 1 END,
              ledger_entries.entry_date,
              ledger_entries.sort_order,
              ledger_entries.id
        """,
        (context.batch_id, payment_month, payment_month),
    ).fetchall()
    paid = allocation_totals(conn, 'immediate', context.batch_id)
    discounts = allocation_totals(conn, 'discount', context.batch_id)
    result = []
    for row in rows:
        data = dict(row)
        original = exact_money(data.get("amount_value") or 0)
        immediate = paid.get(data['payment_key'], 0)
        override_discount = discounts.get(data['payment_key'], 0)
        deferred_from = data.pop("deferred_from_payment_month", None)
        deferred_target = data.pop("deferred_target_payment_month", None)
        usage_month = str(data.get("entry_date") or "")[:7]
        discount_policy = normalize_discount_policy(
            settings.get(f"card_discount_policy:owner:{usage_month}"),
            "owner",
        )
        charge = evaluate_stored_charge(
            original,
            _manual_entry_discount({**data, "override_discount_amount": override_discount}),
            bool(data.get("discount_override") or override_discount or data.get("aux_amount_value")),
            discount_policy,
            usage_month,
            data.get("title"),
            DiscountCard.OWNER,
            merchant=data.get("usage_place"),
            spending_category=data.get("spending_category"),
            settings=settings,
        )
        discount = charge.effective_discount_amount
        data.update(
            {
                "original_amount": original,
                "immediate_paid_amount": immediate,
                "discount_amount": discount,
                "discount_policy": charge.month_policy,
                "automatic_discount_eligible": charge.automatic_discount_eligible,
                "automatic_discount_amount": charge.automatic_discount_amount,
                "effective_discount_amount": discount,
                "effective_amount_value": max(0, original - discount),
                "remaining_amount": max(0, original - immediate - discount),
                "is_transport": transport_title(data.get("title")),
                "is_toll": toll_title(data.get("title")),
                "is_deferred": deferred_from == payment_month and deferred_target > payment_month,
                "is_carried_over": deferred_target == payment_month,
                "payment_keys": [data["payment_key"]] if data.get("payment_key") else [],
                "entry_ids": [data["id"]],
                "payment_parts": [
                    {
                        "entry_payment_key": data["payment_key"],
                        "entry_id": data["id"],
                        "remaining_amount": max(0, original - immediate - discount),
                    }
                ] if data.get("payment_key") else [],
                "is_group": False,
            }
        )
        result.append(data)
    return result


def _group_toll_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    toll_rows = [row for row in rows if row.get("is_toll")]
    if len(toll_rows) <= 1:
        return rows

    # Keep presentation groups homogeneous so partial defer/payment stays actionable.
    states: dict[tuple[bool, bool, bool], list[dict[str, Any]]] = {}
    for row in toll_rows:
        state = (
            bool(row.get("is_deferred")),
            bool(row.get("is_carried_over")),
            bool(row.get("immediate_paid_amount")),
        )
        states.setdefault(state, []).append(row)
    if len(states) > 1:
        grouped_by_id: dict[int, dict[str, Any]] = {}
        subgroup_ids: dict[int, set[int]] = {}
        for state_rows in states.values():
            grouped = _group_toll_rows(state_rows)[0]
            ids = {int(row["id"]) for row in state_rows}
            for item_id in ids:
                grouped_by_id[item_id] = grouped
                subgroup_ids[item_id] = ids
        result = []
        inserted_ids: set[int] = set()
        for row in rows:
            item_id = int(row["id"])
            if item_id in inserted_ids:
                continue
            if item_id in grouped_by_id:
                result.append(grouped_by_id[item_id])
                inserted_ids.update(subgroup_ids[item_id])
            else:
                result.append(row)
        return result

    first = toll_rows[0]
    grouped = {**first}
    grouped.update(
        {
            "id": -int(first["id"]),
            "payment_key": f"group:toll:{first['id']}",
            "payment_keys": [row["payment_key"] for row in toll_rows if row.get("payment_key")],
            "entry_ids": [row["id"] for row in toll_rows],
            "payment_parts": [
                {
                    "entry_payment_key": row["payment_key"],
                    "entry_id": row["id"],
                    "remaining_amount": int(row.get("remaining_amount") or 0),
                }
                for row in toll_rows
                if row.get("payment_key")
            ],
            "date_label": "",
            "group_label": "",
            "title": "하이패스/통행료 통합",
            "usage_place": "하이패스/통행료",
            "usage_item": f"{len(toll_rows)}건",
            "original_amount": sum(int(row.get("original_amount") or 0) for row in toll_rows),
            "amount_value": sum(int(row.get("amount_value") or 0) for row in toll_rows),
            "immediate_paid_amount": sum(int(row.get("immediate_paid_amount") or 0) for row in toll_rows),
            "discount_amount": sum(int(row.get("discount_amount") or 0) for row in toll_rows),
            "automatic_discount_eligible": False,
            "automatic_discount_amount": 0,
            "effective_discount_amount": sum(
                int(row.get("effective_discount_amount") or 0)
                for row in toll_rows
            ),
            "effective_amount_value": sum(
                int(row.get("effective_amount_value") or 0)
                for row in toll_rows
            ),
            "remaining_amount": sum(int(row.get("remaining_amount") or 0) for row in toll_rows),
            "is_transport": any(bool(row.get("is_transport")) for row in toll_rows),
            "is_toll": True,
            "is_deferred": all(bool(row.get("is_deferred")) for row in toll_rows),
            "is_carried_over": all(bool(row.get("is_carried_over")) for row in toll_rows),
            "is_group": True,
        }
    )
    grouped_inserted = False
    result = []
    toll_ids = {row["id"] for row in toll_rows}
    for row in rows:
        if row["id"] not in toll_ids:
            result.append(row)
            continue
        if not grouped_inserted:
            result.append(grouped)
            grouped_inserted = True
    return result


def _events_for_batch(batch_id: int | None) -> list[dict[str, Any]]:
    if batch_id is None:
        return []
    with session() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM card_payment_events
            WHERE batch_id = ?
            ORDER BY event_date DESC, id DESC
            """,
            (batch_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _manual_entry_discount(row: Any) -> int:
    """원장 수동 할인액을 꺼낸다. aux 값이 있으면 과거 할인 이벤트보다 우선한다."""
    if row["discount_override"] and row["aux_amount_value"] is not None:
        return exact_money(row["aux_amount_value"] or 0)
    return exact_money(row["override_discount_amount"] or 0)


def _previous_month(value: date) -> str:
    if value.month == 1:
        return f"{value.year - 1}-12"
    return f"{value.year}-{value.month - 1:02d}"


def _settings_values(conn: Any) -> dict[str, str]:
    return {
        str(row["key"]): str(row["value"])
        for row in conn.execute("SELECT key, value FROM app_settings").fetchall()
    }


def _next_month(value: date) -> str:
    if value.month == 12:
        return f"{value.year + 1}-01"
    return f"{value.year}-{value.month + 1:02d}"


def _next_month_from_month(value: str) -> str:
    parsed = datetime.strptime(f"{value}-01", "%Y-%m-%d").date()
    return _next_month(parsed)


def _payment_due_date(payment_month: str) -> date:
    parsed = datetime.strptime(f"{payment_month}-01", "%Y-%m-%d").date()
    return date(parsed.year, parsed.month, min(14, monthrange(parsed.year, parsed.month)[1]))


def _primary_income_total(payment_month: str) -> int:
    with session() as conn:
        total = query_money_sum(conn,
            """
            SELECT amount_value
            FROM cash_flows
            WHERE occurred_on LIKE ?
              AND is_primary_income = 1
              AND amount_value > 0
            """,
            (f"{payment_month}%",),
        )
    return exact_money(total, 'primary_income_total')


def _setting_value(key: str, conn: Any | None = None) -> str:
    if conn is None:
        with session() as owned_conn:
            return _setting_value(key, owned_conn)
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else ""

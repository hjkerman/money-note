from datetime import date, datetime
from typing import Any
from app.money import exact_money, query_money_sum

from app.db import borrowed_or_new_session, session
from app.repositories.common import ensure_payment_key_available, new_payment_key, row_to_dict
from app.schemas import LedgerEntryIn, LedgerEntryPatch, PlannedEntryIn
from app.services.clock import app_today
from app.services.card_charge import utility_default_discount_excluded
from app.services.financial_relationships import (
    validate_runtime_card_payment_ownership, validate_runtime_recurring_ownership,
)
from app.services.legacy_recurring import (
    infer_legacy_recurring_sources,
    near_confirmation_creation,
    validate_source_epoch, validate_recurring_ownership,
)
from app.services.card_payments import (
    closed_month_payment_batch_id,
    _add_card_payment_batch_item,
    set_entry_discount,
)
from app.repositories.notification_registration import (
    existing_registration,
    legacy_ledger_registration_fingerprint,
    registration_fingerprint,
    save_registration,
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
    "discount_override",
]


def list_entries(
    section: str,
    today: date | None = None,
    conn: Any | None = None,
) -> list[dict[str, Any]]:
    current_month = (today or app_today()).strftime("%Y-%m")
    filter_confirmed_planned = (
        " AND NOT (entry_kind = 'planned' AND COALESCE(confirmed_month, '') = ?)"
        if section == "current"
        else ""
    )
    params: tuple[Any, ...] = (section, current_month) if section == "current" else (section,)
    if conn is None:
        with session() as owned_conn:
            return list_entries(section, today, owned_conn)
    validate_runtime_recurring_ownership(conn)
    validate_runtime_card_payment_ownership(conn)
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


def list_recent_closed_month_expense_counts(limit: int = 3) -> list[int]:
    """최근 마감 월의 본인 지출 건수를 최신 월부터 반환한다."""
    with session() as conn:
        rows = conn.execute(
            """
            SELECT substr(entry_date, 1, 7) AS entry_month, COUNT(*) AS expense_count
            FROM ledger_entries
            WHERE book_section = 'archive'
              AND entry_kind = 'expense'
              AND entry_date IS NOT NULL
            GROUP BY substr(entry_date, 1, 7)
            ORDER BY entry_month DESC
            LIMIT ?
            """,
            (max(1, limit),),
        ).fetchall()
    return [int(row["expense_count"]) for row in rows]


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
        candidates = [dict(row) for row in conn.execute(
            "SELECT * FROM ledger_entries WHERE entry_kind IN ('planned', 'expense')",
        )]
        closed = conn.execute("SELECT value FROM app_settings WHERE key='last_closed_month'").fetchone()
        validate_recurring_ownership(candidates, str(closed["value"]) if closed else "0000-00")
        confirmed_entries = []
        for row in rows:
            item = row_to_dict(row)
            validate_source_epoch(item)
            matches = [expense for expense in candidates
                       if expense.get("source_planned_entry_id") == row["id"]
                       and expense["entry_kind"] == "expense"
                       and expense.get("confirmed_month") == row["confirmed_month"]
                       and expense.get("confirmed_at") == row["confirmed_at"]]
            if len(matches) != 1:
                raise ValueError("recurring confirmation requires exactly one owned expense")
            expense = matches[0]
            item["entry_date"] = expense["entry_date"]
            item["_confirmed_expense"] = row_to_dict(expense)
            confirmed_entries.append(item)
    return confirmed_entries


def get_entry(entry_id: int) -> dict[str, Any] | None:
    with session() as conn:
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
    return row_to_dict(row) if row else None


def confirm_planned_entry(
    entry_id: int,
    today: date | None = None,
    entry_date: str | None = None,
    actual_amount: int | None = None,
    conn: Any | None = None,
) -> dict[str, Any] | None:
    today = today or app_today()
    confirmed_month = today.strftime("%Y-%m")
    with borrowed_or_new_session(conn, transaction_mode="IMMEDIATE") as conn:
        closed = conn.execute("SELECT value FROM app_settings WHERE key = 'last_closed_month'").fetchone()
        if closed and confirmed_month <= str(closed["value"]):
            raise ValueError("카드 정기결제는 실제 달력이 다음 달로 바뀐 뒤 확인할 수 있습니다.")
        planned = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        if planned is None:
            return None
        if planned["entry_kind"] != "planned":
            raise ValueError("only card recurring entries can be confirmed")
        _require_recurring_ownership(conn, entry_id)
        validate_source_epoch(dict(planned))
        if planned["confirmed_month"] == confirmed_month:
            raise ValueError("card recurring entry already confirmed")
        if conn.execute(
            "SELECT 1 FROM ledger_entries WHERE book_section = 'current' AND entry_kind = 'expense' "
            "AND source_planned_entry_id = ? AND (confirmed_month = ? OR confirmed_month IS NULL) LIMIT 1",
            (entry_id, confirmed_month),
        ).fetchone() is not None:
            raise ValueError("recurring confirmation already has a generated expense")
        amount = exact_money(planned["amount_value"] if actual_amount is None else actual_amount)
        if amount < 0:
            raise ValueError("카드 정기결제 실제 원금은 0원 이상이어야 합니다.")

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
        payment_key = new_payment_key(conn)
        cursor = conn.execute(
            """
            INSERT INTO ledger_entries(
                book_section, entry_kind, entry_date, date_label, group_label, title,
                usage_place, usage_item, amount_value, amount_expr, sort_order, payment_key,
                source_planned_entry_id, discount_override
            )
            VALUES ('current', 'expense', ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment_date.isoformat(),
                date_label,
                planned["title"],
                planned["usage_place"],
                planned["usage_item"],
                amount,
                planned["amount_expr"] if amount == int(planned["amount_value"] or 0) else str(amount),
                sort_order,
                payment_key,
                entry_id,
                int(bool(planned["discount_override"]) and planned["aux_amount_value"] is None),
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
        conn.execute(
            """UPDATE ledger_entries
               SET confirmed_month = ?, confirmed_at = (
                   SELECT confirmed_at FROM ledger_entries WHERE id = ?)
               WHERE id = ?""",
            (confirmed_month, entry_id, cursor.lastrowid),
        )
        _require_recurring_ownership(conn, entry_id)
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


def _same_legacy_registered_entry(
    stored: Any, values: dict[str, Any],
    initial_discount_enabled: bool | None, initial_discount_override_amount: int | None,
) -> bool:
    # An old digest omitted some authoritative fields. Upgrade only when the
    # currently stored row proves the same final input; otherwise fail closed.
    fields = (
        "book_section", "entry_kind", "entry_date", "date_label", "group_label",
        "title", "usage_place", "usage_item", "amount_value", "amount_expr",
        "aux_amount_expr", "extra_value", "due_day", "confirmed_at",
        "spending_category",
    )
    if any(stored[field] != values.get(field) for field in fields):
        return False
    if values.get("payment_key") is not None and stored["payment_key"] != values["payment_key"]:
        return False
    if initial_discount_override_amount is not None:
        expected_override, expected_aux = 1, initial_discount_override_amount
    elif initial_discount_enabled is False:
        expected_override, expected_aux = 1, 0
    else:
        expected_override = int(values.get("discount_override") or 0)
        expected_aux = values.get("aux_amount_value")
    return int(stored["discount_override"]) == expected_override and stored["aux_amount_value"] == expected_aux


def create_entry(entry: LedgerEntryIn, conn: Any | None = None) -> dict[str, Any]:
    initial_discount_enabled = entry.discount_enabled
    initial_discount_override_amount = entry.discount_override_amount
    if (
        initial_discount_enabled is None
        and initial_discount_override_amount is None
        and not entry.discount_override
        and entry.aux_amount_value is None
        and entry.entry_kind in {"expense", "late_expense"}
        and utility_default_discount_excluded(entry.usage_place, entry.usage_item)
    ):
        initial_discount_enabled = False
    values = entry.model_dump()
    if values.get("entry_date") is not None:
        values["entry_date"] = values["entry_date"].isoformat()
    _validate_structured_entry(values)
    placeholders = ", ".join("?" for _ in ENTRY_COLUMNS)
    columns = ", ".join(ENTRY_COLUMNS)
    with borrowed_or_new_session(conn, transaction_mode="IMMEDIATE") as conn:
        late_batch_id = None
        if (
            initial_discount_enabled is not None or initial_discount_override_amount is not None
        ) and (entry.entry_kind not in {"expense", "late_expense"}):
            raise ValueError("initial discount intent is only valid for card expenses")

        registration_key = entry.candidate_registration_key
        if registration_key and entry.entry_kind not in {"expense", "late_expense"}:
            raise ValueError("알림 후보 등록 key는 카드 지출에만 사용할 수 있습니다.")
        fingerprint_values = dict(values)
        if initial_discount_override_amount is not None:
            fingerprint_values["discount_override_amount"] = initial_discount_override_amount
        elif initial_discount_enabled is False:
            fingerprint_values["discount_enabled"] = False
        fingerprint = (
            registration_fingerprint("ledger", fingerprint_values) if registration_key else None
        )
        if registration_key:
            try:
                registered_id = existing_registration(conn, registration_key, "ledger", fingerprint)
            except ValueError:
                old = conn.execute(
                    "SELECT target, target_id, request_fingerprint FROM notification_candidate_registrations WHERE registration_key = ?",
                    (registration_key,),
                ).fetchone()
                stored = conn.execute(
                    "SELECT * FROM ledger_entries WHERE id = ?", (old["target_id"],)
                ).fetchone() if old is not None and old["target"] == "ledger" else None
                if (old is None or stored is None or
                    old["request_fingerprint"] != legacy_ledger_registration_fingerprint(fingerprint_values) or
                    not _same_legacy_registered_entry(stored, values, initial_discount_enabled, initial_discount_override_amount)):
                    raise
                conn.execute(
                    "UPDATE notification_candidate_registrations SET request_fingerprint = ? WHERE registration_key = ?",
                    (fingerprint, registration_key),
                )
                registered_id = int(old["target_id"])
            if registered_id is not None:
                registered = conn.execute(
                    "SELECT * FROM ledger_entries WHERE id = ?", (registered_id,)
                ).fetchone()
                if registered is None:
                    raise ValueError("이미 등록 후 삭제된 알림 후보입니다.")
                return row_to_dict(registered)
        if values["entry_kind"] != "planned":
            if values.get("payment_key"):
                ensure_payment_key_available(conn, str(values["payment_key"]))
            else:
                values["payment_key"] = new_payment_key(conn)
        # 마감 월의 새 카드 사용은 귀속 가능한 미결제 batch에만 기록한다.
        if values["entry_kind"] in {"expense", "late_expense"} and values.get("entry_date"):
            setting = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'last_closed_month'"
            ).fetchone()
            entry_month = str(values["entry_date"])[:7]
            if values["entry_kind"] == "late_expense" and (
                not setting or entry_month > str(setting["value"])
            ):
                raise ValueError("마감 전 사용월은 일반 지출로 등록해야 합니다.")
            if setting and entry_month <= str(setting["value"]):
                if int(values.get("amount_value") or 0) <= 0:
                    raise ValueError(
                        "마감한 달의 카드 지출은 양수 사용금액으로만 등록할 수 있습니다."
                    )
                late_batch_id = closed_month_payment_batch_id(conn, entry_month, app_today())
                values["entry_kind"] = "late_expense"
                values["book_section"] = "archive"
                next_order = conn.execute(
                    "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM ledger_entries WHERE book_section = 'archive'"
                ).fetchone()["next_order"]
                values["sort_order"] = int(next_order)
        if values["entry_kind"] != "planned" and int(values.get("sort_order") or 0) <= 0:
            next_order = conn.execute(
                """
                SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order
                FROM ledger_entries
                WHERE book_section = ?
                """,
                (values["book_section"],),
            ).fetchone()["next_order"]
            values["sort_order"] = int(next_order)
        cursor = conn.execute(
            f"INSERT INTO ledger_entries ({columns}) VALUES ({placeholders})",
            tuple(values[column] for column in ENTRY_COLUMNS),
        )
        if late_batch_id is not None:
            _add_card_payment_batch_item(
                conn, late_batch_id, int(cursor.lastrowid), str(values["payment_key"])
            )
        if initial_discount_override_amount is not None:
            set_entry_discount(
                str(values["payment_key"]), initial_discount_override_amount, conn=conn
            )
        elif initial_discount_enabled is False:
            set_entry_discount(str(values["payment_key"]), 0, conn=conn)
        if registration_key:
            save_registration(conn, registration_key, "ledger", int(cursor.lastrowid), fingerprint)
        row = conn.execute(
            "SELECT * FROM ledger_entries WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        if row["entry_kind"] == "planned" or row["confirmed_month"] is not None or row["confirmed_at"] is not None:
            _require_recurring_ownership(conn, int(row["id"]))
        return row_to_dict(row)


def append_planned_entry(entry: PlannedEntryIn, *, conn: Any | None = None) -> dict[str, Any]:
    with borrowed_or_new_session(conn, transaction_mode="IMMEDIATE") as conn:
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
                usage_place, usage_item, amount_value, amount_expr, sort_order, due_day, confirmed_at,
                discount_override
            )
            VALUES ('current', 'planned', NULL, '카드 정기결제', '카드 정기결제', ?, ?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (
                entry.title,
                entry.usage_place,
                entry.usage_item,
                entry.amount_value,
                entry.amount_expr,
                sort_order,
                entry.due_day,
                int(utility_default_discount_excluded(entry.usage_place, entry.usage_item)),
            ),
        )
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return row_to_dict(row)


def delete_planned_entry(entry_id: int, *, conn: Any | None = None) -> bool:
    with borrowed_or_new_session(conn) as conn:
        _require_recurring_ownership(conn, entry_id)
        _detach_recurring_expenses(conn, entry_id)
        cursor = conn.execute(
            """
            DELETE FROM ledger_entries
            WHERE id = ? AND book_section = 'current' AND entry_kind = 'planned'
            """,
            (entry_id,),
        )
    return cursor.rowcount > 0


def reorder_current_entries(ordered_ids: list[int], entry_kind: str | None = None, *, conn: Any | None = None) -> list[dict[str, Any]]:
    with borrowed_or_new_session(conn) as conn:
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


def update_entry(entry_id: int, patch: LedgerEntryPatch, *, conn: Any | None = None) -> dict[str, Any] | None:
    values = patch.model_dump(exclude_unset=True)
    if values.get("entry_date") is not None:
        values["entry_date"] = values["entry_date"].isoformat()
    if not values:
        with borrowed_or_new_session(conn) as conn:
            validate_runtime_recurring_ownership(conn)
            validate_runtime_card_payment_ownership(conn)
            row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        return row_to_dict(row) if row else None

    with borrowed_or_new_session(conn, transaction_mode="IMMEDIATE") as conn:
        existing = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        if existing is None:
            return None
        batch_owned = conn.execute("SELECT 1 FROM card_payment_batch_items "
            "WHERE entry_id=? OR entry_payment_key=? LIMIT 1", (entry_id, existing["payment_key"])).fetchone() is not None
        if batch_owned:
            validate_runtime_card_payment_ownership(conn)
        if existing["entry_kind"] == "planned":
            _require_recurring_ownership(conn, entry_id)
        if existing["source_planned_entry_id"] is None:
            source = _legacy_recurring_source(conn, entry_id, existing, allow_binding=True)
            if source is not None:
                values["source_planned_entry_id"] = source
        source = values.get("source_planned_entry_id") or existing["source_planned_entry_id"]
        if not source and existing["entry_kind"] == "expense" and (
            existing["confirmed_month"] is not None or existing["confirmed_at"] is not None
        ):
            raise ValueError("unresolved recurring confirmation source")
        if source and existing["book_section"] != "current":
            _validate_archived_recurring_source(conn, source)
        if source and existing["book_section"] == "current":
            _ensure_recurring_confirmation_epoch(conn, entry_id, source)
        merged = {**dict(existing), **values}
        _validate_structured_entry(merged)
        assignments = ", ".join(f"{column} = ?" for column in values)
        params = list(values.values()) + [entry_id]
        conn.execute(
            f"UPDATE ledger_entries SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params,
        )
        if source or existing["entry_kind"] == "planned":
            _require_recurring_ownership(conn, source or entry_id)
        if batch_owned:
            validate_runtime_card_payment_ownership(conn)
        row = conn.execute("SELECT * FROM ledger_entries WHERE id = ?", (entry_id,)).fetchone()
        return row_to_dict(row) if row else None


def delete_entry(entry_id: int, *, conn: Any | None = None) -> bool:
    with borrowed_or_new_session(conn, transaction_mode="IMMEDIATE") as conn:
        entry = conn.execute(
            """
            SELECT id, payment_key, source_planned_entry_id, book_section, entry_kind,
                   entry_date, title, usage_place, usage_item, amount_value, created_at,
                   confirmed_month, confirmed_at
            FROM ledger_entries
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()
        if entry is None:
            return False
        if entry["entry_kind"] == "planned":
            _require_recurring_ownership(conn, entry_id)
            _detach_recurring_expenses(conn, entry_id)
        source_planned_entry_id = entry["source_planned_entry_id"]
        if source_planned_entry_id is None:
            source_planned_entry_id = _legacy_recurring_source(conn, entry_id, entry)
        if source_planned_entry_id is None and entry["entry_kind"] == "expense" and (
            entry["confirmed_month"] is not None or entry["confirmed_at"] is not None
        ):
            raise ValueError("unresolved recurring confirmation source")
        if source_planned_entry_id and entry["book_section"] != "current":
            _validate_archived_recurring_source(conn, source_planned_entry_id)
        epoch = None
        if source_planned_entry_id:
            epoch = _ensure_recurring_confirmation_epoch(conn, entry_id, source_planned_entry_id)
        if entry["payment_key"]:
            paid = conn.execute(
                """
                SELECT 1
                FROM card_payment_allocations
                JOIN card_payment_events
                  ON card_payment_events.id = card_payment_allocations.payment_event_id
                WHERE card_payment_allocations.entry_payment_key = ?
                  AND card_payment_events.event_type = 'immediate'
                  AND card_payment_allocations.amount_value > 0
                LIMIT 1
                """,
                (entry["payment_key"],),
            ).fetchone()
            if paid is not None:
                raise ValueError("일부라도 결제된 카드 사용내역은 일반 원장 삭제로 지울 수 없습니다.")
            _delete_card_payment_references(conn, str(entry["payment_key"]))
        cursor = conn.execute("DELETE FROM ledger_entries WHERE id = ?", (entry_id,))
        if epoch is not None:
            conn.execute(
                """
                UPDATE ledger_entries
                SET entry_date = NULL,
                    confirmed_at = NULL,
                    confirmed_month = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND entry_kind = 'planned' AND confirmed_month = ? AND confirmed_at = ?
                """,
                (source_planned_entry_id, epoch[0], epoch[1]),
            )
    return cursor.rowcount > 0


def _validate_archived_recurring_source(conn: Any, source_id: int) -> None:
    source = conn.execute("SELECT * FROM ledger_entries WHERE id=?", (source_id,)).fetchone()
    if source is None or source["entry_kind"] != "planned":
        raise ValueError("unresolved recurring confirmation source")
    _require_recurring_ownership(conn, source_id)


def _require_recurring_ownership(conn: Any, source_id: int) -> None:
    rows = [dict(row) for row in conn.execute(
        "SELECT * FROM ledger_entries WHERE id=? OR source_planned_entry_id=?", (source_id, source_id),
    )]
    closed = conn.execute("SELECT value FROM app_settings WHERE key='last_closed_month'").fetchone()
    validate_recurring_ownership(rows, str(closed["value"]) if closed else "0000-00")


def _detach_recurring_expenses(conn: Any, source_id: int) -> None:
    # Deleting a valid template keeps the actual expenses as ordinary ledger
    # facts. Retire all ownership metadata together with ON DELETE SET NULL.
    conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL "
                 "WHERE source_planned_entry_id=? AND EXISTS (SELECT 1 FROM ledger_entries source "
                 "WHERE source.id=? AND source.book_section='current' AND source.entry_kind='planned')",
                 (source_id, source_id))


def _ensure_recurring_confirmation_epoch(conn: Any, entry_id: int, source_id: int) -> tuple[str, str]:
    rows = [dict(row) for row in conn.execute(
        "SELECT * FROM ledger_entries WHERE id IN (?, ?) OR source_planned_entry_id = ?",
        (source_id, entry_id, source_id),
    )]
    source = next((row for row in rows if row["id"] == source_id), None)
    if source is None or source["entry_kind"] != "planned":
        raise ValueError("unresolved recurring confirmation source")
    validate_source_epoch(source)
    for row in rows:
        if row["id"] == entry_id and row.get("source_planned_entry_id") is None:
            # The caller has already proven this legacy source, in this same
            # transaction, before editing any mutable financial/display field.
            row["source_planned_entry_id"] = source_id
    closed = conn.execute("SELECT value FROM app_settings WHERE key='last_closed_month'").fetchone()
    validate_recurring_ownership(rows, str(closed["value"]) if closed else "0000-00")
    entry = next((row for row in rows if row["id"] == entry_id), None)
    if entry is None or not entry.get("confirmed_month") or not entry.get("confirmed_at"):
        raise ValueError("unresolved recurring confirmation epoch: cancellation identity is not provable")
    if source.get("confirmed_month") is None:
        closed = conn.execute("SELECT value FROM app_settings WHERE key='last_closed_month'").fetchone()
        if str(entry["confirmed_month"]) > (str(closed["value"]) if closed else "0000-00"):
            raise ValueError("unresolved recurring confirmation epoch: source confirmation is missing")
    conn.execute("UPDATE ledger_entries SET confirmed_month = ?, confirmed_at = ? WHERE id = ?",
                 (entry["confirmed_month"], entry["confirmed_at"], entry_id))
    return str(entry["confirmed_month"]), str(entry["confirmed_at"])


def _legacy_recurring_source(
    conn: Any, entry_id: int, entry: Any, *, allow_binding: bool = False,
) -> int | None:
    """Bind before an edit, or reject cancellation of a still-unbound lineage."""
    if entry["book_section"] != "current" or entry["entry_kind"] != "expense":
        return None
    month = str(entry["entry_date"])[:7] if entry["entry_date"] else "0000-00"
    rows = [dict(row) for row in conn.execute(
        """
        SELECT * FROM ledger_entries
        WHERE book_section = 'current'
          AND ((entry_kind = 'planned' AND confirmed_month = ? AND confirmed_at IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM ledger_entries owned
                                WHERE owned.source_planned_entry_id = ledger_entries.id))
               OR (entry_kind = 'expense' AND entry_date LIKE ?))
        """,
        (month, f"{month}%"),
    )]
    sources = infer_legacy_recurring_sources(rows)
    if entry_id in sources:
        if allow_binding:
            return sources[entry_id]
        raise ValueError("unresolved legacy recurring confirmation: bind before cancellation")
    explicitly_linked = {row["source_planned_entry_id"] for row in rows
                         if row["entry_kind"] == "expense" and row["source_planned_entry_id"] is not None}
    for planned in rows:
        if planned["entry_kind"] != "planned" or planned["id"] in explicitly_linked:
            continue
        same_date = planned["entry_date"] is None or planned["entry_date"] == entry["entry_date"]
        same_description = all(
            (planned[field] or "") == (entry[field] or "")
            for field in ("title", "usage_place", "usage_item")
        )
        if same_date and (same_description or planned["amount_value"] == entry["amount_value"]):
            raise ValueError("ambiguous legacy recurring confirmation: source is not provable")
    # An old, already-edited source-less row may have moved to another entry
    # month before this version could bind it. Its immutable creation time can
    # still reveal a plausible confirmation; reject rather than deleting it
    # while silently leaving the reserve released.
    all_confirmed = conn.execute(
        "SELECT id, confirmed_at FROM ledger_entries WHERE book_section = 'current' "
        "AND entry_kind = 'planned' AND confirmed_month IS NOT NULL AND confirmed_at IS NOT NULL"
    ).fetchall()
    if all_confirmed:
        all_explicit = {row[0] for row in conn.execute(
            "SELECT source_planned_entry_id FROM ledger_entries WHERE source_planned_entry_id IS NOT NULL"
        )}
        if any(planned["id"] not in all_explicit and near_confirmation_creation(
            entry["created_at"], planned["confirmed_at"]
        ) for planned in all_confirmed):
            raise ValueError("unresolved legacy recurring confirmation: source is not provable")
    return None


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
    if exact_money(values["amount_value"]) < 0:
        raise ValueError("amount_value must be greater than or equal to zero")


def _delete_card_payment_references(conn: Any, payment_key: str) -> None:
    """장부 행 삭제 시 결제/할인 배분과 이월 상태를 함께 정리한다."""
    validate_runtime_card_payment_ownership(conn)
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
    conn.execute("DELETE FROM card_payment_batch_items WHERE entry_payment_key = ?", (payment_key,))
    conn.execute("DELETE FROM card_payment_deferrals WHERE entry_payment_key = ?", (payment_key,))
    conn.execute("DELETE FROM card_payment_allocations WHERE entry_payment_key = ?", (payment_key,))
    for allocation in allocation_rows:
        event_id = allocation["payment_event_id"]
        remaining = query_money_sum(conn,
            "SELECT amount_value FROM card_payment_allocations WHERE payment_event_id = ?",
            (event_id,),
        )
        remaining = exact_money(remaining, 'payment remaining total')
        if remaining <= 0:
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
                (-int(remaining or 0), allocation["cash_flow_id"]),
            )

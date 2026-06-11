from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Any

from app.db import session


SNAPSHOT_SCHEMA_VERSION = 1
SENSITIVE_SETTING_KEYS = {"share_pin_hash", "share_pin_is_default"}
SNAPSHOT_TABLES = [
    "ledger_entries",
    "monthly_panels",
    "cash_flows",
    "installments",
    "card_payment_events",
    "card_payment_allocations",
    "card_payment_deferrals",
    "app_settings",
    "app_labels",
]
LEDGER_TABLES = [
    "card_payment_deferrals",
    "card_payment_allocations",
    "card_payment_events",
    "installments",
    "cash_flows",
    "monthly_panels",
    "ledger_entries",
]


def export_snapshot(today: date | None = None) -> tuple[str, dict[str, Any]]:
    """최근 3개월 장부 데이터와 비민감 운영 설정을 JSON snapshot으로 만든다."""
    today = today or date.today()
    months = _recent_months(today, 3)
    start_date = f"{months[0]}-01"
    end_date = f"{months[-1]}-{monthrange(int(months[-1][:4]), int(months[-1][5:7]))[1]:02d}"
    with session() as conn:
        ledger_rows = _ledger_rows(conn, start_date, end_date)
        payment_keys = {row["payment_key"] for row in ledger_rows if row.get("payment_key")}
        events = _event_rows(conn, start_date, end_date, payment_keys)
        event_ids = {row["id"] for row in events}
        cash_flow_ids = {row["cash_flow_id"] for row in events if row.get("cash_flow_id") is not None}
        data = {
            "ledger_entries": ledger_rows,
            "monthly_panels": _rows(
                conn,
                "SELECT * FROM monthly_panels WHERE month IN ({}) ORDER BY month, panel_type, sort_order, id".format(
                    ",".join("?" for _ in months),
                ),
                tuple(months),
            ),
            "cash_flows": _cash_flow_rows(conn, start_date, end_date, cash_flow_ids),
            "installments": _rows(
                conn,
                """
                SELECT * FROM installments
                WHERE is_active = 1 OR start_month IN ({})
                ORDER BY is_active DESC, start_month, sort_order, id
                """.format(",".join("?" for _ in months)),
                tuple(months),
            ),
            "card_payment_events": events,
            "card_payment_allocations": _allocation_rows(conn, event_ids),
            "card_payment_deferrals": _deferral_rows(conn, months, payment_keys),
            "app_settings": _rows(
                conn,
                """
                SELECT * FROM app_settings
                WHERE key NOT IN ({})
                ORDER BY key
                """.format(",".join("?" for _ in SENSITIVE_SETTING_KEYS)),
                tuple(SENSITIVE_SETTING_KEYS),
            ),
            "app_labels": _rows(conn, "SELECT * FROM app_labels ORDER BY key"),
        }
    exported_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "exported_at": exported_at,
        "range": {
            "months": months,
            "start_date": start_date,
            "end_date": end_date,
        },
        "data": data,
    }
    filename = f"money-note-snapshot-{exported_at.replace(':', '').replace('-', '')}.money-note-snapshot.json"
    return filename, snapshot


def restore_snapshot(snapshot: dict[str, Any]) -> dict[str, int]:
    """JSON snapshot을 검증한 뒤 장부 테이블과 비민감 운영 설정을 교체한다."""
    _validate_snapshot(snapshot)
    data = snapshot["data"]
    restored: dict[str, int] = {}
    with session() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in LEDGER_TABLES:
            conn.execute(f"DELETE FROM {table}")
        conn.execute(
            "DELETE FROM app_settings WHERE key NOT IN ({})".format(
                ",".join("?" for _ in SENSITIVE_SETTING_KEYS),
            ),
            tuple(SENSITIVE_SETTING_KEYS),
        )
        conn.execute("DELETE FROM app_labels")
        for table in SNAPSHOT_TABLES:
            restored[table] = _insert_rows(conn, table, data[table])
        conn.execute("PRAGMA foreign_keys = ON")
    return restored


def _ledger_rows(conn: Any, start_date: str, end_date: str) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT *
        FROM ledger_entries
        WHERE entry_kind = 'planned'
           OR (entry_date BETWEEN ? AND ?)
           OR (entry_date IS NULL AND book_section = 'current')
        ORDER BY book_section, entry_kind, entry_date, sort_order, id
        """,
        (start_date, end_date),
    )


def _event_rows(conn: Any, start_date: str, end_date: str, payment_keys: set[str]) -> list[dict[str, Any]]:
    rows = _rows(
        conn,
        """
        SELECT DISTINCT card_payment_events.*
        FROM card_payment_events
        LEFT JOIN card_payment_allocations
          ON card_payment_allocations.payment_event_id = card_payment_events.id
        WHERE card_payment_events.event_date BETWEEN ? AND ?
           OR card_payment_allocations.entry_payment_key IN ({})
        ORDER BY card_payment_events.event_date, card_payment_events.id
        """.format(_placeholders(payment_keys)),
        (start_date, end_date, *tuple(payment_keys)),
    )
    return rows


def _cash_flow_rows(conn: Any, start_date: str, end_date: str, cash_flow_ids: set[int]) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT *
        FROM cash_flows
        WHERE occurred_on BETWEEN ? AND ?
           OR id IN ({})
        ORDER BY occurred_on, sort_order, id
        """.format(_placeholders(cash_flow_ids)),
        (start_date, end_date, *tuple(cash_flow_ids)),
    )


def _allocation_rows(conn: Any, event_ids: set[int]) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT *
        FROM card_payment_allocations
        WHERE payment_event_id IN ({})
        ORDER BY payment_event_id, id
        """.format(_placeholders(event_ids)),
        tuple(event_ids),
    )


def _deferral_rows(conn: Any, months: list[str], payment_keys: set[str]) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT *
        FROM card_payment_deferrals
        WHERE from_payment_month IN ({months})
           OR target_payment_month IN ({months})
           OR entry_payment_key IN ({keys})
        ORDER BY target_payment_month, entry_payment_key
        """.format(months=",".join("?" for _ in months), keys=_placeholders(payment_keys)),
        (*tuple(months), *tuple(months), *tuple(payment_keys)),
    )


def _rows(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _insert_rows(conn: Any, table: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    allowed_columns = _table_columns(conn, table)
    normalized_rows = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{table} rows must be objects")
        unknown = set(row) - allowed_columns
        if unknown:
            raise ValueError(f"{table} has unsupported columns: {', '.join(sorted(unknown))}")
        normalized_rows.append({column: row.get(column) for column in allowed_columns if column in row})
    for row in normalized_rows:
        columns = list(row.keys())
        conn.execute(
            f"INSERT INTO {table}({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            tuple(row[column] for column in columns),
        )
    return len(normalized_rows)


def _validate_snapshot(snapshot: dict[str, Any]) -> None:
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("unsupported snapshot schema_version")
    if not isinstance(snapshot.get("range"), dict):
        raise ValueError("snapshot range is missing")
    data = snapshot.get("data")
    if not isinstance(data, dict):
        raise ValueError("snapshot data is missing")
    missing = [table for table in SNAPSHOT_TABLES if table not in data]
    if missing:
        raise ValueError(f"snapshot data is missing tables: {', '.join(missing)}")
    for table in SNAPSHOT_TABLES:
        if not isinstance(data[table], list):
            raise ValueError(f"{table} must be a list")
    for setting in data["app_settings"]:
        if setting.get("key") in SENSITIVE_SETTING_KEYS:
            raise ValueError("snapshot contains sensitive app_settings")


def _table_columns(conn: Any, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _recent_months(today: date, count: int) -> list[str]:
    year = today.year
    month = today.month
    months = []
    for _ in range(count):
        months.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    return list(reversed(months))


def _placeholders(values: set[Any]) -> str:
    if not values:
        return "NULL"
    return ",".join("?" for _ in values)

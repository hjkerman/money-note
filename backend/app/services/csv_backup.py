from __future__ import annotations

import base64
import csv
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any
from zipfile import BadZipFile, ZipFile

from app.db import session


BACKUP_TABLES = [
    "ledger_entries",
    "monthly_panels",
    "app_settings",
    "app_labels",
    "cash_flows",
    "installments",
    "card_payment_events",
    "card_payment_allocations",
    "card_payment_deferrals",
]

EXPORT_META_TABLE = "__meta"


def export_csv_backup() -> tuple[str, bytes]:
    """가계부 운용 데이터를 한 파일짜리 CSV dump로 내보낸다."""
    created_at = datetime.now().strftime("%Y%m%d-%H%M%S")
    with session() as conn:
        payload = _dump_to_single_csv(conn, created_at)
    return f"money-note-data-dump-{created_at}.csv", payload.encode("utf-8")


def import_csv_backup(encoded_payload: str) -> dict[str, int]:
    """CSV dump를 읽어 기존 가계부 운용 데이터를 교체한다."""
    try:
        payload = base64.b64decode(encoded_payload)
    except ValueError as exc:
        raise ValueError("invalid base64 backup payload") from exc

    csv_rows = _read_payload(payload)
    if not csv_rows:
        raise ValueError("backup has no supported CSV rows")

    imported: dict[str, int] = {}
    with session() as conn:
        # 기존 FK가 중간 삭제 순서 때문에 방해하지 않도록 복원 중에만 끈다.
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in reversed(BACKUP_TABLES):
            if table in csv_rows:
                conn.execute(f"DELETE FROM {table}")
        for table in BACKUP_TABLES:
            rows = csv_rows.get(table)
            if rows is None:
                continue
            columns = _table_columns(conn, table)
            _insert_csv_rows(conn, table, columns, rows)
            imported[table] = len(rows)
        conn.execute("PRAGMA foreign_keys = ON")
    return imported


def _dump_to_single_csv(conn: Any, created_at: str) -> str:
    table_columns = {table: _table_columns(conn, table) for table in BACKUP_TABLES}
    fieldnames = _dump_fieldnames(table_columns)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "__table": EXPORT_META_TABLE,
            "__key": "format",
            "__value": "money-note-data-dump",
        }
    )
    writer.writerow(
        {
            "__table": EXPORT_META_TABLE,
            "__key": "created_at",
            "__value": created_at,
        }
    )
    writer.writerow(
        {
            "__table": EXPORT_META_TABLE,
            "__key": "schema_policy",
            "__value": "tolerant",
        }
    )
    for table in BACKUP_TABLES:
        writer.writerow(
            {
                "__table": EXPORT_META_TABLE,
                "__key": "table",
                "__value": table,
            }
        )
    for table in BACKUP_TABLES:
        rows = conn.execute(f"SELECT * FROM {table} ORDER BY {_order_clause(table)}").fetchall()
        for row in rows:
            values = {column: "" for column in fieldnames}
            values["__table"] = table
            for column in table_columns[table]:
                values[column] = "" if row[column] is None else row[column]
            writer.writerow(values)
    return output.getvalue()


def _read_payload(payload: bytes) -> dict[str, list[dict[str, str]]]:
    if payload.startswith(b"PK"):
        return _read_legacy_zip(payload)
    text = payload.decode("utf-8-sig")
    return _rows_by_table(csv.DictReader(StringIO(text)))


def _read_legacy_zip(payload: bytes) -> dict[str, list[dict[str, str]]]:
    try:
        with ZipFile(BytesIO(payload), "r") as archive:
            rows: dict[str, list[dict[str, str]]] = {}
            for table in BACKUP_TABLES:
                filename = f"{table}.csv"
                if filename not in archive.namelist():
                    continue
                with archive.open(filename) as file:
                    text = file.read().decode("utf-8-sig")
                rows[table] = list(csv.DictReader(StringIO(text)))
            return rows
    except BadZipFile as exc:
        raise ValueError("invalid csv backup zip") from exc


def _rows_by_table(rows: csv.DictReader) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        table = row.get("__table") or row.get("table")
        if table == EXPORT_META_TABLE:
            if row.get("__key") == "table" and row.get("__value") in BACKUP_TABLES:
                grouped.setdefault(str(row["__value"]), [])
            continue
        if table not in BACKUP_TABLES:
            continue
        grouped.setdefault(table, []).append(_strip_dump_columns(row))
    return grouped


def _dump_fieldnames(table_columns: dict[str, list[str]]) -> list[str]:
    fieldnames = ["__table", "__key", "__value"]
    for columns in table_columns.values():
        for column in columns:
            if column not in fieldnames:
                fieldnames.append(column)
    return fieldnames


def _strip_dump_columns(row: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in row.items() if key not in {"__table", "table", "__key", "__value"}}


def _table_columns(conn: Any, table: str) -> list[str]:
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _order_clause(table: str) -> str:
    if table in {"app_settings", "app_labels"}:
        return "key"
    if table == "card_payment_deferrals":
        return "entry_payment_key"
    if table == "card_payment_allocations":
        return "id"
    return "id"


def _insert_csv_rows(conn: Any, table: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    input_columns = [column for column in columns if any(column in row for row in rows)]
    if not input_columns:
        return
    placeholders = ", ".join("?" for _ in input_columns)
    column_list = ", ".join(input_columns)
    values = [
        tuple(_csv_value(row.get(column)) for column in input_columns)
        for row in rows
    ]
    conn.executemany(
        f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",
        values,
    )


def _csv_value(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return value

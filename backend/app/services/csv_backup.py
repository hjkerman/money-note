from __future__ import annotations

import base64
import csv
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

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


def export_csv_backup() -> tuple[str, bytes]:
    """가계부 운용 데이터만 CSV 묶음으로 내보낸다."""
    created_at = datetime.now().strftime("%Y%m%d-%H%M%S")
    buffer = BytesIO()
    with session() as conn, ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.csv",
            "key,value\nformat,money-note-csv-backup\ncreated_at,"
            f"{created_at}\ntables,{';'.join(BACKUP_TABLES)}\n",
        )
        for table in BACKUP_TABLES:
            columns = _table_columns(conn, table)
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY {_order_clause(table)}").fetchall()
            archive.writestr(f"{table}.csv", _rows_to_csv(columns, rows))
    return f"money-note-csv-backup-{created_at}.zip", buffer.getvalue()


def import_csv_backup(encoded_zip: str) -> dict[str, int]:
    """CSV backup zip을 읽어 기존 가계부 운용 데이터를 교체한다."""
    try:
        payload = base64.b64decode(encoded_zip)
    except ValueError as exc:
        raise ValueError("invalid base64 backup payload") from exc

    try:
        with ZipFile(BytesIO(payload), "r") as archive:
            csv_rows = {
                table: _read_table_csv(archive, table)
                for table in BACKUP_TABLES
                if f"{table}.csv" in archive.namelist()
            }
    except BadZipFile as exc:
        raise ValueError("invalid csv backup zip") from exc

    if not csv_rows:
        raise ValueError("backup has no supported CSV tables")

    imported: dict[str, int] = {}
    with session() as conn:
        # 기존 FK가 중간 삭제 순서 때문에 방해하지 않도록 복원 중에만 끈다.
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in reversed(BACKUP_TABLES):
            if table in csv_rows:
                conn.execute(f"DELETE FROM {table}")
        for table in BACKUP_TABLES:
            if table not in csv_rows:
                continue
            columns = _table_columns(conn, table)
            rows = csv_rows[table]
            _insert_csv_rows(conn, table, columns, rows)
            imported[table] = len(rows)
        conn.execute("PRAGMA foreign_keys = ON")
    return imported


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


def _rows_to_csv(columns: list[str], rows: list[Any]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: "" if row[column] is None else row[column] for column in columns})
    return output.getvalue()


def _read_table_csv(archive: ZipFile, table: str) -> list[dict[str, str]]:
    with archive.open(f"{table}.csv") as file:
        text = file.read().decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    return list(reader)


def _insert_csv_rows(conn: Any, table: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    placeholders = ", ".join("?" for _ in columns)
    column_list = ", ".join(columns)
    values = [
        tuple(_csv_value(row.get(column)) for column in columns)
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

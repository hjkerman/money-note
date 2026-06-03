from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.db import init_db, session
from app.services.workbook import import_workbook


ENTRY_COLUMNS = [
    "book_section",
    "entry_kind",
    "entry_date",
    "date_label",
    "group_label",
    "title",
    "amount_value",
    "amount_expr",
    "aux_amount_value",
    "aux_amount_expr",
    "extra_value",
    "sort_order",
]

ARCHIVE_ROW_COLUMNS = [
    "source_row",
    "b_value",
    "c_value",
    "d_value",
    "e_value",
    "f_value",
    "merge_down",
    "sort_order",
]

PANEL_COLUMNS = [
    "month",
    "panel_type",
    "title",
    "amount_value",
    "amount_expr",
    "sort_order",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("xlsx", type=Path)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    parsed = import_workbook(args.xlsx)
    init_db()

    with session() as conn:
        if args.replace:
            conn.execute("DELETE FROM ledger_entries")
            conn.execute("DELETE FROM archive_rows")
            conn.execute("DELETE FROM monthly_panels")
            conn.execute("DELETE FROM workbook_labels")
        _insert_many(conn, "ledger_entries", ENTRY_COLUMNS, parsed.current_entries)
        _insert_many(conn, "archive_rows", ARCHIVE_ROW_COLUMNS, parsed.archive_rows)
        _insert_many(conn, "monthly_panels", PANEL_COLUMNS, parsed.panels)
        for key, value in parsed.settings.items():
            conn.execute(
                """
                INSERT INTO app_settings(key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
        for key, value in parsed.labels.items():
            conn.execute(
                """
                INSERT INTO workbook_labels(key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )

    print(
        f"imported {len(parsed.archive_rows)} hard archive rows, "
        f"{len(parsed.current_entries)} current entries, "
        f"{len(parsed.panels)} panels, {len(parsed.settings)} settings, "
        f"{len(parsed.labels)} labels"
    )


def _insert_many(
    conn: sqlite3.Connection,
    table: str,
    columns: list[str],
    records: list[dict],
) -> None:
    placeholders = ", ".join("?" for _ in columns)
    column_list = ", ".join(columns)
    conn.executemany(
        f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})",
        [tuple(record.get(column) for column in columns) for record in records],
    )


if __name__ == "__main__":
    main()

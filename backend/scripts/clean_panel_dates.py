from __future__ import annotations

import argparse
from pathlib import Path
import re
import sqlite3


DATE_PREFIX = re.compile(r"^\s*[\[\(]?\s*(\d{1,2})\s*/\s*(\d{1,2})(?:[^\]\)]*)[\]\)]?\s*")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/money-note.sqlite3"))
    parser.add_argument("--year", type=int, default=2026)
    args = parser.parse_args()

    with sqlite3.connect(args.db) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_columns(conn)
        rows = conn.execute(
            """
            SELECT id, title
            FROM monthly_panels
            WHERE panel_type IN ('claim', 'settlement')
            ORDER BY id
            """
        ).fetchall()
        changed = 0
        for row in rows:
            match = DATE_PREFIX.match(row["title"] or "")
            if not match:
                continue
            month = int(match.group(1))
            day = int(match.group(2))
            if not (1 <= month <= 12 and 1 <= day <= 31):
                continue
            cleaned_title = (row["title"] or "")[match.end() :].strip()
            conn.execute(
                """
                UPDATE monthly_panels
                SET spent_on = ?, title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (f"{args.year:04d}-{month:02d}-{day:02d}", cleaned_title, row["id"]),
            )
            changed += 1
    print(f"cleaned {changed} monthly panel titles")


def _ensure_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(monthly_panels)").fetchall()}
    if "discount_amount" not in columns:
        conn.execute("ALTER TABLE monthly_panels ADD COLUMN discount_amount REAL NOT NULL DEFAULT 0")
    if "spent_on" not in columns:
        conn.execute("ALTER TABLE monthly_panels ADD COLUMN spent_on TEXT")


if __name__ == "__main__":
    main()

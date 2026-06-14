from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any

from app.config import get_settings
from app.db import SCHEMA, session
from app.services.snapshot import PRE_RESTORE_BACKUP_DIR, PRE_RESTORE_FILENAME_RE


def operation_data_stats() -> dict[str, Any]:
    """운영 데이터 크기와 테이블별 row count를 조회한다."""
    db_path = Path(get_settings().db_path)
    db_file_size = db_path.stat().st_size if db_path.exists() else 0
    empty_db_size = _empty_sqlite_size()
    pre_restore = _pre_restore_size_stats(db_path.parent / PRE_RESTORE_BACKUP_DIR)
    with session() as conn:
        table_counts = {
            table: int(conn.execute(f'SELECT COUNT(*) AS count FROM "{table}"').fetchone()["count"])
            for table in _user_tables(conn)
        }
    return {
        "db_file_size_bytes": db_file_size,
        "empty_db_size_bytes": empty_db_size,
        "estimated_data_size_bytes": max(0, db_file_size - empty_db_size),
        "pre_restore_total_size_bytes": pre_restore["total_size_bytes"],
        "pre_restore_count": pre_restore["count"],
        "table_row_counts": table_counts,
    }


def _user_tables(conn: Any) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(row["name"]) for row in rows]


def _empty_sqlite_size() -> int:
    fd, path_text = tempfile.mkstemp(prefix="money-note-empty-", suffix=".sqlite3")
    os.close(fd)
    path = Path(path_text)
    try:
        conn = sqlite3.connect(path)
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()
        return path.stat().st_size
    finally:
        path.unlink(missing_ok=True)


def _pre_restore_size_stats(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"count": 0, "total_size_bytes": 0}
    files = [
        item
        for item in path.iterdir()
        if item.is_file() and PRE_RESTORE_FILENAME_RE.fullmatch(item.name)
    ]
    return {
        "count": len(files),
        "total_size_bytes": sum(item.stat().st_size for item in files),
    }

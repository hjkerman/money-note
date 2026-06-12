from __future__ import annotations

import json
import hashlib
import os
import re
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import tempfile
from datetime import date, datetime, timezone
from typing import Any

from app.config import get_settings
from app.db import SCHEMA, session


SNAPSHOT_SCHEMA_VERSION = 2
SENSITIVE_SETTING_KEYS = {"share_pin_hash", "share_pin_is_default"}
PRE_RESTORE_FILENAME_RE = re.compile(r"^pre_restore-\d{8}T\d{6}Z(?:-\d+)?\.money-note-snapshot\.json$")
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
LEGACY_SNAPSHOT_COLUMNS = {
    "ledger_entries": {"discount_checked"},
    "monthly_panels": {"discount_checked"},
}
LEDGER_TABLES = [
    "card_payment_deferrals",
    "card_payment_allocations",
    "card_payment_events",
    "installments",
    "cash_flows",
    "monthly_panels",
    "ledger_entries",
]
PRE_RESTORE_BACKUP_DIR = "snapshot-backups"


def export_snapshot(today: date | None = None) -> tuple[str, dict[str, Any]]:
    """장부 운용 데이터 전체와 비민감 운영 설정을 JSON snapshot으로 만든다."""
    with session() as conn:
        data = {
            "ledger_entries": _snapshot_rows(
                conn,
                "ledger_entries",
                "book_section, entry_kind, entry_date, sort_order, id",
            ),
            "monthly_panels": _snapshot_rows(conn, "monthly_panels", "month, panel_type, sort_order, id"),
            "cash_flows": _snapshot_rows(conn, "cash_flows", "occurred_on, sort_order, id"),
            "installments": _snapshot_rows(conn, "installments", "is_active DESC, start_month, sort_order, id"),
            "card_payment_events": _snapshot_rows(conn, "card_payment_events", "event_date, id"),
            "card_payment_allocations": _snapshot_rows(conn, "card_payment_allocations", "payment_event_id, id"),
            "card_payment_deferrals": _snapshot_rows(
                conn,
                "card_payment_deferrals",
                "target_payment_month, entry_payment_key",
            ),
            "app_settings": _snapshot_rows(
                conn,
                "app_settings",
                "key",
                where="key NOT IN ({})".format(",".join("?" for _ in SENSITIVE_SETTING_KEYS)),
                params=tuple(SENSITIVE_SETTING_KEYS),
            ),
            "app_labels": _snapshot_rows(conn, "app_labels", "key"),
        }
    exported_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "exported_at": exported_at,
        "range": {"scope": "all"},
        "data": data,
    }
    snapshot["manifest"] = _build_manifest(data)
    snapshot["snapshot_id"] = snapshot["manifest"]["data_sha256"]
    filename = f"money-note-snapshot-{exported_at.replace(':', '').replace('-', '')}.money-note-snapshot.json"
    return filename, snapshot


def restore_snapshot(snapshot: dict[str, Any]) -> dict[str, int]:
    """JSON snapshot을 검증하고 임시 복원에 성공한 뒤 운영 DB를 교체한다."""
    _validate_snapshot(snapshot)
    data = _normalized_snapshot_data(snapshot["data"])
    _dry_run_restore(data)
    _write_pre_restore_backup()
    restored: dict[str, int] = {}
    with session() as conn:
        restored = _replace_snapshot_tables(conn, data)
        _raise_if_foreign_key_errors(conn)
    return restored


def list_pre_restore_backups() -> list[dict[str, Any]]:
    """서버에 보관된 restore 직전 snapshot 목록을 최신순으로 돌려준다."""
    backup_dir = _pre_restore_backup_dir()
    if not backup_dir.exists():
        return []
    items = []
    for path in sorted(backup_dir.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_file() or not PRE_RESTORE_FILENAME_RE.fullmatch(path.name):
            continue
        try:
            snapshot = _read_snapshot_file(path)
        except ValueError:
            continue
        stat = path.stat()
        items.append(
            {
                "filename": path.name,
                "created_at": _timestamp_to_iso(stat.st_mtime),
                "size_bytes": stat.st_size,
                "snapshot_id": snapshot.get("snapshot_id") or snapshot["manifest"]["data_sha256"],
                "exported_at": snapshot.get("exported_at"),
            },
        )
    return items


def read_pre_restore_backup(filename: str) -> tuple[str, dict[str, Any]]:
    """검증된 pre_restore snapshot 파일을 읽는다."""
    path = _pre_restore_path(filename)
    return path.name, _read_snapshot_file(path)


def restore_pre_restore_backup(filename: str) -> dict[str, int]:
    """pre_restore 파일을 일반 snapshot과 동일한 절차로 복원한다."""
    _, snapshot = read_pre_restore_backup(filename)
    return restore_snapshot(snapshot)


def _rows(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _snapshot_rows(
    conn: Any,
    table: str,
    order_by: str,
    where: str | None = None,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    columns = [column for column in _schema_columns(table) if column in _table_columns(conn, table)]
    column_sql = ", ".join(f'"{column}"' for column in columns)
    where_sql = f" WHERE {where}" if where else ""
    return _rows(conn, f"SELECT {column_sql} FROM {table}{where_sql} ORDER BY {order_by}", params)


def _replace_snapshot_tables(conn: Any, data: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    restored: dict[str, int] = {}
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
        for row in data[table]:
            if not isinstance(row, dict):
                raise ValueError(f"{table} rows must be objects")
    for setting in data["app_settings"]:
        if setting.get("key") in SENSITIVE_SETTING_KEYS:
            raise ValueError("snapshot contains sensitive app_settings")
    manifest = snapshot.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError("snapshot manifest is missing")
    expected_manifest = _build_manifest(data)
    if manifest != expected_manifest:
        raise ValueError("snapshot manifest mismatch")


def _normalized_snapshot_data(data: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    for table in SNAPSHOT_TABLES:
        ignored = LEGACY_SNAPSHOT_COLUMNS.get(table, set())
        normalized[table] = [{key: value for key, value in row.items() if key not in ignored} for row in data[table]]
    return normalized


def _table_columns(conn: Any, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _build_manifest(data: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tables = {}
    for table in SNAPSHOT_TABLES:
        rows = data.get(table)
        if not isinstance(rows, list):
            raise ValueError(f"{table} must be a list")
        columns = _snapshot_columns(table, rows)
        for row in rows:
            row_columns = sorted(row.keys())
            if row_columns != columns:
                raise ValueError(f"{table} rows must contain the exact snapshot columns")
        tables[table] = {
            "columns": columns,
            "row_count": len(rows),
            "sha256": _stable_hash(rows),
        }
    return {
        "algorithm": "sha256",
        "tables": tables,
        "data_sha256": _stable_hash({table: data[table] for table in SNAPSHOT_TABLES}),
    }


def _snapshot_columns(table: str, rows: list[dict[str, Any]]) -> list[str]:
    if rows:
        return sorted(rows[0].keys())
    return _schema_columns(table)


def _schema_columns(table: str) -> list[str]:
    with _schema_connection() as conn:
        return sorted(_table_columns(conn, table))


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _dry_run_restore(data: dict[str, list[dict[str, Any]]]) -> None:
    with _schema_connection() as conn:
        _replace_snapshot_tables(conn, data)
        _raise_if_foreign_key_errors(conn)


@contextmanager
def _schema_connection() -> Any:
    conn = sqlite3.connect(":memory:")
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        yield conn
    finally:
        conn.close()


def _raise_if_foreign_key_errors(conn: Any) -> None:
    errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if errors:
        raise ValueError("snapshot foreign key check failed")


def _write_pre_restore_backup() -> Path:
    filename, snapshot = export_snapshot()
    backup_dir = _pre_restore_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = _unique_pre_restore_path(backup_dir / filename.replace("money-note-snapshot-", "pre_restore-"))
    _write_json_atomic(target, snapshot)
    _validate_snapshot(json.loads(target.read_text(encoding="utf-8")))
    return target


def _read_snapshot_file(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ValueError("pre_restore backup not found")
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("pre_restore backup is not valid JSON") from exc
    _validate_snapshot(snapshot)
    return snapshot


def _pre_restore_backup_dir() -> Path:
    return Path(get_settings().db_path).parent / PRE_RESTORE_BACKUP_DIR


def _pre_restore_path(filename: str) -> Path:
    if not PRE_RESTORE_FILENAME_RE.fullmatch(filename):
        raise ValueError("invalid pre_restore filename")
    backup_dir = _pre_restore_backup_dir().resolve()
    path = (backup_dir / filename).resolve()
    if path.parent != backup_dir:
        raise ValueError("invalid pre_restore path")
    return path


def _unique_pre_restore_path(target: Path) -> Path:
    if not target.exists():
        return target
    suffix = ".money-note-snapshot.json"
    base = target.name[: -len(suffix)]
    for index in range(2, 1000):
        candidate = target.with_name(f"{base}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise ValueError("too many pre_restore backups created in the same second")


def _timestamp_to_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json_atomic(target: Path, payload: dict[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        json.loads(tmp_path.read_text(encoding="utf-8"))
        os.replace(tmp_path, target)
        _fsync_directory(target.parent)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        finally:
            raise


def _fsync_directory(path: Path) -> None:
    if not hasattr(os, "O_DIRECTORY"):
        return
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

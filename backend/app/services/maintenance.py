from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db import session
from app.services.snapshot import delete_pre_restore_backup, list_pre_restore_backups


def run_startup_maintenance(audit_retention_days: int, pre_restore_keep_count: int) -> None:
    """만료 세션과 오래된 운영 보조 자료만 정리한다. 장부 데이터는 건드리지 않는다."""
    now = datetime.now(timezone.utc)
    expires_at = _datetime_to_db(now)
    audit_cutoff = _datetime_to_db(now - timedelta(days=audit_retention_days))
    with session() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (expires_at,))
        conn.execute("DELETE FROM share_sessions WHERE expires_at <= ?", (expires_at,))
        conn.execute("DELETE FROM audit_logs WHERE occurred_at < ?", (audit_cutoff,))

    backups = list_pre_restore_backups()
    for item in backups[pre_restore_keep_count:]:
        delete_pre_restore_backup(str(item["filename"]))


def _datetime_to_db(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

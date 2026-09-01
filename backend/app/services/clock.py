from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.config import get_settings


def app_timezone() -> timezone:
    return timezone(timedelta(minutes=get_settings().timezone_offset_minutes))


def app_today() -> date:
    """앱 전체가 공유하는 오늘 날짜다. 개발 테스트에서는 MONEY_NOTE_TODAY로 덮어쓴다."""
    settings = get_settings()
    override = settings.today_override
    if override:
        return date.fromisoformat(override)
    return datetime.now(app_timezone()).date()


def app_today_iso() -> str:
    return app_today().isoformat()


def app_month() -> str:
    return app_today().strftime("%Y-%m")


def app_month_for_utc_timestamp(value: str) -> str:
    """SQLite CURRENT_TIMESTAMP(UTC)를 앱 달력 기준 YYYY-MM로 바꾼다."""
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(app_timezone()).strftime("%Y-%m")

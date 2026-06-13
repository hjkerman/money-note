from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.config import get_settings


def app_today() -> date:
    """앱 전체가 공유하는 오늘 날짜다. 개발 테스트에서는 MONEY_NOTE_TODAY로 덮어쓴다."""
    settings = get_settings()
    override = settings.today_override
    if override:
        return date.fromisoformat(override)
    tz = timezone(timedelta(minutes=settings.timezone_offset_minutes))
    return datetime.now(tz).date()


def app_today_iso() -> str:
    return app_today().isoformat()


def app_month() -> str:
    return app_today().strftime("%Y-%m")

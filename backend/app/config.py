from functools import lru_cache
import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.db_path = Path(os.getenv("MONEY_NOTE_DB_PATH", "data/money-note.sqlite3"))
        self.session_cookie_name = os.getenv("MONEY_NOTE_SESSION_COOKIE_NAME", "money_note_session")
        self.session_days = int(os.getenv("MONEY_NOTE_SESSION_DAYS", "30"))
        self.cookie_secure = os.getenv("MONEY_NOTE_COOKIE_SECURE", "false").lower() == "true"
        self.today_override = os.getenv("MONEY_NOTE_TODAY", "").strip()
        self.timezone_offset_minutes = int(os.getenv("MONEY_NOTE_TIMEZONE_OFFSET_MINUTES", "540"))
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv(
                "MONEY_NOTE_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.db_path = Path(os.getenv("MONEY_NOTE_DB_PATH", "data/money-note.sqlite3"))
        self.export_dir = Path(os.getenv("MONEY_NOTE_EXPORT_DIR", "exports"))
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv(
                "MONEY_NOTE_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ]
        template_path = os.getenv("MONEY_NOTE_TEMPLATE_PATH")
        self.template_path = Path(template_path) if template_path else None


@lru_cache
def get_settings() -> Settings:
    return Settings()

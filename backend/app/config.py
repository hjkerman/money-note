from functools import lru_cache
import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.db_path = Path(os.getenv("MONEY_NOTE_DB_PATH", "data/money-note.sqlite3"))
        self.export_dir = Path(os.getenv("MONEY_NOTE_EXPORT_DIR", "exports"))
        template_path = os.getenv("MONEY_NOTE_TEMPLATE_PATH")
        self.template_path = Path(template_path) if template_path else None


@lru_cache
def get_settings() -> Settings:
    return Settings()

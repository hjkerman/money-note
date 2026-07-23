from functools import lru_cache
import os
from pathlib import Path
from urllib.parse import urlsplit


class Settings:
    def __init__(self) -> None:
        self.db_path = Path(os.getenv("MONEY_NOTE_DB_PATH", "data/money-note.sqlite3"))
        self.session_cookie_name = os.getenv("MONEY_NOTE_SESSION_COOKIE_NAME", "money_note_session")
        self.session_days = int(os.getenv("MONEY_NOTE_SESSION_DAYS", "30"))
        self.mobile_session_days = int(os.getenv("MONEY_NOTE_MOBILE_SESSION_DAYS", "3650"))
        self.cookie_secure = os.getenv("MONEY_NOTE_COOKIE_SECURE", "false").lower() == "true"
        self.login_max_failures = int(os.getenv("MONEY_NOTE_LOGIN_MAX_FAILURES", "5"))
        self.login_window_seconds = int(os.getenv("MONEY_NOTE_LOGIN_WINDOW_SECONDS", "300"))
        self.share_pin_max_failures = int(os.getenv("MONEY_NOTE_SHARE_PIN_MAX_FAILURES", "10"))
        self.share_pin_window_seconds = int(os.getenv("MONEY_NOTE_SHARE_PIN_WINDOW_SECONDS", "600"))
        self.api_request_max_bytes = int(
            os.getenv("MONEY_NOTE_API_REQUEST_MAX_BYTES", str(1024 * 1024))
        )
        self.snapshot_restore_max_bytes = int(
            os.getenv("MONEY_NOTE_SNAPSHOT_RESTORE_MAX_BYTES", str(25 * 1024 * 1024))
        )
        self.audit_log_retention_days = int(
            os.getenv("MONEY_NOTE_AUDIT_LOG_RETENTION_DAYS", "180")
        )
        self.pre_restore_keep_count = int(
            os.getenv("MONEY_NOTE_PRE_RESTORE_KEEP_COUNT", "30")
        )
        self.trust_proxy_headers = (
            os.getenv("MONEY_NOTE_TRUST_PROXY_HEADERS", "true").lower() == "true"
        )
        self.today_override = os.getenv("MONEY_NOTE_TODAY", "").strip()
        self.timezone_offset_minutes = int(os.getenv("MONEY_NOTE_TIMEZONE_OFFSET_MINUTES", "540"))
        apk_path = os.getenv("MONEY_NOTE_APK_PATH", "").strip()
        self.apk_path = Path(apk_path) if apk_path else None
        self.apk_filename = os.getenv("MONEY_NOTE_APK_FILENAME", "money-note.apk").strip() or "money-note.apk"
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv(
                "MONEY_NOTE_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ]

    def validate_runtime(self) -> None:
        """운영 주소를 쓰면서 개발용 보안 설정을 켠 실수를 기동 전에 막는다."""
        positive_values = {
            "MONEY_NOTE_SESSION_DAYS": self.session_days,
            "MONEY_NOTE_MOBILE_SESSION_DAYS": self.mobile_session_days,
            "MONEY_NOTE_LOGIN_MAX_FAILURES": self.login_max_failures,
            "MONEY_NOTE_LOGIN_WINDOW_SECONDS": self.login_window_seconds,
            "MONEY_NOTE_SHARE_PIN_MAX_FAILURES": self.share_pin_max_failures,
            "MONEY_NOTE_SHARE_PIN_WINDOW_SECONDS": self.share_pin_window_seconds,
            "MONEY_NOTE_API_REQUEST_MAX_BYTES": self.api_request_max_bytes,
            "MONEY_NOTE_SNAPSHOT_RESTORE_MAX_BYTES": self.snapshot_restore_max_bytes,
            "MONEY_NOTE_AUDIT_LOG_RETENTION_DAYS": self.audit_log_retention_days,
            "MONEY_NOTE_PRE_RESTORE_KEEP_COUNT": self.pre_restore_keep_count,
        }
        invalid = [name for name, value in positive_values.items() if value <= 0]
        if invalid:
            raise RuntimeError(f"settings must be positive: {', '.join(invalid)}")
        if "*" in self.cors_origins:
            raise RuntimeError("MONEY_NOTE_CORS_ORIGINS must list explicit origins")
        malformed_origins = [
            origin
            for origin in self.cors_origins
            if urlsplit(origin).scheme not in {"http", "https"}
            or not urlsplit(origin).netloc
        ]
        if malformed_origins:
            raise RuntimeError(
                f"invalid MONEY_NOTE_CORS_ORIGINS: {', '.join(malformed_origins)}"
            )

        production_https = any(_is_production_https_origin(origin) for origin in self.cors_origins)
        if production_https and not self.cookie_secure:
            raise RuntimeError(
                "MONEY_NOTE_COOKIE_SECURE=true is required for a production HTTPS origin"
            )
        if production_https and self.today_override:
            raise RuntimeError("MONEY_NOTE_TODAY must be empty in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def _is_production_https_origin(origin: str) -> bool:
    parsed = urlsplit(origin)
    return (
        parsed.scheme == "https"
        and parsed.hostname not in {None, "localhost", "127.0.0.1", "::1"}
    )

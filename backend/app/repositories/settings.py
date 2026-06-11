from app.db import session


def list_settings() -> dict[str, str]:
    with session() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}

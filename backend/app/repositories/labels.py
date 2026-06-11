from app.db import session


def list_labels() -> dict[str, str]:
    with session() as conn:
        rows = conn.execute("SELECT key, value FROM app_labels ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


def upsert_label(key: str, value: str) -> dict[str, str]:
    with session() as conn:
        conn.execute(
            """
            INSERT INTO app_labels(key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
    return {key: value}

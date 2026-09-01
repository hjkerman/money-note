from app.db import session


def list_settings(conn=None) -> dict[str, str]:
    if conn is None:
        with session() as owned_conn:
            return list_settings(owned_conn)
    rows = conn.execute("SELECT key, value FROM app_settings ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}

from __future__ import annotations

import argparse
import sqlite3

from app.auth import create_user, hash_password
from app.db import init_db, session


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--display-name", default="")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    init_db()
    with session() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (args.username,),
        ).fetchone()
        if existing and not args.replace:
            raise SystemExit(f"user already exists: {args.username}")
        if existing and args.replace:
            conn.execute(
                """
                UPDATE users
                SET password_hash = ?, display_name = ?, is_active = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE username = ?
                """,
                (
                    hash_password(args.password),
                    args.display_name or args.username,
                    args.username,
                ),
            )
            print(f"updated user: {args.username}")
            return

    try:
        user = create_user(args.username, args.password, args.display_name)
    except sqlite3.IntegrityError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"created user: {user['username']}")


if __name__ == "__main__":
    main()

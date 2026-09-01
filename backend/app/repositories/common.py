from typing import Any
from uuid import uuid4


def row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def ensure_payment_key_available(conn: Any, payment_key: str) -> None:
    duplicate = conn.execute(
        "SELECT 1 FROM ledger_entries WHERE payment_key = ? LIMIT 1",
        (payment_key,),
    ).fetchone()
    if duplicate is not None:
        raise ValueError("이미 사용 중인 카드 결제 식별자입니다.")


def new_payment_key(conn: Any) -> str:
    for _ in range(10):
        payment_key = uuid4().hex
        if conn.execute(
            "SELECT 1 FROM ledger_entries WHERE payment_key = ? LIMIT 1",
            (payment_key,),
        ).fetchone() is None:
            return payment_key
    raise RuntimeError("고유한 카드 결제 식별자를 생성하지 못했습니다.")

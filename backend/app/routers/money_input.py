"""Raw-token preflight for the existing authoritative integer-money inputs."""

import json
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, Request

from app.schemas import integer_money


MONEY_INPUT_FIELDS = {
    "amount_value", "aux_amount_value", "actual_amount",
    "discount_amount", "discount_override_amount",
}


async def read_request_body(request: Request) -> bytes:
    return await request.body()


def validate_financial_json_money(contents: str | bytes) -> None:
    """No body rewriting: identity/digests and normal model validation remain unchanged."""
    if not contents:
        return
    decoded = json.loads(contents)
    exact = json.loads(contents, parse_float=Decimal)

    def check(raw, parsed):
        if not isinstance(raw, dict) or not isinstance(parsed, dict):
            return
        for field in MONEY_INPUT_FIELDS & raw.keys():
            if integer_money(raw[field]) != integer_money(parsed[field]):
                raise ValueError(f"{field} loses precision during JSON decoding")
        raw_allocations, allocations = raw.get("allocations"), parsed.get("allocations")
        if isinstance(raw_allocations, list) and isinstance(allocations, list):
            for raw_row, row in zip(raw_allocations, allocations, strict=True):
                check(raw_row, row)

    check(exact, decoded)
    # The ordered Offline journal uses these same accepted command inputs.
    # Snapshot tables have their separate, version-aware import preflight.
    if isinstance(exact, dict) and isinstance(exact.get("operations"), list):
        for raw_operation, operation in zip(exact["operations"], decoded["operations"], strict=True):
            if isinstance(raw_operation, dict) and isinstance(operation, dict):
                check(raw_operation.get("payload"), operation.get("payload"))


async def require_lossless_money_body(request: Request) -> None:
    if request.method not in {"POST", "PATCH", "PUT"}:
        return
    try:
        validate_financial_json_money(await request.body())
    except (ValueError, InvalidOperation) as exc:
        raise HTTPException(status_code=422, detail=f"money input must be a lossless integer amount: {exc}") from exc

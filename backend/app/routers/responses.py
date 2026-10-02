"""Prepare application response bytes before the financial transaction commits.

Returning a Response bypasses FastAPI's later model serialization. Only socket
delivery remains outside the transaction; it is inherently an ambiguous result.
"""

from typing import Any

from pydantic import TypeAdapter
from starlette.responses import JSONResponse


def financial_response(content: Any, *, response_type: Any | None = None) -> JSONResponse:
    if response_type is not None:
        adapter = TypeAdapter(response_type)
        content = adapter.dump_python(adapter.validate_python(content), mode="json")
    return JSONResponse(content=content)

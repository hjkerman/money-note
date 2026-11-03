"""Negotiated coding of two already-completed JSON GET responses only."""

import gzip
import re

from starlette.requests import Request
from starlette.responses import Response


_PATHS = frozenset({"/api/admin/snapshot", "/api/authoritative-state"})
_QVALUE = re.compile(r"(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)\Z")


def _qualities(value: str) -> tuple[int, int]:
    """Return gzip/identity weights. Malformed or conflicting entries fail closed.

    Unlisted identity is acceptable except under an explicit wildcard exclusion.
    Duplicate entries use the lowest weight so explicit rejection always wins.
    """
    weights: dict[str, int] = {}
    for entry in value.split(","):
        parts = [part.strip().lower() for part in entry.split(";")]
        coding = parts[0]
        if not coding:
            continue
        weight = 1000
        if len(parts) > 1:
            if len(parts) != 2 or not parts[1].startswith("q=") or not _QVALUE.fullmatch(parts[1][2:]):
                weight = 0
            else:
                weight = int(float(parts[1][2:]) * 1000 + 0.5)
        weights[coding] = min(weights.get(coding, 1000), weight)
    return (
        weights.get("gzip", weights.get("*", 0)),
        weights.get("identity", 0 if weights.get("*") == 0 else 1000),
    )


def _vary(response: Response) -> None:
    values = response.headers.getlist("vary")
    tokens = [token.strip() for value in values for token in value.split(",") if token.strip()]
    if not any(token.lower() in {"accept-encoding", "*"} for token in tokens):
        response.headers["Vary"] = ", ".join([*tokens, "Accept-Encoding"])


def _empty(response: Response, status: int) -> Response:
    # No financial body, attachment, partial gzip, or forbidden identity body.
    return Response(status_code=status, headers={
        key: response.headers[key]
        for key in ("vary", "cache-control", "pragma") if key in response.headers
    })


def code_json_response(request: Request, response: Response) -> Response:
    body = getattr(response, "body", None)
    media_type = response.headers.get("content-type", "").partition(";")[0].strip().lower()
    if (request.method != "GET" or request.url.path not in _PATHS
            or response.status_code != 200 or not isinstance(body, bytes)
            or not (media_type == "application/json" or media_type.endswith("+json"))
            or "content-encoding" in response.headers):
        return response

    _vary(response)
    gzip_q, identity_q = _qualities(",".join(request.headers.getlist("accept-encoding")))
    if len(body) < 1024 or gzip_q == 0 or gzip_q < identity_q:
        return response if identity_q else _empty(response, 406)

    try:
        encoded = gzip.compress(body, compresslevel=6, mtime=0)
    except Exception:
        # Compression happens before any response bytes are sent.
        return response if identity_q else _empty(response, 503)
    response.body = encoded
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Content-Length"] = str(len(encoded))
    return response

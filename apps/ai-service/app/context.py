from __future__ import annotations

import re
import uuid
from contextvars import ContextVar, Token
from typing import Final

from fastapi import Request

REQUEST_ID_HEADER: Final[str] = "X-Request-Id"
MAX_INCOMING_REQUEST_ID_LENGTH: Final[int] = 64

CANONICAL_UUID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_request_id_ctx: ContextVar[str | None] = ContextVar("smart_catering_request_id", default=None)


def normalize_or_generate_request_id(raw_value: str | None) -> str:
    """Preserve canonical UUID (v1-v8, RFC variant) in lowercase, else generate UUIDv4."""
    if raw_value is None or len(raw_value) > MAX_INCOMING_REQUEST_ID_LENGTH:
        return str(uuid.uuid4())

    candidate = raw_value.strip()
    if not candidate:
        return str(uuid.uuid4())

    if not CANONICAL_UUID_PATTERN.match(candidate):
        return str(uuid.uuid4())

    return candidate.lower()


def set_current_request_id(request_id: str) -> Token[str | None]:
    """Bind requestId to the active async context."""
    return _request_id_ctx.set(request_id)


def reset_current_request_id(token: Token[str | None]) -> None:
    """Restore previous requestId context token."""
    _request_id_ctx.reset(token)


def get_request_id(request: Request | None = None) -> str:
    """Retrieve the single canonical requestId for the current request lifecycle."""
    if request is not None:
        state_dict = request.scope.get("state")
        if isinstance(state_dict, dict):
            existing = state_dict.get("request_id")
            if isinstance(existing, str) and existing:
                return existing

    ctx_value = _request_id_ctx.get()
    if isinstance(ctx_value, str) and ctx_value:
        if request is not None:
            state_dict = request.scope.setdefault("state", {})
            if isinstance(state_dict, dict):
                state_dict["request_id"] = ctx_value
        return ctx_value

    raw_header = request.headers.get("x-request-id") if request is not None else None
    resolved = normalize_or_generate_request_id(raw_header)
    if request is not None:
        state_dict = request.scope.setdefault("state", {})
        if isinstance(state_dict, dict):
            state_dict["request_id"] = resolved
    _request_id_ctx.set(resolved)
    return resolved

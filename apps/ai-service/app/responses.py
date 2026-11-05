from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.context import get_request_id
from app.pagination import DEFAULT_LIMIT, DEFAULT_PAGE, build_pagination_meta
from app.schemas import ApiMeta, PaginationMeta


def _response_headers(request_id: str, headers: Mapping[str, str] | None) -> dict[str, str]:
    custom_headers = {
        key.lower(): value
        for key, value in (headers or {}).items()
        if key.lower() not in {"content-type", "content-length", "x-request-id"}
    }
    return {"cache-control": "no-store", **custom_headers, "x-request-id": request_id}


def create_success_response(
    request: Request,
    data: Any,
    *,
    status_code: Literal[200, 201] = 200,
    pagination: PaginationMeta | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Wrap a payload once; routes return this response directly without forwarding it again."""
    if status_code not in (200, 201):
        raise ValueError("Use HTTP 200 or 201 for JSON success; use the no-content helper for 204")
    if isinstance(data, Response):
        raise TypeError("Pass the response payload, not an existing Response")
    request_id = get_request_id(request)
    meta = ApiMeta(requestId=request_id, pagination=pagination)
    return JSONResponse(
        status_code=status_code,
        content={"data": jsonable_encoder(data), "meta": meta.model_dump(exclude_none=True)},
        headers=_response_headers(request_id, headers),
    )


def create_paginated_response(
    request: Request,
    data: Any,
    *,
    page: Any = DEFAULT_PAGE,
    limit: Any = DEFAULT_LIMIT,
    total: Any,
    status_code: Literal[200, 201] = 200,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build a success envelope including validated pagination metadata."""
    return create_success_response(
        request,
        data,
        status_code=status_code,
        pagination=build_pagination_meta(page=page, limit=limit, total=total),
        headers=headers,
    )


def create_no_content_response(
    request: Request,
    *,
    headers: Mapping[str, str] | None = None,
) -> Response:
    """Return HTTP 204 with no body, Content-Type, or Content-Length."""
    return Response(status_code=204, headers=_response_headers(get_request_id(request), headers))

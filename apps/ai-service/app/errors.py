from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any, Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.context import REQUEST_ID_HEADER, get_request_id
from app.schemas import ProblemDetails, ValidationIssue

logger = logging.getLogger("smart_catering.ai_service")

PROBLEM_JSON_MEDIA_TYPE: Final[str] = "application/problem+json"

DOCS_PATHS: Final[frozenset[str]] = frozenset({"/docs", "/openapi.json"})
DOCS_SECURITY_HEADERS: Final[dict[str, str]] = {
    "Cache-Control": "private, no-store",
    "Vary": "Authorization",
}

HTTP_STATUS_TITLES: Final[dict[int, str]] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    422: "Unprocessable Content",
    500: "Internal Server Error",
}

SAFE_STATUS_DETAILS: Final[dict[int, str]] = {
    400: "The request could not be understood or contained malformed syntax.",
    401: "Authentication credentials are required or invalid.",
    403: "You do not have permission to access this resource.",
    404: "The requested resource was not found.",
    405: "The HTTP method is not allowed for this resource.",
    422: "Request validation failed.",
    500: "An unexpected error occurred.",
}

_LOC_PREFIXES_TO_STRIP: Final[frozenset[str]] = frozenset(
    {"body", "query", "path", "header", "cookie"}
)


class AppProblemError(Exception):
    """Explicit application error producing a sanitized RFC 9457 ProblemDetails response."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: str | None = None,
        headers: Mapping[str, str] | None = None,
        errors: list[ValidationIssue] | None = None,
    ) -> None:
        super().__init__(SAFE_STATUS_DETAILS.get(status_code, "Application problem"))
        self.status_code = status_code
        self.detail = detail
        self.headers = dict(headers) if headers is not None else None
        self.errors = list(errors) if errors is not None else None


class ApiInputValidationError(AppProblemError):
    """Raised by reusable helpers when input values fail validation."""

    def __init__(
        self,
        issues: Sequence[ValidationIssue],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        issue_list = list(issues)
        super().__init__(
            status_code=422,
            detail=SAFE_STATUS_DETAILS[422],
            headers=headers,
            errors=issue_list,
        )
        self.issues = issue_list


def normalize_validation_loc(loc: Sequence[Any]) -> str:
    """Strip source prefix (body/query/path/header) and join as dot path or '$'."""
    segments = [str(part) for part in loc if part is not None and str(part) != ""]
    if segments and segments[0] in _LOC_PREFIXES_TO_STRIP:
        segments = segments[1:]
    if not segments:
        return "$"
    return ".".join(segments)


def extract_validation_issues(raw_errors: Sequence[Any]) -> list[ValidationIssue]:
    """Convert FastAPI/Pydantic error dictionaries into sanitized ValidationIssue items."""
    issues: list[ValidationIssue] = []
    for err in raw_errors:
        raw_loc = err.get("loc", ()) if isinstance(err, Mapping) else ()
        loc_seq: Sequence[Any] = raw_loc if isinstance(raw_loc, (list, tuple)) else (raw_loc,)
        path = normalize_validation_loc(loc_seq)
        issues.append(
            ValidationIssue(
                path=path,
                code="invalid_value",
                message="Invalid value",
            )
        )
    if not issues:
        issues.append(ValidationIssue(path="$", code="invalid_value", message="Invalid value"))
    return issues


def is_malformed_json_error(raw_errors: Sequence[Any]) -> bool:
    """Detect whether a RequestValidationError originated from malformed JSON syntax."""
    for err in raw_errors:
        if not isinstance(err, Mapping):
            continue
        err_type = str(err.get("type", ""))
        if err_type == "json_invalid" or err_type.startswith("json_invalid"):
            return True
    return False


def build_problem_details(
    request: Request,
    *,
    status_code: int,
    detail: str | None = None,
    errors: list[ValidationIssue] | None = None,
) -> ProblemDetails:
    """Construct an RFC 9457 ProblemDetails model with safe title/detail and pathname instance."""
    normalized_status = (
        status_code if status_code in HTTP_STATUS_TITLES else (500 if status_code >= 500 else 400)
    )
    title = HTTP_STATUS_TITLES[normalized_status]
    safe_detail = (
        detail
        if detail is not None and normalized_status != 500
        else SAFE_STATUS_DETAILS[normalized_status]
    )
    pathname = request.url.path or "/"
    request_id = get_request_id(request)

    return ProblemDetails(
        type="about:blank",
        title=title,
        status=normalized_status,
        detail=safe_detail,
        instance=pathname,
        requestId=request_id,
        errors=errors if normalized_status == 422 and errors else None,
    )


def create_problem_response(
    request: Request,
    *,
    status_code: int,
    detail: str | None = None,
    errors: list[ValidationIssue] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build an application/problem+json response with X-Request-Id and route security headers."""
    problem = build_problem_details(
        request,
        status_code=status_code,
        detail=detail,
        errors=errors,
    )
    response_headers: dict[str, str] = {"Cache-Control": "no-store"}
    if request.url.path in DOCS_PATHS:
        response_headers.update(DOCS_SECURITY_HEADERS)
    if headers is not None:
        response_headers.update(headers)
    response_headers[REQUEST_ID_HEADER] = problem.requestId

    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
        headers=response_headers,
    )


def _log_controlled_server_problem(request: Request, status_code: int) -> None:
    if status_code >= 500:
        logger.error(
            "Server problem status=500 requestId=%s instance=%s",
            get_request_id(request),
            request.url.path,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach RFC 9457 exception handlers for validation, HTTP, and unexpected server errors."""

    @app.exception_handler(ApiInputValidationError)
    async def handle_api_input_validation_error(
        request: Request,
        exc: ApiInputValidationError,
    ) -> JSONResponse:
        return create_problem_response(
            request,
            status_code=422,
            detail=SAFE_STATUS_DETAILS[422],
            errors=exc.issues,
            headers=exc.headers,
        )

    @app.exception_handler(AppProblemError)
    async def handle_app_problem_error(
        request: Request,
        exc: AppProblemError,
    ) -> JSONResponse:
        _log_controlled_server_problem(request, exc.status_code)
        return create_problem_response(
            request,
            status_code=exc.status_code,
            detail=exc.detail,
            errors=exc.errors,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        raw_errors = exc.errors()
        if is_malformed_json_error(raw_errors):
            return create_problem_response(
                request,
                status_code=400,
                detail="Malformed JSON request body.",
            )
        issues = extract_validation_issues(raw_errors)
        return create_problem_response(
            request,
            status_code=422,
            detail=SAFE_STATUS_DETAILS[422],
            errors=issues,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_starlette_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        status_code = (
            exc.status_code
            if exc.status_code in HTTP_STATUS_TITLES
            else (500 if exc.status_code >= 500 else 400)
        )
        _log_controlled_server_problem(request, status_code)
        safe_headers: dict[str, str] = {}
        if exc.headers:
            for key, value in exc.headers.items():
                if key.lower() in {"www-authenticate", "allow", "cache-control", "vary"}:
                    safe_headers[key] = value
        return create_problem_response(
            request,
            status_code=status_code,
            detail=SAFE_STATUS_DETAILS[status_code],
            headers=safe_headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        request_id = get_request_id(request)
        pathname = request.url.path or "/"
        logger.error(
            "Unhandled server exception type=%s requestId=%s instance=%s",
            exc.__class__.__name__,
            request_id,
            pathname,
        )
        return create_problem_response(
            request,
            status_code=500,
            detail=SAFE_STATUS_DETAILS[500],
        )

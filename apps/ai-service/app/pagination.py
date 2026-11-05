from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final

from fastapi import Request

from app.errors import ApiInputValidationError
from app.schemas import PaginationMeta, ValidationIssue

MAX_SAFE_INTEGER: Final[int] = 9_007_199_254_740_991
DEFAULT_PAGE: Final[int] = 1
DEFAULT_LIMIT: Final[int] = 20
MAX_LIMIT: Final[int] = 100

_DECIMAL_DIGITS_PATTERN: Final[re.Pattern[str]] = re.compile(r"[0-9]+")
_MAX_SAFE_DIGITS: Final[int] = len(str(MAX_SAFE_INTEGER))


@dataclass(frozen=True, slots=True)
class PaginationParams:
    """Validated pagination parameters and safe 0-based offset."""

    page: int = DEFAULT_PAGE
    limit: int = DEFAULT_LIMIT
    offset: int = 0


def _parse_strict_integer(value: Any, *, allow_string: bool) -> int | None:
    """Parse an integer while rejecting booleans, floats, fractions, and non-decimal strings."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if allow_string and isinstance(value, str):
        if not _DECIMAL_DIGITS_PATTERN.fullmatch(value):
            return None
        significant_digits = value.lstrip("0") or "0"
        if len(significant_digits) > _MAX_SAFE_DIGITS:
            return None
        return int(significant_digits, 10)
    return None


def _validate_page_and_limit(
    page: Any,
    limit: Any,
    *,
    allow_string: bool,
) -> tuple[int | None, int | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []

    parsed_page = _parse_strict_integer(page, allow_string=allow_string)
    if parsed_page is None or parsed_page < 1 or parsed_page > MAX_SAFE_INTEGER:
        issues.append(ValidationIssue(path="page", code="invalid_value", message="Invalid value"))
        parsed_page = None

    parsed_limit = _parse_strict_integer(limit, allow_string=allow_string)
    if parsed_limit is None or parsed_limit < 1 or parsed_limit > MAX_LIMIT:
        issues.append(ValidationIssue(path="limit", code="invalid_value", message="Invalid value"))
        parsed_limit = None

    if parsed_page is not None and parsed_limit is not None:
        offset = (parsed_page - 1) * parsed_limit
        window_end = parsed_page * parsed_limit
        if offset > MAX_SAFE_INTEGER or window_end > MAX_SAFE_INTEGER:
            issues.append(
                ValidationIssue(path="page", code="invalid_value", message="Invalid value")
            )
            parsed_page = None

    return parsed_page, parsed_limit, issues


def parse_pagination_params(
    page: Any = DEFAULT_PAGE,
    limit: Any = DEFAULT_LIMIT,
    *,
    allow_string: bool = True,
) -> PaginationParams:
    """Validate page and limit (including offset overflow) and return PaginationParams."""
    effective_page = DEFAULT_PAGE if page is None else page
    effective_limit = DEFAULT_LIMIT if limit is None else limit

    parsed_page, parsed_limit, issues = _validate_page_and_limit(
        effective_page,
        effective_limit,
        allow_string=allow_string,
    )
    if issues or parsed_page is None or parsed_limit is None:
        raise ApiInputValidationError(issues)

    return PaginationParams(
        page=parsed_page,
        limit=parsed_limit,
        offset=(parsed_page - 1) * parsed_limit,
    )


def build_pagination_meta(
    *,
    page: Any = DEFAULT_PAGE,
    limit: Any = DEFAULT_LIMIT,
    total: Any,
) -> PaginationMeta:
    """Validate page, limit, and total against safe integer bounds and compute totalPages."""
    parsed_page, parsed_limit, issues = _validate_page_and_limit(
        page,
        limit,
        allow_string=False,
    )

    parsed_total = _parse_strict_integer(total, allow_string=False)
    if parsed_total is None or parsed_total < 0 or parsed_total > MAX_SAFE_INTEGER:
        issues.append(ValidationIssue(path="total", code="invalid_value", message="Invalid value"))
        parsed_total = None

    if issues or parsed_page is None or parsed_limit is None or parsed_total is None:
        raise ApiInputValidationError(issues)

    total_pages = 0 if parsed_total == 0 else (parsed_total + parsed_limit - 1) // parsed_limit

    return PaginationMeta(
        page=parsed_page,
        limit=parsed_limit,
        total=parsed_total,
        totalPages=total_pages,
    )


def get_pagination_params(request: Request) -> PaginationParams:
    """FastAPI dependency parsing ?page= and ?limit= query parameters."""
    pages = request.query_params.getlist("page")
    limits = request.query_params.getlist("limit")
    issues = [
        ValidationIssue(path=field, code="invalid_value", message="Invalid value")
        for field, values in (("page", pages), ("limit", limits))
        if len(values) > 1
    ]
    if issues:
        raise ApiInputValidationError(issues)
    return parse_pagination_params(
        page=pages[0] if pages else DEFAULT_PAGE,
        limit=limits[0] if limits else DEFAULT_LIMIT,
        allow_string=True,
    )

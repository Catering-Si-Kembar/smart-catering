from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends, Request, Response
from fastapi.testclient import TestClient

from app.errors import ApiInputValidationError
from app.main import create_app
from app.pagination import (
    DEFAULT_LIMIT,
    DEFAULT_PAGE,
    MAX_LIMIT,
    MAX_SAFE_INTEGER,
    PaginationParams,
    build_pagination_meta,
    get_pagination_params,
    parse_pagination_params,
)
from app.responses import create_paginated_response


def test_pagination_defaults_and_total_pages_calculation() -> None:
    params = parse_pagination_params()
    assert params.page == DEFAULT_PAGE == 1
    assert params.limit == DEFAULT_LIMIT == 20
    assert params.offset == 0

    empty_meta = build_pagination_meta(page=1, limit=20, total=0)
    assert empty_meta.model_dump() == {
        "page": 1,
        "limit": 20,
        "total": 0,
        "totalPages": 0,
    }

    exact_meta = build_pagination_meta(page=2, limit=20, total=40)
    assert exact_meta.model_dump() == {
        "page": 2,
        "limit": 20,
        "total": 40,
        "totalPages": 2,
    }

    partial_meta = build_pagination_meta(page=3, limit=20, total=41)
    assert partial_meta.model_dump() == {
        "page": 3,
        "limit": 20,
        "total": 41,
        "totalPages": 3,
    }


def test_pagination_safe_integer_boundary_and_offset_overflow() -> None:
    meta_at_max_total = build_pagination_meta(page=1, limit=1, total=MAX_SAFE_INTEGER)
    assert meta_at_max_total.total == MAX_SAFE_INTEGER
    assert meta_at_max_total.totalPages == MAX_SAFE_INTEGER

    max_page_for_limit_100 = MAX_SAFE_INTEGER // MAX_LIMIT
    valid_high_page = parse_pagination_params(page=max_page_for_limit_100, limit=MAX_LIMIT)
    assert valid_high_page.page == max_page_for_limit_100
    assert valid_high_page.limit == MAX_LIMIT

    with pytest.raises(ApiInputValidationError) as overflow_exc:
        parse_pagination_params(page=max_page_for_limit_100 + 1, limit=MAX_LIMIT)
    assert [issue.path for issue in overflow_exc.value.issues] == ["page"]

    with pytest.raises(ApiInputValidationError) as unsafe_total_exc:
        build_pagination_meta(page=1, limit=20, total=MAX_SAFE_INTEGER + 1)
    assert [issue.path for issue in unsafe_total_exc.value.issues] == ["total"]


@pytest.mark.parametrize(
    ("bad_page", "bad_limit", "bad_total", "expected_paths"),
    [
        (0, 20, 0, ["page"]),
        (-1, 20, 0, ["page"]),
        (1.5, 20, 0, ["page"]),
        ("1.5", 20, 0, ["page"]),
        (True, 20, 0, ["page"]),
        ("abc", 20, 0, ["page"]),
        (MAX_SAFE_INTEGER + 1, 1, 0, ["page"]),
        (1, 0, 0, ["limit"]),
        (1, -5, 0, ["limit"]),
        (1, 101, 0, ["limit"]),
        (1, 20.5, 0, ["limit"]),
        (1, False, 0, ["limit"]),
        (1, "20px", 0, ["limit"]),
        (1, 20, -1, ["total"]),
        (1, 20, 3.14, ["total"]),
        (1, 20, True, ["total"]),
        (1, 20, "100", ["total"]),
        (0, 101, -1, ["page", "limit", "total"]),
    ],
)
def test_pagination_rejects_invalid_fraction_negative_boolean_and_unsafe_values(
    bad_page: object,
    bad_limit: object,
    bad_total: object,
    expected_paths: list[str],
) -> None:
    with pytest.raises(ApiInputValidationError) as exc_info:
        build_pagination_meta(page=bad_page, limit=bad_limit, total=bad_total)

    issues = exc_info.value.issues
    assert [issue.path for issue in issues] == expected_paths
    for issue in issues:
        assert issue.code == "invalid_value"
        assert issue.message == "Invalid value"


def test_paginated_response_helper_and_query_dependency_in_route() -> None:
    app = create_app(env={"APP_ENV": "test"})

    @app.get("/_test/paginated")
    async def ephemeral_paginated(
        request: Request,
        pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    ) -> Response:
        return create_paginated_response(
            request,
            [{"id": "menu-1"}],
            page=pagination.page,
            limit=pagination.limit,
            total=45,
        )

    client = TestClient(app, raise_server_exceptions=False)

    ok_res = client.get("/_test/paginated?page=2&limit=20")
    assert ok_res.status_code == 200
    payload = ok_res.json()
    assert payload["data"] == [{"id": "menu-1"}]
    assert payload["meta"]["requestId"] == ok_res.headers["x-request-id"]
    assert payload["meta"]["pagination"] == {
        "page": 2,
        "limit": 20,
        "total": 45,
        "totalPages": 3,
    }

    err_res = client.get("/_test/paginated?page=0&limit=105")
    assert err_res.status_code == 422
    assert err_res.headers["content-type"].startswith("application/problem+json")
    problem = err_res.json()
    assert problem["title"] == "Unprocessable Content"
    assert problem["status"] == 422
    assert problem["instance"] == "/_test/paginated"
    assert problem["errors"] == [
        {"path": "page", "code": "invalid_value", "message": "Invalid value"},
        {"path": "limit", "code": "invalid_value", "message": "Invalid value"},
    ]

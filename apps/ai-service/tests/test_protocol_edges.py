from typing import Annotated

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.context import normalize_or_generate_request_id
from app.main import create_app
from app.pagination import PaginationParams, get_pagination_params
from app.responses import create_success_response


class NestedInput(BaseModel):
    body: int


class ReservedFieldInput(BaseModel):
    query: NestedInput


@pytest.mark.parametrize("page", ["9" * 4301, "١", "1\n", "1&page=2"])
def test_unsafe_or_ambiguous_pagination_returns_422_without_echoing_input(page: str) -> None:
    application = create_app(env={"APP_ENV": "test"})

    @application.get("/_test/page")
    async def paginated(
        request: Request,
        pagination: Annotated[PaginationParams, Depends(get_pagination_params)],
    ):
        return create_success_response(request, {"page": pagination.page})

    query = "page=1&page=2" if page == "1&page=2" else {"page": page}
    response = TestClient(application).get("/_test/page", params=query)
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["errors"] == [
        {"path": "page", "code": "invalid_value", "message": "Invalid value"}
    ]
    assert page not in response.text


def test_validation_preserves_nested_fields_named_like_location_prefixes() -> None:
    application = create_app(env={"APP_ENV": "test"})

    @application.post("/_test/nested")
    async def nested(payload: ReservedFieldInput) -> None:
        return None

    response = TestClient(application).post("/_test/nested", json={"query": {"body": "invalid"}})
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"path": "query.body", "code": "invalid_value", "message": "Invalid value"}
    ]


def test_oversized_padded_uuid_is_replaced_before_trimming() -> None:
    incoming = "b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b"
    resolved = normalize_or_generate_request_id(" " * 100 + incoming)
    assert resolved != incoming
    assert len(resolved) == 36


@pytest.mark.parametrize(
    ("configured", "supplied", "expected"),
    [("\ufeffops", "\ufeffops", 200), ("ops", "\ufeffops", 401), ("pengelola", "pengelola", 200)],
)
def test_basic_auth_preserves_exact_utf8_credential_identity(
    configured: str, supplied: str, expected: int
) -> None:
    password = "秘密" * 20
    application = create_app(
        env={
            "APP_ENV": "production",
            "DOCS_ENABLED": "true",
            "DOCS_USERNAME": configured,
            "DOCS_PASSWORD": password,
        }
    )
    response = TestClient(application).get("/openapi.json", auth=(supplied, password))
    assert response.status_code == expected
    if expected == 200:
        assert response.json()["openapi"] == "3.1.0"
    else:
        assert response.json()["status"] == 401
        assert response.json()["requestId"] == response.headers["x-request-id"]

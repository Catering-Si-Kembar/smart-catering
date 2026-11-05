from __future__ import annotations

import json

from fastapi import HTTPException, Path, Query, Request, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.errors import AppProblemError
from app.main import create_app
from app.responses import create_success_response
from tests.conftest import UUID_REGEX


class EphemeralOrderCheckPayload(BaseModel):
    menu_code: str = Field(min_length=3)
    portions: int = Field(ge=1, le=500)


def _create_ephemeral_test_client() -> TestClient:
    app = create_app(env={"APP_ENV": "test", "DOCS_PASSWORD": "TOP_SECRET_VALUE_1234567890123456"})

    @app.post("/_test/validate/{category_id}")
    async def ephemeral_validate(
        request: Request,
        category_id: int = Path(ge=1),
        urgent: bool = Query(default=False),
        payload: EphemeralOrderCheckPayload | None = None,
    ) -> Response:
        return create_success_response(
            request,
            {
                "category_id": category_id,
                "urgent": urgent,
                "menu_code": payload.menu_code if payload else None,
            },
        )

    @app.post("/_test/strict-body")
    async def ephemeral_strict_body(
        request: Request,
        payload: EphemeralOrderCheckPayload,
    ) -> Response:
        return create_success_response(
            request,
            {"menu_code": payload.menu_code, "portions": payload.portions},
        )

    @app.get("/_test/direct-pydantic-error")
    async def ephemeral_direct_pydantic_error() -> Response:
        EphemeralOrderCheckPayload(menu_code="x", portions=-1)
        raise AssertionError("Unreachable")

    @app.get("/_test/direct-json-error")
    async def ephemeral_direct_json_error() -> Response:
        json.loads("{malformed")
        raise AssertionError("Unreachable")

    @app.get("/_test/http-error/{code}")
    async def ephemeral_http_error(code: int) -> Response:
        if code == 401:
            raise AppProblemError(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Test"'},
            )
        if code == 403:
            raise HTTPException(
                status_code=403,
                detail="Sensitive internal detail: role=kitchen_secret denied for SQL query",
            )
        if code == 400:
            raise HTTPException(
                status_code=400,
                detail="Raw input leak: {'password': 'secret'}",
            )
        raise HTTPException(status_code=code, detail="Leaked internal detail")

    @app.get("/_test/crash")
    async def ephemeral_crash() -> Response:
        raise RuntimeError(
            "FATAL: Database connection failed for "
            "postgresql://user:SUPER_SECRET_DB_PASS@db:5432/app "
            "with DOCS_PASSWORD=TOP_SECRET_VALUE_1234567890123456"
        )

    return TestClient(app, raise_server_exceptions=False)


def test_unknown_route_returns_404_problem_details_with_pathname_instance() -> None:
    client = _create_ephemeral_test_client()
    incoming_id = "01941234-5678-7abc-8def-0123456789ab"

    response = client.get(
        "/non-existent-route?secret=should_not_appear_in_instance&token=abc",
        headers={"X-Request-Id": incoming_id},
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["x-request-id"] == incoming_id

    problem = response.json()
    assert problem == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "The requested resource was not found.",
        "instance": "/non-existent-route",
        "requestId": incoming_id,
    }
    assert "should_not_appear_in_instance" not in response.text


def test_wrong_method_returns_405_problem_details() -> None:
    client = _create_ephemeral_test_client()
    response = client.post("/health?foo=bar")

    assert response.status_code == 405
    assert response.headers["content-type"].startswith("application/problem+json")
    request_id = response.headers["x-request-id"]
    assert UUID_REGEX.match(request_id)

    problem = response.json()
    assert problem == {
        "type": "about:blank",
        "title": "Method Not Allowed",
        "status": 405,
        "detail": "The HTTP method is not allowed for this resource.",
        "instance": "/health",
        "requestId": request_id,
    }


def test_malformed_json_returns_400_problem_details() -> None:
    client = _create_ephemeral_test_client()
    response = client.post(
        "/_test/strict-body?debug=secret",
        content=b'{"menu_code": "PKT-01", "portions": ',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    request_id = response.headers["x-request-id"]
    assert UUID_REGEX.match(request_id)

    problem = response.json()
    assert problem["type"] == "about:blank"
    assert problem["title"] == "Bad Request"
    assert problem["status"] == 400
    assert problem["instance"] == "/_test/strict-body"
    assert problem["requestId"] == request_id
    assert "PKT-01" not in response.text


def test_structurally_valid_json_with_invalid_fields_returns_422_without_loc_prefix() -> None:
    client = _create_ephemeral_test_client()
    response = client.post(
        "/_test/validate/0?urgent=not_a_bool",
        json={"menu_code": "A", "portions": 0},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    request_id = response.headers["x-request-id"]
    assert UUID_REGEX.match(request_id)

    problem = response.json()
    assert problem["type"] == "about:blank"
    assert problem["title"] == "Unprocessable Content"
    assert problem["status"] == 422
    assert problem["detail"] == "Request validation failed."
    assert problem["instance"] == "/_test/validate/0"
    assert problem["requestId"] == request_id

    errors = problem["errors"]
    assert isinstance(errors, list)
    paths = {item["path"] for item in errors}
    assert paths == {"category_id", "urgent", "menu_code", "portions"}
    for issue in errors:
        assert issue["code"] == "invalid_value"
        assert issue["message"] == "Invalid value"
        assert not issue["path"].startswith(("body.", "query.", "path.", "header."))


def test_root_level_invalid_json_type_maps_path_to_dollar() -> None:
    client = _create_ephemeral_test_client()
    response = client.post(
        "/_test/strict-body",
        json=["not", "an", "object"],
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = response.json()
    assert problem["title"] == "Unprocessable Content"
    assert problem["status"] == 422
    assert problem["errors"] == [
        {
            "path": "$",
            "code": "invalid_value",
            "message": "Invalid value",
        }
    ]


def test_server_model_and_json_failures_are_500_not_client_validation_errors() -> None:
    client = _create_ephemeral_test_client()
    for path in ("/_test/direct-pydantic-error", "/_test/direct-json-error"):
        response = client.get(path)
        assert response.status_code == 500
        assert response.headers["content-type"].startswith("application/problem+json")
        problem = response.json()
        assert problem["detail"] == "An unexpected error occurred."
        assert problem["requestId"] == response.headers["x-request-id"]
        assert "errors" not in problem
        assert "menu_code" not in response.text
        assert "malformed" not in response.text


def test_http_400_401_403_and_500_never_leak_internal_details_or_secrets() -> None:
    client = _create_ephemeral_test_client()

    r400 = client.get("/_test/http-error/400")
    assert r400.status_code == 400
    assert r400.json()["title"] == "Bad Request"
    assert "secret" not in r400.text.lower()

    r401 = client.get("/_test/http-error/401")
    assert r401.status_code == 401
    assert r401.json()["title"] == "Unauthorized"
    assert r401.headers.get("www-authenticate") == 'Basic realm="Test"'

    r403 = client.get("/_test/http-error/403")
    assert r403.status_code == 403
    assert r403.json()["title"] == "Forbidden"
    assert "kitchen_secret" not in r403.text
    assert "SQL" not in r403.text

    r500 = client.get("/_test/crash?query_secret=123")
    assert r500.status_code == 500
    assert r500.headers["content-type"].startswith("application/problem+json")
    req_id = r500.headers["x-request-id"]
    assert UUID_REGEX.match(req_id)
    assert r500.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "An unexpected error occurred.",
        "instance": "/_test/crash",
        "requestId": req_id,
    }
    assert "SUPER_SECRET_DB_PASS" not in r500.text
    assert "TOP_SECRET_VALUE" not in r500.text
    assert "RuntimeError" not in r500.text

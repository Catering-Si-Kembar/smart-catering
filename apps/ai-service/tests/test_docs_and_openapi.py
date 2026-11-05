from __future__ import annotations

import base64
from collections.abc import Callable, Mapping

import pytest
from fastapi.testclient import TestClient


def _basic_auth_header(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def test_dev_and_test_enable_docs_and_openapi_by_default(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    for app_env in ("development", "test"):
        client = make_client({"APP_ENV": app_env, "DOCS_ENABLED": None})

        spec_res = client.get("/openapi.json")
        assert spec_res.status_code == 200
        assert spec_res.headers["cache-control"] == "private, no-store"
        assert "Authorization" in spec_res.headers["vary"]
        assert "x-request-id" in spec_res.headers

        spec = spec_res.json()
        assert spec["openapi"] == "3.1.0"
        assert "data" not in spec
        assert "/health" in spec["paths"]
        assert spec["paths"]["/health"]["get"]["security"] == []

        schemas = spec["components"]["schemas"]
        for expected_schema in (
            "HealthData",
            "PaginationMeta",
            "ApiMeta",
            "HealthResponse",
            "ValidationIssue",
            "ProblemDetails",
        ):
            assert expected_schema in schemas

        security_schemes = spec["components"]["securitySchemes"]
        assert "DocsBasicAuth" in security_schemes
        assert security_schemes["DocsBasicAuth"]["type"] == "http"
        assert security_schemes["DocsBasicAuth"]["scheme"] == "basic"

        docs_res = client.get("/docs")
        assert docs_res.status_code == 200
        assert docs_res.headers["content-type"].startswith("text/html")
        assert docs_res.headers["cache-control"] == "private, no-store"
        assert "Authorization" in docs_res.headers["vary"]
        assert "x-request-id" in docs_res.headers


@pytest.mark.parametrize(
    ("app_env", "docs_enabled"),
    [
        ("development", "false"),
        ("test", "false"),
        ("production", None),
        ("production", ""),
        ("production", "   "),
        ("production", "false"),
    ],
)
def test_disabled_docs_returns_404_problem_and_keeps_health_public(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
    app_env: str,
    docs_enabled: str | None,
) -> None:
    client = make_client(
        {
            "APP_ENV": app_env,
            "DOCS_ENABLED": docs_enabled,
            "DOCS_USERNAME": "admin",
            "DOCS_PASSWORD": "A" * 32,
        }
    )

    for path in ("/docs", "/openapi.json"):
        res = client.get(path)
        assert res.status_code == 404
        assert res.headers["content-type"].startswith("application/problem+json")
        assert res.headers["cache-control"] == "private, no-store"
        assert "Authorization" in res.headers["vary"]
        problem = res.json()
        assert problem["status"] == 404
        assert problem["title"] == "Not Found"
        assert problem["instance"] == path
        assert problem["requestId"] == res.headers["x-request-id"]

    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["data"] == {"status": "ok", "service": "ai-service"}


@pytest.mark.parametrize(
    ("app_env", "docs_enabled"),
    [
        ("development", "TRUE"),
        ("development", "FALSE"),
        ("development", "1"),
        ("development", "yes"),
        ("development", "0"),
        ("development", "no"),
        ("production", "1"),
        ("production", "TRUE"),
        ("production", "invalid"),
        ("staging", None),
        ("staging", "true"),
        ("staging", "false"),
    ],
)
def test_invalid_docs_enabled_or_unknown_app_env_returns_500_problem_and_keeps_health_public(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
    app_env: str,
    docs_enabled: str | None,
) -> None:
    client = make_client(
        {
            "APP_ENV": app_env,
            "DOCS_ENABLED": docs_enabled,
            "DOCS_USERNAME": "admin",
            "DOCS_PASSWORD": "A" * 32,
        }
    )

    for path in ("/docs", "/openapi.json"):
        res = client.get(path)
        assert res.status_code == 500
        assert res.headers["content-type"].startswith("application/problem+json")
        assert res.headers["cache-control"] == "private, no-store"
        assert "Authorization" in res.headers["vary"]
        problem = res.json()
        assert problem == {
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred.",
            "instance": path,
            "requestId": res.headers["x-request-id"],
        }

    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["data"] == {"status": "ok", "service": "ai-service"}


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("", "A" * 32),
        ("   ", "A" * 32),
        ("admin", ""),
        ("admin", "short_password_under_32_chars"),
        ("admin", "A" * 31),
        ("bad:user", "A" * 32),
        ("bad\nuser", "A" * 32),
        ("bad\ruser", "A" * 32),
        ("admin", "A" * 32 + "\n"),
        ("admin", "A" * 32 + "\r"),
    ],
)
def test_production_enabled_docs_with_misconfigured_credentials_returns_500_generic_problem(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
    username: str,
    password: str,
) -> None:
    client = make_client(
        {
            "APP_ENV": "production",
            "DOCS_ENABLED": "true",
            "DOCS_USERNAME": username,
            "DOCS_PASSWORD": password,
        }
    )

    for path in ("/docs", "/openapi.json"):
        res = client.get(path, headers=_basic_auth_header("admin", "A" * 32))
        assert res.status_code == 500
        assert res.headers["content-type"].startswith("application/problem+json")
        assert res.headers["cache-control"] == "private, no-store"
        assert "Authorization" in res.headers["vary"]
        problem = res.json()
        assert problem == {
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred.",
            "instance": path,
            "requestId": res.headers["x-request-id"],
        }
        if password.strip():
            assert password.strip() not in res.text

    health_res = client.get("/health")
    assert health_res.status_code == 200


def test_production_enabled_docs_enforces_http_basic_auth_and_never_leaks_credentials(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    valid_user = "katering-docs-admin"
    valid_pass = "P" * 36
    client = make_client(
        {
            "APP_ENV": "production",
            "DOCS_ENABLED": "true",
            "DOCS_USERNAME": valid_user,
            "DOCS_PASSWORD": valid_pass,
        }
    )

    unauthenticated_cases = [
        {},
        {"Authorization": "Bearer some-jwt-token"},
        {"Authorization": "Basic"},
        {"Authorization": "Basic !!!not_base64!!!"},
        {"Authorization": "Basic " + base64.b64encode(b"no_colon_separator").decode("ascii")},
        {"Authorization": "Basic " + base64.b64encode(b"\xff\xfe:\xff").decode("ascii")},
        _basic_auth_header("wrong-user", valid_pass),
        _basic_auth_header(valid_user, "W" * 36),
        _basic_auth_header("wrong-user", "W" * 36),
    ]

    for headers in unauthenticated_cases:
        for path in ("/docs", "/openapi.json"):
            res = client.get(path, headers=headers)
            assert res.status_code == 401
            assert res.headers["content-type"].startswith("application/problem+json")
            assert res.headers["cache-control"] == "private, no-store"
            assert "Authorization" in res.headers["vary"]
            assert (
                res.headers.get("www-authenticate")
                == 'Basic realm="Smart Catering Docs", charset="UTF-8"'
            )
            problem = res.json()
            assert problem["status"] == 401
            assert problem["title"] == "Unauthorized"
            assert problem["instance"] == path
            assert problem["requestId"] == res.headers["x-request-id"]
            assert valid_pass not in res.text
            assert valid_user not in res.text

    auth_headers = _basic_auth_header(valid_user, valid_pass)

    docs_ok = client.get("/docs", headers=auth_headers)
    assert docs_ok.status_code == 200
    assert docs_ok.headers["cache-control"] == "private, no-store"
    assert "Authorization" in docs_ok.headers["vary"]
    assert valid_pass not in docs_ok.text
    assert valid_user not in docs_ok.text

    spec_ok = client.get("/openapi.json", headers=auth_headers)
    assert spec_ok.status_code == 200
    assert spec_ok.headers["cache-control"] == "private, no-store"
    assert "Authorization" in spec_ok.headers["vary"]
    assert spec_ok.json()["openapi"] == "3.1.0"
    assert valid_pass not in spec_ok.text
    assert valid_user not in spec_ok.text

    health_ok = client.get("/health")
    assert health_ok.status_code == 200


def test_head_requests_on_health_docs_and_openapi_follow_get_semantics_with_empty_body(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    dev_client = make_client({"APP_ENV": "development", "DOCS_ENABLED": "true"})

    for path in ("/health", "/docs", "/openapi.json"):
        get_res = dev_client.get(path)
        head_res = dev_client.head(path)
        assert head_res.status_code == get_res.status_code == 200
        assert head_res.content == b""
        assert "x-request-id" in head_res.headers
        if path in ("/docs", "/openapi.json"):
            assert head_res.headers["cache-control"] == "private, no-store"
            assert "Authorization" in head_res.headers["vary"]

    valid_user = "katering-docs-admin"
    valid_pass = "P" * 36
    prod_client = make_client(
        {
            "APP_ENV": "production",
            "DOCS_ENABLED": "true",
            "DOCS_USERNAME": valid_user,
            "DOCS_PASSWORD": valid_pass,
        }
    )

    for path in ("/docs", "/openapi.json"):
        unauth_head = prod_client.head(path)
        assert unauth_head.status_code == 401
        assert unauth_head.content == b""
        assert (
            unauth_head.headers["www-authenticate"]
            == 'Basic realm="Smart Catering Docs", charset="UTF-8"'
        )
        assert unauth_head.headers["cache-control"] == "private, no-store"

        auth_head = prod_client.head(path, headers=_basic_auth_header(valid_user, valid_pass))
        assert auth_head.status_code == 200
        assert auth_head.content == b""
        assert auth_head.headers["cache-control"] == "private, no-store"

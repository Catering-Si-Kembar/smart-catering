from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Mapping
from typing import Any

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient

from app.main import create_app
from app.responses import create_no_content_response

PROCESS_TIME_PATTERN = re.compile(r"^\d+\.\d{2}$")


def _extract_http_request_logs(
    records: list[logging.LogRecord],
) -> list[tuple[int, dict[str, Any]]]:
    parsed: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        message = record.getMessage()
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("event") == "http_request":
            parsed.append((record.levelno, payload))
    return parsed


def test_responses_include_non_negative_process_time_header_across_routes(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    app = create_app(env={"APP_ENV": "test"})

    @app.delete("/_test/no-content-timing")
    async def no_content_route(request: Request) -> Response:
        return create_no_content_response(request)

    client = TestClient(app, raise_server_exceptions=False)

    responses = [
        client.get("/health"),
        client.head("/health"),
        client.get("/api/v1/health"),
        client.post("/api/v1/ml/predict-relevance", json={"text": "Paket nasi box ayam bakar"}),
        client.post("/api/v1/ml/predict-relevance", json={"text": "   "}),
        client.get("/not-a-route"),
        client.delete("/_test/no-content-timing"),
    ]

    for response in responses:
        raw_header = response.headers.get("x-process-time-ms")
        assert raw_header is not None, f"Missing X-Process-Time-Ms on {response.request.url.path}"
        assert PROCESS_TIME_PATTERN.match(raw_header), f"Unexpected header format: {raw_header!r}"
        assert float(raw_header) >= 0.0

    no_content_res = responses[-1]
    assert no_content_res.status_code == 204
    assert no_content_res.content == b""
    assert "content-type" not in no_content_res.headers


def test_structured_request_log_records_metadata_without_secrets_or_query(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_token = "SUPER_SECRET_INTERNAL_TOKEN_98765"
    secret_bearer = "SUPER_SECRET_BEARER_VALUE_54321"
    secret_query = "SECRET_QUERY_TOKEN_VALUE"
    incoming_id = "01941234-5678-7abc-8def-0123456789ab"

    app = create_app(env={"APP_ENV": "test", "INTERNAL_SERVICE_SECRET": secret_token})
    client = TestClient(app, raise_server_exceptions=False)

    with caplog.at_level(logging.INFO, logger="smart_catering.ai_service"):
        response = client.post(
            f"/api/v1/ml/predict-relevance?token={secret_query}",
            json={"text": "   "},
            headers={
                "X-Request-Id": incoming_id,
                "X-Internal-Token": secret_token,
                "Authorization": f"Bearer {secret_bearer}",
            },
        )

    assert response.status_code == 422
    all_log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert secret_token not in all_log_text
    assert secret_bearer not in all_log_text
    assert secret_query not in all_log_text

    http_logs = _extract_http_request_logs(caplog.records)
    assert len(http_logs) == 1
    levelno, payload = http_logs[0]
    assert levelno == logging.INFO
    assert payload["method"] == "POST"
    assert payload["path"] == "/api/v1/ml/predict-relevance"
    assert payload["status"] == 422
    assert payload["requestId"] == incoming_id
    assert isinstance(payload["durationMs"], (int, float))
    assert payload["durationMs"] >= 0.0


def test_structured_request_log_uses_error_level_for_500_status(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(
        env={
            "APP_ENV": "production",
            "DOCS_ENABLED": "true",
            "DOCS_USERNAME": "ADMIN_USER",
            "DOCS_PASSWORD": "SHORT_PASSWORD",
        }
    )
    client = TestClient(app, raise_server_exceptions=False)

    with caplog.at_level(logging.INFO, logger="smart_catering.ai_service"):
        response = client.get("/docs?secret=DO_NOT_LOG_THIS")

    assert response.status_code == 500
    all_log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "ADMIN_USER" not in all_log_text
    assert "SHORT_PASSWORD" not in all_log_text
    assert "DO_NOT_LOG_THIS" not in all_log_text

    http_logs = _extract_http_request_logs(caplog.records)
    assert len(http_logs) == 1
    levelno, payload = http_logs[0]
    assert levelno == logging.ERROR
    assert payload["method"] == "GET"
    assert payload["path"] == "/docs"
    assert payload["status"] == 500
    assert payload["requestId"] == response.headers["x-request-id"]
    assert isinstance(payload["durationMs"], (int, float))
    assert payload["durationMs"] >= 0.0


def test_openapi_documents_process_time_header(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client({"APP_ENV": "test", "DOCS_ENABLED": "true"})
    spec_res = client.get("/openapi.json")
    assert spec_res.status_code == 200
    document = spec_res.json()

    headers_component = document["components"]["headers"]
    assert "X-Process-Time-Ms" in headers_component

    for path, method in (
        ("/health", "get"),
        ("/api/v1/health", "get"),
        ("/api/v1/ml/predict-relevance", "post"),
    ):
        ok_headers = document["paths"][path][method]["responses"]["200"].get("headers", {})
        assert "X-Request-Id" in ok_headers
        assert "X-Process-Time-Ms" in ok_headers

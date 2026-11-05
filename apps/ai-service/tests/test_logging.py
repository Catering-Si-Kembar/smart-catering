import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_controlled_500_logs_request_correlation_without_credentials_or_query(
    caplog: pytest.LogCaptureFixture,
) -> None:
    application = create_app(
        env={
            "APP_ENV": "production",
            "DOCS_ENABLED": "true",
            "DOCS_USERNAME": "PRIVATE_ADMIN_USERNAME",
            "DOCS_PASSWORD": "PRIVATE_SHORT_PASSWORD",
        }
    )
    response = TestClient(application).get("/docs?token=PRIVATE_QUERY_TOKEN")
    assert response.status_code == 500
    problem = response.json()
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert problem["requestId"] in logs
    assert "/docs" in logs
    assert "PRIVATE_ADMIN_USERNAME" not in logs
    assert "PRIVATE_SHORT_PASSWORD" not in logs
    assert "PRIVATE_QUERY_TOKEN" not in logs
    assert problem["requestId"] == response.headers["x-request-id"]

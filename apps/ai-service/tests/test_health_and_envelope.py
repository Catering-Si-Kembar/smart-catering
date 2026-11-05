from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from fastapi import Request, Response
from fastapi.testclient import TestClient

from app.config import _read_env_file, load_settings
from app.main import create_app
from app.responses import create_no_content_response, create_success_response
from tests.conftest import UUID_REGEX


def test_health_returns_wrapped_envelope_and_request_id_header(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client(None)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    header_request_id = response.headers.get("x-request-id")
    assert header_request_id is not None
    assert UUID_REGEX.match(header_request_id)

    payload = response.json()
    assert set(payload.keys()) == {"data", "meta"}
    assert "success" not in payload
    assert "error" not in payload
    assert payload["data"] == {
        "status": "ok",
        "service": "ai-service",
    }
    assert payload["meta"] == {
        "requestId": header_request_id,
    }


def test_request_id_preserves_valid_uuid_normalized_to_lowercase(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client(None)
    incoming = "01941234-5678-7ABC-8DEF-0123456789AB"

    response = client.get("/health", headers={"X-Request-Id": incoming})

    assert response.status_code == 200
    expected = incoming.lower()
    assert response.headers["x-request-id"] == expected
    assert response.json()["meta"]["requestId"] == expected


def test_request_id_replaces_invalid_or_oversize_incoming_header(
    make_client: Callable[[Mapping[str, str | None] | None], TestClient],
) -> None:
    client = make_client(None)
    invalid_values = [
        "not-a-uuid",
        "",
        "   ",
        "00000000-0000-0000-0000-000000000000",
        "01941234-5678-9abc-8def-0123456789ab",
        "01941234-5678-4abc-0def-0123456789ab",
        "a" * 200,
    ]

    for invalid_id in invalid_values:
        response = client.get("/health", headers={"X-Request-Id": invalid_id})
        assert response.status_code == 200
        generated_id = response.headers["x-request-id"]
        assert generated_id != invalid_id.lower()
        assert UUID_REGEX.match(generated_id)
        assert response.json()["meta"]["requestId"] == generated_id


def test_no_content_204_helper_returns_empty_body_without_json_content_type() -> None:
    app = create_app(env={"APP_ENV": "test"})

    @app.delete("/_test/no-content")
    async def ephemeral_no_content(request: Request) -> Response:
        return create_no_content_response(request)

    client = TestClient(app, raise_server_exceptions=False)
    incoming_id = "123e4567-e89b-42d3-a456-426614174000"
    response = client.delete("/_test/no-content", headers={"X-Request-Id": incoming_id})

    assert response.status_code == 204
    assert response.content == b""
    assert "content-type" not in response.headers
    assert response.headers["x-request-id"] == incoming_id


def test_created_response_preserves_location_and_request_correlation() -> None:
    app = create_app(env={"APP_ENV": "test"})

    @app.post("/_test/created")
    async def ephemeral_created(request: Request) -> Response:
        return create_success_response(
            request,
            {"id": "example"},
            status_code=201,
            headers={"Location": "/_test/resources/example"},
        )

    response = TestClient(app).post("/_test/created")
    assert response.status_code == 201
    assert response.headers["location"] == "/_test/resources/example"
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["meta"]["requestId"] == response.headers["x-request-id"]


def test_dotenv_loading_does_not_mutate_os_environ_and_redacts_secrets(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    secret_password = "S" * 40
    env_file.write_text(
        'APP_ENV="production"\n'
        'CHROMA_URL="http://chroma:8000"\n'
        'DOCS_ENABLED="true"\n'
        'DOCS_USERNAME="ops-admin"\n'
        f'DOCS_PASSWORD="{secret_password}"\n',
        encoding="utf-8",
    )

    sentinel_key = "DOCS_PASSWORD"
    original_value = os.environ.get(sentinel_key)

    settings = load_settings(env={}, env_file=env_file)

    assert os.environ.get(sentinel_key) == original_value
    assert settings.app_env == "production"
    assert settings.chroma_url == "http://chroma:8000"
    assert settings.docs_username == "ops-admin"
    assert settings.docs_password == secret_password
    assert secret_password not in repr(settings)
    assert secret_password not in str(settings)
    assert "[REDACTED]" in repr(settings)


def test_dotenv_filters_non_allowlisted_secrets_and_disables_variable_interpolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    literal_password = "literal-${DATABASE_URL}-${WAHA_API_KEY}-${PROCESS_ONLY_SECRET}-pass"
    env_file.write_text(
        'DATABASE_URL="postgresql://user:SUPER_SECRET_DB_PASS@localhost:5432/catering"\n'
        'WAHA_API_KEY="waha-super-secret-token"\n'
        'API_PORT="3001"\n'
        'AI_HOST="127.0.0.1"\n'
        'AI_PORT="8001"\n'
        'WORKER_PORT="3002"\n'
        'NEXT_PUBLIC_APP_NAME="Katering Si Kembar"\n'
        'APP_ENV="production"\n'
        'CHROMA_URL="http://chroma:8000/${API_PORT}"\n'
        'DOCS_ENABLED="true"\n'
        'DOCS_USERNAME="admin-${WAHA_API_KEY}"\n'
        f'DOCS_PASSWORD="{literal_password}"\n',
        encoding="utf-8",
    )

    monkeypatch.setenv("PROCESS_ONLY_SECRET", "process-secret-should-not-expand")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("WAHA_API_KEY", raising=False)

    parsed_file_values = _read_env_file(env_file)
    assert set(parsed_file_values.keys()) == {
        "APP_ENV",
        "CHROMA_URL",
        "DOCS_ENABLED",
        "DOCS_USERNAME",
        "DOCS_PASSWORD",
    }
    assert "DATABASE_URL" not in parsed_file_values
    assert "WAHA_API_KEY" not in parsed_file_values
    assert "AI_PORT" not in parsed_file_values

    settings = load_settings(
        env={
            "DATABASE_URL": "postgresql://override:secret@db:5432/app",
            "WAHA_API_KEY": "override-waha-secret",
            "PROCESS_ONLY_SECRET": "override-process-secret",
        },
        env_file=env_file,
    )

    assert os.environ.get("DATABASE_URL") is None
    assert os.environ.get("WAHA_API_KEY") is None
    assert settings.app_env == "production"
    assert settings.chroma_url == "http://chroma:8000/${API_PORT}"
    assert settings.docs_enabled_raw == "true"
    assert settings.docs_username == "admin-${WAHA_API_KEY}"
    assert settings.docs_password == literal_password
    assert "SUPER_SECRET_DB_PASS" not in settings.docs_password
    assert "waha-super-secret-token" not in settings.docs_username
    assert "process-secret-should-not-expand" not in settings.docs_password


def test_process_environment_overrides_root_dotenv_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    file_password = "F" * 36
    env_file.write_text(
        'APP_ENV="development"\n'
        'CHROMA_URL="http://file-chroma:8000"\n'
        'DOCS_ENABLED="false"\n'
        'DOCS_USERNAME="file-admin"\n'
        f'DOCS_PASSWORD="{file_password}"\n',
        encoding="utf-8",
    )

    monkeypatch.setattr("app.config.DEFAULT_ENV_PATH", env_file)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CHROMA_URL", "http://process-chroma:9000")
    monkeypatch.setenv("DOCS_ENABLED", "true")
    monkeypatch.delenv("DOCS_USERNAME", raising=False)
    monkeypatch.delenv("DOCS_PASSWORD", raising=False)

    settings_from_process = load_settings()
    assert settings_from_process.app_env == "production"
    assert settings_from_process.chroma_url == "http://process-chroma:9000"
    assert settings_from_process.docs_enabled_raw == "true"
    assert settings_from_process.docs_username == "file-admin"
    assert settings_from_process.docs_password == file_password

    explicit_override = load_settings(
        env={
            "APP_ENV": "test",
            "DOCS_USERNAME": "explicit-admin",
        },
        env_file=env_file,
    )
    assert explicit_override.app_env == "test"
    assert explicit_override.chroma_url == "http://file-chroma:8000"
    assert explicit_override.docs_enabled_raw == "false"
    assert explicit_override.docs_username == "explicit-admin"
    assert explicit_override.docs_password == file_password


def test_existing_directory_cannot_silently_replace_backend_dotenv(tmp_path: Path) -> None:
    invalid_source = tmp_path / ".env"
    invalid_source.mkdir()

    with pytest.raises(OSError):
        load_settings(env={}, env_file=invalid_source)

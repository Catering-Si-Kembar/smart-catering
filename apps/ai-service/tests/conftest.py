from __future__ import annotations

import re
from collections.abc import Callable, Mapping

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app

UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


@pytest.fixture
def make_app() -> Callable[[Mapping[str, str | None] | None], FastAPI]:
    """Factory fixture to build an isolated FastAPI app from an explicit env mapping."""

    def _make_app(env: Mapping[str, str | None] | None = None) -> FastAPI:
        effective_env: dict[str, str | None] = {
            "APP_ENV": "test",
            "DOCS_ENABLED": "true",
        }
        if env is not None:
            effective_env.update(env)
        return create_app(env=effective_env)

    return _make_app


@pytest.fixture
def make_client(
    make_app: Callable[[Mapping[str, str | None] | None], FastAPI],
) -> Callable[[Mapping[str, str | None] | None], TestClient]:
    """Factory fixture returning a TestClient with raise_server_exceptions=False."""

    def _make_client(env: Mapping[str, str | None] | None = None) -> TestClient:
        application = make_app(env)
        return TestClient(application, raise_server_exceptions=False)

    return _make_client

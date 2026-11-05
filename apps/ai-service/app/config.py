from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from dotenv import dotenv_values

DEFAULT_ENV_PATH: Final[Path] = Path(__file__).resolve().parent.parent.parent.parent / ".env"
VALID_APP_ENVS: Final[frozenset[str]] = frozenset({"development", "test", "production"})
ALLOWED_SETTING_KEYS: Final[frozenset[str]] = frozenset(
    {
        "APP_ENV",
        "CHROMA_URL",
        "DOCS_ENABLED",
        "DOCS_USERNAME",
        "DOCS_PASSWORD",
    }
)


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Immutable runtime configuration for the AI service with secret redaction."""

    app_env: str = "development"
    chroma_url: str = "http://127.0.0.1:8000"
    docs_enabled_raw: str | None = None
    docs_username: str = ""
    docs_password: str = ""

    def __repr__(self) -> str:
        return (
            f"AppSettings(app_env={self.app_env!r}, "
            f"chroma_url={self.chroma_url!r}, "
            f"docs_enabled_raw={self.docs_enabled_raw!r}, "
            f"docs_username={self.docs_username!r}, "
            "docs_password='[REDACTED]')"
        )

    def __str__(self) -> str:
        return self.__repr__()


def _filter_allowed_settings(values: Mapping[str, str | None]) -> dict[str, str | None]:
    return {key: value for key, value in values.items() if key in ALLOWED_SETTING_KEYS}


def _read_env_file(path: Path) -> dict[str, str | None]:
    try:
        with path.open(encoding="utf-8") as stream:
            return _filter_allowed_settings(dotenv_values(stream=stream, interpolate=False))
    except FileNotFoundError:
        return {}


def load_settings(
    env: Mapping[str, str | None] | None = None,
    *,
    env_file: Path | str | None = None,
) -> AppSettings:
    """Load service settings without mutating global os.environ."""
    if env is None:
        target_path = Path(env_file) if env_file is not None else DEFAULT_ENV_PATH
        file_values = _read_env_file(target_path)
        merged: dict[str, str | None] = {
            **file_values,
            **_filter_allowed_settings(os.environ),
        }
    else:
        if env_file is not None:
            file_values = _read_env_file(Path(env_file))
            merged = {**file_values, **_filter_allowed_settings(env)}
        else:
            merged = _filter_allowed_settings(env)

    raw_app_env = merged.get("APP_ENV")
    app_env = (
        raw_app_env.strip()
        if raw_app_env is not None and raw_app_env.strip() != ""
        else "development"
    )

    raw_chroma_url = merged.get("CHROMA_URL")
    chroma_url = (
        raw_chroma_url.strip()
        if raw_chroma_url is not None and raw_chroma_url.strip() != ""
        else "http://127.0.0.1:8000"
    )

    docs_enabled_raw = merged.get("DOCS_ENABLED")
    docs_username = merged.get("DOCS_USERNAME") or ""
    docs_password = merged.get("DOCS_PASSWORD") or ""

    return AppSettings(
        app_env=app_env,
        chroma_url=chroma_url,
        docs_enabled_raw=docs_enabled_raw,
        docs_username=docs_username,
        docs_password=docs_password,
    )

from __future__ import annotations

import base64
import binascii
import hmac
from typing import Final

from fastapi import Request, Response
from fastapi.responses import HTMLResponse
from scalar_fastapi import AgentScalarConfig, get_scalar_api_reference

from app.config import VALID_APP_ENVS, AppSettings
from app.context import REQUEST_ID_HEADER, get_request_id
from app.errors import DOCS_SECURITY_HEADERS, AppProblemError

SCALAR_CDN_URL: Final[str] = "https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4"
DOCS_WWW_AUTHENTICATE: Final[str] = 'Basic realm="Smart Catering Docs", charset="UTF-8"'
MIN_PRODUCTION_DOCS_PASSWORD_LENGTH: Final[int] = 32


def _is_valid_production_username(username: str) -> bool:
    if len(username.strip()) == 0:
        return False
    if ":" in username or "\r" in username or "\n" in username:
        return False
    return True


def _is_valid_production_password(password: str) -> bool:
    if len(password) < MIN_PRODUCTION_DOCS_PASSWORD_LENGTH:
        return False
    if "\r" in password or "\n" in password:
        return False
    return True


def _resolve_docs_enabled(settings: AppSettings) -> bool:
    if settings.app_env not in VALID_APP_ENVS:
        raise AppProblemError(status_code=500, headers=DOCS_SECURITY_HEADERS)

    raw = settings.docs_enabled_raw
    trimmed = raw.strip() if raw is not None else ""
    if trimmed == "":
        return settings.app_env in {"development", "test"}
    if trimmed == "true":
        return True
    if trimmed == "false":
        return False

    raise AppProblemError(status_code=500, headers=DOCS_SECURITY_HEADERS)


def _parse_basic_authorization(header_value: str | None) -> tuple[str, str] | None:
    if header_value is None:
        return None
    parts = header_value.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "basic":
        return None
    token = parts[1].strip()
    if not token:
        return None
    try:
        decoded_bytes = base64.b64decode(token, validate=True)
        decoded_str = decoded_bytes.decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None

    if ":" not in decoded_str:
        return None
    username, password = decoded_str.split(":", 1)
    return username, password


def verify_docs_access(request: Request, settings: AppSettings) -> None:
    """Enforce DOCS_ENABLED gating and production HTTP Basic authentication."""
    enabled = _resolve_docs_enabled(settings)
    if not enabled:
        raise AppProblemError(status_code=404, headers=DOCS_SECURITY_HEADERS)

    if settings.app_env == "production":
        expected_user = settings.docs_username
        expected_pass = settings.docs_password
        if not (
            _is_valid_production_username(expected_user)
            and _is_valid_production_password(expected_pass)
        ):
            raise AppProblemError(status_code=500, headers=DOCS_SECURITY_HEADERS)

        expected_user_bytes = expected_user.encode("utf-8")
        expected_pass_bytes = expected_pass.encode("utf-8")

        parsed = _parse_basic_authorization(request.headers.get("authorization"))
        if parsed is None:
            hmac.compare_digest(b"", expected_user_bytes)
            hmac.compare_digest(b"", expected_pass_bytes)
            raise AppProblemError(
                status_code=401,
                headers={
                    **DOCS_SECURITY_HEADERS,
                    "WWW-Authenticate": DOCS_WWW_AUTHENTICATE,
                },
            )

        provided_user, provided_pass = parsed
        user_matches = hmac.compare_digest(provided_user.encode("utf-8"), expected_user_bytes)
        pass_matches = hmac.compare_digest(provided_pass.encode("utf-8"), expected_pass_bytes)
        if not (user_matches and pass_matches):
            raise AppProblemError(
                status_code=401,
                headers={
                    **DOCS_SECURITY_HEADERS,
                    "WWW-Authenticate": DOCS_WWW_AUTHENTICATE,
                },
            )


def render_scalar_docs_response(
    request: Request,
    *,
    title: str = "Smart Catering AI Service API Reference",
) -> Response:
    """Render Scalar API Reference HTML pinned to @scalar/api-reference@1.76.4."""
    request_id = get_request_id(request)
    html_response: HTMLResponse = get_scalar_api_reference(
        openapi_url="/openapi.json",
        title=title,
        scalar_js_url=SCALAR_CDN_URL,
        scalar_favicon_url="data:,",
        scalar_proxy_url="",
        persist_auth=False,
        with_default_fonts=False,
        telemetry=False,
        show_developer_tools="never",
        agent=AgentScalarConfig(disabled=True),
        overrides={"persistAuth": False},
    )
    for key, value in DOCS_SECURITY_HEADERS.items():
        html_response.headers[key] = value
    html_response.headers[REQUEST_ID_HEADER] = request_id

    if request.method == "HEAD":
        return Response(
            content=b"",
            status_code=200,
            headers=dict(html_response.headers),
            media_type="text/html; charset=utf-8",
        )
    return html_response

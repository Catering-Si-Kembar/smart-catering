from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import AppSettings, load_settings
from app.context import (
    REQUEST_ID_HEADER,
    get_request_id,
    normalize_or_generate_request_id,
    reset_current_request_id,
    set_current_request_id,
)
from app.docs import render_scalar_docs_response, verify_docs_access
from app.errors import (
    DOCS_PATHS,
    DOCS_SECURITY_HEADERS,
    create_problem_response,
    register_exception_handlers,
)
from app.insight.service import BusinessInsightService, build_default_insight_service
from app.ml.sentiment.inference import SentimentClassifierService
from app.openapi import build_openapi_schema
from app.rag.service import AgenticRagService, build_default_rag_service
from app.responses import create_success_response
from app.routers import v1_router
from app.schemas import HealthData, HealthResponse

logger = logging.getLogger("smart_catering.ai_service")
PROCESS_TIME_HEADER: Final[str] = "X-Process-Time-Ms"


class SmartCateringFastAPI(FastAPI):
    """FastAPI application subclass caching the canonical OpenAPI 3.1.0 schema."""

    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema is None:
            self.openapi_schema = build_openapi_schema(super().openapi())
        return self.openapi_schema


class RequestContextAndSafetyMiddleware:
    """Pure ASGI middleware guaranteeing single requestId, HEAD body stripping, and 500 fallback."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = time.perf_counter()
        raw_request_id: str | None = None
        for header_name, header_val in scope.get("headers", ()):
            if header_name.lower() == b"x-request-id":
                raw_request_id = header_val.decode("latin-1")
                break

        request_id = normalize_or_generate_request_id(raw_request_id)
        scope = {**scope, "state": {**scope.get("state", {}), "request_id": request_id}}

        token = set_current_request_id(request_id)
        method = str(scope.get("method", "GET")).upper()
        is_head_request = method == "HEAD"
        pathname = scope.get("path") or "/"
        is_docs_path = pathname in DOCS_PATHS
        response_started = False
        current_status_code = 200

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started, current_status_code
            if message["type"] == "http.response.start":
                response_started = True
                current_status_code = int(message.get("status", 200))
                raw_headers: list[tuple[bytes, bytes]] = list(message.get("headers", ()))

                filtered_headers: list[tuple[bytes, bytes]] = []
                for k, v in raw_headers:
                    lower_k = k.lower()
                    if lower_k in {b"x-request-id", b"x-process-time-ms"}:
                        continue
                    if current_status_code == 204 and lower_k in {
                        b"content-type",
                        b"content-length",
                    }:
                        continue
                    if is_docs_path and lower_k in {b"cache-control", b"vary"}:
                        continue
                    filtered_headers.append((k, v))

                if is_docs_path:
                    filtered_headers.append((b"cache-control", b"private, no-store"))
                    filtered_headers.append((b"vary", b"Authorization"))

                duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
                filtered_headers.append(
                    (REQUEST_ID_HEADER.lower().encode("ascii"), request_id.encode("ascii"))
                )
                filtered_headers.append(
                    (
                        PROCESS_TIME_HEADER.lower().encode("ascii"),
                        f"{duration_ms:.2f}".encode("ascii"),
                    )
                )
                message = {**message, "headers": filtered_headers}
                await send(message)
                return

            if message["type"] == "http.response.body":
                if is_head_request or current_status_code == 204:
                    message = {**message, "body": b""}
                await send(message)
                return

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            logger.error(
                "Unhandled ASGI exception type=%s requestId=%s instance=%s",
                exc.__class__.__name__,
                request_id,
                pathname,
            )
            if response_started:
                raise
            current_status_code = 500
            error_response = create_problem_response(Request(scope), status_code=500)
            await error_response(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
            log_payload = {
                "event": "http_request",
                "method": method,
                "path": pathname,
                "status": current_status_code,
                "durationMs": duration_ms,
                "requestId": request_id,
            }
            log_line = json.dumps(log_payload, separators=(",", ":"))
            if current_status_code >= 500:
                logger.error(log_line)
            else:
                logger.info(log_line)
            reset_current_request_id(token)


def create_app(
    settings: AppSettings | None = None,
    *,
    env: Mapping[str, str | None] | None = None,
    env_file: Path | str | None = None,
    sentiment_service: SentimentClassifierService | None = None,
    insight_service: BusinessInsightService | None = None,
    rag_service: AgenticRagService | None = None,
) -> FastAPI:
    """Create a configured FastAPI application instance with isolated settings."""
    resolved_settings = (
        settings if settings is not None else load_settings(env=env, env_file=env_file)
    )

    app = SmartCateringFastAPI(
        title="Smart Catering AI Service API",
        version="0.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = resolved_settings
    app.state.sentiment_service = (
        sentiment_service if sentiment_service is not None else SentimentClassifierService()
    )
    app.state.insight_service = (
        insight_service
        if insight_service is not None
        else build_default_insight_service(resolved_settings)
    )
    app.state.rag_service = (
        rag_service if rag_service is not None else build_default_rag_service(resolved_settings)
    )

    register_exception_handlers(app)
    app.add_middleware(RequestContextAndSafetyMiddleware)
    app.include_router(v1_router)

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["System"],
        summary="Check AI service liveness",
    )
    async def get_health(request: Request) -> Response:
        return create_success_response(
            request,
            HealthData(status="ok", service="ai-service"),
        )

    @app.head("/health", include_in_schema=False)
    async def head_health(request: Request) -> Response:
        response = create_success_response(
            request,
            HealthData(status="ok", service="ai-service"),
        )
        return Response(
            content=b"",
            status_code=200,
            headers=dict(response.headers),
            media_type="application/json",
        )

    @app.api_route("/openapi.json", methods=["GET", "HEAD"], include_in_schema=False)
    async def get_openapi_spec(request: Request) -> Response:
        verify_docs_access(request, resolved_settings)
        request_id = get_request_id(request)
        headers = {
            **DOCS_SECURITY_HEADERS,
            REQUEST_ID_HEADER: request_id,
        }
        spec_response = JSONResponse(
            status_code=200,
            content=app.openapi(),
            headers=headers,
        )
        if request.method == "HEAD":
            return Response(
                content=b"",
                status_code=200,
                headers=dict(spec_response.headers),
                media_type="application/json",
            )
        return spec_response

    @app.api_route("/docs", methods=["GET", "HEAD"], include_in_schema=False)
    async def get_scalar_docs(request: Request) -> Response:
        verify_docs_access(request, resolved_settings)
        return render_scalar_docs_response(
            request,
            title="Smart Catering AI Service API Reference",
        )

    return app


app = create_app()

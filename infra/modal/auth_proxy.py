from __future__ import annotations

import hmac
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Final

logger = logging.getLogger("smart_catering.modal.auth_proxy")

ALLOWED_GET_PATHS: Final[frozenset[str]] = frozenset({"/health", "/v1/models"})
ALLOWED_POST_PATHS: Final[frozenset[str]] = frozenset({"/v1/chat/completions"})
MAX_REQUEST_BODY_BYTES: Final[int] = 1_048_576  # 1 MiB safety cap


def verify_bearer_authorization(auth_header: str | None, expected_token: str) -> bool:
    """Constant-time verification of an Authorization: Bearer <token> header."""
    if not auth_header or not expected_token:
        return False
    parts = auth_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False
    provided = parts[1].strip()
    if not provided:
        return False
    return hmac.compare_digest(provided, expected_token)


class ProxyRuntimeState:
    """Thread-safe container runtime state tracking first-inference cold start."""

    def __init__(
        self,
        *,
        expected_token: str,
        upstream_base_url: str,
        served_model_name: str,
        upstream_timeout_seconds: float = 120.0,
        upstream_health_check: Callable[[], bool] | None = None,
    ) -> None:
        self.expected_token = expected_token
        self.upstream_base_url = upstream_base_url.rstrip("/")
        self.served_model_name = served_model_name
        self.upstream_timeout_seconds = upstream_timeout_seconds
        self._upstream_health_check = upstream_health_check
        self._lock = threading.Lock()
        self._first_inference_completed = False

    def is_upstream_alive(self) -> bool:
        """Return False if an attached upstream process liveness probe reports a crash."""
        if self._upstream_health_check is None:
            return True
        return bool(self._upstream_health_check())

    def consume_cold_start_flag(self) -> bool:
        """Return True only for the first authenticated inference request after container boot."""
        with self._lock:
            if not self._first_inference_completed:
                self._first_inference_completed = True
                return True
            return False


class AuthenticatedModalProxyServer(ThreadingHTTPServer):
    """Threading HTTP server enforcing Bearer auth on all exposed vLLM routes."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        runtime_state: ProxyRuntimeState,
    ) -> None:
        self.runtime_state = runtime_state
        super().__init__(server_address, _ModalAuthProxyHandler)


class _ModalAuthProxyHandler(BaseHTTPRequestHandler):
    """Authenticated reverse proxy guarding /health, /v1/models, and /v1/chat/completions."""

    server: AuthenticatedModalProxyServer

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Suppress default stderr access log that could leak query strings or headers.
        del format, args

    def do_GET(self) -> None:  # noqa: N802
        self._handle_request("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle_request("POST")

    def _send_json(
        self,
        status_code: int,
        payload: dict[str, Any],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(encoded)

    def _handle_request(self, method: str) -> None:
        started_at = time.perf_counter()
        state = self.server.runtime_state
        path = self.path.split("?", 1)[0]

        if not verify_bearer_authorization(
            self.headers.get("Authorization"),
            state.expected_token,
        ):
            self._send_json(
                401,
                {
                    "error": {
                        "message": "Unauthorized: invalid or missing Bearer token.",
                        "type": "authentication_error",
                    }
                },
                extra_headers={"WWW-Authenticate": "Bearer"},
            )
            self._log_event(method, path, 401, started_at, cold_start=False)
            return

        if method == "GET" and path not in ALLOWED_GET_PATHS:
            self._send_json(
                404,
                {"error": {"message": "Not found.", "type": "invalid_request_error"}},
            )
            self._log_event(method, path, 404, started_at, cold_start=False)
            return

        if method == "POST" and path not in ALLOWED_POST_PATHS:
            self._send_json(
                404,
                {"error": {"message": "Not found.", "type": "invalid_request_error"}},
            )
            self._log_event(method, path, 404, started_at, cold_start=False)
            return

        if not state.is_upstream_alive():
            self._send_json(
                503,
                {
                    "status": "unhealthy",
                    "error": {
                        "message": "Internal vLLM worker process is not running.",
                        "type": "service_unavailable",
                    },
                },
            )
            self._log_event(method, path, 503, started_at, cold_start=False)
            return

        body_bytes: bytes | None = None
        if method == "POST":
            raw_len = self.headers.get("Content-Length")
            try:
                content_length = int(raw_len) if raw_len is not None else 0
            except ValueError:
                self._send_json(
                    400,
                    {"error": {"message": "Invalid Content-Length header."}},
                )
                return
            if content_length <= 0 or content_length > MAX_REQUEST_BODY_BYTES:
                self._send_json(
                    413 if content_length > MAX_REQUEST_BODY_BYTES else 400,
                    {"error": {"message": "Request body size is empty or exceeds limit."}},
                )
                return
            body_bytes = self.rfile.read(content_length)

        upstream_url = f"{state.upstream_base_url}{path}"
        upstream_headers: dict[str, str] = {
            "Accept": "application/json",
            "Authorization": f"Bearer {state.expected_token}",
        }
        if body_bytes is not None:
            upstream_headers["Content-Type"] = self.headers.get(
                "Content-Type",
                "application/json",
            )

        is_cold_start = (
            state.consume_cold_start_flag()
            if method == "POST" and path == "/v1/chat/completions"
            else False
        )
        req = urllib.request.Request(
            upstream_url,
            data=body_bytes,
            headers=upstream_headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(  # noqa: S310
                req,
                timeout=state.upstream_timeout_seconds,
            ) as resp:
                resp_status = int(resp.status)
                resp_body = resp.read()
                resp_content_type = resp.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as exc:
            resp_status = int(exc.code)
            resp_body = exc.read()
            resp_content_type = (
                exc.headers.get("Content-Type", "application/json")
                if exc.headers
                else "application/json"
            )
        except TimeoutError:
            self._send_json(
                504,
                {
                    "error": {
                        "message": "Upstream vLLM inference timed out.",
                        "type": "timeout_error",
                    }
                },
            )
            self._log_event(method, path, 504, started_at, cold_start=is_cold_start)
            return
        except urllib.error.URLError:
            self._send_json(
                503,
                {
                    "error": {
                        "message": "Upstream vLLM server is starting or temporarily unavailable.",
                        "type": "service_unavailable",
                    }
                },
            )
            self._log_event(method, path, 503, started_at, cold_start=is_cold_start)
            return

        if method == "GET" and path == "/health" and resp_status == 200 and not resp_body.strip():
            self._send_json(
                200,
                {
                    "status": "healthy",
                    "service": "modal-vllm",
                    "model": state.served_model_name,
                },
            )
            self._log_event(method, path, 200, started_at, cold_start=False)
            return

        self.send_response(resp_status)
        self.send_header("Content-Type", resp_content_type)
        self.send_header("Content-Length", str(len(resp_body)))
        self.send_header("Cache-Control", "no-store")
        if method == "POST" and path == "/v1/chat/completions":
            self.send_header("X-Modal-Cold-Start", "true" if is_cold_start else "false")
        self.end_headers()
        self.wfile.write(resp_body)
        self._log_event(method, path, resp_status, started_at, cold_start=is_cold_start)

    def _log_event(
        self,
        method: str,
        path: str,
        status: int,
        started_at: float,
        *,
        cold_start: bool,
    ) -> None:
        duration_ms = round((time.perf_counter() - started_at) * 1000.0, 2)
        payload = {
            "event": "modal_vllm_request",
            "method": method,
            "path": path,
            "status": status,
            "durationMs": duration_ms,
            "coldStart": cold_start,
        }
        logger.info(json.dumps(payload, separators=(",", ":")))


def create_auth_proxy_server(
    *,
    host: str,
    port: int,
    expected_token: str,
    upstream_base_url: str,
    served_model_name: str,
    upstream_timeout_seconds: float = 120.0,
    upstream_health_check: Callable[[], bool] | None = None,
) -> AuthenticatedModalProxyServer:
    """Create a configured authenticated reverse proxy server for vLLM."""
    state = ProxyRuntimeState(
        expected_token=expected_token,
        upstream_base_url=upstream_base_url,
        served_model_name=served_model_name,
        upstream_timeout_seconds=upstream_timeout_seconds,
        upstream_health_check=upstream_health_check,
    )
    return AuthenticatedModalProxyServer((host, port), state)

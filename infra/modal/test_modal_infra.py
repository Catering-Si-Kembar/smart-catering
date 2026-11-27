from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from infra.modal.auth_proxy import (
    AuthenticatedModalProxyServer,
    create_auth_proxy_server,
    verify_bearer_authorization,
)
from infra.modal.config import (
    DEPLOYMENT_PROFILES,
    build_vllm_serve_command,
    estimate_inference_cost_usd,
    resolve_auth_token,
    resolve_profile,
)
from infra.modal.serve_vllm import (
    ACTIVE_PROFILE,
    APP_NAME,
    SECRET_NAME,
    build_container_env,
    wait_for_vllm_ready,
)
from infra.modal.smoke_test import run_smoke_suite

TEST_TOKEN = "modal-secret-test-token-1234567890"


class _FakeVLLMUpstreamHandler(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible vLLM stub for offline proxy & smoke testing."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        del format, args

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/v1/models":
            body = json.dumps({"data": [{"id": "Qwen/Qwen2.5-7B-Instruct"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(length)
        insight_content = json.dumps(
            {
                "executive_summary": "Sepanjang November 2026 tercatat 38 pesanan (Rp24.500.000).",
                "key_highlights": ["Tingkat penyelesaian 34 dari 38 pesanan."],
                "operational_recommendations": ["Tagih H-1 untuk 4 invoice belum lunas."],
            },
            ensure_ascii=False,
        )
        body = json.dumps(
            {
                "model": "Qwen/Qwen2.5-7B-Instruct",
                "choices": [{"message": {"role": "assistant", "content": insight_content}}],
                "usage": {"total_tokens": 210},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _start_proxy_with_fake_vllm() -> tuple[
    ThreadingHTTPServer,
    AuthenticatedModalProxyServer,
    str,
]:
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), _FakeVLLMUpstreamHandler)
    upstream_port = upstream.server_address[1]
    threading.Thread(target=upstream.serve_forever, daemon=True).start()

    proxy = create_auth_proxy_server(
        host="127.0.0.1",
        port=0,
        expected_token=TEST_TOKEN,
        upstream_base_url=f"http://127.0.0.1:{upstream_port}",
        served_model_name="Qwen/Qwen2.5-7B-Instruct",
    )
    proxy_port = proxy.server_address[1]
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    return upstream, proxy, f"http://127.0.0.1:{proxy_port}"


def test_resolve_profile_supports_primary_fallback_and_validates_scale_to_zero() -> None:
    primary = resolve_profile({})
    assert primary.name == "primary"
    assert primary.model_id == "Qwen/Qwen2.5-7B-Instruct"
    assert primary.gpu == "L4"
    assert primary.scaledown_window_seconds == 60

    fallback = resolve_profile({"MODAL_SLM_PROFILE": "fallback"})
    assert fallback.name == "fallback"
    assert fallback.model_id == "Qwen/Qwen2.5-3B-Instruct"
    assert fallback.gpu == "T4"

    awq = resolve_profile({"MODAL_SLM_PROFILE": "fallback_awq"})
    assert awq.quantization == "awq"
    assert awq.gpu == "T4"

    custom = resolve_profile(
        {
            "MODAL_SLM_PROFILE": "primary",
            "MODAL_GPU": "a10g",
            "MODAL_SCALEDOWN_WINDOW": "90",
        }
    )
    assert custom.gpu == "A10G"
    assert custom.scaledown_window_seconds == 90

    with pytest.raises(ValueError, match="Unsupported MODAL_SLM_PROFILE"):
        resolve_profile({"MODAL_SLM_PROFILE": "nonexistent"})

    with pytest.raises(ValueError, match="scale-to-zero"):
        resolve_profile({"MODAL_SCALEDOWN_WINDOW": "0"})

    with pytest.raises(ValueError, match="Unsupported MODAL_GPU"):
        resolve_profile({"MODAL_GPU": "H100_UNAPPROVED"})


def test_resolve_auth_token_and_vllm_command_builder() -> None:
    assert resolve_auth_token({"MODAL_API_KEY": TEST_TOKEN}) == TEST_TOKEN
    assert resolve_auth_token({"MODAL_AUTH_TOKEN": TEST_TOKEN}) == TEST_TOKEN

    with pytest.raises(ValueError, match="MODAL_API_KEY"):
        resolve_auth_token({})
    with pytest.raises(ValueError, match="MODAL_API_KEY"):
        resolve_auth_token({"MODAL_API_KEY": "short"})

    cmd_primary = build_vllm_serve_command(DEPLOYMENT_PROFILES["primary"], api_key=TEST_TOKEN)
    assert cmd_primary[:3] == ["vllm", "serve", "Qwen/Qwen2.5-7B-Instruct"]
    assert "--api-key" in cmd_primary
    assert "--enforce-eager" in cmd_primary
    assert "--quantization" not in cmd_primary

    cmd_awq = build_vllm_serve_command(DEPLOYMENT_PROFILES["fallback_awq"], api_key=TEST_TOKEN)
    assert "--quantization" in cmd_awq
    assert "awq" in cmd_awq
    assert "awq_marlin" not in cmd_awq

    assert estimate_inference_cost_usd(DEPLOYMENT_PROFILES["fallback"], 10.0) == pytest.approx(
        0.00164
    )


def test_verify_bearer_authorization_uses_strict_scheme_and_token() -> None:
    assert verify_bearer_authorization(f"Bearer {TEST_TOKEN}", TEST_TOKEN) is True
    assert verify_bearer_authorization(f"bearer {TEST_TOKEN}", TEST_TOKEN) is True
    assert verify_bearer_authorization(None, TEST_TOKEN) is False
    assert verify_bearer_authorization("Basic abc", TEST_TOKEN) is False
    assert verify_bearer_authorization("Bearer wrong-token", TEST_TOKEN) is False


def test_auth_proxy_enforces_401_allowlist_and_cold_start_header() -> None:
    upstream, proxy, base_url = _start_proxy_with_fake_vllm()
    try:
        # 1. Missing token on /health -> 401
        with pytest.raises(urllib.error.HTTPError) as exc_401:
            urllib.request.urlopen(f"{base_url}/health", timeout=5.0)
        assert exc_401.value.code == 401
        assert TEST_TOKEN not in exc_401.value.read().decode("utf-8")

        # 2. Disallowed internal path (/metrics) even with valid token -> 404
        req_metrics = urllib.request.Request(
            f"{base_url}/metrics",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            method="GET",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_404:
            urllib.request.urlopen(req_metrics, timeout=5.0)
        assert exc_404.value.code == 404

        # 3. Valid /health -> 200 JSON with model info
        req_health = urllib.request.Request(
            f"{base_url}/health",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            method="GET",
        )
        with urllib.request.urlopen(req_health, timeout=5.0) as resp_health:
            assert resp_health.status == 200
            health_json: dict[str, Any] = json.loads(resp_health.read().decode("utf-8"))
            assert health_json["status"] == "healthy"
            assert health_json["model"] == "Qwen/Qwen2.5-7B-Instruct"

        # 4. Run full smoke_test suite (checks 401, 200 /health, cold start true -> warm false)
        report = run_smoke_suite(
            base_url=f"{base_url}/v1",
            api_key=TEST_TOKEN,
            profile=DEPLOYMENT_PROFILES["primary"],
            warm_runs=2,
            timeout_seconds=10.0,
        )
        assert report.unauthenticated_health_status == 401
        assert report.invalid_token_chat_status == 401
        assert report.authenticated_health_status == 200
        assert report.cold_start_header == "true"
        assert len(report.warm_latencies_ms) == 2
        assert report.json_output_valid is True
        assert report.estimated_total_gpu_cost_usd >= 0.0
    finally:
        proxy.shutdown()
        proxy.server_close()
        upstream.shutdown()
        upstream.server_close()


def test_serve_vllm_module_metadata_container_env_and_readiness_wait() -> None:
    assert APP_NAME == "smart-catering-slm"
    assert SECRET_NAME == "smart-catering-modal-secret"
    assert ACTIVE_PROFILE.scaledown_window_seconds == 60

    fallback_env = build_container_env(DEPLOYMENT_PROFILES["fallback"])
    assert fallback_env["MODAL_SLM_PROFILE"] == "fallback"
    assert fallback_env["MODAL_SLM_MODEL"] == "Qwen/Qwen2.5-3B-Instruct"
    assert fallback_env["MODAL_GPU"] == "T4"
    assert fallback_env["MODAL_SCALEDOWN_WINDOW"] == "60"
    assert "MODAL_API_KEY" not in fallback_env

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), _FakeVLLMUpstreamHandler)
    port = upstream.server_address[1]
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    try:
        wait_for_vllm_ready(
            health_url=f"http://127.0.0.1:{port}/health",
            timeout_seconds=3.0,
            poll_interval_seconds=0.05,
        )
    finally:
        upstream.shutdown()
        upstream.server_close()

    # Fail-fast when internal vLLM subprocess exits prematurely
    exited_proc = subprocess.Popen([sys.executable, "-c", "raise SystemExit(2)"])
    exited_proc.wait(timeout=5.0)
    with pytest.raises(RuntimeError, match="exited prematurely with code 2"):
        wait_for_vllm_ready(
            health_url="http://127.0.0.1:9/health",
            timeout_seconds=5.0,
            poll_interval_seconds=0.05,
            process=exited_proc,
        )


def test_auth_proxy_reports_503_unhealthy_when_upstream_process_exits() -> None:
    alive = False
    proxy = create_auth_proxy_server(
        host="127.0.0.1",
        port=0,
        expected_token=TEST_TOKEN,
        upstream_base_url="http://127.0.0.1:9",
        served_model_name="Qwen/Qwen2.5-7B-Instruct",
        upstream_health_check=lambda: alive,
    )
    proxy_port = proxy.server_address[1]
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{proxy_port}/health",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            method="GET",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_503:
            urllib.request.urlopen(req, timeout=5.0)
        assert exc_503.value.code == 503
        body = json.loads(exc_503.value.read().decode("utf-8"))
        assert body["status"] == "unhealthy"
    finally:
        proxy.shutdown()
        proxy.server_close()

"""Live smoke test & cold-start/warm-latency probe for Modal GPU vLLM deployment (OPS-04).

Usage:
    MODAL_SLM_BASE_URL="https://<workspace>--smart-catering-slm-serve.modal.run/v1" \
    MODAL_API_KEY="<secret>" \
    python infra/modal/smoke_test.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    _repo_root = str(Path(__file__).resolve().parents[2])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

from infra.modal.config import (
    ModalDeploymentProfile,
    estimate_inference_cost_usd,
    resolve_auth_token,
    resolve_profile,
)


@dataclass(frozen=True, slots=True)
class SmokeTestReport:
    """Structured live verification result for OPS-04 documentation and spreadsheet logs."""

    profile_name: str
    gpu: str
    model_used: str
    unauthenticated_health_status: int
    invalid_token_chat_status: int
    authenticated_health_status: int
    cold_start_latency_ms: int
    cold_start_header: str | None
    warm_latencies_ms: list[int]
    avg_warm_latency_ms: float
    estimated_total_gpu_cost_usd: float
    json_output_valid: bool


def _http_call(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
    timeout_seconds: float = 90.0,
) -> tuple[int, dict[str, str], bytes, int]:
    data = json.dumps(json_body, ensure_ascii=False).encode("utf-8") if json_body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # noqa: S310
            elapsed_ms = int(round((time.perf_counter() - started) * 1000.0))
            return int(resp.status), dict(resp.headers.items()), resp.read(), elapsed_ms
    except urllib.error.HTTPError as exc:
        elapsed_ms = int(round((time.perf_counter() - started) * 1000.0))
        hdrs = dict(exc.headers.items()) if exc.headers else {}
        return int(exc.code), hdrs, exc.read(), elapsed_ms


def _normalize_origin_and_v1(base_url: str) -> tuple[str, str]:
    cleaned = base_url.strip().rstrip("/")
    if cleaned.endswith("/v1/chat/completions"):
        origin = cleaned[: -len("/v1/chat/completions")]
        return origin, f"{origin}/v1"
    if cleaned.endswith("/v1"):
        origin = cleaned[: -len("/v1")]
        return origin, cleaned
    return cleaned, f"{cleaned}/v1"


def _sample_ai06_chat_payload(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Keluarkan hanya objek JSON valid dengan kunci executive_summary, "
                    "key_highlights (array), dan operational_recommendations (array) "
                    "menggunakan angka persis dari input."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Periode: November 2026. Total pesanan: 38, selesai: 34, omzet: "
                    "Rp24.500.000, invoice belum lunas: 4, proyeksi minggu depan: 450 porsi."
                ),
            },
        ],
    }


def run_smoke_suite(
    *,
    base_url: str,
    api_key: str,
    profile: ModalDeploymentProfile,
    warm_runs: int = 2,
    timeout_seconds: float = 90.0,
) -> SmokeTestReport:
    """Execute auth rejection (401), health (200), cold-start, and warm-latency probes."""
    origin, v1_url = _normalize_origin_and_v1(base_url)
    health_url = f"{origin}/health"
    chat_url = f"{v1_url}/chat/completions"
    payload = _sample_ai06_chat_payload(profile.served_model_name)

    # 1. Unauthenticated /health must return 401
    unauth_health_status, _, _, _ = _http_call(
        method="GET",
        url=health_url,
        headers={"Accept": "application/json"},
        timeout_seconds=timeout_seconds,
    )
    if unauth_health_status != 401:
        raise RuntimeError(f"Expected 401 on unauthenticated /health, got {unauth_health_status}.")

    # 2. Invalid Bearer token on /v1/chat/completions must return 401
    invalid_chat_status, _, _, _ = _http_call(
        method="POST",
        url=chat_url,
        headers={
            "Authorization": "Bearer invalid-token-must-be-rejected",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json_body=payload,
        timeout_seconds=timeout_seconds,
    )
    if invalid_chat_status != 401:
        raise RuntimeError(f"Expected 401 on invalid token chat, got {invalid_chat_status}.")

    # 3. Authenticated /health must return 200
    auth_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    auth_health_status, _, _, _ = _http_call(
        method="GET",
        url=health_url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        timeout_seconds=timeout_seconds,
    )
    if auth_health_status != 200:
        raise RuntimeError(f"Expected 200 on authenticated /health, got {auth_health_status}.")

    # 4. Request #1 (cold start measurement) + warm runs
    cold_status, cold_headers, cold_body, cold_latency_ms = _http_call(
        method="POST",
        url=chat_url,
        headers=auth_headers,
        json_body=payload,
        timeout_seconds=timeout_seconds,
    )
    if cold_status != 200:
        raise RuntimeError(f"Expected 200 on first chat completion, got {cold_status}.")

    parsed_first = json.loads(cold_body.decode("utf-8"))
    content_first = str(parsed_first["choices"][0]["message"]["content"]).strip()
    parsed_insight = json.loads(content_first)
    json_valid = isinstance(parsed_insight, dict) and {
        "executive_summary",
        "key_highlights",
        "operational_recommendations",
    }.issubset(parsed_insight.keys())

    lower_cold_headers = {k.lower(): v for k, v in cold_headers.items()}
    cold_header = lower_cold_headers.get("x-modal-cold-start")

    warm_latencies: list[int] = []
    for _ in range(max(1, warm_runs)):
        w_status, _, _, w_ms = _http_call(
            method="POST",
            url=chat_url,
            headers=auth_headers,
            json_body=payload,
            timeout_seconds=timeout_seconds,
        )
        if w_status != 200:
            raise RuntimeError(f"Expected 200 on warm chat completion, got {w_status}.")
        warm_latencies.append(w_ms)

    total_active_seconds = (cold_latency_ms + sum(warm_latencies)) / 1000.0
    estimated_cost = estimate_inference_cost_usd(profile, total_active_seconds)
    avg_warm = round(sum(warm_latencies) / len(warm_latencies), 2)

    return SmokeTestReport(
        profile_name=profile.name,
        gpu=profile.gpu,
        model_used=str(parsed_first.get("model") or profile.served_model_name),
        unauthenticated_health_status=unauth_health_status,
        invalid_token_chat_status=invalid_chat_status,
        authenticated_health_status=auth_health_status,
        cold_start_latency_ms=cold_latency_ms,
        cold_start_header=cold_header,
        warm_latencies_ms=warm_latencies,
        avg_warm_latency_ms=avg_warm,
        estimated_total_gpu_cost_usd=estimated_cost,
        json_output_valid=json_valid,
    )


def _main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Modal GPU vLLM deployment (OPS-04).")
    parser.add_argument("--base-url", default=os.environ.get("MODAL_SLM_BASE_URL", ""))
    parser.add_argument("--warm-runs", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    if not args.base_url.strip():
        print("Error: MODAL_SLM_BASE_URL or --base-url is required.", file=sys.stderr)
        return 2

    profile = resolve_profile(os.environ)
    api_key = resolve_auth_token(os.environ)
    report = run_smoke_suite(
        base_url=args.base_url,
        api_key=api_key,
        profile=profile,
        warm_runs=args.warm_runs,
        timeout_seconds=args.timeout,
    )
    print(json.dumps(report.__dict__, indent=2, ensure_ascii=False))
    return 0 if report.json_output_valid else 1


if __name__ == "__main__":
    raise SystemExit(_main())

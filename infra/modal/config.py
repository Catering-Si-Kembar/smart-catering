from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Final

MIN_SCALEDOWN_WINDOW_SECONDS: Final[int] = 15
MAX_SCALEDOWN_WINDOW_SECONDS: Final[int] = 300
MIN_AUTH_TOKEN_LENGTH: Final[int] = 16


@dataclass(frozen=True, slots=True)
class ModalDeploymentProfile:
    """Validated Modal GPU + vLLM runtime profile for AI Business Insight (OPS-04)."""

    name: str
    model_id: str
    served_model_name: str
    gpu: str
    max_model_len: int = 4096
    gpu_memory_utilization: float = 0.90
    dtype: str = "auto"
    quantization: str | None = None
    enforce_eager: bool = True
    scaledown_window_seconds: int = 60
    startup_timeout_seconds: int = 600
    max_concurrent_inputs: int = 8
    estimated_usd_per_gpu_second: float = 0.000222


DEPLOYMENT_PROFILES: Final[dict[str, ModalDeploymentProfile]] = {
    "primary": ModalDeploymentProfile(
        name="primary",
        model_id="Qwen/Qwen2.5-7B-Instruct",
        served_model_name="Qwen/Qwen2.5-7B-Instruct",
        gpu="L4",
        max_model_len=4096,
        gpu_memory_utilization=0.90,
        dtype="auto",
        quantization=None,
        enforce_eager=True,
        scaledown_window_seconds=60,
        startup_timeout_seconds=600,
        max_concurrent_inputs=8,
        estimated_usd_per_gpu_second=0.000222,
    ),
    "fallback": ModalDeploymentProfile(
        name="fallback",
        model_id="Qwen/Qwen2.5-3B-Instruct",
        served_model_name="Qwen/Qwen2.5-3B-Instruct",
        gpu="T4",
        max_model_len=4096,
        gpu_memory_utilization=0.88,
        dtype="float16",
        quantization=None,
        enforce_eager=True,
        scaledown_window_seconds=60,
        startup_timeout_seconds=480,
        max_concurrent_inputs=8,
        estimated_usd_per_gpu_second=0.000164,
    ),
    "fallback_awq": ModalDeploymentProfile(
        name="fallback_awq",
        model_id="Qwen/Qwen2.5-7B-Instruct-AWQ",
        served_model_name="Qwen/Qwen2.5-7B-Instruct-AWQ",
        gpu="T4",
        max_model_len=4096,
        gpu_memory_utilization=0.90,
        dtype="float16",
        quantization="awq_marlin",
        enforce_eager=True,
        scaledown_window_seconds=60,
        startup_timeout_seconds=540,
        max_concurrent_inputs=8,
        estimated_usd_per_gpu_second=0.000164,
    ),
}

ALLOWED_GPUS: Final[frozenset[str]] = frozenset({"T4", "L4", "A10G", "A100", "L40S"})


def resolve_profile(env: Mapping[str, str] | None = None) -> ModalDeploymentProfile:
    """Resolve and validate the active Modal deployment profile from environment variables."""
    source = os.environ if env is None else env
    profile_name = (source.get("MODAL_SLM_PROFILE") or "primary").strip().lower()
    if profile_name not in DEPLOYMENT_PROFILES:
        supported = ", ".join(sorted(DEPLOYMENT_PROFILES))
        raise ValueError(
            f"Unsupported MODAL_SLM_PROFILE={profile_name!r}. Supported values: {supported}."
        )

    profile = DEPLOYMENT_PROFILES[profile_name]

    model_override = (source.get("MODAL_SLM_MODEL") or "").strip()
    if model_override:
        profile = replace(profile, model_id=model_override, served_model_name=model_override)

    gpu_override = (source.get("MODAL_GPU") or "").strip().upper()
    if gpu_override:
        if gpu_override not in ALLOWED_GPUS:
            raise ValueError(
                f"Unsupported MODAL_GPU={gpu_override!r}. Allowed: {sorted(ALLOWED_GPUS)}."
            )
        profile = replace(profile, gpu=gpu_override)

    raw_scaledown = (source.get("MODAL_SCALEDOWN_WINDOW") or "").strip()
    if raw_scaledown:
        try:
            parsed_scaledown = int(raw_scaledown)
        except ValueError as exc:
            raise ValueError("MODAL_SCALEDOWN_WINDOW must be an integer (seconds).") from exc
        if not (MIN_SCALEDOWN_WINDOW_SECONDS <= parsed_scaledown <= MAX_SCALEDOWN_WINDOW_SECONDS):
            raise ValueError(
                "MODAL_SCALEDOWN_WINDOW must be between "
                f"{MIN_SCALEDOWN_WINDOW_SECONDS} and {MAX_SCALEDOWN_WINDOW_SECONDS} seconds "
                "to guarantee scale-to-zero credit protection."
            )
        profile = replace(profile, scaledown_window_seconds=parsed_scaledown)

    return profile


def resolve_auth_token(env: Mapping[str, str] | None = None) -> str:
    """Resolve Modal Bearer auth token (MODAL_API_KEY primary, MODAL_AUTH_TOKEN alias)."""
    source = os.environ if env is None else env
    token = (source.get("MODAL_API_KEY") or source.get("MODAL_AUTH_TOKEN") or "").strip()
    if len(token) < MIN_AUTH_TOKEN_LENGTH:
        raise ValueError(
            "MODAL_API_KEY (or MODAL_AUTH_TOKEN) must be configured in Modal Secrets with at "
            f"least {MIN_AUTH_TOKEN_LENGTH} characters."
        )
    return token


def build_vllm_serve_command(
    profile: ModalDeploymentProfile,
    *,
    api_key: str,
    host: str = "127.0.0.1",
    port: int = 8001,
) -> list[str]:
    """Build argument vector for launching vLLM OpenAI-compatible server without shell=True."""
    if not api_key or len(api_key.strip()) < MIN_AUTH_TOKEN_LENGTH:
        raise ValueError("Refusing to start vLLM without a valid Bearer API key.")

    cmd = [
        "vllm",
        "serve",
        profile.model_id,
        "--host",
        host,
        "--port",
        str(port),
        "--served-model-name",
        profile.served_model_name,
        "--api-key",
        api_key.strip(),
        "--dtype",
        profile.dtype,
        "--max-model-len",
        str(profile.max_model_len),
        "--gpu-memory-utilization",
        f"{profile.gpu_memory_utilization:.2f}",
        "--enable-prefix-caching",
        "--disable-log-requests",
    ]
    if profile.enforce_eager:
        cmd.append("--enforce-eager")
    if profile.quantization:
        cmd.extend(["--quantization", profile.quantization])
    return cmd


def estimate_inference_cost_usd(
    profile: ModalDeploymentProfile,
    elapsed_seconds: float,
) -> float:
    """Estimate GPU compute cost in USD for a given active execution duration."""
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative.")
    return round(elapsed_seconds * profile.estimated_usd_per_gpu_second, 6)

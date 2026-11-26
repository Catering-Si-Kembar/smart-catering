"""Modal Serverless GPU deployment for Smart Catering AI Business Insight (OPS-04).

Deploy primary profile (Qwen2.5-7B-Instruct on L4 GPU):
    modal deploy infra/modal/serve_vllm.py

Deploy credit-saving fallback profile (Qwen2.5-3B-Instruct on T4 GPU):
    MODAL_SLM_PROFILE=fallback modal deploy infra/modal/serve_vllm.py

Pre-warm model weights into the persistent Modal Volume before first deployment:
    modal run infra/modal/serve_vllm.py::download_weights
"""

from __future__ import annotations

import importlib
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Final

if __package__ in {None, ""}:
    _repo_root = str(Path(__file__).resolve().parents[2])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)

from infra.modal.auth_proxy import create_auth_proxy_server
from infra.modal.config import (
    ModalDeploymentProfile,
    build_vllm_serve_command,
    resolve_auth_token,
    resolve_profile,
)


def _load_modal_sdk() -> Any | None:
    """Load the official Modal Python SDK when installed (skipping local infra/modal package)."""
    try:
        module = importlib.import_module("modal")
    except ImportError:
        return None
    if not hasattr(module, "App") or not hasattr(module, "Image"):
        return None
    return module


modal_sdk: Any | None = _load_modal_sdk()

logger = logging.getLogger("smart_catering.modal.serve_vllm")

APP_NAME: Final[str] = "smart-catering-slm"
SECRET_NAME: Final[str] = "smart-catering-modal-secret"
HF_CACHE_VOLUME_NAME: Final[str] = "smart-catering-hf-cache"
VLLM_CACHE_VOLUME_NAME: Final[str] = "smart-catering-vllm-cache"
HF_CACHE_MOUNT_PATH: Final[str] = "/root/.cache/huggingface"
VLLM_CACHE_MOUNT_PATH: Final[str] = "/root/.cache/vllm"
VLLM_VERSION: Final[str] = "0.8.5.post1"
PUBLIC_PROXY_PORT: Final[int] = 8000
INTERNAL_VLLM_PORT: Final[int] = 8001

ACTIVE_PROFILE: Final[ModalDeploymentProfile] = resolve_profile()


def build_container_env(profile: ModalDeploymentProfile) -> dict[str, str]:
    """Build non-secret environment variables baked into the Modal container image."""
    return {
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_HOME": HF_CACHE_MOUNT_PATH,
        "VLLM_CACHE_ROOT": VLLM_CACHE_MOUNT_PATH,
        "PYTHONPATH": "/root",
        "MODAL_SLM_PROFILE": profile.name,
        "MODAL_SLM_MODEL": profile.model_id,
        "MODAL_GPU": profile.gpu,
        "MODAL_SCALEDOWN_WINDOW": str(profile.scaledown_window_seconds),
    }


def wait_for_vllm_ready(
    *,
    health_url: str,
    timeout_seconds: float = 480.0,
    poll_interval_seconds: float = 2.0,
    process: subprocess.Popen[bytes] | None = None,
) -> None:
    """Block until internal vLLM responds 200 on /health, failing fast if the process exits."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process is not None:
            exit_code = process.poll()
            if exit_code is not None:
                raise RuntimeError(
                    f"Internal vLLM process exited prematurely with code {exit_code}."
                )
        try:
            with urllib.request.urlopen(health_url, timeout=5.0) as resp:  # noqa: S310
                if int(resp.status) == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(poll_interval_seconds)
    raise TimeoutError(f"Internal vLLM server did not become ready within {timeout_seconds}s.")


def launch_authenticated_vllm_runtime(
    profile: ModalDeploymentProfile,
    *,
    api_key: str,
    public_port: int = PUBLIC_PROXY_PORT,
    internal_vllm_port: int = INTERNAL_VLLM_PORT,
) -> tuple[subprocess.Popen[bytes], threading.Thread]:
    """Start internal vLLM server and expose authenticated proxy on public_port."""
    cmd = build_vllm_serve_command(
        profile,
        api_key=api_key,
        host="127.0.0.1",
        port=internal_vllm_port,
    )
    logger.info(
        "Launching vLLM profile=%s model=%s gpu=%s scaledown=%ss",
        profile.name,
        profile.model_id,
        profile.gpu,
        profile.scaledown_window_seconds,
    )
    process = subprocess.Popen(cmd, shell=False)

    wait_for_vllm_ready(
        health_url=f"http://127.0.0.1:{internal_vllm_port}/health",
        timeout_seconds=float(max(60, profile.startup_timeout_seconds - 30)),
        process=process,
    )

    proxy_server = create_auth_proxy_server(
        host="0.0.0.0",
        port=public_port,
        expected_token=api_key,
        upstream_base_url=f"http://127.0.0.1:{internal_vllm_port}",
        served_model_name=profile.served_model_name,
        upstream_health_check=lambda: process.poll() is None,
    )
    proxy_thread = threading.Thread(
        target=proxy_server.serve_forever,
        name="modal-vllm-auth-proxy",
        daemon=True,
    )
    proxy_thread.start()
    return process, proxy_thread


if modal_sdk is not None:
    _LOCAL_MODAL_DIR = Path(__file__).resolve().parent

    vllm_image: Any = (
        modal_sdk.Image.debian_slim(python_version="3.12")
        .pip_install(
            f"vllm=={VLLM_VERSION}",
            "huggingface-hub[hf_transfer]==0.30.2",
        )
        .env(build_container_env(ACTIVE_PROFILE))
        .add_local_dir(
            local_path=str(_LOCAL_MODAL_DIR),
            remote_path="/root/infra/modal",
        )
    )

    hf_cache_vol: Any = modal_sdk.Volume.from_name(HF_CACHE_VOLUME_NAME, create_if_missing=True)
    vllm_cache_vol: Any = modal_sdk.Volume.from_name(
        VLLM_CACHE_VOLUME_NAME,
        create_if_missing=True,
    )
    modal_secret: Any = modal_sdk.Secret.from_name(SECRET_NAME)

    app: Any = modal_sdk.App(APP_NAME)

    def _download_weights_impl(profile_name: str | None = None) -> str:
        """Pre-download open-source model weights into Modal Volume to minimize cold starts."""
        hf_hub = importlib.import_module("huggingface_hub")

        env_override = dict(os.environ)
        if profile_name:
            env_override["MODAL_SLM_PROFILE"] = profile_name
            env_override.pop("MODAL_SLM_MODEL", None)
        profile = resolve_profile(env_override)
        hf_token = (os.environ.get("HF_TOKEN") or "").strip() or None
        hf_hub.snapshot_download(
            repo_id=profile.model_id,
            token=hf_token,
            cache_dir=HF_CACHE_MOUNT_PATH,
        )
        hf_cache_vol.commit()
        return f"Cached weights for {profile.model_id} in volume {HF_CACHE_VOLUME_NAME}."

    download_weights: Any = app.function(
        name="download_weights",
        image=vllm_image,
        volumes={HF_CACHE_MOUNT_PATH: hf_cache_vol},
        secrets=[modal_secret],
        timeout=1800,
    )(_download_weights_impl)

    def _serve_impl() -> None:
        """Serve authenticated OpenAI-compatible vLLM endpoint with scale-to-zero."""
        profile = resolve_profile(os.environ)
        api_key = resolve_auth_token(os.environ)
        launch_authenticated_vllm_runtime(
            profile,
            api_key=api_key,
            public_port=PUBLIC_PROXY_PORT,
            internal_vllm_port=INTERNAL_VLLM_PORT,
        )

    serve: Any = app.function(
        name="serve",
        image=vllm_image,
        gpu=ACTIVE_PROFILE.gpu,
        scaledown_window=ACTIVE_PROFILE.scaledown_window_seconds,
        timeout=ACTIVE_PROFILE.startup_timeout_seconds + 120,
        volumes={
            HF_CACHE_MOUNT_PATH: hf_cache_vol,
            VLLM_CACHE_MOUNT_PATH: vllm_cache_vol,
        },
        secrets=[modal_secret],
    )(
        modal_sdk.concurrent(max_inputs=ACTIVE_PROFILE.max_concurrent_inputs)(
            modal_sdk.web_server(
                port=PUBLIC_PROXY_PORT,
                startup_timeout=ACTIVE_PROFILE.startup_timeout_seconds,
            )(_serve_impl)
        )
    )

from __future__ import annotations

import asyncio
import importlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any, Final

from app.insight.ports import (
    InsightConfigurationError,
    InsightRateLimitError,
    InsightTimeoutError,
    InsightUpstreamError,
    ModalSLMCompletion,
)

_COLD_START_THRESHOLD_MS: Final[int] = 4000
_COLD_START_HEADERS: Final[tuple[str, ...]] = ("x-modal-cold-start", "x-cold-start")


def _extract_cold_start_flag(headers: Mapping[str, str], latency_ms: int) -> bool:
    lower_headers = {k.lower(): v.strip().lower() for k, v in headers.items()}
    for header_name in _COLD_START_HEADERS:
        raw = lower_headers.get(header_name)
        if raw in {"1", "true", "yes"}:
            return True
        if raw in {"0", "false", "no"}:
            return False
    return latency_ms >= _COLD_START_THRESHOLD_MS


async def _post_json(
    *,
    url: str,
    headers: Mapping[str, str],
    json_body: dict[str, Any],
    timeout_seconds: float,
) -> tuple[int, Mapping[str, str], Any]:
    """Perform async JSON POST via httpx when optional insight extra is installed, else urllib."""
    try:
        httpx = importlib.import_module("httpx")
    except ImportError:
        httpx = None

    if httpx is not None:
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    url=url,
                    headers=dict(headers),
                    json=json_body,
                )
                body = response.json() if response.content else {}
                return int(response.status_code), dict(response.headers), body
        except httpx.TimeoutException as exc:
            raise InsightTimeoutError("Modal vLLM inference request timed out.") from exc
        except httpx.HTTPError as exc:
            raise InsightUpstreamError(
                "Modal vLLM HTTP transport failed.",
                retryable=True,
            ) from exc
        except ValueError as exc:
            raise InsightUpstreamError("Modal vLLM returned invalid JSON payload.") from exc

    return await asyncio.to_thread(
        _urllib_post_json_sync,
        url=url,
        headers=headers,
        json_body=json_body,
        timeout_seconds=timeout_seconds,
    )


def _urllib_post_json_sync(
    *,
    url: str,
    headers: Mapping[str, str],
    json_body: dict[str, Any],
    timeout_seconds: float,
) -> tuple[int, Mapping[str, str], Any]:
    data_bytes = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers=dict(headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw.strip() else {}
            resp_headers = {k: v for k, v in resp.headers.items()}
            return int(resp.status), resp_headers, parsed
    except urllib.error.HTTPError as exc:
        raw_err = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_err: Any = json.loads(raw_err) if raw_err.strip() else {}
        except ValueError:
            parsed_err = {"detail": raw_err[:200]}
        err_headers = {k: v for k, v in exc.headers.items()} if exc.headers else {}
        return int(exc.code), err_headers, parsed_err
    except TimeoutError as exc:
        raise InsightTimeoutError("Modal vLLM inference request timed out.") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise InsightTimeoutError("Modal vLLM inference request timed out.") from exc
        raise InsightUpstreamError("Modal vLLM connection failed.", retryable=True) from exc
    except ValueError as exc:
        raise InsightUpstreamError("Modal vLLM returned invalid JSON payload.") from exc


class ModalVLLMClient:
    """OpenAI-compatible vLLM client targeting self-hosted Modal Serverless GPU (OPS-04).

    Strictly isolated to AI Business Insight (AI-06); never used for chatbot RAG (AI-05).
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        default_model: str = "",
        max_retries: int = 1,
        max_tokens: int = 700,
    ) -> None:
        self._base_url = base_url.strip().rstrip("/")
        self._api_key = api_key
        self._default_model = default_model.strip()
        self._max_retries = max(0, max_retries)
        self._max_tokens = max_tokens

    def _resolve_endpoint(self) -> str:
        if self._base_url.endswith("/chat/completions"):
            return self._base_url
        return f"{self._base_url}/chat/completions"

    async def generate_insight_json(
        self,
        *,
        messages: Sequence[dict[str, str]],
        model: str,
        timeout_seconds: float,
    ) -> ModalSLMCompletion:
        resolved_model = model.strip() or self._default_model
        if not self._base_url or not self._api_key or not resolved_model:
            raise InsightConfigurationError(
                "MODAL_SLM_BASE_URL, MODAL_API_KEY, and MODAL_SLM_MODEL must be configured."
            )

        endpoint = self._resolve_endpoint()
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": list(messages),
            "temperature": 0.1,
            "max_tokens": self._max_tokens,
            "response_format": {"type": "json_object"},
        }

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            started_at = time.perf_counter()
            try:
                status_code, response_headers, body = await _post_json(
                    url=endpoint,
                    headers=headers,
                    json_body=payload,
                    timeout_seconds=timeout_seconds,
                )
            except InsightTimeoutError:
                raise
            except InsightUpstreamError as exc:
                last_exc = exc
                if exc.retryable and attempt < self._max_retries:
                    continue
                raise

            latency_ms = max(0, int(round((time.perf_counter() - started_at) * 1000.0)))

            if status_code == 429:
                raise InsightRateLimitError("Modal GPU endpoint rate limit or quota exceeded.")
            if status_code in {401, 403}:
                raise InsightUpstreamError(
                    f"Modal GPU authentication rejected (HTTP {status_code}).",
                    retryable=False,
                )
            if status_code in {500, 502, 503, 504} and attempt < self._max_retries:
                last_exc = InsightUpstreamError(
                    f"Modal GPU returned transient HTTP {status_code}.",
                    retryable=True,
                )
                continue
            if status_code != 200:
                raise InsightUpstreamError(
                    f"Modal GPU returned HTTP {status_code}.",
                    retryable=False,
                )

            return self._parse_completion(
                body=body,
                headers=response_headers,
                requested_model=resolved_model,
                latency_ms=latency_ms,
            )

        raise last_exc or InsightUpstreamError("Modal GPU request failed after retries.")

    def _parse_completion(
        self,
        *,
        body: Any,
        headers: Mapping[str, str],
        requested_model: str,
        latency_ms: int,
    ) -> ModalSLMCompletion:
        if not isinstance(body, Mapping):
            raise InsightUpstreamError("Modal vLLM returned non-object JSON payload.")

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise InsightUpstreamError("Modal vLLM returned empty choices array.")

        first_choice = choices[0]
        if not isinstance(first_choice, Mapping):
            raise InsightUpstreamError("Modal vLLM returned malformed choice item.")

        message = first_choice.get("message")
        if not isinstance(message, Mapping):
            raise InsightUpstreamError("Modal vLLM returned malformed message object.")

        content = str(message.get("content") or "").strip()
        if not content:
            raise InsightUpstreamError("Modal vLLM returned empty completion content.")

        raw_model = str(body.get("model") or requested_model).strip() or requested_model
        usage = body.get("usage")
        tokens_used: int | None = None
        if isinstance(usage, Mapping) and isinstance(usage.get("total_tokens"), int):
            tokens_used = max(0, int(usage["total_tokens"]))

        cold_start = _extract_cold_start_flag(headers, latency_ms)
        return ModalSLMCompletion(
            content=content,
            model_used=raw_model,
            latency_ms=latency_ms,
            cold_start=cold_start,
            tokens_used=tokens_used,
        )

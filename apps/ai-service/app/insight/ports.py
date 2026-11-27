from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class InsightClientError(Exception):
    """Base error for AI Business Insight SLM client operations."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class InsightConfigurationError(InsightClientError):
    """Raised when Modal SLM endpoint URL, API key, or model name is not configured."""


class InsightTimeoutError(InsightClientError):
    """Raised when the Modal GPU vLLM inference call exceeds the configured timeout."""


class InsightRateLimitError(InsightClientError):
    """Raised when the Modal GPU endpoint returns HTTP 429 or quota exhaustion."""


class InsightUpstreamError(InsightClientError):
    """Raised when the Modal GPU vLLM endpoint returns an error or invalid response."""


class InsightValidationError(InsightClientError):
    """Raised when the SLM output violates strict JSON schema or numeric accuracy guardrails."""

    def __init__(self, message: str, *, unexpected_count: int = 0) -> None:
        super().__init__(message, retryable=False)
        self.unexpected_count = unexpected_count


@dataclass(frozen=True, slots=True)
class ModalSLMCompletion:
    """Normalized completion metadata returned by an OpenAI-compatible Modal vLLM client."""

    content: str
    model_used: str
    latency_ms: int
    cold_start: bool = False
    tokens_used: int | None = None


class SLMClientPort(Protocol):
    """Port abstraction for self-hosted open-source SLM/LLM inference (Modal GPU + vLLM)."""

    async def generate_insight_json(
        self,
        *,
        messages: Sequence[dict[str, str]],
        model: str,
        timeout_seconds: float,
    ) -> ModalSLMCompletion:
        """Invoke the Modal vLLM chat completion endpoint and return raw JSON text + telemetry."""
        ...

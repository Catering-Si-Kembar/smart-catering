from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

from app.contracts import RagUserRole
from app.rag.schemas import (
    KnowledgeChunk,
    LLMResponse,
    OperationalToolResult,
    RelevanceDecision,
)


class RagUpstreamError(Exception):
    """Base error raised when an external RAG dependency fails."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class RagTimeoutError(RagUpstreamError):
    """Raised when an upstream LLM, ChromaDB, or backend tool call exceeds timeout."""

    def __init__(self, message: str = "Upstream AI or tool call timed out.") -> None:
        super().__init__(message, retryable=True)


class RagRateLimitError(RagUpstreamError):
    """Raised when the proprietary LLM provider rejects a request with HTTP 429."""

    def __init__(self, message: str = "Upstream LLM provider rate limit reached.") -> None:
        super().__init__(message, retryable=False)


class RagConfigurationError(RagUpstreamError):
    """Raised when required LLM provider credentials are not configured."""

    def __init__(self, message: str = "LLM provider credentials are not configured.") -> None:
        super().__init__(message, retryable=False)


class RelevanceClassifierPort(Protocol):
    """Port for the two-class catering domain relevance classifier (AI-02)."""

    async def classify(self, text: str) -> RelevanceDecision: ...


class KnowledgeBasePort(Protocol):
    """Port for PIC-validated ChromaDB knowledge base retrieval (AI-04)."""

    async def search(
        self,
        query: str,
        *,
        top_k: int = 3,
        category: str | None = None,
    ) -> list[KnowledgeChunk]: ...


class OperationalBackendPort(Protocol):
    """Port for read-only PostgreSQL access via Express backend tools (FS-07)."""

    async def get_order_details(
        self,
        *,
        query: str,
        actor_role: RagUserRole,
        actor_id: str | None,
        request_id: str,
    ) -> OperationalToolResult: ...

    async def get_production_schedule(
        self,
        *,
        start_date: str | None,
        end_date: str | None,
        status: str | None,
        actor_role: RagUserRole,
        actor_id: str | None,
        request_id: str,
    ) -> OperationalToolResult: ...

    async def get_invoice_and_payment_status(
        self,
        *,
        query: str,
        actor_role: RagUserRole,
        actor_id: str | None,
        request_id: str,
    ) -> OperationalToolResult: ...


class LLMClientPort(Protocol):
    """Port for proprietary LLM API calls with structured tool calling."""

    async def generate_with_tools(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        tools: Sequence[dict[str, Any]],
        timeout_seconds: float,
    ) -> LLMResponse: ...

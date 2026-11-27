from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts import RagChatHistoryItem, RagUserRole

RelevanceLabel = Literal["relevant", "out_of_domain"]
GuardrailCategory = Literal[
    "ok",
    "prompt_injection",
    "sql_injection",
    "data_exfiltration",
    "out_of_domain",
]
OperationalToolStatus = Literal[
    "ok",
    "not_found",
    "forbidden",
    "invalid_input",
    "timeout",
    "unavailable",
]
KnowledgeCategory = Literal["menu", "faq", "sop", "payment"]


class RelevanceDecision(BaseModel):
    """Output of the two-class catering domain relevance gate (AI-02)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: RelevanceLabel
    is_relevant: bool
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str


class GuardrailVerdict(BaseModel):
    """Decision returned by input security guardrails before invoking the LLM."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    blocked: bool
    category: GuardrailCategory = "ok"
    reason: str | None = None


class KnowledgeChunk(BaseModel):
    """PIC-validated knowledge base document chunk retrieved from ChromaDB (AI-04)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    content: str
    distance: float = Field(ge=0.0)
    source: str
    category: str
    version: str
    validated_at: str
    validation_status: Literal["verified", "draft"]
    is_verified: bool


class OperationalToolResult(BaseModel):
    """Structured result from read-only Express operational tools (FS-07)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_name: str
    source: str
    status: OperationalToolStatus
    reference_id: str | None = None
    data: dict[str, object] | list[dict[str, object]] | None = None
    message: str


class ToolCallRequest(BaseModel):
    """Normalized tool invocation requested by the LLM."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    call_id: str
    name: str
    arguments: dict[str, object] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Normalized response from a proprietary LLM API supporting tool calling."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    content: str = ""
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    tokens_used: int | None = Field(default=None, ge=0)


class AgentContext(BaseModel):
    """Authenticated execution context passed from Express into the Agentic RAG pipeline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    conversation_id: str
    user_role: RagUserRole
    user_id: str | None = None
    request_id: str
    history: list[RagChatHistoryItem] = Field(default_factory=list)


class RetrievalEvalSample(BaseModel):
    """Evaluation case for Hit@3 knowledge base retrieval verification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str
    expected_sources: list[str]
    category: KnowledgeCategory | None = None


class RetrievalEvalReport(BaseModel):
    """Summary metrics for Hit@3 retrieval evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_queries: int = Field(ge=0)
    hits_at_3: int = Field(ge=0)
    hit_rate_at_3: float = Field(ge=0.0, le=1.0)
    metadata_complete_ratio: float = Field(ge=0.0, le=1.0)

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas import ApiMeta

_NON_ALNUM_PATTERN = re.compile(r"[^0-9a-zA-Z]")


def _validate_meaningful_sentiment_text(value: str) -> str:
    """Require at least 3 meaningful alphanumeric characters for sentiment input."""
    meaningful = _NON_ALNUM_PATTERN.sub("", value)
    if len(meaningful) < 3:
        raise ValueError("Input review text must contain at least 3 meaningful characters.")
    return value


NonEmptyText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
SentimentText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=2000),
    AfterValidator(_validate_meaningful_sentiment_text),
]
NonEmptyShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]

# AI-02: Relevance
RelevanceLabel = Literal["relevant", "out_of_domain"]


class RelevancePredictRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: NonEmptyText = Field(
        description="Customer input text to evaluate for food/catering relevance.",
    )


class RelevancePredictData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(
        description="Customer input text evaluated for relevance.",
    )
    label: RelevanceLabel = Field(
        description="Classification label for relevance.",
    )
    is_relevant: bool = Field(
        description="Convenience boolean flag indicating relevance.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model confidence score between 0 and 1.",
    )
    model_version: str = Field(
        description="Identifier or version of the relevance model.",
    )


class RelevancePredictResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: RelevancePredictData
    meta: ApiMeta


class RelevanceModelMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    f1Score: float = Field(
        ge=0.0,
        le=1.0,
        description="F1-score of the relevance model evaluation.",
    )
    accuracy: float = Field(
        ge=0.0,
        le=1.0,
        description="Accuracy score of the relevance model evaluation.",
    )


class RelevanceMetadataData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    modelName: str = Field(
        description="Name of the relevance classification model.",
    )
    version: str = Field(
        description="Semantic version string of the model.",
    )
    algorithm: str = Field(
        description="Core machine learning algorithm name.",
    )
    classes: list[str] = Field(
        description="List of target relevance classification classes.",
    )
    metrics: RelevanceModelMetrics = Field(
        description="Holdout evaluation metrics summary.",
    )
    isSynthetic: bool = Field(
        default=True,
        description="Whether the training dataset includes synthetic samples (is_synthetic=true).",
    )


class RelevanceMetadataResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: RelevanceMetadataData
    meta: ApiMeta


# AI-03: Sentiment
SentimentLabel = Literal["positive", "negative"]


class SentimentProbabilities(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    positive: float = Field(
        ge=0.0,
        le=1.0,
        description="Probability score for positive sentiment.",
    )
    negative: float = Field(
        ge=0.0,
        le=1.0,
        description="Probability score for negative sentiment.",
    )


class SentimentPredictRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: SentimentText = Field(
        description="Customer feedback review text to analyze.",
    )


class SentimentPredictData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str = Field(
        description="Customer review text analyzed.",
    )
    sentiment: SentimentLabel = Field(
        description="Classified sentiment label.",
    )
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for the predicted sentiment.",
    )
    probabilities: SentimentProbabilities = Field(
        description="Probability breakdown per sentiment class.",
    )
    needsAttention: bool = Field(
        default=False,
        description=(
            "Priority complaint indicator, true when sentiment is negative with score >= 0.75."
        ),
    )


class SentimentPredictResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: SentimentPredictData
    meta: ApiMeta


class SentimentBatchItemRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmptyShortText = Field(
        description="Identifier of the feedback review item.",
    )
    text: SentimentText = Field(
        description="Customer review text to analyze.",
    )


class SentimentBatchRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[SentimentBatchItemRequest] = Field(
        min_length=1,
        max_length=100,
        description="Batch collection of review items to analyze.",
    )


class SentimentBatchItemResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: NonEmptyShortText = Field(
        description="Identifier of the analyzed review item.",
    )
    sentiment: SentimentLabel = Field(
        description="Classified sentiment label.",
    )
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for the predicted sentiment.",
    )
    needsAttention: bool = Field(
        default=False,
        description=(
            "Priority complaint indicator, true when sentiment is negative with score >= 0.75."
        ),
    )


class SentimentBatchResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: list[SentimentBatchItemResult] = Field(
        description="List of sentiment analysis batch item results.",
    )
    meta: ApiMeta


# AI-05: RAG Chat
RagUserRole = Literal["ADMIN", "STAFF"]
RagHistoryRole = Literal["user", "assistant"]
RagValidationStatus = Literal["verified", "draft"]


class RagChatHistoryItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    role: RagHistoryRole = Field(
        description="Speaker role for a prior conversation turn.",
    )
    content: NonEmptyText = Field(
        description="Message content of the prior conversation turn.",
    )


class RagChatRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    message: NonEmptyText = Field(
        description="User operational or domain inquiry message.",
    )
    conversation_id: NonEmptyShortText = Field(
        description="Unique conversation session identifier.",
    )
    user_role: RagUserRole = Field(
        description="Backend-verified role of the user interacting with the chat assistant.",
    )
    user_id: NonEmptyShortText | None = Field(
        default=None,
        description=(
            "Optional backend-verified user identifier for audit and scoped read-only tools."
        ),
    )
    history: list[RagChatHistoryItem] = Field(
        default_factory=list,
        max_length=20,
        description="Optional recent conversation turns forwarded from Express ChatLog.",
    )


class RagSourceItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = Field(
        description="Knowledge base document name or backend operational source identifier.",
    )
    category: str = Field(
        description="Category classification of the knowledge chunk or operational data.",
    )
    chunk_id: str | None = Field(
        default=None,
        description=(
            "Unique identifier of the retrieved ChromaDB context chunk, if sourced from KB."
        ),
    )
    version: str | None = Field(
        default=None,
        description="Document version metadata for PIC-validated knowledge base entries.",
    )
    validated_at: str | None = Field(
        default=None,
        description="Validation or last-updated date (YYYY-MM-DD) of the knowledge base document.",
    )
    validation_status: RagValidationStatus | None = Field(
        default=None,
        description="PIC validation status of the knowledge base document.",
    )
    is_verified: bool | None = Field(
        default=None,
        description="Boolean flag indicating whether the knowledge source is PIC-verified.",
    )
    reference_id: str | None = Field(
        default=None,
        description=(
            "Operational record reference (e.g., orderNumber/invoiceNumber) from read-only tools."
        ),
    )


class RagChatData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    reply: str = Field(
        description="Grounded assistant reply or safe fallback guidance.",
    )
    is_relevant: bool = Field(
        description="Whether the inquiry belongs to the catering domain.",
    )
    tools_called: list[str] = Field(
        default_factory=list,
        description="List of tool or retrieval functions invoked.",
    )
    sources: list[RagSourceItem] = Field(
        default_factory=list,
        description="Retrieved grounding knowledge chunks.",
    )
    tokens_used: int | None = Field(
        default=None,
        description="Total tokens consumed during the assistant generation.",
    )
    is_fallback: bool = Field(
        default=False,
        description="Whether a fallback answer was returned due to upstream outage.",
    )


class RagChatResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: RagChatData
    meta: ApiMeta


# AI-06: Business Insight
class InsightTopMenu(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: NonEmptyShortText = Field(
        description="Menu item name.",
    )
    portions: int = Field(
        ge=0,
        description="Portions produced or ordered.",
    )


class InsightMetricsInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    total_orders: int = Field(
        ge=0,
        description="Total catering orders in the reporting period.",
    )
    total_revenue: int = Field(
        ge=0,
        description="Total revenue generated in IDR.",
    )
    completed_orders: int = Field(
        ge=0,
        description="Number of completed catering orders.",
    )
    unpaid_invoices: int = Field(
        ge=0,
        description="Number of unpaid or outstanding invoices.",
    )
    top_menus: list[InsightTopMenu] = Field(
        default_factory=list,
        max_length=20,
        description="Top selling menu items in the period.",
    )
    forecast_next_week_portions: int | None = Field(
        default=None,
        ge=0,
        description="Forecasted production portions for the upcoming week.",
    )

    @model_validator(mode="after")
    def _validate_order_bounds(self) -> InsightMetricsInput:
        if self.completed_orders > self.total_orders:
            raise ValueError("completed_orders cannot exceed total_orders.")
        return self


class InsightGenerateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    period: NonEmptyShortText = Field(
        description="Reporting period identifier (e.g., 'November 2026').",
    )
    metrics: InsightMetricsInput = Field(
        description="Aggregated operational and financial metrics input.",
    )


class InsightGenerateData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    period: str = Field(
        description="Reporting period string.",
    )
    executive_summary: str = Field(
        description="Synthesized executive summary of operational performance.",
    )
    key_highlights: list[str] = Field(
        description="List of key operational and financial highlights.",
    )
    operational_recommendations: list[str] = Field(
        description="Actionable business and operational recommendations.",
    )
    model_used: str = Field(
        description="Name and provider of the language model producing insights.",
    )
    latency_ms: int = Field(
        ge=0,
        description="Total generation latency in milliseconds.",
    )
    is_fallback: bool = Field(
        default=False,
        description="Whether deterministic template fallback was returned.",
    )


class InsightGenerateResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: InsightGenerateData
    meta: ApiMeta


# AI-04: Chroma Knowledge Base Contracts
ChromaCategory = Literal["menu", "faq", "sop", "payment"]


class ChromaChunkMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_id: str = Field(
        description="Canonical knowledge document identifier.",
    )
    source: str = Field(
        description="Source markdown file name.",
    )
    category: str = Field(
        description="Curated knowledge domain category.",
    )
    version: str = Field(
        description="Document version identifier.",
    )
    validated_at: str = Field(
        description="Date of PIC validation.",
    )
    validation_status: Literal["verified", "draft"] = Field(
        description="PIC verification status string.",
    )
    is_verified: bool = Field(
        description="Boolean indicating whether chunk is verified by PIC.",
    )


class ChromaQueryRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: NonEmptyText = Field(
        description="Search query across curated catering knowledge base.",
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Number of top matching chunks to retrieve.",
    )
    category: ChromaCategory | None = Field(
        default=None,
        description="Optional domain category filter.",
    )


class ChromaQueryResultItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str = Field(
        description="Unique identifier for the knowledge chunk.",
    )
    content: str = Field(
        description="Chunk text content.",
    )
    distance: float = Field(
        ge=0.0,
        description="Cosine distance from query vector (lower is more relevant).",
    )
    metadata: ChromaChunkMetadata = Field(
        description="4-field PIC validation metadata.",
    )


class ChromaQueryData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(
        description="Echoed normalized query string.",
    )
    total_hits: int = Field(
        ge=0,
        description="Total number of hits meeting similarity threshold.",
    )
    results: list[ChromaQueryResultItem] = Field(
        description="List of matching knowledge chunks ordered by similarity.",
    )


class ChromaQueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: ChromaQueryData
    meta: ApiMeta


class ChromaIngestRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    knowledge_dir: str | None = Field(
        default=None,
        description="Optional directory path containing curated markdown files.",
    )

    @field_validator("knowledge_dir")
    @classmethod
    def _validate_knowledge_dir(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if ".." in trimmed or trimmed.startswith(("/", "\\")) or ":" in trimmed:
            raise ValueError("Path traversal or absolute directory path is not permitted.")
        return trimmed


class ChromaIngestData(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    collection_name: str = Field(
        description="Name of the ChromaDB collection.",
    )
    files_processed: int = Field(
        ge=0,
        description="Number of knowledge markdown files parsed.",
    )
    chunks_upserted: int = Field(
        ge=0,
        description="Number of chunks upserted in this ingest run.",
    )
    total_chunks: int = Field(
        ge=0,
        description="Total chunks currently stored in the collection.",
    )
    idempotent: bool = Field(
        default=True,
        description="Indicates whether repeated ingest runs yield identical collection state.",
    )


class ChromaIngestResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data: ChromaIngestData
    meta: ApiMeta

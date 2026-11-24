from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyInsightText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=10, max_length=1500),
]
NonEmptyInsightBullet = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=5, max_length=400),
]


class SLMInsightPayload(BaseModel):
    """Strict Pydantic schema validating structured JSON returned by the Modal vLLM SLM."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    executive_summary: NonEmptyInsightText = Field(
        description="Executive summary strictly grounded in input KPI numbers.",
    )
    key_highlights: list[NonEmptyInsightBullet] = Field(
        min_length=1,
        max_length=6,
        description="Concise operational and financial highlights grounded in input KPIs.",
    )
    operational_recommendations: list[NonEmptyInsightBullet] = Field(
        min_length=1,
        max_length=6,
        description="Actionable recommendations for ADMIN catering management.",
    )


class DerivedMenuShare(BaseModel):
    """Deterministic top-menu contribution fact derived from input portions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    portions: int = Field(ge=0)
    share_pct: float = Field(ge=0.0, le=100.0)


class DerivedKPIFacts(BaseModel):
    """Deterministic KPI facts derived from InsightMetricsInput for grounding & verification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_orders: int = Field(ge=0)
    completed_orders: int = Field(ge=0)
    uncompleted_orders: int = Field(ge=0)
    unpaid_invoices: int = Field(ge=0)
    settled_orders_estimate: int = Field(ge=0)
    total_revenue: int = Field(ge=0)
    formatted_revenue: str
    completion_rate_pct: float = Field(ge=0.0, le=100.0)
    completion_rate_floor_pct: float = Field(ge=0.0, le=100.0)
    settled_rate_pct: float = Field(ge=0.0, le=100.0)
    settled_rate_floor_pct: float = Field(ge=0.0, le=100.0)
    average_order_value: int = Field(ge=0)
    formatted_average_order_value: str
    total_top_menu_portions: int = Field(ge=0)
    top_menu_shares: list[DerivedMenuShare] = Field(default_factory=list)
    forecast_next_week_portions: int | None = Field(default=None, ge=0)


class NumericValidationResult(BaseModel):
    """Post-generation numeric sanity check result preventing metric hallucinations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    is_valid: bool
    checked_tokens: list[str] = Field(default_factory=list)
    unexpected_tokens: list[str] = Field(default_factory=list)
    missing_core_metrics: list[str] = Field(default_factory=list)
    reason: str | None = None


class ReportEvaluationRow(BaseModel):
    """Evaluation telemetry for one business report in the 10-report AI-06 benchmark."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    report_id: str
    period: str
    model_used: str
    is_fallback: bool
    latency_ms: int = Field(ge=0)
    numeric_accuracy_passed: bool
    checked_numeric_tokens: int = Field(ge=0)
    unexpected_tokens: list[str] = Field(default_factory=list)
    missing_core_metrics: list[str] = Field(default_factory=list)


class EvaluationSuiteSummary(BaseModel):
    """Aggregated summary across the 10-report AI Business Insight evaluation benchmark."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    is_synthetic: bool = Field(
        default=True,
        description="Explicitly marks that the 10 benchmark reports use non-PII synthetic data.",
    )
    data_source: str = Field(
        default="synthetic_benchmark_non_pii_ai06",
        description="Provenance identifier of the evaluation dataset.",
    )
    total_reports: int = Field(ge=1)
    numeric_match_count: int = Field(ge=0)
    numeric_match_rate: float = Field(ge=0.0, le=1.0)
    fallback_count: int = Field(ge=0)
    min_latency_ms: int = Field(ge=0)
    avg_latency_ms: float = Field(ge=0.0)
    max_latency_ms: int = Field(ge=0)
    results: list[ReportEvaluationRow]

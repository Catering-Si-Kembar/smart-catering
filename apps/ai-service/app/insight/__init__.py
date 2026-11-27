from __future__ import annotations

from app.insight.fallback import DETERMINISTIC_FALLBACK_MODEL, build_deterministic_insight
from app.insight.guardrails import (
    extract_numeric_tokens,
    parse_slm_insight_payload,
    validate_insight_numbers,
)
from app.insight.modal_client import ModalVLLMClient
from app.insight.ports import (
    InsightClientError,
    InsightConfigurationError,
    InsightRateLimitError,
    InsightTimeoutError,
    InsightUpstreamError,
    InsightValidationError,
    ModalSLMCompletion,
    SLMClientPort,
)
from app.insight.prompts import (
    build_insight_messages,
    compute_derived_kpi_facts,
    format_idr,
    sanitize_prompt_text,
)
from app.insight.schemas import (
    DerivedKPIFacts,
    DerivedMenuShare,
    EvaluationSuiteSummary,
    NumericValidationResult,
    ReportEvaluationRow,
    SLMInsightPayload,
)
from app.insight.service import BusinessInsightService, build_default_insight_service

__all__ = [
    "BusinessInsightService",
    "DETERMINISTIC_FALLBACK_MODEL",
    "DerivedKPIFacts",
    "DerivedMenuShare",
    "EvaluationSuiteSummary",
    "InsightClientError",
    "InsightConfigurationError",
    "InsightRateLimitError",
    "InsightTimeoutError",
    "InsightUpstreamError",
    "InsightValidationError",
    "ModalSLMCompletion",
    "ModalVLLMClient",
    "NumericValidationResult",
    "ReportEvaluationRow",
    "SLMClientPort",
    "SLMInsightPayload",
    "build_default_insight_service",
    "build_deterministic_insight",
    "build_insight_messages",
    "compute_derived_kpi_facts",
    "extract_numeric_tokens",
    "format_idr",
    "parse_slm_insight_payload",
    "sanitize_prompt_text",
    "validate_insight_numbers",
]

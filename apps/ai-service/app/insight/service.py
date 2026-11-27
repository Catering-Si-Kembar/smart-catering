from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.config import AppSettings
from app.contracts import InsightGenerateData, InsightGenerateRequest
from app.insight.fallback import DETERMINISTIC_FALLBACK_MODEL, build_deterministic_insight
from app.insight.guardrails import parse_slm_insight_payload, validate_insight_numbers
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
from app.insight.prompts import build_insight_messages, compute_derived_kpi_facts
from app.insight.schemas import DerivedKPIFacts, SLMInsightPayload

logger = logging.getLogger("smart_catering.ai_service.insight")


class BusinessInsightService:
    """Orchestrates AI Business Insight generation (AI-06) with numeric guardrails & fallback."""

    def __init__(
        self,
        *,
        slm_client: SLMClientPort,
        primary_model: str,
        fallback_model: str = "",
        timeout_seconds: float = 18.0,
        secret_values: tuple[str, ...] = (),
    ) -> None:
        self._slm_client = slm_client
        self._primary_model = primary_model.strip()
        self._fallback_model = fallback_model.strip()
        self._timeout_seconds = timeout_seconds
        self._secret_values = tuple(val for val in secret_values if val)

    async def generate(
        self,
        request: InsightGenerateRequest,
        *,
        request_id: str = "unknown",
    ) -> InsightGenerateData:
        """Generate grounded executive insight JSON ready for Express FS-08 analytics PDF."""
        started_at = time.perf_counter()
        facts = compute_derived_kpi_facts(request)
        messages = build_insight_messages(request, facts)

        candidate_models: list[str] = []
        if self._primary_model:
            candidate_models.append(self._primary_model)
        if self._fallback_model and self._fallback_model != self._primary_model:
            candidate_models.append(self._fallback_model)

        fallback_reason: str | None = None
        last_cold_start = False
        last_tokens_used: int | None = None
        last_unexpected_count = 0

        if not candidate_models:
            fallback_reason = "modal_not_configured"
        else:
            for idx, model_name in enumerate(candidate_models):
                elapsed_seconds = time.perf_counter() - started_at
                remaining_timeout = self._timeout_seconds - elapsed_seconds
                if idx > 0 and remaining_timeout < 2.0:
                    fallback_reason = fallback_reason or "timeout_budget_exhausted"
                    break

                attempt_timeout = max(1.0, remaining_timeout)
                try:
                    completion = await self._slm_client.generate_insight_json(
                        messages=messages,
                        model=model_name,
                        timeout_seconds=attempt_timeout,
                    )
                    last_cold_start = completion.cold_start
                    last_tokens_used = completion.tokens_used
                    validated = self._validate_completion(
                        request=request,
                        facts=facts,
                        completion=completion,
                    )
                except InsightConfigurationError:
                    fallback_reason = "modal_not_configured"
                    break
                except InsightRateLimitError:
                    fallback_reason = "modal_rate_limited"
                    break
                except InsightTimeoutError:
                    fallback_reason = "modal_timeout"
                    continue
                except InsightUpstreamError:
                    fallback_reason = "modal_upstream_error"
                    continue
                except InsightValidationError as exc:
                    fallback_reason = "numeric_or_schema_guardrail_failed"
                    last_unexpected_count = exc.unexpected_count
                    continue
                except InsightClientError:
                    fallback_reason = "modal_client_error"
                    continue

                total_latency_ms = max(
                    completion.latency_ms,
                    int(round((time.perf_counter() - started_at) * 1000.0)),
                )
                result = InsightGenerateData(
                    period=request.period,
                    executive_summary=validated.executive_summary,
                    key_highlights=validated.key_highlights,
                    operational_recommendations=validated.operational_recommendations,
                    model_used=completion.model_used,
                    latency_ms=total_latency_ms,
                    is_fallback=idx > 0,
                )
                self._log_generation(
                    request_id=request_id,
                    period=request.period,
                    model_used=result.model_used,
                    latency_ms=result.latency_ms,
                    cold_start=completion.cold_start,
                    is_fallback=result.is_fallback,
                    fallback_reason=fallback_reason if result.is_fallback else None,
                    numeric_check_passed=True,
                    unexpected_numbers_count=0,
                    tokens_used=completion.tokens_used,
                )
                return result

        total_latency_ms = max(0, int(round((time.perf_counter() - started_at) * 1000.0)))
        fallback_result = build_deterministic_insight(
            request,
            facts,
            model_used=DETERMINISTIC_FALLBACK_MODEL,
            latency_ms=total_latency_ms,
        )
        self._log_generation(
            request_id=request_id,
            period=request.period,
            model_used=fallback_result.model_used,
            latency_ms=fallback_result.latency_ms,
            cold_start=last_cold_start,
            is_fallback=True,
            fallback_reason=fallback_reason or "deterministic_fallback",
            numeric_check_passed=True,
            unexpected_numbers_count=last_unexpected_count,
            tokens_used=last_tokens_used,
        )
        return fallback_result

    def _validate_completion(
        self,
        *,
        request: InsightGenerateRequest,
        facts: DerivedKPIFacts,
        completion: ModalSLMCompletion,
    ) -> SLMInsightPayload:
        payload = parse_slm_insight_payload(completion.content)
        check = validate_insight_numbers(
            request,
            facts,
            payload,
            secret_values=self._secret_values,
        )
        if not check.is_valid:
            raise InsightValidationError(
                check.reason or "Numeric verification guardrail failed.",
                unexpected_count=len(check.unexpected_tokens),
            )
        return payload

    def _log_generation(
        self,
        *,
        request_id: str,
        period: str,
        model_used: str,
        latency_ms: int,
        cold_start: bool,
        is_fallback: bool,
        fallback_reason: str | None,
        numeric_check_passed: bool,
        unexpected_numbers_count: int,
        tokens_used: int | None,
    ) -> None:
        log_payload: dict[str, Any] = {
            "event": "insight_generation",
            "requestId": request_id,
            "period": period,
            "modelUsed": model_used,
            "latencyMs": latency_ms,
            "coldStart": cold_start,
            "isFallback": is_fallback,
            "fallbackReason": fallback_reason,
            "numericCheckPassed": numeric_check_passed,
            "unexpectedNumbersCount": unexpected_numbers_count,
            "tokensUsed": tokens_used,
        }
        line = json.dumps(log_payload, separators=(",", ":"), ensure_ascii=False)
        if is_fallback:
            logger.warning(line)
        else:
            logger.info(line)


def build_default_insight_service(settings: AppSettings) -> BusinessInsightService:
    """Build default DI BusinessInsightService wired strictly to Modal GPU vLLM config."""
    client = ModalVLLMClient(
        base_url=settings.modal_slm_base_url,
        api_key=settings.modal_api_key,
        default_model=settings.modal_slm_model,
    )
    return BusinessInsightService(
        slm_client=client,
        primary_model=settings.modal_slm_model,
        fallback_model=settings.modal_slm_fallback_model,
        timeout_seconds=settings.modal_timeout_seconds,
        secret_values=(
            settings.modal_api_key,
            settings.internal_service_secret,
            settings.llm_api_key,
        ),
    )

from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Request, Response

from app.context import get_request_id
from app.contracts import (
    InsightGenerateRequest,
    InsightGenerateResponse,
    RagChatRequest,
    RagChatResponse,
    RelevanceMetadataResponse,
    RelevancePredictRequest,
    RelevancePredictResponse,
    SentimentBatchRequest,
    SentimentBatchResponse,
    SentimentPredictRequest,
    SentimentPredictResponse,
)
from app.errors import AppProblemError
from app.insight.service import BusinessInsightService, build_default_insight_service
from app.responses import create_success_response
from app.schemas import HealthData, HealthResponse


def verify_internal_token(request: Request) -> None:
    """Validate X-Internal-Token header when INTERNAL_SERVICE_SECRET is configured."""
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        return
    secret = getattr(settings, "internal_service_secret", None)
    if not secret:
        return
    token = request.headers.get("x-internal-token")
    if not token or not hmac.compare_digest(token, secret):
        raise AppProblemError(
            status_code=401,
            detail="Authentication credentials are required or invalid.",
        )


def verify_admin_actor(request: Request) -> None:
    """Enforce ADMIN-only RBAC for executive business insight generation.

    Always rejects non-ADMIN X-Actor-Role headers with 403 Forbidden. When running in
    production or with INTERNAL_SERVICE_SECRET configured, requires X-Actor-Role: ADMIN.
    """
    raw_role = request.headers.get("x-actor-role")
    normalized_role = raw_role.strip().upper() if raw_role is not None else ""
    if normalized_role and normalized_role != "ADMIN":
        raise AppProblemError(
            status_code=403,
            detail="Only ADMIN users are authorized to generate AI Business Insights.",
        )

    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        return

    requires_strict_role = bool(getattr(settings, "internal_service_secret", "")) or (
        getattr(settings, "app_env", "development") == "production"
    )
    if requires_strict_role and normalized_role != "ADMIN":
        raise AppProblemError(
            status_code=403,
            detail="Missing or unauthorized X-Actor-Role header; ADMIN role is required.",
        )


def get_insight_service(request: Request) -> BusinessInsightService:
    """Resolve BusinessInsightService via FastAPI dependency injection."""
    service = getattr(request.app.state, "insight_service", None)
    if isinstance(service, BusinessInsightService):
        return service
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise AppProblemError(
            status_code=503,
            detail="Business insight generation service is not initialized.",
        )
    resolved = build_default_insight_service(settings)
    request.app.state.insight_service = resolved
    return resolved


v1_router = APIRouter(prefix="/api/v1")


@v1_router.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Check AI service liveness v1",
)
async def get_v1_health(request: Request) -> Response:
    return create_success_response(
        request,
        HealthData(status="ok", service="ai-service"),
    )


@v1_router.head("/health", include_in_schema=False)
async def head_v1_health(request: Request) -> Response:
    response = create_success_response(
        request,
        HealthData(status="ok", service="ai-service"),
    )
    return Response(
        content=b"",
        status_code=200,
        headers=dict(response.headers),
        media_type="application/json",
    )


@v1_router.post(
    "/ml/predict-relevance",
    response_model=RelevancePredictResponse,
    tags=["Relevance"],
    summary="Predict catering domain relevance",
    dependencies=[Depends(verify_internal_token)],
)
async def predict_relevance(
    payload: RelevancePredictRequest,
) -> RelevancePredictResponse:
    raise AppProblemError(
        status_code=503,
        detail="Relevance prediction capability is temporarily unavailable.",
    )


@v1_router.get(
    "/ml/relevance/metadata",
    response_model=RelevanceMetadataResponse,
    tags=["Relevance"],
    summary="Get relevance classification model metadata",
    dependencies=[Depends(verify_internal_token)],
)
async def get_relevance_metadata() -> RelevanceMetadataResponse:
    raise AppProblemError(
        status_code=503,
        detail="Relevance metadata capability is temporarily unavailable.",
    )


@v1_router.post(
    "/ml/predict-sentiment",
    response_model=SentimentPredictResponse,
    tags=["Sentiment"],
    summary="Predict customer feedback sentiment",
    dependencies=[Depends(verify_internal_token)],
)
async def predict_sentiment(
    payload: SentimentPredictRequest,
) -> SentimentPredictResponse:
    raise AppProblemError(
        status_code=503,
        detail="Sentiment analysis capability is temporarily unavailable.",
    )


@v1_router.post(
    "/ml/predict-sentiment/batch",
    response_model=SentimentBatchResponse,
    tags=["Sentiment"],
    summary="Predict batch customer feedback sentiment",
    dependencies=[Depends(verify_internal_token)],
)
async def predict_sentiment_batch(
    payload: SentimentBatchRequest,
) -> SentimentBatchResponse:
    raise AppProblemError(
        status_code=503,
        detail="Batch sentiment analysis capability is temporarily unavailable.",
    )


@v1_router.post(
    "/rag/chat",
    response_model=RagChatResponse,
    tags=["RAG"],
    summary="Generate catering RAG assistant response",
    dependencies=[Depends(verify_internal_token)],
)
async def rag_chat(
    payload: RagChatRequest,
) -> RagChatResponse:
    raise AppProblemError(
        status_code=503,
        detail="RAG chat assistant capability is temporarily unavailable.",
    )


@v1_router.post(
    "/insight/generate",
    response_model=InsightGenerateResponse,
    tags=["Insights"],
    summary="Generate catering operational business insights",
    dependencies=[Depends(verify_internal_token), Depends(verify_admin_actor)],
)
async def generate_business_insights(
    request: Request,
    payload: InsightGenerateRequest,
    insight_service: BusinessInsightService = Depends(get_insight_service),  # noqa: B008
) -> Response:
    result = await insight_service.generate(payload, request_id=get_request_id(request))
    return create_success_response(request, result)

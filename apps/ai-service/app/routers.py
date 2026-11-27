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
from app.ml.sentiment.inference import (
    SentimentArtifactMissingError,
    SentimentClassifierService,
)
from app.rag.service import AgenticRagService, build_default_rag_service
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


def get_sentiment_service(request: Request) -> SentimentClassifierService:
    """Dependency provider returning singleton SentimentClassifierService from app state."""
    service = getattr(request.app.state, "sentiment_service", None)
    if isinstance(service, SentimentClassifierService):
        return service
    service = SentimentClassifierService()
    request.app.state.sentiment_service = service
    return service


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
    request: Request,
    payload: SentimentPredictRequest,
    sentiment_service: SentimentClassifierService = Depends(get_sentiment_service),  # noqa: B008
) -> Response:
    try:
        result = sentiment_service.predict(payload.text)
    except SentimentArtifactMissingError as exc:
        raise AppProblemError(
            status_code=503,
            detail="Sentiment analysis model artifacts are unavailable.",
        ) from exc
    return create_success_response(request, result)


@v1_router.post(
    "/ml/predict-sentiment/batch",
    response_model=SentimentBatchResponse,
    tags=["Sentiment"],
    summary="Predict batch customer feedback sentiment",
    dependencies=[Depends(verify_internal_token)],
)
async def predict_sentiment_batch(
    request: Request,
    payload: SentimentBatchRequest,
    sentiment_service: SentimentClassifierService = Depends(get_sentiment_service),  # noqa: B008
) -> Response:
    try:
        results = sentiment_service.predict_batch(payload.items)
    except SentimentArtifactMissingError as exc:
        raise AppProblemError(
            status_code=503,
            detail="Sentiment analysis model artifacts are unavailable.",
        ) from exc
    return create_success_response(request, results)


def get_rag_service(request: Request) -> AgenticRagService:
    """Resolve AgenticRagService via FastAPI dependency injection."""
    service = getattr(request.app.state, "rag_service", None)
    if isinstance(service, AgenticRagService):
        return service
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise AppProblemError(
            status_code=503,
            detail="RAG chat assistant service is not initialized.",
        )
    resolved = build_default_rag_service(settings)
    request.app.state.rag_service = resolved
    return resolved


@v1_router.post(
    "/rag/chat",
    response_model=RagChatResponse,
    tags=["RAG"],
    summary="Generate catering RAG assistant response",
    dependencies=[Depends(verify_internal_token)],
)
async def rag_chat(
    request: Request,
    payload: RagChatRequest,
    rag_service: AgenticRagService = Depends(get_rag_service),  # noqa: B008
) -> Response:
    result = await rag_service.chat(payload, request_id=get_request_id(request))
    return create_success_response(request, result)


@v1_router.post(
    "/insight/generate",
    response_model=InsightGenerateResponse,
    tags=["Insights"],
    summary="Generate catering operational business insights",
    dependencies=[Depends(verify_internal_token)],
)
async def generate_business_insights(
    payload: InsightGenerateRequest,
) -> InsightGenerateResponse:
    raise AppProblemError(
        status_code=503,
        detail="Business insight generation capability is temporarily unavailable.",
    )
